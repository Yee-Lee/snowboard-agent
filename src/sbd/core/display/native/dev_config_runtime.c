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
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/spi/spidev.h>
#include "dev_config_runtime.h"
#include "pin_config.h"

/* ------------------------------------------------------------------ */
/*  Module-level 狀態 (由 DEV_ModuleInit_WithConfig 填入)              */
/* ------------------------------------------------------------------ */

static int            g_gpio_handle = -1;
static int            g_spi_handle  = -1;
DisplayConfig  g_cfg;          /* 完整設定的副本 */

/* ------------------------------------------------------------------ */
/*  內部：自動偵測 gpiochip index                                      */
/* ------------------------------------------------------------------ */

static int _detect_gpiochip(void)
{
    char buf[256];
    FILE *fp = popen("cat /proc/cpuinfo | grep 'Raspberry Pi 5'", "r");
    if (!fp) {
        fprintf(stderr, "[DEV] Cannot read /proc/cpuinfo\n");
        return 0;   /* 預設 gpiochip0 */
    }
    int is_rpi5 = (fgets(buf, sizeof(buf), fp) != NULL);
    pclose(fp);
    return is_rpi5 ? 4 : 0;
}

/* ------------------------------------------------------------------ */
/*  Module 初始化                                                      */
/* ------------------------------------------------------------------ */

int DEV_ModuleInit_WithConfig(const DisplayConfig *cfg)
{
    if (!cfg) {
        fprintf(stderr, "[DEV] NULL config\n");
        return -1;
    }
    memcpy(&g_cfg, cfg, sizeof(DisplayConfig));

    /* 1. 決定 gpiochip index */
    int chip_idx = cfg->gpio_chip.chip_index;
    if (chip_idx < 0) {
        chip_idx = _detect_gpiochip();
        fprintf(stderr, "[DEV] Auto-detected gpiochip%d\n", chip_idx);
    }

    /* 2. 開啟 GPIO chip */
    g_gpio_handle = lgGpiochipOpen(chip_idx);
    if (g_gpio_handle < 0) {
        fprintf(stderr, "[DEV] lgGpiochipOpen(%d) failed: %d\n",
                chip_idx, g_gpio_handle);
        return -2;
    }

    DEV_GPIO_Mode(cfg->pins.rst, 1);
    DEV_GPIO_Mode(cfg->pins.dc,  1);

    /* 背光預設開啟 */
    if (cfg->pins.bl >= 0) {
        DEV_GPIO_Mode(cfg->pins.bl, 1);
        DEV_Digital_Write(cfg->pins.bl, 1);
    }

    /* 4. 開啟 SPI */
    char dev_path[32];
    snprintf(dev_path, sizeof(dev_path), "/dev/spidev%d.%d", cfg->spi.bus, cfg->spi.chip);
    g_spi_handle = open(dev_path, O_RDWR);
    if (g_spi_handle < 0) {
        fprintf(stderr, "[DEV] Failed to open %s\n", dev_path);
        lgGpiochipClose(g_gpio_handle);
        g_gpio_handle = -1;
        return -3;
    }
    uint8_t mode = cfg->spi.mode;
    uint8_t bits = 8;
    uint32_t speed = cfg->spi.speed_hz;
    ioctl(g_spi_handle, SPI_IOC_WR_MODE, &mode);
    ioctl(g_spi_handle, SPI_IOC_WR_BITS_PER_WORD, &bits);
    ioctl(g_spi_handle, SPI_IOC_WR_MAX_SPEED_HZ, &speed);

    fprintf(stderr, "[DEV] Init OK — GPIO chip%d, SPI%d.%d @ %d Hz\n",
            chip_idx, cfg->spi.bus, cfg->spi.chip, cfg->spi.speed_hz);
    fprintf(stderr, "[DEV] Pins — CS=%d DC=%d RST=%d BL=%d\n",
            cfg->pins.cs, cfg->pins.dc, cfg->pins.rst, cfg->pins.bl);
    return 0;
}

void DEV_ModuleExit(void)
{
    if (g_spi_handle >= 0) {
        close(g_spi_handle);
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

void DEV_GPIO_Mode(int pin, int mode)
{
    if (pin < 0 || g_gpio_handle < 0) return;
    if (mode) {
        lgGpioClaimOutput(g_gpio_handle, 0, pin, 0);
    } else {
        lgGpioClaimInput(g_gpio_handle, 0, pin);
    }
}

void DEV_Digital_Write(int pin, int value)
{
    if (pin < 0 || g_gpio_handle < 0) return;
    lgGpioWrite(g_gpio_handle, pin, value);
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

void DEV_SPI_WriteByte(uint8_t value)
{
    if (g_spi_handle < 0) return;
    write(g_spi_handle, &value, 1);
}

void DEV_SPI_Write_nByte(const uint8_t *data, uint32_t len)
{
    if (g_spi_handle < 0 || !data || len == 0) return;
    write(g_spi_handle, data, len);
}

/* ------------------------------------------------------------------ */
/*  背光                                                               */
/* ------------------------------------------------------------------ */

void DEV_SetBacklight(int value)
{
    if (g_cfg.pins.bl < 0) return;   /* OLED 無背光 pin，忽略 */
    DEV_Digital_Write(g_cfg.pins.bl, value ? 1 : 0);
}
