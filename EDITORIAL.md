# 1. Redaktionel linje

Navn på alle flader: **Morgentidende**.

Seriøs broadsheet. Ikke partiblad. Ikke vred. Nyheden skal kunne læses af en uenig. Holdningen vises i emnevalg og i stykker mærket Kommentar.

## Sprog

Kort. Aktiv. Dansk. Kedeligt og klart. Ingen slang.

## Forbudt på siden

Ingen intern note. Ingen redaktørstemme. Ingen »ikke en facitliste«, »ikke avisens«, »ingen frit foto«.

## Nyhed er ikke kommentar

En nyhed må ikke slutte med avisens vurdering. Sådanne sætninger hører i Kommentar eller ud.

## Udgivelsestid

Tidspunktet på artiklen er det øjeblik, filen lander i `docs/` og går live. Dansk tid. Format: `29. august 2026 kl. 19.23`.

Forbudt: at sætte kl. 06.00, at datere frem i tiden, at genbruge et gammelt klokkeslæt. Planlagt kø får først tid, når den faktisk publiceres.

`<time datetime>` skal være samme tid i ISO.

## Foto og kredit

Forside og teasere: ingen fotograf-linje. Artikelside: kredit når licensen kræver det. Foto matcher overskriftens sted og emne.

## Anden-tjek (obligatorisk før commit)

1. Sidste afsnit en vurdering fra avisen? → flyt eller slet.
2. Intern note? → slet.
3. Citat ordret med kilde i memoet? Ellers veto.
4. Egennavne forklaret første gang?
5. Foto matcher overskrift?
6. Dårlig oversættelse? → omskriv.
7. Er klokkeslættet det faktiske publiceringstidspunkt? Nej → ret før commit.

## Citatoverskrift, etnicitet, vægtning

Citatoverskrift kun ordret. Etnicitet kun som tegn i anden halvdel. Mindst 4 af 10 ikke-politiske.

## Tvivl

Vred eller partiblad: vælg den neutrale linje.
