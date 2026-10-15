#!/usr/bin/env python3
"""OFFLINE-ONLY STM32F303 Frame1 DFU planning tool: no USB access, no flashing.

Creates one 2048-byte file per physical flash page and a manifest containing
planned operations. Pages begin at 0x08020000 and never overlap the bootloader.

IMPORTANT: dfu-util reads the controller's misleading *128-KiB* sector
layout. Normal bulk download can erase only one actual 2-KiB page. Each page
would need a distinct dfu-util process invocation so the actual firmware's
ERASE_PAGE command receives that native page address. Even this approach has
NOT BEEN VERIFIED ON HARDWARE. No command execution is implemented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

FLASH_BASE = 0x08000000
APP_BASE = 0x08020000
FLASH_END = 0x08080000
BACKUP_SIZE = FLASH_END - FLASH_BASE
APP_OFFSET = APP_BASE - FLASH_BASE
PAGE_SIZE = 2048
SRAM_START = 0x20000000
SRAM_END = 0x20010000


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def validate_vector(blob: bytes, base: int, limit: int, label: str) -> dict:
    if len(blob) < 8:
        raise ValueError(f'{label} too short for an ARM vector table')
    stack, reset = struct.unpack_from('<II', blob)
    if not (SRAM_START < stack <= SRAM_END and stack % 8 == 0):
        raise ValueError(f'{label}: unexpected initial stack pointer 0x{stack:08x}')
    entry = reset & ~1
    if not (reset & 1 and base <= entry < limit):
        raise ValueError(f'{label}: unexpected reset vector 0x{reset:08x}')
    return {'initial_stack': f'0x{stack:08X}', 'reset_vector': f'0x{reset:08X}'}


def create_plan(firmware: bytes, backup: bytes) -> tuple[dict, list[bytes]]:
    if len(backup) != BACKUP_SIZE:
        raise ValueError(f'backup must be {BACKUP_SIZE} bytes; got {len(backup)}')
    loader = backup[:APP_OFFSET]
    loader_vector = validate_vector(loader, FLASH_BASE, APP_BASE, 'backup bootloader')
    if loader == b'\xff' * len(loader):
        raise ValueError('backup is blank in the bootloader region')
    oldapp = backup[APP_OFFSET:]
    original_vector = validate_vector(oldapp, APP_BASE, FLASH_END, 'backup application')
    if not firmware or len(firmware) > FLASH_END - APP_BASE:
        raise ValueError('firmware must be nonempty and within application region')
    candidate_vector = validate_vector(firmware, APP_BASE, APP_BASE + len(firmware), 'new application')
    # Erase stale old application pages as well, not only the new image.
    last_old_non_ff = next((i for i in range(len(oldapp) - 1, -1, -1)
                            if oldapp[i] != 0xff), -1)
    original_bytes_occupied = last_old_non_ff + 1
    span = max(len(firmware), original_bytes_occupied)
    count = math.ceil(span / PAGE_SIZE)
    if count <= 0 or count > (FLASH_END - APP_BASE) // PAGE_SIZE:
        raise ValueError('calculated page count outside application region')

    data = firmware.ljust(count * PAGE_SIZE, b'\xff')
    pages = []
    contents = []
    for index in range(count):
        addr = APP_BASE + index * PAGE_SIZE
        if addr < APP_BASE or addr + PAGE_SIZE > FLASH_END:
            raise ValueError('attempt to address outside application region')
        filename = f'page-{index:03d}-0x{addr:08X}.bin'
        body = data[index * PAGE_SIZE:(index + 1) * PAGE_SIZE]
        contents.append(body)
        pages.append({
            'index': index, 'address': f'0x{addr:08X}', 'bytes': PAGE_SIZE,
            'file': filename, 'sha256': digest(body),
            'would_erase_existing_data': backup[addr-FLASH_BASE:addr-FLASH_BASE+PAGE_SIZE] != body,
        })
    manifest = {
        'mode': 'OFFLINE PLAN ONLY — NEVER FLASHED',
        'chip_family': 'STM32F303VE',
        'application_start': f'0x{APP_BASE:08X}',
        'application_end_exclusive': f'0x{FLASH_END:08X}',
        'bootloader_region_end_exclusive': f'0x{APP_BASE:08X}',
        'native_flash_page_bytes': PAGE_SIZE,
        'firmware_size': len(firmware),
        'firmware_sha256': digest(firmware),
        'backup_size': len(backup),
        'backup_bootloader_sha256': digest(loader),
        'previous_app_bytes_occupied': original_bytes_occupied,
        'pages_to_erase_and_program_if_approved': count,
        'vectors': {'bootloader':loader_vector, 'previous_application': original_vector, 'candidate_application': candidate_vector},
        'pages': pages,
        'cautions': [
            'DO NOT execute writes based on this plan until bootloader recovery is verified.',
            'DFU descriptor reports F4-like sectors; STM32F303 physical pages are 2048 bytes.',
            'Each separately addressed page must be erased/programmed/read back and verified.',
            'Never use DFU mass erase, read unprotect, or write below 0x08020000.',
        ],
    }
    return manifest, contents


def write_plan(out: Path, plan: dict, contents: list[bytes]) -> None:
    if out.exists() and any(out.iterdir()):
        raise ValueError(f'output directory exists and is not empty: {out}')
    out.mkdir(parents=True, exist_ok=True)
    for item, payload in zip(plan['pages'], contents):
        if digest(payload) != item['sha256'] or len(payload) != PAGE_SIZE:
            raise ValueError('internal page checksum mismatch')
        (out / item['file']).write_bytes(payload)
    (out / 'manifest.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    (out / 'README-DO-NOT-FLASH.txt').write_text(
        'FRAME1 OFFLINE DFU PAGE PLAN — NOT AUTHORIZATION TO FLASH\n'
        'This folder ONLY contains page-aligned images and expected hashes.\n'
        'No USB operations have occurred.\n'
        'DO NOT run dfu-util with -D on these files yet.\n'
        'The Up-button DFU recovery and erase implementation have not been\n'
        'verified end-to-end with a replacement app.\n', encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--firmware', required=True, type=Path, help='compiled candidate application .bin')
    parser.add_argument('--backup', required=True, type=Path, help='unmodified 512 KiB original readback')
    parser.add_argument('--out', required=True, type=Path, help='new/empty local output directory')
    args = parser.parse_args()
    try:
        manifest, pages = create_plan(args.firmware.read_bytes(), args.backup.read_bytes())
        write_plan(args.out, manifest, pages)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print('OFFLINE CHECK PASSED — NOTHING HAS BEEN FLASHED')
    print('Application start:', manifest['application_start'])
    print('Validated stack/reset:', manifest['vectors']['candidate_application'])
    print('Physical pages in plan:', len(pages), 'of', PAGE_SIZE, 'bytes each')
    print('Reserved bootloader untouched: first', APP_OFFSET, 'bytes of flash')
    print('Manifest:', args.out / 'manifest.json')
    print('DO NOT FLASH YET: physical DFU recovery remains unverified.')


if __name__ == '__main__':
    main()
