/**
 * dev_config_runtime.c
 *
 * 實作 GPIO/SPI 底層操作，pin number 全部從 g_cfg 取得（執行時設定），
 * 不再依賴 compile-time #define。
 *
 * 依賴: lgpio (USE_DEV_LIB)
 * 連結: -llgpio
 */

#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <lgpio.h>

#include "dev_config_runtime.h"
#include "pin_config.h"

/* ------------------------------------------------------------------ */
/*  Module-level 狀態 (由 DEV_ModuleInit_WithConfig 填入)              */
/* ------------------------------------------------------------------ */

static int            g_gpio_handle = -1;
static int            g_spi_handle  = -1;
static DisplayConfig  g_cfg;          /* 完整設定的副本 */
static int            g_last_error = 0;

/* ------------------------------------------------------------------ */
/*  Module 初始化                                                      */
/* ------------------------------------------------------------------ */

int DEV_ModuleInit_WithConfig(const DisplayConfig *cfg)
{
    if (!cfg) {
        fprintf(stderr, "[DEV] NULL config\n");
        return -1;
    }
    if (cfg->abi_version != DISPLAY_CONFIG_VERSION ||
        cfg->struct_size != (uint32_t)sizeof(DisplayConfig) ||
        cfg->gpio_chip.chip_index < 0 ||
        cfg->pins.rst < 0 || cfg->pins.dc < 0 ||
        cfg->spi.bus < 0 || cfg->spi.chip < 0 ||
        cfg->spi.speed_hz == 0 || cfg->spi.mode > 3) {
        fprintf(stderr, "[DEV] invalid strict config\n");
        return -1;
    }
    memcpy(&g_cfg, cfg, sizeof(DisplayConfig));
    g_last_error = 0;

    /* 1. 決定 gpiochip index */
    int chip_idx = cfg->gpio_chip.chip_index;

    /* 2. 開啟 GPIO chip */
    g_gpio_handle = lgGpiochipOpen(chip_idx);
    if (g_gpio_handle < 0) {
        fprintf(stderr, "[DEV] lgGpiochipOpen(%d) failed: %d\n",
                chip_idx, g_gpio_handle);
        return -2;
    }

    /* 3. 設定 output pin 方向 */
    if (DEV_GPIO_Mode(cfg->pins.rst, 1) < 0 ||
        DEV_GPIO_Mode(cfg->pins.dc, 1) < 0 ||
        (cfg->pins.cs >= 0 && DEV_GPIO_Mode(cfg->pins.cs, 1) < 0) ||
        (cfg->pins.bl >= 0 && DEV_GPIO_Mode(cfg->pins.bl, 1) < 0)) {
        DEV_ModuleExit();
        return -2;
    }

    /* 背光預設開啟 */
    if (cfg->pins.bl >= 0) {
        if (DEV_Digital_Write(cfg->pins.bl, 1) < 0) {
            DEV_ModuleExit();
            return -2;
        }
    }

    /* 4. 開啟 SPI */
    g_spi_handle = lgSpiOpen(
        cfg->spi.bus,
        cfg->spi.chip,
        cfg->spi.speed_hz,
        cfg->spi.mode
    );
    if (g_spi_handle < 0) {
        fprintf(stderr, "[DEV] lgSpiOpen(bus=%d chip=%d freq=%d) failed: %d\n",
                cfg->spi.bus, cfg->spi.chip, cfg->spi.speed_hz, g_spi_handle);
        lgGpiochipClose(g_gpio_handle);
        g_gpio_handle = -1;
        return -3;
    }

    fprintf(stderr, "[DEV] Init OK — GPIO chip%d, SPI%d.%d @ %d Hz\n",
            chip_idx, cfg->spi.bus, cfg->spi.chip, cfg->spi.speed_hz);
    fprintf(stderr, "[DEV] Pins — CS=%d DC=%d RST=%d BL=%d\n",
            cfg->pins.cs, cfg->pins.dc, cfg->pins.rst, cfg->pins.bl);
    return 0;
}

void DEV_ModuleExit(void)
{
    if (g_spi_handle >= 0) {
        lgSpiClose(g_spi_handle);
        g_spi_handle = -1;
    }
    if (g_gpio_handle >= 0) {
        lgGpiochipClose(g_gpio_handle);
        g_gpio_handle = -1;
    }
}

/* ------------------------------------------------------------------ */
/*  GPIO 操作                                                          */
/* ------------------------------------------------------------------ */

int DEV_GPIO_Mode(int pin, int mode)
{
    if (pin < 0 || g_gpio_handle < 0) return -1;
    int rc;
    if (mode) {
        rc = lgGpioClaimOutput(g_gpio_handle, 0, pin, 0);
    } else {
        rc = lgGpioClaimInput(g_gpio_handle, 0, pin);
    }
    if (rc < 0) g_last_error = rc;
    return rc;
}

int DEV_Digital_Write(int pin, int value)
{
    if (pin < 0 || g_gpio_handle < 0) return -1;
    int rc = lgGpioWrite(g_gpio_handle, pin, value);
    if (rc < 0) g_last_error = rc;
    return rc;
}

int DEV_Digital_Read(int pin)
{
    if (pin < 0 || g_gpio_handle < 0) return 0;
    return lgGpioRead(g_gpio_handle, pin);
}

void DEV_Delay_ms(unsigned int ms)
{
    lguSleep(ms / 1000.0);
}

/* ------------------------------------------------------------------ */
/*  SPI 操作                                                           */
/* ------------------------------------------------------------------ */

int DEV_SPI_WriteByte(uint8_t value)
{
    if (g_spi_handle < 0) return -1;
    int rc = lgSpiWrite(g_spi_handle, (const char *)&value, 1);
    if (rc < 0) g_last_error = rc;
    return rc < 0 ? rc : 0;
}

int DEV_SPI_Write_nByte(const uint8_t *data, uint32_t len)
{
    if (g_spi_handle < 0 || !data || len == 0) return -1;
    int rc = lgSpiWrite(g_spi_handle, (const char *)data, (int)len);
    if (rc < 0) g_last_error = rc;
    return rc < 0 ? rc : 0;
}

/* ------------------------------------------------------------------ */
/*  背光                                                               */
/* ------------------------------------------------------------------ */

int DEV_SetBacklight(int value)
{
    if (g_cfg.pins.bl < 0) return 0;   /* OLED 無背光 pin，忽略 */
    return DEV_Digital_Write(g_cfg.pins.bl, value ? 1 : 0);
}

int DEV_LastError(void) { return g_last_error; }
void DEV_ClearError(void) { g_last_error = 0; }
int DEV_ResetPin(void) { return g_cfg.pins.rst; }
int DEV_DataCommandPin(void) { return g_cfg.pins.dc; }
int DEV_BacklightPin(void) { return g_cfg.pins.bl; }
