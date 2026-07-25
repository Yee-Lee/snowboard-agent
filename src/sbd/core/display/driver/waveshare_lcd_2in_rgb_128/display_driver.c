#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "LCD_2inch.h"
#include "DEV_Config.h" // 引入硬體控制標頭檔

// 限制解析度為 128x128，以便與 OLED 比較
#define LOGICAL_WIDTH   128
#define LOGICAL_HEIGHT  128

// 為了讓實體尺寸與 1.5 吋 OLED 相近，我們將 128x128 放大
// 1.5 吋 OLED (128x128) 的像素密度約為 120 PPI，2 吋 LCD (320x240) 約為 200 PPI
// 128 * (200 / 120) = 213.3，我們取 212 方便置中
#define SCALED_WIDTH    212
#define SCALED_HEIGHT   212

// 實際螢幕大小
#define FULL_WIDTH   LCD_2IN_WIDTH
#define FULL_HEIGHT  LCD_2IN_HEIGHT

// 將 SCALED_WIDTH x SCALED_HEIGHT 置中於 320x240 的 LCD 螢幕上
#define OFFSET_X ((FULL_WIDTH - SCALED_WIDTH) / 2)
#define OFFSET_Y ((FULL_HEIGHT - SCALED_HEIGHT) / 2)

#define PY_BUFFER_SIZE (LOGICAL_WIDTH * LOGICAL_HEIGHT * 3) // RGB888
#define FULL_HW_BUFFER_SIZE (FULL_WIDTH * FULL_HEIGHT * 2) // RGB565

// 宣告一個全域緩衝區以存放 320x240 的完整畫面
static uint8_t full_hw_buffer[FULL_HW_BUFFER_SIZE];
static int frame_count = 0;

// 1. 初始化顯示器
void init_display(void) {
    // 呼叫底層 lgpio 與 SPI 腳位初始化
    if(DEV_ModuleInit() != 0) {
        printf("GPIO/SPI Init Failed\n");
        return;
    }

    // 修正：使用 2 吋 LCD 驅動 API
    LCD_2IN_Init();
    LCD_2IN_Clear(0x0000); // 清屏 (黑)
    
    // 將內部緩衝區初始化為黑色 (0x0000)
    memset(full_hw_buffer, 0, FULL_HW_BUFFER_SIZE);
}

// 2. 接收 Python 的 RGB888 (24-bit) 圖片，轉換為 RGB565 (16-bit) 並輸出
void push_frame(const uint8_t* py_buffer, int length) {
    frame_count++;

    if (length != PY_BUFFER_SIZE) {
        printf("Error: Buffer length must be %d bytes (got %d)\n", PY_BUFFER_SIZE, length);
        return;
    }

    // 使用最近鄰插值 (Nearest Neighbor) 將 128x128 放大到 212x212
    // 並填入 320x240 緩衝區的正中央
    for (int y = 0; y < SCALED_HEIGHT; y++) {
        int src_y = y * LOGICAL_HEIGHT / SCALED_HEIGHT;
        int full_y = OFFSET_Y + y;
        
        for (int x = 0; x < SCALED_WIDTH; x++) {
            int src_x = x * LOGICAL_WIDTH / SCALED_WIDTH;
            int py_idx = (src_y * LOGICAL_WIDTH + src_x) * 3;
            
            uint8_t r = py_buffer[py_idx];
            uint8_t g = py_buffer[py_idx+1];
            uint8_t b = py_buffer[py_idx+2];

            uint16_t color = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);

            int hw_idx = (full_y * FULL_WIDTH + OFFSET_X + x) * 2;
            full_hw_buffer[hw_idx] = (color >> 8) & 0xFF; // MSB
            full_hw_buffer[hw_idx+1] = color & 0xFF;      // LSB
        }
    }

    // 使用原廠函式進行全螢幕刷新，確保控制器行為正確
    LCD_2IN_Display(full_hw_buffer);
}

// 3. 關閉顯示器並釋放資源
void close_display(void) {
    LCD_2IN_Clear(0x0000); // 清屏 (黑)
    DEV_ModuleExit();       // 關閉硬體資源
}