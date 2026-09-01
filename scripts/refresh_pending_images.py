#!/usr/bin/env python3
"""Deterministic post-publication photo scout for pending news heroes.

Only published articles with image.pending_image=true are touched. The scout
queries Wikimedia Commons for a lawful contextual photo, changes image metadata
only, and delegates approval to the existing targeted media re-approval flow.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from reapprove_media_change import reapprove, validate_image, validate_replacement_transition

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content" / "articles"
FRONTPAGE = ROOT / "content" / "frontpage.json"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
ALLOWED_LICENSE = re.compile(r"\b(cc0|cc by|cc-by|cc by-sa|cc-by-sa|public domain|pd-)\b", re.I)
TAG_RE = re.compile(r"<[^>]+>")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", str(value or "")))).strip()


def words(value: str) -> list[str]:
    stop = {"efter", "over", "under", "siger", "mener", "skal", "ville", "bliver", "med", "fra", "til", "for", "the", "and", "with", "from"}
    return [x for x in re.findall(r"[A-Za-zÆØÅæøå0-9-]{4,}", value or "") if x.lower() not in stop]


def queries(article: dict) -> list[str]:
    title = str(article.get("title") or "")
    standfirst = str(article.get("standfirst") or "")
    category = str(article.get("category") or "")
    raw = [
        " ".join(words(title)[:7]),
        " ".join(words(title)[:4]),
        " ".join(words(standfirst)[:5]),
        " ".join((words(title)[:3] + words(category)[:2])),
    ]
    return list(dict.fromkeys(x for x in raw if x))[:4]


def commons_photo(article: dict) -> dict | None:
    for q in queries(article):
        params = urllib.parse.urlencode({
            "action": "query", "format": "json", "generator": "search",
            "gsrnamespace": 6, "gsrsearch": q, "gsrlimit": 8,
            "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata",
        })
        req = urllib.request.Request(COMMONS_API + "?" + params, headers={"User-Agent": "MorgentidendePendingMedia/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            continue
        query_terms = set(x.lower() for x in words(q))
        ranked = []
        for page in (payload.get("query", {}).get("pages", {}) or {}).values():
            info = ((page.get("imageinfo") or [{}])[0])
            meta = info.get("extmetadata") or {}
            license_name = clean((meta.get("LicenseShortName") or {}).get("value") or (meta.get("UsageTerms") or {}).get("value") or "")
            if info.get("mime") != "image/jpeg" or not ALLOWED_LICENSE.search(license_name):
                continue
            if int(info.get("width") or 0) < 800 or int(info.get("height") or 0) < 450:
                continue
            desc = clean((meta.get("ImageDescription") or {}).get("value") or "")
            title = str(page.get("title") or "").removeprefix("File:")
            bag = set(x.lower() for x in words(title + " " + desc))
            overlap = len(query_terms & bag)
            if overlap < 1:
                continue
            artist = clean((meta.get("Artist") or {}).get("value") or (meta.get("Credit") or {}).get("value") or "Wikimedia Commons")
            ranked.append((overlap, {
                "src": info.get("thumburl") or info.get("url"),
                "alt": desc or title,
                "credit": artist or "Wikimedia Commons",
                "license": license_name,
                "source_url": info.get("descriptionurl") or f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(str(page.get('title') or ''))}",
                "image_type": "photo",
                "context_type": "archive",
                "caption": "Arkivfoto – billedet viser ikke nødvendigvis selve hændelsen.",
                "pending_image": False,
                "ai_generated": False,
                "placement": "lead",
            }))
        if ranked:
            ranked.sort(key=lambda x: x[0], reverse=True)
            return ranked[0][1]
    return None


def update_frontpage(slug: str, image: dict) -> bool:
    if not FRONTPAGE.exists():
        return False
    state = load(FRONTPAGE)
    changed = False
    for key in ("lead", "ticker"):
        item = state.get(key)
        if isinstance(item, dict) and item.get("slug") == slug:
            if "image_src" in item:
                item["image_src"] = image["src"]; item["image_alt"] = image["alt"]; changed = True
    for key in ("rail", "stack", "narrow"):
        for item in state.get(key, []) or []:
            if isinstance(item, dict) and item.get("slug") == slug and "image_src" in item:
                item["image_src"] = image["src"]; item["image_alt"] = image["alt"]; changed = True
    if changed:
        dump(FRONTPAGE, state)
    return changed


def process(limit: int = 5) -> int:
    changed = 0
    for path in sorted(ARTICLES.glob("*.json")):
        if changed >= limit:
            break
        article = load(path)
        old = article.get("image") or {}
        if article.get("status") != "published" or old.get("pending_image") is not True:
            continue
        replacement = commons_photo(article)
        if not replacement:
            continue
        validate_image(replacement)
        validate_replacement_transition(old, replacement)
        article["image"] = replacement
        dump(path, article)
        reapprove(str(article["slug"]))
        update_frontpage(str(article["slug"]), replacement)
        changed += 1
        print(f"pending-image replaced: {article['slug']} -> {replacement['source_url']}")
    print(f"pending-image scout: replaced={changed}")
    return changed


def self_test() -> None:
    article = {"title": "Brand ved rådhuset i København", "standfirst": "Brandvæsenet rykkede ud", "category": "Danmark"}
    assert queries(article)
    old = {
        "pending_image": True, "ai_generated": True, "image_type": "illustration",
        "context_type": "illustration", "caption": "Illustration",
    }
    new = {
        "src": "https://example.test/a.jpg", "alt": "Stedet", "credit": "X", "license": "CC BY 4.0",
        "source_url": "https://example.test/source", "image_type": "photo", "context_type": "archive",
        "caption": "Arkivfoto", "pending_image": False, "ai_generated": False, "placement": "lead",
    }
    validate_image(new)
    validate_replacement_transition(old, new)
    print("pending_image_refresh self-test: PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test(); return 0
    process(max(1, min(args.limit, 20)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
