# Design — Morgentidende

Låst 29. august 2026. Brugeren har 30. august 2026 godkendt en teknisk ændring: indhold og forside skal fremover genereres fra strukturerede data, så redaktionelle agenter ikke kan ændre layout ved et uheld. Brugeren har samme dag godkendt dark mode med en diskret skydeknap øverst. Den 31. august 2026 godkendte brugeren en skarpere ikke-kursiv wordmark samt en mindre sticky masthead på artikelsider. Det visuelle design er fortsat låst bortset fra disse udtrykkeligt godkendte ændringer.

## Farver

- Papir `#F3EEE4`
- Blæk `#161513`
- Header/footer `#1B2430`
- Ticker `#121820`
- Tema-boks `#E8E2D4`
- Accent `#3D5270`
- Guld `#C9A227`
- Dark mode bruger de låste tema-variabler i `docs/theme.css`; det lyse tema forbliver standardpaletten.

## Typografi

Wordmark: **Roboto Slab 700**, ikke kursiv, med let negativ bogstavafstand for et mere kantet og autoritativt avisudtryk. På forsiden bruges fortsat stor wordmark `clamp(2.35rem, 5.6vw, 3.85rem)`.

På artikelsider er mastheaden sticky og kompakt: wordmark omkring `1.55–2rem` på desktop og cirka `1.45rem` på mobil. Den forbliver synlig ved scroll uden at optage unødigt meget læseareal.

Brød: Source Serif 4. Kicker/UI: Source Sans 3.

## Sideskabelon

Forside: lead + rail + tre kort + fire smalle.
Artikelside: `article-grid` + sidespalte + `.below` fire spalter med foto.
Nyhed/kommentar om samme sag: `.related-teaser` begge veje.
Flere stykker om samme tema: `.theme-box`.
Dark mode-kontrollen ligger diskret øverst til højre i masthead på forside og artikelsider. Første besøg følger systemets tema; et manuelt valg huskes lokalt i browseren.

På artikelsider skal mastheaden være sticky. Den sticky artikelmasthead viser den kompakte Morgentidende-wordmark og dark-mode-kontrollen; den skal ikke vokse til forsidens fulde højde ved scroll.

## Genereret HTML

Nye og substantielt opdaterede artikler skrives som struktureret indhold i `content/articles/`. `scripts/build_all.py` genererer HTML under `docs/artikler/` fra den centrale skabelon. Forsiden styres af `content/frontpage.json` og genereres centralt.

Journalist-, SEO-, sprog-, billed- og redaktøragenter må ikke skrive layout-HTML eller CSS. De ændrer kun felter, som deres prompt giver adgang til.

Legacy-HTML må vises uændret, men skal migreres til generatoren ved større opdatering.

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

style.css-grids, header, logo-fil, wordmark-størrelse/font, grundfarver, dark mode-udtryk eller ny layoutstruktur.

Tilladt inden for låsen: nye artikler, teaser-tekst, sitemap, story clusters, `.related-teaser`, `.theme-box`, offentlige metode-/rettelsessider og metadata.
