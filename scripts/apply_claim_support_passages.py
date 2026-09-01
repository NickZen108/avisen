#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

p = ROOT / 'cloudflare' / 'newsdesk' / 'src' / 'editorial.js'
s = p.read_text(encoding='utf-8')

old = '''      id: { type: "string" }, claim: { type: "string" }, source_indexes: { type: "array", items: { type: "integer" }, minItems: 1 },
      status: { type: "string", enum: ["verified", "uncertain", "rejected"] }, notes: { type: "string" },
    }, required: ["id", "claim", "source_indexes", "status", "notes"] } },'''
new = '''      id: { type: "string" }, claim: { type: "string" }, source_indexes: { type: "array", items: { type: "integer" }, minItems: 1 },
      evidence: { type: "array", minItems: 1, maxItems: 8, items: { type: "object", properties: {
        source_index: { type: "integer" }, quote: { type: "string" },
      }, required: ["source_index", "quote"] } },
      status: { type: "string", enum: ["verified", "uncertain", "rejected"] }, notes: { type: "string" },
    }, required: ["id", "claim", "source_indexes", "evidence", "status", "notes"] } },'''
if old not in s:
    raise SystemExit('factCheckSchema anchor missing')
s = s.replace(old, new, 1)

anchor = '''function evidenceRulePass(assignment, research, claim, evidence) {
  const primaryOk = evidence.some(authoritativePrimary);
  if (namedAccusedCrimeClaim(assignment, claim)) return primaryOk;
  const wireOk = evidence.some(authoritativeEditorial);
  const atoms = new Set(evidence.map(evidenceAtom).filter(Boolean));
  if (highRiskFactClaim(assignment, research, claim)) return primaryOk || atoms.size >= 2;
  return primaryOk || wireOk || atoms.size >= 2;
}
'''
replacement = anchor + '''function normalizedPassageText(value) {
  return String(value || "").normalize("NFKC").toLocaleLowerCase("da-DK")
    .replace(/[“”„‟«»]/g, '"').replace(/[‘’‚‛]/g, "'").replace(/[–—−]/g, "-")
    .replace(/\\s+/g, " ").trim();
}
function supportPassageValid(claim, support, source) {
  if (!source || !support || !Number.isInteger(support.source_index)) return false;
  const quote = normalizedPassageText(support.quote);
  const hay = normalizedPassageText(source.excerpt || source.description || "");
  if (quote.length < 24 || !hay.includes(quote)) return false;
  const claimWords = [...new Set(words(claim?.claim || ""))];
  const quoteWords = new Set(words(support.quote || ""));
  if (claimWords.length) {
    const overlap = claimWords.filter((x) => quoteWords.has(x)).length;
    if (overlap < Math.min(2, claimWords.length)) return false;
  }
  if (numericMaterialClaim(claim)) {
    const nums = String(claim?.claim || "").match(/\\d+(?:[.,]\\d+)?/g) || [];
    if (nums.length && !nums.some((n) => quote.includes(normalizedPassageText(n)))) return false;
  }
  return true;
}
function verifiedSupportPassages(claim, researched) {
  const out = [];
  const seen = new Set();
  for (const row of Array.isArray(claim?.evidence) ? claim.evidence : []) {
    const i = row?.source_index;
    if (!Number.isInteger(i) || i < 0 || i >= researched.length || seen.has(i)) continue;
    const source = researched[i];
    if (!isEvidenceSource(source) || !supportPassageValid(claim, row, source)) continue;
    seen.add(i);
    out.push({ source_index: i, quote: String(row.quote || "").trim(), match_verified: true });
  }
  return out;
}
'''
if anchor not in s:
    raise SystemExit('evidenceRulePass anchor missing')
s = s.replace(anchor, replacement, 1)

