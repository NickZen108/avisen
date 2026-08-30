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

Intet må gå live, hvis ét af disse punkter fejler:

- bærende fakta er ikke dokumenteret efter `SOURCES.md`
- tal, datoer, navne, titler eller citater kan ikke spores til faktaledgeren
- en væsentlig modpart mangler i en konkret strid
- alvorlig beskyldning mod navngiven person ikke er forelagt eller undtagelsen dokumenteret
- nyhedsværdi/freshness ikke passer til genren
- artikel og kommentar er blandet sammen
- sprog-, etik-, billede-, design- eller build-gate siger FAIL
- publiceringstid er fremtidig eller opdigtet
- en ny artikel er blot en dublet af en eksisterende story cluster

Tom plads slår et svagt eller usikkert stykke. Der findes ingen volumenregel, som kan tilsidesætte kvalitet.

## Adskillelse af ansvar

Ingen agent godkender sit eget arbejde. Research skriver ikke artikel. Journalist godkender ikke fakta. SEO må ikke ændre fakta. Sprog må ikke ændre mening. Udgiver må ikke omgå et FAIL.

Pipeline: Scan → Nyhedsdesk → Research → Fact check → Journalist → Sprog → Etik/fairness → SEO/discovery → Billede → Teknisk QA → Forsideredaktør → Udgiver → Post-publication monitor.

## Design og kode

Nye artikler skrives som struktureret indhold under `content/` og genereres til `docs/`. Journalist- og redaktøragenter må ikke håndredigere CSS, logo, header, grids eller andre låste designfiler. Låste filer verificeres maskinelt.

Legacy-artikler i `docs/artikler/` er grandfathered, men ved større redaktionel opdatering skal de migreres til den strukturerede pipeline.

## Transparens og rettelser

Væsentlige fejl rettes åbent efter `CORRECTIONS.md`. Der må ikke laves stille materielle rettelser. AI er et værktøj, aldrig en kilde; se `AI-POLICY.md`.

## Ændring af regler

Designlås og denne forfatning ændres kun efter en udtrykkelig brugerordre. Automatisk drift må ikke omskrive sine egne grundregler.
