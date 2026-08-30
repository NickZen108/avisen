# SEO og discovery — Morgentidende

SEO kører efter journalist, fact check, sprog og etik. SEO må aldrig ændre fakta, vinkel, juridisk status eller redaktionel vægt for at jagte søgninger.

## Alle artikler

- én H1
- `<title>` præcist og normalt højst ca. 60 tegn inkl. `– Morgentidende`, når det kan ske uden at gøre titlen kunstig
- meta description beskriver sagen klart; ca. 140–160 tegn er mål, ikke tvang
- kort, stabil slug med 2–6 meningsbærende ord
- canonical URL
- Open Graph
- korrekt Schema.org-type
- beskrivende alt-tekst
- interne links, når de faktisk hjælper læseren
- ingen keyword stuffing, clickbait eller kunstige FAQ-afsnit

## Nyheder

Nyheder skrives for læseren først. SEO-agenten må ikke indsætte gentagne søgefraser i brødteksten eller ændre H1 til et mere sensationelt søgeord.

Schema: `NewsArticle`.

Ved en fortsættende historie skal den kanoniske URL opdateres frem for at skabe næsten identiske URLs. Gammel artikel får ikke nyt `datePublished`; substantiel opdatering får `dateModified`.

## Guide, feature og historie

Evergreen-stof må gerne planlægges med søgeintention, men kun når emnet har selvstændig redaktionel værdi.

Research kan identificere:

- én primær brugerintention
- 2–3 naturlige spørgsmål
- eksisterende Morgentidende-stof for at undgå kannibalisering

Struktur vælges efter emnet. Nummererede trin, FAQ og HowTo bruges kun, når de faktisk passer — ikke som obligatorisk SEO-skabelon.

Vejledende længde:

- Guide: typisk 700–1400 ord
- Feature: typisk 800–1600 ord

Kortere er bedre, hvis emnet er dækket. Ingen fyld for ordantal.

## Schema

- Nyhed: `NewsArticle`
- Feature/historie: `Article`
- Guide: `Article`; `HowTo` kun ved reelle trin; `FAQPage` kun ved ægte FAQ-indhold
- Kommentar: `OpinionNewsArticle` hvis understøttet i generatoren, ellers `Article` med tydelig kategori

## News sitemap

`docs/news-sitemap.xml` genereres automatisk og indeholder kun relevante nye artikler fra de seneste to døgn. `docs/sitemap.xml` er den almindelige langsigtede sitemap.

## Discovery og loyalitet

Morgentidende optimerer ikke kun for Google. Discovery-mål er:

- direkte besøg
- tilbagevendende læsere
- nyhedsbrev
- RSS/notifikationer når de etableres
- interne story clusters
- søgning og Google News/Discover som distributionskanaler

Rå klik må ikke styre lead eller få systemet til at lære tabloidisme. Engagement bruges senere som sekundært signal sammen med redaktionel vægt.

## E-E-A-T og transparens

Byline: `Morgentidende Redaktion`, medmindre en faktisk navngiven skribent står bag. Kilder, dato, rettelser og metode skal være synlige. Der må aldrig opfindes en ekspert eller forfatterprofil for SEO.
