const FAST_TEXT_MODEL = "@cf/meta/llama-3.1-8b-instruct-fast";
const STRONG_TEXT_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
const IMAGE_MODEL = "@cf/black-forest-labs/flux-1-schnell";
const PUBLIC_BASE = "https://morgentidende-newsdesk.nicolaipetersen108.workers.dev";

const CATEGORIES = ["Indland", "Udland", "Penge", "Krimi", "Videnskab & teknologi", "Sundhed", "Kultur & medier", "Sport", "Liv"];

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
  if (host === "apnews.com" || host.endsWith(".apnews.com") || source === "ap" || source === "associated press" || source === "ap news") return "ap";
  if (["afp", "agence france-presse"].includes(source)) return "afp";
  if (["ritzau", "ritzau bureau"].includes(source)) return "ritzau";
  return null;
}
function evidenceSourceGroup(item) {
  return sourceGroup(item?.source, item?.final_url || item?.url);
}
function metaContent(html, key) {
  const wanted = String(key || "").toLowerCase();
  const tags = String(html || "").match(/<meta[^>]*>/gi) || [];
  for (const tag of tags) {
    const lower = tag.toLowerCase();
    const names = [`name="${wanted}"`, `name='${wanted}'`, `property="${wanted}"`, `property='${wanted}'`];
    if (!names.some((x) => lower.includes(x))) continue;
    const m = tag.match(/content=["']([^"']+)["']/i);
    if (m?.[1]) return stripHtml(m[1]).trim();
  }
  return null;
}
function canonicalUrl(html, baseUrl) {
  const tags = String(html || "").match(/<link[^>]*>/gi) || [];
  for (const tag of tags) {
    if (!tag.toLowerCase().includes("canonical")) continue;
    const m = tag.match(/href=["']([^"']+)["']/i);
    if (!m?.[1]) continue;
    try { return new URL(m[1], baseUrl).href; } catch (_) {}
  }
  return null;
}
function jsonLdField(html, field) {
  const rawHtml = String(html || "");
  const lower = rawHtml.toLowerCase();
  let cursor = 0;
  for (let count = 0; count < 8; count++) {
    const open = lower.indexOf("<script", cursor); if (open < 0) break;
    const tagEnd = lower.indexOf(">", open); if (tagEnd < 0) break;
    const close = lower.indexOf("</script>", tagEnd + 1); if (close < 0) break;
    const tag = lower.slice(open, tagEnd + 1);
    cursor = close + 9;
    if (!tag.includes("application/ld+json")) continue;
    try {
      const raw = JSON.parse(rawHtml.slice(tagEnd + 1, close));
      const nodes = Array.isArray(raw) ? raw : (raw?.['@graph'] || [raw]);
      for (const node of nodes) {
        const value = node?.[field];
        if (typeof value === "string" && value.trim()) return value.trim();
        if (Array.isArray(value)) {
          for (const x of value) if (typeof x?.name === "string" && x.name.trim()) return x.name.trim();
        }
        if (value && typeof value === "object" && typeof value.name === "string" && value.name.trim()) return value.name.trim();
      }
    } catch (_) {}
  }
  return null;
}
function provenanceMetadata(html, pageUrl) {
  const byline = metaContent(html, "author") || metaContent(html, "article:author") || metaContent(html, "parsely-author") || metaContent(html, "dc.creator") || jsonLdField(html, "author");
  const publisher = metaContent(html, "publisher") || metaContent(html, "article:publisher") || jsonLdField(html, "publisher");
  const canonical_url = canonicalUrl(html, pageUrl);
  return { byline: byline || null, publisher: publisher || null, canonical_url };
}
function normalizedOriginName(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}
function containsOriginToken(value, token) {
  return ` ${normalizedOriginName(value)} `.includes(` ${token} `);
}
function metadataWireOrigin(item) {
  const text = `${item?.provenance_meta?.byline || ""} ${item?.provenance_meta?.publisher || ""}`;
  const n = normalizedOriginName(text);
  if (containsOriginToken(n, "reuters") || n.includes("thomson reuters")) return "reuters";
  if (n.includes("associated press") || n.includes("ap news")) return "ap";
  if (n.includes("agence france presse") || containsOriginToken(n, "afp")) return "afp";
  if (containsOriginToken(n, "ritzau") || n.includes("ritzau bureau")) return "ritzau";
  return null;
}
function pressReleaseService(item) {
  const host = hostOf(item?.final_url || item?.url || "");
  const n = normalizedOriginName(`${item?.provenance_meta?.publisher || ""} ${item?.provenance_meta?.byline || ""}`);
  if (host.endsWith("prnewswire.com") || n.includes("pr newswire")) return "prnewswire";
  if (host.endsWith("businesswire.com") || n.includes("business wire")) return "businesswire";
  if (host.endsWith("globenewswire.com") || n.includes("globe newswire")) return "globenewswire";
  if (host.endsWith("cision.com") || containsOriginToken(n, "cision")) return "cision";
  return null;
}
function headlineFingerprint(item) {
  return [...new Set(words(item?.headline || ""))].slice(0, 10).sort().join("-") || slugify(item?.headline || "release");
}
function structuredUpstreamOrigin(item) {
  const directWire = wireOrigin(item) || metadataWireOrigin(item);
  if (directWire) return `wire:${directWire}`;
  const release = pressReleaseService(item);
  if (release) return `press-release:${release}:${headlineFingerprint(item)}`;
  const canonical = item?.provenance_meta?.canonical_url;
  if (canonical) {
    const pageHost = hostOf(item?.final_url || item?.url || "");
    const canonicalHost = hostOf(canonical);
    if (canonicalHost && pageHost && canonicalHost !== pageHost) return `canonical:${canonical.replace(/[?#].*$/, "")}`;
  }
  return null;
}
function provenanceClusters(items) {
  const clusters = [];
  const origins = items.map(structuredUpstreamOrigin);
  for (let i = 0; i < items.length; i++) {
    let cluster = null;
    for (let j = 0; j < i; j++) {
      if (origins[i] && origins[i] === origins[j]) { cluster = clusters[j]; break; }
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
  const upstream = item?.upstream_origin || structuredUpstreamOrigin(item); if (upstream) return `upstream:${upstream}`;
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
    const provenance_meta = type.includes("html") ? provenanceMetadata(html, response.url) : null;
    return { ...signal, excerpt: text || signal.description || "", fetched: Boolean(text), fetch_status: response.status, final_url: response.url, outbound_links: type.includes("html") ? extractOutboundLinks(html, response.url) : [], provenance_meta };
  } catch (error) {
    return { ...signal, excerpt: signal.description || "", fetched: false, fetch_error: String(error), outbound_links: [] };
  } finally { clearTimeout(timer); }
}

function parseJsonText(value) {
  const text = String(value || "").trim();
  if (!text) return null;
  try { return JSON.parse(text); } catch (_) {}
  const unfenced = text.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "").trim();
  if (unfenced !== text) { try { return JSON.parse(unfenced); } catch (_) {} }
  const starts = [];
  for (let i = 0; i < text.length; i++) if (text[i] === "{" || text[i] === "[") starts.push(i);
  for (const start of starts) {
    const open = text[start], close = open === "{" ? "}" : "]";
    let depth = 0, quoted = false, escaped = false;
    for (let i = start; i < text.length; i++) {
      const ch = text[i];
      if (quoted) {
        if (escaped) escaped = false;
        else if (ch === "\\") escaped = true;
        else if (ch === '"') quoted = false;
        continue;
      }
      if (ch === '"') { quoted = true; continue; }
      if (ch === open) depth += 1;
      else if (ch === close) {
        depth -= 1;
        if (depth === 0) {
          try { return JSON.parse(text.slice(start, i + 1)); } catch (_) { break; }
        }
      }
    }
  }
  return null;
}
function responseObject(raw) {
  if (raw && typeof raw.response === "object" && raw.response !== null) return raw.response;
  if (raw && typeof raw.response === "string") { const parsed = parseJsonText(raw.response); if (parsed) return parsed; }
  if (raw && Array.isArray(raw.choices)) {
    const content = raw.choices[0]?.message?.content;
    if (typeof content === "object" && content) return content;
    if (typeof content === "string") { const parsed = parseJsonText(content); if (parsed) return parsed; }
  }
  throw new Error("Workers AI returned no parseable structured response");
}

