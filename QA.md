# Kvalitetskontrol

QA består af både deterministiske tests og selvstændige redaktionelle gates. Et grønt build er nødvendigt, men ikke tilstrækkeligt til publicering.

## 1. Fakta

- hver publiceret struktureret artikel har en faktaledger
- ledgeren indeholder claim-id, kilde, dato, source-group og status
- tal, navne, datoer, embeder og direkte citater er særskilt verificeret
- to URLs fra samme bureau/pressemeddelelse tæller ikke som to uafhængige kilder
- `manual_review: true` må ikke autopubliceres

## 2. Dansk

Sprog-gaten kontrollerer hele sætninger, ikke blot ordbogsopslag. Retskrivningsordbogen er reference; legitime sammensætninger, bøjningsformer, egennavne og fagord kan være korrekte uden selvstændigt opslag.

Kontrollér H1, title, manchet, brødtekst, ticker og teasere for:

- stave- og grammatikfejl
- brudte sætninger
- maskinoversættelsesdansk og anglificering
- mærkelige opdigtede ord
- forkert juridisk status
- ændret betydning efter sproglig omskrivning

## 3. Design og generering

- nye artikler skal komme fra `content/articles/`
- genereret HTML skal have generated-marker
- nye direkte håndskrevne HTML-artikler er FAIL
- låste designfiler skal matche `config/design-lock.txt`
- journalistiske commits må ikke ændre CSS/logo/layout

## 4. Metadata og tid

- én H1
- én gyldig kategori
- canonical URL
- korrekt `lang=da`
- publiceringstid = faktisk live-tid; ingen fremtid
- `updated_at` kun ved substantiel opdatering
- NewsArticle/Article-schema svarer til genren
- meta description er beskrivende, ikke clickbait

## 5. Links og billeder

Hvert link og billede på live forside samt aktuelle artikler skal kunne hentes. Dødt foto er FAIL. Tematisk match alene er ikke nok.

Billedgate kontrollerer desuden:

- motiv passer til overskrift/sted/tid
- ophav og licens er registreret
- alt-tekst beskriver motivet
- generativ illustration er tydeligt mærket og ikke brugt som dokumentarfoto

## 6. Story clusters

- ingen unødvendige dublet-URLs
- kommentar om aktuel sag har `related_news_slug`
- nyhed og kommentar linker begge veje
- kanonisk artikel opdateres ved samme fortsættende hændelse

## 7. Post-publication

Post-publication monitor kører regelmæssigt og rapporterer:

1. døde links og billeder
2. build-/markupfejl
3. utilsigtede interne noter
4. rettelser eller nye fakta, der ændrer artikelens præmis
5. forside der har et forældet lead

Materielle fejl håndteres efter `CORRECTIONS.md`; de rettes ikke stille.

## Rapporter

Teknisk/visuel QA skriver til `reports/qa/`. Rapporten må ikke opfinde metrics eller erklære PASS på checks, den ikke faktisk har kørt.
