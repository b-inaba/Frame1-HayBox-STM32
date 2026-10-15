/* STM32F303VET6: 512 KiB main flash, 64 KiB standard SRAM (+16 KiB CCM).
   Frame1 DFU bootloader and reserved region occupy 0x08000000-0x0801ffff.
   DO NOT link program at 0x08000000. */
ENTRY(Reset_Handler)
MEMORY {
    FLASH (rx)  : ORIGIN = 0x08020000, LENGTH = 384K
    SRAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 64K
}
_estack = ORIGIN(SRAM) + LENGTH(SRAM);
SECTIONS {
    .isr_vector : ALIGN(512) { KEEP(*(.isr_vector)) } > FLASH
    .text : ALIGN(4) {
        *(.text*) *(.rodata*)
        . = ALIGN(4);
    } > FLASH
    .ARM.exidx : { *(.ARM.exidx*) } > FLASH
    .data : ALIGN(4) {
        _sdata = .;
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } > SRAM AT > FLASH
    _sidata = LOADADDR(.data);
    .bss (NOLOAD) : ALIGN(4) {
        _sbss = .;
        *(.bss*) *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } > SRAM
    /DISCARD/ : { *(.comment*) *(.note*) }
}
ASSERT(SIZEOF(.isr_vector) > 8, "Missing vector table")
