#!/usr/bin/env python3
from pathlib import Path

p = Path('cloudflare/newsdesk/src/editorial.js')
s = p.read_text(encoding='utf-8')


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f'{label}: marker not found')
    s = s.replace(old, new, 1)


replace_once(
    'function isEvidenceSource(item) { return item && !item.discovery_only; }\n'
    'function authoritativePrimary(item) { return isEvidenceSource(item) && item.source_kind === "primary"; }\n'
    'function evidenceGroups(items) { return [...new Set(items.filter(isEvidenceSource).map((x) => sourceGroup(x.source, x.final_url || x.url)))]; }',
    '''const DISCOVERY_ONLY_HOSTS = new Set([
  "indblik.dk", "document.no", "timbro.se", "achgut.com", "tichyseinblick.de", "causeur.fr", "contrepoints.org",
  "spiked-online.com", "capx.co", "unherd.com", "reason.com", "nationalreview.com", "city-journal.org",
  "thefederalist.com", "frontpagemag.com", "jihadwatch.org",
]);
function hostOf(value) { try { return new URL(value).hostname.replace(/^www\\./, "").toLowerCase(); } catch (_) { return ""; } }
function isDiscoveryOnly(item) {
  if (!item) return false;
  if (item.discovery_only || /discovery/i.test(item.source_class || "") || item.source_role === "discovery") return true;
  return DISCOVERY_ONLY_HOSTS.has(hostOf(item.final_url || item.url || ""));
}
function isEvidenceSource(item) { return item && !isDiscoveryOnly(item); }
function authoritativePrimary(item) { return isEvidenceSource(item) && item.source_kind === "primary"; }
function evidenceGroups(items) { return [...new Set(items.filter(isEvidenceSource).map((x) => sourceGroup(x.source, x.final_url || x.url)))]; }''',
    'evidence helpers',
)

start = s.index('  if (!usable.some(authoritativePrimary) && evidenceGroups(usable).length < 2) {')
end_marker = '  research.source_payload = sources;'
end = s.index(end_marker, start) + len(end_marker)
s = s[:start] + '''  const evidenceUsable = usable.filter(isEvidenceSource);
  if (!evidenceUsable.some(authoritativePrimary) && evidenceGroups(evidenceUsable).length < 2) {
    return { decision: "watch", rationale: "Lovende discovery-tip, men endnu ikke en autoritativ primærkilde eller to uafhængige redaktionelle kilder", researched: evidenceUsable };
  }
  // Hard boundary: blogs/perspective/advocacy feeds are discovery leads only. They are removed
  // before Research creates claims and can never reach Fact checker, Journalist or source ledger.
  const sources = evidenceUsable.map((s, i) => ({
    source_index: i, name: s.source, headline: s.headline, url: s.final_url || s.url,
    excerpt: s.excerpt.slice(0, 10000), discovery_only: false, source_kind: s.source_kind || "news",
  }));
  const system = `Du er Research på Morgentidende. Kortlæg historien, men fæld ikke fact-check-slutdom. De vedlagte kilder er allerede filtreret, så discovery-blogs og perspektiv/advocacy-feeds ikke indgår. En autoritativ primærkilde kan bære et faktum; ellers kræves normalt to reelt uafhængige redaktionelle kilder. Find bærende faktapåstande, modpositioner, konsekvenser, uenigheder og usikkerhed. Peg på præcise source_indexes. Forelæggelse markeres ved alvorlige belastende påstande. Opfind ikke claims.`;
  const research = await aiJson(env, system, JSON.stringify({ assignment, sources }), researchSchema, 1800, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
  research.researched = evidenceUsable;
  research.source_payload = sources;''' + s[end:]

old_fact = '  const system = `Du er en UAFHÆNGIG Fact checker på Morgentidende. Forsøg aktivt at falsificere hvert kandidat-claim mod de vedlagte kildetekster. discovery_only-kilder kan pege på et emne eller perspektiv, men må aldrig alene verificere et claim. Verified kræver enten én autoritativ primærkilde eller mindst to reelt uafhængige ikke-discovery-kilder. Rejected når evidensen modsiger claimet; ellers uncertain. To solide verificerede bærende claims er nok til en kort artikel. Opfind ingen nye kilder eller fakta.`;'
new_fact = '  if ((research.researched || []).some(isDiscoveryOnly)) throw new Error("Discovery-only source crossed the Research/Fact-check boundary");\n  const system = `Du er en UAFHÆNGIG Fact checker på Morgentidende. Forsøg aktivt at falsificere hvert kandidat-claim mod de vedlagte kildetekster. Discovery-blogs og perspektiv/advocacy-feeds er fjernet før dette trin og må aldrig bruges som kilder. Verified kræver enten én autoritativ primærkilde eller mindst to reelt uafhængige redaktionelle kilder. Rejected når evidensen modsiger claimet; ellers uncertain. To solide verificerede bærende claims er nok til en kort artikel. Opfind ingen nye kilder eller fakta.`;'
replace_once(old_fact, new_fact, 'fact-check boundary')

replace_once(
    'async function writeArticle(env, assignment, dossier) {\n  const sources = dossier.researched.map',
    'async function writeArticle(env, assignment, dossier) {\n  if ((dossier.researched || []).some(isDiscoveryOnly)) throw new Error("Discovery-only source crossed the Journalist boundary");\n  const sources = dossier.researched.filter(isEvidenceSource).map',
    'journalist boundary',
)

replace_once(
    'function makeLedger(storyId, slug, assignment, dossier, desk, accessedAt) {\n  const sources = dossier.researched.map',
    'function makeLedger(storyId, slug, assignment, dossier, desk, accessedAt) {\n  if ((dossier.researched || []).some(isDiscoveryOnly)) throw new Error("Discovery-only source crossed the publication ledger boundary");\n  const sources = dossier.researched.filter(isEvidenceSource).map',
    'ledger boundary',
)

p.write_text(s, encoding='utf-8')
print('Discovery-only source policy applied')
