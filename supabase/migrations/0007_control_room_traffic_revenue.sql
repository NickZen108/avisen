begin;

create table if not exists public.traffic_events (
  id bigint generated always as identity primary key,
  occurred_at timestamptz not null default now(),
  article_slug text not null,
  title text not null default '',
  category text not null default '',
  referrer_host text
);
create index if not exists traffic_events_occurred_idx on public.traffic_events(occurred_at desc);
create index if not exists traffic_events_slug_occurred_idx on public.traffic_events(article_slug, occurred_at desc);
alter table public.traffic_events enable row level security;

create table if not exists public.revenue_events (
  id uuid primary key default gen_random_uuid(),
  occurred_at timestamptz not null default now(),
  source text not null check (source in ('subscription','advertising')),
  gross_amount_ore bigint not null check (gross_amount_ore >= 0),
  currency text not null default 'DKK',
  external_id text unique,
  metadata jsonb not null default '{}'::jsonb
);
create index if not exists revenue_events_occurred_idx on public.revenue_events(occurred_at desc);
create index if not exists revenue_events_source_occurred_idx on public.revenue_events(source, occurred_at desc);
alter table public.revenue_events enable row level security;

-- No browser policies: the app Worker is the only writer/reader for these control-room datasets.
-- Pageviews are accepted only after origin + slug validation. Revenue rows come from trusted
-- server integrations when payment and advertising providers are connected.

commit;
