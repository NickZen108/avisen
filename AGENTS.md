# Agenter — Morgentidende

Alle agenter følger `HUSREGLER.md`. Hver redaktionel beslutning skal have én tydelig ejer; senere agenter må ikke rutinemæssigt gentage tidligere agenters arbejde.

## Pipeline

1. **Scan** — billig bred radar: finder, normaliserer og grupperer signaler. Skriver ikke artikler og vurderer ikke endelig nyhedsværdi.
2. **Nyhedsdesk / assignment** — vælger research-frø, tildeler `story_id`, kategori og foreløbig vægt. Er bevidst relativt åben ved indgangen; tynd dokumentation er Researchs problem.
3. **Research** — finder og strukturerer den nødvendige evidens til historiens bærende claims. Ingen artikelprosa og ingen endelig sandhedsdom. Der er intet globalt krav om tre medier eller tre source-groups.
4. **Fact checker** — forsøger uafhængigt at falsificere researchen og afgør, hvilke claims der er dokumenterede. PASS/FAIL-regler afhænger af claimets og historiens risiko; dette er den primære faktuelle gate.
5. **Nyhedsdesk / recheck** — B-D går normalt deterministisk videre efter Fact checker PASS. Kun A/breaking får et kort recheck for materiel forældelse eller ændret nyhedskerne.
6. **Journalist** — skriver kun ud fra godkendte claims.
7. **Sprogredaktør** — dansk og klarhed. Må ikke ændre fakta.
8. **Etik/fairness** — forelæggelse, identifikation, børn, skade, fairness og nyhed/kommentar. Kan kræve manual review.
9. **Billedredaktør** — match, ophav, licens, autenticitet, grafik og alt-tekst.
10. **Videoredaktør** — finder/verificerer embeds og autentisk hændelsesvideo.
11. **SEO/discovery** — metadata, schema, delingsmetadata og intern linking. Må ikke styre fakta/vinkel.
12. **Slutredaktør** — kontrollerer den færdige version mod de tidligere godkendelser. Skal ikke genresearche eller gentage Fact checker.
13. **Forsideredaktør** — vælger lead og placering.
14. **Teknisk QA** — schema, links, canonical refs, generated-only HTML, build, tider og sitemaps.
15. **Udgiver** — ændrer publiceringsmetadata og afleverer newsroom-PR.
16. **Live technical QA** — kontrollerer live output, links/assets, embeds og template-markers.
17. **Live proofreader** — læser renderet artikel/forside for konkrete sproglige eller visuelle fejl.
18. **Redaktionel update-monitor** — leder efter nye oplysninger, der materielt kan ændre en allerede publiceret historie.

Ved materiel fejl: Post-publication incident → Fact checker genåbner relevante claims → Correction editor → kun relevante fag-gates → Slutredaktør → Udgiver → offentlig rettelseslog.

## Grundprincipper for effektivitet

- **Én ejer pr. beslutning:** nyhedsværdi = Nyhedsdesk; evidensindsamling = Research; faktuel verifikation = Fact checker; fairness/forelæggelse = Etik; sprog = Sprogredaktør; placering = Forsideredaktør; teknik = QA.
- **Billigt først:** deterministisk kode, metadata og simple regler før AI-kald.
- **Progressiv strenghed:** Scan og Nyhedsdesk skal være åbne; kravene bliver strengere tættere på publicering og ved højere risiko.
- **Risiko frem for universelle minimumskrav:** simple officielle fakta kan kræve én stærk primærkilde; alvorlige, omstridte eller højrisiko-påstande kræver mere uafhængig dokumentation.
- **Ingen kildekvoter for deres egen skyld:** stop research, når bærende claims er tilstrækkeligt belyst. Flere medier med samme bureau/pressemeddelelse tæller som samme ophav.
- **Soft flags er ikke hard gates:** tvivl, forelæggelsesbehov og manglende sekundær dækning skal routes til den relevante senere gate frem for automatisk at dræbe historien.
- **Genbrug kompakte strukturer:** send claims, kildeindeks og nødvendige uddrag videre; undgå at sende samme fulde kontekst til flere modeller uden grund.
- **Stærk model er undtagelsen:** brug billig model normalt; eskalér kun ved reel kompleksitet, høj risiko eller teknisk fallback.

## Pipeline v2

Alle nye autopublicerbare artikler skal have `pipeline_version: 2`.

Research udfylder et kompakt evidens-/coverage-overblik i ledgeren. Coverage beskriver dokumentationen; et bestemt antal source-groups er ikke i sig selv et PASS-krav. Fact checker udfylder `fact_check`. Nyhedsdesk udfylder `desk_recheck`, som for B-D kan være deterministisk efter Fact checker PASS. Før publicering opretter Slutredaktør `reports/editorial/approvals/<slug>.json`.

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
2. Research og Fact check færdiggøres; kun A/breaking behøver normalt et aktivt Nyhedsdesk-recheck.
3. Journalist → Sprog → Etik → Billede/Video → SEO.
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

Hard stops skal være få og konkrete. De omfatter blandt andet:

- artikel uden godkendte bærende claims
- samme bureau/pressemeddelelse fejlagtigt talt som flere uafhængige kilder, når uafhængighed er nødvendig
- A/breaking der kræver recheck, men mangler `publish|update`
- pipeline-v2-artikel uden matching final approval
- påkrævet forelæggelse uden kontakt/fristsvar eller dokumenteret undtagelse
- v2-forsidepost der kopierer titel/teaser/billede i stedet for canonical slug-reference
- højrisikostof autopubliceret
- fremtidigt/opdigtet publiceringstidspunkt
- auto-publish-PR der ændrer scripts, workflows, templates eller design

Et universelt minimum på to claims, tre kilder eller tre source-groups er ikke en hard stop. Dokumentationskravet skal passe til den konkrete påstand og risiko.

## Prompts

Operative prompts ligger i `agents/`, herunder:
`scan.md`, `newsdesk.md`, `research.md`, `fact-check.md`, `journalist.md`, `language.md`, `ethics.md`, `image.md`, `video.md`, `seo.md`, `final-editor.md`, `frontpage.md`, `technical-qa.md`, `publisher.md`, `live-proofreader.md`, `post-publication.md` og `correction-editor.md`.
