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
function schemaShapeValid(value, schema) {
  if (!schema) return false;
  if (schema.type === "object") {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    for (const key of schema.required || []) {
      if (!(key in value)) return false;
      if (typeof value[key] === "string" && !String(value[key]).trim()) return false;
    }
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
  return false;
}
function structuredPayloadDiff(before, after) {
  if (!before || !after || typeof before !== "object" || typeof after !== "object") return { changed: false };
  for (const key of ["decision", "status"]) {
    if (key in before && before[key] !== after[key]) return { changed: true, field: key };
  }
  const listKey = Array.isArray(before.claims) ? "claims" : Array.isArray(before.candidate_claims) ? "candidate_claims" : null;
  if (listKey && Array.isArray(after[listKey])) {
    const fingerprint = (rows) => rows.map((c) => `${c?.id || ""}|${c?.claim || ""}|${JSON.stringify(c?.source_indexes || [])}`).join("||");
    if (fingerprint(before[listKey] || []) !== fingerprint(after[listKey] || [])) return { changed: true, field: listKey };
  }
  return { changed: false };
}
function namedAccusedCrimeClaim(_assignment, claim) {
  const text = String(claim?.claim || "");
  if (!/\b(sigtet|tiltalt|mistænkt)\b/iu.test(text)) return false;
  return /\b[A-ZÆØÅ][a-zæøåéèáàíìóòúù-]+\s+[A-ZÆØÅ][a-zæøåéèáàíìóòúù-]+\b/u.test(text);
}
function hostOf(value) {
  try { return new URL(value).hostname.replace(/^www\./, "").toLowerCase(); } catch (_) { return ""; }
}
function wireOrigin(item) {
  const host = hostOf(item?.final_url || item?.url || "");
  const source = String(item?.source || "").toLowerCase().trim();
  if (host === "reuters.com" || host.endsWith(".reuters.com") || source === "reuters") return "reuters";
  if (host === "apnews.com" || host.endsWith(".apnews.com") || source === "ap" || source === "associated press") return "ap";
  return null;
}
const STRONG = ["reuters.com","apnews.com","bbc.com","bbc.co.uk","dr.dk","tv2.dk","nrk.no","theguardian.com","euronews.com","aljazeera.com"];
function strongEditorialSource(item) {
  const host = hostOf(item?.final_url || item?.url || "");
  return STRONG.some((x) => host === x || host.endsWith("." + x));
}
function authoritativeClaimSource(item) {
  if (!item) return false;
  if (item.discovery_only) return false;
  if (wireOrigin(item) || strongEditorialSource(item)) return true;
  const kind = String(item.source_kind || "").toLowerCase();
  const scoped = ["paper","expert","official_statement","company_statement"];
  if (scoped.includes(kind)) return Boolean(String(item.authoritative_for || "").trim());
  return false;
}
function evidenceRulePass(assignment, research, claim, evidence) {
  if (!evidence.some(authoritativeClaimSource)) return false;
  if (namedAccusedCrimeClaim(assignment, claim)) return evidence.some((item) => Boolean(wireOrigin(item)));
  return true;
}
function assert(cond, msg) { if (!cond) throw new Error(msg); }

assert(JSON.stringify(parseJsonText('{"a":1}')) === '{"a":1}', "plain json");
assert(JSON.stringify(parseJsonText("```json\n{\"a\":1}\n```")) === '{"a":1}', "fenced json");
assert(JSON.stringify(parseJsonText("Her er svaret\n{\"a\":1}\nok")) === '{"a":1}', "prose + json");
assert(parseJsonText('{"ok":true} {"claims":[]}').ok === true, "first object wins");
assert(parseJsonText("ikke json") === null, "unparseable");

const factSchema = {
  type: "object",
  properties: {
    decision: { type: "string", enum: ["publish", "hold"] },
    claims: {
      type: "array",
      minItems: 1,
      items: {
        type: "object",
        properties: {
          id: { type: "string" },
          claim: { type: "string" },
          source_indexes: { type: "array", items: { type: "integer" } },
        },
        required: ["id", "claim", "source_indexes"],
      },
    },
  },
  required: ["decision", "claims"],
};
assert(!schemaShapeValid({ decision: "hold" }, factSchema), "missing claims");
assert(!schemaShapeValid({ decision: "hold", claims: {} }, factSchema), "claims object");
assert(!schemaShapeValid({ decision: "hold", claims: [] }, factSchema), "empty claims");
assert(!schemaShapeValid({ decision: "hold", claims: [{ id: "F01", claim: "", source_indexes: [0] }] }, factSchema), "empty claim text");
assert(!schemaShapeValid({ decision: "maybe", claims: [{ id: "F01", claim: "x", source_indexes: [0] }] }, factSchema), "bad enum");
assert(schemaShapeValid({ decision: "hold", claims: [{ id: "F01", claim: "x", source_indexes: [0] }] }, factSchema), "valid fact");
assert(structuredPayloadDiff({ decision: "hold", claims: [{ id: "F01", claim: "A", source_indexes: [1] }] }, { decision: "hold", claims: [{ id: "F01", claim: "A", source_indexes: [1] }] }).changed === false, "diff same");
assert(structuredPayloadDiff({ decision: "hold", claims: [{ id: "F01", claim: "A", source_indexes: [1] }] }, { decision: "publish", claims: [{ id: "F01", claim: "A", source_indexes: [0] }] }).changed === true, "diff decision");
assert(namedAccusedCrimeClaim({}, { claim: "Anders Jensen er sigtet for drab" }) === true, "named accused");
assert(namedAccusedCrimeClaim({}, { claim: "En person er mistænkt for drab" }) === false, "unnamed");
assert(namedAccusedCrimeClaim({}, { claim: "Tyler Robinson pleads not guilty" }) === false, "english not auto-named");
const bbc = { url: "https://www.bbc.com/news/x", final_url: "https://www.bbc.com/news/x", source: "BBC", source_kind: "news" };
const reuters = { url: "https://www.reuters.com/world/x", final_url: "https://www.reuters.com/world/x", source: "Reuters", source_kind: "news" };
const blog = { url: "https://blog.example.invalid/x", final_url: "https://blog.example.invalid/x", source: "Blog", source_kind: "public_media" };
assert(authoritativeClaimSource(bbc) === true, "bbc authoritative");
assert(authoritativeClaimSource(blog) === false, "label-only blog not authoritative");
assert(evidenceRulePass({}, {}, { claim: "En person er mistænkt for drab" }, [bbc]) === true, "unnamed high risk bbc");
assert(evidenceRulePass({}, {}, { claim: "Anders Jensen er sigtet for drab" }, [bbc]) === false, "named accused bbc fails");
assert(evidenceRulePass({}, {}, { claim: "Anders Jensen er sigtet for drab" }, [reuters]) === true, "named accused reuters passes");
console.log("structured_json self-test: PASS");
