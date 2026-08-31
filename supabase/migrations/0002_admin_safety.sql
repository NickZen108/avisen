begin;

-- Prevent accidental removal of the final application administrator.
-- Platform-owner access (Supabase/Cloudflare/GitHub) remains an independent recovery path.
create or replace function public.prevent_last_admin_removal()
returns trigger
language plpgsql
security definer
set search_path = public
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

  select count(*) into admin_count
  from public.user_roles
  where role = 'admin';

  if admin_count <= 1 then
    raise exception 'Cannot remove the final Morgentidende admin';
  end if;

  return coalesce(new, old);
end;
$$;

drop trigger if exists protect_final_admin on public.user_roles;
create trigger protect_final_admin
before delete or update of role on public.user_roles
for each row execute function public.prevent_last_admin_removal();

-- Helper view for platform diagnostics. RLS on user_roles still applies to normal users.
create or replace view public.admin_count as
select count(*)::integer as count
from public.user_roles
where role = 'admin';

commit;
