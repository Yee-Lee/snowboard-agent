#ifndef DEV_CONFIG_SHIM_H
#define DEV_CONFIG_SHIM_H

#include "../include/dev_config_runtime.h"

#define USE_SPI 1
#define OLED_RST_0 DEV_Digital_Write(DEV_ResetPin(), 0)
#define OLED_RST_1 DEV_Digital_Write(DEV_ResetPin(), 1)
#define OLED_DC_0  DEV_Digital_Write(DEV_DataCommandPin(), 0)
#define OLED_DC_1  DEV_Digital_Write(DEV_DataCommandPin(), 1)

#endif
