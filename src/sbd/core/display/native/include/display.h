/** Stable native display ABI v1. */
#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>
#include "pin_config.h"

#ifdef __cplusplus
extern "C" {
#endif

#define DISPLAY_ABI_VERSION UINT32_C(1)
#define DISPLAY_INVALID_HANDLE INT32_C(0)

typedef int32_t DisplayHandle;

typedef enum {
    DISPLAY_OK = 0,
    DISPLAY_E_INVALID_ARGUMENT = -1,
    DISPLAY_E_ABI_MISMATCH = -2,
    DISPLAY_E_BAD_CONFIG = -3,
    DISPLAY_E_ALREADY_OPEN = -4,
    DISPLAY_E_NOT_OPEN = -5,
    DISPLAY_E_INVALID_HANDLE = -6,
    DISPLAY_E_BUFFER_SIZE = -7,
    DISPLAY_E_WRONG_THREAD = -8,
    DISPLAY_E_GPIO = -9,
    DISPLAY_E_SPI = -10,
    DISPLAY_E_PANEL = -11,
    DISPLAY_E_INTERNAL = -12
} DisplayStatus;

typedef struct {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t width;
    uint32_t height;
    uint32_t pixel_format;
    uint32_t byte_order;
    uint32_t buffer_bytes;
    char name[64];
} DisplayInfo;

/** Return the ABI implemented by the loaded artifact. Thread-safe. */
uint32_t display_abi_version(void);

/**
 * Open one display. The config is copied before return.
 * The caller receives a non-zero handle only when DISPLAY_OK is returned.
 */
DisplayStatus display_open(const DisplayConfig *config,
                           DisplayHandle *out_handle);

/** Fill caller-owned metadata. Must run on the owner thread. */
DisplayStatus display_get_info(DisplayHandle handle, DisplayInfo *out_info);

/**
 * Present one full RGB565_MSB_FIRST frame.
 * The buffer is borrowed only for this call and is never modified or retained.
 */
DisplayStatus display_present_rgb565(DisplayHandle handle,
                                     const uint8_t *buffer,
                                     uint32_t length);

/** Release all resources. Invalid/already-closed handles return an error. */
DisplayStatus display_close(DisplayHandle handle);

#ifdef __cplusplus
}
#endif

#endif
