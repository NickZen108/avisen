begin;

create extension if not exists pgcrypto;

create type public.app_role as enum ('reader','chronicler','editor','admin');
create type public.submission_status as enum ('draft','agent_checking','changes_requested','escalated','approved','scheduled','publishing','published','killed');
create type public.agent_decision as enum ('pass','revise','escalate');

create table public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  locale text not null default 'da-DK',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.user_roles (
  user_id uuid not null references auth.users(id) on delete cascade,
  role public.app_role not null,
  granted_at timestamptz not null default now(),
  granted_by uuid references auth.users(id),
  primary key(user_id, role)
);

create table public.submissions (
  id uuid primary key default gen_random_uuid(),
  author_id uuid not null references auth.users(id) on delete restrict,
  locale text not null default 'da-DK',
  category text not null,
  title text not null default '',
  standfirst text not null default '',
  body text not null default '',
  status public.submission_status not null default 'draft',
  current_revision integer not null default 1,
  requested_publish_at timestamptz,
  published_at timestamptz,
  github_slug text,
  story_group_id uuid,
  book_candidate boolean not null default false,
  commercial_kind text check (commercial_kind is null or commercial_kind in ('sponsored','affiliate','house')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.submission_revisions (
  id uuid primary key default gen_random_uuid(),
  submission_id uuid not null references public.submissions(id) on delete cascade,
  revision_no integer not null,
  title text not null,
  standfirst text not null,
  body text not null,
  category text not null,
  content_hash text not null,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  unique(submission_id, revision_no)
);

create table public.agent_reviews (
  id uuid primary key default gen_random_uuid(),
  submission_id uuid not null references public.submissions(id) on delete cascade,
  revision_no integer not null,
  content_hash text not null,
  decision public.agent_decision not null,
  reasons jsonb not null default '[]'::jsonb,
  risk_type text,
  model text,
  created_at timestamptz not null default now()
);

create table public.media (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete restrict,
  submission_id uuid references public.submissions(id) on delete cascade,
  r2_key text not null unique,
  mime_type text not null check (mime_type in ('image/jpeg','image/png','image/webp')),
  byte_size bigint not null check (byte_size > 0 and byte_size <= 10485760),
  alt_text text not null default '',
  license text,
  credit text,
  created_at timestamptz not null default now()
);

create table public.publish_requests (
  id uuid primary key default gen_random_uuid(),
  submission_id uuid not null references public.submissions(id) on delete cascade,
  requested_by uuid not null references auth.users(id),
  requested_for timestamptz not null,
  revision_no integer not null,
  content_hash text not null,
  status text not null default 'pending' check (status in ('pending','processing','committed','published','failed','cancelled')),
  idempotency_key text not null unique,
  attempts integer not null default 0,
  last_error text,
  github_commit_sha text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.subscriptions (
  user_id uuid primary key references auth.users(id) on delete cascade,
  tier text not null default 'free',
  stripe_customer_id text unique,
  stripe_subscription_id text unique,
  status text,
  current_period_end timestamptz,
  updated_at timestamptz not null default now()
);

create table public.audit_log (
  id bigint generated always as identity primary key,
  actor_id uuid references auth.users(id),
  action text not null,
  object_type text not null,
  object_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index submissions_author_status_idx on public.submissions(author_id,status);
create index publish_requests_due_idx on public.publish_requests(status,requested_for);
create index agent_reviews_submission_idx on public.agent_reviews(submission_id,created_at desc);
create index audit_log_created_idx on public.audit_log(created_at desc);

create or replace function public.has_role(required_role public.app_role)
returns boolean language sql stable security definer set search_path = public
as $$ select exists(select 1 from public.user_roles where user_id = auth.uid() and role = required_role); $$;

alter table public.profiles enable row level security;
alter table public.user_roles enable row level security;
alter table public.submissions enable row level security;
alter table public.submission_revisions enable row level security;
alter table public.agent_reviews enable row level security;
alter table public.media enable row level security;
alter table public.publish_requests enable row level security;
alter table public.subscriptions enable row level security;
alter table public.audit_log enable row level security;

create policy profiles_self_read on public.profiles for select using (user_id = auth.uid() or public.has_role('editor') or public.has_role('admin'));
create policy profiles_self_update on public.profiles for update using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy roles_self_read on public.user_roles for select using (user_id = auth.uid() or public.has_role('admin'));

create policy submissions_author_read on public.submissions for select using (author_id = auth.uid() or public.has_role('editor') or public.has_role('admin'));
create policy submissions_author_insert on public.submissions for insert with check (author_id = auth.uid() and public.has_role('chronicler'));
create policy submissions_author_update on public.submissions for update using (author_id = auth.uid() and public.has_role('chronicler') and status in ('draft','changes_requested','approved','scheduled')) with check (author_id = auth.uid());

create policy revisions_read on public.submission_revisions for select using (exists(select 1 from public.submissions s where s.id=submission_id and (s.author_id=auth.uid() or public.has_role('editor') or public.has_role('admin'))));
create policy revisions_insert on public.submission_revisions for insert with check (created_by=auth.uid() and exists(select 1 from public.submissions s where s.id=submission_id and s.author_id=auth.uid() and public.has_role('chronicler')));

create policy reviews_read on public.agent_reviews for select using (exists(select 1 from public.submissions s where s.id=submission_id and (s.author_id=auth.uid() or public.has_role('editor') or public.has_role('admin'))));

create policy media_read on public.media for select using (owner_id=auth.uid() or public.has_role('editor') or public.has_role('admin'));
create policy media_insert on public.media for insert with check (owner_id=auth.uid() and public.has_role('chronicler'));

create policy publish_requests_read on public.publish_requests for select using (requested_by=auth.uid() or public.has_role('editor') or public.has_role('admin'));
create policy subscriptions_self_read on public.subscriptions for select using (user_id=auth.uid() or public.has_role('admin'));
create policy audit_admin_read on public.audit_log for select using (public.has_role('admin'));

-- No browser policy grants INSERT/UPDATE on roles, reviews, publish execution,
-- subscriptions or audit_log. Those are server-side service-role operations only.

commit;
