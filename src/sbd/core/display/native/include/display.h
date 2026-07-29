/**
 * display.h — Stable C ABI for all native display drivers.
 *
 * Every native driver (waveshare_ssd1351, waveshare_st7789, …) must
 * implement this interface.  The Python HAL layer (ctypes_backend.py)
 * calls only these symbols; it never reaches into driver internals.
 *
 * Pin mapping is passed at display_open() time via DisplayConfig
 * (defined in pin_config.h); no pin numbers are hardcoded in the driver.
 *
 * Design rules
 * ------------
 * - All functions return 0 on success, a negative errno-compatible
 *   value on failure (never silently swallow errors or just printf).
 * - display_open / display_present_rgb565 / display_clear /
 *   display_close MUST be called from the same OS thread.
 * - display_get_info may be called from any thread after open().
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>
#include <stddef.h>
#include "pin_config.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ------------------------------------------------------------------ */
/*  Display info                                                        */
/* ------------------------------------------------------------------ */

typedef struct {
    int  width;        /* physical panel width  in pixels */
    int  height;       /* physical panel height in pixels */
    char name[64];     /* e.g. "waveshare_oled_1in5_rgb"  */
} DisplayInfo;

/* ------------------------------------------------------------------ */
/*  Lifecycle                                                           */
/* ------------------------------------------------------------------ */

/**
 * display_open() — Initialise the panel with a pin/SPI configuration.
 *
 * @param config  Pointer to a DisplayConfig describing GPIO pins and SPI
 *                settings.  Pass NULL to use the driver's built-in defaults.
 * @return        A non-zero handle on success, 0 on failure.
 */
int display_open(const DisplayConfig *config);

/**
 * display_get_info() — Return panel metadata.
 *
 * May be called from any thread after display_open() succeeds.
 *
 * @param handle  Handle returned by display_open().
 * @param out     Caller-allocated DisplayInfo to fill.
 * @return        0 on success, negative on error.
 */
int display_get_info(int handle, DisplayInfo *out);

/**
 * display_close() — Release all hardware resources.
 *
 * @param handle  Handle returned by display_open().
 */
void display_close(int handle);

/* ------------------------------------------------------------------ */
/*  Frame transfer                                                      */
/* ------------------------------------------------------------------ */

/**
 * display_present_rgb565() — Push a full-screen frame.
 *
 * @param handle  Handle returned by display_open().
 * @param buffer  RGB565 pixel data, row-major, big-endian.
 *                Length must equal width * height * 2.
 * @param length  Byte count of @buffer.
 * @return        0 on success, negative on error.
 */
int display_present_rgb565(int handle, const uint8_t *buffer, int length);

/**
 * display_present_rect_rgb565() — Push a partial frame.
 *
 * @param handle  Handle returned by display_open().
 * @param x, y   Top-left corner of the destination rectangle.
 * @param width, height  Size of the rectangle.
 * @param buffer  RGB565 data for the rectangle (width * height * 2 bytes).
 * @param length  Byte count of @buffer.
 * @return        0 on success, negative on error.
 */
int display_present_rect_rgb565(int handle,
                                int x, int y,
                                int width, int height,
                                const uint8_t *buffer, int length);

/**
 * display_clear() — Fill the entire panel with black (0x0000).
 *
 * @param handle  Handle returned by display_open().
 */
void display_clear(int handle);

#ifdef __cplusplus
}
#endif

#endif /* DISPLAY_H */
