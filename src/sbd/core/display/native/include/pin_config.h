/**
 * pin_config.h — Runtime-configurable GPIO/SPI pin mapping.
 *
 * 取代原本 DEV_Config.h 中硬編碼的 #define pin number。
 * 每個 driver 在 display_open() 時接收一個 PinConfig，
 * 之後所有 GPIO/SPI 操作都透過這份設定而非 compile-time 常數。
 *
 * 設計原則
 * --------
 * - PinConfig 是 plain C struct，可從 Python / JSON / 環境變數填入。
 * - 使用 -1 代表「此 pin 不存在 / 不使用」（例如沒有背光 BL pin）。
 * - SpiConfig 包含 bus/chip 與頻率，讓同一 driver 可接到不同 SPI bus。
 * - GpiochipConfig 讓 RPi 5 (gpiochip4) 與舊板 (gpiochip0) 都能處理。
 */

#ifndef DISPLAY_PIN_CONFIG_H
#define DISPLAY_PIN_CONFIG_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ------------------------------------------------------------------ */
/*  SPI 設定                                                           */
/* ------------------------------------------------------------------ */

typedef struct {
    int bus;          /* SPI bus index (通常為 0)                     */
    int chip;         /* SPI CE (chip enable) index (0 = CE0, 1 = CE1) */
    int speed_hz;     /* SPI 時脈頻率，單位 Hz (例如 60000000 = 60 MHz) */
    int mode;         /* SPI mode (0~3)；通常為 0                     */
} SpiConfig;

/* ------------------------------------------------------------------ */
/*  GPIO chip 設定                                                     */
/* ------------------------------------------------------------------ */

typedef struct {
    int chip_index;   /* lgpio gpiochip index                         */
                      /* RPi 5: 4 (gpiochip4)                         */
                      /* RPi 4 / Zero / 3: 0 (gpiochip0)              */
                      /* -1 = auto-detect (透過 /proc/cpuinfo 判斷)    */
} GpiochipConfig;

/* ------------------------------------------------------------------ */
/*  Display GPIO pin 對應                                              */
/* ------------------------------------------------------------------ */

typedef struct {
    /* --- 必要 pin --- */
    int rst;      /* 螢幕重置 (Reset / RES)  */
    int dc;       /* 資料/指令切換 (Data/Command) */
    int cs;       /* SPI Chip Select (CE)    */
                  /* 注意：lgpio SPI 通常由 SPI_Handle 管理 CS，       */
                  /*       但某些 driver 需要手動控制此 pin             */

    /* --- 選用 pin (-1 = 不使用) --- */
    int bl;       /* 背光 (Backlight)；LCD 才有，OLED 通常無此 pin    */
} DisplayPinConfig;

/* ------------------------------------------------------------------ */
/*  完整 driver 設定 (傳入 display_open)                              */
/* ------------------------------------------------------------------ */

typedef struct {
    DisplayPinConfig pins;
    SpiConfig        spi;
    GpiochipConfig   gpio_chip;
} DisplayConfig;

/* ------------------------------------------------------------------ */
/*  預設設定 (對應 README.md 的接線表)                                */
/* ------------------------------------------------------------------ */

/**
 * display_config_default_ssd1351()
 *
 * 預設接法（符合 README.md）：
 *   CS  → GPIO 8  (SPI0 CE0, Pin 24)
 *   DC  → GPIO 24 (Pin 18)
 *   RST → GPIO 25 (Pin 22)
 *   BL  → 無 (SSD1351 OLED 無背光 pin)
 *   SPI0, 60 MHz
 */
static inline DisplayConfig display_config_default_ssd1351(void)
{
    DisplayConfig cfg;
    cfg.pins.cs  = 8;
    cfg.pins.dc  = 24;
    cfg.pins.rst = 25;
    cfg.pins.bl  = -1;   /* OLED 無背光 */
    cfg.spi.bus       = 0;
    cfg.spi.chip      = 0;
    cfg.spi.speed_hz  = 60000000;
    cfg.spi.mode      = 0;
    cfg.gpio_chip.chip_index = -1;  /* auto-detect */
    return cfg;
}

/**
 * display_config_default_st7789()
 *
 * 預設接法（符合 README.md）：
 *   CS  → GPIO 8  (SPI0 CE0, Pin 24)
 *   DC  → GPIO 24 (Pin 18)
 *   RST → GPIO 25 (Pin 22)
 *   BL  → GPIO 18 (Pin 12) — LCD 背光
 *   SPI0, 60 MHz
 */
static inline DisplayConfig display_config_default_st7789(void)
{
    DisplayConfig cfg;
    cfg.pins.cs  = 8;
    cfg.pins.dc  = 24;
    cfg.pins.rst = 25;
    cfg.pins.bl  = 18;
    cfg.spi.bus       = 0;
    cfg.spi.chip      = 0;
    cfg.spi.speed_hz  = 60000000;
    cfg.spi.mode      = 0;
    cfg.gpio_chip.chip_index = -1;  /* auto-detect */
    return cfg;
}

#ifdef __cplusplus
}
#endif

#endif /* DISPLAY_PIN_CONFIG_H */
