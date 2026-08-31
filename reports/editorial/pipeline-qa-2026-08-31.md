# Redaktionel pipeline-QA — 31. august 2026

## Mål
Bevar hårde gates for fakta, etik, rettigheder og final approval, men fjern unødige stop, falske gates, rolleforvirring og tekniske deadlocks.

## Nuværende hovedflow
Scan → Newsdesk assignment → Research → Fact check → Newsdesk recheck → Journalist → Sprog → Etik/fairness → Billede/Video → SEO → Slutredaktør → Forsideredaktør → Teknisk QA → Udgiver → live QA → live proofreader → update monitor.

Cloudflare-runtime udfører flere af disse roller i færre tekniske kald, hvorefter GitHub-gates validerer canonical artikel, ledger og approval.

## Kritiske fund og rettelser udført

### 1. Kildekravet lå for tidligt i flowet
Newsdesk-runtime krævede allerede tre forskellige kilder, før historien overhovedet måtte gå til Research. Det gjorde Research-trinnet delvist meningsløst og kunne bremse breaking eller historier, hvor tredje dækning først kommer senere.

**Rettet:** Assignment må nu sende en stærk historie til Research uden tre færdige kilder. Research søger bredde. Automatisk publicering kræver stadig mindst to uafhængige kilder for materielle publicerede claims, mens coverage med to source-groups markeres `limited` i stedet for automatisk stop.

### 2. Tre verificerede claims var et kunstigt volumekrav
En enkel nyhed med to stærke, dokumenterede hovedfakta blev tidligere holdt alene fordi runtime krævede mindst tre materielle claims med dobbelt kildeunderstøttelse.

**Rettet:** To solide bærende claims er nok til et kort nyhedsstykke. Der må ikke opfindes ekstra claims for at opfylde et antal.

### 3. Newsdesk recheck var ikke et rigtigt recheck
Ledgeren fik `desk_recheck: publish`, men begrundelsen blev i praksis genbrugt fra det oprindelige assignment. Dermed så pipeline ud til at have et separat efter-fact-check-tjek uden faktisk at have det.

**Rettet:** Runtime har nu et særskilt, kort Newsdesk-recheck efter Fact checker. Det må ikke genresearche; det vurderer kun om det dokumenterede resultat stadig er aktuelt og publiceringsværdigt.

### 4. Final approval kunne blive ugyldig af rent recovery-metadata
`release_ready.py` betragtede `workflow_state` som teknisk metadata, mens `pipeline_v2_gate.py` regnede det med i det redaktionelle snapshot. En artikel kunne derfor få mismatch alene fordi recovery-systemet skrev en teknisk stopårsag.

**Rettet:** `workflow_state` er nu konsekvent uden for det redaktionelle approval-snapshot.

### 5. Manual review kunne forblive permanent blokeret efter afslutning
Recovery-diagnosen stoppede på `manual_review: true` uden at tage højde for `manual_review_completed`.

**Rettet:** Kun uafsluttet manual review blokerer.

### 6. Recovery routede for groft til Slutredaktøren
Hvis approval-filen fandtes men fx language/image/SEO-gaten manglede PASS, blev alt routet til `final_editor`.

**Rettet:** Recovery kan nu route specifikt til `language`, `ethics`, `image`, `seo` eller `final_editor`.

### 7. Rolleforvirring: Slutredaktør vs. Udgiver
Recovery-instruksen sagde, at Slutredaktøren skulle sætte `ready/release_requested`, mens den øvrige arkitektur korrekt reserverer publiceringsmetadata til Udgiver.

**Rettet:** Slutredaktør opretter approval; Udgiver sætter release-status.

### 8. Runtime brugte gamle kategorier
Cloudflare-runtime havde stadig bl.a. `Nyhed`, `Økonomi`, `Forbruger`, `Kultur`, `Videnskab` og `Parforhold`, selv om hovedkategorierne var ændret.

**Rettet:** Runtime bruger nu Danmark, Udland, Politik, Penge, Krimi, Videnskab & teknologi, Sundhed, Kultur & medier, Sport og Liv.

