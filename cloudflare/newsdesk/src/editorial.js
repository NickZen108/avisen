const FAST_TEXT_MODEL = "@cf/meta/llama-3.1-8b-instruct-fast";
const STRONG_TEXT_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
const IMAGE_MODEL = "@cf/black-forest-labs/flux-1-schnell";
const PUBLIC_BASE = "https://morgentidende-newsdesk.nicolaipetersen108.workers.dev";

const CATEGORIES = ["Danmark", "Udland", "Politik", "Penge", "Krimi", "Videnskab & teknologi", "Sundhed", "Kultur & medier", "Sport", "Liv"];

function nowIso() { return new Date().toISOString(); }
function slugify(value) {
  return String(value || "").toLocaleLowerCase("da-DK").normalize("NFKD")
    .replace(/[æ]/g, "ae").replace(/[ø]/g, "oe").replace(/[å]/g, "aa")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 72);
}
function stripHtml(html) {
  return String(html || "")
    .replace(/<script\b[\s\S]*?<\/script>/gi, " ").replace(/<style\b[\s\S]*?<\/style>/gi, " ")
    .replace(/<nav\b[\s\S]*?<\/nav>/gi, " ").replace(/<footer\b[\s\S]*?<\/footer>/gi, " ")
    .replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&quot;/g, '"')
    .replace(/&#0*39;|&apos;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/\s+/g, " ").trim();
}
function signalKey(signal) { return `${signal?.normalized || slugify(signal?.headline || "")}|${signal?.url || ""}`; }
const PUBLISHER_ROOT_HOSTS = [
  "theguardian.com", "bbc.co.uk", "bbc.com", "politico.eu", "reuters.com", "apnews.com",
  "ft.com", "bloomberg.com", "nytimes.com", "wsj.com", "france24.com", "dw.com", "euronews.com",
  "dr.dk", "tv2.dk", "svt.se", "nrk.no", "aljazeera.com", "sky.com", "skynews.com",
];
function publisherRootHost(value) {
  const host = String(value || "").replace(/^www\./, "").toLowerCase();
  for (const root of PUBLISHER_ROOT_HOSTS) {
    if (host === root || host.endsWith(`.${root}`)) return root;
  }
  return host;
}
function sourceGroup(name, url = null) {
  try { if (url) return `host-${slugify(publisherRootHost(new URL(url).hostname))}`; } catch (_) {}
  return slugify(name || "source") + "-reporting";
}
function wireOrigin(item) {
  const host = hostOf(item?.final_url || item?.url || "");
  const source = String(item?.source || "").toLowerCase().trim();
  if (host === "reuters.com" || host.endsWith(".reuters.com") || source === "reuters" || source === "thomson reuters") return "reuters";
  if (host === "apnews.com" || host.endsWith(".apnews.com") || ["ap", "associated press", "ap news"].includes(source)) return "ap";
  if (["afp", "agence france-presse"].includes(source)) return "afp";
  if (["ritzau", "ritzau bureau"].includes(source)) return "ritzau";
  return null;
}
function evidenceSourceGroup(item) {
  return sourceGroup(item?.source, item?.final_url || item?.url);
}
function provenanceClusters(items) {
  const clusters = [];
  for (let i = 0; i < items.length; i++) {
    let cluster = null;
    for (let j = 0; j < i; j++) {
      const a = `${items[i]?.headline || ""} ${items[i]?.excerpt || items[i]?.description || ""}`;
      const b = `${items[j]?.headline || ""} ${items[j]?.excerpt || items[j]?.description || ""}`;
      if (lexicalSimilarity(a, b) >= 0.90) { cluster = clusters[j]; break; }
    }
    clusters[i] = cluster || `pc-${i + 1}`;
  }
  return clusters;
}
function evidenceAtom(item) {
  if (authoritativePrimary(item)) return `primary:${item?.final_url || item?.url || evidenceSourceGroup(item)}`;
  const wire = wireOrigin(item); if (wire) return `wire:${wire}`;
  if (item?.provenance_cluster) return `cluster:${item.provenance_cluster}`;
  return `publisher:${evidenceSourceGroup(item)}`;
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
    const primary = ["gov.uk", "police.uk", "polizei.berlin.de", "berlin.de", "bund.de", "europa.eu", "ec.europa.eu", "who.int", "un.org",
      "politi.dk", "domstol.dk", "ft.dk", "sst.dk", "ssi.dk", "dst.dk", "forsvaret.dk", "fm.dk", "justitsministeriet.dk", "stm.dk", "um.dk"];
    if (primary.some((x) => host === x || host.endsWith(`.${x}`))) return "primary";
    if (STRONG_EDITORIAL_HOSTS.some((x) => host === x || host.endsWith(`.${x}`))) return "public_media";
  } catch (_) {}
  return null;
}

async function fetchExcerpt(signal) {
  if (signal?.prefetched_excerpt && String(signal.prefetched_excerpt).length >= 160) {
    return {
      ...signal,
      excerpt: String(signal.prefetched_excerpt).slice(0, 12000),
      fetched: true,
      fetch_status: signal.prefetched_status || 200,
      final_url: signal.prefetched_final_url || signal.url,
      outbound_links: Array.isArray(signal.prefetched_outbound_links) ? signal.prefetched_outbound_links.slice(0, 24) : [],
      fetch_origin: "github-actions-prefetch",
    };
  }
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

function responseObject(raw) {
  if (raw && typeof raw.response === "object" && raw.response !== null) return raw.response;
  if (raw && typeof raw.response === "string") { try { return JSON.parse(raw.response); } catch (_) {} }
  if (raw && Array.isArray(raw.choices)) {
    const content = raw.choices[0]?.message?.content;
    if (typeof content === "object" && content) return content;
    if (typeof content === "string") { try { return JSON.parse(content); } catch (_) {} }
  }
  throw new Error("Workers AI returned no parseable structured response");
}

async function aiJson(env, system, user, schema, maxTokens = 2800, model = STRONG_TEXT_MODEL, fallbackModel = null) {
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
    try { env.__AI_FALLBACK_COUNT__ = Number(env.__AI_FALLBACK_COUNT__ || 0) + 1; } catch (_) {}
    const raw = await env.AI.run(fallbackModel, request);
    return responseObject(raw);
  }
}

const assignmentSchema = {
  type: "object", properties: {
    decision: { type: "string", enum: ["research", "watch", "drop"] }, title_hint: { type: "string" },
    category: { type: "string", enum: CATEGORIES }, weight: { type: "string", enum: ["A", "B", "C", "D"] },
    signal_indexes: { type: "array", items: { type: "integer" }, minItems: 0, maxItems: 3 },
    rationale: { type: "string" }, core_question: { type: "string" },
  }, required: ["decision", "title_hint", "category", "weight", "signal_indexes", "rationale", "core_question"],
};

