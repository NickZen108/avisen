#!/usr/bin/env python3
"""Safety wrapper for Morgentidende Pipeline v3.

This module deliberately sits outside the editorial brain. It adds only machine
safety: an atomic daily budget reservation, hard call counts, bounded runtime,
fail-closed backend behavior, and a dedicated low-cost vision pass for Hero
relevance. It then runs the normal v3 pipeline functions.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

import v3_pipeline as p

CPH = ZoneInfo("Europe/Copenhagen")
MAX_RUN_CALLS = int(p.CONFIG["limits"].get("max_ai_calls_per_run", 24))
MAX_STORY_CALLS = int(p.CONFIG["limits"].get("max_ai_calls_per_story", 10))
REQUEST_TIMEOUT = int(p.CONFIG["limits"].get("ai_request_timeout_seconds", 90))
OPERATIONAL_LIMIT = float(p.CONFIG["cost"].get("daily_operational_limit_dkk", 9.0))
HARD_LIMIT = float(p.CONFIG["cost"].get("daily_hard_limit_dkk", 10.0))
FX = float(p.CONFIG["cost"].get("fx_usd_dkk", 6.45))

RUN_CALLS = 0
STORY_CALLS = defaultdict(int)
VISION_CACHE: dict[tuple[str, tuple[str, ...]], dict] = {}


class BudgetLimitExceeded(RuntimeError):
    pass


class SafetyLimitExceeded(RuntimeError):
    pass


def budget_date() -> str:
    return datetime.now(CPH).date().isoformat()


def private_backend(action: str, **kwargs):
    if not p.BACKEND_URL or not p.OIDC_TOKEN:
        raise SafetyLimitExceeded("Private budget backend unavailable; AI calls fail closed")
    r = requests.post(
        p.BACKEND_URL,
        headers={"authorization": f"Bearer {p.OIDC_TOKEN}", "content-type": "application/json"},
        json={"action": action, **kwargs},
        timeout=20,
    )
    data = {}
    try:
        data = r.json()
    except Exception:
        pass
    if r.status_code == 429:
        return {"ok": False, "status": 429, **(data or {})}
    if not r.ok:
        raise SafetyLimitExceeded(f"Private backend {action} failed HTTP {r.status_code}: {str(data)[:250]}")
    return data


def reserve_upper_bound_dkk(model: str, instructions: str, prompt: str, max_output_tokens: int, images: list[str]) -> float:
    prices = p.CONFIG.get("model_prices_usd_per_million_tokens", {}).get(model)
    if not prices:
        raise SafetyLimitExceeded(f"No price configured for model {model}; refusing unmetered call")
    # UTF-8 bytes are a deliberately conservative upper bound for text tokens.
    # Vision input is URL-based, so reserve a generous 8k input tokens/image.
    text_upper = len((str(instructions) + "\n" + str(prompt)).encode("utf-8"))
    input_upper = text_upper + 8000 * len(images or [])
    usd = (
        input_upper * float(prices.get("input", 0))
        + int(max_output_tokens) * float(prices.get("output", 0))
    ) / 1_000_000
    # 50% metering headroom plus 1 øre minimum keeps actual usage below the
    # reservation under normal tokenizer/image-accounting variation.
    return round(max(0.01, usd * FX * 1.50), 6)


def _reserve(stage: str, model: str, instructions: str, prompt: str, max_output_tokens: int, images: list[str], story_id: str | None):
    global RUN_CALLS
    if RUN_CALLS >= MAX_RUN_CALLS:
        raise SafetyLimitExceeded(f"Run call ceiling reached ({MAX_RUN_CALLS})")
    story_key = story_id or "__run__"
    if STORY_CALLS[story_key] >= MAX_STORY_CALLS:
        raise SafetyLimitExceeded(f"Story call ceiling reached ({MAX_STORY_CALLS}) for {story_key}")

    amount = reserve_upper_bound_dkk(model, instructions, prompt, max_output_tokens, images)
    reservation_id = f"{p.RUN_ID}:{RUN_CALLS + 1}:{stage}:{uuid.uuid4().hex[:10]}"
    result = private_backend(
        "budget_reserve",
        reservation_id=reservation_id,
        budget_date=budget_date(),
        amount_dkk=amount,
        run_id=p.RUN_ID,
        stage=stage,
    )
    if not result.get("ok"):
        detail = result.get("budget") or result
        raise BudgetLimitExceeded(
            f"Daily AI budget stop before {stage}: reserved request {amount:.3f} kr; {detail}"
        )
    RUN_CALLS += 1
    STORY_CALLS[story_key] += 1
    return reservation_id, amount


def _settle(reservation_id: str, actual_dkk: float = 0.0, *, unknown_charge: bool = False):
    private_backend(
        "budget_settle",
        reservation_id=reservation_id,
        actual_dkk=max(0.0, float(actual_dkk or 0.0)),
        charge_reservation=bool(unknown_charge),
    )


def safe_call_ai(stage, model, instructions, prompt, *, story_id=None, inbox_id=None,
                 max_output_tokens=800, images=None, web_search=False, reasoning="low"):
    images = list(images or [])[:5]
    if web_search and not str(model or "").startswith("openai/"):
        raise SafetyLimitExceeded("Native Workers AI call cannot be treated as live web research")
    reservation_id, reserved = _reserve(
        stage, model, instructions, prompt, int(max_output_tokens), images, story_id
    )
    payload = {
        "stage": stage,
        "model": model,
        "instructions": instructions,
        "input": prompt,
        "max_output_tokens": int(max_output_tokens),
        "images": images,
        "web_search": bool(web_search),
        "reasoning": reasoning,
    }
    started = time.time()
    error = None
    text = ""
    usage = {}
    request_id = None
    actual_dkk = 0.0
    try:
        r = requests.post(
            p.WORKER_URL + "/run",
            headers={"authorization": f"Bearer {p.WORKER_TOKEN}", "content-type": "application/json"},
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        request_id = r.headers.get("cf-ray")
        try:
            data = r.json()
        except Exception:
            data = {"ok": False, "error": r.text[:500]}
        if not r.ok or not data.get("ok"):
            raise RuntimeError(f"AI {stage} HTTP {r.status_code}: {data}")
        text = data.get("text") or ""
        usage = data.get("usage") or {}
        if not text.strip():
            raise RuntimeError(f"AI {stage} returned empty text")
        inp, out, cached, usd, actual_dkk = p.estimate_cost(model, usage)
        elapsed_ms = int((time.time() - started) * 1000)
        p.backend("log_ai", row={
            "run_id": p.RUN_ID,
            "story_id": story_id,
            "inbox_id": inbox_id,
            "stage": stage,
            "provider": "workers-ai-native" if str(model).startswith("@cf/") else "cloudflare-ai-gateway",
            "model": model,
            "request_id": request_id,
            "attempt": 1,
            "status": "success",
            "input_tokens": inp,
            "output_tokens": out,
            "cached_input_tokens": cached,
            "estimated_cost_usd": round(usd, 8),
            "estimated_cost_dkk": round(actual_dkk, 6),
            "latency_ms": elapsed_ms,
            "prompt_text": prompt,
            "response_text": text,
            "metadata": {"reasoning": reasoning, "web_search": web_search, "image_count": len(images), "budget_reserved_dkk": reserved},
            "expires_at": (datetime.now(timezone.utc) + p.timedelta(days=90)).isoformat(timespec="seconds"),
        })
        _settle(reservation_id, actual_dkk)
        return text, {
            "input_tokens": inp,
            "output_tokens": out,
            "cached_input_tokens": cached,
            "usd": usd,
            "dkk": actual_dkk,
            "latency_ms": elapsed_ms,
        }
    except Exception as e:
        error = str(e)
        elapsed_ms = int((time.time() - started) * 1000)
        # A timeout/provider error can still have consumed tokens remotely. Charge
        # the whole conservative reservation so repeated failures cannot burn money.
        try:
            _settle(reservation_id, actual_dkk, unknown_charge=True)
        finally:
            p.backend("log_ai", row={
                "run_id": p.RUN_ID,
                "story_id": story_id,
                "inbox_id": inbox_id,
                "stage": stage,
                "provider": "workers-ai-native" if str(model).startswith("@cf/") else "cloudflare-ai-gateway",
                "model": model,
                "request_id": request_id,
                "attempt": 1,
                "status": "error",
                "input_tokens": 0,
                "output_tokens": 0,
                "cached_input_tokens": 0,
                "estimated_cost_usd": 0,
                "estimated_cost_dkk": reserved,
                "latency_ms": elapsed_ms,
                "prompt_text": prompt,
                "response_text": text or None,
                "error_message": error,
                "metadata": {"budget_reserved_dkk": reserved, "charged_full_reservation": True},
                "expires_at": (datetime.now(timezone.utc) + p.timedelta(days=90)).isoformat(timespec="seconds"),
            })
        raise


def no_external_research(query, story_id, inbox_id=None):
    # Deliberately do not let a non-web model invent URLs. Scan + direct source
    # fetches remain available. If the Chief still needs research, the story parks.
    return []


def _vision_review(draft, images, story_id):
    key = (story_id, tuple(str(x.get("src") or "") for x in images))
    if key in VISION_CACHE:
        return VISION_CACHE[key]
    model = p.CONFIG["models"]["media_vision"]
    candidates = [
        {"index": i, "description": im.get("description"), "search_term": im.get("search_term"), "license": im.get("license")}
        for i, im in enumerate(images)
    ]
    instructions = """Du er billedredaktør. Se de faktiske billeder og vælg kun et Hero, der semantisk er relevant for den konkrete nyhed. Lovlig licens alene er ikke nok. Afvis historiske, geografisk forkerte eller tilfældige billeder. Svar på præcis to linjer: BEST=<indeks eller NONE> og REASON=<kort dansk begrundelse>. Ingen anden tekst."""
    prompt = json.dumps({"title": draft.get("title"), "standfirst": draft.get("standfirst"), "candidates": candidates}, ensure_ascii=False)
    text, _ = safe_call_ai(
        "media_vision",
        model,
        instructions,
        prompt,
        story_id=story_id,
        max_output_tokens=140,
        images=[x.get("src") for x in images if x.get("src")],
        reasoning="low",
    )
    m = re.search(r"BEST\s*=\s*(NONE|\d+)", text, flags=re.I)
    reason_m = re.search(r"REASON\s*=\s*(.+)", text, flags=re.I)
    if not m:
        result = {"best": None, "reason": "Billedmodellen gav ikke et entydigt valg"}
    elif m.group(1).upper() == "NONE":
        result = {"best": None, "reason": (reason_m.group(1).strip() if reason_m else "Ingen kandidat er relevant")}
    else:
        idx = int(m.group(1))
        result = {"best": idx if 0 <= idx < len(images) else None, "reason": (reason_m.group(1).strip() if reason_m else "")}
    VISION_CACHE[key] = result
    return result


def safe_chief_review(draft, desk, evidence, images, state, story_id, high_risk=False):
    vision = _vision_review(draft, images, story_id)
    if vision.get("best") is None:
        return {
            "decision": "media_retry",
            "issues": [vision.get("reason") or "Ingen semantisk relevant Hero-kandidat"],
            "hero_choice": None,
            "frontpage_role": desk.get("frontpage_intent") or "normal",
            "followup_needs": [],
            "reason": vision.get("reason") or "Ingen relevant Hero",
            "media_search_terms": draft.get("hero_search_terms") or [draft.get("title")],
        }

    best = int(vision["best"])
    chosen = images[best]
    model = p.CONFIG["models"]["chief_high_risk"] if high_risk else p.CONFIG["models"]["chief_normal"]
    instructions = """Du er Chefredaktør på Morgentidende og har reel publiceringsmyndighed. Vurder samlet faktuel støtte og attribution, relevant pluralisme/modpart, naturligt professionelt dansk, rubrik/manchet og passende forside-rolle. En separat billedredaktør har allerede set Hero-pixlerne og godkendt den ene medsendte kandidat; du skal stadig kontrollere licens/metadata og sammenhæng. REPAIR-FIRST: reelle reparerbare problemer giver revise/research_more, ikke drop. DROP er kun til en historie der reelt ikke holder, er dublet, ikke kan dokumenteres eller er blevet irrelevant. Returnér KUN JSON: {"decision":"publish"|"revise"|"research_more"|"media_retry"|"drop","issues":["konkret..."],"hero_choice":0,"frontpage_role":"lead"|"top_story"|"important_followup"|"normal"|"magazine"|"section_only","followup_needs":["authority_response"|"counterparty_response"|"new_development"],"reason":"kort","media_search_terms":["..."]}."""
    payload = {
        "commission": desk,
        "article": draft,
        "evidence": [
            {k: v for k, v in e.items() if k != "text"} | {"text_excerpt": str(e.get("text") or e.get("feed_description") or "")[:5000]}
            for e in evidence
        ],
        "image_candidate": {k: v for k, v in chosen.items() if k != "original_url"},
        "vision_review": vision,
        "frontpage_state": {
            "active_lead": state.get("active_lead"),
            "top_stories": state.get("top_stories"),
            "coverage_last_24h": state.get("coverage_last_24h"),
            "active_packages": state.get("active_packages"),
        },
    }
    data, _ = p.call_json(
        "chief_editor_high_risk" if high_risk else "chief_editor",
        model,
        instructions,
        payload,
        story_id=story_id,
        max_output_tokens=650,
        reasoning="medium" if high_risk else "low",
    )
    if data.get("decision") not in {"publish", "revise", "research_more", "media_retry", "drop"}:
        raise RuntimeError("Chief returned invalid decision")
    if data.get("decision") == "publish":
        data["hero_choice"] = best
    return data


def install_safety_hooks():
    p.call_ai = safe_call_ai
    p.research_web = no_external_research
    p.chief_review = safe_chief_review


def daily_status():
    return private_backend("daily_budget", budget_date=budget_date())


def run_pipeline(cycles: int) -> int:
    install_safety_hooks()
    cycles = max(1, min(int(p.CONFIG["limits"].get("max_cycles_per_run", 3)), int(cycles)))
    report = {
        "schema_version": 2,
        "run_id": p.RUN_ID,
        "started_at": p.now_iso(),
        "cycles_requested": cycles,
        "safety": {
            "hard_daily_limit_dkk": HARD_LIMIT,
            "operational_daily_limit_dkk": OPERATIONAL_LIMIT,
            "max_ai_calls_per_run": MAX_RUN_CALLS,
            "max_ai_calls_per_story": MAX_STORY_CALLS,
            "request_timeout_seconds": REQUEST_TIMEOUT,
        },
        "results": [],
        "stages": [],
        "budget_before": daily_status(),
    }
    for i in range(1, cycles + 1):
        try:
            result = p.cycle(i, report)
        except BudgetLimitExceeded as e:
            result = {"status": "budget_stop", "reason": str(e)[:500]}
            report["results"].append({"cycle": i, **result})
            break
        except SafetyLimitExceeded as e:
            result = {"status": "safety_stop", "reason": str(e)[:500]}
            report["results"].append({"cycle": i, **result})
            break
        except Exception as e:
            # Unexpected infrastructure/model errors stop the run. Do not repeat
            # the same failing path in later cycles and accidentally burn tokens.
            result = {"status": "error_stop", "reason": str(e)[:500]}
            report["results"].append({"cycle": i, **result})
            break
        report["results"].append({"cycle": i, **result})
    report["finished_at"] = p.now_iso()
    report["ai_calls"] = RUN_CALLS
    report["budget_after"] = daily_status()
    out = p.REPORT_ROOT / p.RUN_ID / "summary.json"
    p.dump_json(out, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def smoke() -> int:
    install_safety_hooks()
    model = p.CONFIG["models"]["desk"]
    text, _ = safe_call_ai(
        "integration_smoke",
        model,
        "Svar kun OK.",
        "ping",
        max_output_tokens=64,
        reasoning="low",
    )
    if "OK" not in text.upper():
        raise RuntimeError(f"Unexpected smoke response: {text[:120]}")
    print(json.dumps({"ok": True, "model": model, "budget": daily_status()}, ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=1)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    return smoke() if args.smoke else run_pipeline(args.cycles)


if __name__ == "__main__":
    raise SystemExit(main())
