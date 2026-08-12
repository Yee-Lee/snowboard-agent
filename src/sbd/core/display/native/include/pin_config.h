/** Runtime configuration shared by the Python adapter and native driver. */
#ifndef DISPLAY_PIN_CONFIG_H
#define DISPLAY_PIN_CONFIG_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define DISPLAY_CONFIG_VERSION UINT32_C(1)

typedef enum {
    DISPLAY_PIXEL_FORMAT_RGB565 = 1
} DisplayPixelFormat;

typedef enum {
    DISPLAY_BYTE_ORDER_MSB_FIRST = 1
} DisplayByteOrder;

typedef struct {
    int32_t bus;
    int32_t chip;
    uint32_t speed_hz;
    uint32_t mode;
} SpiConfig;

typedef struct {
    int32_t chip_index; /* resolved gpiochip index; no implicit default */
} GpiochipConfig;

typedef struct {
    int32_t rst;
    int32_t dc;
    int32_t cs; /* reserved; SPI CE is managed by SpiConfig.chip */
    int32_t bl; /* -1 when absent */
} DisplayPinConfig;

typedef struct {
    uint32_t abi_version;
    uint32_t struct_size;
    DisplayPinConfig pins;
    SpiConfig spi;
    GpiochipConfig gpio_chip;
    uint32_t width;
    uint32_t height;
    uint32_t rotation_degrees;
    uint32_t pixel_format;
    uint32_t byte_order;
    uint32_t buffer_bytes;
} DisplayConfig;

static inline void display_config_init(DisplayConfig *config)
{
    if (config == NULL) return;
    *config = (DisplayConfig){0};
    config->abi_version = DISPLAY_CONFIG_VERSION;
    config->struct_size = (uint32_t)sizeof(DisplayConfig);
    config->pins.rst = -1;
    config->pins.dc = -1;
    config->pins.cs = -1;
    config->pins.bl = -1;
    config->gpio_chip.chip_index = -1;
    config->pixel_format = DISPLAY_PIXEL_FORMAT_RGB565;
    config->byte_order = DISPLAY_BYTE_ORDER_MSB_FIRST;
}

#ifdef __cplusplus
}
#endif

#endif
