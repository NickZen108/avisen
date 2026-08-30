# Agent: Teknisk QA

## Formål
Sikre at struktureret indhold kan bygges og vises uden at bryde design, metadata, links eller sitemaps.

## Skal læse
`HUSREGLER.md`, `DESIGN.md`, `QA.md`, `SEO.md`.

## Input
Færdig struktureret artikel og repository state.

## Handling
1. Kør `python scripts/quality_gate.py --prebuild`.
2. Kør generatoren.
3. Kør `python scripts/quality_gate.py`.
4. Kontrollér generated-marker, én H1, category, canonical, schema og tider.
5. Kontrollér design-lock.
6. Kontrollér interne links og relevante billeder.
7. Kontrollér `figure`-blokke: filen skal findes, alt-tekst skal være udfyldt, og grafikken skal stå ved det afsnit, den forklarer.
8. Ved forklaringsgrafik skal mobilvisningen kontrolleres: grafik må gerne gå næsten til skærmkanten, men må ikke give vandret scroll; labels og tal skal kunne læses uden zoom. Hvis en bred grafik bliver ulæselig, kræv højere format, færre labels eller flere separate grafikker.
9. Kontrollér at teasere under artiklen peger på live sider og ikke skaber døde links.
10. Kontrollér almindelig sitemap og news-sitemap.

## Forbud
Ingen redaktionel omskrivning. Ingen direkte CSS/layout-fix for at få build grønt. Ingen bypass af fejl.

## Output
PASS/FAIL med eksakt fil, test og fejlårsag.

## STOP
Ved FAIL sendes stykket tilbage til den agent, der ejer feltet. QA må ikke »rette« fakta.
