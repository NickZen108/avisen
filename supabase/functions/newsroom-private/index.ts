import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createRemoteJWKSet, jwtVerify } from "npm:jose@5.9.6";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const JWKS = createRemoteJWKSet(new URL("https://token.actions.githubusercontent.com/.well-known/jwks"));
const EXPECTED_REPOSITORY = "NickZen108/avisen";
const EXPECTED_REF = "refs/heads/main";
const AUDIENCE = "morgentidende-v3";
const HARD_DAILY_LIMIT_DKK = 10;
const OPERATIONAL_DAILY_LIMIT_DKK = 9;

const jsonHeaders = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" };
const out = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: jsonHeaders });

function copenhagenDate() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Copenhagen", year: "numeric", month: "2-digit", day: "2-digit"
  }).formatToParts(new Date());
  const get = (type: string) => parts.find((x) => x.type === type)?.value || "";
  return `${get("year")}-${get("month")}-${get("day")}`;
}

async function authorize(req: Request) {
  const header = req.headers.get("authorization") || "";
  if (!header.startsWith("Bearer ")) throw new Error("missing bearer token");
  const token = header.slice(7);
  const { payload } = await jwtVerify(token, JWKS, {
    issuer: "https://token.actions.githubusercontent.com",
    audience: AUDIENCE,
  });
  if (payload.repository !== EXPECTED_REPOSITORY) throw new Error("wrong repository");
  if (payload.ref !== EXPECTED_REF) throw new Error("wrong ref");
  return payload;
}

async function rest(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers || {});
  headers.set("apikey", SERVICE_KEY);
  headers.set("authorization", `Bearer ${SERVICE_KEY}`);
  headers.set("content-type", "application/json");
  headers.set("prefer", headers.get("prefer") || "return=representation");
  const r = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, { ...init, headers });
  const text = await r.text();
  if (!r.ok) throw new Error(`supabase ${r.status}: ${text.slice(0, 800)}`);
  return text ? JSON.parse(text) : null;
}

async function rpc(name: string, body: unknown) {
  return await rest(`rpc/${name}`, { method: "POST", body: JSON.stringify(body) });
}

