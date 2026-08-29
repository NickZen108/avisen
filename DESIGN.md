# 2. Design

Låst 29. august 2026. Ændres kun når brugeren skriver det sort på hvidt.

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

## Forbudt uden ny ordre

style.css-grids, header, logo-fil, wordmark-størrelse, grundfarver.

Tilladt: nye artikler, teaser-tekst, sitemap, bruge `.related-teaser` og `.theme-box`.
