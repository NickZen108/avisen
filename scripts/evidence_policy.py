#!/usr/bin/env python3
"""Canonical deterministic evidence policy shared by repository gates.

The Cloudflare Worker mirrors these rules and parity fixtures guard drift.
"""
from __future__ import annotations
import re
from urllib.parse import urlparse

PRIMARY_TYPES = {"primary", "paper", "interview"}
HIGH_RISK = re.compile(r"\b(sigtet|tiltalt|anklag|mistænkt|voldtægt|seksual|misbrug|selvmord|mindreår|diagnose|terror|drab|korruption|svindel|hvidvask|overgreb|racist|ekstremist)\b|\bprivat\s+helbred\b", re.I)
ACCUSED = re.compile(r"\b(sigtet|tiltalt|mistænkt|anklaget)\b", re.I)
NAMED = re.compile(r"\b[A-ZÆØÅ][a-zæøåéèáàíìóòúù-]+\s+[A-ZÆØÅ][a-zæøåéèáàíìóòúù-]+\b")
WIRE_HOSTS = {
    "reuters.com": "reuters",
    "apnews.com": "ap",
}


def authoritative_primary(source: dict | None) -> bool:
    return bool(source and source.get("type") in PRIMARY_TYPES and str(source.get("authoritative_for") or "").strip())


def _source_host(source: dict | None) -> str:
    if not source:
        return ""
    try:
        return (urlparse(str(source.get("url") or "")).hostname or "").removeprefix("www.").lower()
    except Exception:
        return ""


def original_wire(source: dict | None) -> bool:
    """True only for explicit provenance or a known original wire host.

    A source_group label alone is not proof of bureau origin; it may have been
    derived from a secondary publisher mentioning a wire service.
    """
    if not source:
        return False
    if str(source.get("wire_origin") or "").strip():
        return True
    host = _source_host(source)
    return any(host == base or host.endswith("." + base) for base in WIRE_HOSTS)


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
    host = _source_host(source)
    for base, label in WIRE_HOSTS.items():
        if host == base or host.endswith("." + base):
            return "wire:" + label
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
    source_ids = list(claim.get("source_ids", []))
    if int(ledger.get("schema_version") or 0) >= 3:
        verified_passages = {
            str(x.get("source_id")) for x in claim.get("support_passages", [])
            if x.get("match_verified") is True and str(x.get("quote") or "").strip()
        }
        source_ids = [sid for sid in source_ids if sid in verified_passages]
        if not source_ids:
            return False
    rows = [sources.get(sid) for sid in source_ids]
    rows = [s for s in rows if s and not s.get("discovery_only")]
    primary_ok = any(authoritative_primary(s) for s in rows)
    if named_accused(claim):
        return primary_ok
    atoms = {evidence_atom(s) for s in rows if evidence_atom(s)}
    if high_risk(article, ledger, claim):
        return primary_ok or len(atoms) >= 2
    return primary_ok or any(original_wire(s) for s in rows) or len(atoms) >= 2
