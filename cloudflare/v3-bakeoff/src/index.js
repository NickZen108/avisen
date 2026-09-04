const ALLOWED = new Set([
  "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
  "@cf/zai-org/glm-4.7-flash",
  "@cf/qwen/qwen3-30b-a3b-fp8",
  "@cf/openai/gpt-oss-20b",
  "@cf/zai-org/glm-5.3-flash",
  "@cf/qwen/qwen3.8-27b",
]);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return Response.json({ ok: true, service: "morgentidende-v3-bakeoff" });
    }
    if (request.method !== "POST" || url.pathname !== "/run") {
      return new Response("not found", { status: 404 });
    }
    const auth = request.headers.get("authorization") || "";
    if (!env.BAKEOFF_TOKEN || auth !== `Bearer ${env.BAKEOFF_TOKEN}`) {
      return Response.json({ ok: false, error: "unauthorized" }, { status: 401 });
    }
    let body;
    try { body = await request.json(); } catch (_) {
      return Response.json({ ok: false, error: "invalid-json" }, { status: 400 });
    }
    const model = String(body?.model || "");
    if (!ALLOWED.has(model)) return Response.json({ ok: false, error: "model-not-allowed" }, { status: 400 });
    const input = {
      messages: Array.isArray(body?.messages) ? body.messages : [],
      max_tokens: Number.isInteger(body?.max_tokens) ? body.max_tokens : 700,
      temperature: typeof body?.temperature === "number" ? body.temperature : 0.2,
    };
    try {
      const result = await env.AI.run(model, input);
      return Response.json({ ok: true, result });
    } catch (error) {
      return Response.json({ ok: false, error: String(error) }, { status: 500 });
    }
  },
};
