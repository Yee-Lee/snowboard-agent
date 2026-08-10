/**
 * waveshare_st7789 — Native driver for Waveshare 2-inch LCD (ST7789).
 *
 * Panel:      320 × 240, RGB565
 * Interface:  SPI (lgpio)
 *
 * Implements the stable C ABI defined in native/include/display.h.
 *
 * The "waveshare_lcd_2in_rgb_128" scaling mode (128×128 centred on 320×240)
 * is NOT handled here; it is now a HAL profile / renderer layout strategy.
 * This driver always operates at full 320×240 native resolution.
 *
 * Compile:
 *   make      → produces libdisplay.so
 */

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "LCD_2inch.h"
#include "DEV_Config.h"
#include "../include/display.h"

#define LCD_WIDTH   LCD_2IN_WIDTH    /* 320 */
#define LCD_HEIGHT  LCD_2IN_HEIGHT   /* 240 */
#define FRAME_BYTES (LCD_WIDTH * LCD_HEIGHT * 2)  /* RGB565 */

/* Only one handle is supported; handle value 1 means open. */
static int g_is_open = 0;

/* ------------------------------------------------------------------ */
int display_open(const DisplayConfig *config)
{
    if (g_is_open) {
        fprintf(stderr, "[st7789] Already open\n");
        return 1;
    }

    if (DEV_ModuleInit_WithConfig(config) != 0) {
        fprintf(stderr, "[st7789] GPIO/SPI init failed\n");
        return 0;
    }

    LCD_2IN_Init();
    LCD_2IN_Clear(0x0000);

    g_is_open = 1;
    return 1;
}

/* ------------------------------------------------------------------ */
int display_get_info(int handle, DisplayInfo *out)
{
    if (!handle || !g_is_open || !out) return -1;

    out->width  = LCD_WIDTH;
    out->height = LCD_HEIGHT;
    strncpy(out->name, "waveshare_lcd_2in_rgb", sizeof(out->name) - 1);
    out->name[sizeof(out->name) - 1] = '\0';
    return 0;
}

/* ------------------------------------------------------------------ */
int display_present_rgb565(int handle, const uint8_t *buffer, int length)
{
    if (!handle || !g_is_open) return -1;

    if (length != FRAME_BYTES) {
        fprintf(stderr, "[st7789] present: expected %d bytes, got %d\n",
                FRAME_BYTES, length);
        return -2;
    }

    LCD_2IN_Display((uint8_t *)buffer);
    return 0;
}

/* ------------------------------------------------------------------ */
int display_present_rect_rgb565(int handle,
                                int x, int y,
                                int width, int height,
                                const uint8_t *buffer, int length)
{
    if (!handle || !g_is_open) return -1;

    int expected = width * height * 2;
    if (length != expected) {
        fprintf(stderr, "[st7789] present_rect: expected %d bytes, got %d\n",
                expected, length);
        return -2;
    }

    LCD_2IN_SetWindow(x, y, x + width - 1, y + height - 1);

    /* Write pixels directly; LCD_2IN_Display always resets the window,
     * so we use the lower-level approach here. */
    for (int i = 0; i < length; i += 2) {
        LCD_2IN_WriteData_Word((buffer[i] << 8) | buffer[i + 1]);
    }
    return 0;
}

/* ------------------------------------------------------------------ */
void display_clear(int handle)
{
    if (!handle || !g_is_open) return;
    LCD_2IN_Clear(0x0000);
}

/* ------------------------------------------------------------------ */
void display_close(int handle)
{
    if (!handle || !g_is_open) return;
    LCD_2IN_Clear(0x0000);
    DEV_ModuleExit();
    g_is_open = 0;
}