function schemaShapeValid(value, schema) {
  if (!schema) return true;
  if (schema.type === "object") {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    for (const key of schema.required || []) if (!(key in value)) return false;
    for (const [key, child] of Object.entries(schema.properties || {})) {
      if (key in value && !schemaShapeValid(value[key], child)) return false;
    }
    return true;
  }
  if (schema.type === "array") {
    if (!Array.isArray(value)) return false;
    if (Number.isInteger(schema.minItems) && value.length < schema.minItems) return false;
    if (Number.isInteger(schema.maxItems) && value.length > schema.maxItems) return false;
    return !schema.items || value.every((item) => schemaShapeValid(item, schema.items));
  }
  if (schema.type === "string") return typeof value === "string" && (!schema.enum || schema.enum.includes(value));
  if (schema.type === "boolean") return typeof value === "boolean";
  if (schema.type === "integer") return Number.isInteger(value);
  if (schema.type === "number") return typeof value === "number" && Number.isFinite(value);
  return true;
}
function structuredResponse(raw, schema) {
  const parsed = responseObject(raw);
  if (!schemaShapeValid(parsed, schema)) throw new Error("Workers AI returned JSON that does not match required schema shape");
  return parsed;
}
async function aiJson(env, system, user, schema, maxTokens = 2800, model = STRONG_TEXT_MODEL, fallbackModel = null, stage = "unknown") {
  const request = {
    messages: [{ role: "system", content: system }, { role: "user", content: user }],
    max_tokens: maxTokens, temperature: 0.15,
    response_format: { type: "json_schema", json_schema: schema },
  };
  let firstError = null;
  try {
    const raw = await env.AI.run(model, request);
    return structuredResponse(raw, schema);
  } catch (error) {
    firstError = error;
    if (!fallbackModel || fallbackModel === model) throw error;
    console.warn("Workers AI structured-call fallback", model, "->", fallbackModel, String(error));
    try {
    env.__AI_FALLBACK_COUNT__ = Number(env.__AI_FALLBACK_COUNT__ || 0) + 1;
    env.__AI_FALLBACK_BY_STAGE__ = env.__AI_FALLBACK_BY_STAGE__ || {};
    env.__AI_FALLBACK_BY_STAGE__[stage] = Number(env.__AI_FALLBACK_BY_STAGE__[stage] || 0) + 1;
  } catch (_) {}
  }
  try {
    const raw = await env.AI.run(fallbackModel, request);
    return structuredResponse(raw, schema);
  } catch (error) {
    console.warn("Workers AI schema fallback still malformed; trying JSON-object repair", String(error));
    try {
    env.__AI_FALLBACK_COUNT__ = Number(env.__AI_FALLBACK_COUNT__ || 0) + 1;
    env.__AI_FALLBACK_BY_STAGE__ = env.__AI_FALLBACK_BY_STAGE__ || {};
    env.__AI_FALLBACK_BY_STAGE__[stage] = Number(env.__AI_FALLBACK_BY_STAGE__[stage] || 0) + 1;
  } catch (_) {}
    const repairRequest = {
      messages: [
        { role: "system", content: `${system}\nReturn ONLY one JSON object that satisfies every required field and type in the supplied JSON Schema. Do not omit required arrays; use empty arrays only when the schema permits them.` },
        { role: "user", content: `${user}\n\nRequired JSON Schema:\n${JSON.stringify(schema)}` },
      ],
      max_tokens: maxTokens, temperature: 0,
      response_format: { type: "json_object" },
    };
    const repairedRaw = await env.AI.run(fallbackModel, repairRequest);
    try { return structuredResponse(repairedRaw, schema); }
    catch (repairError) {
      repairError.cause = error || firstError;
      throw repairError;
    }
  }
}

const assignmentSchema = {
  type: "object", properties: {
    decision: { type: "string", enum: ["research", "watch", "drop"] }, title_hint: { type: "string" },
    category: { type: "string", enum: CATEGORIES }, weight: { type: "string", enum: ["A", "B", "C", "D"] },
    signal_indexes: { type: "array", items: { type: "integer" }, minItems: 0, maxItems: 3 },
    rationale: { type: "string" }, core_question: { type: "string" },
    story_location: { type: "object", properties: {
      country: { type: "string" }, country_code: { type: "string" },
      place_names_local: { type: "array", maxItems: 4, items: { type: "string" } },
      place_names_english: { type: "array", maxItems: 4, items: { type: "string" } },
    }, required: ["country", "country_code", "place_names_local", "place_names_english"] },
  }, required: ["decision", "title_hint", "category", "weight", "signal_indexes", "rationale", "core_question", "story_location"],
};

const researchSchema = {
  type: "object", properties: {
    decision: { type: "string", enum: ["continue", "watch"] }, rationale: { type: "string" }, core_question: { type: "string" },
    right_of_reply_required: { type: "boolean" }, conflict_present: { type: "boolean" }, contradictions: { type: "array", items: { type: "string" } },
    candidate_claims: { type: "array", minItems: 1, maxItems: 8, items: { type: "object", properties: {
      id: { type: "string" }, claim: { type: "string" }, source_indexes: { type: "array", items: { type: "integer" }, minItems: 1 },
      notes: { type: "string" },
    }, required: ["id", "claim", "source_indexes", "notes"] } },
  }, required: ["decision", "rationale", "core_question", "conflict_present", "contradictions", "candidate_claims"],
};

