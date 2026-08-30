# Redaktionel linje — Morgentidende

Navn på alle flader: **Morgentidende**.

Morgentidende er en seriøs, uafhængig dansk netavis. Nyhedsstof udvælges efter dokumenteret nyhedsværdi og offentlig interesse — ikke efter om historien passer til en politisk eller kulturel linje. Holdning hører kun hjemme i tydeligt mærkede kommentarer.

## Grundprincipper

1. **Sandhed før hastighed.** Hellere senere end forkert.
2. **Nyhed før volumen.** Ingen fyldartikler og ingen tvungen timeproduktion.
3. **Fakta og vurdering adskilles.** Nyheder beskriver; kommentarer argumenterer.
4. **Fairness er relevant vægt, ikke kunstig 50/50.** Modpositioner med reel betydning skal gengives loyalt; dokumenteret fakta får ikke samme vægt som udokumenterede påstande.
5. **Kilder er synlige og sporbare.** AI-output er aldrig kilde.
6. **Rettelser er åbne.** Materielle fejl korrigeres med note og tidsstempel.
7. **Ingen falsk autoritet.** Ingen opdigtede journalister, klienter, øjenvidner eller eksperter.

## Nyhed er ikke kommentar

En nyhed må ikke slutte med avisens vurdering, insinuation eller moralske konklusion. Kommentarer mærkes `Kommentar` og ligger i en selvstændig fil/URL. En kommentar om en aktuel sag publiceres først, når en faktuel nyhedsartikel om samme sag findes og linkes begge veje.

## Fairness og forelæggelse

Når en artikel indeholder konkrete, potentielt skadelige beskyldninger mod en identificerbar person, virksomhed eller institution, skal den berørte part have en reel mulighed for at svare før publicering, medmindre:

- forholdet allerede er ubestridt dokumenteret i en primær offentlig kilde, eller
- akut offentlig sikkerhed gør øjeblikkelig publicering nødvendig.

Undtagelsen skal fremgå af research-memoet. Ved alvorlige beskyldninger, børn, selvmord, seksualforbrydelser, privat helbred, identifikation i kriminalstof eller anden høj risiko går stykket til `manual_review: true` og må ikke autopubliceres.

## Krimi

Skriv sigtet, tiltalt, dømt og frifundet korrekt. Ingen er dømt før dom. Identifikation kræver selvstændig relevans og proportionalitet. Børn og mindreårige anonymiseres som udgangspunkt.

## Citater

Citatoverskrift kun ved ordret, verificeret citat. Oversættelser markeres ikke som direkte citat, medmindre den danske ordlyd er dokumenteret som autoriseret. Ellers parafrasér.

## Publiceringstid

Tidspunktet på artiklen er det øjeblik, den faktisk genereres til `docs/` og går live. Dansk tid. Format: `30. august 2026 kl. 14.23`. `<time datetime>` skal være samme tidspunkt i ISO 8601.

Planlagt stof får først publiceringstid ved faktisk publicering. Ingen fremdatering og ingen genbrug af gammelt klokkeslæt. Ved substantiel senere opdatering vises både oprindelig publicering og `Opdateret`.

## Billeder

Dokumentariske nyhedsbilleder må ikke være generativt skabte eller manipulerede, så de forestiller en virkelig begivenhed, der ikke er fotograferet. AI-grafik må kun bruges som tydeligt mærket **Illustration** og må ikke kunne forveksles med dokumentation.

Billede skal passe til sted, tid og emne. Ophav/licens registreres. Forside og teaser behøver ikke fotograf-linje; artikelside viser kredit, når licensen kræver det.

## Byline og transparens

Standardbyline er `Morgentidende Redaktion`, medmindre en faktisk navngiven skribent står bag. Offentlige sider skal tydeligt forklare redaktionel metode, AI-brug, kontakt og rettelser.

## Lead og forside

Forsiden styres af `FRONTPAGE.md`: vægt først, tid bagefter. Den nyeste artikel er ikke automatisk lead. Kommentar, guide og SEO-stof bliver aldrig lead alene på grund af alder eller klik.

## Obligatorisk anden-tjek før publicering

- Er sidste afsnit en vurdering fra avisen? → flyt til Kommentar eller slet.
- Findes alle bærende fakta i faktaledgeren?
- Er egennavne, tal og datoer verificeret?
- Er relevant modpart med?
- Er kategori og nyhedsvægt korrekt?
- Er historien allerede dækket i samme story cluster?
- Matcher billede og licens?
- Er publiceringstiden faktisk?
- Er leadplaceringen begrundet efter `FRONTPAGE.md`?

Ved tvivl: vælg den neutrale, dokumenterede formulering eller stop.