Deno.serve(async (req: Request) => {
  if (req.method === "GET" && new URL(req.url).pathname.endsWith("/health")) {
    return out({ ok: true, service: "newsroom-private", auth: "github-oidc", hard_daily_limit_dkk: HARD_DAILY_LIMIT_DKK });
  }
  if (req.method !== "POST") return out({ error: "POST required" }, 405);
  try {
    await authorize(req);
  } catch (e) {
    return out({ error: "unauthorized", detail: String(e?.message || e) }, 401);
  }
  try {
    const body = await req.json();
    const action = body?.action;
    if (action === "pull_inbox") {
      const limit = Math.min(20, Math.max(1, Number(body?.limit || 10)));
      const rows = await rest(`publisher_inbox?select=id,created_at,source,kind,priority,title,body,status,story_id,package_id,metadata&status=in.(new,commissioned)&order=priority.asc,created_at.asc&limit=${limit}`);
      return out({ ok: true, rows });
    }
    if (action === "set_inbox_status") {
      const id = String(body?.id || "");
      const status = String(body?.status || "");
      if (!/^[0-9a-f-]{36}$/i.test(id)) return out({ error: "bad id" }, 400);
      if (!["new","triaged","commissioned","parked","completed","rejected"].includes(status)) return out({ error: "bad status" }, 400);
      const patch: Record<string, unknown> = { status, updated_at: new Date().toISOString() };
      if (["completed","rejected"].includes(status)) patch.processed_at = new Date().toISOString();
      if (body?.story_id) patch.story_id = String(body.story_id);
      if (body?.package_id) patch.package_id = String(body.package_id);
      if (body?.pipeline_run_id) patch.pipeline_run_id = String(body.pipeline_run_id);
      const rows = await rest(`publisher_inbox?id=eq.${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(patch) });
      return out({ ok: true, rows });
    }
    if (action === "log_ai") {
      const row = body?.row || {};
      const required = ["run_id","stage","provider","model","status"];
      if (required.some((k) => !row[k])) return out({ error: "missing log fields" }, 400);
      const rows = await rest("ai_run_logs", { method: "POST", body: JSON.stringify({ ...row, created_at: new Date().toISOString() }) });
      return out({ ok: true, rows });
    }
    if (action === "budget_reserve") {
      const reservationId = String(body?.reservation_id || "");
      const amount = Number(body?.amount_dkk || 0);
      const budgetDate = copenhagenDate();
      if (!/^[A-Za-z0-9._:-]{8,180}$/.test(reservationId)) return out({ error: "bad reservation id" }, 400);
      if (!Number.isFinite(amount) || amount <= 0 || amount > HARD_DAILY_LIMIT_DKK) return out({ error: "bad reservation amount" }, 400);
      const result = await rpc("reserve_ai_budget", {
        p_reservation_id: reservationId,
        p_budget_date: budgetDate,
        p_amount_dkk: amount,
        p_run_id: String(body?.run_id || ""),
        p_stage: String(body?.stage || ""),
        p_operational_limit_dkk: OPERATIONAL_DAILY_LIMIT_DKK,
      });
      return out({ ok: Boolean(result?.ok), budget: result, budget_date: budgetDate }, result?.ok ? 200 : 429);
    }
    if (action === "budget_settle") {
      const reservationId = String(body?.reservation_id || "");
      const actual = Number(body?.actual_dkk || 0);
      if (!/^[A-Za-z0-9._:-]{8,180}$/.test(reservationId)) return out({ error: "bad reservation id" }, 400);
      if (!Number.isFinite(actual) || actual < 0) return out({ error: "bad actual amount" }, 400);
      const result = await rpc("settle_ai_budget", {
        p_reservation_id: reservationId,
        p_actual_dkk: actual,
        p_charge_reservation: body?.charge_reservation === true,
      });
      return out({ ok: true, budget: result });
    }
    if (action === "daily_budget") {
      const budgetDate = copenhagenDate();
      const rows = await rest(`ai_daily_budget?select=budget_date,spent_dkk,reserved_dkk,updated_at&budget_date=eq.${encodeURIComponent(budgetDate)}&limit=1`);
      const row = rows?.[0] || { budget_date: budgetDate, spent_dkk: 0, reserved_dkk: 0 };
      const spent = Number(row.spent_dkk || 0), reserved = Number(row.reserved_dkk || 0);
      return out({ ok: true, ...row, hard_limit_dkk: HARD_DAILY_LIMIT_DKK, operational_limit_dkk: OPERATIONAL_DAILY_LIMIT_DKK, remaining_hard_dkk: Math.max(0, HARD_DAILY_LIMIT_DKK - spent - reserved) });
    }
    if (action === "cost_summary") {
      const since = body?.since ? String(body.since) : null;
      let path = "ai_run_logs?select=story_id,stage,status,estimated_cost_dkk,created_at&order=created_at.desc&limit=5000";
      if (since) path += `&created_at=gte.${encodeURIComponent(since)}`;
      const rows = await rest(path);
      const total = (rows || []).reduce((s: number, r: any) => s + Math.max(0, Number(r.estimated_cost_dkk || 0)), 0);
      const published = new Set((rows || []).filter((r: any) => r.stage === "publish" && r.status === "success" && r.story_id).map((r: any) => r.story_id));
      const avg = published.size ? total / published.size : null;
      return out({ ok: true, total_cost_dkk: total, published_articles: published.size, avg_cost_dkk_per_published: avg, rows_count: (rows || []).length, since });
    }
    return out({ error: "unknown action" }, 400);
  } catch (e) {
    return out({ error: "backend failure", detail: String(e?.message || e) }, 500);
  }
});
