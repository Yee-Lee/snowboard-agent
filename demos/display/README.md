# Display Architecture Demo

這是一個獨立的測試工作區，專門用來驗證與展示新的 `DisplayService` 架構 (API -> Service -> Rendering -> HAL -> Native)。

## 依賴需求

- 必須在專案根目錄下，將 `src` 加入 `PYTHONPATH` 才能執行此腳本。
- 若要執行影片測試 (`video` 或 `mow`)，系統需要安裝 `ffmpeg`。
- **硬體接線與底層驅動編譯**：若使用硬體實測，請先參考 [主系統的硬體接線與編譯指南](../../src/sbd/core/display/README.md) 來接線並編譯 `libdisplay.so`。

## 執行方式

請在專案根目錄執行以下指令：

```bash
PYTHONPATH=src python3 demos/display/demo_runner.py -p <平台代號> -s <情境> [--fps <目標幀率>]
```

### 平台代號 (`-p` / `--profile`)

我們將原本的 HAL Profile 封裝成了簡潔的代號：

| 簡寫代號 | 實際 Profile | 說明 |
| :--- | :--- | :--- |
| `mock` | `mock` | **(預設)** PC 開發用無頭模式。 |
| `oled_1.5` | `waveshare_oled_1in5_rgb` | 1.5 吋 OLED (128x128)。 |
| `lcd_2` | `waveshare_lcd_2in_rgb` | 2.0 吋 IPS LCD (320x240，全螢幕)。 |
| `lcd_128` | `waveshare_lcd_2in_rgb_128` | 2.0 吋 IPS LCD (置中限制為 128x128)。 |

### 測試情境 (`-s` / `--scenario`)

| 情境名稱 | 說明 |
| :--- | :--- |
| `starring` | **(預設)** 星空動畫，測試持續渲染與 FPS 效能。 |
| `fade` | 淡入淡出轉場，測試背景圖片讀取與透明度 (Alpha) 計算。 |
| `chat` | 雙語劇本對話，測試字型 (Pillow Text) 與排版推擠效果。 |
| `video` | 影片播放，測試非同步 ffmpeg 解碼 (`countdown.mp4`)。 |
| `mow` | 影片播放，測試 `mow.mp4` 動畫影片。 |

---

## 進階調整與效能測試 (FPS & SPI)

在新架構中，FPS 與傳輸速率分為三個獨立的層級，你可以根據測試需求自由調整：

### 1. 軟體渲染目標幀率 (Target FPS)
使用 `--fps` 參數來決定 `DisplayService` 每秒合成畫面的次數（預設 30）。
這會影響 `starring` 與 `fade` 等程式化動畫的細膩度。如果硬體跟不上這個速度，系統會自動捨棄（Drop frame）來不及送出的影格，確保動畫時間軸不拖慢。
```bash
PYTHONPATH=src python3 demos/display/demo_runner.py -p oled_1.5 -s fade --fps 60
```

### 2. 硬體傳輸極限 (SPI Clock Rate)
決定畫面送到實體面板的傳輸頻寬。預設為 `60_000_000` (60 MHz)。
透過設定環境變數 `DISPLAY_SPI_SPEED` 來降速或超頻：
```bash
DISPLAY_SPI_SPEED=30000000 PYTHONPATH=src python3 demos/display/demo_runner.py -p oled_1.5 -s fade
```

### 3. 影片解碼幀率 (Video Source FPS)
針對 `video` 測試，這取決於 `animators.py` 內 `ffmpeg` 送出的影格速度。
如果需要調整，可以直接修改 `demos/display/animators.py` 中的 `VideoAnimator` 邏輯。

---

## 自訂硬體腳位 (GPIO)

如果你的接線方式與預設的不同，**不需要改程式碼**，只要在指令前面加上環境變數即可自動套用：

```bash
DISPLAY_PIN_CS=8 DISPLAY_PIN_DC=24 PYTHONPATH=src python3 demos/display/demo_runner.py -p oled_1.5 -s chat
```

> 💡 **詳細的硬體腳位配置與對應表，請參考：[硬體接線與編譯指南](../../src/sbd/core/display/README.md)**

## 開發者筆記：如何修改字體與動畫細節

本資料夾內的所有動畫渲染實作（包含 `FadeAnimator`, `ChatAnimator`, `VideoAnimator`）都在 `animators.py` 裡面。
如果你想要：
- **修改字體大小**：請至 `animators.py` 內找到 `ChatAnimator`，修改 `ImageFont.truetype` 的大小參數（預設為 12），並相應調整 `self.line_height`。
- **更改淡入淡出圖片**：請將想要的圖片放進 `assets/` 資料夾，並在 `animators.py` 內修改路徑。
- **自訂新動畫**：只要實作帶有 `render(self, elapsed_time: float)` 方法的類別，並加上 `@register("你的動畫名")`，就能無縫與 `demo_runner.py` 接軌！
