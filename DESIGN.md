# Design — Morgentidende

Låst 29. august 2026. Brugeren har 30. august 2026 godkendt en teknisk ændring: indhold og forside skal fremover genereres fra strukturerede data, så redaktionelle agenter ikke kan ændre layout ved et uheld. Det visuelle design er fortsat låst.

## Farver

- Papir `#F3EEE4`
- Blæk `#161513`
- Header/footer `#1B2430`
- Ticker `#121820`
- Tema-boks `#E8E2D4`
- Accent `#3D5270`
- Guld `#C9A227`

## Typografi

Wordmark: Fraunces italic, `clamp(2.35rem, 5.6vw, 3.85rem)`.
Brød: Source Serif 4. Kicker: Source Sans 3.

## Sideskabelon

Forside: lead + rail + tre kort + fire smalle.
Artikelside: `article-grid` + sidespalte + `.below` fire spalter med foto.
Nyhed/kommentar om samme sag: `.related-teaser` begge veje.
Flere stykker om samme tema: `.theme-box`.

## Genereret HTML

Nye og substantielt opdaterede artikler skrives som struktureret indhold i `content/articles/`. `scripts/build_all.py` genererer HTML under `docs/artikler/` fra den centrale skabelon. Forsiden styres af `content/frontpage.json` og genereres centralt.

Journalist-, SEO-, sprog-, billed- og redaktøragenter må ikke skrive layout-HTML eller CSS. De ændrer kun felter, som deres prompt giver adgang til.

Legacy-HTML må vises uændret, men skal migreres til generatoren ved større opdatering.

## Maskinel lås

`config/design-lock.txt` indeholder Git blob-hash for låste filer. CI fejler, hvis de ændres uden samtidig eksplicit opdatering af designlåsen efter brugerordre.

Låst:

- `docs/style.css`
- `docs/signup.css`
- `docs/logo.svg`
- `docs/logo-mark.svg`
- grundstruktur i generatorens header/footer/layout

## Forbudt uden ny brugerordre

style.css-grids, header, logo-fil, wordmark-størrelse, grundfarver eller ny layoutstruktur.

Tilladt inden for låsen: nye artikler, teaser-tekst, sitemap, story clusters, `.related-teaser`, `.theme-box`, offentlige metode-/rettelsessider og metadata.
