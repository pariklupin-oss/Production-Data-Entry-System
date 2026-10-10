-- STAGED: correct project axgyeppfrcmhwrpxztvv ONLY. Requires existing test table/RPC.
-- No live objects or ERP watcher are changed. No operator is enabled automatically.
begin;
alter table public.production_planning_test add column if not exists erp_closed boolean not null default false;
create table if not exists public.planning_direct_members (
 user_id uuid primary key references auth.users(id) on delete cascade,
 enabled boolean not null default false,
 role text not null default 'operator' check(role in ('operator','admin'))
);
alter table public.planning_direct_members enable row level security;
revoke all on public.planning_direct_members from anon,authenticated;
grant select on public.planning_direct_members to authenticated;
create policy planning_member_self on public.planning_direct_members for select to authenticated using(user_id=auth.uid());
alter table public.production_planning_test enable row level security;
revoke all on public.production_planning_test from anon,authenticated;
grant select on public.production_planning_test to authenticated;
create policy planning_direct_read on public.production_planning_test for select to authenticated using(exists(select 1 from public.planning_direct_members m where m.user_id=auth.uid() and m.enabled));
create or replace function public.planning_direct_mutate(p_action text,p_id text,p_expected bigint,p_data jsonb,p_request text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare access_role text; k text; v numeric; result jsonb; entry_date date;
begin
 select role into access_role from public.planning_direct_members where user_id=auth.uid() and enabled;
 if auth.uid() is null or access_role is null then raise exception 'Operator access required'; end if;
 if p_action is null or p_action not in ('save','extend','override') then raise exception 'Unsupported action'; end if;
 if p_action='override' and access_role<>'admin' then raise exception 'Administrator required for override'; end if;
 if p_id is null or length(p_id)>128 or p_expected is null or p_expected<1 then raise exception 'Job and revision required'; end if;
 if p_request is null or p_request !~ '^[a-zA-Z0-9-]{16,64}$' then raise exception 'Submission ID required'; end if;
 if p_data is null or jsonb_typeof(p_data)<>'object' or p_data-array['Start Time','End Time','Input Qty','Rej Qty','Production Qty','Production Date','Remarks','Destination','No of Pallets']<>'{}'::jsonb then raise exception 'Invalid entry fields'; end if;
 if not(p_data ?& array['Start Time','End Time','Input Qty','Rej Qty','Production Qty','Production Date','Remarks','Destination','No of Pallets']) then raise exception 'Incomplete entry'; end if;
 foreach k in array array['Start Time','End Time'] loop
  if jsonb_typeof(p_data->k)<>'string' or p_data->>k !~ '^([01][0-9]|2[0-3]):[0-5][0-9]$' then raise exception 'Invalid time'; end if;
 end loop;
 if jsonb_typeof(p_data->'Production Date')<>'string' or p_data->>'Production Date' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'Invalid date'; end if;
 entry_date=(p_data->>'Production Date')::date;
 if to_char(entry_date,'YYYY-MM-DD')<>p_data->>'Production Date' then raise exception 'Invalid date'; end if;
 foreach k in array array['Input Qty','Rej Qty','Production Qty','No of Pallets'] loop
  if jsonb_typeof(p_data->k)<>'number' then raise exception 'Invalid quantity'; end if;
  v=(p_data->>k)::numeric;
  if v<0 or v>2147483647 or (k<>'No of Pallets' and v<>trunc(v)) then raise exception 'Invalid quantity'; end if;
 end loop;
 if (p_data->>'Rej Qty')::numeric>(p_data->>'Input Qty')::numeric then raise exception 'Rejection exceeds input'; end if;
 if p_action='extend' and (p_data->>'Production Qty')::numeric<=0 then raise exception 'Extend production must exceed zero'; end if;
 foreach k in array array['Remarks','Destination'] loop
  if jsonb_typeof(p_data->k)<>'string' or length(p_data->>k)>1000 then raise exception 'Invalid text'; end if;
 end loop;
 perform 1 from public.production_planning_test where row_id=p_id for update;
 if exists(select 1 from public.production_planning_test where row_id=p_id and coalesce(data->>'Process Name','') ~* 'STRAPP?ING|BUNDLING|OUTWARD.*QUALITY|QUALITY.*CHECK|\yOQC\y') then raise exception 'Automatic process: operator entry is not allowed'; end if;
 if exists(select 1 from public.production_planning_test where row_id=p_id and (erp_closed or lower(data->>'Job Status')='closed')) then raise exception 'Job is closed'; end if;
 result=public.production_test_mutate(p_action,p_id,p_expected,p_data,auth.uid()::text||':'||p_request);
 return result;
end $$;
revoke all on function public.planning_direct_mutate(text,text,bigint,jsonb,text) from public,anon;
grant execute on function public.planning_direct_mutate(text,text,bigint,jsonb,text) to authenticated;
commit;
-- After creating a TEST login via Supabase Authentication, enable only that user:
-- insert into public.planning_direct_members(user_id,enabled,role)
-- select id,true,'admin' from auth.users where email='pariklupin@gmail.com'
-- on conflict(user_id) do update set enabled=true,role='admin';
