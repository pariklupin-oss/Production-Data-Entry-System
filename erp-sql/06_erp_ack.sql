-- STAGED TEST MIGRATION. No ERP call. Worker-only verified receipt acknowledgement.
begin;
create table if not exists public.planning_erp_receipts_test (
 source_id text primary key references public.production_planning_test(row_id),
 source_revision bigint not null,
 receipt jsonb not null,
 erp_lot_id text not null,
 wo text not null,
 jc text not null,
 pp text not null,
 acknowledged_at timestamptz not null default now(),
 unique(wo,jc,pp,erp_lot_id)
);
alter table public.planning_erp_receipts_test enable row level security;
revoke all on public.planning_erp_receipts_test from public,anon,authenticated;
grant select,insert on public.planning_erp_receipts_test to service_role;
create or replace function public.planning_ack_erp_test(p_source text,p_expected bigint,p_receipt jsonb)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare src public.production_planning_test; prior public.planning_erp_receipts_test;
 qty numeric; total_qty numeric; plan_qty numeric; status text; result_revision bigint;
begin
 select * into src from public.production_planning_test where row_id=p_source for update;
 if not found then raise exception 'Source missing'; end if;
 select * into prior from public.planning_erp_receipts_test where source_id=p_source;
 if found then
  if prior.source_revision<>p_expected or prior.receipt<>p_receipt then raise exception 'Different receipt or revision; reconcile'; end if;
  return jsonb_build_object('id',p_source,'already_acknowledged',true,'revision',src.revision);
 end if;
 if src.revision<>p_expected then raise exception 'Source changed during ERP submission; reconcile'; end if;
 if src.erp_closed then raise exception 'ERP job closed; reconcile'; end if;
 if coalesce(src.data->>'Remarks','') ~* 'TEST\s*ONLY' then raise exception 'TEST ONLY excluded'; end if;
 if lower(coalesce(src.data->>'ERP Status','')) not in ('pending','override') then raise exception 'Pending source required'; end if;
 if jsonb_typeof(p_receipt) is distinct from 'object' or not (p_receipt ?& array['source_id','wo','jc','pp','quantity','erp_lot_id']) then raise exception 'Complete verified receipt required'; end if;
 if p_receipt->>'source_id' is distinct from p_source
 or p_receipt->>'wo' is distinct from src.data->>'WO No'
 or p_receipt->>'jc' is distinct from src.data->>'JC No'
 or p_receipt->>'pp' is distinct from src.data->>'PP Code'
 or coalesce(p_receipt->>'erp_lot_id','')='' then raise exception 'Receipt identity mismatch'; end if;
 if coalesce(src.data->>'WO No','')='' or coalesce(src.data->>'JC No','')='' or coalesce(src.data->>'PP Code','')='' then raise exception 'Job identity missing'; end if;
 if jsonb_typeof(p_receipt->'quantity') is distinct from 'number' then raise exception 'Numeric receipt quantity required'; end if;
 qty=(src.data->>'Production Qty')::numeric;
 if qty is null or qty<=0 or qty<>trunc(qty) or qty<>(p_receipt->>'quantity')::numeric then raise exception 'Receipt quantity mismatch'; end if;
 -- A partial lot retains its actual quantity; no plan quantity is fabricated.
 plan_qty=nullif(src.data->>'Plan Qty','')::numeric;
 if plan_qty is null or plan_qty<=0 then raise exception 'Valid plan quantity required'; end if;
 perform pg_advisory_xact_lock(hashtextextended(concat_ws('|',src.data->>'WO No',src.data->>'JC No',src.data->>'PP Code'),0));
 select qty+coalesce(sum((r.receipt->>'quantity')::numeric),0) into total_qty from public.planning_erp_receipts_test r
 where r.wo=src.data->>'WO No' and r.jc=src.data->>'JC No' and r.pp=src.data->>'PP Code';
 status=case when total_qty>=plan_qty then 'Submitted' else 'Partial' end;
 insert into public.planning_erp_receipts_test(source_id,source_revision,receipt,erp_lot_id,wo,jc,pp)
 values(p_source,p_expected,p_receipt,p_receipt->>'erp_lot_id',src.data->>'WO No',src.data->>'JC No',src.data->>'PP Code');
 update public.production_planning_test set data=data||jsonb_build_object('ERP Status',status),revision=revision+1,updated_at=now()
 where row_id=p_source returning revision into result_revision;
 return jsonb_build_object('id',p_source,'already_acknowledged',false,'revision',result_revision,'status',status);
end $$;
revoke all on function public.planning_ack_erp_test(text,bigint,jsonb) from public,anon,authenticated;
grant execute on function public.planning_ack_erp_test(text,bigint,jsonb) to service_role;
commit;
