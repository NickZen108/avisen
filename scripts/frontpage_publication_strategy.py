#!/usr/bin/env python3
"""Apply Morgentidende's non-gating publication strategy to frontpage state.

This script only ranks and places already-published articles. It deliberately does
not validate publication eligibility and must never become a release/quality gate.
Malformed or incomplete article metadata is skipped with a warning rather than
blocking a build.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = ROOT / "content" / "articles"
FRONTPAGE = ROOT / "content" / "frontpage.json"

# First iteration: preserve the chosen editorial lead while guaranteeing fresh
# A/B main-destination stories a frontpage slot. Related follow-ups are promoted
# as packages so an important perspective is visible in the upper frontpage.
B_MAIN_WINDOW = timedelta(hours=48)
RAIL_LIMIT = 8
NARROW_LIMIT = 12


def warn(message: str) -> None:
    print(f"frontpage strategy: warning: {message}")


def parse_time(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def load_articles() -> dict[str, dict]:
    articles: dict[str, dict] = {}
    for path in sorted(ARTICLES_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            article = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # placement must not block publication
            warn(f"skipping {path.name}: {exc}")
            continue
        if str(article.get("status") or "").lower() != "published":
            continue
        slug = str(article.get("slug") or path.stem).strip()
        if not slug:
            continue
        article["_slug"] = slug
        article["_published"] = parse_time(article.get("published_at"))
        articles[slug] = article
    return articles


def slug_of(raw: object) -> str:
    return str(raw.get("slug") or "").strip() if isinstance(raw, dict) else ""


def item(slug: str) -> dict[str, str]:
    return {"slug": slug}


def dedupe(items: list[object]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for raw in items:
        slug = slug_of(raw)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        out.append(raw if isinstance(raw, dict) else item(slug))
    return out


def published_rank(article: dict) -> float:
    dt = article.get("_published")
    return dt.timestamp() if isinstance(dt, datetime) else 0.0


def main() -> int:
    try:
        state = json.loads(FRONTPAGE.read_text(encoding="utf-8"))
    except Exception as exc:
        warn(f"frontpage state could not be read; leaving it unchanged: {exc}")
        return 0

    articles = load_articles()
    if not articles:
        warn("no published article metadata found; leaving frontpage unchanged")
        return 0

    dated = [a["_published"] for a in articles.values() if a.get("_published")]
    newest = max(dated) if dated else datetime.now(timezone.utc)
    cutoff = newest - B_MAIN_WINDOW

    old_rail = dedupe(list(state.get("rail") or []))
    old_narrow = dedupe(list(state.get("narrow") or []))
    lead_slug = slug_of(state.get("lead") or {})

    # A is a hero/top-three candidate. We do not mechanically replace a valid
    # editorial lead. B + editorial_destination=main is automatically included.
    candidates: list[dict] = []
    for article in articles.values():
        weight = str(article.get("weight") or "").upper()
        destination = str(article.get("editorial_destination") or "").lower()
        published = article.get("_published")
        if destination != "main" or weight not in {"A", "B"}:
            continue
        if published and published < cutoff:
            continue
        candidates.append(article)

    a_candidates = sorted(
        [a for a in candidates if str(a.get("weight") or "").upper() == "A" and a["_slug"] != lead_slug],
        key=published_rank,
        reverse=True,
    )
    followups = sorted(
        [a for a in candidates if str(a.get("related_news_slug") or "").strip() and a["_slug"] != lead_slug],
        key=published_rank,
        reverse=True,
    )
    followup_slugs = {a["_slug"] for a in followups}
    ordinary_b = sorted(
        [
            a for a in candidates
            if str(a.get("weight") or "").upper() == "B"
            and a["_slug"] != lead_slug
            and a["_slug"] not in followup_slugs
        ],
        key=published_rank,
        reverse=True,
    )

    # Build a priority prefix instead of repeatedly inserting at position zero.
    # This keeps the ordering deterministic and ensures a related parent/follow-up
    # package stays together near the top rather than drifting down as other B
    # stories are processed.
    priority: list[dict] = []
    if lead_slug and any(slug_of(x) == lead_slug for x in old_rail):
        priority.append(item(lead_slug))

    for article in a_candidates:
        priority.append(item(article["_slug"]))

    # Group follow-ups by parent: parent immediately followed by all fresh
    # qualifying perspectives/responses. A missing/unpublished parent is not
    # invented; the follow-up itself still gets a high placement.
    seen_parents: set[str] = set()
    for article in followups:
        parent = str(article.get("related_news_slug") or "").strip()
        if parent and parent not in seen_parents and parent in articles and parent != lead_slug:
            priority.append(item(parent))
            seen_parents.add(parent)
        priority.append(item(article["_slug"]))

    for article in ordinary_b:
        priority.append(item(article["_slug"]))

    rail = dedupe(priority + old_rail)[:RAIL_LIMIT]
    narrow = dedupe(priority + old_narrow)[:NARROW_LIMIT]

    state["rail"] = rail
    state["narrow"] = narrow
    state["publication_strategy"] = {
        "version": 2,
        "mode": "placement_only_non_gating",
        "recalculated_from_published_articles": True,
        "related_followups_promoted_as_packages": True,
    }

    FRONTPAGE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "frontpage strategy: applied; "
        f"A/B main candidates considered={len(candidates)}, related_followups={len(followups)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
