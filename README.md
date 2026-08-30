# Morgentidende / Avisen

Offentligt redaktionelt arkiv og kildekode til en stærkt automatiseret dansk netavis.

GitHub er den kanoniske tekniske kopi. Nye artikler går gennem en gated redaktionel pipeline og skrives som struktureret indhold; `docs/` er publiceret/genereret output.

**Repo:** [github.com/NickZen108/avisen](https://github.com/NickZen108/avisen)

## Start her

1. `HUSREGLER.md` — regelhierarki og hårde stopregler
2. `EDITORIAL.md` — presseetik og redaktionel linje
3. `SOURCES.md` — kilder og faktaledger
4. `STYLE.md` — dansk og overskrifter
5. `DESIGN.md` — låst design og generator
6. `CATEGORIES.md` — kategorier og stofmix
7. `SCHEDULE.md` + `FRONTPAGE.md` — publicering og lead
8. `AGENTS.md` — pipeline og agentspecifikke prompts
9. `AUTOMATION.md` — gratis hybridarkitektur og auto-publish-sikkerhed

## Pipeline

Scan → Nyhedsdesk → Research → Fact check → Journalist → Sprog → Etik/fairness → SEO/discovery → Billede → Teknisk QA → Forsideredaktør → Udgiver → Post-publication monitor.

Ingen agent godkender sit eget arbejde. `NO_PUBLISH` er legitimt; der er ingen tvungen timeartikel.

I eksperimentfasen er **AI redaktionen, mens GitHub Actions er maskinrummet**. GitHub Actions bruges til scanning, kandidat-kø, quality gates, guarded auto-merge, build, deployment-kontrol og QA uden betalte model-API-kald. AI afleverer autopublicerbart stof som en `edition/*`/`newsroom/*` PR; den skriver ikke direkte til `main`.

## Mapper

| Sti | Formål |
|---|---|
| `agents/` | komplette prompts for hver redaktionel agent |
| `queue/` | deterministisk kandidat-inventar fra gratis scan; ikke en redaktionel vurdering |
| `sources/` | research og machine-readable fact ledgers |
| `content/articles/` | canonical strukturerede artikelkilder |
| `content/frontpage.json` | canonical forsidevalg |
| `templates/` | låste centrale HTML-skabeloner |
| `scripts/` | build, quality gates, live QA, newsroom queue og scan |
| `docs/` | GitHub Pages/live output |
| `killed/` | afviste assignments/stykker med årsag |
| `reports/` | daglig, ugentlig, editorial og QA-rapportering |

## Build

```bash
python scripts/quality_gate.py --prebuild
python scripts/build_all.py
python scripts/quality_gate.py
```

GitHub Actions kører de samme gates og kan committe genereret public-output. Nye håndskrevne HTML-artikler er forbudt; eksisterende legacy-artikler er grandfathered og migreres ved større opdatering.

## Gratis automation

- `Breaking scan`: hvert 15. minut.
- `Newsroom cycle`: omsætter scan til `queue/candidates.json` uden AI.
- `Quality gates`: tester alle PR'er og main.
- `Auto-publish merge`: merger kun newsroom-PR'er med korrekt `[AUTO]`-kontrakt, snæver fil-allowlist og præcis testet SHA.
- `Build structured edition`: genererer live-output fra structured content.
- `Post-deploy guard`: tre interne smoke-tests og forsigtig rollback af seneste genererede publisher-commit ved vedvarende intern fejl.
- `Post-publication QA`: timevis live-kontrol og rapport.

Alle workflows der skriver til `main`, deler en concurrency-lock, så samtidige scan/publish/QA-kørsler ikke overskriver hinanden.

## Transparens

Offentlige sider i `docs/` beskriver metode, AI-brug og rettelser. Materielle rettelser må ikke foretages stille.