const factCheckSchema = {
  type: "object", properties: {
    contradictions: { type: "array", items: { type: "string" } },
    claims: { type: "array", minItems: 1, maxItems: 12, items: { type: "object", properties: {
      id: { type: "string" }, claim: { type: "string" }, source_indexes: { type: "array", items: { type: "integer" }, minItems: 1 },
      status: { type: "string", enum: ["verified", "uncertain", "rejected"] }, notes: { type: "string" },
    }, required: ["id", "claim", "source_indexes", "status", "notes"] } },
  }, required: ["contradictions", "claims"],
};

const articleSchema = { type: "object", properties: {
  title: { type: "string" }, standfirst: { type: "string" },
  body: { type: "array", minItems: 1, maxItems: 14, items: { type: "object", properties: {
    type: { type: "string", enum: ["p", "h2", "h3"] }, text: { type: "string" },
  }, required: ["type", "text"] } },
}, required: ["title", "standfirst", "body"] };

const finalSchema = { type: "object", properties: {
  category: { type: "string", enum: CATEGORIES },
  blocking_issues: { type: "array", maxItems: 10, items: { type: "object", properties: {
    gate: { type: "string", enum: ["language", "ethics", "final_editor", "evidence"] }, issue: { type: "string" },
  }, required: ["gate", "issue"] } },
}, required: ["category", "blocking_issues"] };

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
const TECH_MAGAZINE_TERMS = ["videnskab", "forskning", "naturvidenskab", "teknologi", "kunstig intelligens", " ai ", "rumfart", "rumteleskop", "astronomi", "fysik", "biologi", "robot", "chip", "halvleder", "militærteknologi", "militaerteknologi", "forsvarsteknologi", "drone", "energi"];
const PEOPLE_MAGAZINE_TERMS = ["psykologi", "psykisk", "mental sundhed", "sundhed", "testosteron", "hormon", "overgangsalder", "menopause", "parforhold", "ægteskab", "aegteskab", "sex", "singleliv", "single", "dating", "opdragelse", "forældre", "foraeldre", "bedsteforældre", "bedsteforaeldre", "familie", "relation", "tilknytning", "evolutionær psykologi", "evolutionaer psykologi"];
function editorialDestination(assignment, scan) {
  const indexes = Array.isArray(assignment?.signal_indexes) ? assignment.signal_indexes : [];
  const signalText = indexes.map((i) => `${scan?.signals?.[i]?.headline || ""} ${scan?.signals?.[i]?.description || ""}`).join(" ");
  const hay = ` ${assignment?.category || ""} ${assignment?.title_hint || ""} ${assignment?.core_question || ""} ${signalText} `.toLocaleLowerCase("da-DK");
  if (assignment?.category === "Videnskab & teknologi" || TECH_MAGAZINE_TERMS.some((x) => hay.includes(x))) return "tech_magazine";
  if (["Sundhed", "Liv"].includes(assignment?.category) || PEOPLE_MAGAZINE_TERMS.some((x) => hay.includes(x))) return "people_magazine";
  return "main";
}
function magazineWritingBrief(destination) {
  if (destination === "tech_magazine") return "Du skriver EKSKLUSIVT til Morgentidendes magasin Viden & teknologi. Artiklen er født til magasinet og må ikke skrives som en kort almindelig nyhedstelegramtekst. Giv verificeret forklaring, kontekst, mekanismer og hvorfor stoffet er interessant eller vigtigt for læseren. Nyheder, forskning, baggrund og evergreen er alle tilladt, men tilføj aldrig fakta ud over de verificerede claims.";
  if (destination === "people_magazine") return "Du skriver EKSKLUSIVT til Morgentidendes magasin Mennesker & liv. Artiklen er født til magasinet og må ikke skrives som en kort almindelig nyhedstelegramtekst. Gør psykologi, sundhed, hormoner, relationer, sex, dating eller familieliv forståeligt, nuanceret og relevant for hverdagen. Brug verificeret forklaring og kontekst, men tilføj aldrig fakta ud over de verificerede claims.";
  return "Du skriver til Morgentidendes almindelige nyhedsstrøm.";
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
  if (!signals.length) return { decision: "drop", title_hint: "", category: "Indland", weight: "D", signal_indexes: [], rationale: "Ingen ubehandlede kandidater med tilstrækkelig aktualitet/grundscore", core_question: "" };
  const system = `Du er Morgentidendes første Nyhedsdesk. Vælg ét konkret research-frø. RESEARCH er standard ved reel nyhedsværdi, originalitet, offentlig betydning eller tydelig redaktionel relevans; tynd dokumentation er Researchs problem, ikke en afvisningsgrund. WATCH kun hvis nyhedskrogen/aktualiteten endnu er uklar. DROP kun ved klar dublet, gammel/triviel sag, rent holdningsstof uden nyhedskrog eller åbenlys spam. discovery_only må udløse Research, men er aldrig dokumentation. Sæt kategori og A-D-vægt. Angiv kun det primære land og op til fire relevante stednavne på lokalt/engelsk navn, når de er tydelige; ellers brug unknown/tomme arrays. Media laver selv billedsøgninger. Svar ultrakort.`;
  return aiJson(env, system, JSON.stringify({ generated_at: scan.generated_at, signals }), assignmentSchema, 260, FAST_TEXT_MODEL, STRONG_TEXT_MODEL, "newsdesk");
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
  "france24.com", "dw.com", "euronews.com", "aljazeera.com", "sky.com", "skynews.com",
  "cnn.com", "nbcnews.com", "cbsnews.com", "abcnews.go.com", "foxnews.com", "spiegel.de", "lemonde.fr",
  "tagesschau.de", "rbb24.de", "itv.com",
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
  const explicit = String(item?.source_kind || item?.source_class || "").toLowerCase().trim();
  if (["paper", "research_paper", "researcher", "scientist", "expert", "company_statement", "organization_statement", "person_statement", "first_party_statement", "interview", "official_statement"].includes(explicit)) return explicit;
  if (authoritativePrimary(item)) return "primary";
  const kind = trustedExpansionKind(item?.final_url || item?.url || "");
  if (kind === "primary") return "primary";
  if (kind === "public_media" || strongEditorialSource(item)) return "strong_editorial";
  return item?.source_kind || "news";
}
function authoritativeClaimSource(item) {
  if (!isEvidenceSource(item)) return false;
  if (authoritativePrimary(item) || authoritativeEditorial(item) || strongEditorialSource(item)) return true;
  const kind = normalizedSourceKind(item);
  return ["paper", "research_paper", "researcher", "scientist", "expert", "company_statement", "organization_statement", "person_statement", "first_party_statement", "interview", "official_statement"].includes(kind);
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
  // House rule: one relevant authoritative source is sufficient for a claim.
  // Named accused claims are the narrow exception: they require a primary source or an original wire.
  if (namedAccusedCrimeClaim(assignment, claim)) {
    return evidence.some((item) => authoritativePrimary(item) || authoritativeEditorial(item));
  }
  // Risk/fairness may still trigger Ethics or final review, but does not impose a hidden two-source quota.
  return evidence.some(authoritativeClaimSource);
}
async function runResearch(env, assignment, selected) {
  let researched = await Promise.all(selected.map(fetchExcerpt));
  researched = researched.map((item) => ({ ...item, source_kind: normalizedSourceKind(item) }));

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

  let evidenceUsable = usable.filter(isEvidenceSource);
  if (!evidenceUsable.some(authoritativeClaimSource)) {
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

  if (!evidenceUsable.length) {
    return { decision: "watch", rationale: "Ingen brugbar dokumentationskilde kunne hentes endnu", researched, candidate_claims: [], contradictions: [], right_of_reply_required: false, conflict_present: false };
  }

  const unique = [];
  const seenUrls = new Set();
  const prioritized = [...evidenceUsable].sort((a, b) =>
    Number(authoritativePrimary(b)) - Number(authoritativePrimary(a)) ||
    Number(strongEditorialSource(b)) - Number(strongEditorialSource(a))
  );
  const hasAuthoritative = prioritized.some(authoritativeClaimSource);
const researchSourceLimit = hasAuthoritative ? 3 : 4;
for (const item of prioritized) {
  const url = item.final_url || item.url;
  if (!url || seenUrls.has(url)) continue;
  seenUrls.add(url);
  unique.push(item);
  if (unique.length >= researchSourceLimit) break;
}

  const researchClusters = provenanceClusters(unique);
  unique.forEach((item, i) => {
    item.provenance_cluster = researchClusters[i];
    item.upstream_origin = structuredUpstreamOrigin(item);
  });
  const sources = unique.map((item, i) => ({
    source_index: i,
    name: item.source,
    headline: item.headline,
    url: item.final_url || item.url,
    excerpt: item.excerpt.slice(0, authoritativeClaimSource(item) ? 1400 : 1000),
    discovery_only: false,
    source_kind: normalizedSourceKind(item),
    source_strength: authoritativePrimary(item) ? "primary" : authoritativeEditorial(item) ? "wire" : strongEditorialSource(item) ? "strong_editorial" : "standard",
    upstream_origin: item.upstream_origin || null,
    byline: item.provenance_meta?.byline || null,
    publisher: item.provenance_meta?.publisher || null,
    canonical_url: item.provenance_meta?.canonical_url || null,
    feed_summary_only: Boolean(item.feed_summary_only),
  }));
  const system = `Du er Research på Morgentidende. Lav et kompakt evidens-kort til Fact checker; vurder ikke nyhedsværdi igen og fæld ikke den endelige sandhedsdom. Kortlæg 1-6 bærende kandidat-claims med præcise source_indexes. Notér kun reelle modsigelser, væsentlige forbehold og nødvendig kontekst. En primærkilde er værdifuld, men du skal ikke kræve et bestemt antal medier. Hvis mindst ét brugbart claim kan kildebelægges, vælg continue; watch kun hvis materialet reelt ikke giver noget kontrollerbart. Sæt kun right_of_reply_required=true ved en konkret alvorlig belastende påstand, hvor fairness faktisk er relevant; ellers kan feltet udelades. Flaget er aldrig en automatisk ventetid eller stopregel. Sæt conflict_present=true kun når historien faktisk rummer en relevant politisk, juridisk, faglig eller parts-konflikt; almindelige hændelsesfakta/statistik kræver ikke kunstig pluralisme. Skriv alle kandidat-claims på idiomatisk dansk, også når originalkilden er norsk, svensk eller et andet sprog. Norske bokmåls-/nynorskformer og svenske ord eller bøjningsformer må ikke føres videre som dansk. Ved oversættelse eller parafrase skal originalens samlede betydning bevares præcist. Opfind intet.`;
  const research = await aiJson(env, system, JSON.stringify({ assignment, sources }), researchSchema, 650, FAST_TEXT_MODEL, STRONG_TEXT_MODEL, "research");
  research.researched = unique;
  research.source_payload = sources;
  return research;
}

function focusedExcerpt(text, claims, maxChars = 500) {
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
  const system = `Du er Morgentidendes uafhængige Fact checker. Kontrollér hvert kandidat-claim mod de vedlagte kildetekster og forsøg aktivt at falsificere det. Brug kun source_indexes, der faktisk dokumenterer claimet. Ét claim kan verificeres af én relevant autoritativ kilde: stort etableret medie/bureau, myndighed/officiel kilde, virksomhed/person om egne forhold, relevant ekspert eller original forskning. Kræv ikke mekanisk kilde nr. 2. Discovery-only-kilder må aldrig verificere claims. Sammenlign materielle tal mod alle relevante kilder; mismatch => uncertain eller forsigtig attribution. Oversættelse/parafrase skal bevare den materielle betydning. Rejected hvis evidensen modsiger claimet, ellers uncertain. Ét verificeret bærende claim er nok; udelad usikre detaljer. Opfind intet.`;
  const fact = await aiJson(env, system, JSON.stringify({
    assignment,
    research: { core_question: research.core_question, rationale: research.rationale, contradictions: research.contradictions, candidate_claims: research.candidate_claims },
    sources: (research.source_payload || []).map((source, i) => ({
      ...source,
      excerpt: focusedExcerpt(research.researched?.[i]?.excerpt || source.excerpt, research.candidate_claims, 500),
    })),
  }), factCheckSchema, 850, FAST_TEXT_MODEL, STRONG_TEXT_MODEL, "fact-check");
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
    if (claim.status === "verified" && (!indexes.length || !evidenceRulePass(assignment, research, claim, evidence))) {
      claim.status = "uncertain";
      claim.notes = `${claim.notes || ""} Nedgraderet af deterministisk gate: claimet mangler en relevant autoritativ kilde.`.trim();
    }
  }
  const verified = fact.claims.filter((c) => c.status === "verified");
  fact.decision = verified.length >= 1 ? "publish" : "hold";
  fact.rationale = verified.length >= 1
    ? `Deterministisk Fact checker: ${verified.length} bærende claim(s) verificeret; usikre eller afviste detaljer udelades fra artiklen.`
    : "Deterministisk Fact checker: ingen bærende claims opfylder dokumentationskravet.";
  return fact;
}

