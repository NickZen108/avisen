begin;

-- Every authenticated account gets a profile and the harmless reader role.
-- Elevated roles are invite/admin decisions and are never self-selected.
create or replace function public.bootstrap_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
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

drop trigger if exists on_auth_user_created_morgentidende on auth.users;
create trigger on_auth_user_created_morgentidende
after insert on auth.users
for each row execute function public.bootstrap_new_user();

commit;
