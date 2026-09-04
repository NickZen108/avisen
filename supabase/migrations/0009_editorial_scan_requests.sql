create table if not exists public.editorial_scan_requests (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  run_id text not null,
  story_id text,
  requested_by text not null check (requested_by in ('journalist','media','chief')),
  kind text not null check (kind in ('source','photo','next_story')),
  query text not null,
  purpose text,
  result_count integer not null default 0 check (result_count >= 0),
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists editorial_scan_requests_created_at_idx
  on public.editorial_scan_requests (created_at desc);
create index if not exists editorial_scan_requests_story_id_idx
  on public.editorial_scan_requests (story_id, created_at desc);

alter table public.editorial_scan_requests enable row level security;
alter table public.editorial_scan_requests force row level security;

comment on table public.editorial_scan_requests is
  'Private audit log of targeted Scan requests ordered by Journalist, Media or Chefredaktør in Pipeline v3.';
