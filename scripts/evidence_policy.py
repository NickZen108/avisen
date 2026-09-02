#!/usr/bin/env python3
"""Canonical deterministic evidence policy shared by repository gates.

The Cloudflare Worker mirrors these rules and parity fixtures guard drift.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

PRIMARY_TYPES = {"primary", "paper", "research_paper", "interview", "official_statement"}
SCOPED_AUTHORITY = {
    "paper", "research_paper", "researcher", "scientist", "expert",
    "company_statement", "organization_statement", "person_statement",
    "first_party_statement", "interview", "official_statement",
}
INSTITUTIONAL_CLASSES = {"official", "authority", "government", "public_body"}
LABEL_ONLY_MEDIA = {"public_media", "major_media", "strong_editorial", "wire"}
AUTHORITATIVE_CLASSES = (
    {"primary"} | INSTITUTIONAL_CLASSES | LABEL_ONLY_MEDIA | SCOPED_AUTHORITY
)
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
NAMED_ACCUSED_VERBS = re.compile(r"\b(sigtet|tiltalt|mistænkt)\b", re.IGNORECASE)
NAMED_PERSON = re.compile(
    r"\b[A-ZÆØÅ][a-zæøåéèáàíìóòúù-]+\s+[A-ZÆØÅ][a-zæøåéèáàíìóòúù-]+\b"
)


def _source_host(source: dict | None) -> str:
    if not source:
        return ""
    try:
        return (urlparse(str(source.get("url") or "")).hostname or "").removeprefix("www.").lower()
    except Exception:
        return ""


def _host_in(host: str, hosts: set[str]) -> bool:
    return any(host == base or host.endswith("." + base) for base in hosts)


def _labels(source: dict | None) -> set[str]:
    if not source:
        return set()
    labels = {
        str(source.get("authority_class") or "").strip().lower(),
        str(source.get("source_kind") or "").strip().lower(),
        str(source.get("source_strength") or "").strip().lower(),
        str(source.get("provenance_type") or "").strip().lower(),
        str(source.get("type") or "").strip().lower(),
    }
    labels.discard("")
    return labels


def authoritative_primary(source: dict | None) -> bool:
    if not source:
        return False
    source_type = str(source.get("type") or "").strip().lower()
    if source_type not in PRIMARY_TYPES:
        return False
    return bool(str(source.get("authoritative_for") or "").strip())


def original_wire(source: dict | None) -> bool:
    """True only for explicit provenance or a known original wire host."""
    if not source:
        return False
    if str(source.get("wire_origin") or "").strip():
        return True
    return _host_in(_source_host(source), set(WIRE_HOSTS))


def primary_or_original_wire(source: dict | None) -> bool:
    return authoritative_primary(source) or original_wire(source)


def authoritative_source(source: dict | None) -> bool:
    """Whether one source may, by itself, verify a claim.

    House rule: one relevant authoritative source is enough. Authority includes
    major newsrooms, official/public authorities, first-party statements about
    own affairs, researchers/experts in field, and original research papers.
    Discovery-only and utility/account pages are never authoritative evidence.
    A media label without a known major-media host or wire origin is not enough.
    """
    if not source or source.get("discovery_only"):
        return False
    if primary_or_original_wire(source):
        return True
    host = _source_host(source)
    if _host_in(host, MAJOR_MEDIA_HOSTS):
        return True
    labels = _labels(source)
    if labels & INSTITUTIONAL_CLASSES:
        return True
    if labels & SCOPED_AUTHORITY:
        return bool(str(source.get("authoritative_for") or "").strip())
    if labels & LABEL_ONLY_MEDIA:
        return False
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


def named_accused_crime_claim(claim: dict | None) -> bool:
    """Danish named-person accusation verbs. English court copy is not auto-classified here."""
    text = str((claim or {}).get("claim") or "")
    if not NAMED_ACCUSED_VERBS.search(text):
        return False
    return bool(NAMED_PERSON.search(text))


def supporting_source_ids(ledger: dict, claim: dict) -> list[str]:
    # Canonical rule: source_ids are the evidence references. No separate passage
    # object may veto an otherwise relevant authoritative source.
    return list(claim.get("source_ids", []))


def claim_has_required_support(article: dict, ledger: dict, claim: dict, sources: dict[str, dict]) -> bool:
    source_ids = supporting_source_ids(ledger, claim)
    if not source_ids:
        return False
    rows = [sources.get(sid) for sid in source_ids]
    rows = [s for s in rows if s and not s.get("discovery_only")]
    if not rows:
        return False
    if named_accused_crime_claim(claim):
        return any(primary_or_original_wire(s) for s in rows)
    return any(authoritative_source(s) for s in rows)
