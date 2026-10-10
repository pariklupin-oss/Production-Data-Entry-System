import unittest
from finishing import next_lot, ReconcileRequired

def row(rid, process, pp, qty='', status='Pending', revision=1, **extra):
 return {'row_id':rid,'revision':revision,'erp_closed':False,'data':{'WO No':'WO1','JC No':'JC1','Process Name':process,'PP Code':pp,'Production Qty':qty,'ERP Status':status,'Production Date':'2026-10-10','Start Time':'08:00','End Time':'09:00',**extra}}
class Lots(unittest.TestCase):
 def setUp(self):
  self.first=row('lot600','FOLDER GLUER','p3',600,'Partial'); self.last=row('lot400','FOLDER GLUER','p3',400,'Submitted'); self.strap=row('strap-template','STRAPPING BUNDLING M/C','p4'); self.qc=row('qc-template','OUTWARD QUALITY CHECK','p5');self.route=[self.first,self.last,self.strap,self.qc]
 def test_partial_actual_lots(self):
  self.assertEqual([next_lot(s,self.route)['quantity'] for s in [self.first,self.last]],[600,400])
 def test_retry_and_revision(self):
  links=[{'source_id':'lot600','target_pp':'p4','source_revision':1,'target_row_id':'queued600'}]
  self.assertIsNone(next_lot(self.first,self.route,links));self.first['revision']=2
  with self.assertRaises(ReconcileRequired):next_lot(self.first,self.route,links)
 def test_qc_waits_for_strapping(self):
  strap=row('strap600','STRAPPING BUNDLING','p4',600,'Pending')
  self.assertIsNone(next_lot(strap,self.route));strap['data']['ERP Status']='Partial'
  self.assertEqual(next_lot(strap,self.route)['target_pp'],'p5')
 def test_wrong_stage_and_ambiguity(self):
  self.assertIsNone(next_lot(row('print','PRINTING','p2',600,'Submitted'),self.route))
  with self.assertRaises(ReconcileRequired):next_lot(self.first,self.route+[row('other','AUTO STITCHING','different')])
 def test_closed_and_test_only(self):
  self.first['erp_closed']=True;self.assertIsNone(next_lot(self.first,self.route));self.first['erp_closed']=False;self.first['data']['Remarks']='TEST ONLY — DO NOT PUSH ERP';self.assertIsNone(next_lot(self.first,self.route))
 def test_legacy_is_not_assumed(self):
  self.strap['data'].update({'ERP Status':'Submitted','Production Qty':600})
  with self.assertRaises(ReconcileRequired):next_lot(self.first,self.route)
if __name__=='__main__':unittest.main()
