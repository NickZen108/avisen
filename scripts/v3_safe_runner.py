#!/usr/bin/env python3
"""Machine-safety wrapper for Morgentidende Pipeline v3.

Editorial decisions stay in v3_pipeline. This wrapper only enforces the daily
budget, call ceilings, timeouts and fail-closed accounting for text/vision,
BGE-M3 embeddings and FLUX.1 Schnell generation.
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
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


class BudgetLimitExceeded(RuntimeError):
    pass


class SafetyLimitExceeded(RuntimeError):
    pass


def budget_date():
    return datetime.now(CPH).date().isoformat()


def private_backend(action, **kwargs):
    if not p.BACKEND_URL or not p.OIDC_TOKEN:
        raise SafetyLimitExceeded("Private budget backend unavailable; AI calls fail closed")
    r = requests.post(
        p.BACKEND_URL,
        headers={"authorization": f"Bearer {p.OIDC_TOKEN}", "content-type": "application/json"},
        json={"action": action, **kwargs},
        timeout=20,
    )
    try:
        data = r.json()
    except Exception:
        data = {}
    if r.status_code == 429:
        return {"ok": False, "status": 429, **data}
    if not r.ok:
        raise SafetyLimitExceeded(f"Private backend {action} failed HTTP {r.status_code}: {str(data)[:250]}")
    return data


def _call_slot(stage, story_id):
    global RUN_CALLS
    if RUN_CALLS >= MAX_RUN_CALLS:
        raise SafetyLimitExceeded(f"Run call ceiling reached ({MAX_RUN_CALLS})")
    key = story_id or "__run__"
    if STORY_CALLS[key] >= MAX_STORY_CALLS:
        raise SafetyLimitExceeded(f"Story call ceiling reached ({MAX_STORY_CALLS}) for {key}")
    RUN_CALLS += 1
    STORY_CALLS[key] += 1
    return RUN_CALLS


def _reserve(stage, amount_dkk, story_id):
    n = _call_slot(stage, story_id)
    reservation_id = f"{p.RUN_ID}:{n}:{stage}:{uuid.uuid4().hex[:10]}"
    result = private_backend(
        "budget_reserve",
        reservation_id=reservation_id,
        budget_date=budget_date(),
        amount_dkk=round(max(0.001, float(amount_dkk)), 6),
        run_id=p.RUN_ID,
        stage=stage,
    )
    if not result.get("ok"):
        raise BudgetLimitExceeded(f"Daily AI budget stop before {stage}: {result.get('budget') or result}")
    return reservation_id


def _settle(reservation_id, actual_dkk=0.0, *, unknown_charge=False):
    private_backend("budget_settle", reservation_id=reservation_id,
                    actual_dkk=max(0.0, float(actual_dkk or 0.0)),
                    charge_reservation=bool(unknown_charge))


def reserve_text_upper(model, instructions, prompt, max_output_tokens, images):
    prices = p.CONFIG.get("model_prices_usd_per_million_tokens", {}).get(model)
    if not prices:
        raise SafetyLimitExceeded(f"No price configured for model {model}")
    text_upper = len((str(instructions) + "\n" + str(prompt)).encode("utf-8"))
    input_upper = text_upper + 8000 * len(images or [])
    usd = (input_upper * float(prices.get("input", 0)) + int(max_output_tokens) * float(prices.get("output", 0))) / 1_000_000
    return max(0.01, usd * FX * 1.50)


def safe_call_ai(stage, model, instructions, prompt, *, story_id=None, inbox_id=None,
                 max_output_tokens=800, images=None, web_search=False, reasoning="low"):
    images = list(images or [])[:5]
    if web_search and not str(model).startswith("openai/"):
        raise SafetyLimitExceeded("Native Workers AI cannot be treated as web search")
    reserved_dkk = reserve_text_upper(model, instructions, prompt, int(max_output_tokens), images)
    reservation_id = _reserve(stage, reserved_dkk, story_id)
    payload = {"stage": stage, "model": model, "instructions": instructions, "input": prompt,
               "max_output_tokens": int(max_output_tokens), "images": images,
               "web_search": bool(web_search), "reasoning": reasoning}
    started = time.time()
    request_id = None
    try:
        r = requests.post(p.WORKER_URL + "/run",
                          headers={"authorization": f"Bearer {p.WORKER_TOKEN}", "content-type": "application/json"},
                          json=payload, timeout=REQUEST_TIMEOUT)
        request_id = r.headers.get("cf-ray")
        try:
            data = r.json()
        except Exception:
            data = {"ok": False, "error": r.text[:500]}
        if not r.ok or not data.get("ok"):
            raise RuntimeError(f"AI {stage} HTTP {r.status_code}: {data}")
        text = data.get("text") or ""
        if not text.strip():
            raise RuntimeError(f"AI {stage} returned empty text")
        usage = data.get("usage") or {}
        inp, out, cached, usd, actual_dkk = p.estimate_cost(model, usage)
        elapsed = int((time.time() - started) * 1000)
        p.backend("log_ai", row={
            "run_id": p.RUN_ID, "story_id": story_id, "inbox_id": inbox_id, "stage": stage,
            "provider": "workers-ai-native" if str(model).startswith("@cf/") else "cloudflare-ai-gateway",
            "model": model, "request_id": request_id, "attempt": 1, "status": "success",
            "input_tokens": inp, "output_tokens": out, "cached_input_tokens": cached,
            "estimated_cost_usd": round(usd, 8), "estimated_cost_dkk": round(actual_dkk, 6),
            "latency_ms": elapsed, "prompt_text": prompt, "response_text": text,
            "metadata": {"reasoning": reasoning, "web_search": web_search, "image_count": len(images),
                         "budget_reserved_dkk": round(reserved_dkk, 6)},
            "expires_at": (datetime.now(timezone.utc) + p.timedelta(days=90)).isoformat(timespec="seconds"),
        })
        _settle(reservation_id, actual_dkk)
        return text, {"input_tokens": inp, "output_tokens": out, "cached_input_tokens": cached,
                      "usd": usd, "dkk": actual_dkk, "latency_ms": elapsed}
    except Exception as e:
        try:
            _settle(reservation_id, 0, unknown_charge=True)
        finally:
            p.backend("log_ai", row={
                "run_id": p.RUN_ID, "story_id": story_id, "stage": stage,
                "provider": "workers-ai-native" if str(model).startswith("@cf/") else "cloudflare-ai-gateway",
                "model": model, "request_id": request_id, "attempt": 1, "status": "error",
                "input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0,
                "estimated_cost_usd": 0, "estimated_cost_dkk": round(reserved_dkk, 6),
                "latency_ms": int((time.time() - started) * 1000), "prompt_text": prompt,
                "error_message": str(e), "metadata": {"charged_full_reservation": True},
                "expires_at": (datetime.now(timezone.utc) + p.timedelta(days=90)).isoformat(timespec="seconds"),
            })
        raise


def safe_embed_texts(texts, story_id=None):
    texts = [str(x)[:1500] for x in (texts or [])][:128]
    if not texts:
        return []
    model = p.CONFIG["models"]["scan_embedding"]
    price = p.CONFIG["model_prices_usd_per_million_tokens"][model]
    upper_tokens = sum(len(x.encode("utf-8")) for x in texts)
    reserve_dkk = max(0.001, upper_tokens * float(price["input"]) / 1_000_000 * FX * 1.5)
    reservation_id = _reserve("scan_embedding", reserve_dkk, story_id)
    started = time.time()
    try:
        r = requests.post(p.WORKER_URL + "/embed",
                          headers={"authorization": f"Bearer {p.WORKER_TOKEN}", "content-type": "application/json"},
                          json={"model": model, "texts": texts}, timeout=REQUEST_TIMEOUT)
        data = r.json()
        if not r.ok or not data.get("ok"):
            raise RuntimeError(f"Embedding HTTP {r.status_code}: {data}")
        usage = data.get("usage") or {}
        inp = int(usage.get("input_tokens") or usage.get("prompt_tokens") or upper_tokens)
        usd = inp * float(price["input"]) / 1_000_000
        dkk = usd * FX
        _settle(reservation_id, dkk)
        p.backend("log_ai", row={
            "run_id": p.RUN_ID, "story_id": story_id, "stage": "scan_embedding", "provider": "workers-ai-native",
            "model": model, "status": "success", "input_tokens": inp, "output_tokens": 0,
            "cached_input_tokens": 0, "estimated_cost_usd": round(usd, 8), "estimated_cost_dkk": round(dkk, 6),
            "latency_ms": int((time.time() - started) * 1000),
            "metadata": {"texts": len(texts), "cluster_threshold": p.BGE_THRESHOLD},
        })
        return data.get("data") or []
    except Exception:
        _settle(reservation_id, 0, unknown_charge=True)
        raise


def _schnell_actual_dkk(steps=4):
    price = p.CONFIG["image_generation_prices_usd"][p.CONFIG["models"]["media_generator"]]
    usd = 4 * float(price.get("per_512_tile", 0)) + int(steps) * float(price.get("per_step", 0))
    return usd * FX


def safe_generate_image(prompt, story_id):
    model = p.CONFIG["models"]["media_generator"]
    steps = int(p.CONFIG.get("media", {}).get("flux_steps", 4))
    expected = _schnell_actual_dkk(steps)
    reservation_id = _reserve("media_generate", max(0.01, expected * 1.5), story_id)
    started = time.time()
    try:
        r = requests.post(p.WORKER_URL + "/image",
                          headers={"authorization": f"Bearer {p.WORKER_TOKEN}", "content-type": "application/json"},
                          json={"model": model, "prompt": str(prompt)[:2048], "steps": steps}, timeout=max(REQUEST_TIMEOUT, 150))
        data = r.json()
        if not r.ok or not data.get("ok") or not data.get("image"):
            raise RuntimeError(f"Image generation HTTP {r.status_code}: {data}")
        _settle(reservation_id, expected)
        p.backend("log_ai", row={
            "run_id": p.RUN_ID, "story_id": story_id, "stage": "media_generate", "provider": "workers-ai-native",
            "model": model, "status": "success", "input_tokens": 0, "output_tokens": 0,
            "cached_input_tokens": 0, "estimated_cost_usd": round(expected / FX, 8),
            "estimated_cost_dkk": round(expected, 6), "latency_ms": int((time.time() - started) * 1000),
            "metadata": {"steps": steps, "generator_only": "flux-1-schnell"},
        })
        return data
    except Exception:
        _settle(reservation_id, 0, unknown_charge=True)
        raise


def install_safety_hooks():
    p.call_ai = safe_call_ai
    p.embed_texts = safe_embed_texts
    p.generate_image = safe_generate_image


def daily_status():
    return private_backend("daily_budget", budget_date=budget_date())


def run_pipeline(cycles):
    install_safety_hooks()
    cycles = max(1, min(int(p.CONFIG["limits"].get("max_cycles_per_run", 3)), int(cycles)))
    report = {
        "schema_version": 3, "run_id": p.RUN_ID, "started_at": p.now_iso(), "cycles_requested": cycles,
        "safety": {"hard_daily_limit_dkk": HARD_LIMIT, "operational_daily_limit_dkk": OPERATIONAL_LIMIT,
                   "max_ai_calls_per_run": MAX_RUN_CALLS, "max_ai_calls_per_story": MAX_STORY_CALLS,
                   "request_timeout_seconds": REQUEST_TIMEOUT},
        "results": [], "stages": [], "budget_before": daily_status(),
    }
    for i in range(1, cycles + 1):
        try:
            result = p.cycle(i, report)
        except BudgetLimitExceeded as e:
            report["results"].append({"cycle": i, "status": "budget_stop", "reason": str(e)[:500]})
            break
        except SafetyLimitExceeded as e:
            report["results"].append({"cycle": i, "status": "safety_stop", "reason": str(e)[:500]})
            break
        except Exception as e:
            report["results"].append({"cycle": i, "status": "error_stop", "reason": str(e)[:500]})
            break
        report["results"].append({"cycle": i, **result})
    report["finished_at"] = p.now_iso()
    report["ai_calls"] = RUN_CALLS
    report["budget_after"] = daily_status()
    p.dump_json(p.REPORT_ROOT / p.RUN_ID / "summary.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def smoke():
    install_safety_hooks()
    model = p.CONFIG["models"]["journalist"]
    text, _ = safe_call_ai("integration_smoke", model, "Svar med ét dansk ord.", "Skriv ordet: klar",
                           max_output_tokens=64, reasoning="low")
    if not text.strip():
        raise RuntimeError("Empty Terra smoke response")
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
