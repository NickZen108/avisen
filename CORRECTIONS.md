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


## Billedskift efter udgivelse

Et publiceret hero-/artikelbillede må udskiftes uden at genkøre hele nyhedspipelinen, når tekst, claims, SEO, kategori og øvrigt redaktionelt indhold er uændret.

Brug `python scripts/reapprove_media_change.py --slug <slug>`. Scriptet:

1. kræver en eksisterende bestået final approval,
2. beviser maskinelt at kun `image` er ændret siden den approval,
3. validerer basale kilde-, kredit- og licensmetadata,
4. opretter en ny målrettet media re-approval med hash af både gammel og ny snapshot,
5. lader den normale Pipeline V2-gate kontrollere den nye snapshot.

Hvis andet end billedet er ændret, stopper scriptet og kræver det almindelige correction/editorial re-approval-workflow. Dermed bliver billedskift muligt efter publicering uden at svække integritetsgaten.
