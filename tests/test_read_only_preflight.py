import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from read_only_preflight import analyze,SIZE

class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.original=bytes([7])*SIZE
    def test_equal(self):
        self.assertEqual(len(analyze(self.original,self.original)),64)
    def test_bad_bootloader(self):
        bad=bytearray(self.original);bad[0x800]^=1
        with self.assertRaisesRegex(ValueError,"bootloader"):
            analyze(self.original,bytes(bad))
    def test_bad_app(self):
        bad=bytearray(self.original);bad[0x20000]^=1
        with self.assertRaisesRegex(ValueError,"app"):
            analyze(self.original,bytes(bad))
    def test_wrong_size(self):
        with self.assertRaisesRegex(ValueError,"524288"):
            analyze(self.original,self.original[:-1])
if __name__=="__main__":
    unittest.main()
