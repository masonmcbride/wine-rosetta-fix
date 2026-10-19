import csv,json,tempfile,unittest
from pathlib import Path
from extract_thread_states import extract
from correlate_thread_states import correlate
from analyze_stalls import analyze

class SchedulerTests(unittest.TestCase):
    def test_decode_references_filter_pid_and_clip(self):
        xml='''<trace-query-result><node>
        <row><start-time id="1">0</start-time><thread id="2" fmt="renderer"><tid>7</tid><process id="3"><pid>42</pid></process></thread><thread-state id="4" fmt="Running">Running</thread-state><duration id="5">10</duration><process ref="3"/></row>
        <row><start-time id="6">10</start-time><thread ref="2"/><thread-state fmt="Blocked">Blocked</thread-state><duration ref="5"/><process ref="3"/></row>
        <row><start-time ref="1"/><thread fmt="other"><tid>8</tid><process id="7"><pid>99</pid></process></thread><thread-state ref="4"/><duration ref="5"/><process ref="7"/></row>
        </node></trace-query-result>'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'in.xml').write_text(xml)
            summary=extract(p/'in.xml',p/'out.csv',42)
            self.assertEqual(summary['target_rows'],2)
            result=correlate(p/'out.csv',{'test':[5,15]})
            self.assertEqual(result['windows']['test']['threads']['7'],{'Running':5,'Blocked':5})
            self.assertEqual(result['overlapping_thread_intervals'],0)

    def test_missing_reference_is_rejected(self):
        from extract_thread_states import References
        import xml.etree.ElementTree as E
        with self.assertRaisesRegex(ValueError,'Missing XML reference'):
            References().decode(E.fromstring('<duration ref="77"/>'))

    def test_overlapping_coverage_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'states.csv';p.write_text('start_ns,end_ns,tid,state\n0,10,7,Running\n0,10,7,Blocked\n')
            with self.assertRaisesRegex(ValueError,'coverage exceeds'):
                correlate(p,{'test':[0,10]})

    def test_point_present_requests_are_counted_in_display_gap(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'toc.xml').write_text('<trace-toc><run><data><table schema="displayed-surfaces-interval"/><table schema="ca-client-present-request"/></data></run></trace-toc>')
            (p/'events.xml').write_text('''<trace-query-result><node xpath="table[1]">
            <row><start-time>0</start-time><duration>40000000</duration><display-name id="1">Display 1</display-name><process id="2"><pid>42</pid></process></row>
            <row><start-time>40000000</start-time><duration>1</duration><display-name ref="1"/><process ref="2"/></row></node>
            <node xpath="table[2]"><row><start-time>20000000</start-time><process ref="2"/></row></node></trace-query-result>''')
            result=analyze(p/'events.xml',p/'toc.xml',42)
            self.assertEqual(result['gaps'][0]['ca-client-present-request']['starts_in_gap'],1)

    def test_gpu_primary_duration_and_pid_filter(self):
        from correlate_gpu_windows import analyze as gpu_analyze
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'gpu.xml'
            p.write_text('''<trace-query-result><node>
            <row><start-time>0</start-time><duration>10</duration><duration>999</duration><process id="1"><pid>42</pid></process></row>
            <row><start-time>5</start-time><duration>10</duration><process ref="1"/></row>
            <row><start-time>0</start-time><duration>20</duration><process><pid>99</pid></process></row>
            </node></trace-query-result>''')
            result=gpu_analyze(p,{'clip':[0,20]},42)
            self.assertEqual(result['target_rows'],2)
            self.assertEqual(result['windows']['clip']['recorded_gpu_union_ms'],.000015)

if __name__=='__main__':unittest.main()
