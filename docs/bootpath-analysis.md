# Frame1 boot sequence — static reconstruction (October 2026)

This is from a user's **offline 512 KiB flash readback**. No proprietary image, device serial, or flash operations are included in the repository. Addresses below are absolute MCU flash addresses. LLVM Thumb disassembly was used to follow code paths.

## Boot sequence in original bootloader

1. The bootloader's own vector table begins at \`0x08000000\`; its reset vector points to \`0x08008075\`.
2. Its reset routine reaches the main boot decision at **\`0x08007334\`**.
3. The routine configures GPIOs and reads several button pins, e.g. through a helper at \`0x08000BCC\` which reads **GPIOx_IDR at register offset +0x10** and masks requested pins.
4. At **\`0x080073FC..0x08007406\`** an input-dependent branch selects the DFU boot path vs the application boot path.
5. When the app path is selected, at **\`0x08007408\`** the code reads the first word from \`0x08020000\`, checks \`initial_sp & 0x2FFE0000 == 0x20000000\`, and branches into DFU if this fails.
6. At **\`0x08007420..0x0800742E\`** it reads the app vector table, executes \`msr msp, r3\` and \`blx r3\` using the app reset vector at \`0x08020004\`.
7. On the DFU path, **\`0x08007430\`** calls \`0x08007794\`, where the bootloader starts its USB DFU service.

### What this proves — and what it doesn't

**Strong static evidence:** the bootloader decides whether to boot the controller application from *its own* code and GPIO input reads. Entering USB DFU therefore does not appear to require functional application code. A malformed application stack pointer is explicitly routed to the DFU path. This improves our expected recoverability if a test application doesn't run.

**Still unproven on hardware:** whether holding Up reliably forces this branch *with a broken application*, whether USB DFU works after arbitrary application memory is erased, and whether a future write can never erase bootloader pages. The original bootloader resides in mutable user flash, so incorrect erase commands are still a bricking risk.

**Only one validity condition was seen before the jump**: stack pointer address mask. The reset vector does not appear to be validated before \`blx\`; a bad reset vector with a plausible stack might crash rather than fall back to DFU. Button override is critical.

## Application initialization implication

The bootloader uses a **\`blx\` handoff**, not an MCU system reset. USB peripheral clocks, RCC PLL state, NVIC pending interrupts, and SysTick may retain state from the loader. The replacement firmware must sanitize these:

- disable interrupts, stop SysTick, disable and clear pending NVIC IRQs, and relocate VTOR;
- before calling libopencm3's \`rcc_clock_setup_pll\`, select HSI as SYSCLK because that routine turns off PLL;
- reset and reinitialize USB peripheral before new enumeration.

Our build-only USB test application now includes these mitigations, but **no hardware execution has been tested**.

## Literal constants recovered

| Address | Value | Meaning |
|---|---|---|
| \`0x08007454\` | \`0x08020000\` | Application vector table base |
| \`0x08007458\` | \`0x2FFE0000\` | MSP plausibility mask |
| \`0x0800745C\` | \`0x08020004\` | Reset handler vector address |

See [bootloader-analysis.md](bootloader-analysis.md) and [DFU write planning](dfu-update-plan.md). These are static observations only, not a blanket endorsement of flashing.
