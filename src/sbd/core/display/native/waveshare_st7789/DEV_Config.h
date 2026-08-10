/*****************************************************************************
* | File      	:   DEV_Config.h
* | Author      :   Waveshare team
* | Function    :   Hardware underlying interface
* | Info        :
*----------------
* |	This version:   V2.0
* | Date        :   2019-07-08
* | Info        :   Basic version
*
******************************************************************************/
#ifndef _DEV_CONFIG_H_
#define _DEV_CONFIG_H_

#include "../include/dev_config_runtime.h"
#include <stdio.h>

#define LCD_CS   g_cfg.pins.cs
#define LCD_RST  g_cfg.pins.rst
#define LCD_DC   g_cfg.pins.dc
#define LCD_BL   g_cfg.pins.bl

#define LCD_CS_0		DEV_Digital_Write(g_cfg.pins.cs, 0)
#define LCD_CS_1		DEV_Digital_Write(g_cfg.pins.cs, 1)

#define LCD_RST_0		DEV_Digital_Write(g_cfg.pins.rst, 0)
#define LCD_RST_1		DEV_Digital_Write(g_cfg.pins.rst, 1)

#define LCD_DC_0		DEV_Digital_Write(g_cfg.pins.dc, 0)
#define LCD_DC_1		DEV_Digital_Write(g_cfg.pins.dc, 1)

#define LCD_BL_0		DEV_Digital_Write(g_cfg.pins.bl, 0)
#define LCD_BL_1		DEV_Digital_Write(g_cfg.pins.bl, 1)

#define LCD_SetBacklight(Value) DEV_SetBacklight(Value)

#define DEV_Delay_ms(x) DEV_Delay_ms(x)

#endif
