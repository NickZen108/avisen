#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def must_sub(text: str, pattern: str, replacement: str, label: str, flags: int = re.S) -> str:
    out, n = re.subn(pattern, replacement, text, count=1, flags=flags)
    if n != 1:
        raise RuntimeError(f"{label}: expected exactly one replacement, got {n}")
    return out


def patch_index() -> None:
    path = "cloudflare/newsdesk/src/index.js"
    text = read(path)
    feeds = r'''const FEEDS = [
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
];'''
    text = must_sub(text, r"const FEEDS = \[[\s\S]*?\n\];", feeds, "feeds")

    text = text.replace('.replace(/&amp;/g, "&").replace(/&quot;/g, \'"\').replace(/&#39;|&apos;/g, "\'")',
                        '.replace(/&amp;/g, "&").replace(/&quot;/g, \'"\').replace(/&#0*39;|&apos;/g, "\'")')

    extract = r'''function extractItems(xml, feed) {
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
async function sha256Hex'''
    text = must_sub(text, r"function extractItems\(xml, source\) \{[\s\S]*?\n\}\nasync function sha256Hex", extract, "extractItems")

    fetch_feed = r'''async function fetchFeed(feed) {
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
async function buildScan'''
    text = must_sub(text, r"async function fetchFeed\(feed\) \{[\s\S]*?\n\}\nasync function buildScan", fetch_feed, "fetchFeed")

    text = text.replace(
        'const stable = signals.map(({ source, headline, normalized, description, url }) => ({ source, headline, normalized, description, url }));',
        'const stable = signals.map(({ source, headline, normalized, description, url, published_at, source_class, discovery_only }) => ({ source, headline, normalized, description, url, published_at, source_class, discovery_only }));'
    )
    text = text.replace('schema_version: 4, runtime: "cloudflare-workers"', 'schema_version: 5, runtime: "cloudflare-workers"')
    text = text.replace(
        'feeds: fetched.map(({ source, ok, status, error }) => ({ source, ok, status, error: error || null })),',
        'feeds: fetched.map(({ source, source_class, region, discovery_only, ok, status, error }) => ({ source, source_class, region, discovery_only, ok, status, error: error || null })),'
    )

    editorial_store = r'''if (request.method === "POST" && url.pathname === "/editorial/store") {
      const incoming = await request.json();
      const stampedAt = incoming.generated_at || incoming.checked_at || new Date().toISOString();
      await this.ctx.storage.put("last_editorial_at", stampedAt);
      await this.ctx.storage.put("latest_editorial", incoming);

      const now = Date.now();
      let handled = (await this.ctx.storage.get("handled_signals")) || [];
      handled = handled.filter((x) => Date.parse(x.expires_at || "") > now);
      const ttlHours = incoming.status === "approved" ? 36 : incoming.status === "watch" ? 2 : incoming.status === "drop" ? 12 : 6;
      for (const key of incoming.handled_signal_keys || []) {
        if (!key) continue;
        handled = handled.filter((x) => x.key !== key);
        handled.unshift({ key, at: stampedAt, status: incoming.status || "hold", expires_at: new Date(now + ttlHours * 3600_000).toISOString() });
      }
      await this.ctx.storage.put("handled_signals", handled.slice(0, 180));

      const history = (await this.ctx.storage.get("editorial_history")) || [];
      history.unshift({ generated_at: stampedAt, status: incoming.status, stage: incoming.stage || "approved", slug: incoming.slug || null, reason: incoming.reason || null, scan_fingerprint: incoming.scan_fingerprint || null, handled_signal_keys: incoming.handled_signal_keys || [] });
      await this.ctx.storage.put("editorial_history", history.slice(0, 144));
      return Response.json({ ok: true }, { headers: jsonHeaders });
    }
    if (request.method === "POST" && url.pathname === "/media/store")'''
    text = must_sub(
        text,
        r'if \(request\.method === "POST" && url\.pathname === "/editorial/store"\) \{[\s\S]*?\n    \}\n    if \(request\.method === "POST" && url\.pathname === "/media/store"\)',
        editorial_store,
        "editorial store",
    )

    old_editorial_state = 'if (url.pathname === "/editorial") return Response.json({ latest: (await this.ctx.storage.get("latest_editorial")) || null, last_editorial_at: (await this.ctx.storage.get("last_editorial_at")) || null }, { headers: jsonHeaders });'
    new_editorial_state = 'if (url.pathname === "/editorial") return Response.json({ latest: (await this.ctx.storage.get("latest_editorial")) || null, last_editorial_at: (await this.ctx.storage.get("last_editorial_at")) || null, handled_signals: (await this.ctx.storage.get("handled_signals")) || [] }, { headers: jsonHeaders });'
    if old_editorial_state not in text:
        raise RuntimeError("editorial state endpoint pattern missing")
    text = text.replace(old_editorial_state, new_editorial_state, 1)

    maybe = r'''async function maybeRunEditorial(env, scan, force = false) {
  const status = await (await getState(env, "/editorial")).json();
  if (!force && !editorialDue(status.last_editorial_at)) return status.latest || { status: "idle", reason: "Editorial cadence not due" };
  const now = Date.now();
  const excludedSignalKeys = (status.handled_signals || [])
    .filter((x) => Date.parse(x.expires_at || "") > now)
    .map((x) => x.key)
    .filter(Boolean);
  try { return persistEditorial(env, await runEditorialCycle(env, scan, { excludedSignalKeys })); }
  catch (error) {
    const failed = { status: "hold", stage: "runtime-error", checked_at: new Date().toISOString(), generated_at: new Date().toISOString(), scan_fingerprint: scan.fingerprint, reason: String(error), handled_signal_keys: [], ai_usage: error?.ai_usage || null };
    return persistEditorial(env, failed);
  }
}

export default'''
    text = must_sub(text, r"async function maybeRunEditorial\(env, scan, force = false\) \{[\s\S]*?\n\}\n\nexport default", maybe, "maybeRunEditorial")

    scheduled = r'''async scheduled(_controller, env, ctx) {
    ctx.waitUntil((async () => {
      // Scheduled Worker work is discovery only. Editorial AI is driven by the
      // import workflow so approved packages cannot be overwritten before GitHub imports them.
      const scan = await buildScan(); await storeScan(env, scan);
    })());
  },
  async fetch'''
    text = must_sub(text, r"async scheduled\(_controller, env, ctx\) \{[\s\S]*?\n  \},\n  async fetch", scheduled, "scheduled scan only")

    write(path, text)


