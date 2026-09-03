#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

# 1) Remove unused parallel agent prompt files only when no file outside agents/ references them.
agents = ROOT / "agents"
removed_agents = []
if agents.exists():
    outside_text = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git" in p.parts or "agents" in p.parts:
            continue
        try:
            outside_text.append((p, p.read_text(encoding="utf-8")))
        except Exception:
            pass
    for p in sorted(agents.glob("*.md")):
        basename = p.name
        rel = f"agents/{basename}"
        referenced = any(rel in text or basename in text for _, text in outside_text)
        if not referenced:
            p.unlink()
            removed_agents.append(rel)
    if agents.exists() and not any(agents.iterdir()):
        agents.rmdir()

# 2) Make publication-attempt logging operational rather than duplicating editorial/source payloads.
log = ROOT / "scripts" / "log_publication_attempt.py"
text = log.read_text(encoding="utf-8")
old = "row={'at':payload.get('generated_at') or datetime.now(timezone.utc).isoformat(timespec='seconds'),'status':status,'stage':stage,'slug':payload.get('slug') or article.get('slug'),'title':article.get('title') or payload.get('title') or audit.get('article_title') or assignment.get('title_hint') or payload.get('slug') or 'Ikke navngivet kandidat','reason':reason or ('Godkendt' if status=='approved' else 'Ingen begrundelse registreret'),'assessment':verdict,'assessment_text':why,'pipeline_action':adjust,'reason_code':reason_code(status,stage,reason),'ai_usage':payload.get('ai_usage'),'diagnostics':{'assignment':assignment,'candidate_claims':research.get('candidate_claims') or [],'researched':research.get('researched') or [],'fact_claims':fact.get('claims') or [],'sources':audit.get('sources') or [],'selected_signals':audit.get('selected_signals') or []}}"
new = "row={'at':payload.get('generated_at') or datetime.now(timezone.utc).isoformat(timespec='seconds'),'status':status,'stage':stage,'slug':payload.get('slug') or article.get('slug'),'title':article.get('title') or payload.get('title') or audit.get('article_title') or assignment.get('title_hint') or payload.get('slug') or 'Ikke navngivet kandidat','reason':reason or ('Godkendt' if status=='approved' else 'Ingen begrundelse registreret'),'assessment':verdict,'reason_code':reason_code(status,stage,reason),'ai_usage':payload.get('ai_usage'),'diagnostics':{'category':assignment.get('category'),'weight':assignment.get('weight'),'article_attempts':audit.get('article_attempts'),'retry_routing':audit.get('retry_routing') or [],'source_count':audit.get('source_count') or len(audit.get('sources') or []),'verified_claim_count':len([c for c in (fact.get('claims') or []) if c.get('status')=='verified'])}}"
if old not in text:
    raise SystemExit("publication attempt row shape changed; refusing blind patch")
log.write_text(text.replace(old, new, 1), encoding="utf-8")

# 3) Compress the two largest runtime prompts without changing ownership or policy.
editorial = ROOT / "cloudflare" / "newsdesk" / "src" / "editorial.js"
body = editorial.read_text(encoding="utf-8")

fact_start = '  const system = `Du er en UAFHÆNGIG Fact checker på Morgentidende.'
fact_end = '`;\n  const fact = await aiJson(env, system,'
si = body.find(fact_start)
ei = body.find(fact_end, si)
if si < 0 or ei < 0:
    raise SystemExit("fact-check prompt anchor missing")
short_fact = '''  const system = `Du er Morgentidendes uafhængige Fact checker. Kontrollér hvert kandidat-claim mod de vedlagte kildetekster og forsøg aktivt at falsificere det. Brug kun source_indexes, der faktisk dokumenterer claimet. Ét claim kan verificeres af én relevant autoritativ kilde: stort etableret medie/bureau, myndighed/officiel kilde, virksomhed/person om egne forhold, relevant ekspert eller original forskning. Kræv ikke mekanisk kilde nr. 2. Discovery-only-kilder må aldrig verificere claims. Sammenlign materielle tal mod alle relevante kilder; mismatch => uncertain eller forsigtig attribution. Oversættelse/parafrase skal bevare den materielle betydning. Rejected hvis evidensen modsiger claimet, ellers uncertain. Ét verificeret bærende claim er nok; udelad usikre detaljer. Opfind intet.`;\n  const fact = await aiJson(env, system,'''
body = body[:si] + short_fact + body[ei + len(fact_end):]

write_start = '  const system = `Du er journalist på Morgentidende. ${destinationBrief}'
write_end = '`;\n  return aiJson(env, system,'
si = body.find(write_start)
ei = body.find(write_end, si)
if si < 0 or ei < 0:
    raise SystemExit("journalist prompt anchor missing")
short_write = '''  const system = `Du er journalist på Morgentidende. ${destinationBrief} Brug KUN verified claims. Skriv præcist, levende og idiomatisk dansk; oversæt norsk/svensk/engelsk fuldt, bortset fra egennavne og officielle produktnavne. Rubrik, manchet og brødtekst må aldrig være stærkere end dokumentationen. Gør attribution konkret (fx “ifølge BBC”), men lav ikke afsnit om hvilke medier der dækkede sagen. Opfind aldrig citater eller fakta. Brug kun reel pluralisme når conflict_present=true og kun fra verificeret materiale. Forklar nødvendige fagord, roller og mindre kendte steder kort. En one-claim-nyhed må være én kort tekstblok: gentag aldrig samme claim og tilføj ikke generelle perspektiver, konsekvenser eller fremtidsforudsigelser uden verified claim. Standfirst er 1-2 korte sætninger, højst 35 ord, aldrig kun et kildenavn. Media ejer heroen.`;\n  return aiJson(env, system,'''
body = body[:si] + short_write + body[ei + len(write_end):]
editorial.write_text(body, encoding="utf-8")

print(f"Removed unused agent files: {len(removed_agents)}")
for p in removed_agents:
    print(p)
print("engine cleanup patch: PASS")
