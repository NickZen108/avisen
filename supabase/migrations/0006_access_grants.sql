begin;

create table public.access_grants (
  email text primary key,
  roles public.app_role[] not null,
  note text,
  created_at timestamptz not null default now(),
  check (email = lower(trim(email)))
);

alter table public.access_grants enable row level security;

insert into public.access_grants(email, roles, note)
values (
  'nicolaipetersen108@gmail.com',
  array['reader','chronicler','editor','admin']::public.app_role[],
  'Founding administrator'
)
on conflict (email) do update set roles = excluded.roles, note = excluded.note;

create or replace function public.has_role(required_role public.app_role)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.user_roles r
    where r.user_id = (select auth.uid())
      and (
        r.role = required_role
        or (required_role = 'reader' and r.role in ('chronicler','editor','admin'))
        or (required_role = 'chronicler' and r.role in ('editor','admin'))
        or (required_role = 'editor' and r.role = 'admin')
      )
  );
$$;

revoke all on public.access_grants from anon, authenticated;
revoke all on function public.has_role(public.app_role) from public;
grant execute on function public.has_role(public.app_role) to authenticated;

commit;
