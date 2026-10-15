# Why the default dfu-util write is dangerous on retail Frame1

**No writes to the user's board have been attempted.**

Original DFU interface advertises:
`@Internal Flash /0x08000000/02*016Ka,02*016Kg,01*064Kg,03*128Kg`.

Frame1 hardware is STM32F303VE with **2,048-byte physical flash pages**.
Our separate bootloader disassembly finds code using the F3 FLASH_CR/PER,
FLASH_AR and STRT registers and advancing page addresses in 0x800 increments.

The dfu-util DfuSe download implementation looks up the **advertised**
memory segment page size and uses it to choose erase requests. It may
therefore send just one ERASE_PAGE request for a 128-KiB host-side sector,
while the device erases only a 2-KiB F3 page. Subsequent flash writes would
then target stale, non-erased locations.

Source analysis:
- https://sources.debian.org/src/libdfu-ahp/1.0~git20221215.dd2df39-5/dfuse.c/#L1159
- https://dfu-util.sourceforge.net/dfuse.html

## Planned solution (not executed)

Create independent **2-KiB page binaries** for the new app, 2-KiB aligned
starting at 0x08020000. Include any old application pages that must be
erased to remove stale code (padded entirely with FF when beyond new image).
Each page would be individually erased and written, with its **actual page
start address** passed to the DFU firmware.

Using a *separate dfu-util process* for each native page can prevent its
incorrect larger-sector bookkeeping from suppressing required page erases.
This is justified by dfu-util's source; however **we have not verified**
the Frame1 bootloader implementation end-to-end and the per-page approach
has not been tested on hardware.

Use the offline-only plan creator:

```sh
python scripts/plan_dfu_pages.py --firmware path/to/frame1-usb-probe.bin --backup path/to/frame1-backup.bin --out local-dfu-plans/usb-probe
```

The resulting page files, sha256 values, and manifest are informational.
**There is no executable flashing command in the script.**

### Safety conditions before enabling a writer

- Confirm bootloader entry while holding Up does not require functional
  application firmware, and verify the first 128 KiB never gets erased.
- Verify the behavior of erase and program commands from the bootloader
  dispatcher, including address bounds, alignment, error handling, and
  whether vector validity, checksum or metadata is required to boot an app.
- Confirm HSE frequency, USB D+/D- connectivity and clock configuration for
  candidate USB probe.
- Develop an allowlisted page-by-page writer requiring explicit user opt-in,
  readback-verifying **each** page, stopping on the first error, and
  re-reading the bootloader region to compare against original backup.
- Provide recovery plan (USB DFU if bootloader works; hardware SWD otherwise).
- Do NOT use mass-erase, read-unprotect, or a whole-app dfu-util -D operation.

**Remember:** the existing bootloader resides in normal user flash.
A full stock-firmware download isn't a guaranteed recovery from its loss.
