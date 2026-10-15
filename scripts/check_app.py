#!/usr/bin/env python3
"""Read-only validation of app binary; NO hardware access."""
import sys
import struct
from pathlib import Path

APP_BASE = 0x08020000
APP_LIMIT = 0x08080000
SRAM_BASE, SRAM_LIMIT = 0x20000000, 0x20010000


def validate(path):
    b = Path(path).read_bytes()
    if len(b) < 8 or len(b) > APP_LIMIT - APP_BASE:
        raise ValueError(f'Invalid app size: {len(b)} bytes')
    msp, reset = struct.unpack_from('<II', b)
    if not (SRAM_BASE < msp <= SRAM_LIMIT and msp % 8 == 0):
        raise ValueError(f'Unexpected initial MSP: 0x{msp:08x}')
    if (reset & 1) != 1 or not (APP_BASE <= (reset & ~1) < APP_BASE + len(b)):
        raise ValueError(f'Reset vector not in linked application: 0x{reset:08x}')
    print(f'PASS: {len(b):,} bytes at 0x{APP_BASE:08x}, MSP=0x{msp:08x}, reset=0x{reset:08x}')
    print('This checks only the binary layout—not whether it can be flashed or run safely.')


if __name__ == '__main__':
    try:
        validate(sys.argv[1])
    except (IndexError, OSError, ValueError) as exc:
        sys.exit(str(exc))
