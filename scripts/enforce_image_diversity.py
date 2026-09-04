#!/usr/bin/env python3
"""Non-gating image-diversity pass for recent published articles.

Policy: the same concrete documentary photo should not be reused within a rolling
window of 20 published articles. The newest conflicting article is given a chance
to receive another lawful Wikimedia Commons image. Publication is never blocked
solely because no suitable alternative can be found.

Identity is based primarily on source_url (Commons file page), falling back to src.
Different cache/thumb URLs of the same Commons file therefore count as one photo.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

import refresh_pending_images as media
from reapprove_media_change import reapprove, validate_image

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content" / "articles"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WINDOW = 20


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def image_identity(image: dict) -> str:
    source = str(image.get("source_url") or "").strip()
    if source:
        try:
            u = urllib.parse.urlparse(source)
            if "commons.wikimedia.org" in u.netloc:
                path = urllib.parse.unquote(u.path)
                m = re.search(r"/wiki/(?:File:|Special:FilePath/)(.+)$", path, re.I)
                if m:
                    return "commons:" + m.group(1).replace("_", " ").casefold()
        except Exception:
            pass
        return "source:" + source.split("#", 1)[0].split("?", 1)[0].casefold()
    src = str(image.get("src") or "").strip()
    return "src:" + src.split("#", 1)[0].split("?", 1)[0].casefold() if src else ""


def published_articles() -> list[tuple[Path, dict]]:
    rows = []
    for path in ARTICLES.glob("*.json"):
        if path.name.startswith("_"):
            continue
        try:
            article = load(path)
        except Exception:
            continue
        if article.get("status") != "published" or not article.get("published_at"):
            continue
        rows.append((path, article))
    rows.sort(key=lambda row: row[1].get("published_at") or "")
    return rows


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(media.TAG_RE.sub(" ", str(value or "")))).strip()


def alternative_from_commons(article: dict, forbidden: set[str]) -> dict | None:
    year = str(article.get("published_at") or "")[:4]
    loc = article.get("story_location") or {}
    person_queries = {q.casefold() for q in media.named_entity_queries(article)}
    location_terms: set[str] = set()
    if isinstance(loc, dict):
        for key in ("place_names_local", "place_names_english", "transliterations"):
            for value in loc.get(key) or []:
                location_terms.update(x.casefold() for x in media.words(value))
        location_terms.update(x.casefold() for x in media.words(str(loc.get("country") or "")))

    ranked: list[tuple[float, dict]] = []
    for q_index, q in enumerate(media.queries(article)):
        params = urllib.parse.urlencode({
            "action": "query", "format": "json", "generator": "search",
            "gsrnamespace": 6, "gsrsearch": q, "gsrlimit": 15,
            "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 1600,
        })
        req = urllib.request.Request(COMMONS_API + "?" + params, headers={"User-Agent": "MorgentidendeImageDiversity/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            continue
        query_terms = {x.casefold() for x in media.words(q)}
        for page in (payload.get("query", {}).get("pages", {}) or {}).values():
            info = ((page.get("imageinfo") or [{}])[0])
            meta = info.get("extmetadata") or {}
            license_name = clean((meta.get("LicenseShortName") or {}).get("value") or (meta.get("UsageTerms") or {}).get("value") or "")
            mime = str(info.get("mime") or "").lower()
            if mime not in media.ALLOWED_VISUAL_MIME or not media.ALLOWED_LICENSE.search(license_name):
                continue
            if int(info.get("width") or 0) < 800 or int(info.get("height") or 0) < 450:
                continue
            src = info.get("thumburl") or info.get("url")
            if not src:
                continue
            desc = clean((meta.get("ImageDescription") or {}).get("value") or "")
            title = str(page.get("title") or "").removeprefix("File:")
            source_url = info.get("descriptionurl") or f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(str(page.get('title') or ''))}"
            candidate_id = image_identity({"source_url": source_url, "src": src})
            if candidate_id in forbidden:
                continue
            bag = {x.casefold() for x in media.words(title + " " + desc)}
            overlap = len(query_terms & bag)
            min_overlap = 1 if len(query_terms) <= 1 else 2
            if query_terms and overlap < min_overlap:
                continue
            visual_text = f"{title} {desc}".casefold()
            is_map = " map" in f" {visual_text}" or "kort" in visual_text or "karte" in visual_text
            is_satellite = any(x in visual_text for x in ("satellite", "landsat", "sentinel", "earth observ", "satellit"))
            graphic = is_map or is_satellite or mime in {"image/svg+xml", "image/tiff"}
            event_scene = media.looks_like_specific_event_scene(visual_text)
            current_event_signal = year.isdigit() and year in visual_text
            if not graphic and event_scene and not current_event_signal:
                continue
            place_match = bool(location_terms & bag)
            person_match = q.casefold() in person_queries and overlap >= 2
            if is_map:
                context_type, caption = "map", "Kort over sagen eller det berørte område."
            elif is_satellite:
                context_type, caption = "satellite", "Satellitbillede relateret til det berørte område."
            elif current_event_signal and event_scene:
                context_type, caption = "event", "Foto relateret til den aktuelle hændelse."
            elif person_match:
                context_type, caption = "person", "Arkivfoto af en central person i sagen – billedet er ikke fra den omtalte hændelse."
            elif place_match:
                context_type, caption = "place", "Arkivfoto af det berørte sted – billedet viser ikke den omtalte hændelse."
            else:
                context_type, caption = "archive", "Kontekstfoto – billedet viser ikke den omtalte hændelse."
            artist = clean((meta.get("Artist") or {}).get("value") or (meta.get("Credit") or {}).get("value") or "Wikimedia Commons")
            score = overlap * 3 + (8 if current_event_signal and event_scene else 0) + (7 if context_type in {"person", "place"} else 0) + min(4, len(location_terms & bag) * 2) + max(0.0, 1.0 - q_index * 0.1)
            hero = {
                "src": src,
                "alt": desc or title,
                "credit": artist or "Wikimedia Commons",
                "license": license_name,
                "source_url": source_url,
                "image_type": "graphic" if graphic else "photo",
                "context_type": context_type,
                "caption": caption,
                "pending_image": False,
                "ai_generated": False,
                "placement": "lead",
            }
            ranked.append((score, hero))
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1]


def enforce(window: int = WINDOW) -> int:
    rows = published_articles()
    changed = 0
    for idx, (path, article) in enumerate(rows):
        image = article.get("image") or {}
        if image.get("image_type") not in {"photo", "video_still"}:
            continue
        current_id = image_identity(image)
        if not current_id:
            continue
        previous = rows[max(0, idx - (window - 1)):idx]
        forbidden = {
            image_identity((older.get("image") or {}))
            for _, older in previous
            if (older.get("image") or {}).get("image_type") in {"photo", "video_still"}
        }
        forbidden.discard("")
        if current_id not in forbidden:
            continue
        replacement = alternative_from_commons(article, forbidden | {current_id})
        if not replacement:
            print(f"WARNING image diversity unresolved (non-gating): {article.get('slug')} repeats a photo within {window} articles")
            continue
        validate_image(replacement)
        article["image"] = replacement
        dump(path, article)
        try:
            reapprove(str(article["slug"]))
        except SystemExit as exc:
            article["image"] = image
            dump(path, article)
            print(f"WARNING image diversity replacement reverted for {article.get('slug')}: {exc}")
            continue
        changed += 1
        print(f"image diversity: replaced {article['slug']} -> {replacement['source_url']}")
    print(f"image diversity: window={window} replaced={changed}")
    return changed


def self_test() -> None:
    a = {"source_url": "https://commons.wikimedia.org/wiki/File:Same_photo.jpg", "src": "https://upload.wikimedia.org/a.jpg"}
    b = {"source_url": "https://commons.wikimedia.org/wiki/File:Same_photo.jpg?x=1", "src": "https://upload.wikimedia.org/b.jpg"}
    assert image_identity(a) == image_identity(b)
    assert image_identity({"source_url": "https://example.test/photo.jpg?width=800"}) == "source:https://example.test/photo.jpg"
    print("image_diversity self-test: PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=WINDOW)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test(); return 0
    enforce(max(2, min(args.window, 100)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
