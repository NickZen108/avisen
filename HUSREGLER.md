# Husregler — Morgentidendes forfatning

Dette er repoets øverste regelsæt. Det fastlægger kun de tværgående principper, der ikke må kunne modsiges af specialistfiler, agentprompts, workflows eller scripts.

## Prioritet og ejerskab

Ved konflikt gælder denne rækkefølge:

1. `HUSREGLER.md` — tværgående principper og stopregler
2. `EDITORIAL.md` — redaktionel linje, presseetik og fairness
3. `SOURCES.md` — kilder, evidens og faktaledger
4. `STYLE.md` — sprog, rubrikker og redaktionel stil
5. `MEDIA_SOURCES.md` — billedkilder, licens og dokumentarisk media
6. `DESIGN.md` — fælles design og genereret HTML
7. `CATEGORIES.md` — kategorier og stofmix
8. `SCHEDULE.md` — udgivelsesrytme og timing
9. `FRONTPAGE.md` — lead, placering og artikelpakker
10. `AGENTS.md` + `agents/*.md` — roller og arbejdsdeling
11. `ARCHITECTURE.md`, `SEO.md`, `PRODUCT.md` og øvrige specialdokumenter

En lavere placeret fil må ikke genindføre en regel, som en højere placeret fil har ophævet. Samme beslutning skal have én ejer; andre led må ikke rutinemæssigt gentage den.

## Redaktionelle hard stops

En ny artikel må ikke publiceres, hvis:

- dens bærende faktuelle påstande ikke er dokumenteret efter `SOURCES.md`;
- Fact checker ikke har PASS på de claims, artiklen faktisk bruger;
- artikel og kommentar er blandet sammen;
- en reel etik-/fairnessrisiko ikke er løst;
- billedets relevans, ophav eller brugsret ikke er tilstrækkeligt afklaret;
- Slutredaktørens final approval mangler eller ikke matcher den aktuelle redaktionelle slutversion;
- publiceringstidspunktet er fremtidigt, opdigtet eller på anden måde forkert;
- historien reelt kun er en dublet uden selvstændig nyhedsværdi.

SEO, almindeligt design/UI, forsideplacering, coverage-metadata, source-group-kvoter og andre tekniske eller redaktionelle hjælpeprocesser må ikke blive selvstændige publiceringsgates.

Sprog, etik, media og slutredaktør er redaktionelle approval-led. Sprog og media kan forsøges op til tre gange; hvis problemet stadig ikke kan løses forsvarligt, droppes artiklen frem for at svække kravene.

Tom plads er bedre end et usikkert eller dårligt stykke. Ingen volumenregel kan tilsidesætte kvalitet.

## Evidens

`SOURCES.md` ejer alle detaljer om kilder og evidens.

Grundreglen er, at **én relevant autoritativ kilde kan være tilstrækkelig til et konkret claim**, når kilden faktisk dokumenterer det inden for sit kompetence- eller vidensområde. Flere kilder bruges, når de tilfører pluralisme, mod-evidens, aktualisering eller nødvendig ekstra sikkerhed — ikke som mekanisk minimum.

AI-output er aldrig en kilde.

## Fairness og følsomme oplysninger

`EDITORIAL.md` ejer de detaljerede presseetiske regler.

Omstridte eller alvorlige beskyldninger må aldrig skrives som fastslåede fakta uden dokumentation. Juridisk status skal være præcis, usikkerhed skal stå tæt på den relevante oplysning, og kendte relevante benægtelser eller forklaringer skal gengives loyalt.

Fairness/right-of-reply er en redaktionel vurdering hos Etik/fairness — ikke en automatisk ventetid eller særskilt deadline-gate.

Overskrift, manchet, billedtekst og teaser må aldrig være stærkere end dokumentationen.

## Ansvarsdeling

Kerneansvar:

