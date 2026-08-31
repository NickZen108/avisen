#!/usr/bin/env python3
"""Production-readiness diagnostics for Morgentidende.

Covers story-level duplicate detection, source-lineage independence, breaking-news
update hygiene, recommendation duplication, accessibility, performance budgets,
and a machine-readable readiness report for Kontrolrummet.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content" / "articles"
DOCS = ROOT / "docs"
OUT = ROOT / "reports" / "editorial" / "production-readiness.json"

HARD = []
WARN = []
METRICS = {}


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def published_articles():
    rows = []
    for p in ARTICLES.glob("*.json"):
        if p.name.startswith("_"):
            continue
        a = load(p)
        if isinstance(a, dict) and a.get("status") == "published" and a.get("slug"):
            a["__path"] = str(p.relative_to(ROOT))
            rows.append(a)
    rows.sort(key=lambda x: x.get("published_at") or "", reverse=True)
    return rows


def norm_title(title: str) -> str:
    x = str(title or "").casefold()
    x = re.sub(r"\b(video|billeder|live|analyse|baggrund|kommentar)\b\s*:? ?", " ", x)
    x = re.sub(r"[^a-z0-9æøå ]+", " ", x)
    return " ".join(x.split())


def title_similarity(a: str, b: str) -> float:
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return 0.0
    ta, tb = set(na.split()), set(nb.split())
    jac = len(ta & tb) / max(1, len(ta | tb))
    seq = SequenceMatcher(None, na, nb).ratio()
    return max(jac, seq)


def source_lineage(a: dict):
    ledger_path = ROOT / str(a.get("ledger") or "")
    ledger = load(ledger_path, {}) if ledger_path.exists() else {}
    sources = ledger.get("sources") or []
    by_url = defaultdict(list)
    by_host = defaultdict(list)
    by_group = defaultdict(list)
    for s in sources:
        url = str(s.get("url") or "")
        if url:
            by_url[url].append(str(s.get("id") or "?"))
            by_host[urlparse(url).hostname or ""].append(str(s.get("id") or "?"))
        group = str(s.get("source_group") or "").strip()
        if group:
            by_group[group].append(str(s.get("id") or "?"))
    duplicate_urls = {u: ids for u, ids in by_url.items() if len(ids) > 1}
    coverage = ledger.get("coverage_sweep") or {}
    declared = set(str(x) for x in coverage.get("independent_source_groups") or [])
    unique_urls = len(by_url)
    unique_hosts = len([x for x in by_host if x])
    unique_groups = len(by_group)
    return {
        "unique_urls": unique_urls,
        "unique_hosts": unique_hosts,
        "unique_groups": unique_groups,
        "declared_groups": len(declared),
        "duplicate_urls": duplicate_urls,
    }


def check_duplicates(items):
    pairs = []
    for i, a in enumerate(items[:80]):
        for b in items[i + 1 : i + 31]:
            same_story = a.get("story_id") and a.get("story_id") == b.get("story_id")
            linked = a.get("related_news_slug") == b.get("slug") or b.get("related_news_slug") == a.get("slug")
            if same_story or linked:
                continue
            score = title_similarity(a.get("title"), b.get("title"))
            if score >= 0.84:
                pairs.append({"a": a["slug"], "b": b["slug"], "score": round(score, 3)})
    if pairs:
        WARN.append(f"{len(pairs)} mulige story-level dubletter bør reviewes")
    METRICS["possible_duplicate_pairs"] = pairs[:30]


def check_source_independence(items):
    weak = []
    for a in items[:100]:
        line = source_lineage(a)
        if line["duplicate_urls"] and line["unique_groups"] >= 3:
            # Same URL presented as multiple source-groups is not independent reporting.
            weak.append({"slug": a["slug"], **line})
        elif line["unique_groups"] < 2 and str(a.get("category")) not in {"Guide", "Kommentar"}:
            weak.append({"slug": a["slug"], **line})
    if weak:
        WARN.append(f"{len(weak)} publicerede artikler har svag eller tvivlsom kildeuafhængighed")
    METRICS["source_independence_flags"] = weak[:30]


def check_breaking_update_model(items):
    invalid = []
    allowed = {"update", "video", "images", "eyewitness", "background", "timeline", "commentary", None}
    slugs = {a.get("slug") for a in items}
    for a in items:
        kind = a.get("followup_type")
        rel = a.get("related_news_slug")
        if kind not in allowed:
            invalid.append({"slug": a["slug"], "reason": f"ukendt followup_type {kind}"})
        if kind and not rel:
            invalid.append({"slug": a["slug"], "reason": "followup_type uden related_news_slug"})
        if rel and rel not in slugs:
            invalid.append({"slug": a["slug"], "reason": "related_news_slug findes ikke blandt publicerede artikler"})
    if invalid:
        HARD.append(f"{len(invalid)} breaking/update-relationer er strukturelt ugyldige")
    METRICS["update_model_flags"] = invalid[:50]


def check_article_html(items):
    a11y = []
    perf = []
    for a in items[:100]:
        path = DOCS / "artikler" / f"{a['slug']}.html"
        if not path.exists():
            HARD.append(f"genereret artikel mangler: {a['slug']}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(re.findall(r"<h1\b", text, re.I)) != 1:
            a11y.append({"slug": a["slug"], "issue": "siden skal have præcis ét h1"})
        for m in re.finditer(r"<img\b[^>]*>", text, re.I):
            tag = m.group(0)
            if not re.search(r'\balt="[^"]*"', tag, re.I):
                a11y.append({"slug": a["slug"], "issue": "img uden alt-attribut"})
                break
        if '<html lang="da"' not in text.lower():
            a11y.append({"slug": a["slug"], "issue": "html lang=da mangler"})
        # Lightweight static budget: HTML should stay modest and non-hero imagery lazy.
        kb = len(text.encode("utf-8")) / 1024
        scripts = len(re.findall(r"<script\b", text, re.I))
        styles = len(re.findall(r"<link\b[^>]+rel=\"stylesheet\"", text, re.I))
        if kb > 220 or scripts > 6 or styles > 8:
            perf.append({"slug": a["slug"], "html_kb": round(kb, 1), "scripts": scripts, "stylesheets": styles})
    if a11y:
        WARN.append(f"{len(a11y)} accessibility-flags i genererede artikler")
    if perf:
        WARN.append(f"{len(perf)} sider overskrider statisk performance-budget")
    METRICS["accessibility_flags"] = a11y[:50]
    METRICS["performance_flags"] = perf[:50]


def check_recommendation_duplication(items):
    # Read the enhanced live output and ensure first/second news shelves are not exact duplicates.
    dupes = []
    for a in items[:50]:
        p = DOCS / "artikler" / f"{a['slug']}.html"
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        blocks = re.findall(r'<section class="wrap below">(.*?)</section>', text, re.S)
        if len(blocks) < 2:
            continue
        href_sets = []
        for block in blocks[:2]:
            href_sets.append(set(re.findall(r'href="([^"]+\.html)"', block)))
        overlap = sorted(href_sets[0] & href_sets[1])
        if overlap:
            dupes.append({"slug": a["slug"], "overlap": overlap})
    if dupes:
        WARN.append(f"{len(dupes)} artikelsider gentager anbefalinger på tværs af nyhedshylder")
    METRICS["recommendation_overlap"] = dupes[:30]


def write_report(items):
    status = "red" if HARD else ("yellow" if WARN else "green")
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "published_count": len(items),
        "hard_failures": HARD,
        "warnings": WARN,
        "metrics": METRICS,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PRODUCTION READINESS: {status.upper()}")
    for x in HARD:
        print("HARD:", x)
    for x in WARN:
        print("WARN:", x)
    # Hard failures block a release; warnings remain visible in Kontrolrummet.
    return 1 if HARD else 0


def main():
    items = published_articles()
    check_duplicates(items)
    check_source_independence(items)
    check_breaking_update_model(items)
    check_article_html(items)
    check_recommendation_duplication(items)
    return write_report(items)


if __name__ == "__main__":
    raise SystemExit(main())