### 9. Små reparerbare fejl blev til fuldt stop
Final review stoppede artiklen ved fx et sprogligt, SEO- eller hero-promptproblem, selv om problemet kunne rettes uden at ændre fakta.

**Rettet:** Runtime må lave én målrettet revision af kun `language`, `seo` eller `image`-promptproblemer og derefter køre et nyt uafhængigt final review. Etik- eller materielle final-editor-problemer må ikke auto-rettes på denne måde.

### 10. Lægmandssprog kom for sent ind
Readability-gaten i GitHub kunne opdage fagsprog efter runtime havde færdiggjort artiklen, hvilket kunne skabe et unødigt recovery-loop.

**Rettet:** Journalist-prompten kræver nu lægmandssprog, forklaring af nødvendige fagtermer og metriske/danske enheder allerede ved første skrivning. GitHub-readability-gaten bevares som sikkerhedsnet.

### 11. En ufærdig artikel kunne stoppe hele avisen
Global `quality_gate.py` validerede også artikler med status `draft`, `researching`, `checking` og `editing` som om de forsøgte at blive publiceret. Under QA blev en koral-historie korrekt parkeret af recovery-systemet, men hele buildet fejlede bagefter, fordi dens ledger endnu ikke fandtes.

**Rettet:** Arbejdsstykker må nu være ufuldstændige uden at blokere resten af avisen. Deres mangler spores i pipeline-health/recovery. De hårde globale publiceringsgates starter først ved `ready`, `scheduled` eller `published`. En ufærdig artikel kan derfor ikke længere holde andre færdige artikler tilbage.

## Redundansvurdering

- **Research vs Fact check:** Begge er nødvendige, men Fact checker må kun challenge/falsificere det allerede indsamlede grundlag og ikke genresearche hele historien. Dette er nu tydeligere, men Cloudflare-runtime udfører dem stadig i samme AI-kald. Det er funktionelt hurtigt, men mindre uafhængigt end den ideelle rollemodel.
- **Fact check vs Slutredaktør:** Begge beholdes. Slutredaktøren skal ikke gentage hele fact check; den kontrollerer den færdige tekst mod ledgeren og stikprøver bærende claims.
- **Sprog vs readability gate:** Sprogredaktør/Journalist forebygger; readability-gate er deterministisk sikkerhedsnet. Ikke unødvendig dublet.
- **Teknisk QA før publicering vs live QA:** Begge nødvendige. Første kontrollerer build/canonical/schema; anden kontrollerer den faktiske live-rendering.
- **Live QA vs live proofreader:** Forskellige formål: teknik vs læseroplevelse/sprog. Behold begge, men live proofreader skal kun åbne nyligt ændrede sider.

## Resterende strukturelle forbedringer

1. **Uafhængig Fact checker-call i Cloudflare.** Ideelt bør Research og Fact checker være to separate modelkald. Det giver stærkere rolleuafhængighed, men koster ekstra latency/AI-forbrug. Anbefales som næste kvalitetsforbedring, ikke som blocker for drift.
2. **Billedkontrol efter generering.** Runtime vurderer hero-prompten før Flux-generering, men har ikke en semantisk vision-gate på det faktiske genererede billede. Teknisk billed-QA fanger dimensioner/assets, ikke altid forkert motiv. Bør tilføjes, hvis en egnet visionmodel kan køres stabilt.
3. **Right-of-reply recovery.** Når forelæggelse kræves, stopper runtime korrekt. Der mangler dog stadig et fuldt automatisk workflow til at registrere kontakt, deadline og svar. Dette bør forblive en hård blocker indtil et sikkert workflow findes.
4. **Mål på pipeline-friktion.** Kontrolrummet bør gemme stop pr. stage, median tid i hver stage, antal auto-reparerede stop og gentagne stopårsager, så vi kan optimere på faktisk drift frem for mavefornemmelse.

## Princip efter QA
En hård blocker skal beskytte mod en reel journalistisk, juridisk eller teknisk risiko. Manglende pynt, et kunstigt antal kilder/claims eller rent teknisk recovery-metadata må ikke alene holde en ellers forsvarlig artikel tilbage.
