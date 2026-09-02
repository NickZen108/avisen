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


def infer_new_destination(article: dict) -> str:
    """Preserve the Newsdesk birth decision; never infer a magazine later."""
    explicit = str(article.get("editorial_destination") or "").strip()
    return explicit if explicit in VALID else MAIN


def is_magazine(article: dict) -> bool:
    return str(article.get("editorial_destination") or "") in {TECH, PEOPLE}
