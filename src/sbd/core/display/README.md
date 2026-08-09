# Raspberry Pi 5 GPIO Pinout Setup

本說明文件記錄了在 Raspberry Pi 5 上同時安裝 **I2S 音訊裝置（喇叭與麥克風）** 及 **7-Pin OLED 顯示器 (SPI)** 的 GPIO 腳位規劃與接線指南。

---

## 📌 GPIO 腳位總表 (Pinout Summary)

| 訊號類別 | 訊號名稱 | MAX98357A (喇叭) | INMP441 (麥克風) | OLED (SPI) 腳位 | RPi 5 實體引腳 (Pin #) | RPi 5 GPIO 編號 | 說明 / 備註 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **電源** | VCC (5V) | VIN | - | - | **Pin 2 / 4** | 5V | MAX98357A 建議接 5V 驅動，音量與動態較充足 |
| **電源** | VDD (3.3V) | - | VDD | VCC | **Pin 1 / 17** | 3.3V | ⚠️ INMP441 務必接 3.3V；OLED 建議接 3.3V |
| **接地** | GND | GND | GND | GND | **Pin 6 / 9 / 14 / 20 / 34** | GND | 所有裝置共同接地 |
| **I2S** | BCLK | BCLK | SCK / BCLK | - | **Pin 12** | **GPIO 18** | I2S 位元時脈 (共線分接) |
| **I2S** | LRCK / WS | LRC | WS / LCLK | - | **Pin 35** | **GPIO 19** | I2S 聲道時脈 (共線分接) |
| **I2S** | DATA OUT | DIN | - | - | **Pin 40** | **GPIO 21** | 音訊輸出 (樹莓派發出) |
| **I2S** | DATA IN | - | SD | - | **Pin 38** | **GPIO 20** | 音訊輸入 (樹莓派接收) |
| **I2S** | L/R Select | - | L/R | - | - | - | INMP441 的 L/R 腳位請直接接地 GND (設定為左聲道) |
| **SPI** | D0 / SCL | - | - | D0 / SCL / SCK | **Pin 23** | **GPIO 11** | SPI0 SCLK (時脈線) |
| **SPI** | D1 / SDA | - | - | D1 / SDA / MOSI | **Pin 19** | **GPIO 10** | SPI0 MOSI (資料發送線) |
| **SPI** | CS / SS | - | - | CS / SS | **Pin 24** | **GPIO 8** | SPI0 CE0 (晶片選擇) |
| **GPIO** | DC / D/C | - | - | DC / D/C | **Pin 22** | **GPIO 25** | 資料 / 指令切換 (Data/Command) |
| **GPIO** | RES / RST | - | - | RES / RST | **Pin 13** | **GPIO 27** | 螢幕重置 (Reset) |

---

## 🛠️ 樹莓派系統設定

### 1. 啟用 SPI 介面
執行以下命令開啟樹莓派設定選單：
```bash
sudo raspi-config
```
1. 進入 `Interface Options` -> `SPI`
2. 選擇 `Yes` 啟用 SPI 介面
3. 儲存後重新啟動樹莓派：
   ```bash
   sudo reboot
   ```

---

## 🐍 Python OLED 測試腳本範例 (luma.oled)

### 1. 安裝必要套件
```bash
pip install luma.oled
```

### 2. 測試程式碼 (`test_oled.py`)
```python
from luma.core.interface.serial import spi
from luma.oled.device import ssd1306  # 若使用 SH1106 請替換為 sh1106
from luma.core.render import canvas

# 初始化 SPI 介面 (port=0, device=0 對應 GPIO 8 / CE0)
# gpio_DC=25 對應 GPIO 25 (Pin 22), gpio_RST=27 對應 GPIO 27 (Pin 13)
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=27)

# 初始化 128x64 OLED 顯示器
device = ssd1306(serial, width=128, height=64)

# 繪製測試畫面
with canvas(device) as draw:
    draw.rectangle(device.bounding_box, outline="white", fill="black")
    draw.text((10, 25), "RPi 5 OLED OK!", fill="white")

input("按 Enter 鍵結束測試...")
```

---

## 🧪 Official Test 腳位配置 (Official Test Pinout)

以下為 Official Test 所使用的 OLED/LCD SPI 接法配置：

| 訊號名稱 | OLED / LCD 腳位 | RPi 實體引腳 (Pin #) | 說明 / 備註 |
| :--- | :--- | :--- | :--- |
| **VCC** | VCC | **Pin 1** | 3.3V 電源 |
| **GND** | GND | **Pin 6** | 接地 |
| **DIN** | DIN / MOSI / SDA | **Pin 19** | SPI0 MOSI (GPIO 10) |
| **CLK** | CLK / SCLK / SCK | **Pin 23** | SPI0 SCLK (GPIO 11) |
| **CS** | CS / CE | **Pin 24** | SPI0 CE0 (GPIO 8) |
| **DC** | DC / RS | **Pin 22** | GPIO 25 (Data/Command) |
| **RST** | RES / RST | **Pin 13** | GPIO 27 (Reset) |
| **BL** | BL / BK / LED | **Pin 12** | GPIO 18 (背光控制，僅 LCD 需要) |

---

## 🛠️ Display 子系統的編譯、測試與除錯方法

本專案將 Display 子系統重構為符合現代架構的設計，分層為 `API` -> `Service` -> `Rendering` -> `HAL` -> `Native`。以下是相關的編譯、測試與除錯指南。

### 1. 編譯 Native C 驅動 (Compilation)

底層面板驅動以 C 實作，利用 `lgpio` 套件與實體硬體通訊，並包裝為穩定的 C ABI `libdisplay.so`。

#### 編譯 SSD1351 (1.5 吋 OLED)
```bash
cd src/sbd/core/display/native/waveshare_ssd1351
make clean && make
```

#### 編譯 ST7789 (2 吋 LCD)
```bash
cd src/sbd/core/display/native/waveshare_st7789
make clean && make
```
編譯成功後，會在各自目錄生成 `libdisplay.so`。Python HAL 層會自動尋找此檔案載入。

---

### 2. 測試方法 (Testing)

測試已區分為不需要硬體參與的**模擬單元測試**與需要實體面板的**硬體整合測試**。

#### A. 模擬單元測試 (CI / 無實體硬體)
驗證 Deterministic 星空渲染與排程 Policy。這是不需要實體面板的 Pure Python 測試：
```bash
# 設定 PYTHONPATH 指向 src 目錄
export PYTHONPATH=src

# 執行星空渲染與 Policy 單元測試
python3 -m pytest src/sbd/core/display/tests/test_renderer_starry.py src/sbd/core/display/tests/test_service_policy.py -v
```

#### B. API 端到端測試 (可在 PC 模擬或實機上執行)
```bash
# 1. PC 模擬模式 (預設，使用 Mock Display)
PYTHONPATH=src python3 -m pytest src/sbd/core/display/tests/test_starry_night.py -v

# 2. 樹莓派實機測試 (使用實體 OLED 顯示)
PYTHONPATH=src python3 -m pytest src/sbd/core/display/tests/test_starry_night.py -v --hardware=waveshare_oled_1in5_rgb
```

#### C. 硬體獨立診斷測試 (Diagnostics)
當畫面異常時，可用於直接對 HAL/Native 層灌入測試幀（紅、黑、漸層色），繞過 Service 大腦：
```bash
# OLED 實機診斷
PYTHONPATH=src python3 -m pytest \
  src/sbd/core/display/tests/integration/test_ssd1351_present.py \
  --display-config poc_display/evidence/<delivery-id>/<run-id>/config.json \
  -m pi_only -v

# LCD 實機診斷
PYTHONPATH=src python3 -m pytest \
  src/sbd/core/display/tests/integration/test_st7789_present.py \
  --display-config <recorded-st7789-config.json> -m pi_only -v
```

---

### 3. 配置與除錯 (Configuration & Debugging)

#### 執行時 Pin 腳位配置 (Runtime Pin Mapping)
實體 fixture 必須從一份已保存並計算 SHA-256 的 local JSON config 載入，不使用環境變數或 source defaults 注入 deployment pins。Schema 與 sanitized example 位於 `poc_display/config/`。執行前需把 example 複製到 evidence run 目錄，填入 panel revision 與解析後的整數 `gpio.chip`。

##### 💡 實用除錯命令範例
使用記錄過的 config 執行診斷：
```bash
PYTHONPATH=src python3 -m pytest \
  src/sbd/core/display/tests/integration/test_ssd1351_present.py \
  --display-config poc_display/evidence/<delivery-id>/<run-id>/config.json \
  -m pi_only -v -s
```

#### 影格延遲與丟幀除錯 (Frame-Drop Debugging)
`RenderScheduler` 內建 `latest-frame-wins` 丟幀機制。如果實體面板刷新速率（例如 SPI 瓶頸）慢於目標 FPS：
- 渲染線程會繼續繪製最新時間點的畫面。
- I/O 發送線程會自動丟棄未被消耗的「舊影格」，只傳送「最新影格」至硬體。
- 這可有效防止動畫滯後、累積延遲的現象。如需監控，可將 `logging` 層級設定為 `DEBUG`，查看系統輸出中 `[MockDisplay]` 或 `[CtypesDisplay]` 的實時畫面更新狀況。
