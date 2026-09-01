#!/usr/bin/env python3
from pathlib import Path

p = Path('cloudflare/newsdesk/src/editorial.js')
s = p.read_text(encoding='utf-8')

def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f'{label}: marker not found')
    s = s.replace(old, new, 1)

rep('if (chosen.length >= 5) break;', 'if (chosen.length >= 4) break;', 'discovery reserve')
rep('if (chosen.length >= 28) break;', 'if (chosen.length >= 20) break;', 'shortlist cap')
rep('if (used >= 4) continue;', 'if (used >= 3) continue;', 'per-source cap')
rep('description: (s.description || "").slice(0, 220),', 'description: (s.description || "").slice(0, 160),', 'description cap')

old_prompt = 'const system = `Du er første Nyhedsdesk på Morgentidende. Vælg ét research-frø, ikke en færdig artikel. RESEARCH når emnet har reel nyhedsværdi og bør undersøges; WATCH når et potentielt vigtigt tip endnu er for tyndt; DROP kun ved klar dublet, gammel/triviel sag eller åbenlys utroværdighed. discovery_only/perspective-kilder er værdifulde tips, men må aldrig i sig selv tælle som verifikation eller få dig til at antage konklusionen. Kategori og A-D-vægt er dit ansvar, ikke Scan. Returnér kort struktureret output.`;\n  return aiJson(env, system, JSON.stringify({ generated_at: scan.generated_at, signals }), assignmentSchema, 550, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);'
new_prompt = 'const system = `Du er Morgentidendes første Nyhedsdesk. Vælg ét konkret research-frø. RESEARCH er standard ved reel nyhedsværdi, originalitet, offentlig betydning eller tydelig redaktionel relevans; tynd dokumentation er Researchs problem, ikke en afvisningsgrund. WATCH kun hvis nyhedskrogen/aktualiteten endnu er uklar. DROP kun ved klar dublet, gammel/triviel sag, rent holdningsstof uden nyhedskrog eller åbenlys spam. discovery_only må udløse Research, men er aldrig dokumentation. Sæt kategori og A-D-vægt. Svar ultrakort.`;\n  return aiJson(env, system, JSON.stringify({ generated_at: scan.generated_at, signals }), assignmentSchema, 260, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);'
rep(old_prompt, new_prompt, 'assignment prompt')

old_recheck = 'const system = `Du er Newsdesk ved et kort recheck EFTER uafhængig Fact checker. Du må ikke genresearche eller gentage fact check. Vurder kun om den dokumenterede historie stadig er aktuel og væsentlig nok, og om kernen stadig svarer til assignment. Hold/kill kræver en konkret redaktionel grund.`;\n  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), contradictions: dossier.contradictions, rationale: dossier.rationale }), deskRecheckSchema, 450, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);'
new_recheck = 'const system = `Du er Nyhedsdesk ved et ultrakort recheck efter bestået Fact check. Genresearch ikke. Udgangspunktet er publish/update. Hold/kill kun ved en ny konkret redaktionel grund: historien er ikke længere aktuel/væsentlig eller dokumentationen ændrer selve nyhedskernen. Svar kort.`;\n  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), contradictions: dossier.contradictions }), deskRecheckSchema, 180, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);'
rep(old_recheck, new_recheck, 'recheck prompt')

p.write_text(s, encoding='utf-8')
print('Newsdesk runtime refactor applied')