const researchSchema = {
  type: "object", properties: {
    decision: { type: "string", enum: ["continue", "watch"] }, rationale: { type: "string" }, core_question: { type: "string" },
    right_of_reply_required: { type: "boolean" }, conflict_present: { type: "boolean" }, contradictions: { type: "array", items: { type: "string" } },
    candidate_claims: { type: "array", minItems: 1, maxItems: 8, items: { type: "object", properties: {
      id: { type: "string" }, claim: { type: "string" }, source_indexes: { type: "array", items: { type: "integer" }, minItems: 1 },
      notes: { type: "string" },
    }, required: ["id", "claim", "source_indexes", "notes"] } },
  }, required: ["decision", "rationale", "core_question", "right_of_reply_required", "conflict_present", "contradictions", "candidate_claims"],
};

const factCheckSchema = {
  type: "object", properties: {
    decision: { type: "string", enum: ["publish", "hold"] }, rationale: { type: "string" },
    contradictions: { type: "array", items: { type: "string" } },
    claims: { type: "array", minItems: 1, maxItems: 12, items: { type: "object", properties: {
      id: { type: "string" }, claim: { type: "string" }, source_indexes: { type: "array", items: { type: "integer" }, minItems: 1 },
      status: { type: "string", enum: ["verified", "uncertain", "rejected"] }, notes: { type: "string" },
    }, required: ["id", "claim", "source_indexes", "status", "notes"] } },
  }, required: ["decision", "rationale", "contradictions", "claims"],
};

const deskRecheckSchema = { type: "object", properties: {
  decision: { type: "string", enum: ["publish", "update", "hold", "kill"] }, rationale: { type: "string" },
}, required: ["decision", "rationale"] };

const articleSchema = { type: "object", properties: {
  title: { type: "string" }, standfirst: { type: "string" },
  body: { type: "array", minItems: 3, maxItems: 14, items: { type: "object", properties: {
    type: { type: "string", enum: ["p", "h2", "h3"] }, text: { type: "string" },
  }, required: ["type", "text"] } },
  seo_title: { type: "string" }, seo_description: { type: "string" },
}, required: ["title", "standfirst", "body", "seo_title", "seo_description"] };

const finalSchema = { type: "object", properties: {
  blocking_issues: { type: "array", maxItems: 10, items: { type: "object", properties: {
    gate: { type: "string", enum: ["language", "ethics", "image", "seo", "final_editor"] }, issue: { type: "string" },
  }, required: ["gate", "issue"] } },
}, required: ["blocking_issues"] };

