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

# Keep the first iteration conservative: preserve the existing editorial lead and
# layout, while guaranteeing fresh A/B main-destination stories a frontpage slot.
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


def slug_of(item: object) -> str:
    return str(item.get("slug") or "").strip() if isinstance(item, dict) else ""


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


def place_after(items: list[dict], slug: str, parent: str | None) -> list[dict]:
    items = [x for x in items if slug_of(x) != slug]
    if parent:
        for index, existing in enumerate(items):
            if slug_of(existing) == parent:
                items.insert(index + 1, item(slug))
                return items
    items.insert(0, item(slug))
    return items


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

    rail = dedupe(list(state.get("rail") or []))
    narrow = dedupe(list(state.get("narrow") or []))
    lead_slug = slug_of(state.get("lead") or {})

    # A is a hero/top-three candidate. We do not mechanically replace a valid
    # editorial lead, but fresh A/main stories are guaranteed a high slot.
    # B + editorial_destination=main is automatically included on the frontpage.
    candidates = []
    for article in articles.values():
        weight = str(article.get("weight") or "").upper()
        destination = str(article.get("editorial_destination") or "").lower()
        published = article.get("_published")
        if destination != "main" or weight not in {"A", "B"}:
            continue
        if published and published < cutoff:
            continue
        candidates.append(article)

    candidates.sort(
        key=lambda a: (0 if str(a.get("weight") or "").upper() == "A" else 1,
                       -(a.get("_published") or datetime.min.replace(tzinfo=timezone.utc)).timestamp())
    )

    for article in candidates:
        slug = article["_slug"]
        if slug == lead_slug:
            continue
        parent = str(article.get("related_news_slug") or "").strip() or None

        # A meaningful related follow-up should sit beside its main story when
        # possible. If its published parent is missing, add the parent first.
        if parent and parent in articles:
            if not any(slug_of(x) == parent for x in rail) and parent != lead_slug:
                rail.insert(0, item(parent))
            if not any(slug_of(x) == parent for x in narrow) and parent != lead_slug:
                narrow.insert(0, item(parent))

        rail = place_after(rail, slug, parent)
        narrow = place_after(narrow, slug, parent)

    # Lead stays visible only once in the supporting lists where legacy layout
    # expects it. De-duplication otherwise prevents repeated cards.
    rail = dedupe(rail)[:RAIL_LIMIT]
    narrow = dedupe(narrow)[:NARROW_LIMIT]

    state["rail"] = rail
    state["narrow"] = narrow
    state["publication_strategy"] = {
        "version": 1,
        "mode": "placement_only_non_gating",
        "recalculated_from_published_articles": True,
    }

    FRONTPAGE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    included = [a["_slug"] for a in candidates]
    print(f"frontpage strategy: applied; A/B main candidates considered={len(included)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
