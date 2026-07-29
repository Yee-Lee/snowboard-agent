# 顯示器驅動 (`core/display/driver`)

此目錄存放不同 SPI 顯示模組的底層 C 語言驅動程式。每個驅動都被封裝成一個共享函式庫 (`libdisplay.so`)，並提供統一的 C API 介面，供上層 Python 程式透過 `ctypes` 呼叫。

這種設計的目標是將硬體差異抽象化，讓上層應用程式 (如 `adaptor/display`) 能以相同方式與不同螢幕互動，符合 `arch.md` 中定義的硬體抽象層 (HAL) 概念。

## 前置依賴

在 Raspberry Pi 上，驅動程式依賴 `lgpio` 函式庫來進行 GPIO 和 SPI 通訊。請先確保已安裝開發套件：

```bash
sudo apt update
sudo apt install liblgpio-dev
```

## 支援的硬體

目前已整合以下驅動：

- **`waveshare_lcd_2in_rgb`**:
  - 型號: Waveshare 2-inch LCD Module
  - 解析度: 320x240
  - 控制器: ST7789V

- **`waveshare_oled_1in5_rgb`**:
  - 型號: Waveshare 1.5-inch RGB OLED Module
  - 解析度: 128x128
  - 控制器: SSD1351

## 編譯

每個驅動目錄都包含一個 `Makefile`，用於將 C 原始碼編譯成 `libdisplay.so`。

```bash
# 進入目標驅動目錄
cd src/sbd/core/display/driver/waveshare_lcd_2in_rgb

# 執行 make 進行編譯
make

# 編譯成功後，同層目錄下會產生 libdisplay.so
```

若要切換到另一個驅動，只需進入對應目錄重新編譯即可。上層應用程式會載入指定路徑的 `.so` 檔。

## 統一 C API 介面

所有驅動都透過 `display_driver.c` 實作了以下三個標準 C 函式：

- `void init_display(void)`: 初始化 GPIO 和 SPI，並傳送螢幕初始化指令序列。
- `void push_frame(const uint8_t* py_buffer, int length)`: 接收來自 Python 的影像緩衝區並將其顯示在螢幕上。
  - `py_buffer`: 指向影像資料的指標，格式為 RGB888 (每像素 3 bytes)。
  - `length`: 緩衝區的總長度。函式內部會檢查長度是否符合 `寬 * 高 * 3`。
- `void close_display(void)`: 清除螢幕並釋放 GPIO/SPI 資源。

## Python 使用方式

上層 Python 程式可使用 `ctypes` 載入編譯好的 `libdisplay.so` 並呼叫其函式。

```python
import ctypes
from PIL import Image

# 1. 載入共享函式庫
display_lib = ctypes.CDLL('./path/to/libdisplay.so')

# 2. 初始化顯示器
display_lib.init_display()

# 3. 準備影像資料 (例如使用 Pillow)
image = Image.new('RGB', (320, 240), 'blue')
raw_data = image.tobytes()

# 4. 推送影像幀
#    必須明確定義參數類型，特別是指標
display_lib.push_frame.argtypes = [ctypes.c_char_p, ctypes.c_int]
display_lib.push_frame(raw_data, len(raw_data))

# 5. 關閉顯示器
display_lib.close_display()
```

每個驅動目錄下的 `test_fade.py` 是一個完整的範例，展示了如何載入函式庫並實現動態的淡入淡出效果。

## 如何新增一個新的顯示器驅動

1.  在 `driver/` 目錄下為新硬體建立一個新目錄，例如 `my_new_lcd/`。
2.  將供應商提供的 C/H 檔案 (例如 `LCD_Driver.c`, `DEV_Config.c` 等) 放入新目錄。
3.  在新目錄中建立一個 `display_driver.c` 檔案，`#include` 供應商的標頭檔，並實作上述的 `init_display`, `push_frame`, `close_display` 三個標準函式。
    - 在 `push_frame` 中，完成從 RGB888 到目標螢幕像素格式 (如 RGB565) 的轉換。
4.  在新目錄中建立一個 `Makefile`，將所有必要的 `.c` 檔案編譯成 `libdisplay.so`。您可以參考現有驅動的 `Makefile` 作為模板。
5.  (可選) 建立一個 `test_*.py` 腳本來驗證您的驅動是否正常工作。

透過遵循此模式，系統可以輕鬆支援新的顯示硬體，而無需修改任何上層應用邏輯。

sudo apt update
sudo apt install liblgpio-dev
