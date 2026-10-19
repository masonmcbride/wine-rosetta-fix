import struct,unittest
from attribute_pe_samples import relocated_jump

class RelocationTests(unittest.TestCase):
    def image(self,kind=3):
        b=bytearray(1024);struct.pack_into('<I',b,60,128);struct.pack_into('<H',b,134,1);struct.pack_into('<H',b,148,224)
        opt=152;struct.pack_into('<I',b,opt+92,16);struct.pack_into('<II',b,opt+136,0x2000,12)
        struct.pack_into('<III',b,388,0x2000,256,768);struct.pack_into('<IIHH',b,768,0x1000,12,(kind<<12)|2,0)
        return bytes(b)
    def test_explicit_highlow_operand(self):
        code=b'\xff\x25'+struct.pack('<I',0x501234)
        self.assertEqual(relocated_jump(self.image(),0x1000,code,0x200000),b'\xff\x25'+struct.pack('<I',0x701234))
    def test_wrong_relocation_kind_is_rejected(self):
        self.assertIsNone(relocated_jump(self.image(1),0x1000,b'\xff\x25'+b'\0'*4,0x200000))
    def test_wrong_instruction_or_unlisted_operand_rejected(self):
        self.assertIsNone(relocated_jump(self.image(),0x1000,b'\x90'*6,0x200000))
        self.assertIsNone(relocated_jump(self.image(),0x1010,b'\xff\x25'+b'\0'*4,0x200000))
