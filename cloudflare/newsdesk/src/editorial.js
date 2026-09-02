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
async function aiJson(env, system, user, schema, maxTokens = 2800, model = STRONG_TEXT_MODEL, fallbackModel = null) {
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
    try { env.__AI_FALLBACK_COUNT__ = Number(env.__AI_FALLBACK_COUNT__ || 0) + 1; } catch (_) {}
  }
  try {
    const raw = await env.AI.run(fallbackModel, request);
    return structuredResponse(raw, schema);
  } catch (error) {
    console.warn("Workers AI schema fallback still malformed; trying JSON-object repair", String(error));
    try { env.__AI_FALLBACK_COUNT__ = Number(env.__AI_FALLBACK_COUNT__ || 0) + 1; } catch (_) {}
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
      primary_language: { type: "string" }, primary_language_code: { type: "string" },
      place_names_local: { type: "array", maxItems: 6, items: { type: "string" } },
      place_names_english: { type: "array", maxItems: 6, items: { type: "string" } },
      transliterations: { type: "array", maxItems: 6, items: { type: "string" } },
      hero_queries_local: { type: "array", maxItems: 3, items: { type: "string" } },
      hero_queries_english: { type: "array", maxItems: 3, items: { type: "string" } },
      hero_queries_transliterated: { type: "array", maxItems: 3, items: { type: "string" } },
    }, required: ["country", "country_code", "primary_language", "primary_language_code", "place_names_local", "place_names_english", "transliterations", "hero_queries_local", "hero_queries_english", "hero_queries_transliterated"] },
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

