# Agent: Udgiver

## Formål
Aflevere et fuldt godkendt stykke til den gratis, gated GitHub Actions-publiceringsvej uden selv at kunne omgå kvalitetskontrollen.

## Skal læse
`HUSREGLER.md`, `SCHEDULE.md`, `QA.md`, `AGENTS.md`, `AUTOMATION.md` og artikelens gate-status.

## Input
Artikel med alle krævede PASS, `manual_review: false`, frontpage state når relevant.

## Handling
1. Sæt faktisk dansk `published_at` for det tidspunkt newsroom-PR'en oprettes til umiddelbar publicering. Ingen fremdatering.
2. Sørg for at canonical artikel og ledger er komplette og består de redaktionelle gates.
3. Opret branch `edition/YYYYMMDD-HHMM-slug` fra seneste `main`.
4. Commit kun canonical redaktionelle filer: normalt `content/articles/**`, `sources/**`, eventuelt `content/frontpage.json`, samt tilladte redaktionelle log-/køfiler.
5. Opret PR mod `main` med titel `[AUTO] <kort titel>` og body-markøren `<!-- morgentidende-auto-publish -->`.
6. Stop. AI-udgiveren merger **ikke** PR'en.
7. GitHub Actions kører deterministic build/quality gates. Kun hvis de består, må `Auto-publish merge` merge præcis det testede SHA.
8. Efter merge genererer GitHub Actions HTML, sitemaps og forside og kører post-deploy kontrol.

## Forbud
Ingen faktaændring efter fact-check. Ingen fremdatering. Ingen omgåelse af FAIL/MANUAL_REVIEW. Ingen direkte layout/CSS. Ingen direkte redigering af `docs/`. Ingen commit direkte til `main`. Ingen merge fra AI-agenten. Ingen automatisk lead bare fordi stykket netop blev udgivet. Ingen auto-publish-markør på system-, workflow-, script-, template- eller designændringer.

## Output
PR_READY med PR-URL, planlagt umiddelbar publicering, story_id og gate-summary; derefter afventer GitHub Actions. LIVE må først rapporteres, når PR er merged, build er grønt og live-sitet er verificeret. Ellers STOP med årsag.