const EDITORIAL_LENS = [
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
    if (chosen.length >= 4) break;
    if ((perSource.get(item.s.source) || 0) >= 1) continue;
    chosen.push(item); usedIndexes.add(item.i); perSource.set(item.s.source, 1);
  }
  for (const item of ranked) {
    if (chosen.length >= 20) break;
    if (usedIndexes.has(item.i)) continue;
    const used = perSource.get(item.s.source) || 0;
    if (used >= 3) continue;
    chosen.push(item); usedIndexes.add(item.i); perSource.set(item.s.source, used + 1);
  }
  chosen.sort((a, b) => b.score - a.score || b.published - a.published || a.i - b.i);
  return chosen.map(({ s, i, score }) => ({
    i, source: s.source, headline: s.headline, description: (s.description || "").slice(0, 160),
    published_at: s.published_at || null, source_class: s.source_class || "news", region: s.region || null,
    discovery_only: Boolean(s.discovery_only), score,
  }));
}
async function chooseAssignment(env, scan, excludedSignalKeys = []) {
  const signals = signalSummary(scan, excludedSignalKeys);
  if (!signals.length) return { decision: "drop", title_hint: "", category: "Danmark", weight: "D", signal_indexes: [], rationale: "Ingen ubehandlede kandidater med tilstrækkelig aktualitet/grundscore", core_question: "" };
  const system = `Du er Morgentidendes første Nyhedsdesk. Vælg ét konkret research-frø. RESEARCH er standard ved reel nyhedsværdi, originalitet, offentlig betydning eller tydelig redaktionel relevans; tynd dokumentation er Researchs problem, ikke en afvisningsgrund. WATCH kun hvis nyhedskrogen/aktualiteten endnu er uklar. DROP kun ved klar dublet, gammel/triviel sag, rent holdningsstof uden nyhedskrog eller åbenlys spam. discovery_only må udløse Research, men er aldrig dokumentation. Sæt kategori og A-D-vægt. Svar ultrakort.`;
  return aiJson(env, system, JSON.stringify({ generated_at: scan.generated_at, signals }), assignmentSchema, 260, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
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
    if (selected.length >= 5) break;
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
const DISCOVERY_ONLY_HOSTS = new Set([
  "indblik.dk", "document.no", "timbro.se", "achgut.com", "tichyseinblick.de", "causeur.fr", "contrepoints.org",
  "spiked-online.com", "capx.co", "unherd.com", "reason.com", "nationalreview.com", "city-journal.org",
  "thefederalist.com", "frontpagemag.com", "jihadwatch.org",
]);
function hostOf(value) { try { return new URL(value).hostname.replace(/^www\./, "").toLowerCase(); } catch (_) { return ""; } }
function isDiscoveryOnly(item) {
  if (!item) return false;
  if (item.discovery_only || /discovery/i.test(item.source_class || "") || item.source_role === "discovery") return true;
  return DISCOVERY_ONLY_HOSTS.has(hostOf(item.final_url || item.url || ""));
}
function isUtilityOrAccountUrl(value) {
  try {
    const u = new URL(value);
    const host = u.hostname.replace(/^www\./, "").toLowerCase();
    const first = host.split(".")[0];
    if (["support", "profile", "account", "accounts", "auth", "login", "subscribe", "subscriptions", "shop", "store", "help"].includes(first)) return true;
    return /\/(?:signin|login|subscribe|subscription|support|account|accounts|register|newsletter|privacy|terms)(?:\/|$)/i.test(u.pathname);
  } catch (_) { return false; }
}
function isEvidenceSource(item) {
  if (!item || isDiscoveryOnly(item)) return false;
  return !isUtilityOrAccountUrl(item.final_url || item.url || "");
}
function authoritativePrimary(item) { return isEvidenceSource(item) && item.source_kind === "primary"; }

const STRONG_EDITORIAL_HOSTS = [
  "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "dr.dk", "tv2.dk", "svt.se", "nrk.no",
  "ft.com", "politico.eu", "bloomberg.com", "theguardian.com", "nytimes.com", "wsj.com",
  "france24.com", "tagesschau.de", "rbb24.de", "itv.com",
];
function strongEditorialSource(item) {
  if (!isEvidenceSource(item)) return false;
  const group = evidenceSourceGroup(item);
  if (["wire-reuters", "wire-ap", "wire-afp", "wire-ritzau"].includes(group)) return true;
  const host = hostOf(item?.final_url || item?.url || "");
  if (STRONG_EDITORIAL_HOSTS.some((x) => host === x || host.endsWith(`.${x}`))) return true;
  const source = String(item?.source || "").toLowerCase().trim();
  return ["reuters", "ap", "associated press", "afp", "ritzau", "bbc", "dr", "tv 2", "tv2", "svt", "nrk", "financial times", "politico"].includes(source);
}
function authoritativeEditorial(item) {
  return Boolean(wireOrigin(item));
}
function normalizedSourceKind(item) {
  if (authoritativePrimary(item)) return "primary";
  const kind = trustedExpansionKind(item?.final_url || item?.url || "");
  if (kind === "primary") return "primary";
  if (kind === "public_media" || strongEditorialSource(item)) return "strong_editorial";
  return item?.source_kind || "news";
}
function evidenceGroups(items) { return [...new Set(items.filter(isEvidenceSource).map(evidenceSourceGroup))]; }

const HIGH_RISK_FACT_TERMS = /\b(sigtet|tiltalt|anklag|mistænkt|voldtægt|seksual|misbrug|selvmord|mindreår|barn|børn|privat helbred|diagnose|terror|drab|korruption|svindel|hvidvask|overgreb|racist|ekstremist)\b/iu;
function highRiskFactClaim(assignment, research, claim) {
  if (research?.right_of_reply_required) return true;
  return HIGH_RISK_FACT_TERMS.test(`${assignment?.title_hint || ""} ${assignment?.core_question || ""} ${claim?.claim || ""}`);
}
function namedAccusedCrimeClaim(assignment, claim) {
  const text = String(claim?.claim || "");
  if (!/\b(sigtet|tiltalt|mistænkt|anklaget)\b/iu.test(text)) return false;
  return /\b[A-ZÆØÅ][a-zæøåéèáàíìóòúù-]+\s+[A-ZÆØÅ][a-zæøåéèáàíìóòúù-]+\b/u.test(text);
}
function numericMaterialClaim(claim) {
  return /\b\d+(?:[.,]\d+)?(?:\s?%|\s?(?:million|milliard|kr\.?|kroner|euro|dollar|døde|dræbte|savnet|procent))?\b/iu.test(String(claim?.claim || ""));
}
function evidenceRulePass(assignment, research, claim, evidence) {
  const primaryOk = evidence.some(authoritativePrimary);
  if (namedAccusedCrimeClaim(assignment, claim)) return primaryOk;
  const wireOk = evidence.some(authoritativeEditorial);
  const atoms = new Set(evidence.map(evidenceAtom).filter(Boolean));
  if (highRiskFactClaim(assignment, research, claim)) return primaryOk || atoms.size >= 2;
  return primaryOk || wireOk || atoms.size >= 2;
}

async function runResearch(env, assignment, selected) {
  let researched = await Promise.all(selected.map(fetchExcerpt));
  researched = researched.map((item) => ({ ...item, source_kind: normalizedSourceKind(item) }));

  // If a strong original newsroom blocks full-page fetching, its own RSS/feed summary can
  // still support a short, explicitly attributed low-risk claim. Generic/unknown feeds do not get this fallback.
  researched = researched.map((item) => {
    const strong = authoritativePrimary(item) || strongEditorialSource(item);
    const minChars = strong ? 80 : 120;
    if ((item.excerpt || "").length >= minChars) return item;
    const summary = `${item.headline || ""}. ${item.description || ""}`.trim();
    if (strong && summary.length >= 80) {
      return { ...item, excerpt: summary.slice(0, 1200), feed_summary_only: true };
    }
    return item;
  });
  let usable = researched.filter((x) => {
    const minChars = (authoritativePrimary(x) || strongEditorialSource(x)) ? 80 : 120;
    return (x.excerpt || "").length >= minChars;
  });

  // Cheap deterministic expansion before spending AI: when the seed set lacks strong
  // corroboration, follow a few clearly trusted primary/public-media links already found
  // on the fetched pages. Discovery sources remain leads only, never evidence.
  let evidenceUsable = usable.filter(isEvidenceSource);
  if (!evidenceUsable.some(authoritativePrimary) || evidenceGroups(evidenceUsable).length < 2) {
    const seen = new Set(usable.map((x) => x.final_url || x.url).filter(Boolean));
    const links = [];
    for (const item of usable) {
      for (const link of item.outbound_links || []) {
        const kind = trustedExpansionKind(link.url);
        if (!kind || seen.has(link.url)) continue;
        seen.add(link.url);
        links.push({
          url: link.url,
          headline: link.text || item.headline || "Original source",
          description: "",
          source: hostOf(link.url) || "linked-source",
          source_kind: kind === "primary" ? "primary" : "strong_editorial",
          source_class: kind,
          discovery_only: false,
        });
      }
    }
    links.sort((a, b) => Number(b.source_kind === "primary") - Number(a.source_kind === "primary"));
    if (links.length) {
      const expanded = await Promise.all(links.slice(0, 4).map(fetchExcerpt));
      usable = usable.concat(expanded.map((x) => ({ ...x, source_kind: normalizedSourceKind(x) })).filter((x) => {
        const minChars = (authoritativePrimary(x) || strongEditorialSource(x)) ? 80 : 120;
        return (x.excerpt || "").length >= minChars;
      }));
      evidenceUsable = usable.filter(isEvidenceSource);
    }
  }

  // Research no longer rejects a promising story merely because corroboration is not
  // already present. Fact checker owns the evidence verdict. We stop only if there is
  // literally no usable evidence source after the cheap expansion attempt.
  if (!evidenceUsable.length) {
    return { decision: "watch", rationale: "Ingen brugbar dokumentationskilde kunne hentes endnu", researched, candidate_claims: [], contradictions: [], right_of_reply_required: false, conflict_present: false };
  }

  const unique = [];
  const seenUrls = new Set();
  const prioritized = [...evidenceUsable].sort((a, b) =>
    Number(authoritativePrimary(b)) - Number(authoritativePrimary(a)) ||
    Number(strongEditorialSource(b)) - Number(strongEditorialSource(a))
  );
  for (const item of prioritized) {
    const url = item.final_url || item.url;
    if (!url || seenUrls.has(url)) continue;
    seenUrls.add(url);
    unique.push(item);
    if (unique.length >= 4) break;
  }

  const researchClusters = provenanceClusters(unique);
  unique.forEach((item, i) => { item.provenance_cluster = researchClusters[i]; });
  const sources = unique.map((item, i) => ({
    source_index: i,
    name: item.source,
    headline: item.headline,
    url: item.final_url || item.url,
    excerpt: item.excerpt.slice(0, 1800),
    discovery_only: false,
    source_kind: normalizedSourceKind(item),
    source_strength: authoritativePrimary(item) ? "primary" : authoritativeEditorial(item) ? "wire" : strongEditorialSource(item) ? "strong_editorial" : "standard",
    feed_summary_only: Boolean(item.feed_summary_only),
  }));
  const system = `Du er Research på Morgentidende. Lav et kompakt evidens-kort til Fact checker; vurder ikke nyhedsværdi igen og fæld ikke den endelige sandhedsdom. Kortlæg 1-6 bærende kandidat-claims med præcise source_indexes. Notér kun reelle modsigelser, væsentlige forbehold og nødvendig kontekst. En primærkilde er værdifuld, men du skal ikke kræve et bestemt antal medier. Hvis mindst ét brugbart claim kan kildebelægges, vælg continue; watch kun hvis materialet reelt ikke giver noget kontrollerbart. Flag alvorlige belastende påstande via right_of_reply_required, men brug ikke flaget som stopregel. Sæt conflict_present=true kun når historien faktisk rummer en relevant politisk, juridisk, faglig eller parts-konflikt; almindelige hændelsesfakta/statistik kræver ikke kunstig pluralisme. Opfind intet.`;
  const research = await aiJson(env, system, JSON.stringify({ assignment, sources }), researchSchema, 650, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
  research.researched = unique;
  research.source_payload = sources;
  return research;
}

function focusedExcerpt(text, claims, maxChars = 1800) {
  const raw = String(text || "");
  if (raw.length <= maxChars) return raw;
  const terms = [...new Set((claims || []).flatMap((x) => words(x?.claim || "")).filter((x) => x.length >= 5))];
  const lower = raw.toLocaleLowerCase("da-DK");
  let hit = -1;
  for (const term of terms) {
    const pos = lower.indexOf(term.toLocaleLowerCase("da-DK"));
    if (pos >= 0 && (hit < 0 || pos < hit)) hit = pos;
  }
  if (hit < 0) return raw.slice(0, maxChars);
  const start = Math.max(0, Math.min(raw.length - maxChars, hit - Math.floor(maxChars * 0.3)));
  return raw.slice(start, start + maxChars);
}

async function runFactCheck(env, assignment, research) {
  if ((research.researched || []).some(isDiscoveryOnly)) throw new Error("Discovery-only source crossed the Research/Fact-check boundary");
  const system = `Du er en UAFHÆNGIG Fact checker på Morgentidende. Forsøg aktivt at falsificere hvert kandidat-claim mod de vedlagte kildetekster. Discovery-blogs og perspektiv/advocacy-feeds er fjernet før dette trin og må aldrig bruges som kilder. For almindelige lavrisiko-fakta kan Verified bæres af én autoritativ primærkilde inden for dens kompetenceområde, én dokumenteret original bureaukilde (Reuters/AP/AFP/Ritzau), eller to provenance-uafhængige troværdige evidenskilder. Ét almindeligt redaktionelt medie kan ikke stå alene. Ved højrisiko kræves primærkilde eller mindst to provenance-uafhængige evidenskilder. Samme bureau/pressemeddelelse tæller kun én gang. Ved højrisiko/fairness-påstande skal du være mere forsigtig og ikke lade én almindelig redaktionel kilde stå alene. Ved navngivne sigtede/tiltalte/mistænkte i kriminalstof kræves en relevant primærkilde fra politi/ret/myndighed. For alle materielle tal (døde, penge, procent, antal osv.) skal du aktivt sammenligne/falsificere tallet mod alle vedlagte relevante kilder; ved mismatch skal claimet være uncertain eller formuleres forsigtigt/attribueret, aldrig vælg automatisk det højeste tal. Rejected når evidensen modsiger claimet; ellers uncertain. Ét verificeret bærende claim er nok til en kort one-claim-artikel; usikre sekundære detaljer skal blot udelades. Opfind ingen nye kilder eller fakta. Din overordnede publish/hold-vurdering er rådgivende; en deterministisk gate beregner den endelige beslutning efter claim-kontrollen.`;
  const fact = await aiJson(env, system, JSON.stringify({
    assignment,
    research: { core_question: research.core_question, rationale: research.rationale, contradictions: research.contradictions, candidate_claims: research.candidate_claims },
    sources: (research.source_payload || []).map((source, i) => ({
      ...source,
      excerpt: focusedExcerpt(research.researched?.[i]?.excerpt || source.excerpt, research.candidate_claims, 1800),
    })),
  }), factCheckSchema, 850, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
  fact.researched = research.researched;
  fact.core_question = research.core_question || assignment.core_question;
  fact.right_of_reply_required = research.right_of_reply_required;
  fact.conflict_present = Boolean(research.conflict_present);
  for (const claim of fact.claims) {
    const indexes = [...new Set((claim.source_indexes || []).filter((i) => Number.isInteger(i) && i >= 0 && i < fact.researched.length))];
    claim.source_indexes = indexes;
    const evidence = indexes.map((i) => fact.researched[i]).filter(isEvidenceSource);
    claim.numeric_material = numericMaterialClaim(claim);
    claim.named_accused_primary_required = namedAccusedCrimeClaim(assignment, claim);
    if (claim.status === "verified" && !evidenceRulePass(assignment, research, claim, evidence)) {
      claim.status = "uncertain";
      claim.notes = `${claim.notes || ""} Nedgraderet af deterministisk gate: dokumentationen opfylder ikke kildekravet for claimets risikoniveau.`.trim();
    }
  }
  const verified = fact.claims.filter((c) => c.status === "verified");
  const modelRationale = fact.rationale || "";
  fact.model_rationale = modelRationale;
  fact.decision = verified.length >= 1 ? "publish" : "hold";
  fact.rationale = verified.length >= 1
    ? `Deterministisk Fact checker: ${verified.length} bærende claim(s) verificeret; usikre eller afviste detaljer udelades fra artiklen.`
    : "Deterministisk Fact checker: ingen bærende claims opfylder dokumentationskravet.";
  return fact;
}

async function deskRecheck(env, assignment, dossier) {
  // B-D stories were just accepted by Newsdesk and Fact checker; repeating that judgement
  // costs an extra model call without new information. Keep only a tiny A/breaking staleness check.
  if (assignment.weight !== "A") {
    return { decision: "publish", rationale: "Fact check bestået; intet særskilt A-recheck nødvendigt" };
  }
  const system = `Du er Nyhedsdesk ved et ultrakort A/breaking-recheck efter bestået Fact check. Genresearch ikke. Hold/kill kun hvis materialet viser, at nyhedskernen siden assignment er blevet materielt forældet eller har skiftet karakter. Ellers publish. Svar kort.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), contradictions: dossier.contradictions }), deskRecheckSchema, 140, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
}

async function writeArticle(env, assignment, dossier) {
  if ((dossier.researched || []).some(isDiscoveryOnly)) throw new Error("Discovery-only source crossed the Journalist boundary");
  const sources = dossier.researched.filter(isEvidenceSource).map((s, i) => ({ source_index: i, name: s.source, headline: s.headline, url: s.final_url || s.url }));
  const system = `Du er journalist på Morgentidende. Skriv præcist og levende dansk, men brug KUN verificerede claims. Gør attribution tydelig og brug gerne korte, præcise citater når de faktisk findes i det verificerede materiale; opfind aldrig citater. Hvis research har conflict_present=true, tilstræb relevant pluralisme mellem reelle parter/synsvinkler ud fra verificeret materiale. Hvis conflict_present=false, må du ikke konstruere kunstig pluralisme. Skriv til almindelige læsere: erstat fagord og engelske brancheord med almindeligt dansk, forklar nødvendige tekniske begreber første gang med 1-2 korte sætninger, og omsæt uvante mål til fx kilometer, meter, Celsius og kilogram. En kort one-claim-nyhed med tre meningsfulde tekstblokke er fuldt acceptabel; fyld aldrig ud. Media ejer heroen; skriv ingen billedprompt eller billedmetadata.`;
  return aiJson(env, system, JSON.stringify({ assignment, conflict_present: Boolean(dossier.conflict_present), verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources }), articleSchema, assignment.weight === "A" || assignment.weight === "B" ? 2200 : 1400, assignment.weight === "A" || assignment.weight === "B" ? STRONG_TEXT_MODEL : FAST_TEXT_MODEL, assignment.weight === "A" || assignment.weight === "B" ? null : STRONG_TEXT_MODEL);
}

function deterministicFinalReview(assignment, dossier, article) {
  const issues = [];
  const add = (gate, issue) => issues.push({ gate, issue });
  if (!String(article?.title || "").trim()) add("language", "Titel mangler");
  if (!String(article?.standfirst || "").trim()) add("language", "Standfirst mangler");
  const body = Array.isArray(article?.body) ? article.body : [];
  if (body.length < 3) add("final_editor", "Færre end tre meningsfulde tekstblokke");
  for (const block of body) {
    if (!["p", "h2", "h3"].includes(block?.type) || !String(block?.text || "").trim()) {
      add("final_editor", "Ugyldig eller tom tekstblok");
      break;
    }
  }
  // SEO og hero-polish repareres/valideres af deres egne deterministiske trin og er ikke redaktionelle hard stops her.
  const failed = new Set(issues.map((x) => x.gate));
  return {
    decision: issues.length ? "hold" : "pass",
    language: failed.has("language") ? "hold" : "pass",
    ethics: "pass",
    image: failed.has("image") ? "hold" : "pass",
    seo: failed.has("seo") ? "hold" : "pass",
    final_editor: failed.has("final_editor") ? "hold" : "pass",
    issues,
    notes: issues.map((x) => `${x.gate}: ${x.issue}`),
    mode: "deterministic-low-risk",
  };
}
function requiresAiFinalReview(assignment, dossier, article) {
  if (["A", "B"].includes(assignment?.weight)) return true;
  if (dossier?.right_of_reply_required) return true;
  if ((dossier?.contradictions || []).length) return true;
  const text = [
    assignment?.title_hint, assignment?.core_question, article?.title, article?.standfirst,
    ...(article?.body || []).map((b) => b?.text || ""),
  ].join(" ").toLocaleLowerCase("da-DK");
  return /\b(sigtet|tiltalt|anklag|voldtægt|seksual|selvmord|mindreår|barnet|børn|privat helbred|diagnose|terror|drab|korruption)\b/u.test(text);
}

async function finalReview(env, assignment, dossier, article) {
  const system = `Du er uafhængig slutredaktør. Kontrollér den færdige artikel mod de verificerede claims uden at genresearche. Returnér kun reelle sikkerheds-/sandhedsproblemer som blockers: materielle påstande ud over dokumentationen, vildledende attribution, relevant men manglende fairness/pluralisme ved conflict_present=true, eller etisk problem. Sprog og SEO er repair/polish og må ikke i sig selv blokere. Media ejer hero og billedsandhed. Små stilpræferencer er aldrig blockers.`;
  const raw = await aiJson(env, system, JSON.stringify({ assignment, claims: dossier.claims, contradictions: dossier.contradictions, article }), finalSchema, 450, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
  const issues = Array.isArray(raw.blocking_issues) ? raw.blocking_issues.filter((x) => x?.gate && x?.issue) : [];
  const failed = new Set(issues.map((x) => x.gate));
  return { decision: issues.length ? "hold" : "pass", language: failed.has("language") ? "hold" : "pass", ethics: failed.has("ethics") ? "hold" : "pass", image: failed.has("image") ? "hold" : "pass", seo: failed.has("seo") ? "hold" : "pass", final_editor: failed.has("final_editor") ? "hold" : "pass", issues, notes: issues.map((x) => `${x.gate}: ${x.issue}`) };
}
async function reviseFixableIssues(env, assignment, dossier, article, review) {
  const fixable = (review.issues || []).filter((x) => ["language", "seo"].includes(x.gate));
  const hard = (review.issues || []).filter((x) => !["language", "seo"].includes(x.gate));
  if (!fixable.length || hard.length) return article;
  const system = `Ret KUN de konkrete language/seo-problemer. Bevar verificerede fakta, vinkel og betydning. Tilføj ingen nye claims. Lægmandssprog og metriske enheder er obligatoriske.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), article, issues: fixable }), articleSchema, 2400, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
}
const DOCUMENTARY_CONTEXTS = new Set(["event", "place", "person", "object", "archive"]);
function validDocumentaryHero(media) {
  if (!media || typeof media !== "object") return false;
  if (!["photo", "video_still"].includes(media.image_type)) return false;
  if (!DOCUMENTARY_CONTEXTS.has(String(media.context_type || ""))) return false;
  if (!/^https:\/\//i.test(String(media.src || ""))) return false;
  if (!/^https:\/\//i.test(String(media.source_url || ""))) return false;
  if (!String(media.alt || "").trim() || !String(media.credit || "").trim() || !String(media.license || "").trim()) return false;
  const license = String(media.license || "").toLowerCase();
  if (["unknown", "ukendt", "tbd", "n/a"].includes(license)) return false;
  if (media.context_type !== "event" && !String(media.caption || "").trim()) return false;
  const host = hostOf(media.source_url);
  if (media.image_type === "video_still" && (host === "youtube.com" || host.endsWith(".youtube.com") || host === "youtu.be")) {
    if (!String(media.rights_basis || "").trim()) return false;
  }
  return true;
}

function documentaryHeroFromSignals(selected = []) {
  const candidates = [];
  for (const signal of selected || []) {
    const candidate = signal?.documentary_hero || signal?.documentary_media || null;
    if (!validDocumentaryHero(candidate)) continue;
    // A discovery-only feed may point us toward media, but it is not itself a
    // usable image source unless the candidate carries an independent licence.
    if (isDiscoveryOnly(signal) && candidate.independent_license !== true) continue;
    const signalIsPrimary = trustedExpansionKind(signal?.final_url || signal?.url || "") === "primary";
    const score = candidate.context_type === "event" ? 30 : signalIsPrimary ? 20 : 10;
    candidates.push({ score, candidate });
  }
  candidates.sort((a, b) => b.score - a.score);
  const chosen = candidates.find((x) => x.score >= 20);
  const candidate = chosen?.candidate;
  if (!candidate) return null;
  return {
    src: candidate.src,
    alt: candidate.alt,
    credit: candidate.credit,
    license: candidate.license,
    source_url: candidate.source_url,
    image_type: candidate.image_type,
    context_type: candidate.context_type,
    caption: candidate.caption || (candidate.image_type === "video_still" ? "Video-still fra den angivne kilde." : candidate.context_type === "event" ? "Foto fra hændelsen." : "Kontekstfoto – billedet viser ikke nødvendigvis selve hændelsen."),
    rights_basis: candidate.rights_basis || null,
    discovery_only_source: Boolean(isDiscoveryOnly((selected || []).find((s) => (s?.documentary_hero || s?.documentary_media) === candidate))),
    independent_license: candidate.independent_license === true,
    pending_image: false,
    ai_generated: false,
    contains_people: Boolean(candidate.contains_people),
    placement: "lead",
  };
}

function temporarySketchPrompt(assignment, article) {
  const subject = [assignment?.core_question, assignment?.title_hint, article?.title, article?.standfirst].filter(Boolean).join(". ").slice(0, 1200);
  return `Black-and-white editorial pencil hatching illustration, newspaper sketch, wide 16:9. Subject context: ${subject}. Clearly hand-drawn graphite/pencil cross-hatching, restrained, symbolic and non-literal. NO photorealism, NO realistic photography, NO documentary-photo aesthetic, NO camera realism, NO text, NO logos, NO watermarks. NO people, NO faces, NO human figures. Do not recreate a concrete accident/crime scene as if witnessed. Do not depict a named accused person, a child, victims, injured or dead people. Use only place/object/geographic/symbolic motifs.`;
}

function staticPencilFallbackBase64() {
  // Deterministic 1024x576 1-bit PBM: abstract hatch/place motif, no people,
  // no text and no attempt to depict the event. Kept tiny and independent of AI quota.
  const width = 1024, height = 576, rowBytes = width >> 3;
  const header = `P4\n${width} ${height}\n`;
  const bytes = new Uint8Array(header.length + rowBytes * height);
  for (let i = 0; i < header.length; i++) bytes[i] = header.charCodeAt(i);
  const offset = header.length;
  const setPixel = (x, y) => {
    if (x < 0 || y < 0 || x >= width || y >= height) return;
    bytes[offset + y * rowBytes + (x >> 3)] |= (1 << (7 - (x & 7)));
  };
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const hatch = ((x + y) % 31 === 0) || ((x - y + 4096) % 47 === 0);
      const ground = y > 470 && y % 11 === 0;
      const frame = (y === 354 || y === 470) && x > 70 && x < 954;
      if (hatch || ground || frame) setPixel(x, y);
    }
  }
  for (let bx = 105, n = 0; bx < 900; bx += 105, n++) {
    const top = 300 - (n % 3) * 22;
    for (let x = bx; x <= bx + 58; x++) { setPixel(x, top); setPixel(x, 470); }
    for (let y = top; y <= 470; y++) { setPixel(bx, y); setPixel(bx + 58, y); }
  }
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  return btoa(binary);
}

async function generateTemporarySketch(env, assignment, article) {
  try {
    const raw = await env.AI.run(IMAGE_MODEL, { prompt: temporarySketchPrompt(assignment, article) });
    if (!raw?.image || typeof raw.image !== "string") throw new Error("Temporary sketch model returned no base64 image");
    return { base64: raw.image, content_type: "image/jpeg", ai_generated: true, generator: "workers_ai_flux" };
  } catch (error) {
    console.warn("Temporary sketch AI unavailable; using static pencil fallback", String(error));
    return { base64: staticPencilFallbackBase64(), content_type: "image/x-portable-bitmap", ai_generated: false, generator: "static_pencil_fallback" };
  }
}

function pendingSketchHero(imageKey, article, sketch) {
  return {
    src: `/img/auto/${imageKey}`,
    alt: `Illustration til: ${article.title}`,
    credit: "Illustration: Morgentidende",
    license: sketch?.ai_generated ? "Morgentidende – AI-genereret illustration" : "Morgentidende – statisk illustration",
    source_url: publicMediaUrl(imageKey),
    image_type: "illustration",
    context_type: "illustration",
    caption: "Illustration",
    pending_image: true,
    ai_generated: Boolean(sketch?.ai_generated),
    generator: sketch?.generator || "workers_ai_flux",
    contains_people: false,
    people_style: "pencil_hatching",
    photorealistic: false,
    placement: "lead",
  };
}

function contextualHeroFromSignals(selected = []) {
  for (const signal of selected || []) {
    const candidate = signal?.documentary_hero || signal?.documentary_media || null;
    if (!validDocumentaryHero(candidate) || candidate.context_type === "event") continue;
    if (isDiscoveryOnly(signal) && candidate.independent_license !== true) continue;
    if (trustedExpansionKind(signal?.final_url || signal?.url || "") === "primary") continue;
    return {
      src: candidate.src,
      alt: candidate.alt,
      credit: candidate.credit,
      license: candidate.license,
      source_url: candidate.source_url,
      image_type: candidate.image_type,
      context_type: candidate.context_type,
      caption: candidate.caption || "Kontekstfoto – billedet viser ikke nødvendigvis selve hændelsen.",
      rights_basis: candidate.rights_basis || null,
      discovery_only_source: Boolean(isDiscoveryOnly(signal)),
      independent_license: candidate.independent_license === true,
      pending_image: false,
      ai_generated: false,
      contains_people: Boolean(candidate.contains_people),
      placement: "lead",
    };
  }
  return null;
}

async function resolveDocumentaryHero(selected, assignment, research) {
  // Single deterministic scout per cycle, after Fact check and before Journalist:
  // event/official signal media -> Commons -> lawful contextual signal media.
  let hero = documentaryHeroFromSignals(selected);
  if (hero) return hero;
  hero = await findCommonsDocumentaryHero(
    assignment,
    {
      title: assignment?.title_hint || "",
      standfirst: (research?.candidate_claims || []).map((x) => x.claim).join(" "),
    },
    research
  );
  if (hero) return hero;
  return contextualHeroFromSignals(selected);
}

function commonsSearchQueries(assignment, article, research = null) {
  const stop = new Set(["mener","siger","efter","over","under","vil","kan","skal","med","fra","til","for","the","and","with","from","says","after","over"]);
  const clean = (value, limit = 7) => words(value).filter((x) => x.length >= 4 && !stop.has(x)).slice(0, limit).join(" ");
  const claims = (research?.candidate_claims || []).map((x) => x.claim).join(" ");
  const raw = [
    clean(`${assignment?.title_hint || ""} ${article?.title || ""}`, 7),
    clean(assignment?.title_hint || article?.title || "", 5),
    clean(assignment?.core_question || "", 5),
    clean(claims, 5),
    clean(article?.standfirst || "", 5),
  ].filter((x) => x && x.length >= 4);
  return [...new Set(raw)].slice(0, 5);
}

function stripCommonsHtml(value) {
  return stripHtml(String(value || "")).slice(0, 500);
}

function commonsLicenseAllowed(value) {
  const v = String(value || "").toLowerCase();
  return /\b(cc0|cc by|cc-by|cc by-sa|cc-by-sa|public domain|pd-)\b/.test(v);
}

async function findCommonsDocumentaryHero(assignment, article, research = null) {
  const queries = commonsSearchQueries(assignment, article, research);
  if (!queries.length) return null;
  for (const q of queries) {
  const params = new URLSearchParams({
    action: "query",
    format: "json",
    origin: "*",
    generator: "search",
    gsrnamespace: "6",
    gsrsearch: q,
    gsrlimit: "8",
    prop: "imageinfo",
    iiprop: "url|mime|size|extmetadata",
  });
  try {
    const res = await fetch(`https://commons.wikimedia.org/w/api.php?${params}`, {
      headers: { "user-agent": "MorgentidendeMediaDesk/1.0" },
      cf: { cacheTtl: 300, cacheEverything: true },
    });
    if (!res.ok) continue;
    const payload = await res.json();
    const pages = Object.values(payload?.query?.pages || {});
    const queryTerms = new Set(words(q));
    const ranked = [];
    for (const page of pages) {
      const info = page?.imageinfo?.[0];
      const meta = info?.extmetadata || {};
      const license = meta.LicenseShortName?.value || meta.UsageTerms?.value || "";
      if (!info?.url || info?.mime !== "image/jpeg" || !commonsLicenseAllowed(license)) continue;
      if ((info.width || 0) < 800 || (info.height || 0) < 450) continue;
      const desc = stripCommonsHtml(meta.ImageDescription?.value || "");
      const title = String(page?.title || "").replace(/^File:/i, "");
      const candidateWords = new Set(words(`${title} ${desc}`));
      let overlap = 0;
      for (const term of queryTerms) if (candidateWords.has(term)) overlap += 1;
      const minOverlap = queryTerms.size <= 1 ? 1 : 2;
      if (overlap < minOverlap) continue;
      const credit = stripCommonsHtml(meta.Artist?.value || meta.Credit?.value || "Wikimedia Commons");
      ranked.push({
        score: overlap,
        hero: {
          src: info.thumburl || info.url,
          alt: desc || title,
          credit: credit || "Wikimedia Commons",
          license: stripCommonsHtml(license),
          source_url: info.descriptionurl || `https://commons.wikimedia.org/wiki/${encodeURIComponent(page.title)}`,
          image_type: "photo",
          context_type: "archive",
          caption: "Arkivfoto – billedet viser ikke nødvendigvis selve hændelsen.",
          pending_image: false,
          ai_generated: false,
          placement: "lead",
        },
      });
    }
    ranked.sort((a, b) => b.score - a.score);
    if (ranked[0]?.hero) return ranked[0].hero;
  } catch (_) {}
  }
  return null;
}


function makeLedger(storyId, slug, assignment, dossier, desk, accessedAt) {
  if ((dossier.researched || []).some(isDiscoveryOnly)) throw new Error("Discovery-only source crossed the publication ledger boundary");
  const evidenceRows = dossier.researched.filter(isEvidenceSource);
  const clusters = provenanceClusters(evidenceRows);
  const sources = evidenceRows.map((s, i) => {
    const url = s.final_url || s.url;
    const primary = s.source_kind === "primary" && !s.discovery_only;
    const publisher = evidenceSourceGroup(s);
    const wire = wireOrigin(s);
    return { id: `S${i + 1}`, name: s.source, url, published_at: s.published_at || null, accessed_at: accessedAt, type: primary ? "primary" : "news", source_group: publisher, publisher_root: publisher.replace(/^host-/, ""), wire_origin: wire, provenance_type: primary ? "primary_record" : wire ? "wire_original" : "reporting", provenance_cluster: clusters[i], primary_record: primary ? url : null, authoritative_for: primary ? (s.headline || "Primary record") : (s.headline || "Independent coverage"), discovery_only: Boolean(s.discovery_only) };
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
    coverage_sweep: { status: groups.length >= 1 ? "pass" : "limited", editorial_source_ids: verificationSources.slice(0, 6).map((s) => s.id), independent_source_groups: groups.slice(0, 6), limitations: groups.length >= 1 ? null : "Ingen brugbar dokumentationskilde registreret", notes: ["Coverage beskriver kildegrundlaget; claim-verifikation afgøres særskilt. Lavrisiko kræver autoritativ primærkilde, dokumenteret original bureaukilde eller to provenance-uafhængige evidenskilder. Højrisiko kræver primærkilde eller to provenance-uafhængige evidenskilder."] },
    claims, numbers: [], quotes: [], right_of_reply: { required: Boolean(dossier.right_of_reply_required), party: null, contacted_at: null, deadline: null, response: null, exception: dossier.right_of_reply_required ? "Flagged by Research; details must be supplied before any required forelæggelse can be considered complete" : null },
    fact_check: { status: "pass", checked_at: accessedAt, notes: ["Uafhængigt Fact checker-call bestået; discovery-only-kilder kan ikke alene verificere claims."] },
    desk_recheck: { status: desk.decision, checked_at: accessedAt, rationale: desk.rationale },
  };
}


const TEXT_NEURON_RATES = {
  "@cf/meta/llama-3.1-8b-instruct-fast": { input: 4119, output: 34868, basis: "8B fast pricing-equivalent estimate" },
  "@cf/meta/llama-3.1-8b-instruct-fp8-fast": { input: 4119, output: 34868, basis: "published Cloudflare rate" },
  "@cf/meta/llama-3.3-70b-instruct-fp8-fast": { input: 26668, output: 204805, basis: "published Cloudflare rate" },
};
function usageRecord(model, raw) {
  if (model === IMAGE_MODEL) {
    return { model, kind: "image", prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, estimated_neurons: 43.2, estimate_only: true, basis: "Flux Schnell minimum estimate: 1 tile + 4 default steps" };
  }
  const u = raw?.usage || raw?.response?.usage || raw?.result?.usage || null;
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

export async function runEditorialCycle(env, scan, options = {}) {
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
    return { status: state, stage: "newsdesk", checked_at: startedAt, generated_at: startedAt, title: assignment.title_hint, reason: check.reason, scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment, selected_signals: check.selected || [] } };
  }

  const research = await runResearch(env, assignment, check.selected);
  let mediaScout = null;
  if (research.decision !== "continue") return { status: research.decision === "watch" ? "watch" : "hold", stage: research.right_of_reply_required ? "ethics" : "research", checked_at: startedAt, generated_at: startedAt, title: assignment.title_hint, reason: research.rationale || "Research hold", scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment, selected_signals: check.selected || [], research: { rationale: research.rationale, candidate_claims: research.candidate_claims || [], contradictions: research.contradictions || [], researched: (research.researched || []).map((x) => ({ source: x.source, headline: x.headline, url: x.final_url || x.url, fetched: x.fetched, fetch_status: x.fetch_status, fetch_error: x.fetch_error, source_kind: x.source_kind, feed_summary_only: Boolean(x.feed_summary_only) })) } } };

  const dossier = await runFactCheck(env, assignment, research);
  if (dossier.decision !== "publish") return { status: "hold", stage: "fact-check", checked_at: startedAt, generated_at: startedAt, title: assignment.title_hint, reason: dossier.rationale || "Fact check hold", scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment, research: { rationale: research.rationale, candidate_claims: research.candidate_claims, contradictions: research.contradictions }, fact_check: { rationale: dossier.rationale, claims: dossier.claims, contradictions: dossier.contradictions }, sources: (dossier.researched || []).map((x) => ({ source: x.source, headline: x.headline, url: x.final_url || x.url, source_kind: x.source_kind })) } };

  mediaScout = await resolveDocumentaryHero(check.selected, assignment, {
    ...research,
    candidate_claims: dossier.claims.filter((c) => c.status === "verified"),
  });
  research.media_strategy = mediaScout ? "have" : "pending_illustration";

  const desk = await deskRecheck(env, assignment, dossier);
  if (!["publish", "update"].includes(desk.decision)) return { status: "hold", stage: "desk-recheck", checked_at: startedAt, generated_at: startedAt, title: assignment.title_hint, reason: desk.rationale || "Newsdesk recheck hold", scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment, fact_check: { claims: dossier.claims, rationale: dossier.rationale }, desk_recheck: desk } };

  let article = await writeArticle(env, assignment, dossier);
  const aiFinalRequired = requiresAiFinalReview(assignment, dossier, article);
  let review = aiFinalRequired ? await finalReview(env, assignment, dossier, article) : deterministicFinalReview(assignment, dossier, article);
  if (review.decision !== "pass") {
    const hardIssues = (review.issues || []).filter((x) => !["language", "seo"].includes(x.gate));
    const revised = await reviseFixableIssues(env, assignment, dossier, article, review);
    if (!hardIssues.length && JSON.stringify(revised) !== JSON.stringify(article)) {
      article = revised;
      // The AI final already found no safety/fact blocker; do not pay for a second
      // final-editor call merely to re-check polish. Deterministic structure checks suffice.
      review = deterministicFinalReview(assignment, dossier, article);
      review.mode = "post-polish-deterministic";
    }
  }
  if (review.decision !== "pass" || [review.language, review.ethics, review.image, review.seo, review.final_editor].some((x) => x !== "pass")) {
    return { status: "hold", stage: "final-editor", checked_at: startedAt, generated_at: startedAt, title: article.title || assignment.title_hint, reason: (review.notes || []).join("; ") || "Final editor hold", scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment, article_title: article.title, fact_check: { claims: dossier.claims, rationale: dossier.rationale }, final_review: review } };
  }

  const date = startedAt.slice(0, 10);
  const slug = `${date}-${slugify(article.title)}`.slice(0, 96).replace(/-+$/g, "");
  const storyId = `${date}-${slugify(assignment.title_hint || article.title)}`.slice(0, 96).replace(/-+$/g, "");
  const documentaryHero = mediaScout;

  const imageKey = `${slug}.jpg`;
  let hero;
  let media;
  if (documentaryHero) {
    hero = { ...documentaryHero, pending_image: false, ai_generated: false };
    media = {
      kind: "documentary",
      key: imageKey,
      content_type: "image/external",
      url: documentaryHero.src,
      source_url: documentaryHero.source_url,
      credit: documentaryHero.credit,
      license: documentaryHero.license,
      image_type: documentaryHero.image_type,
    };
  } else {
    const sketch = await generateTemporarySketch(env, assignment, article);
    hero = pendingSketchHero(imageKey, article, sketch);
    media = {
      kind: "generated",
      key: imageKey,
      content_type: sketch.content_type,
      base64: sketch.base64,
      pending_image: true,
      image_type: "illustration",
    };
  }

  const ledger = makeLedger(storyId, slug, assignment, dossier, desk, startedAt);
  const canonical = {
    pipeline_version: 2, status: "ready", release_requested: true, story_id: storyId, slug,
    category: assignment.category, weight: assignment.weight, title: article.title, standfirst: article.standfirst,
    byline: "Morgentidende Redaktion", published_at: null, updated_at: null, manual_review: false,
    ledger: `sources/${slug}.json`, claim_ids: ledger.claims.map((c) => c.id),
    seo: { title: article.seo_title, description: article.seo_description, canonical: null },
    image: hero,
    body: article.body, source_ids_to_display: ledger.sources.filter((s) => !s.discovery_only).slice(0, 6).map((s) => s.id), related_news_slug: null, related: [], correction_note: null, scheduled_for: null, released_from_schedule_at: null,
  };
  const approvalSnapshot = JSON.parse(JSON.stringify(canonical));
  for (const key of ["status", "published_at", "updated_at", "scheduled_for", "released_from_schedule_at", "release_requested", "publication", "manual_review_completed", "workflow_state"]) delete approvalSnapshot[key];
  const approval = { schema_version: 1, status: "pass", story_id: storyId, article_slug: slug, checked_at: startedAt, gates: { language: "pass", ethics: "pass", image: "pass", seo: "pass", final_editor: "pass" }, final_editor_mode: review.mode || "ai", editorial_snapshot: approvalSnapshot };

  return {
    status: "approved", schema_version: 1, generated_at: startedAt, scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys,
    runtime: "cloudflare-workers-ai", model: STRONG_TEXT_MODEL, models: { fast: FAST_TEXT_MODEL, strong: STRONG_TEXT_MODEL, image: IMAGE_MODEL }, story_id: storyId, slug, article: canonical, ledger, approval,
    media,
    audit: { assignment, research: { rationale: research.rationale, candidate_claims: research.candidate_claims, contradictions: research.contradictions }, fact_check: { rationale: dossier.rationale, claims: dossier.claims, contradictions: dossier.contradictions }, desk_recheck: desk, final_review: review, media_policy: { documentary_first: true, pending_image: Boolean(hero.pending_image), temporary_sketch_allowed_after_scout: true, static_sketch_fallback: true, late_hold_for_no_photo: false }, source_count: ledger.sources.length, independent_source_groups: ledger.coverage_sweep.independent_source_groups },
  };
    })();
  } catch (error) {
    error.ai_usage = { ...summarizeAiUsage(aiUsageEvents), structured_fallback_calls: Number(env.__AI_FALLBACK_COUNT__ || 0) };
    throw error;
  }
  result.ai_usage = { ...summarizeAiUsage(aiUsageEvents), structured_fallback_calls: Number(env.__AI_FALLBACK_COUNT__ || 0) };
  return result;
}

export function editorialDue(lastRunAt) {
  if (!lastRunAt) return true;
  const then = Date.parse(lastRunAt);
  return !Number.isFinite(then) || Date.now() - then >= 13 * 60 * 1000;
}
export function publicMediaUrl(key) { return `${PUBLIC_BASE}/media/${encodeURIComponent(key)}`; }
