#!/usr/bin/env python3
"""Apply Morgentidende's non-gating publication strategy to frontpage state.

This script only ranks and places already-published articles. It deliberately does
not validate publication eligibility and must never become a release/quality gate.
Malformed or incomplete article metadata is skipped rather than blocking a build.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = ROOT / "content" / "articles"
FRONTPAGE = ROOT / "content" / "frontpage.json"
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
        except Exception as exc:
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
        out.append(item(slug))
    return out


def published_rank(article: dict) -> float:
    dt = article.get("_published")
    return dt.timestamp() if isinstance(dt, datetime) else 0.0


def is_magazine(article: dict) -> bool:
    destination = str(article.get("editorial_destination") or "").lower()
    return destination.endswith("_magazine") or destination == "magazine"


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

    newest_articles = sorted(articles.values(), key=published_rank, reverse=True)
    newest = newest_articles[0]
    newest_time = newest.get("_published") or datetime.now(timezone.utc)
    cutoff = newest_time - B_MAIN_WINDOW

    current_lead = slug_of(state.get("lead") or {})
    lead_slug = current_lead if current_lead in articles else ""

    candidates: list[dict] = []
    magazine_candidates: list[dict] = []
    for article in articles.values():
        weight = str(article.get("weight") or "").upper()
        destination = str(article.get("editorial_destination") or "").lower()
        published = article.get("_published")
        if published and published < cutoff:
            continue
        if destination == "main" and weight in {"A", "B"}:
            candidates.append(article)
        if is_magazine(article):
            magazine_candidates.append(article)

    # Preserve the former release behaviour in one place: a fresh standalone A/B
    # main story becomes lead; magazine placement never promotes an article to lead.
    if (
        str(newest.get("weight") or "").upper() in {"A", "B"}
        and str(newest.get("editorial_destination") or "").lower() == "main"
        and not str(newest.get("related_news_slug") or "").strip()
    ):
        lead_slug = newest["_slug"]

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
        [a for a in candidates if str(a.get("weight") or "").upper() == "B" and a["_slug"] != lead_slug and a["_slug"] not in followup_slugs],
        key=published_rank,
        reverse=True,
    )
    magazine_visible = sorted(
        [a for a in magazine_candidates if a["_slug"] != lead_slug],
        key=published_rank,
        reverse=True,
    )

    priority: list[dict] = []
    for article in a_candidates:
        priority.append(item(article["_slug"]))
    seen_parents: set[str] = set()
    for article in followups:
        parent = str(article.get("related_news_slug") or "").strip()
        if parent and parent not in seen_parents and parent in articles and parent != lead_slug:
            priority.append(item(parent))
            seen_parents.add(parent)
        priority.append(item(article["_slug"]))
    # Magazine articles also belong on the ordinary frontpage. Keep them below
    # breaking A/follow-up packages but ahead of the ordinary B backlog.
    for article in magazine_visible:
        priority.append(item(article["_slug"]))
    for article in ordinary_b:
        priority.append(item(article["_slug"]))

    chronological = [item(a["_slug"]) for a in newest_articles if a["_slug"] != lead_slug]
    state["ticker"] = item(newest["_slug"])
    if lead_slug:
        state["lead"] = item(lead_slug)
    state["date"] = newest["_slug"][:10]
    state["rail"] = dedupe(priority + chronological)[:RAIL_LIMIT]
    state["narrow"] = dedupe(priority + chronological)[:NARROW_LIMIT]
    state["publication_strategy"] = {
        "version": 4,
        "mode": "placement_only_non_gating",
        "sole_placement_owner": True,
        "related_followups_promoted_as_packages": True,
        "magazine_articles_also_on_main_frontpage": True,
    }

    FRONTPAGE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "frontpage strategy: applied; "
        f"published={len(articles)}, main priority candidates={len(candidates)}, "
        f"magazine candidates={len(magazine_candidates)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
