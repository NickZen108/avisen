import { DurableObject } from "cloudflare:workers";
import { editorialDue, publicMediaUrl, runEditorialCycle } from "./editorial.js";

const FEEDS = [
  { name: "DR", url: "https://www.dr.dk/nyheder/service/feeds/allenyheder" },
  { name: "TV2", url: "https://services.tv2.dk/api/feeds/nyheder/rss" },
  { name: "The Local Denmark", url: "https://feeds.thelocal.com/rss/dk" },
  { name: "BBC World", url: "https://feeds.bbci.co.uk/news/world/rss.xml" },
  { name: "BBC Europe", url: "https://feeds.bbci.co.uk/news/world/europe/rss.xml" },
  { name: "Euronews", url: "https://www.euronews.com/rss?level=theme&name=news" },
  { name: "Guardian World", url: "https://www.theguardian.com/world/rss" },
  { name: "Al Jazeera", url: "https://www.aljazeera.com/xml/rss/all.xml" },
];

const jsonHeaders = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-robots-tag": "noindex, nofollow",
};

function normalizeTitle(value) {
  return value.toLocaleLowerCase("da-DK").normalize("NFKC")
    .replace(/[^a-z0-9æøåäöüéèáàíìóòúùß ]+/giu, " ").replace(/\s+/g, " ").trim();
}
function decodeXml(value) {
  return String(value || "").replace(/<!\[CDATA\[([\s\S]*?)\]\]>/gi, "$1").replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/\s+/g, " ").trim();
}
function extractItems(xml, source) {
  const blocks = xml.match(/<(?:item|entry)\b[\s\S]*?<\/(?:item|entry)>/gi) || [];
  const out = [];
  for (const block of blocks.slice(0, 28)) {
    const titleMatch = block.match(/<title(?:\s[^>]*)?>([\s\S]*?)<\/title>/i);
    if (!titleMatch) continue;
    const headline = decodeXml(titleMatch[1]);
    if (!headline || headline === source) continue;
    let url = null;
    const linkText = block.match(/<link(?:\s[^>]*)?>([\s\S]*?)<\/link>/i);
    const linkHref = block.match(/<link\b[^>]*href=["']([^"']+)["'][^>]*\/?>/i);
    const guid = block.match(/<guid(?:\s[^>]*)?>([\s\S]*?)<\/guid>/i);
    if (linkHref) url = decodeXml(linkHref[1]); else if (linkText) url = decodeXml(linkText[1]); else if (guid) url = decodeXml(guid[1]);
    if (url && !/^https?:\/\//i.test(url)) url = null;
    const desc = block.match(/<(?:description|summary|content:encoded)(?:\s[^>]*)?>([\s\S]*?)<\/(?:description|summary|content:encoded)>/i);
    out.push({ source, headline, normalized: normalizeTitle(headline), description: desc ? decodeXml(desc[1]).slice(0, 1200) : "", url });
  }
  return out;
}
async function sha256Hex(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((x) => x.toString(16).padStart(2, "0")).join("");
}
async function fetchFeed(feed) {
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(feed.url, { headers: { "user-agent": "MorgentidendeNewsdesk/3.0 (+https://morgentidende.nicolaipetersen108.workers.dev/)" }, signal: controller.signal });
    if (!response.ok) return { source: feed.name, ok: false, status: response.status, signals: [] };
    const xml = await response.text();
    return { source: feed.name, ok: true, status: response.status, signals: extractItems(xml, feed.name) };
  } catch (error) { return { source: feed.name, ok: false, status: null, error: String(error), signals: [] }; }
  finally { clearTimeout(timer); }
}
async function buildScan() {
  const fetched = await Promise.all(FEEDS.map(fetchFeed));
  const signals = fetched.flatMap((x) => x.signals);
  signals.sort((a, b) => a.normalized.localeCompare(b.normalized, "da") || a.source.localeCompare(b.source, "da") || a.headline.localeCompare(b.headline, "da"));
  const stable = signals.map(({ source, headline, normalized, description, url }) => ({ source, headline, normalized, description, url }));
  const fingerprint = await sha256Hex(JSON.stringify(stable));
  const grouped = new Map();
  for (const signal of signals) { const items = grouped.get(signal.normalized) || []; items.push(signal); grouped.set(signal.normalized, items); }
  const exactClusters = [];
  for (const [normalized, items] of grouped.entries()) {
    const sources = [...new Set(items.map((x) => x.source))].sort();
    if (sources.length >= 2) exactClusters.push({ normalized, sources, headlines: items.map((x) => x.headline), note: "Exact normalized headline match only; not proof of independent sourcing." });
  }
  return {
    schema_version: 3, runtime: "cloudflare-workers", generated_at: new Date().toISOString(), fingerprint,
    signal_count: signals.length, feeds: fetched.map(({ source, ok, status, error }) => ({ source, ok, status, error: error || null })),
    signals, exact_clusters: exactClusters, editorial_status: "UNRANKED", warning: "Inventory only until the independent editorial pipeline passes.",
  };
}

