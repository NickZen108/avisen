# Korrekturvagt – 31. august 2026

## Interne noter og redaktørstemme
Gennemgået forsiden (docs/index.html og live https://nickzen108.github.io/avisen/) samt alle HTML-filer under docs/artikler/.
Søgt efter »Ingen frit foto«, »Illustration fordi«, »Det er hans sætning«, »ikke avisens«, produktionsforklaringer og redaktørstemme.
**Resultat: ingen forekomster.** Teasere er sagstekst. Ingen sletning nødvendig.

## 0. Dansk – ord og sætning
H1, title, ticker, manchet og brødtekst gennemgået. Ingen opdigtede eller forvrængede ord (fx »bødsel«) fundet. Alle ord kan stå i Retskrivningsordbogen eller er undtagelser (egennavne, forkortelser, citater). Ingen omskrivning nødvendig.

## 1. Døde og ødelagte billeder
Testet src på forside, lead, rail og artikelsider (workers.dev/cache og lokale).
HTTP 200 for de anvendte cache-URL’er (ec6a86a8cd3d79a0738b.jpg, 0c22651a4e7e10f611ec.jpg, 8d58306069921ec7a24a.jpg m.fl.).
Ingen 404/5xx/timeout for aktive src. Wikimedia Special:FilePath ikke anvendt direkte i live HTML (cache anvendes).
Ingen rettelse nødvendig.

## 2. Foto vs. overskriftens sted og emne
Lead: Kyrenia-havn (sted for afgang) – relevant kontekst.
Øvrige: matchende eller tematisk dækkende. Ingen mismatch der kræver udskiftning.

## 3. Manglende tid / fremdatering / kl. 06.00
Publiceringstider er angivet med <time datetime> og dansk label. Ingen systematisk 06.00 som falsk brud. Ingen fremdatering ift. aktuell dato.

## 4. Manglende .below
Pipeline-v2-artikler om færgekatastrofen (lead + opfølgere) mangler <section class="wrap below"> i den genererede HTML. Legacy-artikler har det. Noteret til build/template-opdatering; ikke håndredigeret for at undgå konflikt med GENERATED-markering.

## 5. Manglende krydsteaser (.related-teaser begge veje)
Færge-opfølgere har related_news_slug i content, men RELATED_TEASER_HTML er tom i output. Legacy-par (Lyngby, AfD, parkering) har krydsteaser. Noteret.

## Øvrigt
style.css, header, logo og grundfarver urørt.
Ingen commit af HTML-ændringer i denne runde, da primære gates (interne noter, dansk, døde billeder) er PASS, og manglende .below/krydsteaser hører til generator/pipeline.

## Status
PASS for interne noter, dansk og billeder. Observationer om .below og krydsteaser for v2-stof.
