import struct
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from plan_dfu_pages import (APP_BASE, APP_OFFSET, BACKUP_SIZE, FLASH_BASE,
                            FLASH_END, PAGE_SIZE, create_plan, write_plan)


def app(n=4100):
    if n < 8: raise ValueError('size')
    return struct.pack('<II', 0x20010000, (APP_BASE + 0x8 | 1)) + b'\x11'*(n-8)


def backup(old_used=9200):
    buf = bytearray(b'\xff'*BACKUP_SIZE)
    buf[0:8] = struct.pack('<II', 0x20010000, FLASH_BASE+0x81)
    buf[APP_OFFSET:APP_OFFSET+old_used] = app(old_used)
    return bytes(buf)


class DfuPlanTests(unittest.TestCase):
    def test_pages_cover_old_and_new(self):
        m, blobs = create_plan(app(4100), backup(9200))
        self.assertEqual(len(blobs), 5)
        self.assertEqual(len(blobs[0]), 2048)
        self.assertEqual(blobs[2][4:], b'\xff' * (PAGE_SIZE - 4))
        self.assertEqual(blobs[-1], b'\xff'*PAGE_SIZE)
        self.assertEqual([p['address'] for p in m['pages']],
                         [f'0x{APP_BASE+i*PAGE_SIZE:08X}' for i in range(5)])

    def test_no_writes_below_app(self):
        m, blobs = create_plan(app(5000), backup(3000))
        self.assertEqual(m['application_start'], f'0x{APP_BASE:08X}')
        self.assertGreaterEqual(int(m['pages'][0]['address'], 16), APP_BASE)
        for item in m['pages']:
            self.assertLessEqual(int(item['address'],16) + PAGE_SIZE, FLASH_END)

    def test_reject_bad_vectors(self):
        b = backup()
        bad = bytearray(app())
        bad[:4] = (0).to_bytes(4, 'little')
        with self.assertRaisesRegex(ValueError, 'stack pointer'):
            create_plan(bytes(bad), b)
        bad = bytearray(app())
        bad[4:8] = (FLASH_BASE+1).to_bytes(4,'little')
        with self.assertRaisesRegex(ValueError, 'reset vector'):
            create_plan(bytes(bad), b)

    def test_reject_oversized(self):
        with self.assertRaisesRegex(ValueError,'firmware'):
            create_plan(app(FLASH_END-APP_BASE+1), backup())

    def test_reject_wrong_backup_size(self):
        with self.assertRaisesRegex(ValueError,'backup must'):
            create_plan(app(), b'\xff'*100)

    def test_manifest_written_with_correct_checksums(self):
        m, blobs = create_plan(app(3000), backup(3000))
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'plan'
            write_plan(out,m,blobs)
            self.assertTrue((out/'manifest.json').exists())
            for p, content in zip(m['pages'],blobs):
                self.assertEqual((out/p['file']).read_bytes(),content)
            with self.assertRaisesRegex(ValueError,'not empty'):
                write_plan(out,m,blobs)


if __name__ == '__main__':
    unittest.main()