old = '''  const system = `Du er en UAFHÆNGIG Fact checker på Morgentidende. Forsøg aktivt at falsificere hvert kandidat-claim mod de vedlagte kildetekster. Discovery-blogs og perspektiv/advocacy-feeds er fjernet før dette trin og må aldrig bruges som kilder. For almindelige lavrisiko-fakta kan Verified bæres af én autoritativ primærkilde inden for dens kompetenceområde, én dokumenteret original bureaukilde (Reuters/AP/AFP/Ritzau), eller to provenance-uafhængige troværdige evidenskilder. Ét almindeligt redaktionelt medie kan ikke stå alene. Ved højrisiko kræves primærkilde eller mindst to provenance-uafhængige evidenskilder. Samme bureau/pressemeddelelse tæller kun én gang. Ved højrisiko/fairness-påstande skal du være mere forsigtig og ikke lade én almindelig redaktionel kilde stå alene. Ved navngivne sigtede/tiltalte/mistænkte i kriminalstof kræves en relevant primærkilde fra politi/ret/myndighed. For alle materielle tal (døde, penge, procent, antal osv.) skal du aktivt sammenligne/falsificere tallet mod alle vedlagte relevante kilder; ved mismatch skal claimet være uncertain eller formuleres forsigtigt/attribueret, aldrig vælg automatisk det højeste tal. Rejected når evidensen modsiger claimet; ellers uncertain. Ét verificeret bærende claim er nok til en kort one-claim-artikel; usikre sekundære detaljer skal blot udelades. Opfind ingen nye kilder eller fakta. Din overordnede publish/hold-vurdering er rådgivende; en deterministisk gate beregner den endelige beslutning efter claim-kontrollen.`;'''
new = '''  const system = `Du er en UAFHÆNGIG Fact checker på Morgentidende. Forsøg aktivt at falsificere hvert kandidat-claim mod de vedlagte kildetekster. Discovery-blogs og perspektiv/advocacy-feeds er fjernet før dette trin og må aldrig bruges som kilder. For HVER source_index du bruger som støtte skal evidence indeholde samme source_index og en KORT, ORDRET passage kopieret direkte fra den vedlagte excerpt, som faktisk dokumenterer netop claimet. Brug aldrig en kilde som støtte blot fordi den handler om samme historie. Hvis du ikke kan citere en konkret støttepassage, må source_index ikke bruges som evidens. For almindelige lavrisiko-fakta kan Verified bæres af én autoritativ primærkilde inden for dens kompetenceområde, én dokumenteret original bureaukilde (Reuters/AP/AFP/Ritzau), eller to provenance-uafhængige troværdige evidenskilder. Ét almindeligt redaktionelt medie kan ikke stå alene. Ved højrisiko kræves primærkilde eller mindst to provenance-uafhængige evidenskilder. Samme bureau/pressemeddelelse tæller kun én gang. Ved højrisiko/fairness-påstande skal du være mere forsigtig og ikke lade én almindelig redaktionel kilde stå alene. Ved navngivne sigtede/tiltalte/mistænkte i kriminalstof kræves en relevant primærkilde fra politi/ret/myndighed. For alle materielle tal (døde, penge, procent, antal osv.) skal du aktivt sammenligne/falsificere tallet mod alle vedlagte relevante kilder; ved mismatch skal claimet være uncertain eller formuleres forsigtigt/attribueret, aldrig vælg automatisk det højeste tal. Rejected når evidensen modsiger claimet; ellers uncertain. Ét verificeret bærende claim er nok til en kort one-claim-artikel; usikre sekundære detaljer skal blot udelades. Opfind ingen nye kilder, fakta eller citater. Din overordnede publish/hold-vurdering er rådgivende; en deterministisk gate beregner den endelige beslutning efter claim-kontrollen.`;'''
if old not in s:
    raise SystemExit('fact checker prompt anchor missing')
s = s.replace(old, new, 1)

old = '''  for (const claim of fact.claims) {
    const indexes = [...new Set((claim.source_indexes || []).filter((i) => Number.isInteger(i) && i >= 0 && i < fact.researched.length))];
    claim.source_indexes = indexes;
    const evidence = indexes.map((i) => fact.researched[i]).filter(isEvidenceSource);
    claim.numeric_material = numericMaterialClaim(claim);
    claim.named_accused_primary_required = namedAccusedCrimeClaim(assignment, claim);
    if (claim.status === "verified" && !evidenceRulePass(assignment, research, claim, evidence)) {
      claim.status = "uncertain";
      claim.notes = `${claim.notes || ""} Nedgraderet af deterministisk gate: dokumentationen opfylder ikke kildekravet for claimets risikoniveau.`.trim();
    }
  }'''
new = '''  for (const claim of fact.claims) {
    const requestedIndexes = [...new Set((claim.source_indexes || []).filter((i) => Number.isInteger(i) && i >= 0 && i < fact.researched.length))];
    const support = verifiedSupportPassages(claim, fact.researched).filter((x) => requestedIndexes.includes(x.source_index));
    const indexes = support.map((x) => x.source_index);
    claim.source_indexes = indexes;
    claim.support_passages = support;
    const evidence = indexes.map((i) => fact.researched[i]).filter(isEvidenceSource);
    claim.numeric_material = numericMaterialClaim(claim);
    claim.named_accused_primary_required = namedAccusedCrimeClaim(assignment, claim);
    if (claim.status === "verified" && (!indexes.length || !evidenceRulePass(assignment, research, claim, evidence))) {
      claim.status = "uncertain";
      claim.notes = `${claim.notes || ""} Nedgraderet af deterministisk gate: claimet mangler en maskinverificeret støttepassage eller opfylder ikke kildekravet for risikoniveauet.`.trim();
    }
  }'''
