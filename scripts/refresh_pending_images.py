#!/usr/bin/env python3
"""Deterministic pre-build lawful-media scout for pending news heroes.

Only published article records with image.pending_image=true are touched before
the public HTML build. The scout queries Wikimedia Commons for a lawful free
visual, preferring direct documentary material, then contextual photos, maps and
satellite imagery, and delegates approval to the targeted media re-approval flow.
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
    # Split compounds such as "Flood-relief" and "Nepal-Tibet" so Commons can
    # match event files whose English titles use the individual terms.
    value = str(value or "").replace("-", " ").replace("/", " ")
    return [x for x in re.findall(r"[A-Za-zÆØÅæøå0-9]{3,}", value) if x.lower() not in stop]


def queries(article: dict) -> list[str]:
    title = str(article.get("title") or "")
    standfirst = str(article.get("standfirst") or "")
    category = str(article.get("category") or "")
    all_text = f"{title} {standfirst}"
    title_words = words(title)
    stand_words = words(standfirst)
    proper = [x for x in words(all_text) if x[:1].isupper()]
    low = all_text.lower()
    hazard = None
    for needles, english in (
        (("flod", "oversvømm", "flood"), "flood"),
        (("brand", "fire"), "fire"),
        (("jordskælv", "earthquake"), "earthquake"),
        (("orkan", "storm", "hurricane"), "storm"),
        (("dron", "drone"), "drone"),
        (("krig", "war"), "war"),
    ):
        if any(n in low for n in needles):
            hazard = english
            break
    year = str(article.get("published_at") or "")[:4]
    context = proper[:3] + ([hazard] if hazard else [])
    raw = [
        " ".join(title_words[:7]),
        " ".join(context),
        " ".join(([year] if year.isdigit() else []) + context),
        " ".join(proper[:2] + ([hazard] if hazard else [])),
        " ".join(stand_words[:5]),
        " ".join((title_words[:3] + words(category)[:2])),
    ]
    return list(dict.fromkeys(x for x in raw if len(x.strip()) >= 3))[:6]


def commons_photo(article: dict) -> dict | None:
    # Keep the story year available for result ranking as well as query building.
    year = str(article.get("published_at") or "")[:4]
    for q in queries(article):
        params = urllib.parse.urlencode({
            "action": "query", "format": "json", "generator": "search",
            "gsrnamespace": 6, "gsrsearch": q, "gsrlimit": 8,
            "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 1600,
        })
        req = urllib.request.Request(COMMONS_API + "?" + params, headers={"User-Agent": "MorgentidendePendingMedia/2.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            continue
        query_terms = set(x.lower().rstrip("s") for x in words(q))
        ranked = []
        for page in (payload.get("query", {}).get("pages", {}) or {}).values():
            info = ((page.get("imageinfo") or [{}])[0])
            meta = info.get("extmetadata") or {}
            license_name = clean((meta.get("LicenseShortName") or {}).get("value") or (meta.get("UsageTerms") or {}).get("value") or "")
            if info.get("mime") not in {"image/jpeg", "image/png", "image/webp", "image/svg+xml"} or not ALLOWED_LICENSE.search(license_name):
                continue
            if int(info.get("width") or 0) < 800 or int(info.get("height") or 0) < 450:
                continue
            desc = clean((meta.get("ImageDescription") or {}).get("value") or "")
            title = str(page.get("title") or "").removeprefix("File:")
            bag = set(x.lower().rstrip("s") for x in words(title + " " + desc))
            overlap = len(query_terms & bag)
            min_overlap = 1 if len(query_terms) <= 1 else 2
            if overlap < min_overlap:
                continue
            artist = clean((meta.get("Artist") or {}).get("value") or (meta.get("Credit") or {}).get("value") or "Wikimedia Commons")
            visual_text = f"{title} {desc}".lower()
            is_map = " map" in f" {visual_text}" or "kort" in visual_text
            is_satellite = any(x in visual_text for x in ("satellite", "landsat", "sentinel", "earth observ"))
            graphic = is_map or is_satellite or info.get("mime") == "image/svg+xml"
            context_type = "map" if is_map else "satellite" if is_satellite else "archive"
            caption = (
                "Kort over sagen eller det berørte område."
                if is_map else
                "Satellitbillede relateret til hændelsen eller det berørte område."
                if is_satellite else
                "Arkivfoto – billedet viser ikke nødvendigvis selve hændelsen."
            )
            # Prefer exact/current event documentation, then contextual visuals.
            event_bonus = 3 if year.isdigit() and year in visual_text else 0
            ranked.append((overlap + event_bonus, {
                "src": info.get("thumburl") or info.get("url"),
                "alt": desc or title,
                "credit": artist or "Wikimedia Commons",
                "license": license_name,
                "source_url": info.get("descriptionurl") or f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(str(page.get('title') or ''))}",
                "image_type": "graphic" if graphic else "photo",
                "context_type": context_type,
                "caption": caption,
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
    article = {"title": "Brand ved rådhuset i København", "standfirst": "Brandvæsenet rykkede ud", "category": "Indland", "published_at": "2026-09-02T10:00:00Z"}
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
    assert "2026" in " ".join(queries(article))
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
