#include <stdint.h>
#include <stdio.h>
#include "LCD_2inch.h"
#include "DEV_Config.h" // 引入硬體控制標頭檔

// 根據 LCD_2inch.h 的定義調整解析度 (240 x 320)
#define LCD_WIDTH   LCD_2IN_WIDTH
#define LCD_HEIGHT  LCD_2IN_HEIGHT

#define PY_BUFFER_SIZE (LCD_WIDTH * LCD_HEIGHT * 3) // RGB888: 230,400 bytes
#define HW_BUFFER_SIZE (LCD_WIDTH * LCD_HEIGHT * 2) // RGB565: 153,600 bytes

// 1. 初始化顯示器
void init_display(void) {
    // 呼叫底層 lgpio 與 SPI 腳位初始化
    if(DEV_ModuleInit() != 0) {
        printf("GPIO/SPI Init Failed\n");
        return;
    }

    // 修正：使用 2 吋 LCD 驅動 API
    LCD_2IN_Init();
    LCD_2IN_Clear(0x0000); // 或是 0x0000 (BLACK) / 0xFFFF (WHITE)
}

// 2. 接收 Python 的 RGB888 (24-bit) 圖片，轉換為 RGB565 (16-bit) 並輸出
void push_frame(const uint8_t* py_buffer, int length) {
    if (length != PY_BUFFER_SIZE) {
        printf("Error: Buffer length must be %d bytes (got %d)\n", PY_BUFFER_SIZE, length);
        return;
    }

    uint8_t hw_buffer[HW_BUFFER_SIZE];

    // RGB888 -> RGB565 轉碼 (Big-Endian 輸出)
    for(int i = 0, j = 0; i < PY_BUFFER_SIZE; i += 3, j += 2) {
        uint8_t r = py_buffer[i];
        uint8_t g = py_buffer[i+1];
        uint8_t b = py_buffer[i+2];

        uint16_t color = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);

        hw_buffer[j]     = (color >> 8) & 0xFF; // MSB
        hw_buffer[j + 1] = color & 0xFF;        // LSB
    }

    // 修正：使用 2 吋 LCD 刷頁面函式
    LCD_2IN_Display(hw_buffer);
}

// 3. 關閉顯示器並釋放資源
void close_display(void) {
    LCD_2IN_Clear(0x0000); // 清屏 (黑)
    DEV_ModuleExit();       // 關閉硬體資源
}
