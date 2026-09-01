import { DurableObject } from "cloudflare:workers";
import { editorialDue, publicMediaUrl, runEditorialCycle } from "./editorial.js";

const FEEDS = [
  // Broad/news sources. These may be used as normal secondary reporting.
  { name: "DR", url: "https://www.dr.dk/nyheder/service/feeds/allenyheder", source_class: "core_news", region: "DK", priority: 4, limit: 24 },
  { name: "TV2", url: "https://services.tv2.dk/api/feeds/nyheder/rss", source_class: "core_news", region: "DK", priority: 4, limit: 24 },
  { name: "The Local Denmark", url: "https://feeds.thelocal.com/rss/dk", source_class: "news", region: "DK", priority: 3, limit: 18 },
  { name: "NRK", url: "https://www.nrk.no/toppsaker.rss", source_class: "news", region: "NO", priority: 3, limit: 18 },
  { name: "SVT", url: "https://www.svt.se/nyheter/rss.xml", source_class: "news", region: "SE", priority: 3, limit: 18 },
  { name: "BBC World", url: "https://feeds.bbci.co.uk/news/world/rss.xml", source_class: "core_news", region: "UK", priority: 4, limit: 22 },
  { name: "BBC Europe", url: "https://feeds.bbci.co.uk/news/world/europe/rss.xml", source_class: "core_news", region: "EU", priority: 4, limit: 22 },
  { name: "Euronews", url: "https://www.euronews.com/rss?level=theme&name=news", source_class: "news", region: "EU", priority: 3, limit: 18 },
  { name: "Politico Europe", url: "https://www.politico.eu/feed/", source_class: "news", region: "EU", priority: 3, limit: 18 },
  { name: "DW", url: "https://rss.dw.com/rdf/rss-en-all", source_class: "news", region: "DE", priority: 3, limit: 18 },
  { name: "France 24", url: "https://www.france24.com/en/rss", source_class: "news", region: "FR", priority: 3, limit: 18 },
  { name: "Guardian World", url: "https://www.theguardian.com/world/rss", source_class: "news", region: "UK", priority: 3, limit: 18 },
  { name: "Sky World", url: "https://feeds.skynews.com/feeds/rss/world.xml", source_class: "news", region: "UK", priority: 3, limit: 18 },
  { name: "Al Jazeera", url: "https://www.aljazeera.com/xml/rss/all.xml", source_class: "news", region: "WORLD", priority: 3, limit: 18 },

  // Perspective/discovery sources. Valuable as tips and agenda discovery, but never
  // sufficient verification merely because they are separate URLs/sites.
  { name: "Indblik", url: "https://indblik.dk/feed/", source_class: "perspective_discovery", region: "DK", priority: 2, limit: 12, discovery_only: true },
  { name: "Document.no", url: "https://www.document.no/feed", source_class: "perspective_discovery", region: "NO", priority: 2, limit: 12, discovery_only: true },
  { name: "Timbro", url: "https://timbro.se/feed/", source_class: "perspective_discovery", region: "SE", priority: 2, limit: 10, discovery_only: true },
  { name: "Achgut", url: "https://www.achgut.com/rss2", source_class: "perspective_discovery", region: "DE", priority: 2, limit: 12, discovery_only: true },
  { name: "Tichys Einblick", url: "https://www.tichyseinblick.de/feed/", source_class: "perspective_discovery", region: "DE", priority: 2, limit: 12, discovery_only: true },
  { name: "Causeur", url: "https://www.causeur.fr/feed", source_class: "perspective_discovery", region: "FR", priority: 2, limit: 12, discovery_only: true },
  { name: "Contrepoints", url: "https://contrepoints.org/feed/", source_class: "perspective_discovery", region: "FR", priority: 2, limit: 12, discovery_only: true },
  { name: "Spiked", url: "https://www.spiked-online.com/feed/", source_class: "perspective_discovery", region: "UK", priority: 2, limit: 12, discovery_only: true },
  { name: "CapX", url: "https://capx.co/feed/", source_class: "perspective_discovery", region: "UK", priority: 2, limit: 12, discovery_only: true },
  { name: "UnHerd", url: "https://unherd.com/feed/", source_class: "perspective_discovery", region: "UK", priority: 2, limit: 12, discovery_only: true },
  { name: "Reason", url: "https://reason.com/feed/", source_class: "perspective_discovery", region: "US", priority: 2, limit: 12, discovery_only: true },
  { name: "National Review", url: "https://www.nationalreview.com/feed/", source_class: "perspective_discovery", region: "US", priority: 2, limit: 12, discovery_only: true },
  { name: "City Journal", url: "https://www.city-journal.org/feed", source_class: "perspective_discovery", region: "US", priority: 2, limit: 12, discovery_only: true },
  { name: "The Federalist", url: "https://thefederalist.com/feed/", source_class: "perspective_discovery", region: "US", priority: 2, limit: 12, discovery_only: true },
  { name: "FrontPageMag", url: "https://www.frontpagemag.com/feed/", source_class: "advocacy_discovery", region: "US", priority: 1, limit: 12, discovery_only: true },
  { name: "JihadWatch", url: "https://www.jihadwatch.org/feed", source_class: "advocacy_discovery", region: "US", priority: 1, limit: 12, discovery_only: true },
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
    .replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#0*39;|&apos;/g, "'")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/\s+/g, " ").trim();
}
function extractItems(xml, feed) {
  const blocks = xml.match(/<(?:item|entry)\b[\s\S]*?<\/(?:item|entry)>/gi) || [];
  const out = [];
  const limit = Number.isInteger(feed.limit) ? feed.limit : 18;
  for (const [feedRank, block] of blocks.slice(0, limit).entries()) {
    const titleMatch = block.match(/<title(?:\s[^>]*)?>([\s\S]*?)<\/title>/i);
    if (!titleMatch) continue;
    const headline = decodeXml(titleMatch[1]);
    if (!headline || headline === feed.name) continue;
    let url = null;
    const linkText = block.match(/<link(?:\s[^>]*)?>([\s\S]*?)<\/link>/i);
    const linkHref = block.match(/<link\b[^>]*href=["']([^"']+)["'][^>]*\/?>/i);
    const guid = block.match(/<guid(?:\s[^>]*)?>([\s\S]*?)<\/guid>/i);
    if (linkHref) url = decodeXml(linkHref[1]); else if (linkText) url = decodeXml(linkText[1]); else if (guid) url = decodeXml(guid[1]);
    if (url && !/^https?:\/\//i.test(url)) url = null;
    const desc = block.match(/<(?:description|summary|content:encoded)(?:\s[^>]*)?>([\s\S]*?)<\/(?:description|summary|content:encoded)>/i);
    const dateMatch = block.match(/<(?:pubDate|published|updated|dc:date)(?:\s[^>]*)?>([\s\S]*?)<\/(?:pubDate|published|updated|dc:date)>/i);
    const parsedDate = dateMatch ? Date.parse(decodeXml(dateMatch[1])) : NaN;
    const published_at = Number.isFinite(parsedDate) ? new Date(parsedDate).toISOString() : null;
    out.push({
      source: feed.name, headline, normalized: normalizeTitle(headline),
      description: desc ? decodeXml(desc[1]).slice(0, 900) : "", url, feed_rank: feedRank, published_at,
      source_class: feed.source_class || "news", region: feed.region || null,
      source_priority: Number.isFinite(feed.priority) ? feed.priority : 2,
      discovery_only: Boolean(feed.discovery_only),
    });
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
    const response = await fetch(feed.url, { headers: { "user-agent": "MorgentidendeNewsdesk/4.0 (+https://morgentidende.nicolaipetersen108.workers.dev/)" }, signal: controller.signal, redirect: "follow" });
    if (!response.ok) return { source: feed.name, source_class: feed.source_class, region: feed.region, discovery_only: Boolean(feed.discovery_only), ok: false, status: response.status, signals: [] };
    const xml = await response.text();
    const signals = extractItems(xml, feed);
    return { source: feed.name, source_class: feed.source_class, region: feed.region, discovery_only: Boolean(feed.discovery_only), ok: signals.length > 0, status: response.status, error: signals.length ? null : "no-feed-items-parsed", signals };
  } catch (error) { return { source: feed.name, source_class: feed.source_class, region: feed.region, discovery_only: Boolean(feed.discovery_only), ok: false, status: null, error: String(error), signals: [] }; }
  finally { clearTimeout(timer); }
}
async function buildScan() {
  const fetched = await Promise.all(FEEDS.map(fetchFeed));
  const signals = fetched.flatMap((x) => x.signals);
  signals.sort((a, b) => a.normalized.localeCompare(b.normalized, "da") || a.source.localeCompare(b.source, "da") || a.headline.localeCompare(b.headline, "da"));
  const stable = signals.map(({ source, headline, normalized, description, url, published_at, source_class, discovery_only }) => ({ source, headline, normalized, description, url, published_at, source_class, discovery_only }));
  const fingerprint = await sha256Hex(JSON.stringify(stable));
  const grouped = new Map();
  for (const signal of signals) { const items = grouped.get(signal.normalized) || []; items.push(signal); grouped.set(signal.normalized, items); }
  const exactClusters = [];
  for (const [normalized, items] of grouped.entries()) {
    const sources = [...new Set(items.map((x) => x.source))].sort();
    if (sources.length >= 2) exactClusters.push({ normalized, sources, headlines: items.map((x) => x.headline), note: "Exact normalized headline match only; not proof of independent sourcing." });
  }
  return {
    schema_version: 5, runtime: "cloudflare-workers", generated_at: new Date().toISOString(), fingerprint,
    signal_count: signals.length, feeds: fetched.map(({ source, source_class, region, discovery_only, ok, status, error }) => ({ source, source_class, region, discovery_only, ok, status, error: error || null })),
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
      const stampedAt = incoming.generated_at || incoming.checked_at || new Date().toISOString();
      await this.ctx.storage.put("last_editorial_at", stampedAt);
      await this.ctx.storage.put("latest_editorial", incoming);

      const now = Date.now();
      let handled = (await this.ctx.storage.get("handled_signals")) || [];
      handled = handled.filter((x) => Date.parse(x.expires_at || "") > now);
      const ttlHours = incoming.status === "approved" ? 36
        : incoming.status === "watch" && incoming.stage === "research" ? 18
        : incoming.status === "watch" ? 4
        : incoming.status === "drop" ? 12 : 6;
      for (const key of incoming.handled_signal_keys || []) {
        if (!key) continue;
        handled = handled.filter((x) => x.key !== key);
        handled.unshift({ key, at: stampedAt, status: incoming.status || "hold", expires_at: new Date(now + ttlHours * 3600_000).toISOString() });
      }
      await this.ctx.storage.put("handled_signals", handled.slice(0, 180));

      const history = (await this.ctx.storage.get("editorial_history")) || [];
      history.unshift({ generated_at: stampedAt, status: incoming.status, stage: incoming.stage || "approved", slug: incoming.slug || null, reason: incoming.reason || null, scan_fingerprint: incoming.scan_fingerprint || null, handled_signal_keys: incoming.handled_signal_keys || [], category: incoming.audit?.assignment?.category || null, weight: incoming.audit?.assignment?.weight || null, ai_usage: incoming.ai_usage || null, github_prefetch: incoming.github_prefetch || null });
      await this.ctx.storage.put("editorial_history", history.slice(0, 144));
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
    if (url.pathname === "/editorial") return Response.json({ latest: (await this.ctx.storage.get("latest_editorial")) || null, last_editorial_at: (await this.ctx.storage.get("last_editorial_at")) || null, handled_signals: (await this.ctx.storage.get("handled_signals")) || [] }, { headers: jsonHeaders });
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
    const media = { ...clone.media }; delete clone.media.base64; clone.media.url = publicMediaUrl(media.key);
    await stateStub(env).fetch("https://state/media/store", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(media) });
  }
  await stateStub(env).fetch("https://state/editorial/store", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(clone) });
  return clone;
}
function mergeGitHubPrefetch(scan, prefetch) {
  if (!prefetch || prefetch.scan_fingerprint !== scan?.fingerprint || !Array.isArray(prefetch.items)) {
    return { scan, used: 0, reason: "missing-or-stale" };
  }
  const byUrl = new Map();
  for (const item of prefetch.items.slice(0, 20)) {
    const url = String(item?.url || "");
    const excerpt = String(item?.excerpt || "");
    if (!item?.ok || !/^https?:\/\//i.test(url) || excerpt.length < 160) continue;
    byUrl.set(url, item);
  }
  let used = 0;
  const signals = (scan.signals || []).map((signal) => {
    const item = byUrl.get(String(signal?.url || ""));
    if (!item) return signal;
    used += 1;
    return {
      ...signal,
      prefetched_excerpt: String(item.excerpt).slice(0, 12000),
      prefetched_final_url: item.final_url || signal.url,
      prefetched_status: item.status || 200,
      prefetched_outbound_links: Array.isArray(item.outbound_links) ? item.outbound_links.slice(0, 24) : [],
    };
  });
  return { scan: { ...scan, signals }, used, reason: used ? "matched" : "no-url-match" };
}

async function maybeRunEditorial(env, scan, force = false, runtimeMeta = null) {
  const status = await (await getState(env, "/editorial")).json();
  if (!force && !editorialDue(status.last_editorial_at)) return status.latest || { status: "idle", reason: "Editorial cadence not due" };
  const now = Date.now();
  const excludedSignalKeys = (status.handled_signals || [])
    .filter((x) => Date.parse(x.expires_at || "") > now)
    .map((x) => x.key)
    .filter(Boolean);
  try {
    const result = await runEditorialCycle(env, scan, { excludedSignalKeys });
    if (runtimeMeta) result.github_prefetch = runtimeMeta;
    return persistEditorial(env, result);
  } catch (error) {
    const failed = { status: "hold", stage: "runtime-error", checked_at: new Date().toISOString(), generated_at: new Date().toISOString(), scan_fingerprint: scan.fingerprint, reason: String(error), handled_signal_keys: [], ai_usage: error?.ai_usage || null };
    if (runtimeMeta) failed.github_prefetch = runtimeMeta;
    return persistEditorial(env, failed);
  }
}

export default {
  async scheduled(_controller, env, ctx) {
    ctx.waitUntil((async () => {
      // Scheduled Worker work is discovery only. Editorial AI is driven by the
      // import workflow so approved packages cannot be overwritten before GitHub imports them.
      const scan = await buildScan(); await storeScan(env, scan);
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
      const state = await (await getState(env)).json(); let scan = state.latest || await buildScan(); if (!state.latest) await storeScan(env, scan);
      let prefetch = null;
      try {
        const type = request.headers.get("content-type") || "";
        if (type.includes("application/json")) prefetch = await request.json();
      } catch (_) {}
      const merged = mergeGitHubPrefetch(scan, prefetch);
      scan = merged.scan;
      const prefetchMeta = {
        used: merged.used,
        reason: merged.reason,
        attempted: Array.isArray(prefetch?.items) ? prefetch.items.length : 0,
        usable: Array.isArray(prefetch?.items) ? prefetch.items.filter((x) => x?.ok && String(x?.excerpt || "").length >= 160).length : 0,
      };
      return Response.json(await maybeRunEditorial(env, scan, true, prefetchMeta), { headers: jsonHeaders });
    }
    if (url.pathname.startsWith("/media/")) {
      const key = decodeURIComponent(url.pathname.slice("/media/".length)); return stateStub(env).fetch(`https://state/media/get?key=${encodeURIComponent(key)}`);
    }
    if (url.pathname === "/history") return getState(env, "/history");
    return new Response("Morgentidende Newsdesk runtime\n", { headers: { "content-type": "text/plain; charset=utf-8", "x-robots-tag": "noindex, nofollow" } });
  },
};
