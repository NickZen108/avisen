#!/usr/bin/env python3
"""One-time/idempotent migration of Cloudflare editorial runtime to the house rule:
one relevant authoritative source is sufficient to verify a claim.
"""
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "cloudflare/newsdesk/src/editorial.js"
s = P.read_text(encoding="utf-8")

replacements = [
(
'''const STRONG_EDITORIAL_HOSTS = [
  "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "dr.dk", "tv2.dk", "svt.se", "nrk.no",
  "ft.com", "politico.eu", "bloomberg.com", "theguardian.com", "nytimes.com", "wsj.com",
  "france24.com", "tagesschau.de", "rbb24.de", "itv.com",
];''',
'''const STRONG_EDITORIAL_HOSTS = [
  "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "dr.dk", "tv2.dk", "svt.se", "nrk.no",
  "ft.com", "politico.eu", "bloomberg.com", "theguardian.com", "nytimes.com", "wsj.com",
  "france24.com", "dw.com", "euronews.com", "aljazeera.com", "sky.com", "skynews.com",
  "cnn.com", "nbcnews.com", "cbsnews.com", "abcnews.go.com", "foxnews.com", "spiegel.de", "lemonde.fr",
  "tagesschau.de", "rbb24.de", "itv.com",
];'''),
(
'''function normalizedSourceKind(item) {
  if (authoritativePrimary(item)) return "primary";
  const kind = trustedExpansionKind(item?.final_url || item?.url || "");''',
'''function normalizedSourceKind(item) {
  const explicit = String(item?.source_kind || item?.source_class || "").toLowerCase().trim();
  if (["paper", "research_paper", "researcher", "scientist", "expert", "company_statement", "organization_statement", "person_statement", "first_party_statement", "interview", "official_statement"].includes(explicit)) return explicit;
  if (authoritativePrimary(item)) return "primary";
  const kind = trustedExpansionKind(item?.final_url || item?.url || "");'''),
(
'''function evidenceGroups(items) { return [...new Set(items.filter(isEvidenceSource).map(evidenceSourceGroup))]; }

const HIGH_RISK_FACT_TERMS''',
'''function evidenceGroups(items) { return [...new Set(items.filter(isEvidenceSource).map(evidenceSourceGroup))]; }
function authoritativeClaimSource(item) {
  if (!isEvidenceSource(item)) return false;
  if (authoritativePrimary(item) || authoritativeEditorial(item) || strongEditorialSource(item)) return true;
  const kind = normalizedSourceKind(item);
  return ["paper", "research_paper", "researcher", "scientist", "expert", "company_statement", "organization_statement", "person_statement", "first_party_statement", "interview", "official_statement"].includes(kind);
}

const HIGH_RISK_FACT_TERMS'''),
(
'''function evidenceRulePass(assignment, research, claim, evidence) {
  const primaryOk = evidence.some(authoritativePrimary);
  if (namedAccusedCrimeClaim(assignment, claim)) return primaryOk;
  const wireOk = evidence.some(authoritativeEditorial);
  const atoms = new Set(evidence.map(evidenceAtom).filter(Boolean));
  if (highRiskFactClaim(assignment, research, claim)) return primaryOk || atoms.size >= 2;
  return primaryOk || wireOk || atoms.size >= 2;
}''',
'''function evidenceRulePass(assignment, research, claim, evidence) {
  // House rule: one relevant authoritative source is sufficient for a claim.
  // Risk/fairness may still trigger Ethics or final review, but does not impose a hidden two-source quota.
  return evidence.some(authoritativeClaimSource);
}'''),
(
'''if (!evidenceUsable.some(authoritativePrimary) || evidenceGroups(evidenceUsable).length < 2) {''',
'''if (!evidenceUsable.some(authoritativeClaimSource)) {'''),
(
'''For almindelige lavrisiko-fakta kan Verified bæres af én autoritativ primærkilde inden for dens kompetenceområde, én dokumenteret original bureaukilde (Reuters/AP/AFP/Ritzau), eller to provenance-uafhængige troværdige evidenskilder. Ét almindeligt redaktionelt medie kan ikke stå alene. Ved højrisiko kræves primærkilde eller mindst to provenance-uafhængige evidenskilder. Samme bureau/pressemeddelelse tæller kun én gang. Ved højrisiko/fairness-påstande skal du være mere forsigtig og ikke lade én almindelig redaktionel kilde stå alene. Ved navngivne sigtede/tiltalte/mistænkte i kriminalstof kræves en relevant primærkilde fra politi/ret/myndighed.''',
'''Et claim kan få Verified på baggrund af én relevant autoritativ kilde, når en kort ordret støttepassage faktisk dokumenterer claimet. Autoritative kilder er: (1) store etablerede redaktionelle medier, (2) myndigheder/officielle kilder, (3) virksomheder, organisationer eller personer om egne forhold, (4) relevante forskere/fageksperter inden for deres fagområde og (5) forskningspapirer/original forskning. Originale bureaukilder som Reuters/AP/AFP/Ritzau er også autoritative. Kræv ikke automatisk kilde nr. 2 blot fordi kilden er et medie. Ved høj risiko, alvorlige beskyldninger eller fairness kan ekstra kontrol, attribution, forelæggelse eller Etik-review være nødvendig, men høj risiko skaber ikke i sig selv en mekanisk to-kilde-regel.'''),
(
'''authoritative_for: primary ? (s.headline || "Primary record") : (s.headline || "Independent coverage"), discovery_only:''',
'''authoritative_for: primary ? (s.headline || "Primary record") : (s.headline || "Independent coverage"), authority_class: normalizedSourceKind(s), discovery_only:'''),
(
'''Coverage beskriver kildegrundlaget; claim-verifikation afgøres særskilt. Lavrisiko kræver autoritativ primærkilde, dokumenteret original bureaukilde eller to provenance-uafhængige evidenskilder. Højrisiko kræver primærkilde eller to provenance-uafhængige evidenskilder.''',
'''Coverage beskriver kildegrundlaget; claim-verifikation afgøres særskilt. Ét claim kan verificeres af én relevant autoritativ kilde: stort redaktionelt medie, myndighed/officiel kilde, virksomhed/person om egne forhold, relevant forsker/fagekspert eller forskningspaper/original forskning. Flere kilder er til pluralisme, mod-evidens og ekstra sikkerhed — ikke en mekanisk kvote.'''),
]

changed = False
for old, new in replacements:
    if new in s:
        continue
    if old not in s:
        raise SystemExit(f"Expected editorial.js policy fragment not found:\n{old[:180]}")
    s = s.replace(old, new, 1)
    changed = True

if changed:
    P.write_text(s, encoding="utf-8")
    print("authoritative source policy: editorial.js updated")
else:
    print("authoritative source policy: already current")
