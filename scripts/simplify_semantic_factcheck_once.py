from pathlib import Path

p = Path('cloudflare/newsdesk/src/editorial.js')
s = p.read_text()

old1 = "Kontrollér også semantisk oversættelse/parafrase mod originalteksten: subjekt, objekt, negation, modalitet, årsag, tid og tal skal betyde det samme. Hvis fx kilden siger at indsatsen/response skal intensiveres, må claimet ikke sige at selve udbruddet/hændelsen skal intensiveres. En sådan betydningsændring er rejected eller uncertain, ikke verified."
new1 = "Kontrollér også, at oversættelse og parafrase samlet bevarer originalkildens betydning. Vurder meningen i hele udsagnet frem for at anvende mekaniske grammatiske delregler. Hvis den danske gengivelse ændrer den materielle betydning, er claimet rejected eller uncertain, ikke verified."

old2 = "Du er den samme uafhængige Fact checker i et sidste semantisk pass. Sammenlign HELE den færdige danske artikel med de eksisterende originalkilder. Dette er ikke en ny kildegate og du må IKKE kræve flere kilder. Kontrollér kun sandhed og betydningsbevarelse: alle materielle udsagn skal kunne rummes i det verificerede materiale, og oversættelse/parafrase skal bevare hvem der gør hvad mod hvem/hvad, subjekt, objekt, negation, modalitet, årsag, tid, attribution og tal. Fri og naturlig dansk formulering er tilladt; ord-for-ord-oversættelse er ikke et krav. HOLD kun ved reel materiel betydningsændring, oversættelsesfejl, unsupported claim eller forkert attribution. Stil, tone, SEO og små sproglige præferencer er aldrig fejl her. Eksempel på materiel fejl: 'response/indsatsen skal intensiveres' må ikke blive til 'udbruddet skal intensiveres'."
new2 = "Du er den samme uafhængige Fact checker i et sidste semantisk pass. Sammenlign HELE den færdige danske artikel med de eksisterende originalkilder og vurder samlet, om betydningen er bevaret korrekt hele vejen igennem. Dette er ikke en ny kildegate og du må IKKE kræve flere kilder. Se på helheden og meningen i hver passage frem for at anvende en tjekliste af grammatiske delregler. Fri og naturlig dansk formulering er tilladt; ord-for-ord-oversættelse er ikke et krav. HOLD kun ved reel materiel betydningsændring, oversættelsesfejl, unsupported claim eller forkert attribution. Stil, tone, SEO og små sproglige præferencer er aldrig fejl her. Hvis du finder en fejl, angiv den konkrete danske passage og hvad originalkilden faktisk betyder."

old3 = "Ret oversættelser så subjekt, objekt, negation, modalitet, årsag, tid, attribution og tal svarer til originalkilden."
new3 = "Ret oversættelser og parafraser, så den samlede betydning svarer til originalkilden."

for old, new in [(old1,new1),(old2,new2),(old3,new3)]:
    if old not in s:
        raise SystemExit(f'Expected text not found: {old[:80]}')
    s = s.replace(old, new, 1)

p.write_text(s)
print('semantic fact-check prompts simplified')
