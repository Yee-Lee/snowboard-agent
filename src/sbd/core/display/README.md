# Display Subsystem & Hardware Setup

本說明文件記錄了 Display 子系統的硬體接線方式（包含本專案共用 I2S 的腳位與官方預設），以及如何編譯底層 `libdisplay.so` 驅動。

---

## 1. 如何硬體接 Pin (硬體接線指南)

為了保留硬體的彈性，我們支援兩種接線方式。您可以根據開發需求選擇其中一種。**系統預設支援動態指定 GPIO Pin**（透過環境變數設定，詳見下方說明）。

### (1) 本專案與 co-I2S 共用 Pin Out (系統預設)
為了在 Raspberry Pi 上能夠同時安裝 I2S 音訊裝置與 SPI 螢幕，我們重新規劃了 GPIO 腳位。**這是本專案程式碼的預設腳位配置**。

依照面板由左至右的接線順序 (VCC -> GND -> DIN -> CLK -> CS -> DC -> RST -> BL)，對應到 Raspberry Pi 5 的接法如下：

| 面板接線順序 (左至右) | 訊號名稱 | RPi 5 實體引腳 (Pin #) | RPi 5 GPIO (BCM) 編號 | 說明 / 備註 |
| :--- | :--- | :--- | :--- | :--- |
| **1** | VCC | **Pin 1 / 17** | 3.3V | 電源 (建議接 3.3V) |
| **2** | GND | **Pin 6 / 9 / 14...** | GND | 接地 |
| **3** | DIN / MOSI | **Pin 19** | **GPIO 10** | SPI0 MOSI |
| **4** | CLK / SCLK | **Pin 23** | **GPIO 11** | SPI0 SCLK |
| **5** | CS / CE | **Pin 24** | **GPIO 8** | SPI0 CE0 |
| **6** | DC / D/C | **Pin 18** | **GPIO 24** | Data / Command 切換 |
| **7** | RST / RES | **Pin 22** | **GPIO 25** | 螢幕 Reset |
| **8** | BL / LED | 不接 | 不接 | (LCD 專用背光。因預設腳位 18 已讓給 I2S BCLK，因此本配置**不接背光腳位**，或者您可另尋其他可用腳位並透過環境變數指定) |

---

### (2) 官方預設 Pin Out (Official Test Pinout)
如果您只有單獨測試螢幕（沒有接麥克風或喇叭），可以參考這個 WaveShare 官方預設的 SPI 腳位接法：

| 面板接線順序 (左至右) | 訊號名稱 | RPi 5 實體引腳 (Pin #) | RPi 5 GPIO (BCM) 編號 | 說明 / 備註 |
| :--- | :--- | :--- | :--- | :--- |
| **1** | VCC | **Pin 1 / 17** | 3.3V | 電源 |
| **2** | GND | **Pin 6 / 9 / 14...** | GND | 接地 |
| **3** | DIN / MOSI | **Pin 19** | **GPIO 10** | SPI0 MOSI |
| **4** | CLK / SCLK | **Pin 23** | **GPIO 11** | SPI0 SCLK |
| **5** | CS / CE | **Pin 24** | **GPIO 8** | SPI0 CE0 |
| **6** | DC / RS | **Pin 22** | **GPIO 25** | Data/Command |
| **7** | RST / RES | **Pin 13** | **GPIO 27** | Reset |
| **8** | BL / BK / LED | **Pin 12** | **GPIO 18** | 背光控制 (僅 LCD 需要，OLED不接) |

*(註：如果您使用官方預設接法，請記得在執行時透過環境變數 `DISPLAY_PIN_DC=25 DISPLAY_PIN_RST=27` 來覆寫腳位，因為我們的程式碼預設是使用上方的共用接法。)*

---

## 2. 怎麼編譯 `.so` (Native C 驅動)

底層面板驅動以 C 實作，並透過 `lgpio` 套件與實體硬體通訊。編譯完成後會產生 `libdisplay.so` 提供給 Python 層呼叫。

### 系統依賴 (前置作業)
如果您是在實機上 (例如 Raspberry Pi OS) 執行編譯，請確認已安裝 `lgpio` 標頭檔與函式庫：
```bash
sudo apt-get update
sudo apt-get install liblgpio-dev
```

### 編譯指令
專案有兩個硬體的 C 驅動，您可以進到對應目錄下執行 `make`。或是直接在 `native` 目錄層級一次全部編譯：

```bash
cd src/sbd/core/display/native

# 一鍵清理並編譯所有硬體驅動 (SSD1351, ST7789)
make clean
make
```

編譯成功後，會在各個硬體驅動的資料夾（如 `waveshare_ssd1351/` 和 `waveshare_st7789/`）內生成 `libdisplay.so`。Python HAL 層會在執行時自動尋找並載入對應的檔案。

---

## 3. 執行時動態指定 GPIO Pin (環境變數)

**系統完全支援在不修改 Python/C 程式碼的情況下，透過環境變數動態指定 GPIO Pin**。這些環境變數會覆寫掉系統的預設值，且在 Native C 層及 Python 層都會生效。

支援的環境變數如下：
- `DISPLAY_PIN_CS`: SPI 片選引腳 (BCM 編號，預設 `8`)
- `DISPLAY_PIN_DC`: 資料/指令引腳 (BCM 編號，預設 `24`)
- `DISPLAY_PIN_RST`: 重置引腳 (BCM 編號，預設 `25`)
- `DISPLAY_PIN_BL`: 背光引腳 (BCM 編號，預設 `-1` 表示不使用，LCD 官方配置常為 `18`)
- `DISPLAY_SPI_SPEED`: SPI 傳輸頻率 (預設 `60000000`)
- `DISPLAY_GPIO_CHIP`: lgpio chip 索引 (預設自動偵測，RPi 5 預設為 `4`)

### 實用範例：使用官方預設接法測試
由於專案預設腳位是給 co-I2S 使用的，如果您現在是使用「官方預設 Pin Out」來接線，您可以直接在執行程式前加上環境變數，將 DC 換成 25、RST 換成 27：

```bash
DISPLAY_PIN_DC=25 DISPLAY_PIN_RST=27 PYTHONPATH=src python3 -m pytest src/sbd/core/display/tests/test_starry_night.py -v --hardware=waveshare_oled_1in5_rgb
```
