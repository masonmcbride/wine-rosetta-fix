import csv,struct,tempfile,unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch
from attribute_pe_samples import attribute

class PEAttributionTests(unittest.TestCase):
    def fixture(self,d,memory='c3',module=None):
        image=Path(d)/'fixture.exe';b=bytearray(1024);b[:2]=b'MZ';struct.pack_into('<I',b,60,128)
        b[128:132]=b'PE\0\0';struct.pack_into('<HH',b,132,0x14c,1);struct.pack_into('<H',b,148,224)
        struct.pack_into('<H',b,152,0x10b);struct.pack_into('<I',b,180,0x400000)
        struct.pack_into('<IIII',b,384,256,0x1000,256,512);struct.pack_into('<I',b,412,0x20000000);b[512]=0xc3;image.write_bytes(b)
        samples=Path(d)/'samples.csv'
        with samples.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['pc','base','module','kind','instruction_bytes']);w.writeheader();w.writerow(dict(pc='0x601000',base='0x600000',module=str(image) if module is None else module,kind='PE32',instruction_bytes=memory))
        return samples,image
    @staticmethod
    def tools(args,**kwargs):
        text='  401000:\tc3 \tret\n' if args[0].endswith('objdump') else 'hot_leaf\nfixture.c:8\n'
        return CompletedProcess(args,0,text,'')
    @patch('attribute_pe_samples.subprocess.run',side_effect=tools.__func__)
    def test_relocated_pc_maps_exact_bytes_and_dwarf(self,_):
        with tempfile.TemporaryDirectory() as d:
            samples,image=self.fixture(d);r=attribute(samples,image)
            self.assertEqual(r['addresses'][0]['static_address'],'0x401000')
            self.assertEqual(r['status_counts'],{'verified_function_instruction':1})
    @patch('attribute_pe_samples.subprocess.run',side_effect=tools.__func__)
    def test_mismatched_runtime_bytes_stay_unresolved(self,_):
        with tempfile.TemporaryDirectory() as d:
            samples,image=self.fixture(d,memory='90');r=attribute(samples,image)
            self.assertEqual(r['status_counts'],{'instruction_bytes_unverified':1})
    @patch('attribute_pe_samples.subprocess.run',side_effect=tools.__func__)
    def test_unknown_module_cannot_be_guessed(self,_):
        with tempfile.TemporaryDirectory() as d:
            samples,image=self.fixture(d,module='UNKNOWN');r=attribute(samples,image)
            self.assertEqual(r['status_counts'],{'unresolved_module':1})

if __name__=='__main__':unittest.main()
