# Morgentidende / Avisen

GitHub er den kanoniske tekniske kopi. Nye artikler går gennem en gated redaktionel pipeline som struktureret indhold; `docs/` er genereret public-output.

## Pipeline v2

Scan → Nyhedsdesk assignment → Research/coverage sweep → Fact check → Nyhedsdesk recheck → Journalist → Sprog → Etik → Billede → SEO → Slutredaktør → Forside → Teknisk QA → Udgiver → live technical QA → Live proofreader → Redaktionel update-monitor.

Ingen agent gør sit eget arbejde publiceringsklart. Slutredaktøren laver et versionsbundet final approval snapshot efter alle redaktionelle ændringer.

## Publicering

Nye auto-artikler bruger `pipeline_version: 2`. Udgiver afleverer `status: ready` + `release_requested: true` uden `published_at`. GitHub Actions sætter faktisk publiceringstid ved release/build efter merge, bygger HTML/sitemaps/rettelseslog og tester live-sitet.

## Canonical data

- `content/articles/` — artikler
- `sources/` — fact ledgers
- `content/frontpage.json` — placering; v2-artikler er normalt slug-referencer
- `content/corrections.json` — offentlig rettelseslog
- `reports/editorial/approvals/` — Slutredaktørens final approvals
- `docs/` — genereret public-output

## Build

```bash
python scripts/release_ready.py
python scripts/quality_gate.py --prebuild
python scripts/build_all.py
python scripts/quality_gate.py
```
