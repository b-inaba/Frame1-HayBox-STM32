# GNU Arm Embedded Toolchain; compile only, never flash
CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size
CFLAGS = -mcpu=cortex-m4 -mthumb -mfloat-abi=soft -Os -std=gnu11 -ffreestanding -fdata-sections -ffunction-sections -Wall -Wextra -Werror
LDFLAGS = -TSTM32F303VE_app.ld -nostdlib -Wl,--gc-sections -Wl,-Map=build/frame1.map

all: build/frame1-app.bin check

build:
	mkdir -p build

build/frame1.elf: src/startup.c src/main.c STM32F303VE_app.ld | build
	$(CC) $(CFLAGS) $(LDFLAGS) src/startup.c src/main.c -o $@
	$(SIZE) $@

build/frame1-app.bin: build/frame1.elf
	$(OBJCOPY) -O binary $< $@

check: build/frame1-app.bin
	python3 scripts/check_app.py build/frame1-app.bin

clean:
	rm -rf build

.PHONY: all clean check
