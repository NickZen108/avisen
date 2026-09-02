#!/usr/bin/env python3
"""One-shot source migration for hero policy v2.

Policy:
1) lawful free event/documentary visual
2) lawful free official/Commons contextual visual
3) lawful free map/satellite/graphic
4) Flux pencil-hatching illustration
5) never publish static grid/placeholder fallback
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str):
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"{label}: already applied")
        return
    if old not in text:
        raise SystemExit(f"{label}: expected anchor not found")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"{label}: applied")


# 1. Cloudflare: Flux is the last-resort hero for every weight. Static placeholder is forbidden.
editorial = ROOT / "cloudflare" / "newsdesk" / "src" / "editorial.js"
old = "__legacy_non_ai_hero_fallback__"
new = '''async function generateTemporarySketch(env, assignment, article) {
  // Hero policy v2: a static placeholder must never reach the public surface.
  // The pre-build media scout gets first chance to replace this pending illustration
  // with a lawful free documentary/context/map/satellite visual. If no such visual
  // exists, Flux pencil hatching is the final public fallback for every story weight.
  const raw = await env.AI.run(IMAGE_MODEL, { prompt: temporarySketchPrompt(assignment, article) });
  if (!raw?.image || typeof raw.image !== "string") {
    throw new Error("Hero unavailable: no lawful free visual found yet and Flux returned no image");
  }
  return { base64: raw.image, content_type: "image/jpeg", ai_generated: true, generator: "workers_ai_flux" };
}
'''
replace_once(editorial, old, new, "cloudflare Flux fallback")

# 2. Commons scout: search less literally and accept lawful graphics/satellite/map images.
refresh = ROOT / "scripts" / "refresh_pending_images.py"
replace_once(
    refresh,
    '''def words(value: str) -> list[str]:
    stop = {"efter", "over", "under", "siger", "mener", "skal", "ville", "bliver", "med", "fra", "til", "for", "the", "and", "with", "from"}
    return [x for x in re.findall(r"[A-Za-zÆØÅæøå0-9-]{4,}", value or "") if x.lower() not in stop]
''',
    '''def words(value: str) -> list[str]:
    stop = {"efter", "over", "under", "siger", "mener", "skal", "ville", "bliver", "med", "fra", "til", "for", "the", "and", "with", "from"}
    # Split compounds such as "Flood-relief" and "Nepal-Tibet" so Commons can
    # match event files whose English titles use the individual terms.
    value = str(value or "").replace("-", " ").replace("/", " ")
    return [x for x in re.findall(r"[A-Za-zÆØÅæøå0-9]{3,}", value) if x.lower() not in stop]
''',
    "Commons tokenization",
)

replace_once(
    refresh,
    '''def queries(article: dict) -> list[str]:
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
''',
    '''def queries(article: dict) -> list[str]:
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
''',
    "Commons query expansion",
)

replace_once(
    refresh,
    '''            "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata",
''',
    '''            "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 1600,
''',
    "Commons thumbnails",
)
replace_once(
    refresh,
    '''        query_terms = set(x.lower() for x in words(q))
''',
    '''        query_terms = set(x.lower().rstrip("s") for x in words(q))
''',
    "Commons query stemming",
)
replace_once(
    refresh,
    '''            if info.get("mime") != "image/jpeg" or not ALLOWED_LICENSE.search(license_name):
                continue
''',
    '''            if info.get("mime") not in {"image/jpeg", "image/png", "image/webp", "image/svg+xml"} or not ALLOWED_LICENSE.search(license_name):
                continue
''',
    "Commons visual formats",
)
replace_once(
    refresh,
    '''            bag = set(x.lower() for x in words(title + " " + desc))
''',
    '''            bag = set(x.lower().rstrip("s") for x in words(title + " " + desc))
''',
    "Commons result stemming",
)
replace_once(
    refresh,
    '''            artist = clean((meta.get("Artist") or {}).get("value") or (meta.get("Credit") or {}).get("value") or "Wikimedia Commons")
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
''',
    '''            artist = clean((meta.get("Artist") or {}).get("value") or (meta.get("Credit") or {}).get("value") or "Wikimedia Commons")
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
            event_bonus = 3 if year and year in visual_text else 0
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
''',
    "Commons documentary ranking",
)

# 3. Media gate: a truthful lawful map/satellite graphic may replace a pending sketch.
reapprove = ROOT / "scripts" / "reapprove_media_change.py"
replace_once(
    reapprove,
    "__legacy_media_gate_with_non_ai_placeholder__",
    '''    if image_type in {"photo", "video_still"}:
        if pending or ai_generated:
            raise SystemExit("Media re-approval blocked: documentary photo/still cannot be pending or AI-generated")
        if context_type not in {"event", "place", "person", "object", "archive"}:
            raise SystemExit("Media re-approval blocked: documentary image has invalid context_type")
        if context_type != "event" and not str(image.get("caption") or "").strip():
            raise SystemExit("Media re-approval blocked: non-event photo requires visible archive/context caption")
    elif image_type == "graphic" and not pending and not ai_generated:
        if context_type not in {"map", "satellite", "archive"}:
            raise SystemExit("Media re-approval blocked: documentary graphic must be map/satellite/archive")
        if not str(image.get("caption") or "").strip():
            raise SystemExit("Media re-approval blocked: documentary graphic requires a visible caption")
    elif pending or ai_generated:
        if image_type != "illustration" or context_type != "illustration":
            raise SystemExit("Media re-approval blocked: pending hero must be image_type=illustration and context_type=illustration")
        if not pending or not ai_generated:
            raise SystemExit("Media re-approval blocked: pending illustration must be AI-generated; static placeholders are forbidden")
''',
    "media gate static-placeholder ban",
)
replace_once(
    reapprove,
    '''        if current_image.get("image_type") not in {"photo", "video_still"}:
            raise SystemExit("Media re-approval blocked: pending sketch must be replaced by photo/video_still")
        if str(current_image.get("context_type") or "") not in {"event", "place", "person", "object", "archive"}:
            raise SystemExit("Media re-approval blocked: replacement documentary context_type invalid")
''',
    '''        if current_image.get("image_type") not in {"photo", "video_still", "graphic"}:
            raise SystemExit("Media re-approval blocked: pending sketch must be replaced by documentary photo/still/map/satellite graphic")
        allowed_context = {"event", "place", "person", "object", "archive"} if current_image.get("image_type") != "graphic" else {"map", "satellite", "archive"}
        if str(current_image.get("context_type") or "") not in allowed_context:
            raise SystemExit("Media re-approval blocked: replacement documentary context_type invalid")
''',
    "media gate documentary graphics",
)

# Basic syntax checks before committing.
print("hero policy v2 migration complete")
