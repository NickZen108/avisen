-- Pipeline v3 AI budget guard.
-- Applied to production on 2026-09-04. Git copy is the canonical schema record.

create table if not exists public.ai_daily_budget (
  budget_date date primary key,
  spent_dkk numeric(12,6) not null default 0,
  reserved_dkk numeric(12,6) not null default 0,
  updated_at timestamptz not null default now(),
  constraint ai_daily_budget_nonnegative check (spent_dkk >= 0 and reserved_dkk >= 0)
);

create table if not exists public.ai_budget_reservations (
  reservation_id text primary key,
  budget_date date not null references public.ai_daily_budget(budget_date) on delete cascade,
  run_id text,
  stage text,
  reserved_dkk numeric(12,6) not null,
  actual_dkk numeric(12,6),
  status text not null default 'reserved' check (status in ('reserved','settled')),
  created_at timestamptz not null default now(),
  settled_at timestamptz
);

alter table public.ai_daily_budget enable row level security;
alter table public.ai_budget_reservations enable row level security;

create or replace function public.reserve_ai_budget(
  p_reservation_id text,
  p_budget_date date,
  p_amount_dkk numeric,
  p_run_id text,
  p_stage text,
  p_operational_limit_dkk numeric default 9.0
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  b public.ai_daily_budget%rowtype;
  existing public.ai_budget_reservations%rowtype;
begin
  if p_amount_dkk is null or p_amount_dkk <= 0 then
    raise exception 'reservation amount must be positive';
  end if;
  if p_operational_limit_dkk <= 0 or p_operational_limit_dkk > 10 then
    raise exception 'operational limit must be in (0,10]';
  end if;

  insert into public.ai_daily_budget(budget_date) values (p_budget_date)
  on conflict (budget_date) do nothing;

  select * into b from public.ai_daily_budget where budget_date = p_budget_date for update;
  select * into existing from public.ai_budget_reservations where reservation_id = p_reservation_id;
  if found then
    return jsonb_build_object(
      'ok', existing.status = 'reserved',
      'duplicate', true,
      'spent_dkk', b.spent_dkk,
      'reserved_dkk', b.reserved_dkk,
      'remaining_hard_dkk', greatest(0, 10 - b.spent_dkk - b.reserved_dkk)
    );
  end if;

  if b.spent_dkk + b.reserved_dkk + p_amount_dkk > p_operational_limit_dkk then
    return jsonb_build_object(
      'ok', false,
      'reason', 'daily_budget_guard',
      'spent_dkk', b.spent_dkk,
      'reserved_dkk', b.reserved_dkk,
      'requested_dkk', p_amount_dkk,
      'operational_limit_dkk', p_operational_limit_dkk,
      'hard_limit_dkk', 10,
      'remaining_hard_dkk', greatest(0, 10 - b.spent_dkk - b.reserved_dkk)
    );
  end if;

  update public.ai_daily_budget
     set reserved_dkk = reserved_dkk + p_amount_dkk, updated_at = now()
   where budget_date = p_budget_date
   returning * into b;

  insert into public.ai_budget_reservations(reservation_id,budget_date,run_id,stage,reserved_dkk)
  values (p_reservation_id,p_budget_date,p_run_id,p_stage,p_amount_dkk);

  return jsonb_build_object(
    'ok', true,
    'spent_dkk', b.spent_dkk,
    'reserved_dkk', b.reserved_dkk,
    'remaining_hard_dkk', greatest(0, 10 - b.spent_dkk - b.reserved_dkk)
  );
end;
$$;

create or replace function public.settle_ai_budget(
  p_reservation_id text,
  p_actual_dkk numeric,
  p_charge_reservation boolean default false
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  r public.ai_budget_reservations%rowtype;
  b public.ai_daily_budget%rowtype;
  charge numeric(12,6);
begin
  select * into r from public.ai_budget_reservations where reservation_id = p_reservation_id for update;
  if not found then raise exception 'unknown reservation'; end if;
  select * into b from public.ai_daily_budget where budget_date = r.budget_date for update;

  if r.status = 'settled' then
    return jsonb_build_object('ok', true, 'duplicate', true, 'spent_dkk', b.spent_dkk, 'reserved_dkk', b.reserved_dkk);
  end if;

  charge := case
    when p_charge_reservation then r.reserved_dkk
    else greatest(0, coalesce(p_actual_dkk, 0))
  end;

  update public.ai_daily_budget
     set reserved_dkk = greatest(0, reserved_dkk - r.reserved_dkk),
         spent_dkk = spent_dkk + charge,
         updated_at = now()
   where budget_date = r.budget_date
   returning * into b;

  update public.ai_budget_reservations
     set actual_dkk = charge, status = 'settled', settled_at = now()
   where reservation_id = p_reservation_id;

  return jsonb_build_object(
    'ok', true,
    'spent_dkk', b.spent_dkk,
    'reserved_dkk', b.reserved_dkk,
    'hard_limit_dkk', 10,
    'remaining_hard_dkk', greatest(0, 10 - b.spent_dkk - b.reserved_dkk),
    'over_hard_limit', b.spent_dkk + b.reserved_dkk > 10
  );
end;
$$;

revoke all on function public.reserve_ai_budget(text,date,numeric,text,text,numeric) from public, anon, authenticated;
revoke all on function public.settle_ai_budget(text,numeric,boolean) from public, anon, authenticated;
grant execute on function public.reserve_ai_budget(text,date,numeric,text,text,numeric) to service_role;
grant execute on function public.settle_ai_budget(text,numeric,boolean) to service_role;
