#include <stdint.h>
#include <stdio.h>
#include "LCD_2inch.h"
#include "DEV_Config.h" // 引入硬體控制標頭檔

// 限制解析度為 128x128，以便與 OLED 比較
#define LOGICAL_WIDTH   128
#define LOGICAL_HEIGHT  128

// 將 128x128 置中於 320x240 的 LCD 螢幕上
#define OFFSET_X ((LCD_2IN_WIDTH - LOGICAL_WIDTH) / 2)
#define OFFSET_Y ((LCD_2IN_HEIGHT - LOGICAL_HEIGHT) / 2)

#define PY_BUFFER_SIZE (LOGICAL_WIDTH * LOGICAL_HEIGHT * 3) // RGB888
#define HW_BUFFER_SIZE (LOGICAL_WIDTH * LOGICAL_HEIGHT * 2) // RGB565

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

    // 設置 128x128 的寫入範圍（置中）
    LCD_2IN_SetWindow(OFFSET_X, OFFSET_Y, OFFSET_X + LOGICAL_WIDTH, OFFSET_Y + LOGICAL_HEIGHT);
    DEV_Digital_Write(LCD_DC, 1);
    
    // 批次寫入硬體緩衝區
    uint32_t total_len = HW_BUFFER_SIZE;
    uint32_t sent = 0;
    while (sent < total_len) {
        uint32_t chunk = total_len - sent;
        if (chunk > 4096) chunk = 4096;
        DEV_SPI_Write_nByte(hw_buffer + sent, chunk);
        sent += chunk;
    }
}

// 3. 關閉顯示器並釋放資源
void close_display(void) {
    LCD_2IN_Clear(0x0000); // 清屏 (黑)
    DEV_ModuleExit();       // 關閉硬體資源
}