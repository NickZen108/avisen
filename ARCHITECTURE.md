# Morgentidende platformarkitektur

## Mål
Den offentlige avis skal være hurtig, billig og læsbar selv når login, betaling eller redaktionel backend er nede. Dynamiske funktioner isoleres fra publiceret indhold.

## Flader

### www
- Cloudflare Workers Static Assets.
- Genereret fra `content/` og `templates/`.
- Ingen runtime-afhængighed af Supabase eller Stripe for almindelig læsning.
- GitHub er source of truth for publiceret redaktionelt indhold.

### app
- Cloudflare Worker under senere `app.<domæne>` eller `/app`.
- Login, profil, kronikørdesk, invitationer og senere abonnementsfunktioner.
- Supabase Auth + PostgreSQL som system of record for dynamiske data.
- R2 til brugeruploadede hero-billeder og andre mediefiler.

### kontrolrum
- Samme app-backend, særskilt admin/redaktør-UI.
- Beskyttes både af Cloudflare Access og applikationsrolle (`editor`/`admin`).
- Read-only pipelinevisning kan genereres fra GitHub/pipeline-health; skrivehandlinger skal gå gennem auditerede API-ruter.

## Kerneleverandører
- Cloudflare: Static Assets, Workers, Access, R2, Workers AI.
- Supabase: Auth, PostgreSQL, invitationer, MFA, RLS.
- GitHub: publiceret redaktionelt source of truth, migrations og pipelinekode.
- Stripe: betalinger, abonnementer og refunds, når monetisering aktiveres.

## Roller
`reader | chronicler | editor | admin`

Kronikører inviteres/godkendes; rollen kan ikke selv vælges ved signup.

## Kronikflow
`draft -> agent_check -> pass/revise/escalate -> publish_requested/scheduled -> GitHub commit -> normal release -> published`

- Kronik-agentens PASS bindes til revisionens SHA-256/hash.
- Enhver tekstændring efter PASS kræver ny kontrol.
- PASS giver kronikøren ret til selv at vælge `udgiv nu` eller planlagt tidspunkt.
- REVISE viser konkret begrundelse til kronikøren.
- ESCALATE vises samtidig i Kontrolrummet.
- Kronikøren skriver aldrig direkte til publiceret HTML.
- `published_at` sættes først af releaseprocessen.

## Monetisering
Fase 1: pæne, tydeligt markerede annoncer med kategori-blacklist.
Fase 2: frivilligt/premium abonnement uden hård paywall som udgangspunkt.
Fase 3: bøger/guides bygget af mærkede how-to-artikler.
Fase 4: sponsoreret indhold, altid tydeligt mærket og adskilt fra redaktionelle nyheder.

Datamodellen reserverer derfor felter til abonnement, `book_candidate` og kommercielt indhold uden at gøre www afhængig af dem.

## Internationalisering
Arkitekturen skal kunne udvides til `da-DK`, `de-DE`, `fr-FR`, `es-ES` uden at kopiere hele platformen.
- Artikler får `locale` og valgfrit `story_group_id`.
- Globale historier kan dele research/claim-grundlag, men hver lokal version får egen titel, tekst, SEO og lokal relevansvurdering.
- Senere genereres korrekte canonical/hreflang-relationer.

## Stabilitetsprincipper
1. Publiceret www må ikke kræve Supabase/Stripe for at blive vist.
2. Alle eksterne writes skal være idempotente.
3. Stripe er økonomisk sandhed; databasen gemmer kun nødvendig spejlet status.
4. Alle vigtige regler, migrations og API-kontrakter ligger i repoet.
5. Secrets ligger kun i runtime secrets.
6. R2 har ingen public write-adgang.
7. Adminhandlinger har auditlog.
8. En enkelt bruger/submission må aldrig blokere avisens build eller andre publiceringer.

## Admin-kontinuitet
- Der skal altid findes mindst to uafhængige admin-veje: Supabase project owner/dashboard og en applikations-adminrolle.
- Fjernelse af sidste aktive admin skal afvises af backend.
- Adminrolle må kun tildeles via en auditeret server-side handling, aldrig fra browserens klientkode.
- Der oprettes en dokumenteret break-glass-procedure, men ingen master-passwords eller hemmelige tokens må ligge i repoet.
- ChatGPT får ikke en delt permanent adgangskode. Administration herfra sker gennem de tilsluttede GitHub/Supabase/Cloudflare-værktøjer med brugerens autorisation, så adgang kan tilbagekaldes uden at dele credentials.

## Mappekontrakt
- `docs/` — genereret offentlig avis.
- `content/` — redaktionel canonical data.
- `cloudflare/newsdesk/` — redaktionel AI/newsdesk runtime.
- `cloudflare/app/` — konto-, kronikør- og admin-API/UI runtime.
- `supabase/migrations/` — versionsstyret database-schema/RLS.
- `contracts/` — stabile JSON/API-kontrakter mellem app, GitHub og pipeline.
- `reports/editorial/` — pipeline-health og ikke-hemmelige driftsrapporter.
