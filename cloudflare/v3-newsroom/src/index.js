const OPENAI_PREFIX = "openai/";

function extractText(result) {
  if (!result) return "";
  if (typeof result === "string") return result;
  if (typeof result.output_text === "string") return result.output_text;
  if (typeof result.response === "string") return result.response;
  if (Array.isArray(result.choices) && result.choices.length) {
    const msg = result.choices[0]?.message;
    if (typeof msg?.content === "string") return msg.content;
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
    input_tokens: Number(u.input_tokens ?? u.prompt_tokens ?? 0) || 0,
    output_tokens: Number(u.output_tokens ?? u.completion_tokens ?? 0) || 0,
    cached_input_tokens: Number(details.cached_tokens ?? details.cache_read_tokens ?? 0) || 0,
  };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return Response.json({ ok: true, service: "morgentidende-v3-newsroom", ai: true });
    }
    if (request.method !== "POST" || url.pathname !== "/run") {
      return new Response("Not found", { status: 404 });
    }
    const auth = request.headers.get("authorization") || "";
    if (!env.RUN_TOKEN || auth !== `Bearer ${env.RUN_TOKEN}`) {
      return Response.json({ ok: false, error: "unauthorized" }, { status: 401 });
    }
    try {
      const body = await request.json();
      const model = String(body.model || "");
      const instructions = String(body.instructions || "");
      const textInput = String(body.input || "");
      const maxOutput = Math.max(64, Math.min(4000, Number(body.max_output_tokens || 800)));
      const images = Array.isArray(body.images) ? body.images.filter(Boolean).slice(0, 5) : [];
      const webSearch = body.web_search === true;
      const reasoning = ["none","low","medium","high"].includes(body.reasoning) ? body.reasoning : "low";

      const allowed = new Set([
        "openai/gpt-5.6-terra",
        "openai/gpt-5.6-sol",
        "openai/gpt-5.6-luna",
        "openai/gpt-5.4-mini",
        "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
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
        result = await env.AI.run(model, params);
      } else {
        result = await env.AI.run(model, {
          messages: [
            { role: "system", content: instructions },
            { role: "user", content: textInput },
          ],
          max_tokens: maxOutput,
          temperature: 0.15,
        });
      }

      const text = extractText(result);
      if (!text) {
        return Response.json({ ok: false, error: "empty model response", usage: usageOf(result) }, { status: 502 });
      }
      return Response.json({ ok: true, text, usage: usageOf(result) });
    } catch (err) {
      return Response.json({ ok: false, error: String(err?.message || err) }, { status: 502 });
    }
  },
};
