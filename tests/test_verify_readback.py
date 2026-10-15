import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verify_readback import verify,RESERVED,SIZE,PAGE,FLASH_BASE
from plan_dfu_pages import create_plan

def samples():
    original=bytearray(b'\xff'*SIZE)
    original[:8]=struct.pack('<II',0x20010000,0x08000081)
    original[RESERVED:RESERVED+8]=struct.pack('<II',0x20010000,0x08020009)
    original[RESERVED+8:RESERVED+2500]=b'\x34'*2492
    original=bytes(original)
    new=struct.pack('<II',0x20010000,0x08020009)+b'\x42'*3000
    plan,images=create_plan(new,original)
    after=bytearray(original)
    for p,buf in zip(plan['pages'],images):
        off=int(p['address'],16)-FLASH_BASE
        after[off:off+PAGE]=buf
    return original,bytes(after),plan

class ReadbackTests(unittest.TestCase):
    def test_good(self):
        a,b,p=samples()
        self.assertIn('PASS',verify(a,b,p))
    def test_bootloader_changed(self):
        a,b,p=samples()
        c=bytearray(b);c[0x800]^=1
        with self.assertRaisesRegex(ValueError,'BOOTLOADER ALTERED'):
            verify(a,bytes(c),p)
    def test_page_not_flashed(self):
        a,b,p=samples()
        c=bytearray(b);c[RESERVED+0x800]^=1
        with self.assertRaisesRegex(ValueError,'PAGE MISMATCH'):
            verify(a,bytes(c),p)
    def test_unplanned_change(self):
        a,b,p=samples()
        c=bytearray(b);c[0x40000]^=1
        with self.assertRaisesRegex(ValueError,'UNPLANNED'):
            verify(a,bytes(c),p)
    def test_redirected_page(self):
        a,b,p=samples()
        p['pages'][0]['address']='0x08000000'
        with self.assertRaisesRegex(ValueError,'invalid address'):
            verify(a,b,p)
    def test_wrong_backup_hash(self):
        a,b,p=samples()
        p['backup_bootloader_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'does not match'):
            verify(a,b,p)
    def test_truncated(self):
        a,b,p=samples()
        with self.assertRaisesRegex(ValueError,'524288'):
            verify(a,b[:-1],p)
