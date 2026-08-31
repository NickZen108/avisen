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

Publicerede opfølgere vises samlet **neden under leadartiklen som en direkte forlængelse af leadkolonnen** i en tydeligt beslægtet, let anderledes farvet `Mere om sagen`-boks med den tynde relation-bjælke bevaret. Boksen viser normalt højst 3–4 af de stærkeste aktuelle opfølgere; øvrige opfølgere kan fortsat være tilgængelige via artiklerne/sagspakken. `Kommentar`, `Video` og `Billeder` skal mærkes synligt, så genren er klar.

Højre spalte ved leaden skal fortsat være den almindelige `Også i dag`-blanding af **andre** nyheder. Selve leaden og dens `related_news_slug`-opfølgere må ikke fylde denne spalte, når de allerede ligger i `Mere om sagen`.

## Hero-billeder

Hero-billeder skal være visuelt stærke, relevante og egnede til både desktop og mobil. Et teknisk diagram er som udgangspunkt forklaringsgrafik inde i artiklen, ikke artikelens hero, medmindre grafikken selv er historien.

**Husregel: Brug rigtige fotos, når de er gode, relevante og juridisk brugbare; ellers generér et flot hero-billede.** Et middelmådigt stock-/Commons-foto vælges ikke bare fordi det er nemt at licensere. Kvalitet og relevans skal være høj nok til et professionelt nyhedsmedie.

For **leadnyheder** er prioriteringen skærpet. Søg først efter: 1) dokumentarfoto fra selve hændelsen, 2) foto af redningsaktion/overlevende/pårørende/politi/ambulance/havn/gerningssted eller anden direkte scene, 3) den konkrete lokalitet, 4) dramatisk relevant miljøfoto fra området, der tydeligt bruges som kontekst, og først derefter 5) illustration/genereret hero. Dramatik og klikværdi er legitime hensyn mellem ellers korrekte billeder.

Et dramatisk billede fra en anden hændelse må aldrig bruges eller beskæres/billedtekstes, så læseren kan tro, at det er dokumentation fra den aktuelle hændelse. Et generisk eller lokalt kontekstfoto skal beskrives sandfærdigt som kontekst.

**Permanent lead photo watch:** Hvis et lead publiceres med et acceptabelt men ikke optimalt foto eller med illustration, beholdes heroen midlertidigt, mens Billedredaktør/update-monitor fortsætter med at lede efter et klart bedre, juridisk brugbart dokumentarfoto, så længe historien er lead. Et bedre fund skal verificeres for ophav, licens, dato/sted og kontekst og derefter routes gennem Billedredaktør → nødvendig etik/kildekontrol → Slutredaktør. Efter PASS udskiftes hero uden unødig forsinkelse og live-QA køres igen. Photo watch må aldrig forsinke selve publiceringen af en væsentlig historie.

For øvrige historier er prioriteten: 1) relevant, lovligt og æstetisk stærkt foto, 2) flot genereret hero-billede, når et godt foto ikke findes eller ikke er tilstrækkeligt visuelt stærkt, 3) relevant redaktionel illustration, når illustrationsformen passer bedre til historien.

Genereret materiale må aldrig fremstilles som dokumentarfoto af en virkelig hændelse, person eller specifik scene. Det registreres som `image_type: illustration`. Dokumentarfotos må gerne få et diskret, ensartet redaktionelt filter eller farvebehandling, hvis det forbedrer helhedsindtrykket, men må ikke manipuleres, så dokumentarisk betydning ændres.

Hero-billedet skal have dækkende alt-tekst og beskæres eller vælges, så hovedmotivet fungerer i både stor hero, kort og mobilvisning.

## Video, screengrabs, links og offentlige kilder

Når en verificeret video er stærkere end det bedste stillfoto, må den officielle embed bruges som hero i artiklen og — efter Forsideredaktørens vurdering — som levende hero på forsiden. YouTube bruges via den officielle embeddable player. Frontpage-autoplay må kun ske muted; autoplay med lyd er forbudt. Hvis embed ikke virker, skal siden falde tilbage til et godkendt hero-foto.

Videoartikler skal som standard have rækkefølgen **rubrik → manchet → stor 16:9 video → forklarende tekst**. Der søges YouTube/primærkilder først, så læseren så vidt muligt kan se materialet uden at forlade Morgentidende.

