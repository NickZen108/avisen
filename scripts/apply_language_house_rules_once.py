from pathlib import Path

# Restore and strengthen the reader-explanation house rule.
house = Path('HUSREGLER.md')
s = house.read_text()
anchor = '## Lægmandssprog, fremmedord og måleenheder\n\n'
insert = (
    '## Lægmandssprog, fremmedord og måleenheder\n\n'
    '**Egennavne skal forklares første gang de optræder**, så en almindelig dansk læser straks ved, hvad personen, organisationen, virksomheden, institutionen, turneringen, ligaen, programmet, myndigheden, stedet eller begivenheden er i den konkrete sammenhæng. Brug en kort naturlig apposition eller forklaring, fx `Diamond League, den internationale serie af topstævner i atletik, ...`, `OpenAI, det amerikanske AI-selskab, ...` eller `Gideon Sa\'ar, Israels udenrigsminister, ...`. Forklaringen skal være kort og relevant; den må ikke blive til leksikonfyld.\n\n'
)
if '**Egennavne skal forklares første gang de optræder**' not in s:
    if anchor not in s:
        raise SystemExit('HUSREGLER anchor missing')
    s = s.replace(anchor, insert, 1)
house.write_text(s)

# Make the same rule explicit in STYLE and guard against Nordic-source leakage.
style = Path('STYLE.md')
s = style.read_text()
old = '- Forklar nødvendige fagord første gang. Brug almindeligt dansk frem for unødvendige engelske brancheord.\n'
new = (
    '- Forklar nødvendige fagord første gang. Brug almindeligt dansk frem for unødvendige engelske brancheord.\n'
    '- Forklar alle egennavne kort første gang: personer med relevant rolle, organisationer/virksomheder med hvad de er, turneringer/ligaer/programmer med hvad de dækker, og mindre kendte steder med nødvendig geografisk kontekst.\n'
    '- Skriv idiomatisk dansk også når kilden er norsk eller svensk. Norske bokmåls-/nynorskformer og svenske ord eller bøjninger må ikke glide med over i den danske tekst. Oversæt meningen til naturligt dansk.\n'
)
if 'Norske bokmåls-/nynorskformer' not in s:
    if old not in s:
        raise SystemExit('STYLE anchor missing')
    s = s.replace(old, new, 1)
style.write_text(s)

# Bind the house rules into the active journalist prompt without adding a new gate.
js = Path('cloudflare/newsdesk/src/editorial.js')
s = js.read_text()
old1 = 'Skriv præcist og levende dansk, men brug KUN verificerede claims.'
new1 = ('Skriv præcist, levende og idiomatisk dansk, men brug KUN verificerede claims. '
        'Når kilden er norsk eller svensk, skal du oversætte fuldt til naturligt dansk; bokmåls-, nynorsk- og svenske ord eller bøjningsformer må ikke glide med over i teksten.')
if old1 in s and 'bokmåls-, nynorsk-' not in s:
    s = s.replace(old1, new1, 1)
old2 = 'Skriv til almindelige læsere: erstat fagord og engelske brancheord med almindeligt dansk, forklar nødvendige tekniske begreber første gang med 1-2 korte sætninger, og omsæt uvante mål til fx kilometer, meter, Celsius og kilogram.'
new2 = ('Skriv til almindelige læsere: erstat fagord og engelske brancheord med almindeligt dansk, forklar nødvendige tekniske begreber første gang med 1-2 korte sætninger, og omsæt uvante mål til fx kilometer, meter, Celsius og kilogram. '
        'Forklar desuden alle egennavne kort første gang de optræder: angiv personers relevante rolle, hvad organisationer/virksomheder/institutioner er, hvad turneringer/ligaer/programmer dækker, og nødvendig geografisk kontekst for mindre kendte steder. Forklar naturligt og kort, uden leksikonfyld.')
if old2 in s and 'Forklar desuden alle egennavne kort første gang' not in s:
    s = s.replace(old2, new2, 1)
js.write_text(s)

# Print any existing Diamond League article(s) for targeted follow-up.
for p in sorted(Path('content/articles').glob('*.json')):
    text = p.read_text(errors='ignore')
    if 'Diamond League' in text:
        print(f'DIAMOND_ARTICLE={p}')
        print(text[:12000])

print('language house rules applied')
