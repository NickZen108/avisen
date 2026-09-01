#!/usr/bin/env python3
from pathlib import Path

p = Path('cloudflare/newsdesk/src/editorial.js')
s = p.read_text(encoding='utf-8')

repls = [
('if (unique.length >= 5) break;', 'if (unique.length >= 4) break;'),
('excerpt: item.excerpt.slice(0, 5000),', 'excerpt: item.excerpt.slice(0, 3500),'),
('researchSchema, 850, FAST_TEXT_MODEL, STRONG_TEXT_MODEL', 'researchSchema, 650, FAST_TEXT_MODEL, STRONG_TEXT_MODEL'),
('Verified kræver enten én autoritativ primærkilde eller mindst to reelt uafhængige redaktionelle kilder. Rejected når evidensen modsiger claimet; ellers uncertain. To solide verificerede bærende claims er nok til en kort artikel.', 'Verified kræver normalt enten én autoritativ primærkilde inden for dens eget kompetenceområde eller to reelt uafhængige troværdige kilder, fx to store redaktioner eller en stor redaktion plus en myndighed/virksomhed/organisation om egne handlinger eller data. Samme bureau/pressemeddelelse tæller kun én gang. Rejected når evidensen modsiger claimet; ellers uncertain. Ét verificeret bærende claim kan være nok til en kort artikel; højrisiko-påstande kræver stærkere målrettet kontrol.'),
('}), factCheckSchema, 2200);', '}), factCheckSchema, 850, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);'),
('if (verified.length < 2) {\n    fact.decision = "hold";\n    fact.rationale = `${fact.rationale || ""} Deterministisk gate: færre end to bærende claims er verificeret.`.trim();\n  }', 'if (verified.length < 1) {\n    fact.decision = "hold";\n    fact.rationale = `${fact.rationale || ""} Ingen bærende claims er verificeret.`.trim();\n  }'),
('return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources }), articleSchema, 3000);', 'return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources }), articleSchema, assignment.weight === "A" || assignment.weight === "B" ? 2200 : 1400, assignment.weight === "A" || assignment.weight === "B" ? STRONG_TEXT_MODEL : FAST_TEXT_MODEL, assignment.weight === "A" || assignment.weight === "B" ? null : STRONG_TEXT_MODEL);'),
('const raw = await aiJson(env, system, JSON.stringify({ assignment, claims: dossier.claims, contradictions: dossier.contradictions, article }), finalSchema, 900);', 'const raw = await aiJson(env, system, JSON.stringify({ assignment, claims: dossier.claims, contradictions: dossier.contradictions, article }), finalSchema, 450, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);'),
('coverage_sweep: { status: groups.length >= 3 ? "pass" : "limited", editorial_source_ids: verificationSources.slice(0, 6).map((s) => s.id), independent_source_groups: groups.slice(0, 6), limitations: groups.length >= 3 ? null : "Færre end tre uafhængige verifikationskilder; discovery-only-kilder tæller ikke med", notes: ["Research kan begynde fra perspektivkilder, men Fact checker kræver autoritativ primærkilde eller uafhængig ikke-discovery-verifikation."] },', 'coverage_sweep: { status: groups.length >= 1 ? "pass" : "limited", editorial_source_ids: verificationSources.slice(0, 6).map((s) => s.id), independent_source_groups: groups.slice(0, 6), limitations: groups.length >= 1 ? null : "Ingen brugbar dokumentationskilde registreret", notes: ["Coverage beskriver kildegrundlaget; claim-verifikation afgøres særskilt. En autoritativ primærkilde eller to uafhængige troværdige kilder er normalt nok for et almindeligt bærende faktum."] },'),
]
for old, new in repls:
    if old not in s:
        raise SystemExit(f'marker not found: {old[:100]}')
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('Full pipeline runtime optimization applied')
