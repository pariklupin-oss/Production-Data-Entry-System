"""Pure automatic-lot planning. No ERP calls and no network at import time."""
import re
from decimal import Decimal, InvalidOperation
AUTO = re.compile(r'STRAPP?ING|BUNDLING|OUTWARD.*QUALITY|QUALITY.*CHECK|\bOQC\b', re.I)
DONE = {'submitted', 'partial'}
class ReconcileRequired(ValueError):
    pass

def stage(row):
    name = str(row.get('Process Name', '')).upper()
    if 'STRAP' in name or 'BUNDL' in name: return 4
    if 'QUALITY' in name or 'OQC' in name or 'OUTWARD' in name: return 5
    if 'CORRUGAT' in name or 'BOARDLINE' in name: return 1
    if 'PRINT' in name or 'SLOT' in name: return 2
    return 3

def quantity(value):
    try: q = Decimal(str(value))
    except InvalidOperation: raise ReconcileRequired('Invalid production quantity')
    if not q.is_finite() or q <= 0 or q != q.to_integral_value():
        raise ReconcileRequired('Positive integer production required')
    return int(q)

def next_lot(source, records, links=()):
    """Return ONE next automatic lot, only after predecessor ERP acknowledgement.

    source/records use SQL {row_id, revision, erp_closed, data}. An ambiguous
    process route or legacy unlinked output raises instead of silently guessing.
    """
    data = source['data']
    if source.get('erp_closed') or str(data.get('ERP Status','')).lower() not in DONE:
        return None
    if 'TEST ONLY' in str(data.get('Remarks','')).upper(): return None
    wo, jc = str(data.get('WO No','')).strip(), str(data.get('JC No','')).strip()
    if not wo or not jc or not source.get('row_id'): raise ReconcileRequired('Stable source identity required')
    route = [r for r in records if str(r['data'].get('WO No','')).strip()==wo and str(r['data'].get('JC No','')).strip()==jc and not r.get('erp_closed')]
    if any(r.get('erp_closed') for r in records if str(r['data'].get('WO No','')).strip()==wo and str(r['data'].get('JC No','')).strip()==jc):
        raise ReconcileRequired('Conflicting ERP closure statuses')
    current = stage(data)
    stages = {stage(r['data']) for r in route}
    if current == 5: return None
    target_stage = 5 if current == 4 else (4 if 4 in stages else 5)
    if target_stage not in stages: return None
    if current < 4:
        last_manual = max((s for s in stages if s < 4), default=0)
        if current != last_manual: return None
        candidates = {str(r['data'].get('PP Code','')).strip() for r in route if stage(r['data'])==last_manual}
        if len(candidates)!=1: raise ReconcileRequired('Manual predecessor is ambiguous')
    candidates = [r for r in route if stage(r['data'])==target_stage]
    pps = {str(r['data'].get('PP Code','')).strip() for r in candidates}
    if len(pps)!=1 or '' in pps: raise ReconcileRequired('Automatic target PP is ambiguous')
    target_pp = next(iter(pps))
    identity = (source['row_id'], target_pp)
    for link in links:
        if (link['source_id'],link['target_pp'])==identity:
            if int(link['source_revision'])!=int(source['revision']):
                raise ReconcileRequired('Acknowledged source was revised; reconcile existing downstream lot')
            return None
    # Legacy ERP output without a stable link must be reconciled, never inferred
    # from matching quantity/time because two legitimate lots can match exactly.
    for row in candidates:
        rdata=row['data']
        if str(rdata.get('ERP Status','')).lower() in DONE and not any(l['target_row_id']==row['row_id'] for l in links):
            raise ReconcileRequired('Legacy target output has no source link')
    q = quantity(data.get('Production Qty'))
    for field in ('Production Date','Start Time','End Time'):
        if not data.get(field): raise ReconcileRequired('Source production timing required')
    return {'source_id':source['row_id'], 'source_revision':int(source['revision']),
            'target_pp':target_pp, 'quantity':q, 'target_stage':target_stage}
