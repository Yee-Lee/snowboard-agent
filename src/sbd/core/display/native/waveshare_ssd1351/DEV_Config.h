#ifndef _DEV_CONFIG_H_
#define _DEV_CONFIG_H_

#include "../include/dev_config_runtime.h"

// Define macros that the driver uses, pointing to g_cfg
#define OLED_CS_0       DEV_Digital_Write(g_cfg.pins.cs, 0)
#define OLED_CS_1       DEV_Digital_Write(g_cfg.pins.cs, 1)

#define OLED_RST_0      DEV_Digital_Write(g_cfg.pins.rst, 0)
#define OLED_RST_1      DEV_Digital_Write(g_cfg.pins.rst, 1)

#define OLED_DC_0       DEV_Digital_Write(g_cfg.pins.dc, 0)
#define OLED_DC_1       DEV_Digital_Write(g_cfg.pins.dc, 1)

// Used for delay
#define DEV_Delay_ms(x) DEV_Delay_ms(x)

#endif // _DEV_CONFIG_H_
