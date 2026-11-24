-- STAGED, TEST ONLY. Install after SQL review; no ERP submission performed.
begin;
create table if not exists public.planning_finishing_links_test(
 source_id text not null references public.production_planning_test(row_id),
 target_pp text not null,
 source_revision bigint not null,
 target_row_id text not null unique references public.production_planning_test(row_id),
 created_at timestamptz not null default now(),
 primary key(source_id,target_pp)
);
alter table public.planning_finishing_links_test enable row level security;
revoke all on public.planning_finishing_links_test from public,anon,authenticated;
grant select,insert on public.planning_finishing_links_test to service_role;
create or replace function public.planning_route_stage_test(p jsonb)
returns integer language sql immutable set search_path='' as $$
select case when coalesce(p->>'Process Name','') ~* 'STRAP|BUNDL' then 4
 when coalesce(p->>'Process Name','') ~* 'QUALITY|OQC|OUTWARD' then 5
 when coalesce(p->>'Process Name','') ~* 'CORRUGAT|BOARDLINE' then 1
 when coalesce(p->>'Process Name','') ~* 'PRINT|SLOT' then 2 else 3 end;
$$;
revoke all on function public.planning_route_stage_test(jsonb) from public,anon,authenticated;
grant execute on function public.planning_route_stage_test(jsonb) to service_role;
create or replace function public.planning_enqueue_finishing_test(p_source text,p_expected bigint,p_target_pp text)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare src public.production_planning_test; tpl public.production_planning_test;
 prior public.planning_finishing_links_test; st integer; next_st integer; last_manual integer;
 target_count integer; source_count integer; q numeric; new_id text; body jsonb;
begin
 select * into src from public.production_planning_test where row_id=p_source for update;
 if not found or src.revision<>p_expected then raise exception 'Source missing or revised'; end if;
 if src.erp_closed or lower(coalesce(src.data->>'ERP Status','')) not in ('submitted','partial') then raise exception 'Confirmed open source lot required'; end if;
 if upper(coalesce(src.data->>'Remarks','')) like '%TEST ONLY%' then raise exception 'TEST ONLY lot excluded'; end if;
 if coalesce(src.data->>'WO No','')='' or coalesce(src.data->>'JC No','')='' then raise exception 'Source job identity missing'; end if;
 perform pg_advisory_xact_lock(hashtextextended(concat_ws('|',src.data->>'WO No',src.data->>'JC No'),0));
 select * into prior from public.planning_finishing_links_test where source_id=p_source and target_pp=p_target_pp;
 if found then
  if prior.source_revision<>p_expected then raise exception 'Source revised after downstream lot creation; reconcile'; end if;
  return jsonb_build_object('id',prior.target_row_id,'already_exists',true);
 end if;
 if exists(select 1 from public.production_planning_test r where r.data->>'WO No'=src.data->>'WO No' and r.data->>'JC No'=src.data->>'JC No' and r.erp_closed) then raise exception 'ERP job closed'; end if;
 st=public.planning_route_stage_test(src.data);
 if st=5 then raise exception 'No next automatic process'; end if;
 select case when st=4 then 5 when exists(select 1 from public.production_planning_test r where r.data->>'WO No'=src.data->>'WO No' and r.data->>'JC No'=src.data->>'JC No' and public.planning_route_stage_test(r.data)=4) then 4 else 5 end into next_st;
 if st<4 then
  select max(public.planning_route_stage_test(r.data)) into last_manual from public.production_planning_test r where r.data->>'WO No'=src.data->>'WO No' and r.data->>'JC No'=src.data->>'JC No' and public.planning_route_stage_test(r.data)<4;
  if st<>last_manual then raise exception 'Source is not last manual route stage'; end if;
  select count(distinct r.data->>'PP Code') into source_count from public.production_planning_test r where r.data->>'WO No'=src.data->>'WO No' and r.data->>'JC No'=src.data->>'JC No' and public.planning_route_stage_test(r.data)=st;
  if source_count<>1 then raise exception 'Ambiguous manual predecessor'; end if;
 end if;
 select count(distinct r.data->>'PP Code') into target_count from public.production_planning_test r where r.data->>'WO No'=src.data->>'WO No' and r.data->>'JC No'=src.data->>'JC No' and public.planning_route_stage_test(r.data)=next_st;
 if target_count<>1 or coalesce(p_target_pp,'')='' then raise exception 'Ambiguous automatic target'; end if;
 select * into tpl from public.production_planning_test r where r.data->>'WO No'=src.data->>'WO No' and r.data->>'JC No'=src.data->>'JC No' and r.data->>'PP Code'=p_target_pp and public.planning_route_stage_test(r.data)=next_st order by (r.source_row=0),r.source_row,r.row_id limit 1;
 if not found then raise exception 'Automatic target absent from route'; end if;
 if exists(select 1 from public.production_planning_test r where r.data->>'WO No'=src.data->>'WO No' and r.data->>'JC No'=src.data->>'JC No' and r.data->>'PP Code'=p_target_pp and lower(r.data->>'ERP Status') in ('submitted','partial') and not exists(select 1 from public.planning_finishing_links_test l where l.target_row_id=r.row_id)) then raise exception 'Legacy output without source mapping; reconcile before enqueue'; end if;
 q=(src.data->>'Production Qty')::numeric;
 if q is null or q<=0 or q<>trunc(q) or q>2147483647 then raise exception 'Invalid source output'; end if;
 if coalesce(src.data->>'Production Date','')='' or coalesce(src.data->>'Start Time','')='' or coalesce(src.data->>'End Time','')='' then raise exception 'Source timing missing'; end if;
 new_id=replace(gen_random_uuid()::text,'-','');
 body=tpl.data||jsonb_build_object('Row ID',new_id,'Date',src.data->>'Date','Production Date',src.data->>'Production Date','Start Time',src.data->>'Start Time','End Time',src.data->>'End Time','Input Qty',q,'Production Qty',q,'Rej Qty',0,'No of Pallets',0,'ERP Status','Pending','Job Status','Open','Remarks','[SRC:'||p_source||']');
 insert into public.production_planning_test(row_id,source_row,data) values(new_id,0,body);
 insert into public.planning_finishing_links_test(source_id,target_pp,source_revision,target_row_id) values(p_source,p_target_pp,p_expected,new_id);
 return jsonb_build_object('id',new_id,'already_exists',false,'status','Pending','quantity',q);
end $$;
revoke all on function public.planning_enqueue_finishing_test(text,bigint,text) from public,anon,authenticated;
grant execute on function public.planning_enqueue_finishing_test(text,bigint,text) to service_role;
commit;
