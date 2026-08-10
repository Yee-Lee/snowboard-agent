/**
 * waveshare_ssd1351 — Native driver for Waveshare 1.5-inch OLED (SSD1351).
 *
 * Panel:      128 × 128, RGB565
 * Interface:  SPI (lgpio)
 *
 * Implements the stable C ABI defined in native/include/display.h.
 * This file is the display_driver.c equivalent, rewritten to:
 *   - Return error codes instead of printing and continuing.
 *   - Expose the versioned ABI (display_open / display_get_info /
 *     display_present_rgb565 / display_present_rect_rgb565 /
 *     display_clear / display_close).
 *
 * Compile:
 *   make      → produces libdisplay.so
 */

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "OLED_1in5_rgb.h"
#include "DEV_Config.h"
#include "../include/display.h"

#define OLED_WIDTH  128
#define OLED_HEIGHT 128
#define FRAME_BYTES (OLED_WIDTH * OLED_HEIGHT * 2)  /* RGB565 */
#define RGB888_BYTES (OLED_WIDTH * OLED_HEIGHT * 3)

/* Only one handle is supported; handle value 1 means open. */
static int g_is_open = 0;

/* ------------------------------------------------------------------ */
int display_open(const DisplayConfig *config)
{
    if (g_is_open) {
        fprintf(stderr, "[ssd1351] Already open\n");
        return 1;  /* return existing handle */
    }

    if (DEV_ModuleInit_WithConfig(config) != 0) {
        fprintf(stderr, "[ssd1351] GPIO/SPI init failed\n");
        return 0;  /* 0 == failure */
    }

    OLED_1in5_rgb_Init();
    OLED_1in5_rgb_Clear();

    g_is_open = 1;
    return 1;  /* handle */
}

/* ------------------------------------------------------------------ */
int display_get_info(int handle, DisplayInfo *out)
{
    if (!handle || !g_is_open || !out) return -1;

    out->width  = OLED_WIDTH;
    out->height = OLED_HEIGHT;
    strncpy(out->name, "waveshare_oled_1in5_rgb", sizeof(out->name) - 1);
    out->name[sizeof(out->name) - 1] = '\0';
    return 0;
}

/* ------------------------------------------------------------------ */
int display_present_rgb565(int handle, const uint8_t *buffer, int length)
{
    if (!handle || !g_is_open) return -1;

    if (length != FRAME_BYTES) {
        fprintf(stderr, "[ssd1351] present: expected %d bytes, got %d\n",
                FRAME_BYTES, length);
        return -2;
    }

    /* OLED_1in5_rgb_Display expects a non-const pointer; we cast safely
     * since the underlying SPI write does not modify the buffer. */
    OLED_1in5_rgb_Display((uint8_t *)buffer);
    return 0;
}

/* ------------------------------------------------------------------ */
int display_present_rect_rgb565(int handle,
                                int x, int y,
                                int width, int height,
                                const uint8_t *buffer, int length)
{
    /* The SSD1351 supports window addressing; for now fall back to full
     * frame re-send.  A proper partial-update path can be added later
     * by implementing OLED_1in5_rgb_DisplayWindow(). */
    (void)x; (void)y; (void)width; (void)height;
    return display_present_rgb565(handle, buffer, length);
}

/* ------------------------------------------------------------------ */
void display_clear(int handle)
{
    if (!handle || !g_is_open) return;
    OLED_1in5_rgb_Clear();
}

/* ------------------------------------------------------------------ */
void display_close(int handle)
{
    if (!handle || !g_is_open) return;
    OLED_1in5_rgb_Clear();
    DEV_ModuleExit();
    g_is_open = 0;
}
