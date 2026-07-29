/**
 * dev_config_runtime.h / dev_config_runtime.c
 *
 * 取代原本 Waveshare 的 DEV_Config.h/c。
 *
 * 差別：
 *   - 不再使用 compile-time #define pin number。
 *   - 所有 GPIO/SPI 操作接受明確的 PinConfig 參數，或透過一個
 *     module-level 的 g_cfg (由 DEV_ModuleInit_WithConfig 設定)。
 *   - 支援 RPi 5 (gpiochip4) 自動偵測。
 *   - 使用 lgpio 作為底層 (USE_DEV_LIB)。
 */

#ifndef DEV_CONFIG_RUNTIME_H
#define DEV_CONFIG_RUNTIME_H

#include <stdint.h>
#include "pin_config.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef uint8_t  UBYTE;
typedef uint16_t UWORD;
typedef uint32_t UDOUBLE;

/* ------------------------------------------------------------------ */
/*  Module 初始化 (傳入 config)                                        */
/* ------------------------------------------------------------------ */

/**
 * DEV_ModuleInit_WithConfig()
 *
 * 初始化 GPIO chip 與 SPI，使用呼叫端提供的 DisplayConfig。
 * 成功回傳 0，失敗回傳非零。
 */
int DEV_ModuleInit_WithConfig(const DisplayConfig *cfg);

/**
 * DEV_ModuleExit()
 *
 * 關閉 SPI 與 GPIO chip。
 */
void DEV_ModuleExit(void);

/* ------------------------------------------------------------------ */
/*  GPIO 操作                                                          */
/* ------------------------------------------------------------------ */

void  DEV_GPIO_Mode(int pin, int mode);   /* mode: 1=output, 0=input */
void  DEV_Digital_Write(int pin, int value);
int   DEV_Digital_Read(int pin);
void  DEV_Delay_ms(unsigned int ms);

/* ------------------------------------------------------------------ */
/*  SPI 操作                                                           */
/* ------------------------------------------------------------------ */

void DEV_SPI_WriteByte(uint8_t value);
void DEV_SPI_Write_nByte(const uint8_t *data, uint32_t len);

/* ------------------------------------------------------------------ */
/*  背光 (僅 LCD；OLED bl=-1 時為 no-op)                              */
/* ------------------------------------------------------------------ */

void DEV_SetBacklight(int value);   /* value: 0=off, 1=on */

#ifdef __cplusplus
}
#endif

#endif /* DEV_CONFIG_RUNTIME_H */
