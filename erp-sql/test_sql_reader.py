import io,json,unittest
from sql_reader import SQLReader,PROJECT_URL,disposition

class ReaderTests(unittest.TestCase):
    def test_wrong_account_and_public_key(self):
        with self.assertRaises(ValueError):SQLReader('https://davnwqvcbailwydlkqni.supabase.co','private-placeholder')
        with self.assertRaises(ValueError):SQLReader(PROJECT_URL,'sb_publishable_placeholder')
    def test_get_only_paginated(self):
        calls=[]
        def opener(req,timeout):
            calls.append(req)
            offset=0 if len(calls)==1 else 500
            n=500 if offset==0 else 1
            return io.StringIO(json.dumps([dict(row_id=f'{i:05}',data={}) for i in range(offset,offset+n)]))
        rows=SQLReader(PROJECT_URL,'private-placeholder',opener).rows()
        self.assertEqual(len(rows),501);self.assertTrue(all(r.get_method()=='GET' for r in calls));self.assertIn('offset=500',calls[1].full_url)
    def test_no_old_import_automatically_approved(self):
        row=dict(row_id='old',data={'ERP Status':'Pending','Production Qty':1})
        self.assertEqual(disposition(row),'Not approved for controlled ERP test')
        row['data']['Remarks']='Test   Only';self.assertEqual(disposition(row,{'old'}),'TEST ONLY - excluded')
        row['erp_closed']=True;self.assertEqual(disposition(row,{'old'}),'ERP closed')
    def test_repeated_page_rejected(self):
        page=[dict(row_id=f'{i:05}',data={}) for i in range(500)]
        with self.assertRaises(RuntimeError):SQLReader(PROJECT_URL,'private-placeholder',lambda *a,**k:io.StringIO(json.dumps(page))).rows()

if __name__=='__main__':unittest.main()