async function writeArticle(env, assignment, dossier) {
  if ((dossier.researched || []).some(isDiscoveryOnly)) throw new Error("Discovery-only source crossed the Journalist boundary");
  const sources = dossier.researched.filter(isEvidenceSource).map((s, i) => ({ source_index: i, name: s.source, headline: s.headline, url: s.final_url || s.url }));
  const destinationBrief = magazineWritingBrief(assignment?.editorial_destination || "main");
  const system = `Du er journalist på Morgentidende. ${destinationBrief} HÅRD REGEL: Al redaktionel tekst skal være på dansk, inklusive rubrik, manchet, brødtekst, mellemoverskrifter og citater. Citater på andre sprog skal oversættes loyalt til naturligt dansk med samme betydning og forbehold. Kun egennavne, officielle navne og produkt-/værknavne må stå på originalsproget. Brug KUN verified claims. Skriv præcist, levende og idiomatisk dansk; oversæt norsk/svensk/engelsk fuldt, bortset fra egennavne og officielle navne. Oversæt også almindelige jobtitler og faste vendinger. Norske former som styreleder, nestleder, går av, gått av, etter, nei, overtar, ledervervet, kaptein, vanskelig og sjokk- må aldrig stå som dansk; brug naturlige danske ord og bøjninger. Rubrik, manchet og brødtekst må aldrig være stærkere end dokumentationen. Gør attribution konkret (fx “ifølge BBC”), men lav ikke afsnit om hvilke medier der dækkede sagen. Opfind aldrig citater eller fakta. Brug kun reel pluralisme når conflict_present=true og kun fra verificeret materiale. Forklar nødvendige fagord, roller og mindre kendte steder kort. En one-claim-nyhed må være én kort tekstblok: gentag aldrig samme claim og tilføj ikke generelle perspektiver, konsekvenser eller fremtidsforudsigelser uden verified claim. Standfirst er 1-2 korte sætninger, højst 35 ord, aldrig kun et kildenavn. Media ejer heroen.`;
  return aiJson(env, system, JSON.stringify({ assignment, conflict_present: Boolean(dossier.conflict_present), verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources }), articleSchema, assignment.weight === "A" || assignment.weight === "B" ? 2200 : 1400, FAST_TEXT_MODEL, assignment.weight === "A" || assignment.weight === "B" ? STRONG_TEXT_MODEL : null, "journalist");
}

