# Workers AI neuron- og stabilitetsoptimering — 2026-09-01

## Mål
Minimér Workers AI-neurons pr. redaktionel cyklus uden at sænke journalistisk kvalitet, publiceringskapacitet eller driftsstabilitet.

## Hovedfund
Den største omkostning var ikke billedgenerering, men at alle strukturerede teksttrin brugte `@cf/meta/llama-3.3-70b-instruct-fp8-fast`. En artikel kunne derfor udløse 6–8 70B-kald: Newsdesk, Research, Fact check, desk recheck, Journalist, Final Editor og ved behov revision + ny Final Editor.

Cloudflares aktuelle prisside angiver 70B-modellen til 26.668 neurons pr. million inputtokens og 204.805 pr. million outputtokens. Den aktive 8B-fast-variant ligger i den billige fast-klasse omkring 4.119 neurons pr. million inputtokens og 34.868 pr. million outputtokens. Det gør lavrisiko-kald omtrent seks gange billigere i compute-klassen end 70B, før øvrige forskelle i faktisk tokenforbrug.

Kilder:
- https://developers.cloudflare.com/workers-ai/platform/pricing/
- https://developers.cloudflare.com/workers-ai/features/json-mode/
- https://developers.cloudflare.com/workers-ai/models/llama-3.1-8b-instruct-fast/
- https://developers.cloudflare.com/workers-ai/models/llama-3.3-70b-instruct-fp8-fast/
- https://developers.cloudflare.com/workers-ai/features/prompt-caching/

## Ændringer implementeret

### 1. To modelklasser i stedet for én
**Billig/fast model:** `@cf/meta/llama-3.1-8b-instruct-fast`

Bruges til:
- første Newsdesk-assignment
- Research-udtræk og strukturering
- desk recheck
- målrettet reparation af sprog/SEO/image-prompt

**Stærk model:** `@cf/meta/llama-3.3-70b-instruct-fp8-fast`

Bevares til:
- uafhængig Fact checker
- journalistisk artikeltekst
- uafhængig Final Editor

Det er bevidst: de dyreste kald er bevaret dér, hvor en svagere model potentielt kan koste faktuel præcision eller journalistisk kvalitet.

### 2. Fail-safe modelrouting
8B-kald har 70B som fejl-fallback. Hvis billigmodellen ikke kan levere et parsebart schema-output, falder cyklussen tilbage til den stærke model i stedet for at bryde produktionsflowet.

Cloudflare dokumenterer JSON Mode for begge valgte modeller, men gør samtidig opmærksom på, at schemaoverholdelse ikke kan garanteres i alle tilfælde. Derfor er fallbacken vigtig for stabilitet.

### 3. Kortere outputbudgetter
Maksimum-output er sænket, uden at schemas eller journalistiske krav er reduceret:
- Newsdesk: 1600 → 900
- Research: 3000 → 2200
- Fact checker: 3000 → 2400
- desk recheck: 700 → 450
- Journalist: 3800 → 3000
- Final Editor: 1400 → 900
- målrettet revision: 3000 → 2400

`max_tokens` er kun et loft, men lavere lofter begrænser kostbare runaway-/overforklarende outputs og gør agenternes opgave mere fokuseret.

### 4. Newsdesk får færre, men bedre kandidater
Et vigtigt QA-fund var, at scannerens samlede signaler blev alfabetisk sorteret, hvorefter AI'en fik de første 100. Det betød, at Newsdesk kunne bruge neurons på et tilfældigt alfabetisk udsnit i stedet for de friskeste/stærkest dækkede historier.

Nu foretages en deterministisk, gratis shortlist før AI-kaldet:
- fler-kilde-clusters prioriteres
- høj placering i det enkelte feed prioriteres
- publiceringstid bruges, når feedet leverer den
- maks. seks kandidater fra samme kilde
- højst 40 kandidater sendes til Newsdesk
- beskrivelser er kortet ned fra 500 til 360 tegn i dette trin

Dette reducerer input samtidig med, at kandidatpuljen bliver mere nyhedsrelevant og kildebred.

### 5. Kildevalg begrænset til seks pr. historie
Newsdesk kan højst sende seks signaler videre. Det holder Research/Fact-check-context inden for stærkmodellens vindue og reducerer unødvendig inputmængde. Det ændrer ikke kravet om kildeuafhængighed eller faktadækning.

