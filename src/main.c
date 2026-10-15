#include <stdint.h>

/* Bring-up skeleton ONLY. No GPIO or USB is initialized and there is
   no observable signal. It is NOT a flash-ready functional test. */
static volatile uint32_t heartbeat;

int main(void) {
    for (;;) {
        heartbeat++;
        __asm__ volatile ("nop");
    }
}