- Scan finder signaler.
- Nyhedsdesk vælger historier og foreløbig kategori/vægt.
- Research indsamler evidens.
- Fact checker afgør faktuel verifikation.
- Journalist skriver teksten.
- Sprog ejer sproglig kvalitet.
- Etik/fairness ejer presseetiske risici og modpartsbehandling.
- Medieredaktør ejer billede/video, relevans, ophav og brugsret.
- Slutredaktør ejer samlet redaktionel publicerbarhed og endelig kategori.
- Forsideredaktør ejer placering, lead og artikelpakker blandt allerede publicerbare historier.
- Builder ejer genereret HTML/output.
- Post-deploy/live QA ejer kun faktisk live-funktionalitet.

Ingen rolle må alene gøre sit eget arbejde endeligt publiceringsklart. Specialistled må ikke overtage hinandens ansvar eller genkontrollere hele tidligere trin uden konkret grund.

## Pipeline og versionsbinding

Nye autopublicerbare artikler bruger `pipeline_version: 2`.

Slutredaktørens approval ligger i `reports/editorial/approvals/<slug>.json` og bindes til den godkendte redaktionelle version.

Efter approval må udgiver/build ændre tekniske publicerings- og placeringsmetadata uden ny redaktionel approval. Hvis titel, manchet, brødtekst, claims, faktuelt indhold, billede, byline, correction note eller andet materielt redaktionelt indhold ændres, skal Slutredaktøren godkende den nye version.

Gamle allerede publicerede artikler kan være grandfathered; det må ikke bruges som genvej for nye artikler.

## Media

`MEDIA_SOURCES.md` er eneste detaljerede sandhedskilde for billedkilder, licens og dokumentarisk media.

Overordnet gælder:

- brug gratis, lovligt og relevant dokumentarfoto, når det findes;
- et foto må aldrig fremstilles som dokumentation for en anden hændelse end den faktisk viser;
- genereret materiale må aldrig fremstilles som dokumentarfoto og registreres som illustration;
- uklare rettigheder betyder, at materialet ikke publiceres som foto;
- alt-tekst og nødvendig kredit/licensmetadata skal være korrekte.

Video og screengrabs følger samme princip om verificerbar kontekst, ophav og brugsret.

## Forside og opfølgninger

`FRONTPAGE.md` er eneste detaljerede sandhedskilde for lead, ticker, artikelpakker og forsideplacering.

Forsiden må kun rangere og placere historier, der allerede er publicerbare. Forsidestrategi må aldrig blive en publiceringsgate.

En opfølgning skal have selvstændig nyhedsværdi eller en tydelig funktion; den må ikke blot omskrive hovedartiklen. Relaterede historier kobles med de eksisterende relationfelter og præsenteres samlet efter `FRONTPAGE.md`.

## Design, sprog, kategorier og timing

Detaljer ejes af deres respektive specialistfiler:

- `STYLE.md` — sprog og rubrikstil
- `DESIGN.md` — fælles UI/design
- `CATEGORIES.md` — gyldige kategorier og stofmix
- `SCHEDULE.md` — udgivelsesrytme og planlagt stof
- `FRONTPAGE.md` — placering og lead

Artikelproduktion må ikke ændre fælles templates, CSS eller theme-filer som bivirkning af en enkelt artikel.

Der findes ingen kategori `Politik`; politisk nyhedsstof placeres i den relevante eksisterende kategori, typisk Indland eller Udland.

## Rettelser og transparens

Materielle fejl rettes åbent efter `CORRECTIONS.md`; de må ikke skjules gennem stille omskrivning eller falsk ny publiceringstid.

Byline, ophav og offentlige oplysninger om redaktionel metode må ikke være falske eller opdigtede.

## Simplificeringsregel

Repoet skal foretrække den enkleste arkitektur, der bevarer nødvendig journalistisk, juridisk og teknisk sikkerhed:

- én ejer pr. beslutning;
- ingen dublerede gates;
- ingen skjulte strengere regler i scripts end i de canonical dokumenter;
- ingen historiske procesfiler som parallelle sandhedskilder;
- fail-open for ikke-kritisk analytics, rapportering og præsentationsmetadata;
- lokal reparation eller lokal parkering frem for at stoppe hele avisen, når fejlen kun rammer ét stykke.
