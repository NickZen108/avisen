# Korrekturvagt – 29. august 2026 kl. 20.07 CEST

## Interne noter og redaktørstemme
Gennemgået forsiden (`docs/index.html`) og alle 15 HTML-filer i `docs/artikler/`.
Søgt efter: »Ingen frit foto«, »Illustration fordi«, »Det er hans sætning«, »ikke avisens«, produktionsforklaringer, redaktørstemme.
**Resultat: ingen forekomster.** Ingen sletning nødvendig. Teasere er allerede sagstekst.

## Døde fotos
Følgende Wikimedia-URL’er returnerede 404:
- `Føtex.jpg`
- `Irma_supermarket_Frederiksberg.JPG`
- `Folketinget.jpg`

**Rettet:** Erstattet med `Grocery_store.jpg` og `Christiansborg.jpg` i index.html og de berørte artikler (ukraine-stoette, kommentar-lyngby, kommentar-emballage).
Commit: f848012 (index) + efterfølgende.

## Foto vs. overskriftens sted
- Lyngby-artiklen: Lyngby Station / Værløse Station – acceptabelt.
- Søften: Grubenhaus (rekonstruktion) – acceptabelt.
- Øvrige: generiske eller tematisk dækkende. Ingen mismatch kræver øjeblikkelig udskiftning.

## Manglende tid
Ingen artikelsider har `<time datetime>`.
Meta-linjer findes, men ISO-tid mangler ifølge EDITORIAL.md.
**Anbefaling til næste runde:** Indsæt `<time datetime="YYYY-MM-DDTHH:MM:00+02:00">` matching meta-teksten.

Bemærk: Flere artikler er dateret 30. august (frem i tiden) og nogle med kl. 06.00. EDITORIAL forbyder begge. Dateline på forsiden er 29. august.

## Manglende .below
Alle artikelsider har `<section class="wrap below">` med fire spalter. OK.

## Manglende krydsteaser
- Lyngby-nyhed ↔ kommentar-lyngby: begge har `.related-teaser`. OK.
- Insa-AfD ↔ kommentar-afd: begge har. OK.
- soevn-sst ↔ guide-soevn: **mangler** begge veje.
- moms-paa-mad ↔ kommentar-emballage: mangler (tematisk relevant).

**Anbefaling:** Tilføj `.related-teaser` for søvn-parret og eventuelt emballage/moms.

## Øvrigt
style.css urørt. Ingen intern note slettet (ingen fundet).

## Status
Døde fotos rettet og committed. Resterende punkter (tid, krydsteaser, fremdatering) noteret til næste korrekturrunde.
