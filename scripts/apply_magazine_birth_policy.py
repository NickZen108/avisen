#!/usr/bin/env python3
"""One-shot source migration: make magazine destination part of Newsdesk birth.

Idempotent. Fails loudly if the expected canonical anchors have drifted.
Triggered once after the workflow was installed.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "cloudflare" / "newsdesk" / "src" / "editorial.js"
text = PATH.read_text(encoding="utf-8")

if "function editorialDestination(assignment, scan)" in text:
    print("magazine birth policy already applied")
    raise SystemExit(0)

anchor = '''function topicBoost(signal) {
  const hay = `${signal.headline || ""} ${signal.description || ""}`.toLocaleLowerCase("da-DK");
  const lens = EDITORIAL_LENS.some((x) => hay.includes(x)) ? 4 : 0;
  const general = GENERAL_IMPORTANCE.some((x) => hay.includes(x)) ? 4 : 0;
  return Math.max(lens, general);
}
'''
insert = anchor + '''const TECH_MAGAZINE_TERMS = ["videnskab", "forskning", "naturvidenskab", "teknologi", "kunstig intelligens", " ai ", "rumfart", "rumteleskop", "astronomi", "fysik", "biologi", "robot", "chip", "halvleder", "militærteknologi", "militaerteknologi", "forsvarsteknologi", "drone", "energi"];
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
'''
if anchor not in text:
    raise SystemExit("anchor topicBoost not found")
text = text.replace(anchor, insert, 1)

old = '''  const assignment = await chooseAssignment(env, scan, options.excludedSignalKeys || []);
  const check = validateAssignment(assignment, scan);'''
new = '''  const assignment = await chooseAssignment(env, scan, options.excludedSignalKeys || []);
  assignment.editorial_destination = editorialDestination(assignment, scan);
  const check = validateAssignment(assignment, scan);'''
if old not in text:
    raise SystemExit("assignment anchor not found")
text = text.replace(old, new, 1)

old = '''  const sources = dossier.researched.filter(isEvidenceSource).map((s, i) => ({ source_index: i, name: s.source, headline: s.headline, url: s.final_url || s.url }));
  const system = `Du er journalist på Morgentidende. Skriv præcist og levende dansk, men brug KUN verificerede claims.'''
new = '''  const sources = dossier.researched.filter(isEvidenceSource).map((s, i) => ({ source_index: i, name: s.source, headline: s.headline, url: s.final_url || s.url }));
  const destinationBrief = magazineWritingBrief(assignment?.editorial_destination || "main");
  const system = `Du er journalist på Morgentidende. ${destinationBrief} Skriv præcist og levende dansk, men brug KUN verificerede claims.'''
if old not in text:
    raise SystemExit("journalist anchor not found")
text = text.replace(old, new, 1)

old = '''    assignment: { category: assignment.category, weight: assignment.weight, core_question: dossier.core_question || assignment.core_question, manual_review: false },'''
new = '''    assignment: { category: assignment.category, weight: assignment.weight, editorial_destination: assignment.editorial_destination || "main", core_question: dossier.core_question || assignment.core_question, manual_review: false },'''
if old not in text:
    raise SystemExit("ledger assignment anchor not found")
text = text.replace(old, new, 1)

old = '''    category: assignment.category, weight: assignment.weight, title: article.title, standfirst: article.standfirst,'''
new = '''    category: assignment.category, weight: assignment.weight, editorial_destination: assignment.editorial_destination || "main", title: article.title, standfirst: article.standfirst,'''
if old not in text:
    raise SystemExit("canonical anchor not found")
text = text.replace(old, new, 1)

PATH.write_text(text, encoding="utf-8")
print("magazine birth policy applied to editorial.js")
