import importlib.util,json,plistlib,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from build_pacing_template import narrow,TYPES
from capture_pacing import command,validate_session

class CaptureTests(unittest.TestCase):
    def test_template_drops_unrequested_instruments(self):
        # Synthetic archive with real keyed-archive reference semantics.
        o=['null',3];top={'$0':plistlib.UID(1)}
        for i,name in enumerate([TYPES['display'],TYPES['states'],'unwanted']):
            o.append({'NS.string':name});top[f'${2*i+1}']=plistlib.UID(len(o)-1)
            o.append({'config':name});top[f'${2*i+2}']=plistlib.UID(len(o)-1)
        o.extend([TYPES['display'],TYPES['states'],'unwanted']);keys=[plistlib.UID(i) for i in range(8,11)]
        o.append({'NS.keys':keys,'NS.objects':keys});top['stubInfoByUUID']=plistlib.UID(11)
        r=narrow({'$objects':o,'$top':top},{TYPES['display']});self.assertEqual(r['$objects'][r['$top']['$0'].data],1)
        self.assertNotIn('$3',r['$top']);self.assertEqual(len(r['$objects'][11]['NS.keys']),1)
        self.assertEqual(o[1],3) # Original archive remains unchanged.
    def test_command_is_attached_bounded_and_not_broad_template(self):
        c=command(123,'combined',Path('/tmp/example.trace'),'ready.name')
        self.assertEqual(c[c.index('--attach')+1],'123');self.assertEqual(c[c.index('--time-limit')+1],'5s')
        self.assertNotIn('--all-processes',c);self.assertTrue(c[c.index('--template')+1].endswith('/pacing.tracetemplate'))
    def test_trigger_reuse_and_expired_session_rejected(self):
        with tempfile.TemporaryDirectory() as d,patch('capture_pacing.PRIVATE',Path(d)):
            p=Path(d)/'address-recovery/session';p.mkdir(parents=True);f=p/'launch.json';f.write_text(json.dumps({'synchronized_markers':True}))
            validate_session(p)
            with patch('capture_pacing.time.time',return_value=f.stat().st_mtime+541):
                with self.assertRaisesRegex(ValueError,'expire'):validate_session(p)
            (p/'capture.trigger').touch()
            with self.assertRaisesRegex(ValueError,'already triggered'):validate_session(p)
