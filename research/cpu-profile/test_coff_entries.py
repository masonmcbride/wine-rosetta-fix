import struct,unittest
from resolve_coff_entries import entries
class CoffEntryTests(unittest.TestCase):
    def fixture(self,kind=0x20,section=1):
        b=bytearray(512);struct.pack_into('<I',b,60,128);b[128:132]=b'PE\0\0';struct.pack_into('<HH',b,132,0x14c,1);struct.pack_into('<II',b,140,256,1);struct.pack_into('<H',b,148,224);struct.pack_into('<I',b,180,0x400000);struct.pack_into('<I',b,388,0x1000)
        b[256:264]=b'_hot\0\0\0\0';struct.pack_into('<IhHBB',b,264,0x10,section,kind,2,0);struct.pack_into('<I',b,274,4);return bytes(b)
    def test_exact_function_entry_address(self):self.assertEqual(dict(entries(self.fixture())),{0x401010:['_hot']})
    def test_nonfunction_and_absolute_symbols_excluded(self):
        self.assertEqual(dict(entries(self.fixture(kind=0))),{});self.assertEqual(dict(entries(self.fixture(section=-1))),{})