Et screengrab fra YouTube eller anden video kan bruges som hero, når optagelsen er central for journalistikken og brugen har et dokumenteret juridisk grundlag, fx CC/public domain, licens/tilladelse eller en konkret forsvarlig citat-/reportagevurdering. At videoen er offentlig på YouTube, eller at et andet medie har screengrabbet den, giver ikke i sig selv Morgentidende en licens. Kreditering og link/embed til originalen er påkrævet, men erstatter ikke rettighedsvurderingen.

**Rå URL'er må ikke stå som læsetekst.** Eksterne links skal altid have et kort, menneskeligt linknavn som `Se optagelserne hos ...` eller kildens/dokumentets navn. Eksterne links bruges kun, når de giver konkret dokumentations- eller oplevelsesværdi.

Den fulde kilde- og claim-dokumentation skal fortsat ligge i ledgeren og bestå alle interne gates, men **en standardsektion med en liste over alle eksterne kilder vises ikke automatisk offentligt**. Det er ikke et krav, at læseren sendes videre til Reuters/AP/etc. fra hver artikel. Originale dokumenter, video, primærkilder og andet med selvstændig læserværdi kan stadig linkes kontekstuelt i artiklen.

Relaterede interne links må aldrig bruge CMS-agtig tekst som `Læs den faktuelle nyhedsartikel`. Vis i stedet den faktiske rubrik på den artikel, der linkes til, under en menneskelig label som `Mere om sagen`.

## Lægmandssprog, fremmedord og måleenheder

Morgentidende skrives til almindelige læsere, ikke til fagfolk. **Hvis et fremmedord, fagudtryk, teknisk begreb eller brancheudtryk kan erstattes af almindeligt dansk uden at miste vigtig præcision, skal det erstattes.** Skriv fx `andre planeter` før eller i stedet for `exoplaneter`, og `større/bredere kortlægninger` eller en konkret dansk forklaring i stedet for engelske fagord som `surveys`, medmindre selve fagtermen er nødvendig.

Hvis en nødvendig term ikke kan oversættes enkelt eller præcist nok, skal den **forklares første gang den optræder med 1–2 korte sætninger i direkte lægmandssprog**. Forklaringen skal fortælle, hvad begrebet er, og hvorfor det betyder noget i netop historien. Eksempel: Et `Lagrange-punkt` må ikke stå uforklaret; læseren skal kort få at vide, at det er et område i rummet, hvor tyngdekraften fra to store legemer gør det muligt for et rumfartøj at holde en stabil placering med relativt lidt brændstof.

**Uvant mål og enheder skal omsættes til en enhed, en dansk læser umiddelbart forstår.** Nautiske mil, feet, miles, Fahrenheit, acres, pounds og tilsvarende må ikke stå alene i almindelig nyhedstekst. Brug som hovedregel kilometer, meter, kilometer i timen, Celsius, kvadratkilometer/hektar og kilogram. Hvis originalenheden har redaktionel betydning, kan den stå i parentes efter den letforståelige omregning, fx `cirka 7,4 kilometer (4 nautiske mil)`.

Sprogredaktøren skal aktivt lede efter sådanne ord og enheder før PASS. Slutredaktøren skal betragte uforklaret nødvendig fagsprog eller en uvant måleenhed uden lægmandsomregning som en redaktionel fejl, ikke blot som et stilspørgsmål.

## Design og kode

Nye artikler skrives som struktureret indhold under `content/` og genereres til `docs/`. Journalist- og redaktøragenter må ikke håndredigere CSS, logo, header, grids eller andre låste designfiler. Låste filer verificeres maskinelt.

Legacy-artikler i `docs/artikler/` er grandfathered, men ved større redaktionel opdatering skal de migreres til den strukturerede pipeline.

## Post-publication

Teknisk live-QA og redaktionel overvågning er to forskellige opgaver:

- GitHub/live QA kontrollerer HTTP, markup, interne assets og de netop ændrede/recent publicerede URL'er.
- Live proofreader læser den renderede side, som læseren ser, for tekst-/renderingsfejl og forskelle fra canonical indhold.
- Redaktionel update-monitor leder efter nye oplysninger, der ændrer et bærende claim, story-vægt eller lead.
- Aktuelle leadhistorier er altid omfattet af permanent photo watch, også hvis de kun er vægt B.
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