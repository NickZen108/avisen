#!/usr/bin/env python3
"""Normalize legacy Newsdesk categories to the current public taxonomy.

The Cloudflare desk may still emit legacy Danmark/Politik while deployments roll
through. Only those legacy values are touched. Subject-specific sections win
before the Indland/Udland fallback, so a Danish sports story becomes Sport rather
than Indland and a foreign health story becomes Sundhed rather than Udland.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content" / "articles"
APPROVALS = ROOT / "reports" / "editorial" / "approvals"

DOMESTIC = (
    "danmark", "dansk", "folketing", "folketinget", "christiansborg",
    "den danske regering", "statsministeriet", "statsministeren",
    "kommunal", "kommune", "region hovedstaden", "region sjælland",
    "region syddanmark", "region midtjylland", "region nordjylland",
    "grønland", "færø", "forbrugerombudsmand", "sikkerhedsstyrelsen",
    "fødevarestyrelsen", "rigspolitiet", "ft.dk", "stm.dk",
)

SUBJECT_RULES = (
    ("Sport", ("sport", "fodbold", "håndbold", "tennis", "atletik", "diamond league", "ol ", "vm ", "champions league", "superliga", "landshold", "warholm")),
    ("Sundhed", ("sundhed", "sygdom", "læge", "patient", "hospital", "medicin", "hormon", "menopause", "overgangsalder", "testosteron", "søvn", "depression", "angst")),
    ("Parforhold", ("parforhold", "ægteskab", "skilsmisse", "dating", "kæreste", "partner", "utroskab")),
    ("Videnskab & teknologi", ("videnskab", "forskning", "teknologi", "kunstig intelligens", " ai ", "robot", "chip", "rumfart", "rumteleskop", "nasa")),
    ("Kultur & medier", ("kultur", "film", "musik", "bog", "forfatter", "kunst", "tv ", "medier", "skuespiller")),
    ("Krimi", ("drab", "mord", "sigtet", "tiltalt", "anholdt", "politi", "kriminalitet", "vold", "røveri")),
    ("Økonomi", ("økonomi", "rente", "inflation", "centralbank", "arbejdsløshed", "bnp", "aktier", "finans")),
    ("Forbruger", ("forbruger", "butik", "pris", "produkt", "tilbagekald", "supermarked", "detailhandel")),
)


def dump(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def article_text(article: dict) -> str:
    body = article.get("body") or []
    body_text = " ".join(
        str(block.get("text") or "") if isinstance(block, dict) else str(block)
        for block in body
    ) if isinstance(body, list) else str(body)
    text = " ".join(str(article.get(k) or "") for k in ("title", "standfirst", "summary")) + " " + body_text
    sources = article.get("sources") or []
    if isinstance(sources, list):
        text += " " + " ".join(str(x.get("url") or x.get("source_url") or "") for x in sources if isinstance(x, dict))
    return f" {text.lower()} "


def classify_legacy(article: dict) -> str:
    text = article_text(article)
    for category, tokens in SUBJECT_RULES:
        if any(token in text for token in tokens):
            return category
    return "Indland" if any(token in text for token in DOMESTIC) else "Udland"


def target_category(article: dict) -> str | None:
    old = str(article.get("category") or "").strip()
    if old in {"Danmark", "Politik"}:
        return classify_legacy(article)
    return None


def migrate_approval(slug: str, old: str, new: str) -> bool:
    path = APPROVALS / f"{slug}.json"
    if not path.exists():
        return False
    try:
        approval = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    snapshot = approval.get("editorial_snapshot")
    if not isinstance(snapshot, dict) or str(snapshot.get("category") or "") != old:
        return False
    snapshot["category"] = new
    approval["category_migration"] = {
        "mode": "deterministic-taxonomy-migration",
        "from": old,
        "to": new,
        "migrated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "changed_fields": ["category"],
        "reason": "Legacy Newsdesk category mapped to current subject-first public taxonomy",
    }
    dump(path, approval)
    return True


def main() -> int:
    changed = 0
    approvals_changed = 0
    for path in sorted(ARTICLES.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            article = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        old = str(article.get("category") or "").strip()
        new = target_category(article)
        if not new or new == old:
            continue
        article["category"] = new
        dump(path, article)
        changed += 1
        slug = str(article.get("slug") or path.stem)
        if migrate_approval(slug, old, new):
            approvals_changed += 1
    print(f"category normalization: changed={changed}; approvals_changed={approvals_changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
