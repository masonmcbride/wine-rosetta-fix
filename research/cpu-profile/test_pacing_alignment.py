import csv,json,tempfile,unittest
from pathlib import Path
from align_pacing_samples import align,mapping,marker_times

class AlignmentTests(unittest.TestCase):
    def sync(self):return dict(pid=12,sample_start=10,start_marker_before=10,start_marker_after=10,end_marker_before=13,end_marker_after=13,start_marker_enabled=1,end_marker_enabled=1)
    def xml(self,pid=12,end=True):
        return '<root><row><event-time id="1">100000000</event-time><process id="2"><pid>'+str(pid)+'</pid></process><subsystem id="3">com.mason.wine-profile</subsystem><signpost-name>WineSampleStart</signpost-name></row>'+('<row><event-time>3100000000</event-time><process ref="2"/><subsystem ref="3"/><signpost-name>WineSampleEnd</signpost-name></row>' if end else '')+'</root>'
    def test_pid_reference_and_missing_markers(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'signposts.xml';p.write_text(self.xml());self.assertEqual(marker_times(p,12)['WineSampleEnd'],3100000000)
            with self.assertRaisesRegex(ValueError,'Missing'):marker_times(p,13)
            p.write_text(self.xml(end=False))
            with self.assertRaisesRegex(ValueError,'Missing'):marker_times(p,12)
    def test_clock_disagreement_rejected(self):
        with self.assertRaisesRegex(ValueError,'disagree'):mapping(self.sync(),dict(WineSampleStart=0,WineSampleEnd=3001000000))
    def test_no_extrapolation_and_exact_midpoint(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);s=d/'s.csv';s.write_text('time,pc\n1.5,0x123\n4,0x456\n');j=d/'sync.json';j.write_text(json.dumps(self.sync()));m=d/'markers.xml';m.write_text(self.xml());o=d/'aligned.csv'
            r=align(s,j,m,o);self.assertEqual(r['aligned_rows'],1);self.assertEqual(r['outside_anchor_range'],1)
            with o.open() as f:self.assertEqual(int(next(csv.DictReader(f))['trace_time_ns']),1600000000)
