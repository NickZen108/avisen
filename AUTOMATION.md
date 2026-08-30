# Gratis automationsarkitektur — eksperimentfase

Målet i denne fase er maksimal stabilitet uden betalte AI-API-kald.

## Princip

**AI = redaktion. GitHub Actions = maskinrum.**

GitHub Actions på standard runners bruges til alt deterministisk arbejde i det offentlige repo: scanning, kø, quality gates, merge-vagt, build, sitemaps, deployment-kontrol, retries, QA og rollback-sikkerhed.

AI bruges kun til det, scripts ikke bør foregive at kunne: nyhedsværdi, research, kildevurdering, faktaledger, journalistik, sprog, fairness og forsidevurdering. I eksperimentfasen kommer AI-arbejdet fra ChatGPT-automation/manuel ChatGPT-brug — **ikke** fra OpenAI-, xAI-, Anthropic- eller andre betalte API-kald inde i GitHub Actions.

## Gratis flow

1. `Breaking scan` kører hvert 15. minut og skriver `scan/latest.md`.
2. `Newsroom cycle` kører efter et vellykket scan og laver `queue/candidates.json` uden AI. Filen er kun en kandidat-inventarliste; den er ikke en redaktionel vurdering.
3. ChatGPT-redaktionen læser køen + aktuelle kilder og udfører den fulde agentpipeline.
4. Godkendt autopublicerbart stof afleveres på branch `edition/*` eller `newsroom/*` som en PR mod `main`.
5. Auto-PR skal have titelprefix `[AUTO] ` og body-markøren `<!-- morgentidende-auto-publish -->`.
6. `Quality gates` bygger og tester PR-head deterministisk.
7. `Auto-publish merge` kan kun merge PR'er fra dette repo, med korrekt branch/prefix/marker, med højst 50 ændrede filer, uden deletions og kun fra en snæver redaktionel allowlist. Den merger præcis det SHA, der bestod testen.
8. Merge til `main` udløser `Build structured edition`, som genererer `docs/` fra canonical struktureret indhold.
9. Alle workflows der skriver til `main`, bruger samme concurrency-lock, så scan, kø, publish, QA og rollback ikke kan overskrive hinanden.
10. `Post-deploy guard` giver GitHub Pages tid til at deploye og tester derefter tre gange. Kun ved vedvarende **interne** fejl kan det seneste genererede publisher-commit rulles tilbage. Tredjepartsbilleder kan give advarsel, men aldrig automatisk rollback.
11. `Post-publication QA` kører fortsat hver time og skriver live-rapport.

## Hvad GitHub Actions ikke må gøre i gratis fase

- kalde en betalt LLM/API
- skrive journalistik ud fra en overskrift alene
- afgøre breaking, fairness eller source-independence med simple heuristikker
- masseproducere fyldartikler
- auto-merge system-, design-, workflow-, template- eller scriptændringer
- auto-publicere `manual_review: true`

## Auto-publish allowlist

En `[AUTO]` newsroom-PR må kun ændre:

- `content/articles/**`
- `content/frontpage.json`
- `sources/**`
- `killed/**`
- `scheduled/**`
- `reports/editorial/**`

En fjernet fil stopper auto-merge. Ændringer udenfor listen stopper auto-merge.

## Systemændringer

Ændringer af regler, scripts, workflows, templates, design, CSS og generatorer skal gå gennem en almindelig PR uden auto-publish-markør og skal bevidst godkendes/merges som systemarbejde.

## Senere

Når formatet er stabilt og økonomien kan bære det, kan AI-redaktionen flyttes ind i GitHub Actions via en model-API. Arkitekturen ændres ikke: API-agenten afleverer stadig kun en newsroom-PR; den får aldrig direkte live-adgang.
