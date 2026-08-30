# Kvalitetskontrol

QA består af redaktionelle gates, deterministiske tests og live-kontrol. Et grønt build er nødvendigt, men ikke tilstrækkeligt til publicering.

## Pipeline v2

Nye auto-publicerede artikler skal have `pipeline_version: 2`.

Før `ready`, `scheduled` eller `published` kræves coverage sweep, `fact_check.status: pass`, `desk_recheck.status: publish|update`, opfyldt forelæggelse og matching `reports/editorial/approvals/<slug>.json`.

Approval-gates `language`, `ethics`, `image`, `seo`, `final_editor` skal være `pass`. Final approval indeholder et snapshot af de redaktionelle artikeldata. Ændres journalistisk indhold efter approval, er det FAIL.

Gamle allerede publicerede v1-artikler er grandfathered. En ny `[AUTO]`-PR må ikke ændre/publicere en artikel uden pipeline v2.

## Fakta

- claim-id'er findes i ledgeren
- publicable claims er `verified`
- bærende claims har autoritativ primærstøtte eller reelt uafhængig støtte
- source-groups afledes af sources

## Billede før SEO

Billedredaktøren afslutter billedvalg/licens/alt-tekst før SEO færdiggør Open Graph og delingsmetadata.

## Forside

Pipeline-v2-artikler refereres normalt kun med `slug` i `content/frontpage.json`. Builderen henter canonical titel, kategori, manchet, billede og publiceringstid fra artiklen. Legacy-artikler kan beholde eksplicitte displayfelter.

## Metadata og tid

`published_at` sættes af release-motoren ved faktisk release/build, ikke ved PR-oprettelse.

## Live QA

Efter deploy kontrolleres forsiden, eksplicit netop ændrede artikel-URL'er, recent publicerede artikler, interne assets og template-markers. Live proofreader er en separat redaktionel korrektur af den renderede side.

## Rettelser

`content/corrections.json` er canonical offentlig rettelseslog. `docs/rettelser.html` genereres. Materielle fejl må ikke rettes stille.
