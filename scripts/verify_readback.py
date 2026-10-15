#!/usr/bin/env python3
"""READ-ONLY verifier for 512 KiB Frame1 original/after flash dumps and offline plan."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

FLASH_BASE=0x08000000
APP_BASE=0x08020000
END=0x08080000
RESERVED=APP_BASE-FLASH_BASE
SIZE=END-FLASH_BASE
PAGE=2048

def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def verify(original: bytes, readback: bytes, manifest: dict) -> str:
    if len(original)!=SIZE or len(readback)!=SIZE:
        raise ValueError('both images must be exactly 524288 bytes')
    if original[:RESERVED]!=readback[:RESERVED]:
        off=next(i for i in range(RESERVED) if original[i]!=readback[i])
        raise ValueError(f'BOOTLOADER ALTERED at 0x{FLASH_BASE+off:08X}')
    if manifest.get('backup_bootloader_sha256')!=sha256(original[:RESERVED]):
        raise ValueError('manifest backup does not match original')
    if manifest.get('application_start')!=f'0x{APP_BASE:08X}':
        raise ValueError('invalid application start')
    if manifest.get('application_end_exclusive')!=f'0x{END:08X}':
        raise ValueError('invalid application end')
    if manifest.get('native_flash_page_bytes')!=PAGE:
        raise ValueError('invalid physical page size')
    pages=manifest.get('pages')
    if not isinstance(pages,list) or not 1<=len(pages)<=((END-APP_BASE)//PAGE):
        raise ValueError('invalid planned page list')
    if manifest.get('pages_to_erase_and_program_if_approved')!=len(pages):
        raise ValueError('manifest page count inconsistent')
    for i,p in enumerate(pages):
        addr=APP_BASE+i*PAGE
        if p.get('index')!=i or p.get('address')!=f'0x{addr:08X}' or p.get('bytes')!=PAGE:
            raise ValueError(f'invalid address or length at page {i}')
        page=readback[addr-FLASH_BASE:addr-FLASH_BASE+PAGE]
        if sha256(page)!=p.get('sha256'):
            raise ValueError(f'PAGE MISMATCH at 0x{addr:08X}')
    tail=RESERVED+len(pages)*PAGE
    if original[tail:]!=readback[tail:]:
        off=next(i for i in range(tail,SIZE) if original[i]!=readback[i])
        raise ValueError(f'UNPLANNED FLASH CHANGE at 0x{FLASH_BASE+off:08X}')
    return f'PASS: original bootloader untouched; {len(pages)} pages verified; remaining flash unchanged'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before',type=Path,required=True)
    p.add_argument('--after',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True)
    args=p.parse_args()
    try:
        print(verify(args.before.read_bytes(),args.after.read_bytes(),
                     json.loads(args.manifest.read_text(encoding='utf-8'))))
    except (OSError,ValueError) as e:
        p.error(str(e))

if __name__=='__main__':
    main()
