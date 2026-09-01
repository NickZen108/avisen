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
    assert not sync.authoritative_editorial({"name": "NRK", "url": "https://www.nrk.no/sak"})
    assert sync.strong_editorial({"name": "NRK", "url": "https://www.nrk.no/sak"})
    assert sync.strong_editorial({"name": "Financial Times", "url": "https://www.ft.com/content/example"})
    assert not sync.strong_editorial({"name": "Example Blog", "url": "https://example.test/post"})
    assert not sync.high_risk_claim({"category": "Udland", "title": "Minister deltager i EU-møde", "standfirst": ""}, {"right_of_reply": {"required": False}}, {"claim": "Minister deltager i mødet"})
    assert sync.high_risk_claim({"category": "Krimi", "title": "Fem dømt", "standfirst": ""}, {"right_of_reply": {"required": False}}, {"claim": "Fem dømt for hvidvask"})
    assert sync.valid_documentary_image({
        "src": "https://example.test/photo.jpg",
        "source_url": "https://example.test/license",
        "image_type": "photo",
        "alt": "Dokumentarisk foto",
        "credit": "Example",
        "license": "CC BY 4.0",
    })
    assert not sync.valid_documentary_image({
        "src": "https://example.test/ai.jpg",
        "source_url": "https://example.test/source",
        "image_type": "illustration",
        "alt": "AI",
        "credit": "Morgentidende",
        "license": "Morgentidende",
    })

    js = (ROOT / "cloudflare" / "newsdesk" / "src" / "editorial.js").read_text(encoding="utf-8")
    required = [
        'function authoritativeEditorial(item)',
        'function strongEditorialSource(item)',
        'function normalizedSourceKind(item)',
        'function highRiskFactClaim(assignment, research, claim)',
        'function evidenceRulePass(assignment, research, claim, evidence)',
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
        'host === "reuters.com"',
        'source === "ap"',
        'For almindelige lavrisiko-fakta kan Verified bæres',
        'Ét verificeret bærende claim er nok til en kort one-claim-artikel',
        'Din overordnede publish/hold-vurdering er rådgivende',
        'feed_summary_only',
        'source_strength',
        'fact.decision = verified.length >= 1 ? "publish" : "hold"',
        'function newsRequiresDocumentaryHero()',
        'function validDocumentaryHero(media)',
        'function documentaryHeroFromSignals(selected = [])',
        'async function findCommonsDocumentaryHero(assignment, article)',
        'commonsLicenseAllowed',
        'image/jpeg',
        'if (requiresDocumentary && !documentaryHero)',
        'Nyheder kræver et ægte, juridisk anvendeligt dokumentarisk hero-billede',
        'ai_hero_allowed: false',
    ]
    missing = [item for item in required if item not in js]
    assert not missing, f"Hybrid runtime regression: missing {missing}"
    assert "await generateHero(" not in js, "AI hero generation must not exist in the autonomous news runtime"
    assert "flux-1-schnell" not in js, "News runtime must not reference a generative image model"

    index_js = (ROOT / "cloudflare" / "newsdesk" / "src" / "index.js").read_text(encoding="utf-8")
    for item in (
        'function mergeGitHubPrefetch(scan, prefetch)',
        'prefetch.scan_fingerprint !== scan?.fingerprint',
        'github_prefetch: incoming.github_prefetch || null',
        'if (runtimeMeta) result.github_prefetch = runtimeMeta',
        'prefetchMeta',
        'attempted:',
        'usable:',
    ):
        assert item in index_js, f"GitHub prefetch boundary regression: {item}"

    print("hybrid_runtime self-test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
