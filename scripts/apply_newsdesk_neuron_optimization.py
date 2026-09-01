#!/usr/bin/env python3
from pathlib import Path


def swap(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Expected snippet missing for {label}")
    return text.replace(old, new, 1)


def optimize_editorial() -> None:
    path = Path("cloudflare/newsdesk/src/editorial.js")
    text = path.read_text(encoding="utf-8")

    legacy_image = "const raw = await env.AI.run(IMAGE_MODEL, { prompt, seed: Math.floor(Math.random() * 100000) });"
    current_image = "const raw = await env.AI.run(IMAGE_MODEL, { prompt });"
    if legacy_image in text:
        text = text.replace(legacy_image, current_image, 1)

    text = swap(
        text,
        'const TEXT_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";',
        'const FAST_TEXT_MODEL = "@cf/meta/llama-3.1-8b-instruct-fast";\nconst STRONG_TEXT_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";',
        "model tier constants",
    )

    old_ai = '''async function aiJson(env, system, user, schema, maxTokens = 2800) {
  const raw = await env.AI.run(TEXT_MODEL, {
    messages: [{ role: "system", content: system }, { role: "user", content: user }],
    max_tokens: maxTokens, temperature: 0.15,
    response_format: { type: "json_schema", json_schema: schema },
  });
  return responseObject(raw);
}'''
    new_ai = '''async function aiJson(env, system, user, schema, maxTokens = 2800, model = STRONG_TEXT_MODEL, fallbackModel = null) {
  const request = {
    messages: [{ role: "system", content: system }, { role: "user", content: user }],
    max_tokens: maxTokens, temperature: 0.15,
    response_format: { type: "json_schema", json_schema: schema },
  };
  try {
    const raw = await env.AI.run(model, request);
    return responseObject(raw);
  } catch (error) {
    if (!fallbackModel || fallbackModel === model) throw error;
    console.warn("Workers AI structured-call fallback", model, "->", fallbackModel, String(error));
    const raw = await env.AI.run(fallbackModel, request);
    return responseObject(raw);
  }
}'''
    text = swap(text, old_ai, new_ai, "tier-aware structured AI helper")

    text = swap(
        text,
        'signal_indexes: { type: "array", items: { type: "integer" }, minItems: 0, maxItems: 8 },',
        'signal_indexes: { type: "array", items: { type: "integer" }, minItems: 0, maxItems: 6 },',
        "assignment source cap",
    )

    old_summary = '''function signalSummary(scan) {
  return scan.signals.slice(0, 100).map((s, i) => ({ i, source: s.source, headline: s.headline, description: (s.description || "").slice(0, 500), url: s.url }));
}'''
    new_summary = '''function signalSummary(scan) {
  const clusterSizes = new Map((scan.exact_clusters || []).map((c) => [c.normalized, (c.sources || []).length]));
  const ranked = scan.signals.map((s, i) => ({
    s, i,
    cluster: clusterSizes.get(s.normalized) || 1,
    feedRank: Number.isInteger(s.feed_rank) ? s.feed_rank : 99,
    published: Date.parse(s.published_at || "") || 0,
  })).sort((a, b) =>
    b.cluster - a.cluster || a.feedRank - b.feedRank || b.published - a.published ||
    a.s.source.localeCompare(b.s.source, "da") || a.s.headline.localeCompare(b.s.headline, "da")
  );
  const perSource = new Map();
  const chosen = [];
  for (const item of ranked) {
    if (chosen.length >= 40) break;
    const used = perSource.get(item.s.source) || 0;
    if (used >= 6) continue;
    perSource.set(item.s.source, used + 1);
    chosen.push(item);
  }
  return chosen.map(({ s, i }) => ({ i, source: s.source, headline: s.headline, description: (s.description || "").slice(0, 360), url: s.url, published_at: s.published_at || null }));
}'''
    text = swap(text, old_summary, new_summary, "quality-preserving signal shortlist")

    changes = [
        (
            'return aiJson(env, system, JSON.stringify({ generated_at: scan.generated_at, signals: signalSummary(scan) }), assignmentSchema, 1600);',
            'return aiJson(env, system, JSON.stringify({ generated_at: scan.generated_at, signals: signalSummary(scan) }), assignmentSchema, 900, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);',
            "assignment model routing",
        ),
        (
            'const research = await aiJson(env, system, JSON.stringify({ assignment, sources }), researchSchema, 3000);',
            'const research = await aiJson(env, system, JSON.stringify({ assignment, sources }), researchSchema, 2200, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);',
            "research model routing",
        ),
        ('}), factCheckSchema, 3000);', '}), factCheckSchema, 2400);', "fact-check output cap"),
        (
            'return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), contradictions: dossier.contradictions, rationale: dossier.rationale }), deskRecheckSchema, 700);',
            'return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), contradictions: dossier.contradictions, rationale: dossier.rationale }), deskRecheckSchema, 450, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);',
            "desk recheck model routing",
        ),
        (
            'return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources }), articleSchema, 3800);',
            'return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources }), articleSchema, 3000);',
            "writer output cap",
        ),
        (
            'const raw = await aiJson(env, system, JSON.stringify({ assignment, claims: dossier.claims, contradictions: dossier.contradictions, article }), finalSchema, 1400);',
            'const raw = await aiJson(env, system, JSON.stringify({ assignment, claims: dossier.claims, contradictions: dossier.contradictions, article }), finalSchema, 900);',
            "final review output cap",
        ),
        (
            'return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), article, issues: fixable }), articleSchema, 3000);',
            'return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), article, issues: fixable }), articleSchema, 2400, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);',
            "repair model routing",
        ),
        (
            'runtime: "cloudflare-workers-ai", model: TEXT_MODEL, story_id: storyId, slug, article: canonical, ledger, approval,',
            'runtime: "cloudflare-workers-ai", model: STRONG_TEXT_MODEL, models: { fast: FAST_TEXT_MODEL, strong: STRONG_TEXT_MODEL, image: IMAGE_MODEL }, story_id: storyId, slug, article: canonical, ledger, approval,',
            "runtime model audit",
        ),
    ]
    for old, new, label in changes:
        text = swap(text, old, new, label)

    path.write_text(text, encoding="utf-8")


def optimize_index() -> None:
    path = Path("cloudflare/newsdesk/src/index.js")
    text = path.read_text(encoding="utf-8")

    legacy_media = "const media = clone.media; delete clone.media.base64; clone.media.url = publicMediaUrl(media.key);"
    current_media = "const media = { ...clone.media }; delete clone.media.base64; clone.media.url = publicMediaUrl(media.key);"
    if legacy_media in text:
        text = text.replace(legacy_media, current_media, 1)

    text = swap(
        text,
        "for (const block of blocks.slice(0, 28)) {",
        "for (const [feedRank, block] of blocks.slice(0, 28).entries()) {",
        "feed rank capture",
    )

    old_push = '''    const desc = block.match(/<(?:description|summary|content:encoded)(?:\\s[^>]*)?>([\\s\\S]*?)<\\/(?:description|summary|content:encoded)>/i);
    out.push({ source, headline, normalized: normalizeTitle(headline), description: desc ? decodeXml(desc[1]).slice(0, 1200) : "", url });'''
    new_push = '''    const desc = block.match(/<(?:description|summary|content:encoded)(?:\\s[^>]*)?>([\\s\\S]*?)<\\/(?:description|summary|content:encoded)>/i);
    const dateMatch = block.match(/<(?:pubDate|published|updated|dc:date)(?:\\s[^>]*)?>([\\s\\S]*?)<\\/(?:pubDate|published|updated|dc:date)>/i);
    const parsedDate = dateMatch ? Date.parse(decodeXml(dateMatch[1])) : NaN;
    const published_at = Number.isFinite(parsedDate) ? new Date(parsedDate).toISOString() : null;
    out.push({ source, headline, normalized: normalizeTitle(headline), description: desc ? decodeXml(desc[1]).slice(0, 1200) : "", url, feed_rank: feedRank, published_at });'''
    text = swap(text, old_push, new_push, "feed freshness metadata")

    text = swap(
        text,
        'schema_version: 3, runtime: "cloudflare-workers", generated_at: new Date().toISOString(), fingerprint,',
        'schema_version: 4, runtime: "cloudflare-workers", generated_at: new Date().toISOString(), fingerprint,',
        "scan schema bump",
    )

    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    optimize_editorial()
    optimize_index()
    print("Newsdesk neuron optimization applied or already present")
