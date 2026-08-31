# Lead follow-up desk

Når en historie bliver lead, åbnes straks en aktiv sagspakke. Målet er normalt 2–3 selvstændige opfølgere så hurtigt som dokumentation og kvalitet tillader. De behøver ikke udkomme samtidig.

## Prioritet

Følgende vinkler ligger øverst og vurderes parallelt — ikke sekventielt:

1. **Nye væsentlige oplysninger**: nye dødstal, redningsarbejde, anholdelser, myndighedsreaktioner, nye dokumenter eller andre materielle udviklinger.
2. **Ægte video og billeder fra hændelsen**: verificerede, relevante og juridisk brugbare videoer/fotos har samme høje prioritet som en stor faktuel opdatering. Søg aktivt efter dem straks, bl.a. hos primærkilder, myndigheder, redaktionelle medier, YouTube og andre åbne platforme. Et fund skal verificeres før brug; uploadtid, ophav, sted/tid og om materialet faktisk viser den påståede hændelse skal vurderes. Embed/link må kun bruges på en måde, som rettighedshaveren/platformen tillader. Intet AI-genereret materiale må fremstilles som dokumentation fra hændelsen.
3. **Øjenvidner/menneskelig vinkel**: autentiske, kildebelagte beretninger fra overlevende, øjenvidner, pårørende eller lokale kilder.
4. **Baggrund/forklaring**: tidslinje, årsager, geografi, teknik, institutioner, tidligere lignende hændelser og relevante data.
5. **Kommentar/analyse**: kun når der er en reel tese og et dokumenteret nyhedsgrundlag; tydeligt mærket `Kommentar`.

Visuelt materiale er ikke pynt. Hvis en verificeret video eller stærk billedserie eksisterer, kan en selvstændig opfølger som `Video: Her ...` eller `Billeder: ...` prioriteres før en almindelig baggrundsartikel, så længe rubrikken præcist beskriver det dokumenterede materiale og ikke overdriver.

## Kvalitetskrav

- Ingen dubletter af leaden; hver opfølger skal have en selvstændig nyhedsværdi eller tydelig særskilt funktion.
- Almindelige faktuelle opfølgere følger samme multi-source/fact-check-gates som øvrige nyheder.
- En ren video-/billedartikel må bruge selve originalmaterialet som primær dokumentation for, hvad materialet viser, men kontekstuelle faktuelle påstande skal stadig verificeres efter `SOURCES.md`.
- Uverificeret social video, genbrugte katastrofebilleder, deepfakes eller forkert dateret materiale publiceres ikke.
- Grafisk/voldsomt materiale kræver en konkret redaktionel vurdering af nødvendighed, beskæring/advarsel og værdighed. Klikværdi er aldrig alene tilstrækkelig begrundelse.

## Data og kobling

Alle opfølgere får `related_news_slug` sat til den aktuelle lead-slug og `followup_type` sat til én af: `update`, `video`, `images`, `eyewitness`, `background`, `timeline`, `commentary`.

Forsiden samler publicerede opfølgere i en tydeligt beslægtet `Mere om sagen`-boks tæt på leaden. Kommentar skal altid være synligt mærket `Kommentar`; video/billeder mærkes `Video`/`Billeder`.

## Tempo

Så snart en lead er valgt, skal desk'en straks åbne mindst tre researchspor parallelt: (a) nye fakta, (b) video/billeder, (c) den stærkeste af øjenvidne/baggrund/kommentar. Publicér hvert spor, når det selvstændigt er klar; vent ikke på de andre.
