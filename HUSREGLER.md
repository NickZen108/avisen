# Husregler — Morgentidendes forfatning

Disse regler gælder for alle mennesker, agenter, workflows og scripts i repoet. En agent må ikke nøjes med sin egen prompt.

## Prioritet

Ved konflikt vinder den højest placerede regel:

1. `HUSREGLER.md` — denne forfatning og stopregler
2. `EDITORIAL.md` — presseetik, neutralitet, publiceringsansvar
3. `SOURCES.md` — kildekrav, faktaledger og citater
4. `STYLE.md` — dansk, overskrifter og redaktionelt sprog
5. `DESIGN.md` + `DESIGN.lock.md` — låst udseende og genereret HTML
6. `CATEGORIES.md` — kategorier og stofmix
7. `SCHEDULE.md` + `FRONTPAGE.md` — udgivelsesrytme, breaking og lead
8. `AGENTS.md` + `agents/*.md` — arbejdsdeling og agentspecifikke instruktioner
9. `SEO.md`, `QA.md`, `PRODUCT.md` — specialregler

En lavere regel må aldrig ophæve en højere. Ved tvivl: stop og send til redaktør/manual review; gæt aldrig.

## Hårde gates

Intet nyt pipeline-v2-stykke må gå live, hvis ét af disse punkter fejler:

- bærende fakta er ikke dokumenteret efter `SOURCES.md`
- coverage sweep mangler, eller en legitim begrænsning ikke er dokumenteret
- Fact checker har ikke PASS
- Nyhedsdesk har ikke efter research/fact check bekræftet `PUBLISH` eller `UPDATE`
- tal, datoer, navne, titler eller citater kan ikke spores til faktaledgeren
- påkrævet forelæggelse/modpart mangler, eller frist/undtagelse ikke er dokumenteret
- nyhedsværdi/freshness ikke passer til genren
- artikel og kommentar er blandet sammen
- sprog-, etik-, billede- eller SEO-opgaven er uafklaret
- Slutredaktørens uafhængige final approval mangler eller ikke matcher den aktuelle redaktionelle slutversion
- frontpage-, design- eller build-gate siger FAIL
- `manual_review: true` forsøges autopubliceret uden eksplicit afsluttet manuel review
- publiceringstid er fremtidig eller opdigtet
- en ny artikel er blot en dublet af en eksisterende story cluster

Tom plads slår et svagt eller usikkert stykke. Der findes ingen volumenregel, som kan tilsidesætte kvalitet.

## Adskillelse af ansvar

Ingen agent må alene gøre sit eget arbejde publiceringsklart. En agent må markere sin egen delopgave som færdig, men den endelige publiceringsgodkendelse kommer fra en anden rolle.

Research skriver ikke artikel. Fact checker skriver ikke artiklen og genresearcher ikke hele historien uden grund. Journalist godkender ikke fakta. Sprog må ikke ændre mening. Etik må ikke omskrive fakta. Billede vælger billedmateriale før SEO færdiggør delingsmetadata. SEO må ikke ændre journalistikken. Slutredaktøren ændrer ikke teksten ved PASS; ved fejl sender den tilbage til den ansvarlige agent. Udgiver må kun ændre publiceringsmetadata efter final approval og må aldrig omgå et FAIL.

Pipeline:

Scan → Nyhedsdesk/assignment → Research → Fact check → Nyhedsdesk/recheck → Journalist → Sprog → Etik/fairness → Billede → SEO/discovery → Slutredaktør → Forsideredaktør → Teknisk QA → Udgiver → live teknisk QA → Live proofreader → Redaktionel update-monitor.

## Pipeline v2 og versionsbinding

Nye autopublicerbare artikler bruger `pipeline_version: 2`.

Slutredaktørens approval ligger under `reports/editorial/approvals/<slug>.json` og indeholder et snapshot af den godkendte **redaktionelle** artikelversion. Efter approval må Udgiver/GitHub kun ændre publiceringsmetadata såsom `status`, `published_at`, `scheduled_for`, `release_requested` og tekniske releasefelter.

Hvis titel, manchet, brødtekst, claim-liste, SEO, billede, kilder til visning, relaterede links, kategori, byline, correction note eller andre redaktionelle felter ændres efter approval, bliver approval ugyldig og Slutredaktøren skal køre igen.

Gamle allerede publicerede strukturerede artikler uden `pipeline_version: 2` er grandfathered. En ny `[AUTO]`-PR må ikke autopublicere en artikel uden pipeline v2.

## Forsiden

For pipeline-v2-artikler skal `content/frontpage.json` normalt kun referere til artiklens `slug`. Titel, manchet/teaser, kategori, billede og publiceringstid hentes fra den kanoniske artikel ved build. Dermed kan en gammel kopi på forsiden ikke modsige en senere rettelse i artiklen.

Legacy-artikler uden struktureret canonical kilde kan fortsat have eksplicitte displayfelter.

## Lead-opfølgninger

Når en historie bliver lead, åbnes straks en aktiv sagspakke. Målet er normalt 2–3 selvstændige opfølgere så hurtigt som dokumentation og kvalitet tillader; de behøver ikke udkomme samtidig.

Nyhedsdesk skal straks åbne mindst tre parallelle researchspor: (1) nye væsentlige fakta, (2) autentisk video/billeder fra hændelsen og (3) den stærkeste øvrige vinkel som øjenvidne, baggrund, tidslinje, tidligere lignende hændelser eller tydeligt mærket Kommentar.

