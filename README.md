# Frame1-HayBox-STM32

An experimental zero-cost effort to bring open-source, tournament-nerfed Melee controller firmware to **original retail Frame1 hardware**.

**WARNING: NO BUILDS IN THIS REPOSITORY ARE APPROVED FOR FLASHING.** These are development experiments. Do not use the generated binaries on your Frame1 yet.

## Verified from a local user's controller and readback

- STM32F303VE microcontroller (512 KiB flash; 80 KiB total SRAM)
- `0483:DF11` USB DFU enumerates when holding Up during USB connect
- User-flash bootloader at `0x08000000`, controller app at `0x08020000`.
- 2 KiB actual flash pages, despite DFU reporting mismatched sector layout.
- Static analysis found 2 KiB incremental page erases in the bootloader; see [bootloader research](docs/bootloader-analysis.md).
- Bootloader must be protected; losing it could disable Up-button USB recovery.

## Builds

`make` builds the simple original skeleton only.

`make usb-probe` builds a **separate, untested** USB device-enumeration probe using LGPL-licensed [libopencm3](https://github.com/libopencm3/libopencm3). GitHub Actions fetches and builds pinned libopencm3 automatically. The USB probe aims to appear as a distinct vendor-specific USB device, not a GameCube adapter or HID.

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
2. Whether Up-button recovery is guaranteed to work with a broken/absent app.
3. Whether USB crystal and pull-up assumptions of the probe match actual Frame1 PCB.
4. How all buttons are wired; how to implement Joybus output and port tournament-nerfed HayBox logic.

Never commit the original closed-source Frame1 firmware dump or serial identifiers to this public repo. Any eventual uploader must explicitly protect `0x08000000..0x0801FFFF`, reject mass erase, and verify a post-write readback.
