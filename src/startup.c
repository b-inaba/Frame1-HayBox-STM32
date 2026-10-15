#include <stdint.h>

extern uint32_t _estack;
extern uint32_t _sidata, _sdata, _edata;
extern uint32_t _sbss, _ebss;
int main(void);

void Reset_Handler(void);
void Default_Handler(void);

/* These are the initial MSP and exception vectors at 0x08020000.
   The hardware/Frame1 bootloader must transfer control appropriately. */
__attribute__((section(".isr_vector"), used, aligned(512)))
const void * const vectors[16 + 82] = {
    [0] = &_estack,
    [1] = (void *)Reset_Handler,
    [2 ... 97] = (void *)Default_Handler
};

void Reset_Handler(void) {
    /* Relocate the application vector table for interrupts. */
    *(volatile uint32_t *)0xE000ED08u = 0x08020000u;
    for (uint32_t *dst = &_sdata, *src = &_sidata; dst < &_edata; ) {
        *dst++ = *src++;
    }
    for (uint32_t *dst = &_sbss; dst < &_ebss; ) {
        *dst++ = 0u;
    }
    (void)main();
    for (;;) { __asm__ volatile ("wfi"); }
}
void Default_Handler(void) {
    for (;;) { __asm__ volatile ("wfi"); }
}
