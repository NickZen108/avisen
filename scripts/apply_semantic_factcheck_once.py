from pathlib import Path

p = Path('cloudflare/newsdesk/src/editorial.js')
s = p.read_text(encoding='utf-8')

old = '''const deskRecheckSchema = { type: "object", properties: {
  decision: { type: "string", enum: ["publish", "update", "hold", "kill"] }, rationale: { type: "string" },
}, required: ["decision", "rationale"] };'''
new = '''const semanticFactCheckSchema = {
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
}, required: ["decision", "rationale"] };'''
assert old in s, 'schema anchor missing'
s = s.replace(old, new, 1)

old = 'Sæt conflict_present=true kun når historien faktisk rummer en relevant politisk, juridisk, faglig eller parts-konflikt; almindelige hændelsesfakta/statistik kræver ikke kunstig pluralisme. Opfind intet.`;'
new = 'Sæt conflict_present=true kun når historien faktisk rummer en relevant politisk, juridisk, faglig eller parts-konflikt; almindelige hændelsesfakta/statistik kræver ikke kunstig pluralisme. Ved oversættelse eller parafrase fra et andet sprog skal betydningen bevares præcist: hvem gør hvad mod hvem/hvad, subjekt, objekt, negation, modalitet, årsag, tid og tal må ikke skifte. Oversæt ikke et ord som response/efforts/measure til selve hændelsen eller problemet, hvis det ændrer betydningen. Opfind intet.`;'
assert old in s, 'research prompt anchor missing'
s = s.replace(old, new, 1)

old = 'Rejected når evidensen modsiger claimet; ellers uncertain. Ét verificeret bærende claim er nok til en kort one-claim-artikel; usikre sekundære detaljer skal blot udelades. Opfind ingen nye kilder, fakta eller citater.'
new = 'Kontrollér også semantisk oversættelse/parafrase mod originalteksten: subjekt, objekt, negation, modalitet, årsag, tid og tal skal betyde det samme. Hvis fx kilden siger at indsatsen/response skal intensiveres, må claimet ikke sige at selve udbruddet/hændelsen skal intensiveres. En sådan betydningsændring er rejected eller uncertain, ikke verified. Rejected når evidensen modsiger claimet; ellers uncertain. Ét verificeret bærende claim er nok til en kort one-claim-artikel; usikre sekundære detaljer skal blot udelades. Opfind ingen nye kilder, fakta eller citater.'
assert old in s, 'fact prompt anchor missing'
s = s.replace(old, new, 1)

anchor = 'async function deskRecheck(env, assignment, dossier) {'
insert = '''async function finalSemanticFactCheck(env, assignment, dossier, article) {
  const sources = (dossier.researched || []).filter(isEvidenceSource).map((source, i) => ({
    source_index: i, name: source.source, headline: source.headline,
    url: source.final_url || source.url,
    excerpt: String(source.excerpt || source.description || "").slice(0, 2400),
  }));
  const system = `Du er den samme uafhængige Fact checker i et sidste semantisk pass. Sammenlign HELE den færdige danske artikel med de eksisterende originalkilder. Dette er ikke en ny kildegate og du må IKKE kræve flere kilder. Kontrollér kun sandhed og betydningsbevarelse: alle materielle udsagn skal kunne rummes i det verificerede materiale, og oversættelse/parafrase skal bevare hvem der gør hvad mod hvem/hvad, subjekt, objekt, negation, modalitet, årsag, tid, attribution og tal. Fri og naturlig dansk formulering er tilladt; ord-for-ord-oversættelse er ikke et krav. HOLD kun ved reel materiel betydningsændring, oversættelsesfejl, unsupported claim eller forkert attribution. Stil, tone, SEO og små sproglige præferencer er aldrig fejl her. Eksempel på materiel fejl: 'response/indsatsen skal intensiveres' må ikke blive til 'udbruddet skal intensiveres'.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources, article }), semanticFactCheckSchema, 700, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
}

async function reviseSemanticFactIssues(env, assignment, dossier, article, semantic) {
  if (semantic?.decision !== "hold" || !(semantic?.issues || []).length) return article;
  const sources = (dossier.researched || []).filter(isEvidenceSource).map((source, i) => ({
    source_index: i, name: source.source, headline: source.headline,
    excerpt: String(source.excerpt || source.description || "").slice(0, 2400),
  }));
  const system = `Ret KUN de konkrete semantiske/faktuelle problemer fundet af Fact checker. Bevar artikelstruktur, vinkel og verificerede fakta så vidt muligt. Ret oversættelser så subjekt, objekt, negation, modalitet, årsag, tid, attribution og tal svarer til originalkilden. Tilføj ingen nye claims og kræv ingen nye kilder. Returnér hele artiklen i samme schema.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources, article, issues: semantic.issues }), articleSchema, assignment.weight === "A" || assignment.weight === "B" ? 2200 : 1400, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
}

async function deskRecheck(env, assignment, dossier) {'''
assert anchor in s, 'desk anchor missing'
s = s.replace(anchor, insert, 1)

old = '''  let article = await writeArticle(env, assignment, dossier);
  const aiFinalRequired = requiresAiFinalReview(assignment, dossier, article);'''
new = '''  let article = await writeArticle(env, assignment, dossier);
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
  const aiFinalRequired = requiresAiFinalReview(assignment, dossier, article);'''
assert old in s, 'article/final anchor missing'
s = s.replace(old, new, 1)

old = 'fact_check: { rationale: dossier.rationale, claims: dossier.claims, contradictions: dossier.contradictions }, desk_recheck: desk, final_review: review,'
new = 'fact_check: { rationale: dossier.rationale, claims: dossier.claims, contradictions: dossier.contradictions, semantic: semanticFactCheck }, desk_recheck: desk, final_review: review,'
assert old in s, 'audit anchor missing'
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('semantic fact-check patch applied')