async function finalReview(env, assignment, dossier, article) {
  const system = `Du er Morgentidendes uafhængige slutredaktør. HÅRD SPROGREGEL: al redaktionel tekst og alle citater skal være på dansk; citater fra andre sprog skal være loyalt oversat. Kun egennavne, officielle navne og produkt-/værknavne må stå på originalsproget. Lav ét kort slutcheck af den færdige artikel mod de ALLEREDE verificerede claims; du må ikke genresearche og må ikke mekanisk kræve flere kilder. Vælg samtidig den korrekte kategori blandt de tilladte kategorier. Forkert kategori er IKKE en blocker: returnér bare korrekt category. Returnér kun reelle blockers: (final_editor) artikelteksten går ud over verified claims, har vildledende/forkert attribution, rubrik/manchet er stærkere end dokumentationen eller nyhed og kommentar blandes; (ethics) konkret uløst fairness-/presseetisk risiko som kan repareres med det eksisterende verificerede materiale; (language) tydeligt fremmedsprogligt læk, brudt dansk eller uklar formulering som faktisk kræver reparation. Fang især norsk/svensk læk i ellers dansk tekst, fx styreleder, nestleder, går av, gått av, etter, nei, overtar, ledervervet, kaptein, vanskelig og sjokk-; (evidence) kun når selve det verificerede evidensgrundlag er materielt selvmodsigende eller utilstrækkeligt til at skrive historien sikkert, så Research/Fact checker reelt må køres igen. Brug IKKE evidence for tekst, der blot skal fjernes eller omskrives til de eksisterende claims. Små stilpræferencer, SEO, metadata og media er aldrig blockers her. Media ejer billedsandhed og brugsret. Hvis artiklen er klar, returnér tom blocking_issues.`;
  const reviewModel = ["A", "B"].includes(assignment?.weight) ? STRONG_TEXT_MODEL : FAST_TEXT_MODEL;
  const reviewFallback = reviewModel === FAST_TEXT_MODEL ? STRONG_TEXT_MODEL : null;
  const raw = await aiJson(env, system, JSON.stringify({ categories: CATEGORIES, assignment, claims: dossier.claims.filter((c) => c.status === "verified"), contradictions: dossier.contradictions, article }), finalSchema, 360, reviewModel, reviewFallback, "final-editor");
  if (CATEGORIES.includes(raw.category)) assignment.category = raw.category;
  const issues = Array.isArray(raw.blocking_issues) ? raw.blocking_issues.filter((x) => x?.gate && x?.issue) : [];
  const failed = new Set(issues.map((x) => x.gate));
  return { decision: issues.length ? "hold" : "pass", language: failed.has("language") ? "hold" : "pass", ethics: failed.has("ethics") ? "hold" : "pass", final_editor: failed.has("final_editor") ? "hold" : "pass", issues, notes: issues.map((x) => `${x.gate}: ${x.issue}`) };
}
function normalizedArticleFingerprint(article) {
  const normalized = {
    title: String(article?.title || "").replace(/\s+/g, " ").trim(),
    standfirst: String(article?.standfirst || "").replace(/\s+/g, " ").trim(),
    body: (article?.body || []).map((b) => ({ type: b?.type || "", text: String(b?.text || "").replace(/\s+/g, " ").trim() })),
  };
  return JSON.stringify(normalized);
}
async function reviseArticleIssues(env, assignment, dossier, article, review) {
  const issues = (review.issues || []).filter((x) => ["language", "ethics", "final_editor"].includes(x.gate));
  if (!issues.length) return article;
  const languageOnly = issues.every((x) => x.gate === "language");
  const system = languageOnly
    ? `Du reparerer KUN sprog og klarhed i en allerede fact-checket artikel. Returnér hele artiklen i samme schema. Ændr ikke fakta, attribution, vinkel eller betydning. Ret kun de konkrete sprogproblemer fra Slutredaktøren. Fjern alle norske/svenske/engelske almindelige ord og bøjninger. Oversæt også fremmedsprogede citater loyalt til dansk. Kun egennavne, officielle navne og produkt-/værknavne bevares på originalsproget.`
    : `Du reparerer en allerede fact-checket artikel. Ret KUN de konkrete problemer fra Slutredaktøren og returnér hele artiklen i samme schema. Brug kun de verificerede claims. Ved final_editor: fjern eller omskriv tekst, der går ud over de verificerede claims; opfind aldrig nye fakta. Ved ethics: tilføj kun fairness/attribution, hvis den nødvendige information allerede findes i de verificerede claims; ellers kan problemet ikke repareres automatisk. SEO må aldrig være blocker. Bevar vinkel og betydning så langt det er forsvarligt.`;
  const payload = languageOnly ? { article, issues } : { verified_claims: dossier.claims.filter((c) => c.status === "verified"), article, issues };
  return aiJson(env, system, JSON.stringify(payload), articleSchema, assignment.weight === "A" || assignment.weight === "B" ? 2200 : 1400, FAST_TEXT_MODEL, null, "repair");
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

async function generateTemporarySketch(env, assignment, article) {
  // Hero policy v2: a static placeholder must never reach the public surface.
  // The pre-build media scout gets first chance to replace this pending illustration
  // with a lawful free documentary/context/map/satellite visual. If no such visual
  // exists, Flux pencil hatching is the final public fallback for every story weight.
  const raw = await env.AI.run(IMAGE_MODEL, { prompt: temporarySketchPrompt(assignment, article) });
  if (!raw?.image || typeof raw.image !== "string") {
    throw new Error("Hero unavailable: no lawful free visual found yet and Flux returned no image");
  }
  return { base64: raw.image, content_type: "image/jpeg", ai_generated: true, generator: "workers_ai_flux" };
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

function mediaWords(value) {
  return (String(value || "").normalize("NFKC").match(/[\p{L}\p{N}]{2,}/gu) || [])
    .map((x) => x.toLocaleLowerCase()).filter(Boolean);
}
function commonsSearchQueries(assignment, article, research = null) {
  const loc = assignment?.story_location || {};
  const supplied = [
    ...(Array.isArray(loc.place_names_local) ? loc.place_names_local : []),
    ...(Array.isArray(loc.place_names_english) ? loc.place_names_english : []),
  ].map((x) => String(x || "").trim()).filter((x) => x.length >= 2);
  const stop = new Set(["mener","siger","efter","over","under","vil","kan","skal","med","fra","til","for","the","and","with","from","says","after"]);
  const clean = (value, limit = 7) => mediaWords(value).filter((x) => !stop.has(x)).slice(0, limit).join(" ");
  const claims = (research?.candidate_claims || []).map((x) => x.claim).join(" ");
  const fallback = [
    clean(`${assignment?.title_hint || ""} ${article?.title || ""}`, 7),
    clean(assignment?.core_question || "", 5),
    clean(claims, 5),
    clean(article?.standfirst || "", 5),
  ].filter((x) => x && x.length >= 2);
  return [...new Set([...supplied, ...fallback])].slice(0, 8);
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
  const allowedMime = new Set(["image/jpeg", "image/png", "image/webp", "image/svg+xml", "image/tiff", "image/gif", "image/avif"]);
  const loc = assignment?.story_location || {};
  const locationTerms = new Set([
    ...(Array.isArray(loc.place_names_local) ? loc.place_names_local : []),
    ...(Array.isArray(loc.place_names_english) ? loc.place_names_english : []),
    loc.country || "",
  ].flatMap(mediaWords));
  const year = String(new Date().getUTCFullYear());
  const winners = new Map();

  for (let qIndex = 0; qIndex < queries.length; qIndex++) {
    const q = queries[qIndex];
    const params = new URLSearchParams({
      action: "query", format: "json", origin: "*", generator: "search",
      gsrnamespace: "6", gsrsearch: q, gsrlimit: "10",
      prop: "imageinfo", iiprop: "url|mime|size|extmetadata", iiurlwidth: "1600",
    });
    try {
      const res = await fetch(`https://commons.wikimedia.org/w/api.php?${params}`, {
        headers: { "user-agent": "MorgentidendeMediaDesk/2.0" },
        cf: { cacheTtl: 300, cacheEverything: true },
      });
      if (!res.ok) continue;
      const payload = await res.json();
      const pages = Object.values(payload?.query?.pages || {});
      const queryTerms = new Set(mediaWords(q));
      for (const page of pages) {
        const info = page?.imageinfo?.[0];
        const meta = info?.extmetadata || {};
        const license = meta.LicenseShortName?.value || meta.UsageTerms?.value || "";
        const mime = String(info?.mime || "").toLowerCase();
        if (!info?.url || !allowedMime.has(mime) || !commonsLicenseAllowed(license)) continue;
        if ((info.width || 0) < 800 || (info.height || 0) < 450) continue;
        // Formats such as SVG/TIFF/GIF should use Wikimedia's rasterized thumbnail.
        const requiresThumb = ["image/svg+xml", "image/tiff", "image/gif"].includes(mime);
        const src = info.thumburl || (!requiresThumb ? info.url : null);
        if (!src) continue;

        const desc = stripCommonsHtml(meta.ImageDescription?.value || "");
        const title = String(page?.title || "").replace(/^File:/i, "");
        const candidateWords = new Set(mediaWords(`${title} ${desc}`));
        let overlap = 0;
        for (const term of queryTerms) if (candidateWords.has(term)) overlap += 1;
        const minOverlap = queryTerms.size <= 1 ? 1 : 2;
        if (queryTerms.size && overlap < minOverlap) continue;
        const subjectTerms = [...queryTerms].filter((term) => !locationTerms.has(term));
        if (subjectTerms.length && !subjectTerms.some((term) => candidateWords.has(term))) continue;

        const visualText = `${title} ${desc}`.toLocaleLowerCase();
        const isMap = /(^|\s)(map|kort|karte)(\s|$)/iu.test(visualText);
        const isSatellite = ["satellite", "landsat", "sentinel", "earth observ", "satellit"].some((x) => visualText.includes(x));
        const graphic = isMap || isSatellite || mime === "image/svg+xml";
        const contextType = isMap ? "map" : isSatellite ? "satellite" : "archive";
        const caption = isMap ? "Kort over sagen eller det berørte område." : isSatellite ? "Satellitbillede relateret til hændelsen eller det berørte område." : "Arkivfoto – billedet viser ikke nødvendigvis selve hændelsen.";
        let placeOverlap = 0;
        for (const term of locationTerms) if (candidateWords.has(term)) placeOverlap += 1;
        const eventBonus = visualText.includes(year) ? 5 : 0;
        const queryPriorityBonus = Math.max(0, 1 - qIndex * 0.1);
        const score = overlap * 3 + Math.min(4, placeOverlap * 2) + eventBonus + queryPriorityBonus;
        const sourceUrl = info.descriptionurl || `https://commons.wikimedia.org/wiki/${encodeURIComponent(page.title)}`;
        const credit = stripCommonsHtml(meta.Artist?.value || meta.Credit?.value || "Wikimedia Commons");
        const candidate = {
          score,
          hero: {
            src, alt: desc || title, credit: credit || "Wikimedia Commons", license: stripCommonsHtml(license),
            source_url: sourceUrl, image_type: graphic ? "graphic" : "photo", context_type: contextType, caption,
            pending_image: false, ai_generated: false, placement: "lead",
          },
        };
        const old = winners.get(sourceUrl);
        if (!old || candidate.score > old.score) winners.set(sourceUrl, candidate);
      }
    } catch (_) {}
  }
  const ranked = [...winners.values()].sort((a, b) => b.score - a.score);
  return ranked[0]?.hero || null;
}

function makeLedger(storyId, slug, assignment, dossier, accessedAt) {
  if ((dossier.researched || []).some(isDiscoveryOnly)) throw new Error("Discovery-only source crossed the publication ledger boundary");
  const evidenceRows = dossier.researched.filter(isEvidenceSource);
  const clusters = provenanceClusters(evidenceRows);
  const sources = evidenceRows.map((s, i) => {
    const url = s.final_url || s.url;
    const primary = s.source_kind === "primary" && !s.discovery_only;
    const publisher = evidenceSourceGroup(s);
    const wire = wireOrigin(s) || metadataWireOrigin(s);
    const upstream = s.upstream_origin || structuredUpstreamOrigin(s);
    return { id: `S${i + 1}`, name: s.source, url, published_at: s.published_at || null, accessed_at: accessedAt, type: primary ? "primary" : "news", source_group: publisher, publisher_root: publisher.replace(/^host-/, ""), wire_origin: wire, upstream_origin: upstream, provenance_type: primary ? "primary_record" : wire ? "wire_original" : upstream?.startsWith("press-release:") ? "press_release" : upstream?.startsWith("canonical:") ? "syndicated" : "reporting", provenance_cluster: clusters[i], provenance_basis: upstream ? "structured_metadata" : "publisher_or_similarity", byline: s.provenance_meta?.byline || null, publisher_name: s.provenance_meta?.publisher || null, canonical_url: s.provenance_meta?.canonical_url || null, primary_record: primary ? url : null, authoritative_for: primary ? (s.headline || "Primary record") : (s.headline || "Independent coverage"), authority_class: normalizedSourceKind(s), discovery_only: Boolean(s.discovery_only) };
  });
  const verificationSources = sources.filter((s) => !s.discovery_only);
  const groups = [...new Set(verificationSources.map((s) => s.source_group))];
  const claims = dossier.claims.filter((c) => c.status === "verified").map((c, i) => {
    const ids = [...new Set(c.source_indexes)].map((n) => sources[n]?.id).filter(Boolean);
    return { id: `F${String(i + 1).padStart(2, "0")}`, claim: c.claim, status: "verified", source_ids: ids, independent_groups: ids.map((id) => sources.find((s) => s.id === id && !s.discovery_only)?.source_group).filter(Boolean), checked_at: accessedAt, notes: c.notes || "" };
  });
  return {
    schema_version: 3, story_id: storyId, article_slug: slug,
    assignment: { category: assignment.category, weight: assignment.weight, editorial_destination: assignment.editorial_destination || "main", story_location: assignment.story_location || null, core_question: dossier.core_question || assignment.core_question },
    sources,
    coverage_sweep: { status: groups.length >= 1 ? "pass" : "limited", editorial_source_ids: verificationSources.slice(0, 6).map((s) => s.id), independent_source_groups: groups.slice(0, 6), limitations: groups.length >= 1 ? null : "Ingen brugbar dokumentationskilde registreret", notes: ["Coverage beskriver kildegrundlaget; claim-verifikation afgøres særskilt. Ét claim kan verificeres af én relevant autoritativ kilde: stort redaktionelt medie, myndighed/officiel kilde, virksomhed/person om egne forhold, relevant forsker/fagekspert eller forskningspaper/original forskning. Flere kilder er til pluralisme, mod-evidens og ekstra sikkerhed — ikke en mekanisk kvote."] },
    claims, numbers: [], quotes: [], right_of_reply: { required: Boolean(dossier.right_of_reply_required), party: null, contacted_at: null, deadline: null, response: null, exception: dossier.right_of_reply_required ? "Flagged by Research; details must be supplied before any required forelæggelse can be considered complete" : null },
    fact_check: { status: "pass", checked_at: accessedAt, notes: ["Uafhængigt Fact checker-call bestået; hvert publiceret claim har mindst én relevant autoritativ kilde, og discovery-only-kilder kan ikke verificere claims."] },
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
  assignment.editorial_destination = editorialDestination(assignment, scan);
  const check = validateAssignment(assignment, scan);
  const handledSignalKeys = check.handled_signal_keys || [];
  if (!check.ok) {
    const state = check.state === "watch" ? "watch" : check.state === "drop" ? "drop" : "hold";
    return { status: state, stage: "newsdesk", checked_at: startedAt, generated_at: startedAt, title: assignment.title_hint, reason: check.reason, scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment, selected_signals: check.selected || [] } };
  }

  const research = await runResearch(env, assignment, check.selected);
  let currentResearch = research;
  if (currentResearch.decision !== "continue") return { status: currentResearch.decision === "watch" ? "watch" : "hold", stage: currentResearch.right_of_reply_required ? "ethics" : "research", checked_at: startedAt, generated_at: startedAt, title: assignment.title_hint, reason: currentResearch.rationale || "Research hold", scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment, selected_signals: check.selected || [], research: { rationale: currentResearch.rationale, candidate_claims: currentResearch.candidate_claims || [], contradictions: currentResearch.contradictions || [], researched: (currentResearch.researched || []).map((x) => ({ source: x.source, headline: x.headline, url: x.final_url || x.url, fetched: x.fetched, fetch_status: x.fetch_status, fetch_error: x.fetch_error, source_kind: x.source_kind, feed_summary_only: Boolean(x.feed_summary_only) })) } } };

  let dossier = await runFactCheck(env, assignment, currentResearch);
  if (dossier.decision !== "publish") return { status: "hold", stage: "fact-check", checked_at: startedAt, generated_at: startedAt, title: assignment.title_hint, reason: dossier.rationale || "Fact check hold", scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment, research: { rationale: currentResearch.rationale, candidate_claims: currentResearch.candidate_claims, contradictions: currentResearch.contradictions }, fact_check: { rationale: dossier.rationale, claims: dossier.claims, contradictions: dossier.contradictions }, sources: (dossier.researched || []).map((x) => ({ source: x.source, headline: x.headline, url: x.final_url || x.url, source_kind: x.source_kind })) } };

  let mediaScout = await resolveDocumentaryHero(check.selected, assignment, {
    ...currentResearch,
    candidate_claims: dossier.claims.filter((c) => c.status === "verified"),
  });
  currentResearch.media_strategy = mediaScout ? "have" : "pending_illustration";

  let article = await writeArticle(env, assignment, dossier);

  const MAX_ARTICLE_ATTEMPTS = 3;
  let articleAttempts = 1;
  let review = await finalReview(env, assignment, dossier, article);
  const routing = [];
  while (review.decision !== "pass" && articleAttempts < MAX_ARTICLE_ATTEMPTS) {
    const evidenceIssue = (review.issues || []).some((x) => x.gate === "evidence");
    if (evidenceIssue) {
      const previousEvidence = JSON.stringify(dossier.claims || []);
      const nextResearch = await runResearch(env, assignment, check.selected);
      if (nextResearch.decision !== "continue") break;
      const nextDossier = await runFactCheck(env, assignment, nextResearch);
      if (nextDossier.decision !== "publish") break;
      const nextEvidence = JSON.stringify(nextDossier.claims || []);
      if (nextEvidence === previousEvidence) break;
      currentResearch = nextResearch;
      dossier = nextDossier;
      mediaScout = await resolveDocumentaryHero(check.selected, assignment, {
        ...currentResearch,
        candidate_claims: dossier.claims.filter((c) => c.status === "verified"),
      });
      currentResearch.media_strategy = mediaScout ? "have" : "pending_illustration";
      article = await writeArticle(env, assignment, dossier);
      articleAttempts += 1;
      routing.push("evidence→research→fact-check→journalist→final-editor");
      review = await finalReview(env, assignment, dossier, article);
      continue;
    }

    const revised = await reviseArticleIssues(env, assignment, dossier, article, review);
    if (normalizedArticleFingerprint(revised) === normalizedArticleFingerprint(article)) { routing.push("local-repair→no-progress"); break; }
    article = revised;
    articleAttempts += 1;
    routing.push("local-repair→final-editor");
    review = await finalReview(env, assignment, dossier, article);
  }
  if (review.decision !== "pass") {
    return { status: "drop", stage: "final-editor", checked_at: startedAt, generated_at: startedAt, title: article.title || assignment.title_hint, reason: `Droppet efter ${articleAttempts} artikel-forsøg: ${(review.notes || []).join("; ") || "Slutredaktør godkendte ikke artiklen"}`, scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment, article_title: article.title, article_attempts: articleAttempts, retry_routing: routing, fact_check: { claims: dossier.claims, rationale: dossier.rationale }, final_review: review } };
  }

  // Media is finalized only after the text has passed. Avoid paying for Flux on drafts that will be rewritten or dropped.
  const date = startedAt.slice(0, 10);
  const slug = `${date}-${slugify(article.title)}`.slice(0, 96).replace(/-+$/g, "");
  const storyId = `${date}-${slugify(assignment.title_hint || article.title)}`.slice(0, 96).replace(/-+$/g, "");
  const imageKey = `${slug}.jpg`;
  let hero;
  let media;
  if (mediaScout) {
    hero = { ...mediaScout, pending_image: false, ai_generated: false };
    media = {
      kind: "documentary",
      key: imageKey,
      content_type: "image/external",
      url: mediaScout.src,
      source_url: mediaScout.source_url,
      credit: mediaScout.credit,
      license: mediaScout.license,
      image_type: mediaScout.image_type,
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

  const ledger = makeLedger(storyId, slug, assignment, dossier, startedAt);
  const canonical = {
    pipeline_version: 2, status: "ready", release_requested: true, story_id: storyId, slug,
    category: assignment.category, weight: assignment.weight, editorial_destination: assignment.editorial_destination || "main", story_location: assignment.story_location || null, title: article.title, standfirst: article.standfirst,
    byline: "Morgentidende Redaktion", published_at: null, updated_at: null,
    ledger: `sources/${slug}.json`, claim_ids: ledger.claims.map((c) => c.id),
    seo: { title: article.title, description: article.standfirst, canonical: null },
    image: hero,
    body: article.body, source_ids_to_display: ledger.sources.filter((s) => !s.discovery_only).slice(0, 6).map((s) => s.id), related_news_slug: null, related: [], correction_note: null, scheduled_for: null, released_from_schedule_at: null,
  };
  const approvalSnapshot = JSON.parse(JSON.stringify(canonical));
  for (const key of ["status", "published_at", "updated_at", "scheduled_for", "released_from_schedule_at", "release_requested", "publication", "workflow_state"]) delete approvalSnapshot[key];
  const approval = { schema_version: 1, status: "pass", story_id: storyId, article_slug: slug, checked_at: startedAt, final_editor_mode: review.mode || "ai", editorial_snapshot: approvalSnapshot };

  return {
    status: "approved", schema_version: 1, generated_at: startedAt, scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys,
    runtime: "cloudflare-workers-ai", model: STRONG_TEXT_MODEL, models: { fast: FAST_TEXT_MODEL, strong: STRONG_TEXT_MODEL, image: IMAGE_MODEL }, story_id: storyId, slug, article: canonical, ledger, approval,
    media,
    audit: { assignment, research: { rationale: research.rationale, candidate_claims: research.candidate_claims, contradictions: research.contradictions }, fact_check: { rationale: dossier.rationale, claims: dossier.claims, contradictions: dossier.contradictions }, article_attempts: articleAttempts, retry_routing: routing, language_mode: articleAttempts === 1 ? "write-once-no-repair" : "conditional-repair", final_review: review, media_policy: { documentary_first: true, multilingual_location_search: true, pending_image: Boolean(hero.pending_image), temporary_sketch_allowed_after_scout: true, static_sketch_fallback: false, late_hold_for_no_photo: false }, source_count: ledger.sources.length, independent_source_groups: ledger.coverage_sweep.independent_source_groups },
  };
    })();
  } catch (error) {
    error.ai_usage = { ...summarizeAiUsage(aiUsageEvents), structured_fallback_calls: Number(env.__AI_FALLBACK_COUNT__ || 0), structured_fallback_by_stage: env.__AI_FALLBACK_BY_STAGE__ || {} };
    throw error;
  }
  result.ai_usage = { ...summarizeAiUsage(aiUsageEvents), structured_fallback_calls: Number(env.__AI_FALLBACK_COUNT__ || 0), structured_fallback_by_stage: env.__AI_FALLBACK_BY_STAGE__ || {} };
  return result;
}

export function editorialDue(lastRunAt) {
  if (!lastRunAt) return true;
  const then = Date.parse(lastRunAt);
  return !Number.isFinite(then) || Date.now() - then >= 13 * 60 * 1000;
}
export function publicMediaUrl(key) { return `${PUBLIC_BASE}/media/${encodeURIComponent(key)}`; }
