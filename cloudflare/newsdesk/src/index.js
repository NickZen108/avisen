import { DurableObject } from "cloudflare:workers";

const FEEDS = [
  { name: "DR", url: "https://www.dr.dk/nyheder/service/feeds/allenyheder" },
  { name: "TV2", url: "https://www.tv2.dk/rss" },
  { name: "Berlingske", url: "https://www.berlingske.dk/rss" },
];

const jsonHeaders = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-robots-tag": "noindex, nofollow",
};

function normalizeTitle(value) {
  return value
    .toLocaleLowerCase("da-DK")
    .normalize("NFKC")
    .replace(/[^a-z0-9æøåäöüéèáàíìóòúùß ]+/giu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function decodeXml(value) {
  return value
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/gi, "$1")
    .replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();
}

function extractItems(xml, source) {
  const blocks = xml.match(/<(?:item|entry)\b[\s\S]*?<\/(?:item|entry)>/gi) || [];
  const out = [];

  for (const block of blocks.slice(0, 24)) {
    const titleMatch = block.match(/<title(?:\s[^>]*)?>([\s\S]*?)<\/title>/i);
    if (!titleMatch) continue;
    const headline = decodeXml(titleMatch[1]);
    if (!headline || headline === source) continue;

    let url = null;
    const linkText = block.match(/<link(?:\s[^>]*)?>([\s\S]*?)<\/link>/i);
    const linkHref = block.match(/<link\b[^>]*href=["']([^"']+)["'][^>]*\/?>/i);
    const guid = block.match(/<guid(?:\s[^>]*)?>([\s\S]*?)<\/guid>/i);
    if (linkHref) url = decodeXml(linkHref[1]);
    else if (linkText) url = decodeXml(linkText[1]);
    else if (guid) url = decodeXml(guid[1]);
    if (url && !/^https?:\/\//i.test(url)) url = null;

    out.push({
      source,
      headline,
      normalized: normalizeTitle(headline),
      url,
    });
  }
  return out;
}

async function sha256Hex(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((x) => x.toString(16).padStart(2, "0")).join("");
}

async function fetchFeed(feed) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(feed.url, {
      headers: { "user-agent": "MorgentidendeNewsdesk/2.0 (+https://morgentidende.nicolaipetersen108.workers.dev/)" },
      signal: controller.signal,
    });
    if (!response.ok) {
      return { source: feed.name, ok: false, status: response.status, signals: [] };
    }
    const xml = await response.text();
    return { source: feed.name, ok: true, status: response.status, signals: extractItems(xml, feed.name) };
  } catch (error) {
    return { source: feed.name, ok: false, status: null, error: String(error), signals: [] };
  } finally {
    clearTimeout(timer);
  }
}

async function buildScan() {
  const fetched = await Promise.all(FEEDS.map(fetchFeed));
  const signals = fetched.flatMap((x) => x.signals);
  signals.sort((a, b) =>
    a.normalized.localeCompare(b.normalized, "da") ||
    a.source.localeCompare(b.source, "da") ||
    a.headline.localeCompare(b.headline, "da")
  );

  const stable = signals.map(({ source, headline, normalized, url }) => ({ source, headline, normalized, url }));
  const fingerprint = await sha256Hex(JSON.stringify(stable));
  const grouped = new Map();
  for (const signal of signals) {
    const items = grouped.get(signal.normalized) || [];
    items.push(signal);
    grouped.set(signal.normalized, items);
  }

  const exactClusters = [];
  for (const [normalized, items] of grouped.entries()) {
    const sources = [...new Set(items.map((x) => x.source))].sort();
    if (sources.length >= 2) {
      exactClusters.push({
        normalized,
        sources,
        headlines: items.map((x) => x.headline),
        note: "Exact normalized headline match only; not proof of independent sourcing.",
      });
    }
  }

  return {
    schema_version: 2,
    runtime: "cloudflare-workers",
    generated_at: new Date().toISOString(),
    fingerprint,
    signal_count: signals.length,
    feeds: fetched.map(({ source, ok, status, error }) => ({ source, ok, status, error: error || null })),
    signals,
    exact_clusters: exactClusters,
    editorial_status: "UNRANKED",
    warning: "This queue is an inventory, not a news-value or verification decision.",
  };
}

export class NewsroomState extends DurableObject {
  async fetch(request) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/store") {
      const incoming = await request.json();
      const previous = await this.ctx.storage.get("latest");
      if (!previous || previous.fingerprint !== incoming.fingerprint) {
        await this.ctx.storage.put("latest", incoming);
        const history = (await this.ctx.storage.get("history")) || [];
        history.unshift({ generated_at: incoming.generated_at, fingerprint: incoming.fingerprint, signal_count: incoming.signal_count });
        await this.ctx.storage.put("history", history.slice(0, 288));
      } else {
        incoming.generated_at = previous.generated_at;
      }
      await this.ctx.storage.put("last_attempt_at", new Date().toISOString());
      return new Response(JSON.stringify({ ok: true, changed: !previous || previous.fingerprint !== incoming.fingerprint }), { headers: jsonHeaders });
    }

    if (url.pathname === "/history") {
      const history = (await this.ctx.storage.get("history")) || [];
      return new Response(JSON.stringify(history), { headers: jsonHeaders });
    }

    const latest = await this.ctx.storage.get("latest");
    const lastAttempt = await this.ctx.storage.get("last_attempt_at");
    return new Response(JSON.stringify({ latest: latest || null, last_attempt_at: lastAttempt || null }), { headers: jsonHeaders });
  }
}

async function storeScan(env, scan) {
  const id = env.NEWSROOM_STATE.idFromName("global");
  const stub = env.NEWSROOM_STATE.get(id);
  return stub.fetch("https://state/store", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(scan),
  });
}

async function getState(env, path = "/state") {
  const id = env.NEWSROOM_STATE.idFromName("global");
  return env.NEWSROOM_STATE.get(id).fetch(`https://state${path}`);
}

export default {
  async scheduled(_controller, env, ctx) {
    ctx.waitUntil((async () => {
      const scan = await buildScan();
      await storeScan(env, scan);
    })());
  },

  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/health") {
      const state = await (await getState(env)).json();
      return new Response(JSON.stringify({
        ok: true,
        service: "morgentidende-newsdesk",
        runtime: "cloudflare-workers",
        latest_generated_at: state.latest?.generated_at || null,
        last_attempt_at: state.last_attempt_at || null,
        signal_count: state.latest?.signal_count || 0,
      }), { headers: jsonHeaders });
    }

    if (url.pathname === "/candidates") {
      const state = await (await getState(env)).json();
      if (!state.latest) {
        const scan = await buildScan();
        await storeScan(env, scan);
        return new Response(JSON.stringify(scan), { headers: jsonHeaders });
      }
      return new Response(JSON.stringify(state.latest), { headers: jsonHeaders });
    }

    if (url.pathname === "/history") {
      return getState(env, "/history");
    }

    return new Response("Morgentidende Newsdesk runtime\n", {
      headers: { "content-type": "text/plain; charset=utf-8", "x-robots-tag": "noindex, nofollow" },
    });
  },
};