def patch_editorial() -> None:
    path = "cloudflare/newsdesk/src/editorial.js"
    text = read(path)

    helpers = r'''function stripHtml(html) {
  return String(html || "")
    .replace(/<script\b[\s\S]*?<\/script>/gi, " ").replace(/<style\b[\s\S]*?<\/style>/gi, " ")
    .replace(/<nav\b[\s\S]*?<\/nav>/gi, " ").replace(/<footer\b[\s\S]*?<\/footer>/gi, " ")
    .replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&quot;/g, '"')
    .replace(/&#0*39;|&apos;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/\s+/g, " ").trim();
}
function signalKey(signal) { return `${signal?.normalized || slugify(signal?.headline || "")}|${signal?.url || ""}`; }
function sourceGroup(name, url = null) {
  try { if (url) return `host-${slugify(new URL(url).hostname.replace(/^www\./, ""))}`; } catch (_) {}
  return slugify(name || "source") + "-reporting";
}
const STOPWORDS = new Set("the and for with from that this have are was were will into over after before says said der die das den dem des ein eine und mit von auf für til med fra som det den der en et af og i på at de la le les des une un du et pour avec dans sur est sont que qui de l en au aux".split(/\s+/));
function words(value) {
  return String(value || "").toLocaleLowerCase("da-DK").normalize("NFKD")
    .replace(/[^a-z0-9æøåäöüéèáàíìóòúùß ]+/giu, " ").split(/\s+/)
    .filter((x) => x.length >= 4 && !STOPWORDS.has(x));
}
function lexicalSimilarity(a, b) {
  const A = new Set(words(a)), B = new Set(words(b));
  if (!A.size || !B.size) return 0;
  let overlap = 0; for (const x of A) if (B.has(x)) overlap += 1;
  return overlap / Math.min(A.size, B.size);
}
function extractOutboundLinks(html, baseUrl) {
  const out = []; const seen = new Set();
  const re = /<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;
  for (const match of String(html || "").matchAll(re)) {
    try {
      const u = new URL(match[1], baseUrl); if (!/^https?:$/.test(u.protocol)) continue;
      const baseHost = new URL(baseUrl).hostname.replace(/^www\./, "");
      const host = u.hostname.replace(/^www\./, "");
      if (!host || host === baseHost || seen.has(u.href)) continue;
      seen.add(u.href); out.push({ url: u.href, text: stripHtml(match[2]).slice(0, 180) });
      if (out.length >= 24) break;
    } catch (_) {}
  }
  return out;
}
function trustedExpansionKind(value) {
  try {
    const host = new URL(value).hostname.replace(/^www\./, "").toLowerCase();
    const primary = ["gov.uk", "police.uk", "polizei.berlin.de", "berlin.de", "bund.de", "europa.eu", "ec.europa.eu", "who.int", "un.org"];
    if (primary.some((x) => host === x || host.endsWith(`.${x}`))) return "primary";
    const reporting = ["rbb24.de", "tagesschau.de", "itv.com", "bbc.co.uk", "bbc.com", "reuters.com", "apnews.com", "dr.dk", "tv2.dk", "svt.se", "nrk.no", "france24.com"];
    if (reporting.some((x) => host === x || host.endsWith(`.${x}`))) return "public_media";
  } catch (_) {}
  return null;
}

async function fetchExcerpt'''
    text = must_sub(text, r"function stripHtml\(html\) \{[\s\S]*?\n\}\n\nasync function fetchExcerpt", helpers, "editorial helpers")

    fetch_excerpt = r'''async function fetchExcerpt(signal) {
  if (!signal?.url) return { ...signal, excerpt: signal?.description || "", fetched: false, outbound_links: [] };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 18000);
  try {
    const response = await fetch(signal.url, {
      headers: { "user-agent": "MorgentidendeResearch/1.2 (+https://morgentidende.nicolaipetersen108.workers.dev/)" },
      signal: controller.signal, redirect: "follow",
    });
    if (!response.ok) return { ...signal, excerpt: signal.description || "", fetched: false, fetch_status: response.status, outbound_links: [] };
    const type = response.headers.get("content-type") || "";
    if (!type.includes("html") && !type.includes("text")) return { ...signal, excerpt: signal.description || "", fetched: false, fetch_status: response.status, outbound_links: [] };
    const html = await response.text();
    const text = stripHtml(html).slice(0, 12000);
    return { ...signal, excerpt: text || signal.description || "", fetched: Boolean(text), fetch_status: response.status, final_url: response.url, outbound_links: type.includes("html") ? extractOutboundLinks(html, response.url) : [] };
  } catch (error) {
    return { ...signal, excerpt: signal.description || "", fetched: false, fetch_error: String(error), outbound_links: [] };
  } finally { clearTimeout(timer); }
}

function responseObject'''
    text = must_sub(text, r"async function fetchExcerpt\(signal\) \{[\s\S]*?\n\}\n\nfunction responseObject", fetch_excerpt, "fetchExcerpt")

    text = text.replace('decision: { type: "string", enum: ["publish", "hold"] }', 'decision: { type: "string", enum: ["research", "watch", "drop"] }', 1)
    text = text.replace('signal_indexes: { type: "array", items: { type: "integer" }, minItems: 0, maxItems: 6 }', 'signal_indexes: { type: "array", items: { type: "integer" }, minItems: 0, maxItems: 3 }', 1)
    text = text.replace('decision: { type: "string", enum: ["continue", "hold"] }', 'decision: { type: "string", enum: ["continue", "watch", "hold"] }', 1)

    selection = r'''const EDITORIAL_LENS = [
  "ytringsfri", "censur", "overvåg", "privacy", "freedom", "liberty", "surveillance", "censor",
  "skat", "afgift", "regul", "tax", "regulation", "immigration", "migration", "asylum", "migrant",
  "islam", "jihad", "religion", "kvinder", "women", "rape", "voldt", "fgm", "forced marriage",
  "demokr", "democr", "police", "terror", "extrem", "waste", "spild", "cost", "omkost",
];
const GENERAL_IMPORTANCE = ["war", "krig", "election", "valg", "earthquake", "jordskælv", "flood", "oversvømm", "fire", "brand", "ebola", "pandemic", "central bank", "rente", "ai ", "artificial intelligence", "space", "rumfart", "court", "domstol"];
function topicBoost(signal) {
  const hay = `${signal.headline || ""} ${signal.description || ""}`.toLocaleLowerCase("da-DK");
  const lens = EDITORIAL_LENS.some((x) => hay.includes(x)) ? 4 : 0;
  const general = GENERAL_IMPORTANCE.some((x) => hay.includes(x)) ? 4 : 0;
  return Math.max(lens, general);
}
function signalSummary(scan, excludedSignalKeys = []) {
  const excluded = new Set(excludedSignalKeys || []);
  const now = Date.parse(scan.generated_at || "") || Date.now();
  const clusterSizes = new Map((scan.exact_clusters || []).map((c) => [c.normalized, (c.sources || []).length]));
  const ranked = scan.signals.map((s, i) => {
    const published = Date.parse(s.published_at || "") || 0;
    const ageHours = published ? Math.max(0, (now - published) / 3600000) : null;
    const freshness = ageHours === null ? 2 : ageHours <= 2 ? 12 : ageHours <= 6 ? 9 : ageHours <= 24 ? 6 : ageHours <= 72 ? 2 : -6;
    const feedRank = Number.isInteger(s.feed_rank) ? s.feed_rank : 99;
    const feedScore = Math.max(0, 8 - Math.floor(feedRank / 3));
    const sourceScore = Math.max(0, Math.min(4, Number(s.source_priority) || 2));
    const clusterBonus = Math.min(2, Math.max(0, (clusterSizes.get(s.normalized) || 1) - 1));
    return { s, i, score: freshness + feedScore + sourceScore + clusterBonus + topicBoost(s), published };
  }).filter((x) => !excluded.has(signalKey(x.s)) && x.score > 0)
    .sort((a, b) => b.score - a.score || b.published - a.published || a.i - b.i);

  const chosen = []; const usedIndexes = new Set(); const perSource = new Map();
  // Reserve a few places for perspective sources so original/niche tips are not buried by mainstream volume.
  for (const item of ranked.filter((x) => x.s.discovery_only)) {
    if (chosen.length >= 5) break;
    if ((perSource.get(item.s.source) || 0) >= 1) continue;
    chosen.push(item); usedIndexes.add(item.i); perSource.set(item.s.source, 1);
  }
  for (const item of ranked) {
    if (chosen.length >= 28) break;
    if (usedIndexes.has(item.i)) continue;
    const used = perSource.get(item.s.source) || 0;
    if (used >= 4) continue;
    chosen.push(item); usedIndexes.add(item.i); perSource.set(item.s.source, used + 1);
  }
  chosen.sort((a, b) => b.score - a.score || b.published - a.published || a.i - b.i);
  return chosen.map(({ s, i, score }) => ({
    i, source: s.source, headline: s.headline, description: (s.description || "").slice(0, 220),
    published_at: s.published_at || null, source_class: s.source_class || "news", region: s.region || null,
    discovery_only: Boolean(s.discovery_only), score,
  }));
}
async function chooseAssignment(env, scan, excludedSignalKeys = []) {
  const signals = signalSummary(scan, excludedSignalKeys);
  if (!signals.length) return { decision: "drop", title_hint: "", category: "Danmark", weight: "D", signal_indexes: [], rationale: "Ingen ubehandlede kandidater med tilstrækkelig aktualitet/grundscore", core_question: "" };
  const system = `Du er første Nyhedsdesk på Morgentidende. Vælg ét research-frø, ikke en færdig artikel. RESEARCH når emnet har reel nyhedsværdi og bør undersøges; WATCH når et potentielt vigtigt tip endnu er for tyndt; DROP kun ved klar dublet, gammel/triviel sag eller åbenlys utroværdighed. discovery_only/perspective-kilder er værdifulde tips, men må aldrig i sig selv tælle som verifikation eller få dig til at antage konklusionen. Kategori og A-D-vægt er dit ansvar, ikke Scan. Returnér kort struktureret output.`;
  return aiJson(env, system, JSON.stringify({ generated_at: scan.generated_at, signals }), assignmentSchema, 550, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
}
function validIndexes(indexes, scan) { return [...new Set((indexes || []).filter((i) => Number.isInteger(i) && i >= 0 && i < scan.signals.length))]; }
function expandRelatedSignals(seedIndexes, scan) {
  const selected = seedIndexes.map((i) => ({ ...scan.signals[i], signal_index: i }));
  const selectedIndexes = new Set(seedIndexes);
  const candidates = [];
  for (let i = 0; i < scan.signals.length; i++) {
    if (selectedIndexes.has(i)) continue;
    const s = scan.signals[i];
    let best = 0;
    for (const seed of selected) {
      if (s.normalized && seed.normalized && s.normalized === seed.normalized) best = Math.max(best, 1);
      best = Math.max(best, lexicalSimilarity(`${seed.headline} ${seed.description || ""}`, `${s.headline} ${s.description || ""}`));
    }
    if (best >= 0.34) candidates.push({ i, s, best, published: Date.parse(s.published_at || "") || 0 });
  }
  candidates.sort((a, b) => b.best - a.best || b.published - a.published || a.i - b.i);
  const perSource = new Map(selected.map((s) => [s.source, 1]));
  for (const item of candidates) {
    if (selected.length >= 6) break;
    if ((perSource.get(item.s.source) || 0) >= 1) continue;
    selected.push({ ...item.s, signal_index: item.i }); perSource.set(item.s.source, 1);
  }
  return selected;
}
function validateAssignment(assignment, scan) {
  const indexes = validIndexes(assignment.signal_indexes, scan);
  const handled_signal_keys = indexes.map((i) => signalKey(scan.signals[i]));
  if (assignment.decision !== "research") return { ok: false, state: assignment.decision || "watch", reason: assignment.rationale || "Newsdesk hold", handled_signal_keys };
  if (!indexes.length) return { ok: false, state: "watch", reason: "Newsdesk valgte ingen brugbare research-frø", handled_signal_keys };
  const selected = expandRelatedSignals(indexes, scan);
  if (!selected.some((x) => x.url)) return { ok: false, state: "watch", reason: "Ingen kilde-URL til research", handled_signal_keys };
  return { ok: true, selected, handled_signal_keys };
}
function isEvidenceSource(item) { return item && !item.discovery_only; }
function authoritativePrimary(item) { return isEvidenceSource(item) && item.source_kind === "primary"; }
function evidenceGroups(items) { return [...new Set(items.filter(isEvidenceSource).map((x) => sourceGroup(x.source, x.final_url || x.url)))]; }

async function runResearch'''
    text = must_sub(
        text,
        r"function signalSummary\(scan\) \{[\s\S]*?\n\}\nasync function chooseAssignment\(env, scan\) \{[\s\S]*?\n\}\nfunction distinctSources\(items\) \{[\s\S]*?\n\}\nfunction validateAssignment\(assignment, scan\) \{[\s\S]*?\n\}\n\nasync function runResearch",
        selection,
        "selection and shortlist",
    )

    research = r'''async function runResearch(env, assignment, selected) {
  let researched = await Promise.all(selected.map(fetchExcerpt));
  let usable = researched.filter((x) => (x.excerpt || "").length >= 160);

  // Perspective/advocacy sources can trigger research. If the ordinary feed set does not
  // yet corroborate the tip, follow only clearly trusted primary/public-media links from it.
  if (!usable.some(authoritativePrimary) && evidenceGroups(usable).length < 2) {
    const target = `${assignment.title_hint || ""} ${assignment.core_question || ""}`;
    const links = [];
    for (const item of usable) {
      for (const link of item.outbound_links || []) {
        const kind = trustedExpansionKind(link.url); if (!kind) continue;
        links.push({ ...link, kind, score: lexicalSimilarity(target, `${link.text} ${link.url}`) });
      }
    }
    links.sort((a, b) => b.score - a.score);
    const seen = new Set(); const extraSignals = [];
    for (const link of links) {
      if (extraSignals.length >= 4 || seen.has(link.url)) continue;
      seen.add(link.url);
      let host = "linked-source"; try { host = new URL(link.url).hostname.replace(/^www\./, ""); } catch (_) {}
      extraSignals.push({ source: host, headline: link.text || assignment.title_hint || "Linked source", url: link.url, description: "", discovery_only: false, source_kind: link.kind, source_class: link.kind });
    }
    if (extraSignals.length) {
      const extra = await Promise.all(extraSignals.map(fetchExcerpt));
      researched = researched.concat(extra);
      usable = researched.filter((x) => (x.excerpt || "").length >= 160);
    }
  }

  if (!usable.some(authoritativePrimary) && evidenceGroups(usable).length < 2) {
    return { decision: "watch", rationale: "Lovende tip, men endnu ikke en autoritativ primærkilde eller to uafhængige ikke-discovery-kilder", researched: usable };
  }
  const sources = usable.map((s, i) => ({
    source_index: i, name: s.source, headline: s.headline, url: s.final_url || s.url,
    excerpt: s.excerpt.slice(0, 10000), discovery_only: Boolean(s.discovery_only), source_kind: s.source_kind || (s.discovery_only ? "discovery" : "news"),
  }));
  const system = `Du er Research på Morgentidende. Kortlæg historien, men fæld ikke fact-check-slutdom. discovery_only-kilder er tips/perspektiv og må ikke være bærende verifikation. En autoritativ primærkilde kan bære et faktum; ellers kræves normalt to reelt uafhængige ikke-discovery-kilder. Find bærende faktapåstande, modpositioner, konsekvenser, uenigheder og usikkerhed. Peg på præcise source_indexes. Forelæggelse markeres ved alvorlige belastende påstande. Opfind ikke claims.`;
  const research = await aiJson(env, system, JSON.stringify({ assignment, sources }), researchSchema, 1800, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
  research.researched = usable;
  research.source_payload = sources;
  if (research.right_of_reply_required) research.decision = "hold";
  return research;
}

async function runFactCheck'''
    text = must_sub(text, r"async function runResearch\(env, assignment, selected\) \{[\s\S]*?\n\}\n\nasync function runFactCheck", research, "runResearch")

    fact = r'''async function runFactCheck(env, assignment, research) {
  const system = `Du er en UAFHÆNGIG Fact checker på Morgentidende. Forsøg aktivt at falsificere hvert kandidat-claim mod de vedlagte kildetekster. discovery_only-kilder kan pege på et emne eller perspektiv, men må aldrig alene verificere et claim. Verified kræver enten én autoritativ primærkilde eller mindst to reelt uafhængige ikke-discovery-kilder. Rejected når evidensen modsiger claimet; ellers uncertain. To solide verificerede bærende claims er nok til en kort artikel. Opfind ingen nye kilder eller fakta.`;
  const fact = await aiJson(env, system, JSON.stringify({
    assignment,
    research: { core_question: research.core_question, rationale: research.rationale, contradictions: research.contradictions, candidate_claims: research.candidate_claims },
    sources: research.source_payload,
  }), factCheckSchema, 2200);
  fact.researched = research.researched;
  fact.core_question = research.core_question || assignment.core_question;
  fact.right_of_reply_required = research.right_of_reply_required;
  for (const claim of fact.claims) {
    const indexes = [...new Set((claim.source_indexes || []).filter((i) => Number.isInteger(i) && i >= 0 && i < fact.researched.length))];
    claim.source_indexes = indexes;
    const evidence = indexes.map((i) => fact.researched[i]).filter(isEvidenceSource);
    const primaryOk = evidence.some(authoritativePrimary);
    const independent = new Set(evidence.map((s) => sourceGroup(s.source, s.final_url || s.url)));
    if (claim.status === "verified" && !primaryOk && independent.size < 2) {
      claim.status = "uncertain";
      claim.notes = `${claim.notes || ""} Nedgraderet af deterministisk gate: ingen autoritativ primærkilde og færre end to uafhængige ikke-discovery-kilder.`.trim();
    }
  }
  const verified = fact.claims.filter((c) => c.status === "verified");
  if (verified.length < 2) {
    fact.decision = "hold";
    fact.rationale = `${fact.rationale || ""} Deterministisk gate: færre end to bærende claims er verificeret.`.trim();
  }
  return fact;
}

async function deskRecheck'''
    text = must_sub(text, r"async function runFactCheck\(env, assignment, research\) \{[\s\S]*?\n\}\n\nasync function deskRecheck", fact, "runFactCheck")

    ledger = r'''function makeLedger(storyId, slug, assignment, dossier, desk, accessedAt) {
  const sources = dossier.researched.map((s, i) => {
    const url = s.final_url || s.url;
    const primary = s.source_kind === "primary" && !s.discovery_only;
    return { id: `S${i + 1}`, name: s.source, url, published_at: s.published_at || null, accessed_at: accessedAt, type: primary ? "primary" : "news", source_group: sourceGroup(s.source, url), authoritative_for: primary ? (s.headline || "Primary record") : (s.headline || "Independent coverage"), discovery_only: Boolean(s.discovery_only) };
  });
  const verificationSources = sources.filter((s) => !s.discovery_only);
  const groups = [...new Set(verificationSources.map((s) => s.source_group))];
  const claims = dossier.claims.filter((c) => c.status === "verified").map((c, i) => {
    const ids = [...new Set(c.source_indexes)].map((n) => sources[n]?.id).filter(Boolean);
    return { id: `F${String(i + 1).padStart(2, "0")}`, claim: c.claim, status: "verified", source_ids: ids, independent_groups: ids.map((id) => sources.find((s) => s.id === id && !s.discovery_only)?.source_group).filter(Boolean), checked_at: accessedAt, notes: c.notes || "" };
  });
  return {
    schema_version: 2, story_id: storyId, article_slug: slug,
    assignment: { category: assignment.category, weight: assignment.weight, core_question: dossier.core_question || assignment.core_question, manual_review: false },
    sources,
    coverage_sweep: { status: groups.length >= 3 ? "pass" : "limited", editorial_source_ids: verificationSources.slice(0, 6).map((s) => s.id), independent_source_groups: groups.slice(0, 6), limitations: groups.length >= 3 ? null : "Færre end tre uafhængige verifikationskilder; discovery-only-kilder tæller ikke med", notes: ["Research kan begynde fra perspektivkilder, men Fact checker kræver autoritativ primærkilde eller uafhængig ikke-discovery-verifikation."] },
    claims, numbers: [], quotes: [], right_of_reply: { required: false, party: null, contacted_at: null, deadline: null, response: null, exception: null },
    fact_check: { status: "pass", checked_at: accessedAt, notes: ["Uafhængigt Fact checker-call bestået; discovery-only-kilder kan ikke alene verificere claims."] },
    desk_recheck: { status: desk.decision, checked_at: accessedAt, rationale: desk.rationale },
  };
}


const TEXT_NEURON_RATES'''
    text = must_sub(text, r"function makeLedger\(storyId, slug, assignment, dossier, desk, accessedAt\) \{[\s\S]*?\n\}\n\n\nconst TEXT_NEURON_RATES", ledger, "makeLedger")

    cycle = r'''export async function runEditorialCycle(env, scan, options = {}) {
  const aiUsageEvents = [];
  env = trackedAiEnv(env, aiUsageEvents);
  let result;
  try {
    result = await (async () => {
  const startedAt = nowIso();
  const assignment = await chooseAssignment(env, scan, options.excludedSignalKeys || []);
  const check = validateAssignment(assignment, scan);
  const handledSignalKeys = check.handled_signal_keys || [];
  if (!check.ok) {
    const state = check.state === "watch" ? "watch" : check.state === "drop" ? "drop" : "hold";
    return { status: state, stage: "newsdesk", checked_at: startedAt, generated_at: startedAt, reason: check.reason, scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment } };
  }

  const research = await runResearch(env, assignment, check.selected);
  if (research.decision !== "continue") return { status: research.decision === "watch" ? "watch" : "hold", stage: research.right_of_reply_required ? "ethics" : "research", checked_at: startedAt, generated_at: startedAt, reason: research.rationale || "Research hold", scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment } };

  const dossier = await runFactCheck(env, assignment, research);
  if (dossier.decision !== "publish") return { status: "hold", stage: "fact-check", checked_at: startedAt, generated_at: startedAt, reason: dossier.rationale || "Fact check hold", scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment } };

  const desk = await deskRecheck(env, assignment, dossier);
  if (!["publish", "update"].includes(desk.decision)) return { status: "hold", stage: "desk-recheck", checked_at: startedAt, generated_at: startedAt, reason: desk.rationale || "Newsdesk recheck hold", scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment } };

  let article = await writeArticle(env, assignment, dossier);
  let review = await finalReview(env, assignment, dossier, article);
  if (review.decision !== "pass") {
    const revised = await reviseFixableIssues(env, assignment, dossier, article, review);
    if (JSON.stringify(revised) !== JSON.stringify(article)) { article = revised; review = await finalReview(env, assignment, dossier, article); }
  }
  if (review.decision !== "pass" || [review.language, review.ethics, review.image, review.seo, review.final_editor].some((x) => x !== "pass")) {
    return { status: "hold", stage: "final-editor", checked_at: startedAt, generated_at: startedAt, reason: (review.notes || []).join("; ") || "Final editor hold", scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment } };
  }

  const date = startedAt.slice(0, 10);
  const slug = `${date}-${slugify(article.title)}`.slice(0, 96).replace(/-+$/g, "");
  const storyId = `${date}-${slugify(assignment.title_hint || article.title)}`.slice(0, 96).replace(/-+$/g, "");
  const imageKey = `${slug}.jpg`;
  const imageBase64 = await generateHero(env, article);
  const ledger = makeLedger(storyId, slug, assignment, dossier, desk, startedAt);
  const canonical = {
    pipeline_version: 2, status: "ready", release_requested: true, story_id: storyId, slug,
    category: assignment.category, weight: assignment.weight, title: article.title, standfirst: article.standfirst,
    byline: "Morgentidende Redaktion", published_at: null, updated_at: null, manual_review: false,
    ledger: `sources/${slug}.json`, claim_ids: ledger.claims.map((c) => c.id),
    seo: { title: article.seo_title, description: article.seo_description, canonical: null },
    image: { src: `/img/auto/${imageKey}`, alt: article.hero_alt, credit: "Morgentidende", license: "Morgentidende", source_url: null, image_type: "illustration", placement: "lead" },
    body: article.body, source_ids_to_display: ledger.sources.filter((s) => !s.discovery_only).slice(0, 6).map((s) => s.id), related_news_slug: null, related: [], correction_note: null, scheduled_for: null, released_from_schedule_at: null,
  };
  const approvalSnapshot = JSON.parse(JSON.stringify(canonical));
  for (const key of ["status", "published_at", "updated_at", "scheduled_for", "released_from_schedule_at", "release_requested", "publication", "manual_review_completed", "workflow_state"]) delete approvalSnapshot[key];
  const approval = { schema_version: 1, status: "pass", story_id: storyId, article_slug: slug, checked_at: startedAt, gates: { language: "pass", ethics: "pass", image: "pass", seo: "pass", final_editor: "pass" }, editorial_snapshot: approvalSnapshot };

  return {
    status: "approved", schema_version: 1, generated_at: startedAt, scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys,
    runtime: "cloudflare-workers-ai", model: STRONG_TEXT_MODEL, models: { fast: FAST_TEXT_MODEL, strong: STRONG_TEXT_MODEL, image: IMAGE_MODEL }, story_id: storyId, slug, article: canonical, ledger, approval,
    media: { key: imageKey, content_type: "image/jpeg", base64: imageBase64 },
    audit: { assignment, research: { rationale: research.rationale, candidate_claims: research.candidate_claims, contradictions: research.contradictions }, fact_check: { rationale: dossier.rationale, claims: dossier.claims, contradictions: dossier.contradictions }, desk_recheck: desk, final_review: review, source_count: ledger.sources.length, independent_source_groups: ledger.coverage_sweep.independent_source_groups },
  };
    })();
  } catch (error) {
    error.ai_usage = summarizeAiUsage(aiUsageEvents);
    throw error;
  }
  result.ai_usage = summarizeAiUsage(aiUsageEvents);
  return result;
}

export function editorialDue'''
    text = must_sub(text, r"export async function runEditorialCycle\(env, scan\) \{[\s\S]*?\n\}\n\nexport function editorialDue", cycle, "runEditorialCycle")
    text = text.replace('Date.now() - then >= 27 * 60 * 1000', 'Date.now() - then >= 13 * 60 * 1000')

    write(path, text)


