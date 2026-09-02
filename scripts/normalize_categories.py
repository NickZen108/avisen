#!/usr/bin/env python3
"""Normalize legacy main categories to the current Indland/Udland model.

New pipeline output may temporarily still say Danmark or Politik. This cheap,
deterministic postprocessor prevents those labels from reaching publication.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content" / "articles"

DOMESTIC = (
    "danmark", "dansk", "folketing", "christiansborg", "regering", "statsminister",
    "minister", "kommune", "region", "grønland", "faero", "færø", "ft.dk",
    "stm.dk", "politi.dk", "dr.dk", "tv2.dk",
)


def classify_legacy_politics(article: dict) -> str:
    text = " ".join(str(article.get(k) or "") for k in ("title", "standfirst", "body", "summary")).lower()
    sources = article.get("sources") or []
    if isinstance(sources, list):
        text += " " + " ".join(str(x.get("url") or x.get("source_url") or "") for x in sources if isinstance(x, dict)).lower()
    return "Indland" if any(token in text for token in DOMESTIC) else "Udland"


def normalize(article: dict) -> bool:
    old = str(article.get("category") or "").strip()
    if old == "Danmark":
        article["category"] = "Indland"
        return True
    if old == "Politik":
        article["category"] = classify_legacy_politics(article)
        return True
    return False


def main() -> int:
    changed = 0
    for path in sorted(ARTICLES.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            article = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if normalize(article):
            path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            changed += 1
    print(f"category normalization: changed={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
