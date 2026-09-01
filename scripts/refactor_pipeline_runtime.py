#!/usr/bin/env python3
from pathlib import Path

def replace_once(text, old, new, label):
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise SystemExit(f'marker not found for {label}: {old[:100]}')

# Runtime AI/token/source rules.
p = Path('cloudflare/newsdesk/src/editorial.js')
s = p.read_text(encoding='utf-8')
repls = [
('if (unique.length >= 5) break;', 'if (unique.length >= 4) break;', 'research source cap'),
('excerpt: item.excerpt.slice(0, 5000),', 'excerpt: item.excerpt.slice(0, 3500),', 'research excerpt cap'),
('researchSchema, 850, FAST_TEXT_MODEL, STRONG_TEXT_MODEL', 'researchSchema, 650, FAST_TEXT_MODEL, STRONG_TEXT_MODEL', 'research output cap'),
('Verified kræver enten én autoritativ primærkilde eller mindst to reelt uafhængige redaktionelle kilder. Rejected når evidensen modsiger claimet; ellers uncertain. To solide verificerede bærende claims er nok til en kort artikel.', 'Verified kræver normalt enten én autoritativ primærkilde inden for dens eget kompetenceområde eller to reelt uafhængige troværdige kilder, fx to store redaktioner eller en stor redaktion plus en myndighed/virksomhed/organisation om egne handlinger eller data. Samme bureau/pressemeddelelse tæller kun én gang. Rejected når evidensen modsiger claimet; ellers uncertain. Ét verificeret bærende claim kan være nok til en kort artikel; højrisiko-påstande kræver stærkere målrettet kontrol.', 'fact policy'),
('}), factCheckSchema, 2200);', '}), factCheckSchema, 850, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);', 'fact cost'),
('if (verified.length < 2) {\n    fact.decision = "hold";\n    fact.rationale = `${fact.rationale || ""} Deterministisk gate: færre end to bærende claims er verificeret.`.trim();\n  }', 'if (verified.length < 1) {\n    fact.decision = "hold";\n    fact.rationale = `${fact.rationale || ""} Ingen bærende claims er verificeret.`.trim();\n  }', 'single claim'),
('return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources }), articleSchema, 3000);', 'return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources }), articleSchema, assignment.weight === "A" || assignment.weight === "B" ? 2200 : 1400, assignment.weight === "A" || assignment.weight === "B" ? STRONG_TEXT_MODEL : FAST_TEXT_MODEL, assignment.weight === "A" || assignment.weight === "B" ? null : STRONG_TEXT_MODEL);', 'journalist model'),
('const raw = await aiJson(env, system, JSON.stringify({ assignment, claims: dossier.claims, contradictions: dossier.contradictions, article }), finalSchema, 900);', 'const raw = await aiJson(env, system, JSON.stringify({ assignment, claims: dossier.claims, contradictions: dossier.contradictions, article }), finalSchema, 450, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);', 'final review cost'),
('coverage_sweep: { status: groups.length >= 3 ? "pass" : "limited", editorial_source_ids: verificationSources.slice(0, 6).map((s) => s.id), independent_source_groups: groups.slice(0, 6), limitations: groups.length >= 3 ? null : "Færre end tre uafhængige verifikationskilder; discovery-only-kilder tæller ikke med", notes: ["Research kan begynde fra perspektivkilder, men Fact checker kræver autoritativ primærkilde eller uafhængig ikke-discovery-verifikation."] },', 'coverage_sweep: { status: groups.length >= 1 ? "pass" : "limited", editorial_source_ids: verificationSources.slice(0, 6).map((s) => s.id), independent_source_groups: groups.slice(0, 6), limitations: groups.length >= 1 ? null : "Ingen brugbar dokumentationskilde registreret", notes: ["Coverage beskriver kildegrundlaget; claim-verifikation afgøres særskilt. En autoritativ primærkilde eller to uafhængige troværdige kilder er normalt nok for et almindeligt bærende faktum."] },', 'coverage rule'),
]
for old,new,label in repls:
    s=replace_once(s,old,new,label)
p.write_text(s,encoding='utf-8')

# GitHub importer must not reintroduce the old 3-source / 2-claim gates.
p = Path('scripts/sync_cloudflare_editorial.py')
s = p.read_text(encoding='utf-8')
s = replace_once(s, 'coverage["status"] = "pass" if len(groups) >= 3 else "limited"', 'coverage["status"] = "pass" if len(groups) >= 1 else "limited"', 'import coverage pass')
s = replace_once(s, 'coverage["limitations"] = None if len(groups) >= 3 else "Færre end tre uafhængige kildegrupper efter import; bærende claims skal stadig være dokumenteret"', 'coverage["limitations"] = None if len(groups) >= 1 else "Ingen reel dokumentationskilde efter import"', 'import coverage note')
s = replace_once(s, 'if len(claims) < 2:\n        fail("for få verificerede bærende claims")', 'if len(claims) < 1:\n        fail("ingen verificerede bærende claims")', 'import single claim')
p.write_text(s,encoding='utf-8')

# Readability heuristics are useful diagnostics, but should not kill an otherwise verified story.
p = Path('scripts/readability_gate.py')
s = p.read_text(encoding='utf-8')
s = replace_once(s, '        raise SystemExit(1)\n    print(f"Readability gate: PASS ({checked} pipeline-v2 artikler)")', '        print("Readability gate: WARN only; redaktionel betydning afgøres af Journalist/Slutredaktør")\n        return\n    print(f"Readability gate: PASS ({checked} pipeline-v2 artikler)")', 'readability soft gate')
p.write_text(s,encoding='utf-8')

print('Full pipeline runtime/import/gate optimization applied')
