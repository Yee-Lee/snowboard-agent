#include <stdint.h>
#include <stdio.h>
#include "OLED_1in5_rgb.h" 
#include "DEV_Config.h" // 引入硬體控制標頭檔

#define OLED_WIDTH  128
#define OLED_HEIGHT 128
#define PY_BUFFER_SIZE (OLED_WIDTH * OLED_HEIGHT * 3) 
#define HW_BUFFER_SIZE (OLED_WIDTH * OLED_HEIGHT * 2) 

// 1. 初始化顯示器
void init_display(void) {
    // 呼叫底層 lgpio 與 SPI 腳位初始化
    if(DEV_ModuleInit() != 0) { 
        printf("GPIO/SPI Init Failed\n"); 
        return; 
    }
    
    OLED_1in5_rgb_Init();
    OLED_1in5_rgb_Clear();
}

// 2. 接收 Python 的 RGB888 (24-bit) 圖片，轉換為 RGB565 (16-bit) 並輸出
void push_frame(const uint8_t* py_buffer, int length) {
    if (length != PY_BUFFER_SIZE) {
        printf("Error: Buffer length must be %d bytes\n", PY_BUFFER_SIZE);
        return;
    }

    uint8_t hw_buffer[HW_BUFFER_SIZE];

    for(int i = 0, j = 0; i < PY_BUFFER_SIZE; i += 3, j += 2) {
        uint8_t r = py_buffer[i];
        uint8_t g = py_buffer[i+1];
        uint8_t b = py_buffer[i+2];

        uint16_t color = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);

        hw_buffer[j]     = color >> 8;
        hw_buffer[j + 1] = color & 0xFF;
    }

    OLED_1in5_rgb_Display(hw_buffer);
}

// 3. 關閉顯示器並釋放資源
void close_display(void) {
    OLED_1in5_rgb_Clear();
    DEV_ModuleExit(); // 關閉硬體資源
}
