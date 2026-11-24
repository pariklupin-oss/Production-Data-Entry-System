import copy
import tempfile
import unittest
from pathlib import Path
from bridge import Journal, execute, ReconcileRequired

class Adapter:
    def __init__(self): self.submits=0; self.fail_submit=False; self.fail_ack=False; self.found=True; self.bad=False; self.acks=0
    def submit(self,row):
        self.submits+=1
        if self.fail_submit: raise TimeoutError('uncertain submit')
    def verify(self,row):
        if not self.found:return None
        d=row['data'];return dict(source_id=row['row_id'],wo=d['WO No'],jc=d['JC No'],pp=d['PP Code'],quantity=999 if self.bad else d['Production Qty'],erp_lot_id='ERP-LOT-1')
    def ack(self,row,receipt):
        self.acks+=1
        if self.fail_ack:raise ConnectionError('SQL offline')

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'journal.db';self.j=Journal(self.path);self.a=Adapter()
        self.row=dict(row_id='lot-1',revision=3,data={'WO No':'WO1','JC No':'JC1','PP Code':'PP1','Production Qty':600,'ERP Status':'Pending','Production Date':'2026-10-10','Start Time':'08:00','End Time':'09:00','Remarks':''})
    def tearDown(self):self.j.close();self.tmp.cleanup()
    def test_retry_after_success(self):
        self.assertEqual(execute(self.row,self.j,self.a,self.a),'acknowledged');self.assertEqual(execute(self.row,self.j,self.a,self.a),'already_acknowledged');self.assertEqual(self.a.submits,1)
    def test_restart_after_uncertain_erp(self):
        self.a.fail_submit=True
        with self.assertRaises(TimeoutError):execute(self.row,self.j,self.a,self.a)
        self.j.close();self.j=Journal(self.path);self.a.fail_submit=False
        self.assertEqual(execute(self.row,self.j,self.a,self.a),'acknowledged');self.assertEqual(self.a.submits,1)
    def test_sql_outage_does_not_repeat_erp(self):
        self.a.fail_ack=True
        with self.assertRaises(ConnectionError):execute(self.row,self.j,self.a,self.a)
        self.a.fail_ack=False;execute(self.row,self.j,self.a,self.a);self.assertEqual(self.a.submits,1)
    def test_unknown_receipt_never_resubmits(self):
        self.a.found=False
        for _ in range(2):
            with self.assertRaises(ReconcileRequired):execute(self.row,self.j,self.a,self.a)
        self.assertEqual(self.a.submits,1);self.assertEqual(self.a.acks,0)
    def test_revision_and_receipt_mismatch(self):
        self.a.bad=True
        with self.assertRaises(ReconcileRequired):execute(self.row,self.j,self.a,self.a)
        changed=copy.deepcopy(self.row);changed['revision']=4
        with self.assertRaises(ReconcileRequired):execute(changed,self.j,self.a,self.a)
        self.assertEqual(self.a.submits,1);self.assertEqual(self.a.acks,0)
    def test_closed_and_test_only(self):
        self.row['data']['Remarks']='test only';self.assertEqual(execute(self.row,self.j,self.a,self.a),'excluded')
        self.row['data']['Remarks']='';self.row['erp_closed']=True;self.assertEqual(execute(self.row,self.j,self.a,self.a),'excluded');self.assertEqual(self.a.submits,0)
    def test_two_workers_share_claim(self):
        second=Journal(self.path)
        try:
            self.assertTrue(self.j.claim(self.row)[0]);self.assertFalse(second.claim(self.row)[0])
        finally:second.close()

if __name__=='__main__':unittest.main()