const semanticFactCheckSchema = {
  type: "object", properties: {
    decision: { type: "string", enum: ["pass", "hold"] },
    issues: { type: "array", maxItems: 8, items: { type: "object", properties: {
      type: { type: "string", enum: ["meaning_shift", "translation_error", "unsupported_claim", "attribution_error"] },
      issue: { type: "string" }, source_indexes: { type: "array", items: { type: "integer" }, minItems: 1 },
    }, required: ["type", "issue", "source_indexes"] } },
    notes: { type: "array", maxItems: 8, items: { type: "string" } },
  }, required: ["decision", "issues", "notes"],
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
  const system = `Du er Morgentidendes første Nyhedsdesk. Vælg ét konkret research-frø. RESEARCH er standard ved reel nyhedsværdi, originalitet, offentlig betydning eller tydelig redaktionel relevans; tynd dokumentation er Researchs problem, ikke en afvisningsgrund. WATCH kun hvis nyhedskrogen/aktualiteten endnu er uklar. DROP kun ved klar dublet, gammel/triviel sag, rent holdningsstof uden nyhedskrog eller åbenlys spam. discovery_only må udløse Research, men er aldrig dokumentation. Sæt kategori og A-D-vægt. Fastslå samtidig story_location FØR research og hero: primært land, ISO-landekode, vigtigste lokale sprog, lokale og engelske stednavne samt evt. translitterationer. Lav 1-3 korte hero-søgefraser på lokalt sprog og 1-3 på engelsk; ved andet alfabet også translittererede varianter. Brug hændelsestype + sted + år når det er kendt. Oversæt ikke egennavne forkert. Hvis landet reelt er uklart eller sagen ikke har ét primært land, brug country='unknown', country_code='', primary_language='unknown' og tomme lokale arrays, men lav stadig engelske hero-termer hvis muligt. Svar ultrakort.`;
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
function evidenceGroups(items) { return [...new Set(items.filter(isEvidenceSource).map(evidenceSourceGroup))]; }
function authoritativeClaimSource(item) {
  if (!isEvidenceSource(item)) return false;
  if (authoritativePrimary(item) || authoritativeEditorial(item) || strongEditorialSource(item)) return true;
  const kind = normalizedSourceKind(item);
  return ["paper", "research_paper", "researcher", "scientist", "expert", "company_statement", "organization_statement", "person_statement", "first_party_statement", "interview", "official_statement"].includes(kind);
}

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
  for (const item of prioritized) {
    const url = item.final_url || item.url;
    if (!url || seenUrls.has(url)) continue;
    seenUrls.add(url);
    unique.push(item);
    if (unique.length >= 4) break;
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
    excerpt: item.excerpt.slice(0, 1800),
    discovery_only: false,
    source_kind: normalizedSourceKind(item),
    source_strength: authoritativePrimary(item) ? "primary" : authoritativeEditorial(item) ? "wire" : strongEditorialSource(item) ? "strong_editorial" : "standard",
    upstream_origin: item.upstream_origin || null,
    byline: item.provenance_meta?.byline || null,
    publisher: item.provenance_meta?.publisher || null,
    canonical_url: item.provenance_meta?.canonical_url || null,
    feed_summary_only: Boolean(item.feed_summary_only),
  }));
  const system = `Du er Research på Morgentidende. Lav et kompakt evidens-kort til Fact checker; vurder ikke nyhedsværdi igen og fæld ikke den endelige sandhedsdom. Kortlæg 1-6 bærende kandidat-claims med præcise source_indexes. Notér kun reelle modsigelser, væsentlige forbehold og nødvendig kontekst. En primærkilde er værdifuld, men du skal ikke kræve et bestemt antal medier. Hvis mindst ét brugbart claim kan kildebelægges, vælg continue; watch kun hvis materialet reelt ikke giver noget kontrollerbart. Flag alvorlige belastende påstande via right_of_reply_required, men brug ikke flaget som stopregel. Sæt conflict_present=true kun når historien faktisk rummer en relevant politisk, juridisk, faglig eller parts-konflikt; almindelige hændelsesfakta/statistik kræver ikke kunstig pluralisme. Ved oversættelse eller parafrase fra et andet sprog skal betydningen bevares præcist: hvem gør hvad mod hvem/hvad, subjekt, objekt, negation, modalitet, årsag, tid og tal må ikke skifte. Oversæt ikke et ord som response/efforts/measure til selve hændelsen eller problemet, hvis det ændrer betydningen. Opfind intet.`;
  const research = await aiJson(env, system, JSON.stringify({ assignment, sources }), researchSchema, 650, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
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
  const system = `Du er en UAFHÆNGIG Fact checker på Morgentidende. Forsøg aktivt at falsificere hvert kandidat-claim mod de vedlagte kildetekster. Discovery-blogs og perspektiv/advocacy-feeds er fjernet før dette trin og må aldrig bruges som kilder. Angiv kun source_indexes for kilder, der faktisk dokumenterer claimet; brug aldrig en kilde som støtte blot fordi den handler om samme historie. Et claim kan få Verified på baggrund af én relevant autoritativ kilde. Autoritative kilder er: (1) store etablerede redaktionelle medier som BBC, Reuters, AP, Financial Times m.fl., (2) myndigheder/officielle kilder, (3) virksomheder, organisationer eller personer om egne forhold, (4) relevante forskere/fageksperter inden for deres fagområde og (5) forskningspapirer/original forskning. Originale bureaukilder som Reuters/AP/AFP/Ritzau er også autoritative. Kræv ikke automatisk kilde nr. 2, når én relevant autoritativ kilde dokumenterer claimet. Ved høj risiko, alvorlige beskyldninger eller fairness kan ekstra kontrol, attribution, forelæggelse eller Etik-review være nødvendig, men høj risiko skaber ikke i sig selv en mekanisk to-kilde-regel. For alle materielle tal (døde, penge, procent, antal osv.) skal du aktivt sammenligne/falsificere tallet mod alle vedlagte relevante kilder; ved mismatch skal claimet være uncertain eller formuleres forsigtigt/attribueret, aldrig vælg automatisk det højeste tal. Kontrollér også, at oversættelse og parafrase samlet bevarer originalkildens betydning. Vurder meningen i hele udsagnet frem for at anvende mekaniske grammatiske delregler. Hvis den danske gengivelse ændrer den materielle betydning, er claimet rejected eller uncertain, ikke verified. Rejected når evidensen modsiger claimet; ellers uncertain. Ét verificeret bærende claim er nok til en kort one-claim-artikel; usikre sekundære detaljer skal blot udelades. Opfind ingen nye kilder, fakta eller citater. Din overordnede publish/hold-vurdering er rådgivende; en deterministisk gate beregner den endelige beslutning efter claim-kontrollen.`;
  const fact = await aiJson(env, system, JSON.stringify({
    assignment,
    research: { core_question: research.core_question, rationale: research.rationale, contradictions: research.contradictions, candidate_claims: research.candidate_claims },
    sources: (research.source_payload || []).map((source, i) => ({
      ...source,
      excerpt: focusedExcerpt(research.researched?.[i]?.excerpt || source.excerpt, research.candidate_claims, 500),
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
    if (claim.status === "verified" && (!indexes.length || !evidenceRulePass(assignment, research, claim, evidence))) {
      claim.status = "uncertain";
      claim.notes = `${claim.notes || ""} Nedgraderet af deterministisk gate: claimet mangler en relevant autoritativ kilde.`.trim();
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

async function finalSemanticFactCheck(env, assignment, dossier, article) {
  const sources = (dossier.researched || []).filter(isEvidenceSource).map((source, i) => ({
    source_index: i, name: source.source, headline: source.headline,
    url: source.final_url || source.url,
    excerpt: String(source.excerpt || source.description || "").slice(0, 2400),
  }));
  const system = `Du er den samme uafhængige Fact checker i et sidste semantisk pass. Sammenlign HELE den færdige danske artikel med de eksisterende originalkilder og vurder samlet, om betydningen er bevaret korrekt hele vejen igennem. Dette er ikke en ny kildegate og du må IKKE kræve flere kilder. Se på helheden og meningen i hver passage frem for at anvende en tjekliste af grammatiske delregler. Fri og naturlig dansk formulering er tilladt; ord-for-ord-oversættelse er ikke et krav. HOLD kun ved reel materiel betydningsændring, oversættelsesfejl, unsupported claim eller forkert attribution. Stil, tone, SEO og små sproglige præferencer er aldrig fejl her. Hvis du finder en fejl, angiv den konkrete danske passage og hvad originalkilden faktisk betyder.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources, article }), semanticFactCheckSchema, 700, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
}

async function reviseSemanticFactIssues(env, assignment, dossier, article, semantic) {
  if (semantic?.decision !== "hold" || !(semantic?.issues || []).length) return article;
  const sources = (dossier.researched || []).filter(isEvidenceSource).map((source, i) => ({
    source_index: i, name: source.source, headline: source.headline,
    excerpt: String(source.excerpt || source.description || "").slice(0, 2400),
  }));
  const system = `Ret KUN de konkrete semantiske/faktuelle problemer fundet af Fact checker. Bevar artikelstruktur, vinkel og verificerede fakta så vidt muligt. Ret oversættelser og parafraser, så den samlede betydning svarer til originalkilden. Tilføj ingen nye claims og kræv ingen nye kilder. Returnér hele artiklen i samme schema.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources, article, issues: semantic.issues }), articleSchema, assignment.weight === "A" || assignment.weight === "B" ? 2200 : 1400, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
}

async function deskRecheck(env, assignment, dossier) {
  if (assignment.weight !== "A") {
    return { decision: "publish", rationale: "Fact check bestået; intet særskilt A-recheck nødvendigt" };
  }
  const system = `Du er Nyhedsdesk ved et ultrakort A/breaking-recheck efter bestået Fact check. Genresearch ikke. Hold/kill kun hvis materialet viser, at nyhedskernen siden assignment er blevet materielt forældet eller har skiftet karakter. Ellers publish. Svar kort.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), contradictions: dossier.contradictions }), deskRecheckSchema, 140, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
}

async function writeArticle(env, assignment, dossier) {
  if ((dossier.researched || []).some(isDiscoveryOnly)) throw new Error("Discovery-only source crossed the Journalist boundary");
  const sources = dossier.researched.filter(isEvidenceSource).map((s, i) => ({ source_index: i, name: s.source, headline: s.headline, url: s.final_url || s.url }));
  const destinationBrief = magazineWritingBrief(assignment?.editorial_destination || "main");
  const system = `Du er journalist på Morgentidende. ${destinationBrief} Skriv præcist, levende og idiomatisk dansk, men brug KUN verificerede claims. Når kilden er norsk eller svensk, skal du oversætte fuldt til naturligt dansk; bokmåls-, nynorsk- og svenske ord eller bøjningsformer må ikke glide med over i teksten. Gør attribution tydelig og brug gerne korte, præcise citater når de faktisk findes i det verificerede materiale; opfind aldrig citater. Hvis research har conflict_present=true, tilstræb relevant pluralisme mellem reelle parter/synsvinkler ud fra verificeret materiale. Hvis conflict_present=false, må du ikke konstruere kunstig pluralisme. Skriv til almindelige læsere: erstat fagord og engelske brancheord med almindeligt dansk, forklar nødvendige tekniske begreber første gang med 1-2 korte sætninger, og omsæt uvante mål til fx kilometer, meter, Celsius og kilogram. Forklar desuden alle egennavne kort første gang de optræder: angiv personers relevante rolle, hvad organisationer/virksomheder/institutioner er, hvad turneringer/ligaer/programmer dækker, og nødvendig geografisk kontekst for mindre kendte steder. Forklar naturligt og kort, uden leksikonfyld. En kort one-claim-nyhed med tre meningsfulde tekstblokke er fuldt acceptabel; fyld aldrig ud. Media ejer heroen; skriv ingen billedprompt eller billedmetadata.`;
  return aiJson(env, system, JSON.stringify({ assignment, conflict_present: Boolean(dossier.conflict_present), verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources }), articleSchema, assignment.weight === "A" || assignment.weight === "B" ? 2200 : 1400, FAST_TEXT_MODEL, assignment.weight === "A" || assignment.weight === "B" ? STRONG_TEXT_MODEL : null);
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
    ...(Array.isArray(loc.hero_queries_local) ? loc.hero_queries_local : []),
    ...(Array.isArray(loc.hero_queries_transliterated) ? loc.hero_queries_transliterated : []),
    ...(Array.isArray(loc.hero_queries_english) ? loc.hero_queries_english : []),
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
    ...(Array.isArray(loc.transliterations) ? loc.transliterations : []),
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

function makeLedger(storyId, slug, assignment, dossier, desk, accessedAt) {
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
    assignment: { category: assignment.category, weight: assignment.weight, editorial_destination: assignment.editorial_destination || "main", story_location: assignment.story_location || null, core_question: dossier.core_question || assignment.core_question, manual_review: false },
    sources,
    coverage_sweep: { status: groups.length >= 1 ? "pass" : "limited", editorial_source_ids: verificationSources.slice(0, 6).map((s) => s.id), independent_source_groups: groups.slice(0, 6), limitations: groups.length >= 1 ? null : "Ingen brugbar dokumentationskilde registreret", notes: ["Coverage beskriver kildegrundlaget; claim-verifikation afgøres særskilt. Ét claim kan verificeres af én relevant autoritativ kilde: stort redaktionelt medie, myndighed/officiel kilde, virksomhed/person om egne forhold, relevant forsker/fagekspert eller forskningspaper/original forskning. Flere kilder er til pluralisme, mod-evidens og ekstra sikkerhed — ikke en mekanisk kvote."] },
    claims, numbers: [], quotes: [], right_of_reply: { required: Boolean(dossier.right_of_reply_required), party: null, contacted_at: null, deadline: null, response: null, exception: dossier.right_of_reply_required ? "Flagged by Research; details must be supplied before any required forelæggelse can be considered complete" : null },
    fact_check: { status: "pass", checked_at: accessedAt, notes: ["Uafhængigt Fact checker-call bestået; hvert publiceret claim har mindst én relevant autoritativ kilde, og discovery-only-kilder kan ikke verificere claims."] },
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
  assignment.editorial_destination = editorialDestination(assignment, scan);
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
let semanticFactCheck = await finalSemanticFactCheck(env, assignment, dossier, article);
if (semanticFactCheck.decision !== "pass") {
  const revised = await reviseSemanticFactIssues(env, assignment, dossier, article, semanticFactCheck);
  if (JSON.stringify(revised) !== JSON.stringify(article)) {
    article = revised;
    semanticFactCheck = await finalSemanticFactCheck(env, assignment, dossier, article);
  }
}
if (semanticFactCheck.decision !== "pass") {
  return { status: "hold", stage: "fact-check", checked_at: startedAt, generated_at: startedAt, title: article.title || assignment.title_hint, reason: (semanticFactCheck.issues || []).map((x) => x.issue).join("; ") || "Fact checker: semantisk fejl mod originalkilden", scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment, article_title: article.title, fact_check: { claims: dossier.claims, rationale: dossier.rationale, semantic: semanticFactCheck } } };
}
const aiFinalRequired = requiresAiFinalReview(assignment, dossier, article);
  let review = aiFinalRequired ? await finalReview(env, assignment, dossier, article) : deterministicFinalReview(assignment, dossier, article);
  if (review.decision !== "pass") {
    const hardIssues = (review.issues || []).filter((x) => !["language", "seo"].includes(x.gate));
    const revised = await reviseFixableIssues(env, assignment, dossier, article, review);
    if (!hardIssues.length && JSON.stringify(revised) !== JSON.stringify(article)) {
      article = revised;
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
    category: assignment.category, weight: assignment.weight, editorial_destination: assignment.editorial_destination || "main", story_location: assignment.story_location || null, title: article.title, standfirst: article.standfirst,
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
    audit: { assignment, research: { rationale: research.rationale, candidate_claims: research.candidate_claims, contradictions: research.contradictions }, fact_check: { rationale: dossier.rationale, claims: dossier.claims, contradictions: dossier.contradictions, semantic: semanticFactCheck }, desk_recheck: desk, final_review: review, media_policy: { documentary_first: true, multilingual_location_search: true, pending_image: Boolean(hero.pending_image), temporary_sketch_allowed_after_scout: true, static_sketch_fallback: false, late_hold_for_no_photo: false }, source_count: ledger.sources.length, independent_source_groups: ledger.coverage_sweep.independent_source_groups },
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
