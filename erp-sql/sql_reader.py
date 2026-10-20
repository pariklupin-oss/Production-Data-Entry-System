"""Read-only Supabase test reader. Does not import ERP or expose credentials."""
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_URL = 'https://axgyeppfrcmhwrpxztvv.supabase.co'

class SQLReader:
    def __init__(self, url, key, opener=urlopen):
        if url.rstrip('/') != PROJECT_URL:
            raise ValueError('Only the pariklupin test project is permitted')
        if not key or key.startswith('sb_publishable_'):
            raise ValueError('Private worker credential must be configured locally; never use the mobile publishable key')
        self.url=PROJECT_URL; self.key=key; self.opener=opener

    def rows(self):
        result=[]; last=''
        for offset in range(0,100001,500):
            req=Request(self.url+'/rest/v1/production_planning_test?select=row_id,revision,source_row,data,erp_closed&order=row_id.asc&limit=500&offset='+str(offset),headers={'apikey':self.key,'Authorization':'Bearer '+self.key,'Accept':'application/json'},method='GET')
            try:
                with self.opener(req,timeout=30) as response:
                    page=json.load(response)
            except (HTTPError,URLError):
                raise RuntimeError('SQL read failed. Check local worker credentials/network; no entry was submitted.') from None
            if not isinstance(page,list):raise RuntimeError('Unexpected SQL response')
            for row in page:
                if not isinstance(row,dict) or not isinstance(row.get('data'),dict) or not row.get('row_id') or row['row_id']<=last:
                    raise RuntimeError('SQL page changed or repeated; retry read later')
                last=row['row_id']
            result.extend(page)
            if len(page)<500:return result
        raise RuntimeError('SQL read limit reached')

def disposition(row, approved_ids=()):
    d=row['data']
    if row.get('erp_closed'):return 'ERP closed'
    if re.search(r'TEST\s*ONLY',str(d.get('Remarks','')),re.I):return 'TEST ONLY - excluded'
    if str(d.get('ERP Status','')).strip().lower() not in ('pending','override'):return 'Not pending ERP'
    if row['row_id'] not in approved_ids:return 'Not approved for controlled ERP test'
    if not all(str(d.get(k,'')).strip() for k in ('WO No','JC No','PP Code','Production Date','Start Time','End Time')):return 'Identity/timing incomplete'
    q=d.get('Production Qty')
    try:
        valid=not isinstance(q,bool) and float(q)>0 and float(q).is_integer()
    except (TypeError,ValueError):valid=False
    if not valid:return 'Quantity incomplete'
    return 'Ready for review - no ERP submission'

if __name__=='__main__':
    try:
        reader=SQLReader(os.environ.get('STARISH_SUPABASE_URL',PROJECT_URL),os.environ.get('STARISH_SQL_WORKER_KEY',''))
        counts={}
        for row in reader.rows():
            state=disposition(row);counts[state]=counts.get(state,0)+1
        print(json.dumps(counts,indent=2))
        print('READ ONLY: no ERP submit, no SQL write, no watcher started.')
    except (ValueError,RuntimeError) as error:
        print(str(error));raise SystemExit(1)
