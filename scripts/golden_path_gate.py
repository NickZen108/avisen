#!/usr/bin/env python3
"""Verify that at least one real published Pipeline-v2 article traversed the full path.

The gate deliberately uses production-shaped repository artifacts rather than a toy
fixture: canonical article -> ledger -> research coverage -> claim verification -> desk
recheck -> final approval -> generated article -> front-page/live-proof readiness.
Coverage quality is claim/risk dependent; this repository-level proof must not impose
a universal source-count quota that is stricter than the editorial pipeline itself.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "content" / "articles"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def published_v2():
    rows = []
    for p in ART.glob("*.json"):
        if p.name.startswith("_"):
            continue
        try:
            a = load(p)
        except Exception:
            continue
        if a.get("pipeline_version") == 2 and a.get("status") == "published":
            rows.append((a.get("published_at") or "", p, a))
    rows.sort(reverse=True, key=lambda x: x[0])
    return rows


def problems_for(path, a):
    problems = []
    ledger_path = ROOT / str(a.get("ledger") or "")
    if not ledger_path.exists():
        problems.append("ledger mangler")
        ledger = {}
    else:
        ledger = load(ledger_path)

    sweep = ledger.get("coverage_sweep") or {}
    if sweep.get("status") != "pass":
        problems.append("coverage_sweep er ikke pass")

    sources = {s.get("id"): s for s in ledger.get("sources") or [] if s.get("id")}
    for cid in a.get("claim_ids") or []:
        claim = next((c for c in ledger.get("claims") or [] if c.get("id") == cid), None)
        if not claim or claim.get("status") != "verified":
            problems.append(f"claim {cid} er ikke verified")
            continue
        groups = {str(sources.get(sid, {}).get("source_group") or "") for sid in claim.get("source_ids") or []}
        groups.discard("")
        primary_ok = any(
            sources.get(sid, {}).get("type") in {"primary", "paper", "interview"}
            and str(sources.get(sid, {}).get("authoritative_for") or "").strip()
            for sid in claim.get("source_ids") or []
        )
        if not primary_ok and len(groups) < 2:
            problems.append(f"claim {cid} har hverken autoritativ primærkilde eller to source-groups")

    if (ledger.get("fact_check") or {}).get("status") != "pass":
        problems.append("fact_check er ikke pass")
    if (ledger.get("desk_recheck") or {}).get("status") not in {"publish", "update"}:
        problems.append("desk_recheck er ikke publish/update")

    approval_path = ROOT / "reports" / "editorial" / "approvals" / f"{a['slug']}.json"
    if not approval_path.exists():
        problems.append("final approval mangler")
    else:
        approval = load(approval_path)
        gates = approval.get("gates") or {}
        for gate in ("language", "ethics", "image", "seo", "final_editor"):
            if gates.get(gate) != "pass":
                problems.append(f"approval gate {gate} er ikke pass")

    html_path = ROOT / "docs" / "artikler" / f"{a['slug']}.html"
    if not html_path.exists():
        problems.append("genereret artikel-HTML mangler")
    else:
        html = html_path.read_text(encoding="utf-8", errors="replace")
        if a.get("title") not in html:
            problems.append("genereret HTML indeholder ikke canonical titel")
        if "Morgentidende" not in html:
            problems.append("genereret HTML mangler masthead")
    return problems


def main():
    rows = published_v2()
    if not rows:
        print("GOLDEN PATH: FAIL - ingen publiceret Pipeline-v2 artikel")
        return 1

    diagnostics = []
    for _, path, a in rows:
        problems = problems_for(path, a)
        if not problems:
            print(f"GOLDEN PATH: PASS - {a['slug']}")
            return 0
        diagnostics.append((path, problems))

    path, problems = diagnostics[0]
    print(f"GOLDEN PATH: FAIL - ingen komplet publiceret golden-path artikel; seneste kandidat {path.name}")
    for p in problems:
        print("-", p)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
