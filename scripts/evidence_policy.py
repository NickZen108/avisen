#!/usr/bin/env python3
"""Canonical deterministic evidence policy shared by repository gates.

The Cloudflare Worker mirrors these rules and parity fixtures guard drift.
"""
from __future__ import annotations
import re

PRIMARY_TYPES = {"primary", "paper", "interview"}
HIGH_RISK = re.compile(r"\b(sigtet|tiltalt|anklag|mistænkt|voldtægt|seksual|misbrug|selvmord|mindreår|barn|børn|privat helbred|diagnose|terror|drab|korruption|svindel|hvidvask|overgreb|racist|ekstremist)\b", re.I)
ACCUSED = re.compile(r"\b(sigtet|tiltalt|mistænkt|anklaget)\b", re.I)
NAMED = re.compile(r"\b[A-ZÆØÅ][a-zæøåéèáàíìóòúù-]+\s+[A-ZÆØÅ][a-zæøåéèáàíìóòúù-]+\b")
WIRES = ("reuters", "associated press", "apnews", "agence france-presse", "afp", "ritzau")


def authoritative_primary(source: dict | None) -> bool:
    return bool(source and source.get("type") in PRIMARY_TYPES and str(source.get("authoritative_for") or "").strip())


def original_wire(source: dict | None) -> bool:
    if not source:
        return False
    if str(source.get("wire_origin") or "").strip():
        return True
    group = str(source.get("source_group") or "").lower()
    return group.startswith("wire-")


def evidence_atom(source: dict | None) -> str:
    if not source:
        return ""
    if authoritative_primary(source):
        record = str(source.get("primary_record") or source.get("url") or source.get("source_group") or "primary").strip()
        return "primary:" + record
    upstream = str(source.get("upstream_origin") or "").strip().lower()
    if upstream:
        return "upstream:" + upstream
    wire = str(source.get("wire_origin") or "").strip().lower()
    if wire:
        return "wire:" + wire
    cluster = str(source.get("provenance_cluster") or "").strip()
    if cluster:
        return "cluster:" + cluster
    root = str(source.get("publisher_root") or source.get("source_group") or "").strip().lower()
    return "publisher:" + root if root else ""


def high_risk(article: dict, ledger: dict, claim: dict) -> bool:
    if (ledger.get("right_of_reply") or {}).get("required"):
        return True
    text = " ".join(str(x or "") for x in (article.get("title"), article.get("standfirst"), claim.get("claim")))
    return bool(HIGH_RISK.search(text))


def named_accused(claim: dict) -> bool:
    text = str(claim.get("claim") or "")
    return bool(ACCUSED.search(text) and NAMED.search(text))


def claim_has_required_support(article: dict, ledger: dict, claim: dict, sources: dict[str, dict]) -> bool:
    rows = [sources.get(sid) for sid in claim.get("source_ids", [])]
    rows = [s for s in rows if s]
    primary_ok = any(authoritative_primary(s) for s in rows)
    if named_accused(claim):
        return primary_ok
    atoms = {evidence_atom(s) for s in rows if evidence_atom(s)}
    if high_risk(article, ledger, claim):
        return primary_ok or len(atoms) >= 2
    return primary_ok or any(original_wire(s) for s in rows) or len(atoms) >= 2