**Verificeret video og stærke autentiske billeder har samme topprioritet som store faktuelle opdateringer** såsom nye dødstal, redningsarbejde eller anholdelser. Der skal søges aktivt efter visuelt materiale hos primærkilder, myndigheder, redaktionelle medier, YouTube og andre åbne platforme. Materialet må først bruges, når ophav, kontekst, dato/sted og juridisk/platformsmæssig brug er tilstrækkeligt afklaret. Genereret materiale må aldrig fremstilles som dokumentation fra den virkelige hændelse.

En visuel opfølger må gerne have en direkte, præcis rubrik som `Video: Her ...` eller `Billeder: ...`, hvis materialet faktisk dokumenterer det beskrevne. Klikværdi er et legitimt hensyn ved valg mellem ellers forsvarlige vinkler, men kan aldrig erstatte dokumentation, etik eller relevans.

Hver opfølger skal have selvstændig nyhedsværdi eller funktion og må ikke blot omskrive leaden. Den mærkes med `related_news_slug` til leaden samt `followup_type`: `update`, `video`, `images`, `eyewitness`, `background`, `timeline` eller `commentary`.

Publicerede opfølgere vises samlet tæt på leaden i en tydeligt beslægtet, let anderledes farvet `Mere om sagen`-boks. `Kommentar`, `Video` og `Billeder` skal mærkes synligt, så genren er klar.

## Hero-billeder

Hero-billeder skal være visuelt stærke, relevante og egnede til både desktop og mobil. Et teknisk diagram er som udgangspunkt forklaringsgrafik inde i artiklen, ikke artikelens hero, medmindre grafikken selv er historien.

**Husregel: Brug rigtige fotos, når de er gode, relevante og juridisk brugbare; ellers generér et flot hero-billede.** Et middelmådigt stock-/Commons-foto vælges ikke bare fordi det er nemt at licensere. Kvalitet og relevans skal være høj nok til et professionelt nyhedsmedie.

Prioritet er derfor: 1) relevant, lovligt og æstetisk stærkt foto, 2) flot genereret hero-billede, når et godt foto ikke findes eller ikke er tilstrækkeligt visuelt stærkt, 3) relevant redaktionel illustration, når illustrationsformen passer bedre til historien.

Genereret materiale må aldrig fremstilles som dokumentarfoto af en virkelig hændelse, person eller specifik scene. Det registreres som `image_type: illustration`. Dokumentarfotos må gerne få et diskret, ensartet redaktionelt filter eller farvebehandling, hvis det forbedrer helhedsindtrykket, men må ikke manipuleres, så dokumentarisk betydning ændres.

Hero-billedet skal have dækkende alt-tekst og beskæres eller vælges, så hovedmotivet fungerer i både stor hero, kort og mobilvisning.

## Design og kode

Nye artikler skrives som struktureret indhold under `content/` og genereres til `docs/`. Journalist- og redaktøragenter må ikke håndredigere CSS, logo, header, grids eller andre låste designfiler. Låste filer verificeres maskinelt.

Legacy-artikler i `docs/artikler/` er grandfathered, men ved større redaktionel opdatering skal de migreres til den strukturerede pipeline.

## Post-publication

Teknisk live-QA og redaktionel overvågning er to forskellige opgaver:

- GitHub/live QA kontrollerer HTTP, markup, interne assets og de netop ændrede/recent publicerede URL'er.
- Live proofreader læser den renderede side, som læseren ser, for tekst-/renderingsfejl og forskelle fra canonical indhold.
- Redaktionel update-monitor leder efter nye oplysninger, der ændrer et bærende claim, story-vægt eller lead.
- A/breaking-stof overvåges aktivt de første 6 timer, mens almindelige historier kun genåbnes ved et konkret væsentligt signal; se `agents/post-publication.md`.

Ingen af dem må lave stille materielle rettelser.

## Offentlig metode og intern værktøjsbrug

Den offentlige avis skal beskrive dokumentation, kildearbejde, ansvar, rettelser og redaktionelle principper sandfærdigt. **Foreløbig skal offentlige sider ikke fremhæve, markedsføre eller kvantificere brugen af AI, sprogmodeller eller automatisering.**

Det er samtidig forbudt at skabe et falsk indtryk ved at opfinde menneskelige journalister, redaktører, øjenvidner eller eksperter eller ved at påstå, at en tekst er menneskeskrevet, hvis det ikke kan dokumenteres. Standardbyline `Morgentidende Redaktion` er en organisationsbyline og må bruges.

Den interne `AI-POLICY.md` gælder uændret for research, kildebrug, billeder og kvalitet. Hvis lovgivning, platformskrav eller presseetiske hensyn senere kræver en konkret offentlig AI-oplysning, går dette krav foran ønsket om lav profil.

## Transparens og rettelser

Væsentlige fejl rettes åbent efter `CORRECTIONS.md`. Der må ikke laves stille materielle rettelser. AI er et værktøj, aldrig en kilde; se `AI-POLICY.md`.

Den offentlige rettelseslog genereres fra `content/corrections.json`; `docs/rettelser.html` er output og må ikke være den kanoniske log.

## Ændring af regler

Designlås og denne forfatning ændres kun efter en udtrykkelig brugerordre. Automatisk drift må ikke omskrive sine egne grundregler.
