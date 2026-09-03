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
    assert not (ROOT / "config" / "pipeline-thresholds.json").exists(), "Legacy parallel threshold policy must stay removed"

    dispatch = load_module("dispatch", ROOT / "scripts" / "editorial_cycle_selector.py")
    dispatch.self_test()
    categories = load_module("categories", ROOT / "scripts" / "normalize_categories.py")
    categories.self_test()
    prefetch = load_module("prefetch", ROOT / "scripts" / "github_source_prefetch.py")
    prefetch.self_test()
    pending_refresh = load_module("pending_refresh", ROOT / "scripts" / "refresh_pending_images.py")
    pending_refresh.self_test()

    # Evidence authority is canonical in evidence_policy.py. The sync layer imports
    # that policy rather than maintaining a second, drifting set of source helpers.
    policy = load_module("evidence_policy", ROOT / "scripts" / "evidence_policy.py")
    assert policy.authoritative_source({"name": "Reuters", "url": "https://www.reuters.com/world/example"})
    assert policy.authoritative_source({"name": "Associated Press", "url": "https://apnews.com/article/example"})
    assert policy.authoritative_source({"name": "NRK", "url": "https://www.nrk.no/sak"})
    assert policy.authoritative_source({"name": "Financial Times", "url": "https://www.ft.com/content/example"})
    assert not policy.authoritative_source({"name": "Example Blog", "url": "https://example.test/post"})
    assert policy.authoritative_source({"type": "expert", "authoritative_for": "macroeconomics", "url": "https://example.test/expert"})
    assert not policy.authoritative_source({"type": "expert", "url": "https://example.test/expert"})

    sync = load_module("sync", ROOT / "scripts" / "sync_cloudflare_editorial.py")
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
    non_ai_pending = {
        **pending,
        "ai_generated": False,
        "generator": "non_ai_placeholder",
        "license": "Morgentidende – placeholder",
    }
    assert not sync.valid_pending_illustration(non_ai_pending)

    js = (ROOT / "cloudflare" / "newsdesk" / "src" / "editorial.js").read_text(encoding="utf-8")
    required = [
        'function authoritativeEditorial(item)',
        'function strongEditorialSource(item)',
        'function normalizedSourceKind(item)',
        'function evidenceRulePass(assignment, research, claim, evidence)',
        '"wire-reuters", "wire-ap", "wire-afp", "wire-ritzau"',
        '["A", "B"].includes(assignment?.weight)',
        'final_editor_mode: review.mode || "ai"',
        'Discovery-only source crossed the Research/Fact-check boundary',
        'fetch_origin: "github-actions-prefetch"',
        'host === "reuters.com"',
        'source === "ap"',
        'feed_summary_only',
        'source_strength',
        'fact.decision = verified.length >= 1 && unsupported.length === 0 ? "publish" : "hold"',
        'function validDocumentaryHero(media)',
        'function documentaryHeroFromSignals(selected = [])',
        'function contextualHeroFromSignals(selected = [])',
        'async function resolveDocumentaryHero(selected, assignment, research)',
        'async function findCommonsDocumentaryHero(assignment, article',
        'commonsLicenseAllowed',
        'image/jpeg',
        'async function generateTemporarySketch(env, assignment, article)',
        'function pendingSketchHero(imageKey, article, sketch)',
        'structured_fallback_calls',
        'structured_fallback_by_stage',
        'function normalizedArticleFingerprint(article)',
        'const languageOnly = issues.every((x) => x.gate === "language")',
        'const researchSourceLimit = hasAuthoritative ? 3 : 4',
        'pending_image: true',
        'people_style: "pencil_hatching"',
        'NO photorealism',
        'temporary_sketch_allowed_after_scout: true',
        'static_sketch_fallback: false',
        'late_hold_for_no_photo: false',
        'function namedAccusedCrimeClaim(assignment, claim)',
        'function numericMaterialClaim(claim)',
        'media_strategy',
        'const contextType = isMap ? "map" : isSatellite ? "satellite" : "archive"',
        'Arkivfoto – billedet viser ikke nødvendigvis selve hændelsen.',
    ]
    missing = [item for item in required if item not in js]
    assert not missing, f"Hybrid runtime regression: missing {missing}"
    fact_schema = js.split('const factCheckSchema', 1)[1].split('const articleSchema', 1)[0]
    assert 'decision:' not in fact_schema, "Fact model must not spend output tokens on deterministic decision"
    assert 'rationale:' not in fact_schema, "Fact model must not spend output tokens on deterministic rationale"
    assert 'hero_prompt' not in js.split('const articleSchema', 1)[1].split('const finalSchema', 1)[0], "Journalist schema must not spend output tokens on hero_prompt"
    assert 'hero_alt' not in js.split('const articleSchema', 1)[1].split('const finalSchema', 1)[0], "Journalist schema must not spend output tokens on hero_alt"
    assert 'seo_title' not in js.split('const articleSchema', 1)[1].split('const finalSchema', 1)[0], "Journalist schema must not spend output tokens on SEO"
    assert 'hero_queries_' not in js, "Newsdesk must not spend output tokens on hero search queries"
    assert 'if (!res.ok) return null' not in js, "Commons HTTP failure must continue to later queries"
    assert '["Krimi", "Sundhed"].includes(assignment?.category)' not in js, "Risk must be content-based, not category-based"
    assert js.count('await findCommonsDocumentaryHero(') <= 2, "One runtime scout plus helper definition only; no repeated post-Journalist Commons calls"

    assert 'flux-1-schnell' in js, "Temporary pending sketch requires the constrained image model"
    assert 'image_type: "illustration"' in js
    assert 'context_type: "illustration"' in js
    assert 'caption: "Illustration"' in js
    assert 'return { status: "hold", stage: "media"' not in js, "No-photo must not late-hold a verified article"
    assert 'staticPencilFallbackBase64' not in js, "Static image placeholders must not exist in the runtime"

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
