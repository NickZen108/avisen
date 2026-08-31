# Morgentidende — admin recovery runbook

Målet er, at en fejl i app-login eller en forkert rolleændring aldrig må låse ejeren ude af platformen.

## Uafhængige adgangsveje
1. **Supabase project owner** — kan administrere databasen uafhængigt af Morgentidendes app-login.
2. **GitHub repository owner** — source of truth for kode, migrations og publiceringspipeline.
3. **Cloudflare account owner** — hosting/runtime. Indtil direkte chat-connector er tilgængelig, kan deployments fortsat styres via GitHub Actions.
4. **Applikationsrollen `admin`** — adgang i Morgentidendes Kontrolrum.

Ingen delt masteradgangskode bruges. Secrets gemmes aldrig i repoet.

## Beskyttelse mod sidste-admin-fejl
Databasetriggeren `private.prevent_last_admin_removal()` afviser sletning eller nedgradering af den sidste `admin` i `public.user_roles`.

## Genopret app-admin
Hvis Kontrolrummet ikke accepterer en ellers gyldig bruger:

1. Bekræft brugerens konto i `auth.users`.
2. Tildel rollen server-side:

```sql
insert into public.user_roles(user_id, role, granted_by)
values ('<user-uuid>', 'admin', '<granting-admin-uuid>')
on conflict (user_id, role) do nothing;
```

Ved ren break-glass recovery, hvor ingen applikations-admin kan bruges, kan Supabase project owner udføre tildelingen direkte. Hændelsen skal efterfølgende registreres i `audit_log` med årsagen `break_glass_admin_recovery`.

## Hvis app-backend er nede
Den offentlige avis er statisk på Cloudflare og skal fortsat være læsbar. Reparer app/auth uden at flytte eller deaktivere `www`.

## Administration fra ChatGPT
Når brugerens autoriserede GitHub- og Supabase-forbindelser er aktive, kan ændringer i repo, SQL-migrations, sikkerhedstjek og rolle-recovery udføres fra chatten uden at dele permanente credentials med assistenten. Cloudflare-operationer udføres via GitHub Actions, indtil en direkte autoriseret Cloudflare-forbindelse er tilgængelig.

## Regel
En recovery må aldrig omgå redaktionelle publiceringsgates. Admin-recovery genskaber adgang; den giver ikke tilladelse til at publicere ikke-godkendt journalistik.
