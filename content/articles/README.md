# Strukturerede artikler

Nye artikler oprettes her som JSON. `docs/artikler/*.html` er genereret output og må ikke håndskrives for nye artikler.

## Minimumfelter

- `status`: `draft`, `ready`, `scheduled` eller `published`
- `story_id`
- `slug` uden `.html`
- `category`
- `weight`: `A`, `B`, `C` eller `D`
- `title`
- `standfirst`
- `byline` (normalt `Morgentidende Redaktion`)
- `manual_review`
- `ledger`: sti til JSON-ledger i `sources/`
- `claim_ids`: claims faktisk brugt i teksten
- `body`: strukturerede blokke
- `seo`
- `image` eller `null`

`published_at` sættes først ved faktisk publicering. `updated_at` bruges ved substantiel opdatering.

## Body blocks

Tilladte typer: `p`, `h2`, `h3`, `ul`, `ol`, `blockquote` og `figure`. Tekst escapes af generatoren; journalisten leverer ikke vilkårlig HTML.

En `figure` bruges til grafik, der hører til et bestemt sted i artiklen. Minimum er `src` og `alt`; derudover kan bruges `caption`, `credit`, `source_url` og `wide`. Lokale grafikker ligger i `docs/img/` og refereres fra artikel-HTML som `../img/filnavn.svg`. `wide: true` giver næsten kant-til-kant-visning på mobil uden vandret scroll.

Hvis artikelens `image` primært bruges til Open Graph/metadata, mens grafikken skal stå inde i teksten, sættes `placement: inline`. Så vises den ikke automatisk som lead-billede øverst.

## Relaterede artikler

`related` indeholder normalt 2–4 relevante live artikler. Generatoren bruger dem både i artikelens sidefelt og som teasere under artiklen. Brug ikke planlagte eller upublicerede slugs.

## Kommentar

`category: Kommentar` kræver `related_news_slug` til den live faktuelle artikel om samme aktuelle story.

## Publicering

Når `status` ændres til `published` og alle gates er PASS, genererer `scripts/build_all.py` HTML. `quality_gate.py` afviser nye håndskrevne HTML-artikler.
