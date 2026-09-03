# Husregler — Morgentidendes forfatning

Dette er repoets øverste regelsæt. Specialistfiler, agentprompts, workflows og scripts må ikke modsige det.

## Én regel → én ejer → én canonical fil

Ved konflikt gælder denne rækkefølge:

1. `HUSREGLER.md` — tværgående principper og stopregler
2. `EDITORIAL.md` — redaktionel linje, presseetik og fairness
3. `SOURCES.md` — kilder, evidens og faktaledger
4. `STYLE.md` — sprog og rubrikstil
5. `MEDIA_SOURCES.md` — media, ophav og licens
6. `DESIGN.md` — fælles design
7. `CATEGORIES.md` — kategorier
8. `SCHEDULE.md` — timing og planlagt stof
9. `FRONTPAGE.md` — lead og placering
10. `AGENTS.md` — roller, rækkefølge og fejl-routing
11. øvrige specialdokumenter

En lavere fil må ikke genindføre en regel, som en højere fil har ophævet. Samme beslutning må ikke have flere ejere.

## Hard stops

En ny artikel må ikke publiceres, hvis:

- dens bærende claims ikke er dokumenteret efter `SOURCES.md`;
- Fact checker ikke har PASS på de claims, artiklen bruger;
- artikel og kommentar er blandet sammen;
- en reel etik-/fairnessrisiko ikke er løst;
- media er misvisende eller brugsretten er utilstrækkeligt afklaret;
- Slutredaktørens final approval mangler eller ikke matcher den aktuelle redaktionelle version;
- publiceringstidspunktet er forkert eller opdigtet;
- historien reelt kun er en dublet uden selvstændig nyhedsværdi.

SEO, forsideplacering, analytics, rapportering, coverage-metadata, source-group-kvoter og almindelige design/UI-forhold må ikke blive selvstændige redaktionelle publiceringsgates.

Tom plads er bedre end et usikkert eller dårligt stykke. Volumen må aldrig tilsidesætte kvalitet.

## Evidens

`SOURCES.md` ejer alle detaljer om evidens. Grundreglen er, at **én relevant autoritativ kilde kan være tilstrækkelig til et konkret claim**, når kilden faktisk dokumenterer claimet inden for sit kompetence- eller vidensområde. Flere kilder bruges for pluralisme, mod-evidens, aktualisering eller nødvendig ekstra sikkerhed — ikke som mekanisk minimum.

AI-output er aldrig en kilde.

## Fairness

`EDITORIAL.md` ejer de detaljerede presseetiske regler. Omstridte eller alvorlige beskyldninger må ikke skrives som fastslåede fakta uden dokumentation. Juridisk status skal være præcis, relevant usikkerhed skal stå tæt på oplysningen, og kendte relevante benægtelser eller forklaringer gengives loyalt.

Fairness/right-of-reply er en redaktionel vurdering hos Etik/fairness — ikke en automatisk ventetid eller deadline-gate. Rubrik, manchet, billedtekst og teaser må aldrig være stærkere end dokumentationen.

## Avis-motoren

Den canonical rækkefølge og fejl-routing står i `AGENTS.md`.

Principper:

- Scan og teknisk filtrering skal være så billigt/deterministisk som muligt.
- Research indsamler evidens; Fact checker er eneste ejer af claim-verifikation.
- Journalist skriver kun fra verificerede claims.
- Sprog reparerer sprog uden at genresearche.
- Media ejer billede/video/illustration og brugsret.
- Etik/fairness er betinget og aktiveres ved konkret risiko, ikke som obligatorisk ekstra AI-kald på alt stof.
- Slutredaktør ejer samlet publicerbarhed og endelig kategori.
- Release accepterer et gyldigt Fact checker-PASS + et versionsmatchende final approval; release må ikke genfortolke specialistgates.
- Forsiden placerer allerede publicerbare historier og må aldrig blokere publicering.

## Maksimum tre artikel-forsøg

En artikel må have højst **tre redaktionelle artikelversioner/forsøg** i slutfasen. Efter tredje mislykkede version droppes artiklen.

Et nyt artikel-forsøg betyder ikke en fuld genkørsel af kæden. Fejl sendes kun til nærmeste ejer:

- sprog → Sprog;
- tekst ud over verificerede claims / forkert attribution → Journalist;
- manglende eller tvivlsom evidens → Research/Fact checker;
- fairness/etik → Etik/fairness, og kun den konkrete evidensmangel videre til Research;
- media → Media;
- kategori → Slutredaktør;
- SEO/metadata/forside → deterministisk repair/fallback.

Tidligere verificeret arbejde genbruges. Ingen artikel må loope ubegrænset eller starte forfra alene fordi et sent led finder en lokal fejl.

## Versionsbinding

Nye autopublicerbare artikler bruger `pipeline_version: 2`. Slutredaktørens approval i `reports/editorial/approvals/<slug>.json` bindes til den godkendte redaktionelle version.

Efter approval må release/build ændre tekniske publicerings- og placeringsmetadata uden ny redaktionel approval. Ændres materielt redaktionelt indhold, kræves nyt final approval.

## Media, forside og design

- `MEDIA_SOURCES.md` er eneste detaljerede sandhedskilde for media og licens. Genereret materiale må aldrig fremstilles som dokumentarfoto.
- `FRONTPAGE.md` er eneste detaljerede sandhedskilde for lead, ticker, artikelpakker og placering. Forsidestrategi er ikke en gate.
- `DESIGN.md` ejer fælles UI/design. Artikelproduktion må ikke ændre fælles templates/CSS/theme som bivirkning af en artikel.
- Der findes ingen kategori `Politik`; politisk nyhedsstof placeres i relevant eksisterende kategori, typisk Indland eller Udland.

## Rettelser og transparens

Materielle fejl rettes åbent efter `CORRECTIONS.md`. Byline, ophav og offentlige oplysninger om redaktionel metode må ikke være falske eller opdigtede.

## Simplificering og økonomi

Repoet skal foretrække den enkleste arkitektur, der bevarer nødvendig journalistisk, juridisk og teknisk sikkerhed:

- én ejer pr. beslutning;
- ingen dublerede eller skjulte gates;
- ingen historiske procesfiler som parallelle sandhedskilder;
- lokal reparation frem for fuld genkørsel;
- billig model/deterministisk kode før dyr model, når kvaliteten kan bevares;
- fail-open for ikke-kritisk analytics, rapportering og præsentationsmetadata;
- mål AI-forbrug pr. faktisk godkendt/publiceret artikel, ikke bare råt totalforbrug.
