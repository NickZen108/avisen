# Redaktørgate

Redaktøren er sidste redaktionelle veto før teknisk QA og udgivelse. Redaktøren må ikke erstatte specialist-gates; den kontrollerer, at de findes, og at stykket som helhed holder.

## Krævede PASS

Før redaktøren kan godkende, skal følgende være PASS eller dokumenteret ikke relevant:

- Newsdesk/assignment
- Research/faktaledger
- Fact check
- Journalist
- Sprog
- Etik/fairness
- SEO/discovery
- Billede

`manual_review: true` kan ikke ophæves automatisk.

## Afvis hvis

- research er tynd eller kildernes uafhængighed er falsk
- nyheden er gammel eller mangler reel ny udvikling
- headline er stærkere end dokumentationen
- et tal, navn, titel, dato eller citat ikke kan spores til ledgeren
- en relevant modpart mangler
- nyhedsteksten indeholder avisens egen konklusion
- artikel og kommentar er blandet sammen
- historien er en dublet uden selvstændig nyhed
- foto, ophav eller licens er uklart
- artiklen er lavet for at fylde en tidsplads eller kategori-kvote
- tonen er vred, hånlig, aktivistisk eller partipolitisk

## Godkend kun hvis

- det bærende faktum opfylder `SOURCES.md`
- kategori og nyhedsvægt er rimelige
- artikelens første afsnit og H1 kan bæres af dokumentationen
- usikkerheder er tydelige
- story cluster er korrekt
- kommentar, hvis relevant, linkes fra/til den faktuelle artikel

## Ved afvisning

Skriv et kort kill-notat i `killed/{dato}-{slug}.md` med primær årsag og gate. Læg ikke HTML live. Et afvist stykke kan genåbnes, når manglen faktisk er løst.

Tom plads slår et dårligt stykke.
