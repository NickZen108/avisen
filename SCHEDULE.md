# Planlagt udgivelse

Som WordPress «Schedule». Artikler gøres færdige i køen. De går først live, når udgiver-agenten slipper dem.

## Kø

`scheduled/YYYY-MM-DD-slug.md` med frontmatter:

```
publish_at: 2026-08-30T10:00:00+02:00
status: queued
slug: ...
title: ...
genre: ...
html_path: scheduled/html/YYYY-MM-DD-slug.html
```

Færdig HTML ligger i `scheduled/html/`.

## Slots (Europe/Copenhagen)

07:30 · 10:00 · 13:00 · 16:00 · 19:00 · 21:30

Mindst 3 timer mellem to live-udgivelser. Ingen klumper. Maks. én artikel pr. slot.

## Udgiver-agent

Kører hver time 07–22. Finder den ældste queued-fil hvor publish_at ≤ nu. Flytter HTML til `docs/artikler/{slug}.html`, opdaterer forside + sitemap, sætter status: live. Stopper. Hvis ingen er forfalden: ingen ændring.