### 6. Billedmodellen er beholdt
`@cf/black-forest-labs/flux-1-schnell` er allerede meget billig i neuronregnskabet sammenlignet med LLM-output. Billedet genereres først efter Final Editor PASS. Derfor er der ingen gevinst ved at ofre billedkvalitet eller fjerne billeder for at spare neurons.

## Gates som IKKE er fjernet eller svækket
- Research og Fact checker er fortsat separate roller/kald.
- Fact checker er fortsat stærk model.
- mindst to verificerede bærende claims kræves til normal kort nyhed.
- kildeuafhængighed kontrolleres deterministisk efter Fact checker.
- forelæggelse/etik er fortsat hard stop.
- Journalist må fortsat kun skrive fra verificerede claims.
- Final Editor er fortsat separat stærk model.
- en ændret slutversion kræver fortsat ny slutvurdering.
- hero genereres først efter redaktionelt PASS.

## Optimeringer undersøgt, men ikke aktiveret endnu

### Skifte stærkmodel til en nyere billigere model
Cloudflare har nyere modeller med markant lavere unit pricing, fx `@cf/openai/gpt-oss-20b`, `@cf/google/gemma-4-26b-a4b-it` og `@cf/qwen/qwen3-30b-a3b-fp8`. Nogle har attraktiv reasoning-/structured-output funktionalitet og lavere outputpris end Llama 70B.

De er **ikke** sat ind i Fact checker/Journalist/Final Editor endnu. Pris alene er ikke tilstrækkelig dokumentation for samme journalistiske kvalitet, og dagens gratis neuronkvote er opbrugt, så vi kan ikke lave en ordentlig parallel A/B-evaluering nu. Før et sådant skifte skal modellerne testes blindt på samme sæt historier mod nuværende 70B og de deterministiske gates.

### AI Gateway response caching
AI Gateway kan cache identiske requests. Det er nyttigt for retries og statiske workloads, men nyhedsresearch er dynamisk, så bred caching kan give stale svar. Derfor aktiveres det ikke ukritisk som generel løsning.

### Prefix/prompt caching
Cloudflare anbefaler statiske instruktioner først og dynamisk indhold bagefter; pipelineprompts er allerede bygget sådan. Prefix caching kan give yderligere besparelse på understøttede modeller. Vi bør måle `usage`/cached-token-data efter kvotereset, før vi regner en besparelse ind i kapacitetsplanen.

### Færre redaktionelle roller
Ikke anbefalet. At slå Research og Fact checker sammen eller fjerne Final Editor ville spare kald, men det ville direkte svække den uafhængighed, QA'en netop er designet til at bevare.

## Forventet effekt
De lavrisiko-kald, der nu bruger 8B-fast, ligger i en compute-prisklasse omkring 6× under 70B for både input og output. Samtidig er Newsdesk-input reduceret kraftigt og outputlofter er sænket. Den samlede besparelse pr. færdig artikel kan derfor blive betydelig, men der angives ikke et falsk præcist procenttal, før vi har faktiske usage-data fra nye komplette cyklusser efter kvotereset.

## Test og drift
- Den optimerede Worker er deployed via normal Cloudflare Newsdesk-deploy.
- Smoke-test af `/health`, `/candidates` og `/editorial/latest` består.
- Repository Quality Gates består efter ændringen.
- Fuld artikel-A/B og faktisk neurons/artikel kan først måles, når Workers AI igen tillader inferens eller Paid aktiveres.

## Næste målepunkt
Efter kvotereset bør 10–20 komplette redaktionelle cyklusser måles på:
1. input/outputtokens pr. agent
2. estimerede/rapporterede neurons pr. agent og pr. godkendt artikel
3. 8B→70B fallback-rate
4. andel artikler der bliver blokeret pr. stage
5. faktuelle/finale QA-fejl sammenlignet med tidligere 70B-only pipeline
6. publicerede artikler pr. 10.000 neurons

Et stærkmodelskifte bør kun ske, hvis en blind A/B-test viser mindst samme faktuelle sikkerhed, dansk sproglig kvalitet og Final Editor-resultat.