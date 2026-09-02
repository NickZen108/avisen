#!/usr/bin/env python3
"""Canonical deterministic evidence policy shared by repository gates.

The Cloudflare Worker mirrors these rules and parity fixtures guard drift.
"""
from __future__ import annotations
from urllib.parse import urlparse

PRIMARY_TYPES = {"primary", "paper", "research_paper", "interview", "official_statement"}
AUTHORITATIVE_CLASSES = {
    "primary", "official", "authority", "government", "public_body",
    "strong_editorial", "public_media", "major_media", "wire",
    "paper", "research_paper", "researcher", "scientist", "expert",
    "company_statement", "organization_statement", "person_statement",
    "first_party_statement", "interview", "official_statement",
}
MAJOR_MEDIA_HOSTS = {
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "dr.dk", "tv2.dk",
    "svt.se", "nrk.no", "ft.com", "politico.eu", "bloomberg.com",
    "theguardian.com", "nytimes.com", "wsj.com", "france24.com", "dw.com",
    "euronews.com", "aljazeera.com", "sky.com", "skynews.com", "cnn.com",
    "nbcnews.com", "cbsnews.com", "abcnews.go.com", "foxnews.com",
    "spiegel.de", "lemonde.fr", "tagesschau.de", "rbb24.de", "itv.com",
}
WIRE_HOSTS = {
    "reuters.com": "reuters",
    "apnews.com": "ap",
}


def _source_host(source: dict | None) -> str:
    if not source:
        return ""
    try:
        return (urlparse(str(source.get("url") or "")).hostname or "").removeprefix("www.").lower()
    except Exception:
        return ""


def _host_in(host: str, hosts: set[str]) -> bool:
    return any(host == base or host.endswith("." + base) for base in hosts)


def authoritative_primary(source: dict | None) -> bool:
    if not source:
        return False
    source_type = str(source.get("type") or "").strip().lower()
    if source_type not in PRIMARY_TYPES:
        return False
    # Primary/first-party material must say what it is authoritative for.
    return bool(str(source.get("authoritative_for") or "").strip())


def original_wire(source: dict | None) -> bool:
    """True only for explicit provenance or a known original wire host."""
    if not source:
        return False
    if str(source.get("wire_origin") or "").strip():
        return True
    return _host_in(_source_host(source), set(WIRE_HOSTS))


def authoritative_source(source: dict | None) -> bool:
    """Whether one source may, by itself, verify a claim.

    House rule: one relevant authoritative source is enough. Authority includes
    major newsrooms, official/public authorities, first-party statements about
    own affairs, researchers/experts in field, and original research papers.
    Discovery-only and utility/account pages are never authoritative evidence.
    """
    if not source or source.get("discovery_only"):
        return False
    if authoritative_primary(source) or original_wire(source):
        return True
    host = _source_host(source)
    if _host_in(host, MAJOR_MEDIA_HOSTS):
        return True
    labels = {
        str(source.get("authority_class") or "").strip().lower(),
        str(source.get("source_kind") or "").strip().lower(),
        str(source.get("source_strength") or "").strip().lower(),
        str(source.get("provenance_type") or "").strip().lower(),
        str(source.get("type") or "").strip().lower(),
    }
    labels.discard("")
    if labels & AUTHORITATIVE_CLASSES:
        # First-party/expert/research authority must be explicitly scoped.
        scoped = {
            "paper", "research_paper", "researcher", "scientist", "expert",
            "company_statement", "organization_statement", "person_statement",
            "first_party_statement", "interview", "official_statement",
        }
        if labels & scoped:
            return bool(str(source.get("authoritative_for") or "").strip())
        return True
    return False


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
    return any(authoritative_source(s) for s in rows)
