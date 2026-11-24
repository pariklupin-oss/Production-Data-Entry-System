import unittest
from erp_planning_to_sql import build_route
class Routes(unittest.TestCase):
 def setUp(self):
  self.job={'WO No':'WO1','JC No':'1','Item Code':'IT1','PP Code':'PP_100','Plan Qty':'1000'}
  self.route=[{'pp_code':'PP_100','process_name':'CORRUGATION','ups':3},{'pp_code':'PP_180','process_name':'PRINTING'},{'pp_code':'PP_205','process_name':'AUTO STITCHING'},{'pp_code':'PP_206','process_name':'STRAPPING BUNDLING'},{'pp_code':'PP_210','process_name':'OUTWARD QUALITY CHECK'}]
 def test_real_sequence_and_stable_ids(self):
  rows=build_route(self.job,self.route,'2026-10-10');self.assertEqual(rows[2]['data']['Destination'],'STRAPPING BUNDLING');self.assertEqual(rows[1]['data']['PP Code'],'PP_180');self.assertEqual(rows[-1]['data']['Route Sequence'],5);self.assertEqual(rows[0]['row_id'],build_route(self.job,self.route,'2026-10-11')[0]['row_id'])
 def test_incomplete_route_and_guessed_pp_rejected(self):
  with self.assertRaises(ValueError):build_route(self.job,[],'2026-10-10')
  self.route[1]['pp_code']=''
  with self.assertRaises(ValueError):build_route(self.job,self.route,'2026-10-10')
 def test_missing_ups_rejected(self):
  self.route[0].pop('ups')
  with self.assertRaises(ValueError):build_route(self.job,self.route,'2026-10-10')
if __name__=='__main__':unittest.main()
