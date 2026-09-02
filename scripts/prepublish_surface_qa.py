#!/usr/bin/env python3
"""Deterministic pre-publish surface checks for Morgentidende.

This complements fact/editorial gates: it protects hero/media metadata and the
shared light/dark responsive shell before generated HTML can be deployed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content" / "articles"

ALLOWED_AI_PEOPLE_STYLES = {
    "editorial_illustration",
    "pencil_sketch",
    "pencil_hatching",
    "line_art",
    "collage",
    "silhouette",
    "flat_vector",
    "watercolor",
    "woodcut",
    "ink_drawing",
}
PHOTOREAL_STYLE_TERMS = {
    "photorealistic",
    "photo_realistic",
    "realistic_photo",
    "documentary_photo",
    "cinematic_photo",
}


def check_ai_people_style(label: str, image: dict, faults: list[str]) -> None:
    if not image.get("ai_generated"):
        return
    if image.get("image_type") != "illustration":
        faults.append(f"{label}: AI-genereret grafik skal være mærket illustration")
    contains_people = image.get("contains_people")
    if not isinstance(contains_people, bool):
        faults.append(f"{label}: AI-grafik skal deklarere contains_people true|false")
        return
    if not contains_people:
        return
    style = str(image.get("people_style") or "").strip().lower()
    if not style:
        faults.append(f"{label}: AI-grafik med mennesker mangler people_style")
        return
    if style in PHOTOREAL_STYLE_TERMS or image.get("photorealistic") is True:
        faults.append(f"{label}: fotorealistiske AI-personer er ikke tilladt")
    elif style not in ALLOWED_AI_PEOPLE_STYLES:
        faults.append(f"{label}: ikke-godkendt AI-personstil {style!r}")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    faults: list[str] = []

    # Shared shell must retain the responsive viewport and accessible dark-mode switch.
    for template_name in ("article.html", "index.html"):
        path = ROOT / "templates" / template_name
        text = path.read_text(encoding="utf-8")
        for needle, label in (
            ('name="viewport"', "responsive viewport"),
            ("theme.css", "dark-mode CSS"),
            ("theme.js", "dark-mode JS"),
            ('class="theme-toggle"', "dark-mode toggle"),
            ('role="switch"', "accessible switch semantics"),
        ):
            if needle not in text:
                faults.append(f"{template_name}: mangler {label}")

    theme_css = (ROOT / "docs" / "theme.css").read_text(encoding="utf-8")
    theme_js = (ROOT / "docs" / "theme.js").read_text(encoding="utf-8")
    if "prefers-color-scheme" not in theme_js and "prefers-color-scheme" not in theme_css:
        faults.append("dark mode følger ikke systempræference")
    if "localStorage" not in theme_js:
        faults.append("dark mode husker ikke brugerens valg")

    for path in sorted(ARTICLES.glob("*.json")):
        if path.name.startswith("_"):
            continue
        article = load(path)
        if article.get("status") not in {"ready", "published"}:
            continue
        image = article.get("image")
        origin = article.get("automation_origin")

        # Autonomous news may publish with a temporary, unmistakably illustrative
        # pencil hero after deterministic media scouting. Image integrity remains hard.
        if origin == "cloudflare-workers-ai":
            if not isinstance(image, dict):
                faults.append(f"{path.name}: autonom artikel mangler hero")
                continue
            if image.get("placement", "lead") != "lead":
                faults.append(f"{path.name}: autonom artikel har ikke lead-hero")

            image_type = image.get("image_type")
            context_type = str(image.get("context_type") or "").strip().lower()
            pending = image.get("pending_image") is True
            ai_generated = image.get("ai_generated") is True

            if image_type in {"photo", "video_still"}:
                if pending or ai_generated:
                    faults.append(f"{path.name}: dokumentarisk foto/still må ikke være pending eller AI-genereret")
                if context_type not in {"event", "place", "person", "object", "archive"}:
                    faults.append(f"{path.name}: ugyldig context_type for dokumentarisk hero")
                if context_type != "event" and not str(image.get("caption") or "").strip():
                    faults.append(f"{path.name}: ikke-hændelsesfoto kræver synlig arkiv-/kontekst-caption")
                source_url = str(image.get("source_url") or "").lower()
                if image_type == "video_still" and ("youtube.com" in source_url or "youtu.be" in source_url):
                    if not str(image.get("rights_basis") or "").strip():
                        faults.append(f"{path.name}: YouTube-video-still kræver dokumenteret rights_basis")
                if image.get("discovery_only_source") is True and image.get("independent_license") is not True:
                    faults.append(f"{path.name}: discovery_only må ikke være billedkilde uden selvstændig licens")
            elif image_type == "graphic":
                # Lawful, non-AI documentary maps/satellite images are a valid hero
                # before we fall back to a Flux pencil illustration.
                if pending or ai_generated:
                    faults.append(f"{path.name}: dokumentarisk grafik må ikke være pending eller AI-genereret")
                if context_type not in {"map", "satellite", "archive"}:
                    faults.append(f"{path.name}: ugyldig context_type for dokumentarisk grafik")
                if not str(image.get("caption") or "").strip():
                    faults.append(f"{path.name}: dokumentarisk grafik kræver synlig kontekst-caption")
                source_url = str(image.get("source_url") or "").lower()
                if image.get("discovery_only_source") is True and image.get("independent_license") is not True:
                    faults.append(f"{path.name}: discovery_only må ikke være grafikkilde uden selvstændig licens")
            elif image_type == "illustration":
                # Legacy static placeholders can still be read while old records are
                # being replaced, but the canonical Cloudflare generator no longer
                # creates them. New fallback heroes are Flux-generated pencil art.
                static_fallback = image.get("generator") == "static_pencil_fallback"
                if not pending or (not ai_generated and not static_fallback):
                    faults.append(f"{path.name}: nyhedsillustration skal være pending og AI-genereret (legacy static accepteres kun under migration)")
                if context_type != "illustration":
                    faults.append(f"{path.name}: pending illustration skal have context_type=illustration")
                if str(image.get("caption") or "").strip().lower() != "illustration":
                    faults.append(f"{path.name}: pending illustration skal have synlig caption 'Illustration'")
                if image.get("photorealistic") is True:
                    faults.append(f"{path.name}: pending illustration må ikke være fotorealistisk")
            else:
                faults.append(f"{path.name}: ugyldig autonom hero-type {image_type!r}")

            for key in ("src", "alt", "credit", "license", "source_url"):
                if not str(image.get(key) or "").strip():
                    faults.append(f"{path.name}: hero mangler {key}")

            src = str(image.get("src") or "")
            # Raw SVG is still not a public hero; Commons SVGs are requested as raster thumbnails.
            if src.lower().endswith(".svg"):
                faults.append(f"{path.name}: autonom hero må ikke være rå SVG")
            if src.startswith("/img/"):
                local = ROOT / "docs" / src.lstrip("/")
                if not local.exists():
                    faults.append(f"{path.name}: lokal hero findes ikke: {src}")

        if isinstance(image, dict):
            check_ai_people_style(path.name, image, faults)

        # Every declared lead image, including older articles, needs basic truthful metadata.
        if isinstance(image, dict) and image.get("src") and image.get("placement", "lead") == "lead":
            if not str(image.get("alt") or "").strip():
                faults.append(f"{path.name}: lead-billede mangler alt-tekst")
            if not str(image.get("credit") or "").strip():
                faults.append(f"{path.name}: lead-billede mangler kredit")
            if image.get("image_type") in {"photo", "graphic"} and not str(image.get("license") or "").strip():
                faults.append(f"{path.name}: foto/grafik mangler licens")

        for i, block in enumerate(article.get("body") or []):
            if block.get("type") != "figure":
                continue
            if not str(block.get("src") or "").strip():
                faults.append(f"{path.name}: figur {i} mangler src")
            if not str(block.get("alt") or "").strip():
                faults.append(f"{path.name}: figur {i} mangler alt-tekst")
            check_ai_people_style(f"{path.name}: figur {i}", block, faults)

    # Generated hero CSS must have a crop-safe default; diagrams are inline/contain.
    style = (ROOT / "docs" / "style.css").read_text(encoding="utf-8")
    if not re.search(r"\.lead-fig\s+img\s*\{[^}]*object-fit:\s*cover", style, re.S):
        faults.append("style.css: hero mangler object-fit: cover")
    if not re.search(r"\.article-graphic\s+img\s*\{[^}]*object-fit:\s*contain", style, re.S):
        faults.append("style.css: inline grafik mangler object-fit: contain")

    if faults:
        print("PREPUBLISH SURFACE QA: FAIL")
        for fault in faults:
            print("-", fault)
        return 1
    print("PREPUBLISH SURFACE QA: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
