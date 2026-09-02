#!/usr/bin/env python3
"""Canonical editorial destination policy for Morgentidende.

A story belongs to a magazine only when it is explicitly born with an
editorial_destination. Topic similarity alone never moves an ordinary story into
a magazine later.
"""
from __future__ import annotations

TECH = "tech_magazine"
PEOPLE = "people_magazine"
MAIN = "main"
VALID = {MAIN, TECH, PEOPLE}

TECH_TERMS = (
    "videnskab", "forskning", "naturvidenskab", "teknologi", "kunstig intelligens", " ai ",
    "rumfart", "rumteleskop", "astronomi", "fysik", "biologi", "robot", "chip", "halvleder",
    "militærteknologi", "militaerteknologi", "forsvarsteknologi", "drone", "energi",
)
PEOPLE_TERMS = (
    "psykologi", "psykisk", "mental sundhed", "sundhed", "testosteron", "hormon",
    "overgangsalder", "menopause", "parforhold", "ægteskab", "aegteskab", "sex",
    "singleliv", "single", "dating", "opdragelse", "forældre", "foraeldre",
    "bedsteforældre", "bedsteforaeldre", "familie", "relation", "tilknytning",
    "evolutionær psykologi", "evolutionaer psykologi",
)


def article_text(article: dict) -> str:
    body = article.get("body") or []
    body_text = " ".join(
        str(block.get("text") or "") if isinstance(block, dict) else str(block)
        for block in body
    ) if isinstance(body, list) else str(body)
    tags = article.get("tags") or []
    if isinstance(tags, list):
        tags = " ".join(str(x) for x in tags)
    return f" {article.get('category','')} {article.get('title','')} {article.get('standfirst','')} {tags} {body_text} ".lower()


def infer_new_destination(article: dict) -> str:
    """Choose a destination once, at ingestion/birth of a new article.

    Explicit Cloudflare assignment wins. Otherwise deterministic subject rules
    provide a safe bridge while the Newsdesk runtime rolls out the same field.
    Existing stored articles are never reclassified by this function.
    """
    explicit = str(article.get("editorial_destination") or "").strip()
    if explicit in VALID:
        return explicit
    text = article_text(article)
    category = str(article.get("category") or "").strip()
    if category == "Videnskab & teknologi" or any(term in text for term in TECH_TERMS):
        return TECH
    if category in {"Sundhed", "Parforhold", "Liv"} or any(term in text for term in PEOPLE_TERMS):
        return PEOPLE
    return MAIN


def is_magazine(article: dict) -> bool:
    return str(article.get("editorial_destination") or "") in {TECH, PEOPLE}
