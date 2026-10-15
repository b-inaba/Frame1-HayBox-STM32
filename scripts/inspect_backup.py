#!/usr/bin/env python3
"""Analyze original 512 KiB Frame1 flash dump; no device writes."""
import sys, hashlib, struct
from pathlib import Path

b = Path(sys.argv[1]).read_bytes() if len(sys.argv) > 1 else b''
if len(b) != 512*1024:
    raise SystemExit('Expected a 524288-byte flash dump as argument')

for label, offset in [('bootloader', 0), ('application', 0x20000)]:
    sp, reset = struct.unpack_from('<II', b, offset)
    print(f'{label} at 0x{0x08000000+offset:08x}: MSP=0x{sp:08x}, reset=0x{reset:08x}')

print('Bootloader/reserved region SHA256:', hashlib.sha256(b[:0x20000]).hexdigest())
print('Application region SHA256:        ', hashlib.sha256(b[0x20000:]).hexdigest())
print('Used through address:', hex(0x08000000 + max(i for i,x in enumerate(b) if x != 0xff)))