function base64ToBytes(base64) {
  const binary = atob(base64); const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

export class NewsroomState extends DurableObject {
  async fetch(request) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/store") {
      const incoming = await request.json(); const previous = await this.ctx.storage.get("latest");
      if (!previous || previous.fingerprint !== incoming.fingerprint) {
        await this.ctx.storage.put("latest", incoming);
        const history = (await this.ctx.storage.get("history")) || [];
        history.unshift({ generated_at: incoming.generated_at, fingerprint: incoming.fingerprint, signal_count: incoming.signal_count });
        await this.ctx.storage.put("history", history.slice(0, 288));
      } else incoming.generated_at = previous.generated_at;
      await this.ctx.storage.put("last_attempt_at", new Date().toISOString());
      return Response.json({ ok: true, changed: !previous || previous.fingerprint !== incoming.fingerprint }, { headers: jsonHeaders });
    }
    if (request.method === "POST" && url.pathname === "/editorial/store") {
      const incoming = await request.json();
      await this.ctx.storage.put("last_editorial_at", incoming.generated_at || incoming.checked_at || new Date().toISOString());
      await this.ctx.storage.put("latest_editorial", incoming);
      const history = (await this.ctx.storage.get("editorial_history")) || [];
      history.unshift({ generated_at: incoming.generated_at || incoming.checked_at, status: incoming.status, stage: incoming.stage || "approved", slug: incoming.slug || null, reason: incoming.reason || null, scan_fingerprint: incoming.scan_fingerprint || null });
      await this.ctx.storage.put("editorial_history", history.slice(0, 96));
      return Response.json({ ok: true }, { headers: jsonHeaders });
    }
    if (request.method === "POST" && url.pathname === "/media/store") {
      const incoming = await request.json(); const key = String(incoming.key || ""); const b64 = String(incoming.base64 || "");
      if (!key || !b64) return new Response("bad media", { status: 400 });
      const chunkSize = 90000; const chunks = [];
      for (let i = 0; i < b64.length; i += chunkSize) chunks.push(b64.slice(i, i + chunkSize));
      await this.ctx.storage.put(`media:${key}:meta`, { chunks: chunks.length, content_type: incoming.content_type || "image/jpeg" });
      for (let i = 0; i < chunks.length; i++) await this.ctx.storage.put(`media:${key}:${i}`, chunks[i]);
      return Response.json({ ok: true, chunks: chunks.length }, { headers: jsonHeaders });
    }
    if (url.pathname === "/media/get") {
      const key = url.searchParams.get("key") || ""; const meta = await this.ctx.storage.get(`media:${key}:meta`);
      if (!meta) return new Response("not found", { status: 404 });
      let b64 = ""; for (let i = 0; i < meta.chunks; i++) b64 += (await this.ctx.storage.get(`media:${key}:${i}`)) || "";
      return new Response(base64ToBytes(b64), { headers: { "content-type": meta.content_type, "cache-control": "public, max-age=31536000, immutable", "x-robots-tag": "noindex" } });
    }
    if (url.pathname === "/history") return Response.json((await this.ctx.storage.get("history")) || [], { headers: jsonHeaders });
    if (url.pathname === "/editorial/history") return Response.json((await this.ctx.storage.get("editorial_history")) || [], { headers: jsonHeaders });
    if (url.pathname === "/editorial") return Response.json({ latest: (await this.ctx.storage.get("latest_editorial")) || null, last_editorial_at: (await this.ctx.storage.get("last_editorial_at")) || null }, { headers: jsonHeaders });
    const latest = await this.ctx.storage.get("latest"); const lastAttempt = await this.ctx.storage.get("last_attempt_at");
    return Response.json({ latest: latest || null, last_attempt_at: lastAttempt || null }, { headers: jsonHeaders });
  }
}

