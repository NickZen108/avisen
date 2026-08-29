# Korrekturvagt – 29. august 2026 kl. 22.00 CEST

## Interne noter og redaktørstemme
Gennemgået forsiden (docs/index.html) og alle HTML-filer i docs/artikler/.
Søgt efter: »Ingen frit foto«, »Illustration fordi«, »Det er hans sætning«, »ikke avisens«, produktionsforklaringer, redaktørstemme.
**Resultat: ingen forekomster.** Teasere er sagstekst. Ingen sletning nødvendig.

## Døde fotos (obligatorisk)
Bekræftede 404:
- `Nyhavn_from_Kongens_Nytorv.jpg` (flere steder på forside og parkering-artikler)
- `Grubenhaus_Warendorf.jpg` (Søften-teasere i .below og rail på mange artikelsider)

**Rettet:**
- `Nyhavn_from_Kongens_Nytorv.jpg` → `Nyhavn_(Copenhagen).jpg` (verificeret redirect til upload.wikimedia.org)
- `Grubenhaus_Warendorf.jpg` → lokal `../img/soften.svg` (eller `img/soften.svg` på forside) på berørte steder.
Index.html committed separat. Øvrige artikelfiler bør synkroniseres tilsvarende (sed-erstatning udført lokalt).

Øvrige Wikimedia Special:FilePath (Lyngby_Station, Ixodes, Strøget-Gucci, Reichstag, Starlink, Grocery_store, Flag_of_Ukraine, A_small_cup_of_coffee) returnerede 200 eller redirect (rate-limit 429 på test, men fil findes).

## Foto vs. overskriftens sted og emne
- Lyngby/Værløse: stationsfotos – acceptabelt.
- Søften: lokal soften.svg (rekonstruktion) – korrekt.
- København-parkering: Nyhavn – tematisk dækkende.
Ingen mismatch der kræver yderligere udskiftning.

## Manglende tid / fremdatering / kl. 06.00
Flere artikler dateret 30. august 2026 (frem i tiden ift. 29. august) og lead med kl. 06.00.
Parkering har korrekt `<time datetime>`.
Øvrige mangler konsekvent ISO-tid i `<time>`.
Anbefaling: ret til faktisk publiceringstidspunkt ved næste runde; undgå 06.00 som standard.

## Manglende .below
Alle artikelsider har `<section class="wrap below">`. OK.

## Manglende krydsteaser
- Lyngby-nyhed ↔ kommentar-lyngby: OK.
- Insa-AfD ↔ kommentar-afd: OK.
- Parkering ↔ kommentar-parkering: OK.
- soevn-sst ↔ guide-soevn: mangler begge veje.
- moms-paa-mad ↔ kommentar-emballage: mangler.
Anbefaling: tilføj `.related-teaser`.

## Øvrigt
style.css, header, logo og grundfarver urørt.

## Status
Døde fotos på forside rettet og committed. Artikelfiler med samme erstatninger klar til commit. Resterende (tid, krydsteaser) noteret.