def patch_sync_validator() -> None:
    path = "scripts/sync_cloudflare_editorial.py"
    text = read(path)
    text = text.replace(
        'ids = [sid for sid in coverage.get("editorial_source_ids", []) if sid in source_map][:6]',
        'ids = [sid for sid in coverage.get("editorial_source_ids", []) if sid in source_map and not source_map[sid].get("discovery_only")][:6]'
    )
    old = '''        source_groups = {
            str(source_map.get(sid, {}).get("source_group") or "").strip()
            for sid in ids
        }'''
    new = '''        source_groups = {
            str(source_map.get(sid, {}).get("source_group") or "").strip()
            for sid in ids
            if not source_map.get(sid, {}).get("discovery_only")
        }'''
    if old not in text:
        raise RuntimeError("sync validator source_groups pattern missing")
    text = text.replace(old, new, 1)
    write(path, text)


def patch_docs() -> None:
    write("agents/scan.md", """# Agent: Scan\n\n## Formål\nVær Morgentidendes billige, brede radar. Find signaler og grupper dem uden at lave journalistisk dom, fact check eller artikelprosa.\n\n## Skal læse\n`HUSREGLER.md`, `EDITORIAL.md`, `SOURCES.md`, `SCAN.md`, `SCHEDULE.md`, `AUTOMATION.md`.\n\n## Input\n`queue/candidates.json`/`scan/latest.md`, feeds og officielle kilder samt kendte live-story references når de findes. Inventaret er discovery, aldrig verifikation.\n\n## Handling\n1. Saml signaler bredt og billigt.\n2. Normalisér og deduplikér teknisk; registrér første observation og sandsynligt fælles kildeophav.\n3. Bevar originale enkeltkilde-signaler. Mange omtaler er ikke et krav for at komme videre.\n4. Markér `discovery_only` for perspektiv-/advocacy-kilder. De kan være gode tip, men tæller ikke som bevis.\n5. Knyt signalet til eksisterende story når det tydeligt er samme hændelse; ellers lad Nyhedsdesk afgøre NEW/UPDATE.\n6. Brug den redaktionelle linje som et let opmærksomhedsboost, aldrig som sandhedstest eller ønsket konklusion.\n7. Send signaler videre til Nyhedsdesk.\n\n## Ikke Scan-agentens arbejde\nKategori, A-D-vægt, endelig nyhedsværdi, researchbeslutning, fact check og publiceringsbeslutning ligger hos Nyhedsdesk/Research/Fact checker.\n\n## Output\nRåt `candidate/signal`: neutral headline/summary, URL, tidspunkt, source metadata, `discovery_only`, evt. relation til eksisterende story. Ingen artikeltekst.\n\n## Status\nScan må teknisk markere åbenlys `DROP` (fx identisk dublet/spam) men skal ellers bevare tvivlsomme, potentielt vigtige signaler til Nyhedsdesks `WATCH`/`RESEARCH`.\n""")

    write("SCAN.md", """# Scan-agent og discovery\n\nScan er et signalsystem, ikke journalist, fact checker eller publiceringsmotor.\n\n## Arkitektur\n1. Cloudflare Worker henter feeds hyppigt og gemmer rå signaler. Dette trin bruger ingen LLM-neurons.\n2. GitHub synkroniserer inventaret.\n3. En billig 8B-Newsdesk-vurdering får kun en kort deterministisk shortlist. Den vælger `RESEARCH`, `WATCH` eller `DROP`; kategori og A-D-vægt fastsættes her.\n4. Research/Fact check kommer først bagefter.\n\n## Shortlist uden blind vinkel\nShortlisten prioriterer aktualitet, placering i feedet, kildeklasse og offentlig/redaktionel relevans. Eksakte overskrifts-clusters giver kun en lille bonus og er aldrig bevis på kildeuafhængighed. Et mindre antal pladser reserveres til seriøse perspektiv-/discovery-kilder, så originale historier ikke drukner i mainstream-volumen.\n\n## Perspektivkilder\nStore liberale, konservative og nationalkonservative medier/blogs kan bruges som discovery i Skandinavien, Tyskland, Frankrig, Storbritannien og USA. Eksempler i den aktive scanner er bl.a. Document.no, Achgut, Tichys Einblick, Causeur, Contrepoints, Spiked, CapX, Reason, National Review, City Journal, FrontPageMag og JihadWatch.\n\nDisse er markeret `discovery_only` i scanneren. Det er en sikkerhedsregel om kildebrug, ikke en dom over deres politiske syn: De må starte en historie og pege på oversete dokumenter, men de tæller ikke alene som uafhængig verifikation. Research forsøger automatisk at følge tydeligt betroede links til primærkilder/offentlige medier og kræver derefter den normale dokumentation.\n\n## WATCH i stedet for tidligt afslag\nEt vigtigt enkeltkilde-tip skal normalt blive `WATCH`, ikke dø. WATCH får kortere cooldown end en godkendt/publiceret historie, så ny dokumentation kan få sagen genåbnet.\n\n## Flere samtidige historier\nSamme scan-inventar må behandles flere gange. Allerede håndterede signaler får midlertidig TTL, så næste redaktionelle cyklus tager næste stærke kandidat i stedet for at vælge den samme igen. Import-workflowet kan behandle op til tre forskellige kandidater pr. 15-minutters runde.\n\n## Ingen fyld\nNår de resterende kandidater ikke bærer research, er `DROP`/ingen artikel korrekt. Kapacitet er ikke kvote.\n""")

    newsdesk = read("agents/newsdesk.md")
    insert = """\n## Første assignment\n- Scan leverer signaler, ikke en færdig nyhedsvurdering.\n- Nyhedsdesk sætter kategori og A-D-vægt.\n- Vælg `RESEARCH`, `WATCH` eller `DROP`. Brug `WATCH` ved et potentielt vigtigt, men endnu tyndt enkeltkilde-tip; `DROP` kræver en konkret grund som klar dublet, gammel/triviel sag eller åbenlys utroværdighed.\n- Perspektiv-/advocacy-kilder markeret `discovery_only` kan være værdifulde agenda-tip, men må ikke behandles som verifikation.\n- Samme inventory kan give flere assignments; håndterede signaler sættes midlertidigt til side, så andre stærke historier også får en chance.\n"""
    newsdesk = newsdesk.replace("## Recheck efter Fact checker", insert + "\n## Recheck efter Fact checker", 1)
    write("agents/newsdesk.md", newsdesk)

    sources = read("SOURCES.md")
    marker = "## Uafhængighed\n"
    discovery = """## Discovery-/perspektivkilder\n\nIdeologiske, aktivistiske eller stærkt kommenterende medier kan være fremragende til at opdage oversete sager. De kan derfor stå i scannerens feednet som `discovery_only`. Det betyder:\n\n- de kan udløse `RESEARCH` eller `WATCH`\n- de kan pege på primærdokumenter og andre kilder\n- deres politiske retning er ikke i sig selv et argument for eller imod historien\n- de tæller ikke alene som uafhængig verifikation af et bærende claim\n- hvis de linker til en autoritativ primærkilde, skal Research åbne og kontrollere primærkilden direkte\n\nEn autoritativ primærkilde kan fortsat bære et faktum efter reglerne nedenfor; ellers kræves reelt uafhængig dokumentation.\n\n"""
    if marker not in sources:
        raise RuntimeError("SOURCES marker missing")
    sources = sources.replace(marker, discovery + marker, 1)
    write("SOURCES.md", sources)

    commentator = read("agents/commentator.md")
    old = "3. Ved religion/kultur må kommentaren kritisere idéer, institutioner, normer og praksisser tydeligt, herunder deres konsekvenser for kvinders frihed, demokrati, fred og social tillid. Den må ikke gøre mennesker kollektivt ansvarlige for deres baggrund eller tro."
    new = old + "\n   Ved verificerede historier om migration/asyl, seksualforbrydelser, tvangsægteskab, FGM eller kvinders rettigheder må en særskilt kommentar argumentere for strengere adgangs-, integrations- eller udvisningspolitik. Argumentet skal rettes mod regler, handlinger og dokumenterede normer/risici; det må ikke slutte fra enkeltpersoners handlinger til kollektiv skyld eller medfødte egenskaber hos en religion, nationalitet eller etnicitet. Påstande om mønstre eller kulturforskelle kræver selvstændig dokumentation."
    if old not in commentator:
        raise RuntimeError("commentator marker missing")
    commentator = commentator.replace(old, new, 1)
    write("agents/commentator.md", commentator)

    report = """# Scan/Newsdesk-refaktor — 1. september 2026\n\nImplementeret efter redaktionel gennemgang:\n\n- Scan er reduceret til discovery/deduplikering/metadata; kategori, A-D-vægt og researchdom ligger hos Nyhedsdesk.\n- Exact-headline-clusters er nedgraderet fra dominerende rankingfaktor til lille bonus.\n- AI-shortlist reduceret fra 40 kandidater á 360 tegn til 28 á 220 tegn; Newsdesk-outputloft 900 → 550 tokens.\n- Research-outputloft 2200 → 1800; Fact checker 2400 → 2200.\n- Deterministisk relateret-historie-ekspansion gør, at Newsdesk kan vælge få seed-signaler og Research stadig kan få op til seks relevante kilder.\n- `WATCH` beskytter vigtige enkeltkilde-tip mod tidligt permanent afslag.\n- Håndterede signaler får TTL, så samme inventar kan levere flere forskellige historier uden at AI vælger den samme igen.\n- Automatisk Cloudflare cron laver kun discovery; editorial AI køres i import-workflowet, så godkendte pakker ikke overskrives før GitHub kan importere dem.\n- Import-workflowet kører hvert 15. minut og kan behandle op til tre forskellige kandidater.\n- Discovery-nettet er udvidet med flere mainstream-kilder og liberale/konservative/nationalkonservative perspektivkilder i Skandinavien, Tyskland, Frankrig, UK og USA, herunder JihadWatch/FrontPageMag.\n- Perspektiv-/advocacy-kilder er `discovery_only`: de kan starte research, men tæller ikke som verifikation. Research følger betroede links til primærkilder/offentlige medier, når de findes.\n- Fact-check-reglen er harmoniseret med `SOURCES.md`: ét autoritativt primærdokument ELLER to reelt uafhængige ikke-discovery-kilder kan verificere et claim.\n\nMålet er højere recall af vigtige historier, færre falske afslag og lavere neuron/token-forbrug i første redaktionelle led uden at svække verifikationsgates.\n"""
    write("reports/editorial/scan-newsdesk-refactor-2026-09-01.md", report)


