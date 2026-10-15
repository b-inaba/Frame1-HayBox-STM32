#!/usr/bin/env python3
"""Read-only Frame1 USB DFU verification against a PRIVATE original backup."""
from pathlib import Path
import argparse, hashlib, os, re, subprocess, tempfile

SIZE=524288
DEVICE_RE=re.compile(r'Found DFU: \[0483:df11\].*?alt=0,.*?name="@Internal Flash',re.I)

def analyze(backup,current):
    if len(backup)!=SIZE or len(current)!=SIZE:
        raise ValueError("Expected two exactly 524288-byte images")
    if backup[:0x20000]!=current[:0x20000]:
        raise ValueError("STOP: bootloader/reserved region differs")
    if backup[0x20000:]!=current[0x20000:]:
        raise ValueError("STOP: app region differs")
    return hashlib.sha256(current).hexdigest()

def run(exe,args):
    r=subprocess.run([exe,*args],capture_output=True,text=True,timeout=120)
    if r.returncode:
        raise RuntimeError("dfu-util error: "+(r.stderr or r.stdout)[-1500:])
    return r.stdout+"\n"+r.stderr

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--backup",required=True,type=Path)
    p.add_argument("--dfu-util",default="dfu-util.exe" if os.name=="nt" else "dfu-util")
    a=p.parse_args()
    try:
        backup=a.backup.read_bytes()
        if len(backup)!=SIZE:
            raise ValueError("Original backup must be 524288 bytes")
        devices=run(a.dfu_util,["-l"])
        if len(DEVICE_RE.findall(devices))!=1:
            raise ValueError("Expected exactly one Frame1 in USB DFU mode")
        with tempfile.TemporaryDirectory() as directory:
            dest=Path(directory)/"live-readback.bin"
            run(a.dfu_util,["-d","0483:df11","-a","0","-s",
                            "0x08000000:524288","-U",str(dest)])
            current=dest.read_bytes()
        checksum=analyze(backup,current)
        print("PASS: Full 512 KiB readback matches your Frame1 backup.")
        print("SHA256:",checksum)
        print("The device was not modified.")
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as e:
        p.exit(2,"STOP: "+str(e)+"\n")
if __name__=="__main__":
    main()
