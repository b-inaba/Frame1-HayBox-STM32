import struct
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from canary_test import (FLASH_LENGTH,APP_BASE,FLASH_BASE,CANARY_OFFSET,
                         CANARY_SIZE,planned_payload,prepare,analyze)

def mock_backup():
    b=bytearray(b"\xff"*FLASH_LENGTH)
    struct.pack_into("<II",b,0,0x20010000,0x08008075)
    struct.pack_into("<II",b,APP_BASE-FLASH_BASE,0x20010000,0x08023FA9)
    b[0x8000:0x8100]=b"\x01"*256
    b[0x20100:0x20200]=b"\x22"*256
    return bytes(b)

class CanaryTests(unittest.TestCase):
    def test_prepare(self):
        b=mock_backup()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"plan"
            m=prepare(b,path)
            self.assertEqual(m["canary_address"],"0x08060800")
            self.assertEqual((path/"canary.bin").read_bytes(),planned_payload())
    def test_initial_blank(self):
        b=mock_backup()
        self.assertIn("Blank canary",analyze(b,b,planned_payload()))
    def test_flashed_pattern(self):
        b=mock_backup(); new=bytearray(b)
        new[CANARY_OFFSET:CANARY_OFFSET+CANARY_SIZE]=planned_payload()
        self.assertIn("Exact canary",analyze(b,bytes(new),planned_payload()))
    def test_error_before(self):
        b=mock_backup(); new=bytearray(b); new[0x1000]^=1
        with self.assertRaisesRegex(ValueError,"BEFORE canary"):
            analyze(b,bytes(new),planned_payload())
    def test_error_after(self):
        b=mock_backup(); new=bytearray(b); new[-1]^=1
        with self.assertRaisesRegex(ValueError,"AFTER canary"):
            analyze(b,bytes(new),planned_payload())
    def test_corrupt_canary(self):
        b=mock_backup(); new=bytearray(b)
        new[CANARY_OFFSET:CANARY_OFFSET+CANARY_SIZE]=planned_payload()
        new[CANARY_OFFSET+3]^=1
        with self.assertRaisesRegex(ValueError,"Canary readback mismatch"):
            analyze(b,bytes(new),planned_payload())
    def test_not_blank(self):
        b=bytearray(mock_backup()); b[CANARY_OFFSET]=0
        with self.assertRaisesRegex(ValueError,"not blank"):
            analyze(bytes(b),bytes(b),planned_payload())
    def test_invalid_file(self):
        with self.assertRaisesRegex(ValueError,"Wrong readback"):
            analyze(mock_backup(),b"\xff"*100,planned_payload())
    def test_reject_unapproved_payload(self):
        b=mock_backup()
        with self.assertRaisesRegex(ValueError,"does not match"):
            analyze(b,b,b"\xff"*CANARY_SIZE)
if __name__=="__main__": unittest.main()
