#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'cloudflare' / 'newsdesk' / 'src' / 'editorial.js'
text = PATH.read_text(encoding='utf-8')

def once(old, new, label):
    global text
    if old not in text:
        raise SystemExit(f'missing fragment: {label}')
    text = text.replace(old, new, 1)

# Final editor returns the final category directly instead of making category a retry/blocker.
once('''const finalSchema = { type: "object", properties: {
  blocking_issues: { type: "array", maxItems: 10, items: { type: "object", properties: {
    gate: { type: "string", enum: ["language", "ethics", "final_editor"] }, issue: { type: "string" },
  }, required: ["gate", "issue"] } },
}, required: ["blocking_issues"] };''', '''const finalSchema = { type: "object", properties: {
  category: { type: "string", enum: CATEGORIES },
  blocking_issues: { type: "array", maxItems: 10, items: { type: "object", properties: {
    gate: { type: "string", enum: ["language", "ethics", "final_editor"] }, issue: { type: "string" },
  }, required: ["gate", "issue"] } },
}, required: ["category", "blocking_issues"] };''', 'final schema')

# Mandatory whole-article language rewrite is removed. Language is repaired only when final editor finds a real issue.
text, n = re.subn(r'\nasync function polishArticleLanguage\(.*?\n}\n\nfunction deterministicFinalReview', '\nfunction deterministicFinalReview', text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('polishArticleLanguage removal failed')

# The short final editor becomes the single post-writing check for all stories.
text, n = re.subn(r'\nfunction deterministicFinalReview\(.*?\nasync function finalReview', '\nasync function finalReview', text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('deterministic/requiresAi final removal failed')

old_final = '''async function finalReview(env, assignment, dossier, article) {
  const system = `Du er uafhængig slutredaktør. Kontrollér den færdige artikel mod de verificerede claims uden at genresearche. Returnér kun reelle sikkerheds-/sandhedsproblemer som blockers: materielle påstande ud over dokumentationen, vildledende attribution, relevant men manglende fairness/pluralisme ved conflict_present=true, etisk problem, uklar/blandet genre eller en materielt forkert kategori i forhold til artikelens faktiske hovedemne og Morgentidendes kategorier. Hvis kategorien er forkert, rapportér det som final_editor-problem og angiv den korrekte kategori i issue-teksten. Kontrollér også at rubrik og manchet ikke er stærkere end dokumentationen. Sprog og SEO er repair/polish og må ikke i sig selv blokere. Media ejer hero og billedsandhed. Små stilpræferencer er aldrig blockers.`;
  const raw = await aiJson(env, system, JSON.stringify({ assignment, claims: dossier.claims, contradictions: dossier.contradictions, article }), finalSchema, 450, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
  const issues = Array.isArray(raw.blocking_issues) ? raw.blocking_issues.filter((x) => x?.gate && x?.issue) : [];
  const failed = new Set(issues.map((x) => x.gate));
  return { decision: issues.length ? "hold" : "pass", language: failed.has("language") ? "hold" : "pass", ethics: failed.has("ethics") ? "hold" : "pass", final_editor: failed.has("final_editor") ? "hold" : "pass", issues, notes: issues.map((x) => `${x.gate}: ${x.issue}`) };
}'''
new_final = '''async function finalReview(env, assignment, dossier, article) {
  const system = `Du er Morgentidendes uafhængige slutredaktør. Lav ét kort slutcheck af den færdige artikel mod de ALLEREDE verificerede claims; du må ikke genresearche og må ikke kræve flere kilder. Vælg samtidig den korrekte kategori blandt de tilladte kategorier. Forkert kategori er IKKE en blocker: returnér bare korrekt category. Returnér kun reelle blockers: (final_editor) materielle påstande ud over verified claims, vildledende/forkert attribution, rubrik/manchet stærkere end dokumentationen eller blanding af nyhed og kommentar; (ethics) konkret uløst fairness-/presseetisk risiko; (language) tydeligt fremmedsprogligt læk, brudt dansk eller uklar formulering som faktisk kræver reparation. Små stilpræferencer, SEO, metadata og media er aldrig blockers her. Media ejer billedsandhed og brugsret. Hvis artiklen er klar, returnér tom blocking_issues.`;
  const raw = await aiJson(env, system, JSON.stringify({ categories: CATEGORIES, assignment, claims: dossier.claims.filter((c) => c.status === "verified"), contradictions: dossier.contradictions, article }), finalSchema, 360, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
  if (CATEGORIES.includes(raw.category)) assignment.category = raw.category;
  const issues = Array.isArray(raw.blocking_issues) ? raw.blocking_issues.filter((x) => x?.gate && x?.issue) : [];
  const failed = new Set(issues.map((x) => x.gate));
  return { decision: issues.length ? "hold" : "pass", language: failed.has("language") ? "hold" : "pass", ethics: failed.has("ethics") ? "hold" : "pass", final_editor: failed.has("final_editor") ? "hold" : "pass", issues, notes: issues.map((x) => `${x.gate}: ${x.issue}`) };
}'''
once(old_final, new_final, 'finalReview')

# No unconditional language call. Every failed revision reuses the cheap short final review.
once('''  let article = await writeArticle(env, assignment, dossier);
  article = await polishArticleLanguage(env, assignment, dossier, article);

  const date = startedAt.slice(0, 10);''', '''  let article = await writeArticle(env, assignment, dossier);

  const date = startedAt.slice(0, 10);''', 'mandatory language call')
once('''  const aiFinalRequired = requiresAiFinalReview(assignment, dossier, article);
  let review = aiFinalRequired ? await finalReview(env, assignment, dossier, article) : deterministicFinalReview(assignment, dossier, article);''', '''  let review = await finalReview(env, assignment, dossier, article);''', 'first final review')
once('''    review = aiFinalRequired ? await finalReview(env, assignment, dossier, article) : deterministicFinalReview(assignment, dossier, article);''', '''    review = await finalReview(env, assignment, dossier, article);''', 'retry final review')

# Audit the normal cost path explicitly.
once('''    audit: { assignment, research: { rationale: research.rationale, candidate_claims: research.candidate_claims, contradictions: research.contradictions }, fact_check: { rationale: dossier.rationale, claims: dossier.claims, contradictions: dossier.contradictions }, article_attempts: articleAttempts, final_review: review,''', '''    audit: { assignment, research: { rationale: research.rationale, candidate_claims: research.candidate_claims, contradictions: research.contradictions }, fact_check: { rationale: dossier.rationale, claims: dossier.claims, contradictions: dossier.contradictions }, article_attempts: articleAttempts, language_mode: articleAttempts === 1 ? "write-once-no-repair" : "conditional-repair", final_review: review,''', 'audit language mode')

for retired in ('polishArticleLanguage', 'requiresAiFinalReview', 'deterministicFinalReview'):
    if retired in text:
        raise SystemExit(f'{retired} still present')
PATH.write_text(text, encoding='utf-8')
print('conditional language repair patch: PASS')
