# Strukturerede artikler

Nye artikler oprettes her som JSON. `docs/artikler/*.html` er genereret output og må ikke håndskrives for nye artikler.

## Minimumfelter

- `status`: `draft`, `ready` eller `published`
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

`published_at` sættes først ved faktisk publicering. `updated_at` bruges kun ved substantiel opdatering.

## Body blocks

Tilladte typer: `p`, `h2`, `h3`, `ul`, `ol`, `blockquote`. Tekst escapes af generatoren; journalisten leverer ikke vilkårlig HTML.

## Kommentar

`category: Kommentar` kræver `related_news_slug` til den live faktuelle artikel om samme aktuelle story.

## Publicering

Når `status` ændres til `published` og alle gates er PASS, genererer `scripts/build_all.py` HTML. `quality_gate.py` afviser nye håndskrevne HTML-artikler.