if old not in s:
    raise SystemExit('fact claim normalization anchor missing')
s = s.replace(old, new, 1)

old = '''    return { id: `F${String(i + 1).padStart(2, "0")}`, claim: c.claim, status: "verified", source_ids: ids, independent_groups: ids.map((id) => sources.find((s) => s.id === id && !s.discovery_only)?.source_group).filter(Boolean), checked_at: accessedAt, notes: c.notes || "" };'''
new = '''    const support_passages = (c.support_passages || []).map((x) => ({ source_id: sources[x.source_index]?.id, quote: x.quote, match_verified: x.match_verified === true })).filter((x) => x.source_id && ids.includes(x.source_id));
    return { id: `F${String(i + 1).padStart(2, "0")}`, claim: c.claim, status: "verified", source_ids: ids, support_passages, independent_groups: ids.map((id) => sources.find((s) => s.id === id && !s.discovery_only)?.source_group).filter(Boolean), checked_at: accessedAt, notes: c.notes || "" };'''
if old not in s:
    raise SystemExit('ledger claim anchor missing')
s = s.replace(old, new, 1)

s = s.replace('''    schema_version: 2, story_id: storyId, article_slug: slug,''', '''    schema_version: 3, story_id: storyId, article_slug: slug,''', 1)
s = s.replace('''    fact_check: { status: "pass", checked_at: accessedAt, notes: ["Uafhængigt Fact checker-call bestået; discovery-only-kilder kan ikke alene verificere claims."] },''', '''    fact_check: { status: "pass", checked_at: accessedAt, notes: ["Uafhængigt Fact checker-call bestået; hvert publiceret claim har mindst én maskinverificeret støttepassage, og discovery-only-kilder kan ikke verificere claims."] },''', 1)
p.write_text(s, encoding='utf-8')

p = ROOT / 'scripts' / 'evidence_policy.py'
e = p.read_text(encoding='utf-8')
old = '''def claim_has_required_support(article: dict, ledger: dict, claim: dict, sources: dict[str, dict]) -> bool:
    rows = [sources.get(sid) for sid in claim.get("source_ids", [])]
    rows = [s for s in rows if s]'''
new = '''def claim_has_required_support(article: dict, ledger: dict, claim: dict, sources: dict[str, dict]) -> bool:
    source_ids = list(claim.get("source_ids", []))
    if int(ledger.get("schema_version") or 0) >= 3:
        verified_passages = {
            str(x.get("source_id")) for x in claim.get("support_passages", [])
            if x.get("match_verified") is True and str(x.get("quote") or "").strip()
        }
        source_ids = [sid for sid in source_ids if sid in verified_passages]
        if not source_ids:
            return False
    rows = [sources.get(sid) for sid in source_ids]
    rows = [s for s in rows if s]'''
if old not in e:
    raise SystemExit('python claim support anchor missing')
e = e.replace(old, new, 1)
p.write_text(e, encoding='utf-8')

p = ROOT / 'scripts' / 'evidence_policy_selftest.py'
t = p.read_text(encoding='utf-8')
needle = "check('wire low risk passes',True,a,l,{'claim':'En almindelig oplysning','source_ids':['S1']},[src('S1','host-reuters-com',wire_origin='reuters')])\n"
insert = needle + "l3={'schema_version':3,'right_of_reply':{'required':False}}\ncheck('v3 missing support passage fails',False,a,l3,{'claim':'En almindelig oplysning','source_ids':['S1'],'support_passages':[]},[src('S1','host-reuters-com',wire_origin='reuters')])\ncheck('v3 verified support passage passes',True,a,l3,{'claim':'En almindelig oplysning','source_ids':['S1'],'support_passages':[{'source_id':'S1','quote':'En almindelig oplysning fremgår her.','match_verified':True}]},[src('S1','host-reuters-com',wire_origin='reuters')])\n"
if needle not in t:
    raise SystemExit('selftest insertion anchor missing')
t = t.replace(needle, insert, 1)
p.write_text(t, encoding='utf-8')

print('Claim support passage migration applied')
