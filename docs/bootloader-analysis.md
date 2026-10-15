# Read-only DFU bootloader analysis

This report summarizes **observations from a locally supplied 524,288-byte flash dump**. The proprietary binary itself is intentionally not committed.

## Layout

| Byte offset | Flash address | Observation |
|---|---|---|
| `0x00000` | `0x08000000` | Bootloader vector table, MSP `0x20010000`, reset `0x08008075` |
| `0x08800` | `0x08008800` | First fully erased 2-KiB page after bootloader |
| `0x20000` | `0x08020000` | Original controller application vector table, reset `0x08023FA9` |
| `0x2A800` | `0x0802A800` | First fully erased 2-KiB page after application |
| `0x80000` | `0x08080000` | Physical flash end (exclusive) |

The bootloader is in **regular user flash**, not exclusively the immutable factory system ROM. The Up-button recovery behavior could depend on it.

## Erasing routine — evidence (bootloader offsets)

Inspected ARM Thumb instructions using LLVM objdump locally:

- At `+0x0888..0x0890`, code accesses `FLASH_CR` and sets bit 1, `PER` (page erase).
- At `+0x0892..0x0898`, the target page address is written to `FLASH_AR` (register offset `+0x14` from `0x40022000`).
- At `+0x089A..0x08A4`, it sets bit 6, `STRT`, starting an actual page erase.
- At `+0x07E6..0x081A`, a loop calls that erase routine then increments the page address by `0x800` (2,048 bytes).
- At `+0x081A..0x082A`, the loop count is also scaled by `0x800`.

**Interpretation:** the internal erase routine is page-based and compatible with STM32F303's real 2-KiB flash pages, despite the DFU interface advertising F4-style larger sectors. This is **static analysis, not a tested end-to-end DFU write**.

## Remaining hazard

A PC-side DFU client may use the misleading sector descriptor to calculate how many erase requests to send. A 128-KiB host "sector" erase request might erase just **one 2-KiB device page**, leaving old data in the other pages. Programming there could fail or corrupt the app. Conversely, an unexpectedly broad erase could damage the loader. We have not yet traced the entire command dispatcher or tested write behavior.

**Do not flash yet.** Any future uploader must understand the real page granularity, restrict requests to `0x08020000`–`0x0807FFFF`, verify the protected loader pages, and read back written data before celebrating.

Reference: ST RM0316, section 4, page-erase algorithm and flash map. https://www.st.com/resource/en/reference_manual/dm00043574.pdf
