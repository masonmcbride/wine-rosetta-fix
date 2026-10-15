"""Reject misleading CPU attribution and preserve uncovered/unknown costs."""
import csv,json,pathlib,tempfile,unittest
from analyze_mach import analyze
class AccountingChecks(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=pathlib.Path(self.tmp.name)/'pcs.csv'
 def capture(self,threads,samples):
  pathlib.Path(str(self.path)+'.stats.json').write_text(json.dumps(dict(threads=threads,failures=0,overflow=0)))
  with self.path.open('w') as f:
   w=csv.DictWriter(f,fieldnames=['pc','base','module','tid','time','user_us','system_us']);w.writeheader()
   for tid,u,s in samples:w.writerow(dict(pc='0x1',base='0x0',module='UNKNOWN',tid=tid,time=0,user_us=u,system_us=s))
  return analyze(self.path)
 def test_unknown_cost_and_tail_are_preserved(self):
  r=self.capture([dict(tid=1,first_user_us=100,first_system_us=10,cpu_us=100)],[(1,150,20),(1,170,25)])
  self.assertEqual(r['attributed_cpu_us'],85);self.assertEqual(r['unattributed_cpu_us'],15);self.assertEqual(r['unresolved_attributed_cpu_us'],85)
 def test_threads_have_independent_cpu_baselines(self):
  r=self.capture([dict(tid=1,first_user_us=10,first_system_us=0,cpu_us=40),dict(tid=2,first_user_us=1000,first_system_us=0,cpu_us=10)],[(1,50,0),(2,1010,0)])
  self.assertEqual(r['attributed_cpu_us'],50);self.assertEqual(r['per_thread']['2']['user_us'],10)
 def test_backwards_cpu_counters_rejected(self):
  with self.assertRaisesRegex(ValueError,'backwards'):
   self.capture([dict(tid=1,first_user_us=100,first_system_us=0,cpu_us=10)],[(1,90,0)])
if __name__=='__main__':unittest.main()
