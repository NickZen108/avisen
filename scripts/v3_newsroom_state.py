#!/usr/bin/env python3
"""Build compact Newsroom State + Forside v2 from published source-of-truth articles.

The public front page never has its own stale article list. The same build also
creates a compact Chief Snapshot so Terra can judge placement and next editorial
need without re-reading whole articles or the whole rendered front page.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "content" / "articles"
STATE_PATH = ROOT / "state" / "newsroom-v3.json"
FRONTPAGE_PATH = ROOT / "content" / "frontpage-v2.json"
FRONTPAGE_COMPAT = ROOT / "content" / "frontpage.json"

MAGAZINE = {"Feature", "Historie", "Guide", "Videnskab", "Sundhed", "Parforhold", "Liv", "Kultur & medier"}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_dt(value):
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def age_minutes(article, now):
    dt = parse_dt(article.get("published_at"))
    if dt == datetime.min.replace(tzinfo=timezone.utc):
        return None
    return max(0, int((now - dt).total_seconds() // 60))


def item(article, now=None):
    row = {
        "slug": article["slug"],
        "story_id": article.get("story_id") or article["slug"],
        "package_id": article.get("package_id"),
        "category": article.get("category") or "Nyhed",
        "article_type": article.get("article_type") or "news",
        "title": article.get("title") or "",
        "standfirst": article.get("standfirst") or "",
        "published_at": article.get("published_at"),
        "weight": article.get("weight") or "C",
        "frontpage_role": article.get("frontpage_role") or "normal",
        "topics": article.get("topics") or [],
        "followup_needs": article.get("followup_needs") or [],
        "next_scan_requests": article.get("next_scan_requests") or [],
    }
    if now:
        row["age_minutes"] = age_minutes(article, now)
    return row


def published_articles():
    rows = []
    for path in ART_DIR.glob("*.json"):
        if path.name.startswith("_"):
            continue
        try:
            article = load_json(path)
        except Exception:
            continue
        if article.get("status") != "published" or not article.get("slug") or not article.get("published_at"):
            continue
        rows.append(article)
    rows.sort(key=lambda a: parse_dt(a.get("published_at")), reverse=True)
    return rows


def choose_lead(rows):
    if not rows:
        return None
    explicit = [a for a in rows if a.get("frontpage_role") == "lead"]
    if explicit:
        return explicit[0]
    strong = [a for a in rows if str(a.get("weight") or "").upper() == "A"]
    return (strong or rows)[0]


def dedupe_scan_requests(rows, limit=8):
    out, seen = [], set()
    for a in rows[:20]:
        for req in (a.get("next_scan_requests") or []):
            if isinstance(req, str):
                query, purpose = req, ""
            elif isinstance(req, dict):
                query, purpose = req.get("query"), req.get("purpose")
            else:
                continue
            query = str(query or "").strip()
            if not query or query.casefold() in seen:
                continue
            seen.add(query.casefold())
            out.append({
                "type": "chief_next_need",
                "query": query[:500],
                "need": query[:500],
                "purpose": str(purpose or "")[:500],
                "from_story_id": a.get("story_id"),
                "from_package_id": a.get("package_id"),
            })
            if len(out) >= limit:
                return out
    return out


def build():
    now = datetime.now(timezone.utc)
    rows = published_articles()
    lead = choose_lead(rows)

    top = []
    preferred = [a for a in rows if a is not lead and a.get("frontpage_role") in {"top_story", "important_followup"}]
    for a in preferred + rows:
        if a is lead or a in top or a.get("frontpage_role") == "section_only":
            continue
        top.append(a)
        if len(top) >= 7:
            break

    magazine = [a for a in rows if (a.get("frontpage_role") == "magazine" or a.get("category") in MAGAZINE) and a is not lead][:6]
    normal_stream = [a for a in rows if a is not lead and a not in magazine and a.get("frontpage_role") != "section_only"][:24]

    cutoff24 = now - timedelta(hours=24)
    recent24 = [a for a in rows if parse_dt(a.get("published_at")) >= cutoff24]
    coverage = Counter(a.get("category") or "Nyhed" for a in recent24)
    topic_counter = Counter()
    for a in recent24:
        for topic in (a.get("topics") or [])[:5]:
            t = str(topic).strip()
            if t:
                topic_counter[t] += 1

    packages = defaultdict(lambda: {"articles": [], "followup_needs": set(), "latest_at": None, "latest_title": ""})
    for a in rows[:80]:
        pid = a.get("package_id")
        if not pid:
            continue
        p = packages[pid]
        p["articles"].append(a["slug"])
        p["followup_needs"].update(str(x) for x in (a.get("followup_needs") or []) if x)
        if not p["latest_at"] or parse_dt(a.get("published_at")) > parse_dt(p["latest_at"]):
            p["latest_at"] = a.get("published_at")
            p["latest_title"] = a.get("title") or ""
    package_rows = []
    for pid, p in packages.items():
        package_rows.append({
            "package_id": pid,
            "articles": p["articles"][:8],
            "followup_needs": sorted(p["followup_needs"]),
            "latest_at": p["latest_at"],
            "latest_title": p["latest_title"],
        })
    package_rows.sort(key=lambda x: parse_dt(x["latest_at"]), reverse=True)

    scan_focus = dedupe_scan_requests(rows, limit=8)
    if coverage.get("Indland", 0) == 0:
        scan_focus.append({"type": "coverage_nudge", "query": "vigtig dansk nyhed i dag", "need": "vigtig dansk nyhed i dag",
                           "purpose": "Forsiden har ingen Indland-historie de seneste 24 timer; vælg kun hvis nyhedsværdien er god."})
    if coverage.get("Udland", 0) == 0:
        scan_focus.append({"type": "coverage_nudge", "query": "vigtig international nyhed i dag", "need": "vigtig international nyhed i dag",
                           "purpose": "Forsiden har ingen Udland-historie de seneste 24 timer; vælg kun hvis nyhedsværdien er god."})

    visible = ([lead] if lead else []) + top[:5]
    chief_snapshot = {
        "generated_at": now.isoformat(timespec="seconds"),
        "lead_age_minutes": age_minutes(lead, now) if lead else None,
        "visible_slots": [
            {
                "slot": "lead" if a is lead else (a.get("frontpage_role") or "normal"),
                "category": a.get("category") or "Nyhed",
                "article_type": a.get("article_type") or "news",
                "title": a.get("title") or "",
                "age_minutes": age_minutes(a, now),
                "story_id": a.get("story_id"),
                "package_id": a.get("package_id"),
                "topics": (a.get("topics") or [])[:4],
                "followup_needs": (a.get("followup_needs") or [])[:4],
            }
            for a in visible
        ],
        "coverage_last_24h": dict(coverage),
        "top_topics_last_24h": [{"topic": t, "count": n} for t, n in topic_counter.most_common(10)],
        "open_packages": [
            {"package_id": p["package_id"], "latest_title": p["latest_title"],
             "followup_needs": p["followup_needs"][:5], "article_count": len(p["articles"])}
            for p in package_rows[:10]
        ],
        "pending_scan_needs": scan_focus[:10],
    }

    state = {
        "schema_version": 2,
        "generated_at": now.isoformat(timespec="seconds"),
        "pipeline": "v3",
        "published_count": len(rows),
        "active_lead": item(lead, now) if lead else None,
        "top_stories": [item(a, now) for a in top[:5]],
        "coverage_last_24h": dict(coverage),
        "active_packages": package_rows[:12],
        "scan_brief": scan_focus[:10],
        "chief_snapshot": chief_snapshot,
        "recent_articles": [item(a, now) for a in rows[:30]],
        "note": "State is derived from published articles. Code compresses frontpage state; Chief retains editorial judgment.",
    }

    def fp_item(a):
        if not a:
            return None
        im = a.get("image") or {}
        return {
            "slug": a["slug"],
            "category": a.get("category") or "Nyhed",
            "title": a.get("title") or "",
            "standfirst": a.get("standfirst") or "",
            "teaser": a.get("standfirst") or "",
            "published_label": a.get("published_at") or "",
            "image_src": im.get("src") or "",
            "image_alt": im.get("alt") or "",
            "image_caption": im.get("caption") or "",
            "image_credit": im.get("credit") or "",
            "frontpage_role": a.get("frontpage_role") or "normal",
        }

    rail = [fp_item(a) for a in top[:5]]
    stack_articles = magazine[:3]
    if len(stack_articles) < 3:
        for a in normal_stream:
            if a not in stack_articles and a not in top[:5]:
                stack_articles.append(a)
            if len(stack_articles) >= 3:
                break
    narrow, seen = [], ({lead["slug"]} if lead else set())
    for a in top + normal_stream + magazine:
        if a["slug"] in seen:
            continue
        seen.add(a["slug"])
        narrow.append(fp_item(a))
        if len(narrow) >= 16:
            break

    frontpage = {
        "schema_version": 2,
        "generated_at": now.isoformat(timespec="seconds"),
        "date": now.date().isoformat(),
        "edition_label": "Danmarks nye avis",
        "source_of_truth": "published_articles",
        "lead": fp_item(lead),
        "ticker": fp_item(lead),
        "rail": rail,
        "stack": [fp_item(a) for a in stack_articles],
        "narrow": narrow,
        "roles": {
            "lead": lead["slug"] if lead else None,
            "top_story": [a["slug"] for a in top if a.get("frontpage_role") == "top_story"][:4],
            "important_followup": [a["slug"] for a in top if a.get("frontpage_role") == "important_followup"][:4],
            "magazine": [a["slug"] for a in magazine],
        },
        "publication_strategy": {
            "version": 6,
            "chief_editor_owns_high_placement": True,
            "automatic_backfill": True,
            "published_only": True,
            "category_quotas": False,
            "compact_chief_snapshot": True,
        },
    }

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rendered = json.dumps(frontpage, ensure_ascii=False, indent=2) + "\n"
    FRONTPAGE_PATH.write_text(rendered, encoding="utf-8")
    FRONTPAGE_COMPAT.write_text(rendered, encoding="utf-8")
    print(f"Newsroom v3 state: {len(rows)} published; lead={lead.get('slug') if lead else 'none'}")
    return state, frontpage


if __name__ == "__main__":
    build()