function stateStub(env) { return env.NEWSROOM_STATE.get(env.NEWSROOM_STATE.idFromName("global")); }
async function storeScan(env, scan) { return stateStub(env).fetch("https://state/store", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(scan) }); }
async function getState(env, path = "/state") { return stateStub(env).fetch(`https://state${path}`); }
async function persistEditorial(env, result) {
  const clone = structuredClone(result);
  if (clone.status === "approved" && clone.media?.base64) {
    const media = clone.media; delete clone.media.base64; clone.media.url = publicMediaUrl(media.key);
    await stateStub(env).fetch("https://state/media/store", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(media) });
  }
  await stateStub(env).fetch("https://state/editorial/store", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(clone) });
  return clone;
}
async function maybeRunEditorial(env, scan, force = false) {
  const status = await (await getState(env, "/editorial")).json();
  if (!force && !editorialDue(status.last_editorial_at)) return status.latest || { status: "idle", reason: "Editorial cadence not due" };
  if (!force && status.latest?.scan_fingerprint === scan.fingerprint) {
    const held = { status: "hold", stage: "newsdesk", checked_at: new Date().toISOString(), generated_at: new Date().toISOString(), scan_fingerprint: scan.fingerprint, reason: "Ingen ændring i kildeinventaret siden forrige redaktionelle cyklus" };
    return persistEditorial(env, held);
  }
  try { return persistEditorial(env, await runEditorialCycle(env, scan)); }
  catch (error) {
    const failed = { status: "hold", stage: "runtime-error", checked_at: new Date().toISOString(), generated_at: new Date().toISOString(), scan_fingerprint: scan.fingerprint, reason: String(error) };
    return persistEditorial(env, failed);
  }
}

export default {
  async scheduled(_controller, env, ctx) {
    ctx.waitUntil((async () => {
      const scan = await buildScan(); await storeScan(env, scan); await maybeRunEditorial(env, scan, false);
    })());
  },
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/health") {
      const state = await (await getState(env)).json(); const editorial = await (await getState(env, "/editorial")).json();
      return Response.json({ ok: true, service: "morgentidende-newsdesk", runtime: "cloudflare-workers", ai_runtime: Boolean(env.AI), latest_generated_at: state.latest?.generated_at || null, last_attempt_at: state.last_attempt_at || null, signal_count: state.latest?.signal_count || 0, last_editorial_at: editorial.last_editorial_at || null, editorial_status: editorial.latest?.status || null }, { headers: jsonHeaders });
    }
    if (url.pathname === "/candidates") {
      const state = await (await getState(env)).json();
      if (!state.latest) { const scan = await buildScan(); await storeScan(env, scan); return Response.json(scan, { headers: jsonHeaders }); }
      return Response.json(state.latest, { headers: jsonHeaders });
    }
    if (url.pathname === "/editorial/latest") { const state = await (await getState(env, "/editorial")).json(); return Response.json(state.latest || { status: "none" }, { headers: jsonHeaders }); }
    if (url.pathname === "/editorial/history") return getState(env, "/editorial/history");
    if (url.pathname === "/run-editorial" && request.method === "POST") {
      const state = await (await getState(env)).json(); const scan = state.latest || await buildScan(); if (!state.latest) await storeScan(env, scan);
      return Response.json(await maybeRunEditorial(env, scan, true), { headers: jsonHeaders });
    }
    if (url.pathname.startsWith("/media/")) {
      const key = decodeURIComponent(url.pathname.slice("/media/".length)); return stateStub(env).fetch(`https://state/media/get?key=${encodeURIComponent(key)}`);
    }
    if (url.pathname === "/history") return getState(env, "/history");
    return new Response("Morgentidende Newsdesk runtime\n", { headers: { "content-type": "text/plain; charset=utf-8", "x-robots-tag": "noindex, nofollow" } });
  },
};
