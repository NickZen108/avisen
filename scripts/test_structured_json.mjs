import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const mod = await import(pathToFileURL(resolve("cloudflare/newsdesk/src/editorial.js")).href);
const {
  parseJsonText,
  schemaShapeValid,
  structuredPayloadDiff,
  namedAccusedCrimeClaim,
  evidenceRulePass,
  authoritativeClaimSource,
} = mod;

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

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

const before = { decision: "hold", claims: [{ id: "F01", claim: "A", source_indexes: [1] }] };
const afterSame = { decision: "hold", claims: [{ id: "F01", claim: "A", source_indexes: [1] }] };
const afterChanged = { decision: "publish", claims: [{ id: "F01", claim: "A", source_indexes: [0] }] };
assert(structuredPayloadDiff(before, afterSame).changed === false, "diff same");
assert(structuredPayloadDiff(before, afterChanged).changed === true, "diff decision");

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
