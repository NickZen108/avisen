#!/usr/bin/env python3
from pathlib import Path

EDITORIAL = Path('cloudflare/newsdesk/src/editorial.js')
INDEX = Path('cloudflare/newsdesk/src/index.js')

HELPERS = r'''
const TEXT_NEURON_RATES = {
  "@cf/meta/llama-3.1-8b-instruct-fast": { input: 4119, output: 34868, basis: "8B fast pricing-equivalent estimate" },
  "@cf/meta/llama-3.1-8b-instruct-fp8-fast": { input: 4119, output: 34868, basis: "published Cloudflare rate" },
  "@cf/meta/llama-3.3-70b-instruct-fp8-fast": { input: 26668, output: 204805, basis: "published Cloudflare rate" },
};
function usageRecord(model, raw) {
  const u = raw?.usage || raw?.response?.usage || raw?.result?.usage || null;
  if (model === IMAGE_MODEL) {
    // Flux Schnell defaults to four steps. Cloudflare bills 9.6 neurons/step plus
    // 4.8 neurons per 512x512 tile. Tile count is not surfaced by this binding,
    // so 43.2 is a transparent minimum estimate (one tile + four steps).
    return { model, kind: "image", prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, estimated_neurons: 43.2, estimate_only: true, basis: "minimum: 1 tile + 4 default steps" };
  }
  if (!u) return { model, kind: "text", metered: false, estimated_neurons: null };
  const prompt = Number(u.prompt_tokens ?? u.input_tokens ?? 0) || 0;
  const completion = Number(u.completion_tokens ?? u.output_tokens ?? 0) || 0;
  const total = Number(u.total_tokens ?? (prompt + completion)) || (prompt + completion);
  const rates = TEXT_NEURON_RATES[model];
  const neurons = rates ? (prompt * rates.input + completion * rates.output) / 1_000_000 : null;
  return { model, kind: "text", prompt_tokens: prompt, completion_tokens: completion, total_tokens: total, estimated_neurons: neurons, estimate_only: true, basis: rates?.basis || "rate unavailable" };
}
function trackedAiEnv(env, events) {
  const trackedAI = {
    run: async (model, input, options) => {
      const raw = await env.AI.run(model, input, options);
      events.push(usageRecord(model, raw));
      return raw;
    },
  };
  return new Proxy(env, { get(target, prop, receiver) { return prop === "AI" ? trackedAI : Reflect.get(target, prop, receiver); } });
}
function summarizeAiUsage(events) {
  const text = events.filter((x) => x.kind === "text");
  const knownNeurons = events.filter((x) => Number.isFinite(x.estimated_neurons));
  const byModel = {};
  for (const item of events) {
    const row = byModel[item.model] || { calls: 0, prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, estimated_neurons: 0 };
    row.calls += 1;
    row.prompt_tokens += item.prompt_tokens || 0;
    row.completion_tokens += item.completion_tokens || 0;
    row.total_tokens += item.total_tokens || 0;
    if (Number.isFinite(item.estimated_neurons)) row.estimated_neurons += item.estimated_neurons;
    byModel[item.model] = row;
  }
  return {
    calls: events.length,
    text_calls: text.length,
    image_calls: events.filter((x) => x.kind === "image").length,
    prompt_tokens: text.reduce((n, x) => n + (x.prompt_tokens || 0), 0),
    completion_tokens: text.reduce((n, x) => n + (x.completion_tokens || 0), 0),
    total_tokens: text.reduce((n, x) => n + (x.total_tokens || 0), 0),
    estimated_neurons: knownNeurons.reduce((n, x) => n + x.estimated_neurons, 0),
    complete_token_telemetry: text.every((x) => x.metered !== false),
    neuron_values_are_estimates: true,
    by_model: byModel,
  };
}
'''


def patch_editorial():
    text = EDITORIAL.read_text(encoding='utf-8')
    if 'function summarizeAiUsage(events)' not in text:
        marker = 'export async function runEditorialCycle(env, scan) {'
        if marker not in text:
            raise RuntimeError('runEditorialCycle marker missing')
        text = text.replace(marker, HELPERS + '\n' + marker, 1)
    if 'const aiUsageEvents = [];' not in text:
        old = 'export async function runEditorialCycle(env, scan) {\n  const startedAt = nowIso();'
        new = 'export async function runEditorialCycle(env, scan) {\n  const aiUsageEvents = [];\n  env = trackedAiEnv(env, aiUsageEvents);\n  let result;\n  try {\n    result = await (async () => {\n  const startedAt = nowIso();'
        if old not in text:
            raise RuntimeError('cycle start marker missing')
        text = text.replace(old, new, 1)
        tail = '\n}\n\nexport function editorialDue'
        idx = text.rfind(tail)
        if idx < 0:
            raise RuntimeError('cycle tail marker missing')
        replacement = '\n    })();\n  } catch (error) {\n    error.ai_usage = summarizeAiUsage(aiUsageEvents);\n    throw error;\n  }\n  result.ai_usage = summarizeAiUsage(aiUsageEvents);\n  return result;\n}\n\nexport function editorialDue'
        text = text[:idx] + replacement + text[idx + len(tail):]
    EDITORIAL.write_text(text, encoding='utf-8')


def patch_index():
    text = INDEX.read_text(encoding='utf-8')
    old = 'const failed = { status: "hold", stage: "runtime-error", checked_at: new Date().toISOString(), generated_at: new Date().toISOString(), scan_fingerprint: scan.fingerprint, reason: String(error) };'
    new = 'const failed = { status: "hold", stage: "runtime-error", checked_at: new Date().toISOString(), generated_at: new Date().toISOString(), scan_fingerprint: scan.fingerprint, reason: String(error), ai_usage: error?.ai_usage || null };'
    if new not in text:
        if old not in text:
            raise RuntimeError('runtime error marker missing')
        text = text.replace(old, new, 1)
    INDEX.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    patch_editorial()
    patch_index()
    print('AI usage telemetry applied or already present')
