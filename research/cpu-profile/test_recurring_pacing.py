import tempfile,unittest
from pathlib import Path
from analyze_recurring_pacing import integrals
from compare_pacing_gpu import gpu_union

class RecurrenceTests(unittest.TestCase):
    def test_exact_prefixes_and_unobserved_gap(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.csv';p.write_text('start_ns,end_ns,tid,state\n0,10,7,Running\n10,20,7,Blocked\n30,40,7,Running\n')
            data,rows=integrals(p,[5,10,15,25,35,45]);self.assertEqual(rows,3)
            self.assertEqual(list(data['7']['prefix']['Running']),[5,10,10,10,15,20])
            self.assertEqual(list(data['7']['prefix']['Blocked']),[0,0,5,10,10,10])
            self.assertEqual(25-sum(v[3] for v in data['7']['prefix'].values()),5)

    def test_overlapping_scheduler_intervals_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.csv';p.write_text('start_ns,end_ns,tid,state\n0,10,7,Running\n9,20,7,Blocked\n')
            with self.assertRaisesRegex(ValueError,'overlapping'):integrals(p,[0,10,20])

    def test_gpu_union_prefix_and_process_filter(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'g.xml';p.write_text('''<r><node>
            <row><start-time>0</start-time><duration>10</duration><duration>999</duration><process id="1"><pid>42</pid></process></row>
            <row><start-time>5</start-time><duration>10</duration><process ref="1"/></row>
            <row><start-time>15</start-time><duration>99</duration><process><pid>99</pid></process></row>
            </node></r>''')
            cdf=gpu_union(p,42)
            self.assertEqual([cdf(t) for t in [-1,0,7,12,15,100]],[0,0,7,12,15,15])

    def test_function_audit_keeps_raw_and_missing_leaves_unresolved(self):
        from audit_function_attribution import audit
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cpu.xml'
            p.write_text('''<r><node>
            <row><sample-time>5</sample-time><thread id="1"><process><pid>42</pid></process></thread><core/><thread-state/><sentinel/><kperf-bt fmt="PC:0x123, 1 frames"><text-address fmt="0x123">291</text-address></kperf-bt></row>
            <row><sample-time>6</sample-time><thread ref="1"/><core/><thread-state/><sentinel/><sentinel/></row>
            <row><sample-time>7</sample-time><thread><process><pid>99</pid></process></thread><core/><thread-state/><sentinel/><sentinel/></row>
            </node></r>''')
            result=audit(p,42,0,10)
            self.assertEqual(result['counts']['samples'],2)
            self.assertEqual(result['counts']['raw_pc_labels'],1)
            self.assertEqual(result['counts']['missing_user_backtrace'],1)
            self.assertEqual(result['verified_function_assembly_mappings'],0)

if __name__=='__main__':unittest.main()
