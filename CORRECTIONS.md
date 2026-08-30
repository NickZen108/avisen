# Rettelser og præciseringer

Morgentidende retter fejl hurtigt, synligt og proportionalt. Materielle fejl må ikke forsvinde gennem stille omskrivning.

## Niveauer

**Typo/stil:** uden ændring af mening; kan rettes uden offentlig note.

**Præcisering:** ikke direkte forkert, men væsentligt misforståelig/mangelfuld kontekst.

**Rettelse:** materiel faktuel fejl.

**Tilbagetrækning:** bærende præmis kan ikke opretholdes.

## Workflow

1. Live proofreader, update-monitor, læser eller redaktør registrerer mulig fejl.
2. Fact checker genåbner de relevante claim-id'er.
3. **Correction editor** klassificerer og skriver den nødvendige rettelse fra genverificerede claims.
4. Relevante Sprog/Etik/Billede/SEO-gates køres igen.
5. Slutredaktør godkender den nye redaktionelle slutversion.
6. Udgiver opdaterer `updated_at` ved release/publicering.
7. Ved præcisering/rettelse/tilbagetrækning tilføjes entry til `content/corrections.json`.
8. Generatoren opdaterer `docs/rettelser.html`.

## Canonical rettelseslog

`content/corrections.json` er sandheden. `docs/rettelser.html` må ikke håndredigeres som primær log.

Hver offentlig entry har mindst `type`, `article_slug`, `timestamp`, `summary`.
