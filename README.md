# Avisen

Offentligt redaktionelt arkiv.

GitHub er den kanoniske kopi af avisen. Natlige Grok-automations skriver **udkast** til `drafts/`. Færdige stykker flyttes til `published/` efter menneskelig godkendelse.

**Repo:** [github.com/NickZen108/avisen](https://github.com/NickZen108/avisen)

## Status

Dette er en frisk start. Indholdet fra Grok Bot blev ikke eksporteret automatisk (Bot-kvoten var opbrugt). Nye artikler lander som drafts.

## Mappeopdeling

| Sti | Formål |
|---|---|
| `drafts/` | Udkast fra natlig automation eller manuel research |
| `published/` | Godkendte artikler |
| `sources/` | Kildelister og noter |
| `STYLE.md` | Sprog, længde, kildekrav |
| `EDITORIAL.md` | Redaktionel linje og emner |

## Arbejdsgang

1. Automation kører om natten, researcher ét emne og committer én fil i `drafts/`.
2. Redaktør læser draft, retter og flytter til `published/`.
3. Live-site (fx Hostinger) trækker kun fra `published/` — ikke fra drafts.

## Skabelon

Nye artikler følger `drafts/_template.md`.
