/** Optional native ABI v1 driver for Waveshare 2-inch LCD / ST7789. */
#include <pthread.h>
#include <stdint.h>
#include <string.h>

#include "LCD_2inch.h"
#include "DEV_Config.h"
#include "../include/display.h"

#define LCD_WIDTH ((uint32_t)LCD_2IN_WIDTH)
#define LCD_HEIGHT ((uint32_t)LCD_2IN_HEIGHT)
#define FRAME_BYTES (LCD_WIDTH * LCD_HEIGHT * UINT32_C(2))

static int g_is_open = 0;
static pthread_t g_owner_thread;

static int is_owner_thread(void)
{
    return g_is_open && pthread_equal(g_owner_thread, pthread_self());
}

static DisplayStatus validate_config(const DisplayConfig *config)
{
    if (config == NULL) return DISPLAY_E_INVALID_ARGUMENT;
    if (config->abi_version != DISPLAY_ABI_VERSION ||
        config->struct_size != (uint32_t)sizeof(DisplayConfig)) {
        return DISPLAY_E_ABI_MISMATCH;
    }
    if (config->width != LCD_WIDTH || config->height != LCD_HEIGHT ||
        config->rotation_degrees != 0 ||
        config->pixel_format != DISPLAY_PIXEL_FORMAT_RGB565 ||
        config->byte_order != DISPLAY_BYTE_ORDER_MSB_FIRST ||
        config->buffer_bytes != FRAME_BYTES ||
        config->pins.dc < 0 || config->pins.rst < 0 ||
        config->pins.bl < 0 || config->spi.bus < 0 ||
        config->spi.chip < 0 || config->spi.mode != 0 ||
        config->spi.speed_hz == 0 || config->gpio_chip.chip_index < 0) {
        return DISPLAY_E_BAD_CONFIG;
    }
    return DISPLAY_OK;
}

uint32_t display_abi_version(void)
{
    return DISPLAY_ABI_VERSION;
}

DisplayStatus display_open(const DisplayConfig *config,
                           DisplayHandle *out_handle)
{
    DisplayStatus status;
    int rc;

    if (out_handle == NULL) return DISPLAY_E_INVALID_ARGUMENT;
    *out_handle = DISPLAY_INVALID_HANDLE;
    if (g_is_open) return DISPLAY_E_ALREADY_OPEN;
    status = validate_config(config);
    if (status != DISPLAY_OK) return status;

    rc = DEV_ModuleInit_WithConfig(config);
    if (rc != 0) return rc == -3 ? DISPLAY_E_SPI : DISPLAY_E_GPIO;

    DEV_ClearError();
    LCD_2IN_Init();
    if (DEV_LastError() < 0) {
        DEV_ModuleExit();
        return DISPLAY_E_PANEL;
    }

    g_owner_thread = pthread_self();
    g_is_open = 1;
    *out_handle = INT32_C(1);
    return DISPLAY_OK;
}

DisplayStatus display_get_info(DisplayHandle handle, DisplayInfo *out_info)
{
    if (!g_is_open) return DISPLAY_E_NOT_OPEN;
    if (handle != INT32_C(1)) return DISPLAY_E_INVALID_HANDLE;
    if (!is_owner_thread()) return DISPLAY_E_WRONG_THREAD;
    if (out_info == NULL) return DISPLAY_E_INVALID_ARGUMENT;

    *out_info = (DisplayInfo){0};
    out_info->abi_version = DISPLAY_ABI_VERSION;
    out_info->struct_size = (uint32_t)sizeof(DisplayInfo);
    out_info->width = LCD_WIDTH;
    out_info->height = LCD_HEIGHT;
    out_info->pixel_format = DISPLAY_PIXEL_FORMAT_RGB565;
    out_info->byte_order = DISPLAY_BYTE_ORDER_MSB_FIRST;
    out_info->buffer_bytes = FRAME_BYTES;
    strncpy(out_info->name, "waveshare_st7789", sizeof(out_info->name) - 1);
    return DISPLAY_OK;
}

DisplayStatus display_present_rgb565(DisplayHandle handle,
                                     const uint8_t *buffer,
                                     uint32_t length)
{
    if (!g_is_open) return DISPLAY_E_NOT_OPEN;
    if (handle != INT32_C(1)) return DISPLAY_E_INVALID_HANDLE;
    if (!is_owner_thread()) return DISPLAY_E_WRONG_THREAD;
    if (buffer == NULL) return DISPLAY_E_INVALID_ARGUMENT;
    if (length != FRAME_BYTES) return DISPLAY_E_BUFFER_SIZE;

    DEV_ClearError();
    LCD_2IN_Display((uint8_t *)buffer);
    return DEV_LastError() < 0 ? DISPLAY_E_SPI : DISPLAY_OK;
}

DisplayStatus display_close(DisplayHandle handle)
{
    if (!g_is_open) return DISPLAY_E_NOT_OPEN;
    if (handle != INT32_C(1)) return DISPLAY_E_INVALID_HANDLE;
    if (!is_owner_thread()) return DISPLAY_E_WRONG_THREAD;

    DEV_ModuleExit();
    g_is_open = 0;
    return DISPLAY_OK;
}
