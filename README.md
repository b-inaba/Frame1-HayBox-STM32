# Frame1-HayBox-STM32

An experimental zero-cost effort to bring open-source, tournament-nerfed Melee controller firmware to **original retail Frame1 hardware**.

**WARNING: NO BUILDS IN THIS REPOSITORY ARE APPROVED FOR FLASHING.** These are development experiments. Do not use the generated binaries on your Frame1 yet.

## Verified from a local user's controller and readback

- STM32F303VE microcontroller (512 KiB flash; 80 KiB total SRAM)
- `0483:DF11` USB DFU enumerates when holding Up during USB connect
- User-flash bootloader at `0x08000000`, controller app at `0x08020000`.
- 2 KiB actual flash pages, despite DFU reporting mismatched sector layout.
- Static analysis found 2 KiB incremental page erases in the bootloader; see [bootloader research](docs/bootloader-analysis.md).
- The original bootloader checks GPIO button states and the app vector before `BLX` handoff, independently of the app; see [boot sequence analysis](docs/bootpath-analysis.md).
- Bootloader must be protected; losing it could disable Up-button USB recovery.

## Builds

`make` builds the simple original skeleton only.

`make usb-probe` builds a **separate, untested** USB device-enumeration probe using LGPL-licensed [libopencm3](https://github.com/libopencm3/libopencm3). GitHub Actions fetches and builds pinned libopencm3 automatically. The USB probe aims to appear as a distinct vendor-specific USB device, not a GameCube adapter or HID.

The USB probe now handles bootloader-to-app clock handoff (HSI before reconfiguring PLL) and sanitizes leftover interrupt state. These are static mitigations, not proof of working hardware.

Builds link to `0x08020000`. Actions compiles and validates binaries and publishes the results, but **does not flash any hardware**.

To build the probe locally, install arm-none-eabi-gcc and newlib, then:
```sh
git clone https://github.com/libopencm3/libopencm3.git external/libopencm3
git -C external/libopencm3 checkout ddcbb2889fa018626c604e27ea50e66db5755b78
make -C external/libopencm3 TARGETS=stm32/f3
make usb-probe
```

## Unknowns before a first write

1. Whether a host-side DFU write properly erases **every 2 KiB page**, despite the descriptor mismatch.
2. Bootloader-owned Up/GPIO selection appears independent of the app, but recovery after an invalid reset handler is not yet hardware-verified.
3. Whether USB crystal and pull-up assumptions of the probe match actual Frame1 PCB.
4. How all buttons are wired; how to implement Joybus output and port tournament-nerfed HayBox logic.

After a future experimental flash, compare the entire 512 KiB readback with the original backup and page-plan manifest using `scripts/verify_readback.py`. This is **read only** and not a substitute for proving USB recovery.

Never commit the original closed-source Frame1 firmware dump or serial identifiers to this public repo. Any eventual uploader must explicitly protect `0x08000000..0x0801FFFF`, reject mass erase, and verify a post-write readback.


## Read-only DFU preflight (zero write operations)

The optional script \`scripts/read_only_preflight.py\` identifies exactly one
Frame1 USB DFU device, reads its entire 512 KiB flash using dfu-util \`-U\`,
and compares it byte-for-byte against your *private* original backup.
It contains no \`-D\` programming command.

On Windows, open a Command Prompt in the repository directory,
hold **Up** while connecting the Frame1, then run (adjust both paths):

\`\`\`cmd
py -3 scripts\read_only_preflight.py --backup "C:\path\to\frame1-backup.bin" --dfu-util "C:\path\to\dfu-util.exe"
\`\`\`

A passing result proves the original flash is unchanged; it does **not**
prove a future write will be safe. Do not upload or commit your private backup.


## Canary page experiment (preparation ONLY)

The user has confirmed a complete, byte-for-byte read-only DFU preflight
against the original 512 KiB backup.

Our proposed *first write* would be a 2048-byte canary in a **blank page at
0x08060800**, far above both the bootloader and original application.
This is **NOT YET AUTHORIZED OR TESTED ON HARDWARE** and could still brick
the board if the bootloader misinterprets the erase/write requests.

Create the canary **offline**, using the original backup, with:

\`\`\`cmd
py -3 scripts\canary_test.py prepare --backup "C:\path\to\frame1-backup.bin" --out canary-output
\`\`\`

The script writes only local files: \`canary.bin\`, a manifest and warning
instructions. It contains no flashing capability. It refuses the operation
unless that physical page is \`0xFF\` in the original backup.

After a separately approved canary write and 512 KiB hardware readback,
the script can verify that **only** the exact target page changed:

\`\`\`cmd
py -3 scripts\canary_test.py verify --backup "C:\path\to\frame1-backup.bin" --readback "C:\path\to\full-readback.bin" --canary canary-output\canary.bin
\`\`\`

Any changes elsewhere, including the bootloader, produce a STOP error.
Do not start an actual write without reviewing the per-page DFU protocol
and accepting that failure may require external SWD hardware to recover.
