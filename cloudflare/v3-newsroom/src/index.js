const OPENAI_PREFIX = "openai/";
const GATEWAY_OPTIONS = { gateway: { id: "default" } };
const GEMMA_VISION = "@cf/google/gemma-4-26b-a4b-it";
const QWEN_TEXT = "@cf/qwen/qwen3-30b-a3b-fp8";
const BGE_M3 = "@cf/baai/bge-m3";
const FLUX_SCHNELL = "@cf/black-forest-labs/flux-1-schnell";

function extractText(result) {
  if (!result) return "";
  if (typeof result === "string") return result;
  if (typeof result.output_text === "string") return result.output_text;
  if (typeof result.response === "string") return result.response;
  if (Array.isArray(result.choices) && result.choices.length) {
    const msg = result.choices[0]?.message;
    if (typeof msg?.content === "string") return msg.content;
    if (Array.isArray(msg?.content)) {
      return msg.content.map((x) => x?.text || x?.content || "").filter(Boolean).join("\n");
    }
  }
  if (Array.isArray(result.output)) {
    const parts = [];
    for (const item of result.output) {
      if (!Array.isArray(item?.content)) continue;
      for (const c of item.content) {
        if (typeof c?.text === "string") parts.push(c.text);
        else if (typeof c?.output_text === "string") parts.push(c.output_text);
      }
    }
    if (parts.length) return parts.join("\n");
  }
  return "";
}

function usageOf(result) {
  const u = result?.usage || {};
  const details = u.input_tokens_details || u.prompt_tokens_details || {};
  return {
    input_tokens: Number(u.input_tokens ?? u.prompt_tokens ?? u.total_tokens ?? 0) || 0,
    output_tokens: Number(u.output_tokens ?? u.completion_tokens ?? 0) || 0,
    cached_input_tokens: Number(details.cached_tokens ?? details.cache_read_tokens ?? 0) || 0,
  };
}

function authorized(request, env) {
  const auth = request.headers.get("authorization") || "";
  return Boolean(env.RUN_TOKEN && auth === `Bearer ${env.RUN_TOKEN}`);
}

async function runText(body, env) {
  const model = String(body.model || "");
  const instructions = String(body.instructions || "");
  const textInput = String(body.input || "");
  const maxOutput = Math.max(64, Math.min(4000, Number(body.max_output_tokens || 800)));
  const images = Array.isArray(body.images) ? body.images.filter(Boolean).slice(0, 5) : [];
  const webSearch = body.web_search === true;
  const reasoning = ["none", "low", "medium", "high"].includes(body.reasoning) ? body.reasoning : "low";

  const allowed = new Set([
    "openai/gpt-5.6-terra",
    "openai/gpt-5.6-sol",
    QWEN_TEXT,
    GEMMA_VISION,
  ]);
  if (!allowed.has(model)) {
    return Response.json({ ok: false, error: "model not allowlisted" }, { status: 400 });
  }

  let result;
  if (model.startsWith(OPENAI_PREFIX)) {
    let input = textInput;
    if (images.length) {
      input = [{
        role: "user",
        content: [
          { type: "input_text", text: textInput },
          ...images.map((image_url) => ({ type: "input_image", image_url })),
        ],
      }];
    }
    const params = {
      input,
      instructions,
      max_output_tokens: maxOutput,
      reasoning: { effort: reasoning },
      text: { format: { type: "text" }, verbosity: "low" },
    };
    if (webSearch) params.tools = [{ type: "web_search_preview" }];
    result = await env.AI.run(model, params, GATEWAY_OPTIONS);
  } else if (model === GEMMA_VISION && images.length) {
    const content = [
      { type: "text", text: `${instructions}\n\n${textInput}` },
      ...images.map((image_url) => ({ type: "image_url", image_url: { url: image_url } })),
    ];
    result = await env.AI.run(model, {
      messages: [{ role: "user", content }],
      max_tokens: maxOutput,
      temperature: 0.1,
      chat_template_kwargs: { enable_thinking: reasoning !== "none" && reasoning !== "low" },
    });
  } else {
    result = await env.AI.run(model, {
      messages: [
        { role: "system", content: instructions },
        { role: "user", content: textInput },
      ],
      max_tokens: maxOutput,
      temperature: 0.1,
    });
  }

  const text = extractText(result);
  if (!text) {
    return Response.json({ ok: false, error: "empty model response", usage: usageOf(result) }, { status: 502 });
  }
  return Response.json({ ok: true, text, usage: usageOf(result), gateway_log_id: env.AI.aiGatewayLogId || null });
}

async function runEmbed(body, env) {
  const model = String(body.model || "");
  if (model !== BGE_M3) {
    return Response.json({ ok: false, error: "embedding model not allowlisted" }, { status: 400 });
  }
  const texts = Array.isArray(body.texts) ? body.texts.map(String).filter(Boolean).slice(0, 128) : [];
  if (!texts.length) {
    return Response.json({ ok: false, error: "texts required" }, { status: 400 });
  }
  const result = await env.AI.run(model, { text: texts });
  const data = Array.isArray(result?.data) ? result.data : [];
  if (!data.length) {
    return Response.json({ ok: false, error: "empty embeddings", usage: usageOf(result) }, { status: 502 });
  }
  return Response.json({ ok: true, data, usage: usageOf(result) });
}

async function runImage(body, env) {
  const model = String(body.model || "");
  if (model !== FLUX_SCHNELL) {
    return Response.json({ ok: false, error: "image model not allowlisted" }, { status: 400 });
  }
  const prompt = String(body.prompt || "").trim().slice(0, 2048);
  if (!prompt) return Response.json({ ok: false, error: "prompt required" }, { status: 400 });
  const steps = Math.max(1, Math.min(8, Number(body.steps || 4)));
  const result = await env.AI.run(model, {
    prompt,
    steps,
    seed: Math.floor(Math.random() * 2147483647),
  });
  if (!result?.image) {
    return Response.json({ ok: false, error: "empty image response" }, { status: 502 });
  }
  return Response.json({ ok: true, image: result.image, steps });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return Response.json({
        ok: true,
        service: "morgentidende-v3-newsroom",
        native_workers_ai: true,
        chain: {
          scan_embedding: BGE_M3,
          desk: QWEN_TEXT,
          media: GEMMA_VISION,
          image_generator: FLUX_SCHNELL,
        },
      });
    }
    if (request.method !== "POST" || !["/run", "/embed", "/image"].includes(url.pathname)) {
      return new Response("Not found", { status: 404 });
    }
    if (!authorized(request, env)) {
      return Response.json({ ok: false, error: "unauthorized" }, { status: 401 });
    }
    try {
      const body = await request.json();
      if (url.pathname === "/embed") return await runEmbed(body, env);
      if (url.pathname === "/image") return await runImage(body, env);
      return await runText(body, env);
    } catch (err) {
      return Response.json({ ok: false, error: String(err?.message || err) }, { status: 502 });
    }
  },
};
