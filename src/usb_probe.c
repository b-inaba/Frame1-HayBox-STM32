/* Experimental USB enumeration probe. BUILD-ONLY, NOT APPROVED FOR FLASH.
 * STM32F303xE full-speed USB, assumes the PCB's HSE oscillator is 8 MHz.
 * Uses libopencm3 (LGPL-3.0-or-later) for USB endpoint-zero enumeration.
 * Uses temporary TEST-ONLY USB identifiers; not for redistribution as a product.
 */
#include <libopencm3/stm32/rcc.h>
#include <libopencm3/usb/usbd.h>
#include <libopencm3/usb/usbstd.h>

static const struct usb_device_descriptor device_desc = {
    .bLength = USB_DT_DEVICE_SIZE,
    .bDescriptorType = USB_DT_DEVICE,
    .bcdUSB = 0x0200,
    .bDeviceClass = 0x00,
    .bDeviceSubClass = 0x00,
    .bDeviceProtocol = 0x00,
    .bMaxPacketSize0 = 64,
    .idVendor = 0xcafe, /* Temporary experimental ID: not allocated to this project */
    .idProduct = 0xf303,
    .bcdDevice = 0x0001,
    .iManufacturer = 1,
    .iProduct = 2,
    .iSerialNumber = 0,
    .bNumConfigurations = 1
};
static const struct usb_interface_descriptor interface_desc = {
    .bLength = USB_DT_INTERFACE_SIZE,
    .bDescriptorType = USB_DT_INTERFACE,
    .bInterfaceNumber = 0,
    .bAlternateSetting = 0,
    .bNumEndpoints = 0,
    .bInterfaceClass = 0xff, /* Vendor-specific; no Windows driver expected */
    .bInterfaceSubClass = 0,
    .bInterfaceProtocol = 0,
    .iInterface = 0
};
static const struct usb_interface interfaces[] = {
    {.num_altsetting = 1, .altsetting = &interface_desc}
};
static const struct usb_config_descriptor config_desc = {
    .bLength = USB_DT_CONFIGURATION_SIZE,
    .bDescriptorType = USB_DT_CONFIGURATION,
    .wTotalLength = 0, /* libopencm3 generates total from interfaces */
    .bNumInterfaces = 1,
    .bConfigurationValue = 1,
    .iConfiguration = 0,
    .bmAttributes = 0x80,
    .bMaxPower = 50, /* 100 mA */
    .interface = interfaces
};
static const char *usb_strings[] = {
    "Frame1 community experiment",
    "Frame1 STM32 USB Probe (UNTESTED)"
};
static uint8_t control_buffer[128];

int main(void) {
    /* Assumed 8-MHz HSE -> 72-MHz CPU / 48-MHz USB via PLL / 1.5.
       Must verify crystal and actual USB wiring before flashing! */
    /* Important: the Frame1 user-flash bootloader BLX-jumps to our app
       without resetting RCC. Its PLL may already be SYSCLK. libopencm3's
       clock_setup_pll turns PLL off, so first switch SYSCLK back to HSI. */
    rcc_osc_on(RCC_HSI);
    rcc_wait_for_osc_ready(RCC_HSI);
    rcc_set_sysclk_source(RCC_CFGR_SW_HSI);
    rcc_wait_for_sysclk_status(RCC_HSI);
    rcc_clock_setup_pll(&rcc_hse8mhz_configs[0]);
    rcc_periph_clock_enable(RCC_USB);
    rcc_periph_reset_pulse(RST_USB);
    /* On F303xD/E, USB D+/D- connect directly when USB peripheral is enabled:
       do NOT configure PA11/PA12 as an alternate function. (ST AN4807) */

    usbd_device *dev = usbd_init(
        &st_usbfs_v1_usb_driver, &device_desc, &config_desc,
        usb_strings, 2, control_buffer, sizeof(control_buffer));

    while (1) {
        usbd_poll(dev);
    }
}
