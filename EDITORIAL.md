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

## Forside-lead

Som DR, TV 2 og Berlingske på nettet: vægt først, tid bagefter. Leadet er den sag, der bærer udgaven nu. Ikke det nyeste ur.

Rangorden, højest først:
1. Breaking med konkret, pågående hændelse.
2. Krimi og ret med navngivne tiltalte og ny proces.
3. Vedtaget eller officielt brudt stof (Folketing, kommune, styrelse, dom).
4. Politisk eller kommunalt udspil, takster, målinger.
5. Feature, guide, historie, sundhed uden brud.

Kommentar og guide bliver aldrig lead. Time-artiklen arver ikke 1-eren, fordi den er ny.

Breaking overtager leadet med det samme. Bliver til næste vurdering.

Et lead uden ny udvikling i sagen rykker ned efter otte timer, eller ved midnat, hvis der findes et yngre stykke længere oppe i rangordenen — eller et udspil, når intet tungere er tilbage. En retssag må blive til aften, så længe den er dagens tungeste. Den må ikke stå som evig 1-er, når intet nyt er sket og der ligger frisk stof.

Når lead skiftes: det gamle går i rail eller første kort. Foto, H1 og manchet følger den nye sag. Ticker må være et andet stykke (det seneste). Rør ikke CSS.

## Anden-tjek (obligatorisk før commit)

1. Sidste afsnit en vurdering fra avisen? → flyt eller slet.
2. Intern note? → slet.
3. Citat ordret med kilde i memoet? Ellers veto.
4. Egennavne forklaret første gang?
5. Foto matcher overskrift?
6. Dårlig oversættelse? → omskriv.
7. Er klokkeslættet det faktiske publiceringstidspunkt? Nej → ret før commit.
8. Bærer leadet stadig udgaven, eller skal det rykke efter forside-reglen?

## Citatoverskrift, etnicitet, vægtning

Citatoverskrift kun ordret. Etnicitet kun som tegn i anden halvdel. Mindst 4 af 10 ikke-politiske.

## Tvivl

Vred eller partiblad: vælg den neutrale linje.