def patch_workflows() -> None:
    write(".github/workflows/cloudflare-editorial-sync.yml", """name: Cloudflare editorial sync\n\non:\n  schedule:\n    - cron: '4,19,34,49 * * * *'\n  workflow_dispatch:\n    inputs:\n      cycles:\n        description: 'Maximum distinct editorial candidates to process'\n        required: false\n        default: '3'\n\npermissions:\n  contents: write\n\nconcurrency:\n  group: morgentidende-editorial-import\n  cancel-in-progress: false\n\njobs:\n  sync:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n        with:\n          ref: main\n          fetch-depth: 0\n      - name: Sync latest main\n        run: git fetch origin main && git reset --hard origin/main\n      - uses: actions/setup-python@v5\n        with:\n          python-version: '3.12'\n      - name: Install image normalizer\n        run: python -m pip install --disable-pip-version-check pillow\n      - name: Run and import distinct editorial candidates\n        env:\n          INPUT_CYCLES: ${{ github.event.inputs.cycles }}\n        run: |\n          set -euo pipefail\n          BASE='https://morgentidende-newsdesk.nicolaipetersen108.workers.dev'\n          MAX='${INPUT_CYCLES:-3}'\n          case "$MAX" in 1|2|3) ;; *) MAX=3 ;; esac\n          for i in $(seq 1 "$MAX"); do\n            OUT="/tmp/editorial-$i.json"\n            curl --fail --silent --show-error --max-time 240 -X POST "$BASE/run-editorial" -o "$OUT"\n            python -m json.tool "$OUT" >/dev/null\n            jq '{status,stage,generated_at,slug,reason,runtime,handled_signal_keys}' "$OUT"\n            python scripts/log_publication_attempt.py --input "$OUT"\n            python scripts/sync_cloudflare_editorial.py --input "$OUT"\n            HANDLED=$(jq '(.handled_signal_keys // []) | length' "$OUT")\n            STATUS=$(jq -r '.status // "hold"' "$OUT")\n            STAGE=$(jq -r '.stage // ""' "$OUT")\n            if [ "$STAGE" = 'runtime-error' ] || { [ "$HANDLED" -eq 0 ] && [ "$STATUS" != 'approved' ]; }; then\n              echo 'Ingen yderligere distinkt kandidat i denne runde'\n              break\n            fi\n          done\n      - name: Canonical gates before commit\n        run: python scripts/quality_gate.py --prebuild && python scripts/pipeline_v2_gate.py && python scripts/prepublish_surface_qa.py\n      - name: Refresh control room report\n        run: python scripts/build_control_room.py\n      - name: Commit imported packages and attempt log\n        run: |\n          set -euo pipefail\n          git config user.name 'morgentidende-cloudflare-editorial'\n          git config user.email '41898282+github-actions[bot]@users.noreply.github.com'\n          git add content/articles sources reports/editorial/approvals content/frontpage.json docs/img/auto reports/editorial/publication-attempts.jsonl docs/kontrolrum 2>/dev/null || true\n          if git diff --cached --quiet; then\n            echo 'Ingen ny godkendt artikel eller rapport at importere'\n          else\n            git commit -m 'editorial: import cycle results'\n            git pull --rebase origin main\n            git push origin main\n          fi\n""")

    deploy = read(".github/workflows/cloudflare-newsdesk-deploy.yml")
    deploy = deploy.replace("      - 'scripts/apply_newsdesk_neuron_optimization.py'\n      - 'scripts/add_ai_usage_telemetry.py'\n", "")
    deploy = must_sub(
        deploy,
        r"      - name: Apply deterministic neuron optimization and usage telemetry[\s\S]*?\n\n      - name: Deploy Newsdesk Worker",
        "      - name: Validate Newsdesk source\n        run: node --check cloudflare/newsdesk/src/index.js && node --check cloudflare/newsdesk/src/editorial.js\n\n      - name: Deploy Newsdesk Worker",
        "deploy optimizer removal",
    )
    write(".github/workflows/cloudflare-newsdesk-deploy.yml", deploy)


def cleanup_once_files() -> None:
    for rel in ["scripts/_apply_scan_refactor_once.py", ".github/workflows/scan-refactor-once.yml"]:
        p = ROOT / rel
        if p.exists():
            p.unlink()


def main() -> None:
    patch_index()
    patch_editorial()
    patch_sync_validator()
    patch_docs()
    patch_workflows()
    cleanup_once_files()
    print("Scan/Newsdesk refactor applied")


if __name__ == "__main__":
    main()
