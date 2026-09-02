#!/usr/bin/env python3
"""Deterministic lead follow-up state for the existing Newsdesk pipeline.

When frontpage lead changes, an active follow-up window starts (minimum 6 hours).
Related candidates are boosted. Small developments update the lead article;
only a self-contained new development becomes a separate follow-up article.
A larger new A-story can still take the lead.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "reports" / "editorial" / "lead-followup.json"
FRONTPAGE = ROOT / "content" / "frontpage.json"
ARTICLES = ROOT / "content" / "articles"
MIN_WINDOW = timedelta(hours=6)
RELATED_THRESHOLD = 0.34

DEVELOPMENT_MARKERS = (
    "udtal", "officiel", "pressemeddelelse",
    "øjenvidne", "ojenvidne", "eyewitness",
    "dokument", "rapport",
    "dødstal", "doedstal",
    "video", "optagelse", "billedmateriale",
    "reaktion", "konsekvens", "følgevirkning", "folgevirkning",
    "korrektion", "dementi", "modstrid",
    "arrest", "anhold", "sigtet", "tiltalt", "mistænkt", "mistaenkt",
    "tilbagehold",
)

STOP = {
    "den", "det", "der", "som", "og", "i", "på", "pa", "til", "af", "en", "et",
    "er", "har", "blev", "med", "fra", "om", "for", "de", "du", "at", "ikke",
    "the", "and", "for", "from", "with", "that", "this", "was", "were", "have",
}


def parse_time(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def now_utc(now=None):
    if now is None:
        return datetime.now(timezone.utc)
    if isinstance(now, str):
        parsed = parse_time(now)
        return parsed or datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def tokens(value: str) -> set[str]:
    words = re.findall(r"[a-z0-9æøåäöüéèáà]{3,}", str(value or "").lower())
    return {w for w in words if w not in STOP}


def lexical_similarity(a: str, b: str) -> float:
    left, right = tokens(a), tokens(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def article_text(article: dict) -> str:
    parts = [article.get("title") or "", article.get("standfirst") or ""]
    for block in article.get("body") or []:
        if isinstance(block, dict):
            parts.append(block.get("text") or "")
        else:
            parts.append(str(block))
    return " ".join(parts)


def signal_text(signal: dict) -> str:
    return " ".join([
        str(signal.get("headline") or signal.get("title") or ""),
        str(signal.get("description") or signal.get("standfirst") or ""),
        str(signal.get("normalized") or ""),
    ])


def load_article(slug: str | None) -> dict | None:
    if not slug:
        return None
    return load_json(ARTICLES / f"{slug}.json")


def frontpage_lead_slug() -> str | None:
    state = load_json(FRONTPAGE, {}) or {}
    slug = ((state.get("lead") or {}).get("slug") or "").strip()
    return slug or None


def related_to_lead(text: str, lead: dict | None, threshold: float = RELATED_THRESHOLD) -> bool:
    if not lead:
        return False
    lead_blob = article_text(lead)
    if lexical_similarity(text, lead_blob) >= threshold:
        return True
    title_tokens = {t for t in tokens(lead.get("title") or "") if len(t) >= 4}
    found = tokens(text)
    if title_tokens and sum(1 for t in title_tokens if any(t in f or f in t for f in found)) >= max(1, min(2, len(title_tokens))):
        return True
    distinctive = {t for t in tokens(f"{lead.get('title') or ''} {lead.get('standfirst') or ''}") if len(t) >= 5}
    return len(distinctive) >= 2 and len(distinctive & found) >= max(2, min(3, len(distinctive) // 2))


def has_substantial_development(new_text: str, lead_text: str) -> bool:
    hay = (new_text or "").lower()
    if not any(marker in hay for marker in DEVELOPMENT_MARKERS):
        return False
    novel = tokens(new_text) - tokens(lead_text)
    return len(novel) >= 8


def classify_candidate(candidate: dict, lead: dict | None) -> dict:
    text = signal_text(candidate) if "headline" in candidate or "normalized" in candidate else article_text(candidate)
    if not lead:
        return {"related": False, "action": "independent", "reason": "ingen aktiv lead"}
    if not related_to_lead(text, lead):
        weight = str(candidate.get("weight") or "")
        action = "independent_a" if weight == "A" else "independent"
        return {"related": False, "action": action, "reason": "ikke samme historie"}
    if has_substantial_development(text, article_text(lead)):
        return {"related": True, "action": "new_followup", "reason": "selvstændig udvikling"}
    return {"related": True, "action": "update_lead", "reason": "mindre opdatering til lead"}


def empty_state() -> dict:
    return {
        "schema_version": 1,
        "active": False,
        "lead_slug": None,
        "story_id": None,
        "activated_at": None,
        "window_ends_at": None,
        "last_significant_at": None,
        "title": None,
        "standfirst": None,
    }


def window_end(state: dict):
    ends = parse_time(state.get("window_ends_at"))
    last = parse_time(state.get("last_significant_at"))
    activated = parse_time(state.get("activated_at"))
    if last and activated:
        extended = last + MIN_WINDOW
        if ends:
            return max(ends, extended)
        return extended
    return ends


def is_active(state: dict | None, now=None) -> bool:
    if not state or not state.get("active") or not state.get("lead_slug"):
        return False
    current = now_utc(now)
    ends = window_end(state)
    return bool(ends and ends > current)


def activate_from_article(article: dict, now=None) -> dict:
    current = now_utc(now)
    ends = current + MIN_WINDOW
    return {
        "schema_version": 1,
        "active": True,
        "lead_slug": article.get("slug"),
        "story_id": article.get("story_id"),
        "activated_at": iso(current),
        "window_ends_at": iso(ends),
        "last_significant_at": iso(current),
        "title": article.get("title"),
        "standfirst": article.get("standfirst"),
    }


def mark_significant(state: dict, now=None) -> dict:
    current = now_utc(now)
    state = dict(state or empty_state())
    state["last_significant_at"] = iso(current)
    ends = window_end(state) or (current + MIN_WINDOW)
    if ends < current + MIN_WINDOW:
        ends = current + MIN_WINDOW
    state["window_ends_at"] = iso(ends)
    state["active"] = True
    return state


def deactivate(state: dict) -> dict:
    state = dict(state or empty_state())
    state["active"] = False
    return state


def load_state() -> dict:
    return load_json(STATE_PATH, empty_state()) or empty_state()


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sync_from_frontpage(now=None) -> dict:
    current = now_utc(now)
    state = load_state()
    slug = frontpage_lead_slug()
    article = load_article(slug)
    if not slug or not article:
        state = deactivate(state)
        save_state(state)
        return state
    if state.get("lead_slug") != slug:
        state = activate_from_article(article, current)
        save_state(state)
        return state
    if not is_active(state, current):
        state["active"] = False
        save_state(state)
        return state
    state["title"] = article.get("title") or state.get("title")
    state["standfirst"] = article.get("standfirst") or state.get("standfirst")
    state["story_id"] = article.get("story_id") or state.get("story_id")
    save_state(state)
    return state


def worker_context(now=None):
    state = sync_from_frontpage(now)
    if not is_active(state, now):
        return None
    lead = load_article(state.get("lead_slug")) or {}
    return {
        "active": True,
        "lead_slug": state.get("lead_slug"),
        "story_id": state.get("story_id"),
        "activated_at": state.get("activated_at"),
        "window_ends_at": iso(window_end(state)) if window_end(state) else state.get("window_ends_at"),
        "title": state.get("title") or lead.get("title"),
        "standfirst": state.get("standfirst") or lead.get("standfirst"),
        "lead_text": article_text(lead)[:4000] if lead else "",
    }


def should_replace_lead(new_article: dict, now=None) -> bool:
    state = load_state()
    if not is_active(state, now):
        return str(new_article.get("weight") or "") in {"A", "B"} and not new_article.get("related_news_slug")
    if new_article.get("related_news_slug") == state.get("lead_slug"):
        return False
    if new_article.get("slug") == state.get("lead_slug"):
        return False
    lead = load_article(state.get("lead_slug"))
    verdict = classify_candidate(new_article, lead)
    if verdict["related"]:
        return False
    return str(new_article.get("weight") or "") == "A"


def boost_score(base: float, candidate: dict, now=None) -> float:
    state = load_state()
    if not is_active(state, now):
        return base
    lead = {
        "title": state.get("title") or "",
        "standfirst": state.get("standfirst") or "",
        "body": [],
    }
    article = load_article(state.get("lead_slug"))
    if article:
        lead = article
    verdict = classify_candidate(candidate, lead)
    if verdict["action"] == "new_followup":
        return base + 14
    if verdict["related"]:
        return base + 8
    return base


def self_test() -> None:
    lead = {
        "slug": "lead-slug",
        "story_id": "lead-story",
        "weight": "B",
        "title": "Færge kæntrer ud for Nordcypern",
        "standfirst": "Mindst otte mennesker er omkommet efter en færge kæntrede.",
        "body": [{"type": "p", "text": "Redningsarbejde er i gang ud for Nordcypern."}],
    }
    small = {
        "headline": "Færgeulykke ved Nordcypern: redningsarbejde fortsætter",
        "description": "Myndigheder siger at søgningen fortsætter natten over.",
        "weight": "C",
    }
    big = {
        "headline": "Kaptajn og syv fra besætningen tilbageholdt efter færgeulykke ved Nordcypern",
        "description": "Politiet har officielt tilbageholdt kaptajnen. Nye dokumenter og øjenvidneberetninger beskriver brag før færgen kæntrede.",
        "weight": "B",
    }
    other_a = {
        "title": "Jordskælv rammer Tokyo og standser metroen",
        "standfirst": "Et kraftigt jordskælv har ramt Tokyo. Myndighederne advarer om efterskælv.",
        "weight": "A",
        "body": [{"type": "p", "text": "Officielle tal følger."}],
    }
    other_b = {
        "title": "Lokal fodboldklub vinder træningskamp",
        "standfirst": "Resultatet faldt sent onsdag.",
        "weight": "B",
    }
    assert classify_candidate(small, lead)["action"] == "update_lead"
    assert classify_candidate(big, lead)["action"] == "new_followup"
    assert classify_candidate(other_a, lead)["action"] == "independent_a"
    stamp = "2026-09-02T06:00:00Z"
    state = activate_from_article(lead, stamp)
    assert is_active(state, "2026-09-02T11:00:00Z")
    assert not is_active(state, "2026-09-02T13:00:00Z")
    extended = mark_significant(state, "2026-09-02T11:30:00Z")
    assert is_active(extended, "2026-09-02T16:00:00Z")
    assert related_to_lead(signal_text(big), lead)
    assert not related_to_lead(article_text(other_b), lead)
    print("lead_followup self-test: PASS")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--sync", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
    elif args.sync:
        state = sync_from_frontpage()
        print(json.dumps({"active": is_active(state), "lead_slug": state.get("lead_slug"), "window_ends_at": state.get("window_ends_at")}, ensure_ascii=False))
    else:
        self_test()
