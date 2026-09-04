#!/usr/bin/env python3
"""Create a deterministic editorial follow-up plan from the current frontpage lead.

The frontpage owns the lead decision. This planner translates a lead change into
search needs for Scan/Newsdesk without becoming a publication gate.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTPAGE = ROOT / "content" / "frontpage.json"
ARTICLES = ROOT / "content" / "articles"
OUT = ROOT / "reports" / "editorial" / "followup-plan.json"

SPECIAL_INTEREST_TERMS = {
    "nationalkonservativ", "nationalkonservative", "vox", "reform uk", "farage",
    "migration", "migrant", "indvandring", "asyl", "grænse", "graense",
    "ytringsfrihed", "censur", "eu-regulering", "dsa", "libertær", "libertaer",
    "skat", "skatter", "statens", "offentlige udgifter", "regulering", "frihed",
}


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def lead_article() -> dict | None:
    front = load(FRONTPAGE, {}) or {}
    slug = str(((front.get("lead") or {}).get("slug") or "")).strip()
    if not slug:
        return None
    return load(ARTICLES / f"{slug}.json")


def text_of(article: dict) -> str:
    parts = [str(article.get("title") or ""), str(article.get("standfirst") or "")]
    for block in article.get("body") or []:
        if isinstance(block, dict):
            parts.append(str(block.get("text") or ""))
    return " ".join(parts).lower()


def build_plan(article: dict | None) -> dict:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if not article:
        return {
            "schema_version": 1,
            "generated_at": now,
            "active": False,
            "lead_slug": None,
            "requests": [],
            "commentary": {"consider": False, "reason": "ingen aktiv lead"},
            "mode": "advisory_non_gating",
        }
    text = text_of(article)
    matched = sorted(term for term in SPECIAL_INTEREST_TERMS if term in text)
    requests = [
        {"type": "new_development", "priority": "high", "instruction": "Søg efter nye verificerbare oplysninger om lead-sagen."},
        {"type": "authority_response", "priority": "high", "instruction": "Søg efter myndigheders eller ansvarlige institutioners svar."},
        {"type": "counterparty_response", "priority": "high", "instruction": "Søg efter modpartens eller den kritiserede parts svar."},
        {"type": "background", "priority": "medium", "instruction": "Søg efter dokumentation og baggrund, der forklarer konsekvenser og kontekst."},
    ]
    commentary = bool(matched)
    if commentary:
        requests.append({
            "type": "commentary_material",
            "priority": "medium",
            "instruction": "Søg efter materiale til en mulig Kommentar/Perspektiv. Kommentar bestilles kun hvis der findes en selvstændig tese og tilstrækkeligt verificeret materiale.",
        })
    return {
        "schema_version": 1,
        "generated_at": now,
        "active": True,
        "lead_slug": article.get("slug"),
        "story_id": article.get("story_id"),
        "title": article.get("title"),
        "weight": article.get("weight"),
        "requests": requests,
        "commentary": {
            "consider": commentary,
            "special_interest_matches": matched,
            "rule": "overvej kommentar; aldrig automatisk publiceringskrav",
        },
        "mode": "advisory_non_gating",
    }


def main() -> int:
    plan = build_plan(lead_article())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"active": plan["active"], "lead_slug": plan.get("lead_slug"), "commentary": plan["commentary"]["consider"], "requests": len(plan["requests"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
