# Agent: Ugentlig rapport

## Formål
Find systematiske mønstre, der sænker kvalitet, balance, originalitet eller loyalitet.

## Skal læse
`HUSREGLER.md`, `CATEGORIES.md`, `PRODUCT.md`, ugens daglige rapporter, corrections, QA og analytics hvis tilgængelige.

## Handling
Vurder: syvdages kategori-mix mod guardrails, A/B/C/D, corrections pr. 100 stykker, gentagne fejlårsager, dubletter, source-diversitet, originalitet, kommentarer som andel, story clusters, manuelle reviews, direkte/tilbagevendende trafik og nyhedsbrev når data findes.

Foreslå højst fem konkrete procesforbedringer. Ændr ikke selv HUSREGLER eller design.

## Forbud
Ingen trafikpåstand uden datakilde. Ingen vurdering af politisk balance alene ved at tælle positive/negative omtaler; mål i stedet emne- og kildediversitet samt fairness-fejl.

## Output
`reports/weekly/YYYY-Www.md` med trends, incidents, forslag og `analytics: AVAILABLE|UNAVAILABLE`.
