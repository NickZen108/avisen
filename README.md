# Morgentidende

GitHub er source of truth for redaktionelt indhold og pipelinekode. `content/` og `sources/` er canonical data; `docs/` er genereret public-output.

## Canonical dokumentation

- `HUSREGLER.md` — overordnede principper og hard stops
- `EDITORIAL.md` — redaktionel linje og presseetik
- `SOURCES.md` — kilder og faktuel evidens
- `AGENTS.md` — roller og ansvar
- `ARCHITECTURE.md` — teknisk arkitektur
- `SCAN.md` — discovery
- `SCHEDULE.md` — udgivelsesrytme
- `FRONTPAGE.md` — lead og placering
- `MEDIA_SOURCES.md` — lovlige/gratis billedkilder og mediaregler
- `STYLE.md`, `DESIGN.md`, `CATEGORIES.md`, `SEO.md` — specialistregler

README’en gentager ikke disse regler. Ved konflikt gælder prioriteten i `HUSREGLER.md`.

## Centrale data

- `content/articles/` — artikler
- `sources/` — faktaledgers
- `content/frontpage.json` — forsideplacering
- `content/corrections.json` — offentlig rettelseslog
- `reports/editorial/approvals/` — versionsbundne final approvals
- `docs/` — genereret offentlig avis

## Canonical build

```bash
python scripts/build_all_v2.py
```

Publicering og øvrige nødvendige trin køres af workflows i `.github/workflows/`; README’en er ikke en proceskontrakt.
