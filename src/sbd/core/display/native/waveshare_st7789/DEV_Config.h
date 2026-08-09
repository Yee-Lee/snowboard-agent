#ifndef DEV_CONFIG_SHIM_H
#define DEV_CONFIG_SHIM_H

#include "../include/dev_config_runtime.h"

#define LCD_RST DEV_ResetPin()
#define LCD_DC  DEV_DataCommandPin()
#define LCD_BL  DEV_BacklightPin()
#define LCD_CS_0 ((void)0)
#define LCD_CS_1 ((void)0)
#define LCD_RST_0 DEV_Digital_Write(LCD_RST, 0)
#define LCD_RST_1 DEV_Digital_Write(LCD_RST, 1)
#define LCD_DC_0 DEV_Digital_Write(LCD_DC, 0)
#define LCD_DC_1 DEV_Digital_Write(LCD_DC, 1)
#define LCD_BL_0 DEV_SetBacklight(0)
#define LCD_BL_1 DEV_SetBacklight(1)

#endif
