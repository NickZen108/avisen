# Agenter — Morgentidende

Alle agenter læser først `HUSREGLER.md` og følger prioriteten dér. En agent må markere sin egen opgave som færdig, men må ikke alene gøre sit eget arbejde publiceringsklart eller ophæve et FAIL.

## Pipeline

1. **Scan** — finder signaler og kandidater. Skriver ikke artikler.
2. **Nyhedsdesk / assignment** — deduplikerer, tildeler `story_id`, kategori, vægt og researchopgave. Kan KILL/HOLD.
3. **Research** — udfører coverage sweep og bygger faktaledger/kildememo. Ingen artikelprosa.
4. **Fact checker** — falsificerer researchen, åbner originalkilder, kontrollerer claims, uafhængighed, citater, tal og målrettet mod-evidens. PASS/FAIL.
5. **Nyhedsdesk / recheck** — ser på det faktiske dokumenterede resultat og vælger `PUBLISH`, `UPDATE`, `HOLD` eller `KILL`. Historien er ikke automatisk værd at skrive, bare fordi den var værd at researche.
6. **Journalist** — skriver kun ud fra PASS-ledger og recheck.
7. **Sprogredaktør** — dansk, klarhed og overskrift. Må ikke ændre fakta.
8. **Etik/fairness** — forelæggelse, identifikation, børn, skade, fairness og nyhed/kommentar. Kan kræve manual review.
9. **Billedredaktør** — match, ophav, licens, autenticitet, grafik og alt-tekst.
10. **SEO/discovery** — metadata, schema, delingsmetadata og intern linking efter billedvalget. Må ikke styre fakta/vinkel.
11. **Slutredaktør** — uafhængigt anden-tjek af hele den færdige redaktionelle version mod ledger og tidligere gates. Retter ikke ved PASS; opretter final approval snapshot.
12. **Forsideredaktør** — vælger lead og placering. Pipeline-v2-artikler refereres normalt kun med `slug`.
13. **Teknisk QA** — schema, links, canonical frontpage refs, generated-only HTML, design lock, build, tider og sitemaps.
14. **Udgiver** — ændrer kun publiceringsmetadata og afleverer newsroom-PR. Sætter ikke selv en opdigtet live-tid.
15. **Live technical QA** — GitHub-kontrol af live forside, netop ændrede/recent artikler, links/assets og template-markers.
16. **Live proofreader** — læser renderet artikel/forside for sproglige eller visuelle fejl og sammenholder med canonical indhold.
17. **Redaktionel update-monitor** — leder efter nye oplysninger, der kan ændre claims, artikel eller forsidevægt.

Ved materiel fejl: Post-publication incident → Fact checker genåbner claims → Correction editor → relevante fag-gates → Slutredaktør → Udgiver → offentlig rettelseslog.

## Pipeline v2

Alle nye autopublicerbare artikler skal have `pipeline_version: 2`.

Research udfylder `coverage_sweep` i ledgeren. Fact checker udfylder `fact_check`. Nyhedsdesk udfylder `desk_recheck`. Før publicering opretter Slutredaktør `reports/editorial/approvals/<slug>.json`.

Approval-filen indeholder:
- `status: pass`
- story/slug
- tidspunkt
- status for language, ethics, image, seo og final_editor
- et snapshot af artikelens redaktionelle felter

Quality gate sammenholder snapshot og nuværende artikel efter at rent tekniske/publiceringsfelter er fjernet. Ændres journalistisk indhold bagefter, bliver approval ugyldig.

## Leveringsvej

Et nyt autopublicerbart stykke afleveres sådan:

1. Arbejd på `edition/*` eller `newsroom/*` fra seneste `main`.
2. Research/Fact check/Nyhedsdesk recheck færdiggøres.
3. Journalist → Sprog → Etik → Billede → SEO.
4. Slutredaktør opretter final approval snapshot.
5. Forsideredaktør opdaterer eventuelt `content/frontpage.json` med canonical slug-reference.
6. Teknisk QA køres.
7. Udgiver sætter ved umiddelbar publicering `status: ready` og `release_requested: true`; `published_at` forbliver tom.
8. PR mod `main` har titel `[AUTO] ...` og body-markøren `<!-- morgentidende-auto-publish -->`.
9. Quality gates tester det præcise PR-head. Auto-publish merge accepterer kun pipeline-v2-artikler fra eget repo og allowlisten.
10. Efter merge sætter GitHub release-tidspunktet, bygger public-output og kører live-kontrol.

Ved planlagt stof sætter Udgiver kun planlægningsmetadata; faktisk `published_at` sættes ved release.

Højrisiko, `manual_review: true`, regelændringer, designændringer, workflows, scripts og andre systemændringer må aldrig bruge auto-publish-markøren.

## Stopregler

Fejl omfatter blandt andet:

- artikel uden godkendt ledger
- coverage sweep markeret PASS med færre end tre reelt uafhængige source-groups
- samme bureau/pressemeddelelse talt flere gange
- Fact check PASS uden desk recheck `publish|update`
- pipeline-v2-artikel uden matching final approval
- påkrævet forelæggelse uden kontakt/fristsvar eller dokumenteret undtagelse
- v2-forsidepost der kopierer titel/teaser/billede i stedet for canonical slug-reference
- højrisikostof autopubliceret
- fremtidigt/opdigtet publiceringstidspunkt
- auto-publish-PR der ændrer scripts, workflows, templates eller design

## Prompts

Operative prompts ligger i `agents/`, herunder:
`newsdesk.md`, `research.md`, `fact-check.md`, `journalist.md`, `language.md`, `ethics.md`, `image.md`, `seo.md`, `final-editor.md`, `frontpage.md`, `technical-qa.md`, `publisher.md`, `live-proofreader.md`, `post-publication.md` og `correction-editor.md`.
