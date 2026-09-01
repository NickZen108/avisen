#!/usr/bin/env python3
"""Fail pipeline-v2 articles that expose unexplained jargon or unfamiliar units."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content" / "articles"

# Terms that should normally be translated rather than exposed to readers.
FORBIDDEN_WORDS = {
    r"\bsurveys?\b": "oversæt 'survey' til fx kortlægning/undersøgelse",
    r"\bliftoff\b": "brug fx 'opsendelsen'",
    r"\bpayload\b": "brug/forklar fx nyttelast",
    r"\btelemetry\b": "brug/forklar fx måle- og statusdata",
}

# Technical terms are allowed only when the same article contains a plain-language explanation.
EXPLAINED_TERMS = [
    (r"\bexoplanet(?:er)?\b", [r"planet(?:er)?\s+(?:uden for|udenfor)\s+(?:vores\s+)?solsystem", r"planet(?:er)?.{0,80}andre stjerner"]),
    (r"\blagrange(?:-punkt(?:et|er)?)?\b", [r"tyngdekraft", r"samme placering.{0,80}(?:jorden|solen)", r"små kurskorrektioner"]),
    (r"\btelemetri(?:data)?\b", [r"måle-?\s*og\s*statusdata", r"måledata", r"statusdata"]),
    (r"\binfrarød(?:t|e)?\b", [r"længere bølgelæng", r"øjne.{0,50}(?:ikke|kan ikke)\s+se"]),
    (r"\bmørk energi\b", [r"fænomener?.{0,120}(?:univers|ikke.*forstå)", r"påvirker.{0,80}univers"]),
    (r"\bmørk materie\b", [r"fænomener?.{0,120}(?:galaks|ikke.*forstå)", r"påvirker.{0,80}galaks"]),
]

UNFAMILIAR_UNITS = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:nautiske?\s+mil|miles?|feet|foot|knob|mph|°\s*f|fahrenheit)\b",
    re.IGNORECASE,
)
METRIC_NEARBY = re.compile(r"(?:kilometer|km\b|meter\b|m\b|km/t|°\s*c|celsius)", re.IGNORECASE)


def public_text(article: dict) -> str:
    bits = [article.get("title", ""), article.get("standfirst", "")]
    seo = article.get("seo") or {}
    bits += [seo.get("title", ""), seo.get("description", "")]
    for block in article.get("body") or []:
        if isinstance(block, dict):
            bits.append(str(block.get("text", "")))
            bits.extend(str(x) for x in (block.get("items") or []))
    return "\n".join(x for x in bits if x).lower()


def unit_has_metric_conversion(text: str, match: re.Match[str]) -> bool:
    start = max(0, match.start() - 100)
    end = min(len(text), match.end() + 100)
    return bool(METRIC_NEARBY.search(text[start:end]))


def check_article(path: Path) -> list[str]:
    article = json.loads(path.read_text(encoding="utf-8"))
    if article.get("pipeline_version") != 2 or article.get("status") not in {"ready", "published"}:
        return []
    text = public_text(article)
    errors: list[str] = []

    for pattern, advice in FORBIDDEN_WORDS.items():
        if re.search(pattern, text, re.IGNORECASE):
            errors.append(f"{path.name}: lægmandssprog: {advice}")

    for term_pattern, explanation_patterns in EXPLAINED_TERMS:
        if re.search(term_pattern, text, re.IGNORECASE) and not any(
            re.search(p, text, re.IGNORECASE | re.DOTALL) for p in explanation_patterns
        ):
            term = re.search(term_pattern, text, re.IGNORECASE).group(0)
            errors.append(f"{path.name}: fagterm '{term}' bruges uden kort lægmandsforklaring")

    for match in UNFAMILIAR_UNITS.finditer(text):
        if not unit_has_metric_conversion(text, match):
            errors.append(
                f"{path.name}: uvant enhed '{match.group(0)}' mangler nærliggende dansk/metrisk omregning"
            )

    return errors


def main() -> None:
    errors: list[str] = []
    checked = 0
    for path in sorted(ARTICLES.glob("*.json")):
        if path.name.startswith("_"):
            continue
        article = json.loads(path.read_text(encoding="utf-8"))
        if article.get("pipeline_version") == 2 and article.get("status") in {"ready", "published"}:
            checked += 1
        errors.extend(check_article(path))

    if errors:
        print(f"Readability gate: FAIL ({len(errors)} fejl i {checked} pipeline-v2 artikler)")
        for error in errors:
            print(f"- {error}")
        print("Readability gate: WARN only; redaktionel betydning afgøres af Journalist/Slutredaktør")
        return
    print(f"Readability gate: PASS ({checked} pipeline-v2 artikler)")


if __name__ == "__main__":
    main()
