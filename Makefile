# GNU Arm Embedded Toolchain. NO FLASH TARGET.
CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size
CFLAGS = -mcpu=cortex-m4 -mthumb -mfloat-abi=soft -Os -std=gnu11 -ffreestanding -fdata-sections -ffunction-sections -Wall -Wextra -Werror
LDFLAGS = -TSTM32F303VE_app.ld -nostdlib -Wl,--gc-sections

all: build/frame1-app.bin check

build:
	mkdir -p build

build/frame1.elf: src/startup.c src/main.c STM32F303VE_app.ld | build
	$(CC) $(CFLAGS) $(LDFLAGS) -Wl,-Map=build/frame1.map src/startup.c src/main.c -o $@
	$(SIZE) $@

build/frame1-app.bin: build/frame1.elf
	$(OBJCOPY) -O binary $< $@

check: build/frame1-app.bin
	python3 scripts/check_app.py build/frame1-app.bin

# Build-only USB device descriptor / EP0 prototype.
# Library downloaded and built by CI; no device programming is performed.
LIBOPENCM3 = external/libopencm3
build/frame1-usb-probe.elf: src/startup.c src/usb_probe.c STM32F303VE_app.ld | build
	@test -f $(LIBOPENCM3)/lib/libopencm3_stm32f3.a || (echo "Run library setup from README" && exit 1)
	$(CC) $(CFLAGS) -DSTM32F3 -I$(LIBOPENCM3)/include $(LDFLAGS) -Wl,-Map=build/frame1-usb-probe.map src/startup.c src/usb_probe.c -L$(LIBOPENCM3)/lib -lopencm3_stm32f3 -lc -lgcc -lnosys -o $@
	$(SIZE) $@

build/frame1-usb-probe.bin: build/frame1-usb-probe.elf
	$(OBJCOPY) -O binary $< $@

usb-probe: build/frame1-usb-probe.bin
	python3 scripts/check_app.py build/frame1-usb-probe.bin

clean:
	rm -rf build

.PHONY: all clean check usb-probe
