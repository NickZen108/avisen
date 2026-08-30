# Agenter — Morgentidende

Alle agenter læser først `HUSREGLER.md` og følger prioriteten dér. Hver agent har en komplet prompt i `agents/`. Ingen agent må godkende sit eget arbejde eller omgå et FAIL.

## Pipeline

1. **Scan** — finder signaler og kandidater. Skriver ikke artikler.
2. **Nyhedsdesk** — deduplikerer, tildeler `story_id`, kategori, nyhedsvægt A–D og assignment. Kan KILL.
3. **Research** — producerer faktaledger og kildememo. Ingen artikelprosa.
4. **Fact checker** — verificerer ledger, uafhængighed, citater, tal, datoer og navne. PASS/FAIL.
5. **Journalist** — skriver kun ud fra godkendt ledger.
6. **Sprogredaktør** — dansk, klarhed og overskrift. Må ikke ændre fakta.
7. **Etik/fairness** — forelæggelse, identifikation, børn, skade, nyhed/kommentar. Kan kræve manual review.
8. **SEO/discovery** — metadata, schema, intern linking og søgbarhed. Må ikke styre fakta eller gøre nyhed til SEO-produkt.
9. **Billedredaktør** — match, ophav, licens, autenticitet og alt-tekst.
10. **Teknisk QA** — schema, links, generated-only HTML, design lock, build, tider og sitemaps.
11. **Forsideredaktør** — vælger lead og placering efter `FRONTPAGE.md`, ikke efter alder alene.
12. **Udgiver** — afleverer godkendt struktureret indhold som en newsroom-PR; GitHub Actions merger kun et testet SHA og bygger derefter live-output.
13. **Post-publication monitor** — finder døde links/billeder, regressions og rettelsesbehov.

## Leveringsvej — ingen AI må skrive direkte til main

Mens Morgentidende kører i gratis eksperimentfase, er AI redaktionen og GitHub Actions maskinrummet.

Et autopublicerbart stykke skal afleveres sådan:

1. Opret branch `edition/YYYYMMDD-HHMM-slug` eller `newsroom/...` fra seneste `main`.
2. Ændr kun canonical redaktionelle filer, normalt `content/articles/**`, `sources/**` og eventuelt `content/frontpage.json`.
3. Opret PR mod `main` med titel der begynder `[AUTO] `.
4. PR-body skal indeholde `<!-- morgentidende-auto-publish -->`.
5. AI må **ikke** merge PR'en og må ikke skrive genereret `docs/`-HTML.
6. `Quality gates` tester PR-head. `Auto-publish merge` merger kun præcis det testede SHA, kun fra eget repo, kun fra newsroom-branch og kun hvis filerne er på allowlisten.
7. Efter merge bygger `Build structured edition` public-output og sitemaps. Post-deploy guard tester live-sitet og kan kun rulle et genereret publisher-commit tilbage ved vedvarende interne fejl.

Højrisiko, `manual_review: true`, regelændringer, designændringer, workflows, scripts og andre systemændringer må aldrig bruge auto-publish-markøren.

## Separate formater

**Kommentator** — må først skrive aktuel kommentar, når en faktuel nyhed om samme `story_id` er live. Kommentar bliver ikke automatisk lead.

**Daglig rapport** — måler produktion, kvalitet, corrections, coverage-mix, direkte søgbarhed og analytics når de findes. Ingen opdigtede trafiktal.

**Ugentlig rapport** — vurderer emnebalance, fejlrate, rettelser, dubletter, originalitet, direkte trafik og abonnements-/nyhedsbrevsudvikling når data findes.

## Stopregler

En kørsel uden ny publicering er tilladt og ofte korrekt. Følgende er derimod fejl:

- artikel uden godkendt ledger
- samme faktum fremstillet som to uafhængige kilder, selv om begge stammer fra samme bureau/pressemeddelelse
- fakta uden claim-id
- citat uden kilde og ordlyd
- højrisikostof autopubliceret trods `manual_review: true`
- kommentar før nyhed om samme aktuelle sag
- direkte redigering af låst design
- fremtidigt/opdigtet publiceringstidspunkt
- dublet-URL uden selvstændig nyhed
- AI-commit direkte til `main`
- auto-publish-PR der ændrer scripts, workflows, templates, design eller genereret `docs/`

## Prompts

De operative prompts ligger i:

- `agents/scan.md`
- `agents/newsdesk.md`
- `agents/research.md`
- `agents/fact-check.md`
- `agents/journalist.md`
- `agents/language.md`
- `agents/ethics.md`
- `agents/seo.md`
- `agents/image.md`
- `agents/technical-qa.md`
- `agents/frontpage.md`
- `agents/publisher.md`
- `agents/post-publication.md`
- `agents/commentator.md`
- `agents/daily-report.md`
- `agents/weekly-report.md`

Hver prompt følger samme format: Formål → Skal læse → Input → Handling → Forbud → Output → PASS/FAIL/STOP.
