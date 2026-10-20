"""Corrugation Excel -> ERP WO process route -> isolated SQL planning.
Factory-PC only. Uses existing local ERP reader functions; never runs its main.
Default produces preview. --apply inserts missing processes only, retaining all
existing SQL/operator rows. No production submissions and no Google Sheet calls.
"""
import argparse,importlib.util,json,os,re,sys,uuid
from datetime import datetime
from pathlib import Path
from urllib.request import Request
from sql_reader import SQLReader,PROJECT_URL
ROOT=Path(r'D:\PRODUCTION AUTOMATION\EXCEL FILE')

def build_route(job,processes,plan_date):
    for k in ('WO No','JC No','Item Code','PP Code','Plan Qty'):
        if not str(job.get(k,'')).strip():raise ValueError(f'Missing planning {k}')
    if not processes:raise ValueError('ERP route missing; no corrugation-only fallback')
    codes=[str(p.get('pp_code','')).strip() for p in processes]
    if any(not re.fullmatch(r'PP_\d+',c) for c in codes) or len(codes)!=len(set(codes)):raise ValueError('Actual unique ERP PP Codes required; no sequential-code guessing')
    if codes[0]!=job['PP Code']:raise ValueError('Corrugation planning PP differs from ERP route')
    qty=int(str(job['Plan Qty']).replace(',',''))
    if qty<=0:raise ValueError('Positive plan quantity required')
    rows=[]
    for i,p in enumerate(processes):
        proc=str(p.get('process_name','')).strip()
        if not proc:raise ValueError('ERP process name missing')
        corr=bool(re.search('CORRUGAT|BOARDLINE',proc,re.I))
        ups=p.get('ups') or (None if corr else 1)
        if corr and not ups:raise ValueError('ERP corrugation UPS missing; route withheld')
        ups=int(ups)
        if ups<1:raise ValueError('UPS must be positive')
        rid=uuid.uuid5(uuid.NAMESPACE_URL,json.dumps([job['WO No'],job['JC No'],codes[i]],separators=(',',':'))).hex
        data={k:job.get(k,'') for k in ('WO No','JC No','Customer','Item Code','Model Name')}
        data.update({'Row ID':rid,'Date':job.get('Schedule Date') or plan_date,'PP Code':codes[i],'Process Name':proc,'Machine Name':p.get('machine_name') or proc,'Plan Qty':qty,'UPS':ups,'Route Sequence':i+1,'Destination':processes[i+1]['process_name'] if i+1<len(processes) else '', 'ERP Status':'Pending','Job Status':'Open','Production Date':'','Start Time':'','End Time':'','Input Qty':'','Production Qty':'','Rej Qty':'','No of Pallets':'','Remarks':''})
        rows.append({'row_id':rid,'source_row':i+1,'data':data})
    return rows

def insert_missing(rows,reader):
    before=reader.rows()
    # Existing sheet-seeded IDs differ from stable ERP IDs: match full WO+JC+PP.
    identities={(str(r['data'].get('WO No','')),str(r['data'].get('JC No','')),str(r['data'].get('PP Code',''))) for r in before}
    missing=[r for r in rows if tuple(str(r['data'][k]) for k in ('WO No','JC No','PP Code')) not in identities]
    for start in range(0,len(missing),250):
        req=Request(PROJECT_URL+'/rest/v1/production_planning_test?on_conflict=row_id',method='POST',data=json.dumps(missing[start:start+250]).encode(),headers={'apikey':reader.key,'Authorization':'Bearer '+reader.key,'Content-Type':'application/json','Prefer':'resolution=ignore-duplicates,return=minimal'})
        with reader.opener(req,timeout=60) as response:response.read()
    after=reader.rows();present={(str(r['data'].get('WO No','')),str(r['data'].get('JC No','')),str(r['data'].get('PP Code',''))) for r in after}
    if any(tuple(str(r['data'][k]) for k in ('WO No','JC No','PP Code')) not in present for r in rows):raise RuntimeError('SQL route verification failed')
    return {'processes_verified':len(rows),'missing_processes_requested':len(missing),'existing_processes_retained':len(rows)-len(missing)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--date',required=True,help='DD-MM-YYYY');parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    target=datetime.strptime(args.date,'%d-%m-%Y').strftime('%Y-%m-%d')
    legacy_path=ROOT/'erp_to_gsheet.py'
    if not legacy_path.is_file():raise ValueError('Existing erp_to_gsheet.py not found in factory folder')
    sys.path.insert(0,str(ROOT))
    spec=importlib.util.spec_from_file_location('starish_existing_erp_reader',legacy_path);legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    jobs=legacy.read_planning_excel(args.date)
    if not jobs:raise ValueError('No Corrugation Planning jobs found for selected date')
    # Standard Selenium session. No anti-detection driver/fingerprint alterations.
    from selenium import webdriver
    driver=webdriver.Chrome();rows=[];errors=[]
    try:
        for job in jobs:
            try:
                processes=legacy.get_processes_from_plan_page(driver,job['WO No'],job['JC No'])
                rows.extend(build_route(job,processes,target))
            except Exception:errors.append({'wo':job.get('WO No'),'jc':job.get('JC No'),'reason':'ERP route/PP/UPS requires inspection'})
    finally:driver.quit()
    preview={'date':target,'job_cards':len(jobs),'processes':len(rows),'errors':errors,'rows':rows}
    Path('erp_planning_preview.json').write_text(json.dumps(preview,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in preview.items() if k!='rows'},indent=2))
    if errors:raise ValueError('Incomplete routes: preview saved; SQL import withheld for entire batch')
    if args.apply:
        reader=SQLReader(os.environ.get('STARISH_SUPABASE_URL',PROJECT_URL),os.environ.get('STARISH_SQL_WORKER_KEY',''))
        print(json.dumps(insert_missing(rows,reader),indent=2))
    else:print('Preview only. No SQL writes. Review erp_planning_preview.json before --apply.')
    print('No production entry submitted. No Google Sheet changed.')

if __name__=='__main__':
    try:main()
    except Exception:print('Planning fetch/import stopped. Review local preview and ERP route; no production submission performed.');raise SystemExit(1)
