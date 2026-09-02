#!/usr/bin/env python3
"""Normalize legacy main categories to the current Indland/Udland model.

This is a semantic category migration only: Danmark -> Indland and Politik ->
Indland/Udland by primary arena. When an immutable Pipeline V2 approval exists,
its editorial snapshot is migrated in lockstep and the migration is recorded so
later image-only reapproval can still prove that no unrelated editorial fields
changed.
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


def dump(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def classify_legacy_politics(article: dict) -> str:
    text = " ".join(str(article.get(k) or "") for k in ("title", "standfirst", "body", "summary")).lower()
    sources = article.get("sources") or []
    if isinstance(sources, list):
        text += " " + " ".join(str(x.get("url") or x.get("source_url") or "") for x in sources if isinstance(x, dict)).lower()
    return "Indland" if any(token in text for token in DOMESTIC) else "Udland"


def target_category(article: dict) -> str | None:
    old = str(article.get("category") or "").strip()
    if old == "Danmark":
        return "Indland"
    if old == "Politik":
        return classify_legacy_politics(article)
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
        "reason": "Politik removed as main category; Danmark renamed to Indland",
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
