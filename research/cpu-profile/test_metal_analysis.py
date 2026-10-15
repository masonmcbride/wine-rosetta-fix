import tempfile
import unittest
from pathlib import Path

from summarize_metal import summarize


class MetalAnalysisTests(unittest.TestCase):
    def test_references_and_process_filter_preserve_display_gaps(self):
        events = '''<trace-query-result><node xpath="//run/data/table[1]">
        <row><start-time id="1">1000000</start-time><duration>8000000</duration>
        <display-name id="2">Display 1</display-name>
        <narrative id="3"><process id="4"><pid>42</pid></process></narrative></row>
        <row><start-time>9000000</start-time><duration>16000000</duration>
        <display-name ref="2"/><narrative ref="3"/></row>
        <row><start-time>10000000</start-time><duration>1</duration>
        <display-name ref="2"/><process><pid>99</pid></process></row>
        </node><node xpath="//run/data/table[2]">
        <row><start-time>100</start-time><duration>100</duration><process ref="4"/></row>
        <row><start-time>150</start-time><duration>100</duration><process ref="4"/></row>
        </node></trace-query-result>'''
        toc = '''<trace-toc><run><data>
        <table schema="displayed-surfaces-interval"/>
        <table schema="metal-gpu-intervals"/>
        </data></run></trace-toc>'''
        with tempfile.TemporaryDirectory() as tmp:
            e, t = Path(tmp) / 'events.xml', Path(tmp) / 'toc.xml'
            e.write_text(events)
            t.write_text(toc)
            result = summarize(e, t, 42)['tables']
        display = result['displayed-surfaces-interval']
        self.assertEqual(display['all_rows'], 3)
        self.assertEqual(display['target_rows'], 2)
        self.assertEqual(display['per_display']['Display 1']['gap_ms']['p50_ms'], 8)
        self.assertEqual(result['metal-gpu-intervals']['interval_union_ms'], .00015)

    def test_unresolved_reference_fails_instead_of_dropping_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            e, t = Path(tmp) / 'events.xml', Path(tmp) / 'toc.xml'
            e.write_text('<trace-query-result><node xpath="table[1]">'
                         '<row><process ref="missing"/></row></node></trace-query-result>')
            t.write_text('<trace-toc><run><data><table schema="metal-gpu-intervals"/>'
                         '</data></run></trace-toc>')
            with self.assertRaisesRegex(ValueError, 'Unresolved XML reference'):
                summarize(e, t, 42)


if __name__ == '__main__':
    unittest.main()
