#!/usr/bin/env python3
"""Deterministic pre-build lawful-media scout for pending news heroes.

Only published article records with image.pending_image=true are touched before
the public HTML build. The scout queries Wikimedia Commons for a lawful free
visual, preferring direct documentary material, then neutral contextual photos
of the place/person/object, then maps and satellite imagery.

Safety rule: when an image looks like a specific event scene (for example a
protest, riot, fire or flood) but cannot be tied to the current event/year, it is
not used as a generic archive hero. A neutral place/person image is preferred so
readers are not given a false impression that an unrelated event photo depicts
the event described in the article.

When Newsdesk has supplied story_location metadata, search is location-aware and
multilingual: local-language queries, transliterations/alternate place names and
English queries are all searched, then ranked together. Older articles without
story_location retain a conservative title/standfirst fallback.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
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
ALLOWED_VISUAL_MIME = {
    "image/jpeg", "image/png", "image/webp", "image/svg+xml",
    "image/tiff", "image/gif", "image/avif",
}
EVENT_SCENE_WORDS = {
    "protest", "protests", "protester", "protesters", "demonstration", "demonstrations",
    "manifestation", "manifestations", "manifestación", "manifestaciones", "rally", "march",
    "riot", "riots", "unrest", "clash", "clashes", "strike", "streik", "strejk",
    "fire", "wildfire", "brand", "flood", "flooding", "oversvømmelse", "earthquake",
    "jordskælv", "explosion", "bombing", "attack", "angreb", "shooting", "skyderi",
    "rescue", "redning", "evacuation", "evakuering",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", str(value or "")))).strip()


def words(value: str) -> list[str]:
    """Unicode-aware tokens including combining marks used by many scripts."""
    stop = {
        "efter", "over", "under", "siger", "mener", "skal", "ville", "bliver", "med", "fra", "til", "for",
        "the", "and", "with", "from", "after", "says",
    }
    value = unicodedata.normalize("NFC", str(value or "").replace("-", " ").replace("/", " "))
    tokens: list[str] = []
    current: list[str] = []
    for ch in value:
        category = unicodedata.category(ch)
        if ch.isalnum() or category.startswith("M"):
            current.append(ch)
        else:
            if current:
                token = "".join(current).strip()
                if len(token) >= 2:
                    tokens.append(token)
                current = []
    if current:
        token = "".join(current).strip()
        if len(token) >= 2:
            tokens.append(token)
    return [x for x in tokens if x.casefold() not in stop]


def named_entity_queries(article: dict) -> list[str]:
    """Extract useful multi-word proper names, especially people, before broad story queries."""
    body = article.get("body") or []
    body_text = " ".join(
        str(block.get("text") or "")
        for block in body[:2]
        if isinstance(block, dict)
    )
    text = f"{article.get('title') or ''} {body_text}"
    pattern = re.compile(r"\b([A-ZÆØÅ][\w.'’\-]+(?:\s+[A-ZÆØÅ][\w.'’\-]+){1,3})\b", re.UNICODE)
    out: list[str] = []
    for match in pattern.finditer(text):
        q = clean(match.group(1))
        toks = words(q)
        if not (2 <= len(toks) <= 4):
            continue
        if all(token.isupper() for token in toks):
            continue
        if q not in out:
            out.append(q)
    return out[:4]


def location_queries(article: dict) -> list[str]:
    loc = article.get("story_location") or {}
    if not isinstance(loc, dict):
        return []
    buckets = (
        loc.get("hero_queries_local") or [],
        loc.get("hero_queries_transliterated") or [],
        loc.get("hero_queries_english") or [],
    )
    out: list[str] = []
    for bucket in buckets:
        if not isinstance(bucket, list):
            continue
        for value in bucket:
            q = clean(value)
            if len(q) >= 2 and q not in out:
                out.append(q)
    return out[:6]


def fallback_queries(article: dict) -> list[str]:
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
    return [x for x in raw if len(x.strip()) >= 2]


def queries(article: dict) -> list[str]:
    raw = named_entity_queries(article) + location_queries(article) + fallback_queries(article)[:2]
    return list(dict.fromkeys(x for x in raw if x))[:8]


def looks_like_specific_event_scene(value: str) -> bool:
    tokens = {x.casefold() for x in words(value)}
    return bool(tokens & EVENT_SCENE_WORDS)


def commons_photo(article: dict) -> dict | None:
    year = str(article.get("published_at") or "")[:4]
    loc = article.get("story_location") or {}
    person_queries = {q.casefold() for q in named_entity_queries(article)}
    location_terms = set()
    if isinstance(loc, dict):
        for key in ("place_names_local", "place_names_english", "transliterations"):
            for value in loc.get(key) or []:
                location_terms.update(x.casefold() for x in words(value))
        country = str(loc.get("country") or "")
        location_terms.update(x.casefold() for x in words(country))

    ranked_by_source: dict[str, tuple[float, dict]] = {}
    for q_index, q in enumerate(queries(article)):
        params = urllib.parse.urlencode({
            "action": "query", "format": "json", "generator": "search",
            "gsrnamespace": 6, "gsrsearch": q, "gsrlimit": 10,
            "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 1600,
        })
        req = urllib.request.Request(COMMONS_API + "?" + params, headers={"User-Agent": "MorgentidendePendingMedia/3.3"})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            continue

        query_terms = set(x.casefold() for x in words(q))
        for page in (payload.get("query", {}).get("pages", {}) or {}).values():
            info = ((page.get("imageinfo") or [{}])[0])
            meta = info.get("extmetadata") or {}
            license_name = clean((meta.get("LicenseShortName") or {}).get("value") or (meta.get("UsageTerms") or {}).get("value") or "")
            mime = str(info.get("mime") or "").lower()
            if mime not in ALLOWED_VISUAL_MIME or not ALLOWED_LICENSE.search(license_name):
                continue
            if int(info.get("width") or 0) < 800 or int(info.get("height") or 0) < 450:
                continue
            src = info.get("thumburl") or info.get("url")
            if not src:
                continue

            desc = clean((meta.get("ImageDescription") or {}).get("value") or "")
            title = str(page.get("title") or "").removeprefix("File:")
            bag = set(x.casefold() for x in words(title + " " + desc))
            overlap = len(query_terms & bag)
            min_overlap = 1 if len(query_terms) <= 1 else 2
            if query_terms and overlap < min_overlap:
                continue

            artist = clean((meta.get("Artist") or {}).get("value") or (meta.get("Credit") or {}).get("value") or "Wikimedia Commons")
            visual_text = f"{title} {desc}".casefold()
            is_map = " map" in f" {visual_text}" or "kort" in visual_text or "karte" in visual_text
            is_satellite = any(x in visual_text for x in ("satellite", "landsat", "sentinel", "earth observ", "satellit"))
            graphic = is_map or is_satellite or mime in {"image/svg+xml", "image/tiff"}
            event_scene = looks_like_specific_event_scene(visual_text)
            current_event_signal = year.isdigit() and year in visual_text

            # Do not use an unrelated event scene as generic archive context. This is
            # the exact class of error that made a 1932 protest look like the current
            # Ceuta demonstration. Neutral place/person imagery is safer.
            if not graphic and event_scene and not current_event_signal:
                continue

            place_match = bool(location_terms & bag)
            person_match = q.casefold() in person_queries and overlap >= 2
            if is_map:
                context_type = "map"
                caption = "Kort over sagen eller det berørte område."
            elif is_satellite:
                context_type = "satellite"
                caption = "Satellitbillede relateret til det berørte område."
            elif current_event_signal and event_scene:
                context_type = "event"
                caption = "Foto relateret til den aktuelle hændelse."
            elif person_match:
                context_type = "person"
                caption = "Arkivfoto af en central person i sagen – billedet er ikke fra den omtalte hændelse."
            elif place_match:
                context_type = "place"
                caption = "Arkivfoto af det berørte sted – billedet viser ikke den omtalte hændelse."
            else:
                context_type = "archive"
                caption = "Kontekstfoto – billedet viser ikke den omtalte hændelse."

            event_bonus = 8 if current_event_signal and event_scene else 0
            safe_context_bonus = 7 if context_type in {"person", "place"} else 0
            place_bonus = min(4, len(location_terms & bag) * 2)
            query_priority_bonus = max(0.0, 1.0 - q_index * 0.1)
            score = overlap * 3 + event_bonus + safe_context_bonus + place_bonus + query_priority_bonus
            source_url = info.get("descriptionurl") or f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(str(page.get('title') or ''))}"
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
            previous = ranked_by_source.get(source_url)
            if previous is None or score > previous[0]:
                ranked_by_source[source_url] = (score, hero)

    if not ranked_by_source:
        return None
    ranked = sorted(ranked_by_source.values(), key=lambda x: x[0], reverse=True)
    return ranked[0][1]


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
    article = {
        "title": "Oversvømmelser rammer Nepal",
        "standfirst": "Redningsarbejdet fortsætter",
        "category": "Udland",
        "published_at": "2026-09-02T10:00:00Z",
        "story_location": {
            "country": "Nepal",
            "country_code": "NP",
            "primary_language": "Nepali",
            "primary_language_code": "ne",
            "place_names_local": ["नेपाल"],
            "place_names_english": ["Nepal"],
            "transliterations": ["Nepal"],
            "hero_queries_local": ["नेपाल बाढी २०२६"],
            "hero_queries_english": ["Nepal flood 2026"],
            "hero_queries_transliterated": ["Nepal badhi 2026"],
        },
    }
    qs = queries(article)
    assert any(q.startswith("नेपाल") for q in qs)
    assert any("Nepal flood" in q for q in qs)
    assert words("नेपाल बाढी") == ["नेपाल", "बाढी"]
    assert looks_like_specific_event_scene("Demonstration in Spain 1932")
    person_article = {
        "title": "Trump foreslår ændring",
        "standfirst": "DR",
        "body": [{"type": "p", "text": "USA's præsident Donald Trump har fremsat forslaget."}],
        "story_location": {"hero_queries_english": ["Trump proposal"]},
    }
    assert queries(person_article)[0] == "Donald Trump"
    old = {
        "pending_image": True, "ai_generated": True, "image_type": "illustration",
        "context_type": "illustration", "caption": "Illustration",
    }
    new = {
        "src": "https://example.test/a.jpg", "alt": "Stedet", "credit": "X", "license": "CC BY 4.0",
        "source_url": "https://example.test/source", "image_type": "photo", "context_type": "place",
        "caption": "Arkivfoto af stedet – billedet viser ikke hændelsen.", "pending_image": False, "ai_generated": False, "placement": "lead",
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
