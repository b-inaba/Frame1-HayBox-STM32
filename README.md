# Frame1 STM32F303 HayBox port — bring-up skeleton

**Research build only. NOT READY TO FLASH.** This is a minimal linker/startup project, not HayBox yet.

## Hardware discoveries from the supplied 512 KiB flash dump

- MCU as identified in photo: STM32F303VET6 (confirm top marking as necessary)
- DFU USB interface: VID 0483, PID DF11
- Vector table of bootloader at `0x08000000`
- Application vector table at `0x08020000`
- All bytes at `0x08010000...0x0801ffff` are `0xff`
- Bootloader code extends beyond `0x08008000`
- Physical flash: 2 KiB pages per ST RM0316
- DFU-reported memory descriptor instead describes F4-style **16/64/128 KiB sectors**
- **Crucial:** firmware DFU bootloader lives in writable user flash, so `mass-erase`, `unprotect`, or an incorrect erase range may destroy it. Backup alone does not guarantee USB recovery.

## Build with GitHub Actions

This repository's **Build STM32F303 application** workflow compiles and checks the linker layout without accessing any hardware. On a Linux host with `arm-none-eabi-gcc`, run `make`.

The linked app has a vector table at `0x08020000`. The implementation currently just loops. There is no observable behavior, so **do not flash this build**.

## Next tasks

1. Read/disassemble the bootloader's flash-erasing function to determine actual erase behavior versus advertised DFU sectors. Test this off-device.
2. Document DFU boot-entry condition (hardware Up at boot vs bootloader GPIO logic); continue to preserve `0x08000000...0x0801ffff`.
3. Add STM32F3 USB driver and an identifiable CDC/HID test, *then* decide on a cautious first write.
4. Map button GPIOs and port HayBox logic, followed by GameCube Joybus output.

## Do not

Do not use `dfu-util -D`, `:mass-erase`, `:unprotect`, `:force`, or change option bytes on the current board until the bootloader behavior is validated.

**Do not commit private dumps or the original proprietary Frame1 firmware into this public repository.**
