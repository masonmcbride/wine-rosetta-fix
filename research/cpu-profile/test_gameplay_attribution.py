import contextlib,csv,io,json,runpy,struct,tempfile,unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

class MachAttributionTests(unittest.TestCase):
    def run_fixture(self,memory):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);image=p/'engine'/'fixture.so';image.parent.mkdir()
            b=bytearray(512);struct.pack_into('<IiiIIII',b,0,0xfeedfacf,0x1000007,3,6,1,72,0)
            struct.pack_into('<II',b,32,0x19,72);struct.pack_into('<QQQQ',b,56,0,512,0,512);struct.pack_into('<I',b,92,5);b[256]=0xc3;image.write_bytes(b)
            sample=p/'samples.csv'
            with sample.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['pc','base','module','kind','instruction_bytes']);w.writeheader();w.writerow(dict(pc='0x60100',base='0x60000',module=str(image),kind='MachO64',instruction_bytes=memory))
            Path(str(sample)+'.stats.json').write_text(json.dumps({'threads':[]}))
            result=CompletedProcess([],0,'0000000000000100 <_fixture>:\n 100: c3  retq\n','')
            with patch('sys.argv',['attribute_gameplay_wine.py',str(sample),'--output',str(p/'out')]),patch('subprocess.run',return_value=result),contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(Path(__file__).with_name('attribute_gameplay_wine.py')),run_name='__main__')
            return json.loads((p/'out/wine-mach-instructions.json').read_text())[0]
    def test_relocated_exact_instruction(self):
        r=self.run_fixture('c3');self.assertEqual(r['static_address'],'0x100');self.assertEqual(r['bytes'],'c3');self.assertEqual(r['file_offset'],'0x100')
    def test_mismatch_not_accepted(self):
        self.assertEqual(self.run_fixture('90')['status'],'instruction_bytes_mismatch')
