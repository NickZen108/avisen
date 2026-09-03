# Agenter og processer — Morgentidende

Alle roller følger `HUSREGLER.md`. Hver beslutning har én ejer. En senere rolle må ikke rutinemæssigt gentage tidligere arbejde.

## Den enkle avis-motor

Normal vej:

**Scan → Nyhedsdesk → Research → Fact checker → Journalist → Media → Slutredaktør → Release/build → Forside/deploy**

1. **Scan** finder, normaliserer og grupperer signaler. Dette skal være så billigt og deterministisk som muligt.
2. **Nyhedsdesk** vælger historien, story-id, foreløbig kategori og A-D-vægt.
3. **Research** finder og strukturerer kun den evidens, historien faktisk behøver. Kildekrav følger `SOURCES.md`.
4. **Fact checker** er eneste ejer af faktuel claim-verifikation. Der køres ikke et ekstra generelt fact-check senere i kæden.
5. **Journalist** skriver titel, manchet og artikel udelukkende fra verificerede claims og forventes at levere publicerbart dansk første gang.
6. **Media** vælger/verificerer foto, video eller illustration efter `MEDIA_SOURCES.md`.
7. **Slutredaktør** laver ét kort slutcheck mod de allerede verificerede claims, fastsætter endelig kategori og udsteder det versionsbundne final approval.

**Sprog** er kun en betinget repair-gren: hvis Slutredaktøren finder et reelt sprogproblem, repareres den eksisterende tekst målrettet. Der betales ikke for en fuld sproglig omskrivning af alle artikler.

**Etik/fairness** er ligeledes en betinget sidegren ved konkret presseetisk risiko, ikke et obligatorisk ekstra AI-kald på alt stof.

SEO/discovery, release, builder, forsideplacering og teknisk QA er maskinrum og må ikke blive selvstændige redaktionelle gates.

## Fejl sendes kun til nærmeste ejer

Et senere led må ikke sende en artikel tilbage til starten uden en konkret grund:

- **Sprogfejl** → målrettet Sprog-repair af den eksisterende artikel.
- **Artikeltekst går ud over verificerede claims / forkert attribution** → Journalist reparerer teksten ud fra de samme verificerede claims. Fact checker genkøres ikke, medmindre selve evidensen er problemet.
- **Manglende eller tvivlsom evidens** → Research/Fact checker. Dette er den eneste normale grund til at gå så langt tilbage.
- **Fairness/etik** → Etik/fairness; eksisterende verificeret materiale bruges først. Mangler nødvendig dokumentation eller modpartsoplysning, routes kun den konkrete mangel til Research.
- **Mediafejl** → Media finder/retter media; teksten og Fact checker genkøres ikke.
- **Kategori** → Slutredaktør retter kategorien direkte; artiklen sendes ikke gennem kæden igen.
- **SEO/metadata/forside** → deterministisk reparation/fallback; aldrig tilbage til journalistikken.

## Maksimum tre artikel-forsøg

En artikel må have højst **tre artikelversioner/forsøg** i den redaktionelle slutfase:

- Forsøg 1 er Journalistens normale artikel.
- Hvis Slutredaktøren finder et konkret reparerbart problem, laves kun en lokal version 2.
- Hvis nødvendigt kan der laves én lokal version 3.
- Efter tre versioner droppes artiklen, hvis den stadig ikke kan godkendes.

Et nyt forsøg betyder ikke, at Scan, Nyhedsdesk, Research og Fact checker automatisk køres igen. Tidligere arbejde genbruges, medmindre fejlen faktisk ejes dér. Det begrænser både loops, tokens og neurons.

## Deterministisk maskinrum

- **Release** accepterer kun et gyldigt Fact checker-PASS og et versionsmatchende final approval; release genfortolker ikke specialistgates.
- **Builder** genererer offentlig HTML fra canonical data.
- **SEO/metadata** afledes/repareres uden redaktionel blokering.
- **Forsideredaktør/placeringslogik** rangerer kun allerede publicerbare historier og kan ikke blokere publicering.
- **Teknisk QA** kontrollerer kode/build/output, ikke journalistiske beslutninger.
- **Live QA** kontrollerer den publicerede overflade efter deploy.

## Efter publicering

- **Update-monitor** reagerer kun på materielle nye oplysninger og sender dem til den nærmeste relevante ejer.
- **Correction editor** bruges ved materielle rettelser efter publicering.

Separate produktflows som kommentarer, kronikker og short-video er ikke trin i den almindelige nyhedspipeline. Rapportering og analytics er driftsanalyse, ikke artikelbehandling.

## Økonomiprincip

Billigste sikre operation først:

1. deterministisk kode/fallback,
2. genbrug af eksisterende verificeret data,
3. lille/fast model til afgrænsede repair-opgaver,
4. stærkere model kun ved reel kompleksitet eller struktureret-output-fallback.

Mål især AI-kald, tokens og neurons **pr. godkendt/publiceret artikel**, retry-rate og andel droppede artikler. Lavt forbrug er kun godt, hvis fejl- og korrektionsraten samtidig er lav.
