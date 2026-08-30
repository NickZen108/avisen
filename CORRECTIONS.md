# Rettelser og præciseringer

Morgentidende retter fejl hurtigt, synligt og proportionalt. Materielle fejl må ikke forsvinde gennem stille omskrivning.

## Niveauer

**Typo/stil:** stavefejl, tegnsætning eller layout uden ændring af mening. Kan rettes uden offentlig note; logges af QA hvis systematisk.

**Præcisering:** oprindelig tekst var ikke direkte forkert, men kunne misforstås eller manglede vigtig kontekst. Tilføj synlig `Præcisering` med tidspunkt, hvis ændringen er væsentlig for forståelsen.

**Rettelse:** faktuel fejl i navn, tal, dato, titel, citat, juridisk status, hændelsesforløb eller anden materiel oplysning. Ret teksten og tilføj synlig `Rettelse` nederst med hvad der var forkert, hvad der er korrekt, og tidspunkt.

**Tilbagetrækning:** artikelens bærende præmis kan ikke opretholdes. Fjern ikke URL'en lydløst; erstat med tydelig forklaring, medmindre juridiske/privatlivsmæssige hensyn kræver andet.

## Workflow

1. Post-publication monitor eller redaktør registrerer mulig fejl.
2. Fact checker genåbner de relevante claim-id'er.
3. Rettelse godkendes af redaktør.
4. Udgiver opdaterer artikel og `updated_at`.
5. Ved materiel fejl opdateres `docs/rettelser.html`/rettelsesloggen.
6. Hvis fejlen også stod i H1, ticker eller forside, rettes alle flader.

## Ingen stealth corrections

En ændring er materiel, hvis en rimelig læser kunne ændre forståelse, vurdering af ansvar eller konklusion på grund af den. Så kræves note.

## Hastighed

Fejl med risiko for skade rettes straks efter verifikation. Mindre præciseringer ved førstkommende redaktionelle gennemgang. Der ventes ikke på en bestemt publiceringsslot.

## Sporbarhed

Research-ledgeren bevarer den oprindelige claim-status og noterer ændringen. Git-historikken er intern teknisk dokumentation; den offentlige læser skal ikke være afhængig af GitHub for at opdage en rettelse.
