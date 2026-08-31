begin;

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
grant usage on schema private to authenticated;

-- RLS helper lives outside the exposed API schema. It only answers whether
-- the current authenticated user has a role; callers cannot choose another user.
create or replace function private.has_role(required_role public.app_role)
returns boolean
language sql
stable
security definer
set search_path = public, private
as $$
  select exists(
    select 1 from public.user_roles
    where user_id = auth.uid() and role = required_role
  );
$$;
revoke all on function private.has_role(public.app_role) from public, anon;
grant execute on function private.has_role(public.app_role) to authenticated;

-- Trigger-only functions are also kept out of the exposed public schema.
create or replace function private.prevent_last_admin_removal()
returns trigger
language plpgsql
security definer
set search_path = public, private
as $$
declare
  admin_count integer;
begin
  if old.role <> 'admin' then
    return coalesce(new, old);
  end if;
  if tg_op = 'UPDATE' and new.role = 'admin' then
    return new;
  end if;
  select count(*) into admin_count from public.user_roles where role = 'admin';
  if admin_count <= 1 then
    raise exception 'Cannot remove the final Morgentidende admin';
  end if;
  return coalesce(new, old);
end;
$$;
revoke all on function private.prevent_last_admin_removal() from public, anon, authenticated;

drop trigger if exists protect_final_admin on public.user_roles;
create trigger protect_final_admin
before delete or update of role on public.user_roles
for each row execute function private.prevent_last_admin_removal();

create or replace function private.bootstrap_new_user()
returns trigger
language plpgsql
security definer
set search_path = public, private
as $$
begin
  insert into public.profiles(user_id, display_name, locale)
  values (
    new.id,
    nullif(coalesce(new.raw_user_meta_data->>'display_name', new.raw_user_meta_data->>'name', ''), ''),
    coalesce(nullif(new.raw_user_meta_data->>'locale', ''), 'da-DK')
  )
  on conflict (user_id) do nothing;

  insert into public.user_roles(user_id, role)
  values (new.id, 'reader')
  on conflict (user_id, role) do nothing;

  insert into public.subscriptions(user_id, tier, status)
  values (new.id, 'free', 'inactive')
  on conflict (user_id) do nothing;

  return new;
end;
$$;
revoke all on function private.bootstrap_new_user() from public, anon, authenticated;

drop trigger if exists on_auth_user_created_morgentidende on auth.users;
create trigger on_auth_user_created_morgentidende
after insert on auth.users
for each row execute function private.bootstrap_new_user();

-- Rebuild policies against the non-exposed helper.
drop policy if exists profiles_self_read on public.profiles;
create policy profiles_self_read on public.profiles for select using (user_id = auth.uid() or private.has_role('editor') or private.has_role('admin'));

drop policy if exists roles_self_read on public.user_roles;
create policy roles_self_read on public.user_roles for select using (user_id = auth.uid() or private.has_role('admin'));

drop policy if exists submissions_author_read on public.submissions;
create policy submissions_author_read on public.submissions for select using (author_id = auth.uid() or private.has_role('editor') or private.has_role('admin'));
drop policy if exists submissions_author_insert on public.submissions;
create policy submissions_author_insert on public.submissions for insert with check (author_id = auth.uid() and private.has_role('chronicler'));
drop policy if exists submissions_author_update on public.submissions;
create policy submissions_author_update on public.submissions for update using (author_id = auth.uid() and private.has_role('chronicler') and status in ('draft','changes_requested','approved','scheduled')) with check (author_id = auth.uid());

drop policy if exists revisions_read on public.submission_revisions;
create policy revisions_read on public.submission_revisions for select using (exists(select 1 from public.submissions s where s.id=submission_id and (s.author_id=auth.uid() or private.has_role('editor') or private.has_role('admin'))));
drop policy if exists revisions_insert on public.submission_revisions;
create policy revisions_insert on public.submission_revisions for insert with check (created_by=auth.uid() and exists(select 1 from public.submissions s where s.id=submission_id and s.author_id=auth.uid() and private.has_role('chronicler')));

drop policy if exists reviews_read on public.agent_reviews;
create policy reviews_read on public.agent_reviews for select using (exists(select 1 from public.submissions s where s.id=submission_id and (s.author_id=auth.uid() or private.has_role('editor') or private.has_role('admin'))));

drop policy if exists media_read on public.media;
create policy media_read on public.media for select using (owner_id=auth.uid() or private.has_role('editor') or private.has_role('admin'));
drop policy if exists media_insert on public.media;
create policy media_insert on public.media for insert with check (owner_id=auth.uid() and private.has_role('chronicler'));

drop policy if exists publish_requests_read on public.publish_requests;
create policy publish_requests_read on public.publish_requests for select using (requested_by=auth.uid() or private.has_role('editor') or private.has_role('admin'));

drop policy if exists subscriptions_self_read on public.subscriptions;
create policy subscriptions_self_read on public.subscriptions for select using (user_id=auth.uid() or private.has_role('admin'));

drop policy if exists audit_admin_read on public.audit_log;
create policy audit_admin_read on public.audit_log for select using (private.has_role('admin'));

-- Remove obsolete externally exposed helpers/view.
drop view if exists public.admin_count;
drop function if exists public.has_role(public.app_role);
drop function if exists public.prevent_last_admin_removal();
drop function if exists public.bootstrap_new_user();

commit;
