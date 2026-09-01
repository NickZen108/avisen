#!/usr/bin/env python3
"""Regression checks for the hybrid GitHub/Cloudflare editorial architecture."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> int:
    thresholds = json.loads((ROOT / "config" / "pipeline-thresholds.json").read_text(encoding="utf-8"))
    assert thresholds["schema_version"] >= 2
    assert thresholds["evidence_policy"]["min_verified_material_claims"] == 1
    assert thresholds["evidence_policy"]["named_accused_crime_requires_primary"] is True
    assert thresholds["evidence_policy"]["discovery_only_never_evidence"] is True
    assert thresholds["evidence_policy"]["high_risk_scope"] == "content_flags_and_right_of_reply_not_category"
    assert thresholds["evidence_policy"]["named_accused_primary_scope"] == "all_categories"
    fact_stage = next(x for x in thresholds["stages"] if x["id"] == "fact_check")
    assert next(x for x in fact_stage["requirements"] if x["key"] == "min_verified_material_claims")["value"] == 1
    research_stage = next(x for x in thresholds["stages"] if x["id"] == "research")
    assert next(x for x in research_stage["requirements"] if x["key"] == "min_distinct_sources")["value"] == 1
    image_stage = next(x for x in thresholds["stages"] if x["id"] == "image")
    assert next(x for x in image_stage["requirements"] if x["key"] == "no_photo_is_soft")["value"] == 1
    assert next(x for x in image_stage["requirements"] if x["key"] == "documentary_first")["value"] == 1

    dispatch = load_module("dispatch", ROOT / "scripts" / "editorial_dispatch_gate.py")
    dispatch.self_test()
    prefetch = load_module("prefetch", ROOT / "scripts" / "github_source_prefetch.py")
    prefetch.self_test()
    pending_refresh = load_module("pending_refresh", ROOT / "scripts" / "refresh_pending_images.py")
    pending_refresh.self_test()

    sync = load_module("sync", ROOT / "scripts" / "sync_cloudflare_editorial.py")
    assert sync.authoritative_editorial({"name": "Reuters", "source_group": "wire-reuters"})
    assert sync.authoritative_editorial({"name": "Associated Press", "source_group": "wire-ap"})
    assert not sync.authoritative_editorial({"name": "NRK", "url": "https://www.nrk.no/sak"})
    assert sync.strong_editorial({"name": "NRK", "url": "https://www.nrk.no/sak"})
    assert sync.strong_editorial({"name": "Financial Times", "url": "https://www.ft.com/content/example"})
    assert not sync.strong_editorial({"name": "Example Blog", "url": "https://example.test/post"})
    assert not sync.high_risk_claim({"category": "Udland", "title": "Minister deltager i EU-møde", "standfirst": ""}, {"right_of_reply": {"required": False}}, {"claim": "Minister deltager i mødet"})
    assert sync.high_risk_claim({"category": "Krimi", "title": "Fem dømt", "standfirst": ""}, {"right_of_reply": {"required": False}}, {"claim": "Fem dømt for hvidvask"})
    assert not sync.high_risk_claim({"category": "Sundhed", "title": "Ny statistik om medicin", "standfirst": ""}, {"right_of_reply": {"required": False}}, {"claim": "Rapporten blev offentliggjort tirsdag"})
    assert sync.named_accused_crime_claim({"category": "Politik"}, {"claim": "Jens Jensen er sigtet i sagen"})
    assert sync.valid_documentary_image({
        "src": "https://example.test/photo.jpg",
        "source_url": "https://example.test/license",
        "image_type": "photo",
        "alt": "Dokumentarisk foto",
        "credit": "Example",
        "license": "CC BY 4.0",
        "context_type": "event",
    })
    assert sync.valid_documentary_image({
        "src": "https://example.test/station.jpg",
        "source_url": "https://example.test/license",
        "image_type": "photo",
        "alt": "Stationen",
        "credit": "Example",
        "license": "CC BY 4.0",
        "context_type": "archive",
        "caption": "Arkivfoto",
    })
    assert not sync.valid_documentary_image({
        "src": "https://example.test/station.jpg",
        "source_url": "https://example.test/license",
        "image_type": "photo",
        "alt": "Stationen",
        "credit": "Example",
        "license": "CC BY 4.0",
        "context_type": "archive",
    }), "Archive/context photo without caption must fail"
    assert not sync.valid_documentary_image({
        "src": "https://img.youtube.com/example.jpg",
        "source_url": "https://www.youtube.com/watch?v=example",
        "image_type": "video_still",
        "alt": "Video-still",
        "credit": "Video source",
        "license": "Citation basis",
        "context_type": "event",
        "caption": "Still fra video",
    }), "YouTube still without documented rights_basis must fail"
    assert not sync.valid_documentary_image({
        "src": "https://example.test/ai.jpg",
        "source_url": "https://example.test/source",
        "image_type": "illustration",
        "alt": "AI",
        "credit": "Morgentidende",
        "license": "Morgentidende",
    })
    pending = {
        "src": "/img/auto/pending.jpg",
        "source_url": "https://example.test/generated",
        "image_type": "illustration",
        "context_type": "illustration",
        "alt": "Illustration",
        "credit": "Illustration: Morgentidende",
        "license": "Morgentidende – AI-genereret illustration",
        "caption": "Illustration",
        "pending_image": True,
        "ai_generated": True,
        "contains_people": False,
        "people_style": "pencil_hatching",
        "photorealistic": False,
    }
    assert sync.valid_pending_illustration(pending)
    assert not sync.valid_pending_illustration({**pending, "image_type": "photo"})
    assert not sync.valid_pending_illustration({**pending, "context_type": "event"})
    assert not sync.valid_pending_illustration({**pending, "photorealistic": True})
    static_pending = {
        **pending,
        "ai_generated": False,
        "generator": "static_pencil_fallback",
        "license": "Morgentidende – statisk illustration",
    }
    assert sync.valid_pending_illustration(static_pending)
    assert not sync.valid_pending_illustration({**static_pending, "generator": "unknown"})

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
        'function validDocumentaryHero(media)',
        'function documentaryHeroFromSignals(selected = [])',
        'function contextualHeroFromSignals(selected = [])',
        'async function resolveDocumentaryHero(selected, assignment, research)',
        'async function findCommonsDocumentaryHero(assignment, article',
        'commonsLicenseAllowed',
        'image/jpeg',
        'async function generateTemporarySketch(env, assignment, article)',
        'function pendingSketchHero(imageKey, article, sketch)',
        'function staticPencilFallbackBase64()',
        'static_pencil_fallback',
        'structured_fallback_calls',
        'pending_image: true',
        'people_style: "pencil_hatching"',
        'NO photorealism',
        'temporary_sketch_allowed_after_scout: true',
        'static_sketch_fallback: true',
        'late_hold_for_no_photo: false',
        'function namedAccusedCrimeClaim(assignment, claim)',
        'function numericMaterialClaim(claim)',
        'media_strategy',
        'context_type: "archive"',
        'Arkivfoto – billedet viser ikke nødvendigvis selve hændelsen.',
    ]
    missing = [item for item in required if item not in js]
    assert not missing, f"Hybrid runtime regression: missing {missing}"
    assert 'hero_prompt' not in js.split('const articleSchema', 1)[1].split('const finalSchema', 1)[0], "Journalist schema must not spend output tokens on hero_prompt"
    assert 'hero_alt' not in js.split('const articleSchema', 1)[1].split('const finalSchema', 1)[0], "Journalist schema must not spend output tokens on hero_alt"
    assert 'if (!res.ok) return null' not in js, "Commons HTTP failure must continue to later queries"
    assert '["Krimi", "Sundhed"].includes(assignment?.category)' not in js, "Risk must be content-based, not category-based"
    assert js.count('await findCommonsDocumentaryHero(') <= 2, "One runtime scout plus helper definition only; no repeated post-Journalist Commons calls"
    assert 'required: Boolean(dossier.right_of_reply_required)' in js, "Ledger must preserve Research right-of-reply flag"

    assert 'flux-1-schnell' in js, "Temporary pending sketch requires the constrained image model"
    assert 'image_type: "illustration"' in js
    assert 'context_type: "illustration"' in js
    assert 'caption: "Illustration"' in js
    assert 'return { status: "hold", stage: "media"' not in js, "No-photo must not late-hold a verified article"

    index_js = (ROOT / "cloudflare" / "newsdesk" / "src" / "index.js").read_text(encoding="utf-8")
    for item in (
        'const INTERNAL_PATHS = new Set([',
        '"/run-editorial"',
        '"/candidates"',
        '"/editorial/latest"',
        '"/editorial/history"',
        '"/history"',
        'async function constantTimeTokenEqual(expected, supplied)',
        'env.EDITORIAL_RUN_TOKEN',
        'request.headers.get("authorization")',
        'request.headers.get("x-editorial-token")',
        'const authFailure = await authorizeInternal(request, env, url.pathname)',
        'status: 503',
        'status: 401',
    ):
        assert item in index_js, f"Newsdesk auth regression: {item}"
    health_block = index_js.split('if (url.pathname === "/health")', 1)[1].split('const authFailure', 1)[0]
    for forbidden in ("fingerprint", "slug", "ai_usage", "latest_editorial", "signal_count", "editorial_status"):
        assert forbidden not in health_block, f"Public health leaks internal field: {forbidden}"
    assert 'url.pathname.startsWith("/media/")' in index_js, "Known public media retrieval must remain available"
    assert index_js.index('const authFailure = await authorizeInternal') < index_js.index('if (url.pathname === "/candidates")'), "Internal routes must be guarded before routing"

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

    editorial_sync = (ROOT / ".github" / "workflows" / "cloudflare-editorial-sync.yml").read_text(encoding="utf-8")
    deploy_workflow = (ROOT / ".github" / "workflows" / "cloudflare-newsdesk-deploy.yml").read_text(encoding="utf-8")
    breaking_scan = (ROOT / ".github" / "workflows" / "breaking-scan.yml").read_text(encoding="utf-8")
    publication_sprint = (ROOT / ".github" / "workflows" / "publication-sprint-2026-09-01.yml").read_text(encoding="utf-8")
    scan_sync = (ROOT / "scripts" / "sync_cloudflare_scan.py").read_text(encoding="utf-8")
    editorial_importer = (ROOT / "scripts" / "sync_cloudflare_editorial.py").read_text(encoding="utf-8")
    for label, text in (
        ("editorial sync", editorial_sync),
        ("deploy smoke", deploy_workflow),
        ("breaking scan", breaking_scan),
        ("publication sprint", publication_sprint),
    ):
        assert "secrets.EDITORIAL_RUN_TOKEN" in text, f"{label} must source EDITORIAL_RUN_TOKEN from GitHub secrets"
    assert 'Authorization: Bearer $EDITORIAL_RUN_TOKEN' in editorial_sync
    assert 'Authorization: Bearer $EDITORIAL_RUN_TOKEN' in publication_sprint
    assert 'Missing required GitHub secret EDITORIAL_RUN_TOKEN' in editorial_sync
    assert 'Missing required GitHub secret EDITORIAL_RUN_TOKEN' in deploy_workflow
    assert 'Authorization": f"Bearer {token}"' in scan_sync
    assert 'EDITORIAL_RUN_TOKEN is required to fetch internal Newsdesk endpoints' in editorial_importer
    assert (ROOT / "cloudflare" / "newsdesk" / "AUTH.md").exists()

    print("hybrid_runtime self-test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
