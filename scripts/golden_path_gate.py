#!/usr/bin/env python3
"""Verify that at least one real published Pipeline-v2 article traversed the full path.

The gate deliberately uses production-shaped repository artifacts rather than a toy
fixture: canonical article -> ledger -> source sweep -> claim verification -> desk
recheck -> final approval -> generated article -> front-page/live-proof readiness.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "content" / "articles"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def latest_v2():
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
    return rows[0] if rows else None


def main():
    row = latest_v2()
    if not row:
        print("GOLDEN PATH: FAIL - ingen publiceret Pipeline-v2 artikel")
        return 1
    _, path, a = row
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
    if len(set(sweep.get("independent_source_groups") or [])) < 3:
        problems.append("coverage sweep har under tre deklarerede source-groups")

    sources = {s.get("id"): s for s in ledger.get("sources") or [] if s.get("id")}
    for cid in a.get("claim_ids") or []:
        claim = next((c for c in ledger.get("claims") or [] if c.get("id") == cid), None)
        if not claim or claim.get("status") != "verified":
            problems.append(f"claim {cid} er ikke verified")
            continue
        groups = {str(sources.get(sid, {}).get("source_group") or "") for sid in claim.get("source_ids") or []}
        groups.discard("")
        if len(groups) < 2:
            problems.append(f"claim {cid} har under to source-groups")

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

    if problems:
        print(f"GOLDEN PATH: FAIL ({path.name})")
        for p in problems:
            print("-", p)
        return 1
    print(f"GOLDEN PATH: PASS - {a['slug']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
