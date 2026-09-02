# Design — Morgentidende

Låst 29. august 2026. Brugeren har 30. august 2026 godkendt en teknisk ændring: indhold og forside skal fremover genereres fra strukturerede data, så redaktionelle agenter ikke kan ændre layout ved et uheld. Brugeren har samme dag godkendt dark mode med en diskret skydeknap øverst. Den 31. august 2026 godkendte brugeren en skarpere ikke-kursiv wordmark samt en mindre sticky masthead på artikelsider. Samme dag godkendte brugeren en lysere varm papirbaggrund, kontrolleret variation i forsidens rubriktypografi og en oprydning af undersider/navigation. Den 2. september 2026 godkendte brugeren, at mastheaden med logoet skal være sticky på alle sider. Det visuelle design er fortsat låst bortset fra disse udtrykkeligt godkendte ændringer.

## Farver

- Papir `#F8F5EF` — næsten hvid med en diskret varm tone
- Blæk `#161513`
- Header/footer `#1B2430`
- Ticker `#121820`
- Tema-boks `#E8E2D4`
- Accent `#3D5270`
- Guld `#C9A227`
- Dark mode bruger de låste tema-variabler i `docs/theme.css`; det lyse tema forbliver standardpaletten.

Den varme papirfarve skal give Morgentidende en egen identitet uden at gøre siden beige, retro eller bogagtig. Store neutrale flader skal ved første blik opleves næsten hvide.

## Typografi

Wordmark: **Roboto Slab 700**, ikke kursiv, med let negativ bogstavafstand for et mere kantet og autoritativt avisudtryk. Samme wordmark-font skal bruges på forside, artikler og alle undersider.

Mastheaden med logoet er sticky på alle sider og forbliver synlig ved scroll. På artikelsider er den desuden kompakt: wordmark omkring `1.55–2rem` på desktop og cirka `1.45rem` på mobil, så den ikke optager unødigt meget læseareal.

Brød: Source Serif 4. Kicker/UI: Source Sans 3.

`Også i dag` og `Mere om sagen` bruger samme serif-familie og omtrent samme visuelle vægt. Kategorilabels forbliver små sans serif-labels.

## Rubrikhierarki på forsiden

Forsiden skal have kontrolleret variation, ikke én mekanisk rubrikstil. Canonical artikeltitel ændres ikke af rendererens typografi.

- `classic`: almindelig seriøs rubrik.
- `split`: ved en naturlig kolon-opdeling kan anslaget før kolon stå tydeligere/federe, mens resten står lettere.
- `video`: `Video:` eller `Billeder:` kan få diskret accentfarve og stærkere vægt.
- `quote`: citatrubrik får egen diskret typografisk behandling, men ikke dekorativ overdrivelse.

Blandet fed/normal skrift og to farver bruges kun på udvalgte historier, især lead, stærke kort eller verificeret video. De må ikke dominere hele forsiden. Smalle lister og højre rail skal som udgangspunkt være roligere.

## Navigation og undersider

Forsidens primære menu skal være enkel: nyheder og nyhedsbrev. `Om` og `Rettelser` er utility-links og ligger i footeren frem for at optage plads i hovedmenuen.

`Om`, `Rettelser` og `Nyhedsbrev` skal visuelt føles som samme produkt som forsiden: samme Roboto Slab-wordmark, varm papirbaggrund, serif-brødtekst og dark-mode-kontrol. Undersider må gerne bruge et roligt kort/panel med mere luft end almindelige artikler.

Nyhedsbrevsiden skal have en tydelig, indbydende CTA med stort skrivefelt, enkel knap og kort forklaring af værdien før formularen.

På mobil skal dark-mode-knappen ligge tydeligt til højre for wordmarken med reserveret plads omkring logoet; den må aldrig overlappe logoet. På den store forsideheader placeres den i den øverste højre del af mastheaden frem for at forsøge at centrere sig mod hele headerens højde.

## Sideskabelon

Forside: lead + rail + tre kort + fire smalle.
Artikelside: `article-grid` + sidespalte + `.below` fire spalter med foto.
Nyhed/kommentar om samme sag: `.related-teaser` begge veje.
Flere stykker om samme tema: `.theme-box`.

## Genereret HTML

Nye og substantielt opdaterede artikler skrives som struktureret indhold i `content/articles/`. `scripts/build_all.py` genererer HTML under `docs/artikler/` fra den centrale skabelon. Forsiden styres af `content/frontpage.json` og genereres centralt. Rettelsessiden genereres centralt af buildet, så dens masthead og footer ikke glider væk fra resten af designet.

Journalist-, SEO-, sprog-, billed- og redaktøragenter må ikke skrive layout-HTML eller CSS. De ændrer kun felter, som deres prompt giver adgang til.

## Maskinel lås

`config/design-lock.txt` indeholder Git blob-hash for låste filer. CI fejler, hvis de ændres uden samtidig eksplicit opdatering af designlåsen efter brugerordre.

Låst:

- `docs/style.css`
- `docs/signup.css`
- `docs/theme.css`
- `docs/theme.js`
- `docs/logo.svg`
- `docs/logo-mark.svg`
- grundstruktur i generatorens header/footer/layout

## Forbudt uden ny brugerordre

style.css-grids, header, logo-fil, wordmark-størrelse/font, grundfarver, dark mode-udtryk, rubrikdesignsystem eller ny layoutstruktur.

Tilladt inden for låsen: nye artikler, teaser-tekst, sitemap, story clusters, `.related-teaser`, `.theme-box`, offentlige metode-/rettelsessider og metadata.
