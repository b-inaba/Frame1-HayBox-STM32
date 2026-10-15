#!/usr/bin/env python3
"""Offline-only Frame1 DFU canary planner/readback verifier. NO USB/writes."""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

FLASH_BASE=0x08000000
FLASH_LENGTH=0x80000
APP_BASE=0x08020000
CANARY_ADDR=0x08060800
CANARY_SIZE=2048
CANARY_OFFSET=CANARY_ADDR-FLASH_BASE
MARKER=b"FRAME1-HAYBOX-DFU-CANARY-V1|0x08060800|"

def sha(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def planned_payload()->bytes:
    head=MARKER+bytes([0x55,0xAA,0x00,0x5A,0xA5,0xC3,0x3C])
    return head+b"\xff"*(CANARY_SIZE-len(head))

def check_original(backup:bytes):
    if len(backup)!=FLASH_LENGTH:
        raise ValueError("Backup must be exactly 524288 bytes")
    sp,entry=struct.unpack_from("<II",backup,0)
    asp,aentry=struct.unpack_from("<II",backup,APP_BASE-FLASH_BASE)
    if not (0x20000000<sp<=0x20010000 and (entry&~1)<APP_BASE and entry&1):
        raise ValueError("Invalid original bootloader vectors")
    if not (0x20000000<asp<=0x20010000 and APP_BASE<=(aentry&~1)<CANARY_ADDR and aentry&1):
        raise ValueError("Invalid original application vectors")
    if backup[CANARY_OFFSET:CANARY_OFFSET+CANARY_SIZE]!=b"\xff"*CANARY_SIZE:
        raise ValueError(f"Canary page at 0x{CANARY_ADDR:08X} is not blank")

def prepare(backup:bytes,destination:Path):
    check_original(backup)
    if destination.exists():
        raise ValueError("Output directory already exists; choose a new directory")
    destination.mkdir(parents=True)
    body=planned_payload()
    (destination/"canary.bin").write_bytes(body)
    manifest={
        "mode":"OFFLINE PLAN ONLY - NO HARDWARE WRITES",
        "original_backup_sha256":sha(backup),
        "canary_address":f"0x{CANARY_ADDR:08X}",
        "page_size":CANARY_SIZE,
        "canary_sha256":sha(body),
        "original_bootloader_sha256":sha(backup[:APP_BASE-FLASH_BASE]),
    }
    (destination/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (destination/"READ-ME.txt").write_text(
        "CANARY TEST RESEARCH ONLY. DO NOT FLASH THIS BIN YET.\n"
        "Target address is 0x08060800; not 0x08020000.\n"
        "The script does not communicate with any USB device.\n")
    return manifest

def analyze(backup:bytes,image:bytes,canary:bytes):
    check_original(backup)
    if len(image)!=FLASH_LENGTH or len(canary)!=CANARY_SIZE:
        raise ValueError("Wrong readback or canary size")
    if canary!=planned_payload():
        raise ValueError("Canary file does not match planned test pattern")
    if backup[:CANARY_OFFSET]!=image[:CANARY_OFFSET]:
        at=next(i for i in range(CANARY_OFFSET) if backup[i]!=image[i])
        raise ValueError(f"Unexpected flash difference BEFORE canary at 0x{FLASH_BASE+at:08X}")
    tail=CANARY_OFFSET+CANARY_SIZE
    if backup[tail:]!=image[tail:]:
        at=next(i for i in range(tail,FLASH_LENGTH) if backup[i]!=image[i])
        raise ValueError(f"Unexpected flash difference AFTER canary at 0x{FLASH_BASE+at:08X}")
    now=image[CANARY_OFFSET:tail]
    if now==b"\xff"*CANARY_SIZE:
        return "PASS: Blank canary page; all other flash matches original."
    if now==canary:
        return "PASS: Exact canary page present; bootloader, app, and all other flash unchanged."
    wrong=next(i for i,(actual,expected) in enumerate(zip(now,canary)) if actual!=expected)
    raise ValueError(f"Canary readback mismatch at 0x{CANARY_ADDR+wrong:08X}")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="action",required=True)
    p=sub.add_parser("prepare",help="Generate offline canary file")
    p.add_argument("--backup",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p=sub.add_parser("verify",help="Compare 512 KiB dump against original")
    p.add_argument("--backup",type=Path,required=True)
    p.add_argument("--readback",type=Path,required=True)
    p.add_argument("--canary",type=Path,required=True)
    args=parser.parse_args()
    try:
        backup=args.backup.read_bytes()
        if args.action=="prepare":
            info=prepare(backup,args.out)
            print("PASS: offline canary plan for",info["canary_address"])
            print("No device accessed. DO NOT FLASH YET.")
        else:
            print(analyze(backup,args.readback.read_bytes(),args.canary.read_bytes()))
    except (OSError,ValueError) as e:
        sys.exit("STOP: "+str(e))
if __name__=="__main__":
    main()
