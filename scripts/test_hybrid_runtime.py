#!/usr/bin/env python3
"""Regression checks for the hybrid GitHub/Cloudflare editorial architecture."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> int:
    dispatch = load_module("dispatch", ROOT / "scripts" / "editorial_dispatch_gate.py")
    dispatch.self_test()
    prefetch = load_module("prefetch", ROOT / "scripts" / "github_source_prefetch.py")
    prefetch.self_test()

    sync = load_module("sync", ROOT / "scripts" / "sync_cloudflare_editorial.py")
    assert sync.authoritative_editorial({"name": "Reuters", "source_group": "wire-reuters"})
    assert sync.authoritative_editorial({"name": "Associated Press", "source_group": "wire-ap"})
    assert not sync.authoritative_editorial({"name": "Example Blog", "source_group": "host-example.test"})

    js = (ROOT / "cloudflare" / "newsdesk" / "src" / "editorial.js").read_text(encoding="utf-8")
    required = [
        'function authoritativeEditorial(item)',
        '"wire-reuters", "wire-ap", "wire-afp", "wire-ritzau"',
        'function deterministicFinalReview(assignment, dossier, article)',
        'function requiresAiFinalReview(assignment, dossier, article)',
        '["A", "B"].includes(assignment?.weight)',
        '["Krimi", "Sundhed"].includes(assignment?.category)',
        'dossier?.right_of_reply_required',
        'const aiFinalRequired = requiresAiFinalReview',
        'final_editor_mode: review.mode || "ai"',
        'Discovery-only source crossed the Research/Fact-check boundary',
        'fetch_origin: "github-actions-prefetch"',
    ]
    missing = [item for item in required if item not in js]
    assert not missing, f"Hybrid runtime regression: missing {missing}"

    index_js = (ROOT / "cloudflare" / "newsdesk" / "src" / "index.js").read_text(encoding="utf-8")
    for item in ('function mergeGitHubPrefetch(scan, prefetch)', 'prefetch.scan_fingerprint !== scan?.fingerprint', 'result.github_prefetch'):
        assert item in index_js, f"GitHub prefetch boundary regression: {item}"

    print("hybrid_runtime self-test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
