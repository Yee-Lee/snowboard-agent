# M3 開發與硬體驗收 Runbook (m3-development.md)

本文件說明如何操作、測試與驗收 **M3（Raspberry Pi HAL 與硬體 Bring-up）**；驗收行為與 Pass gate 以 [`test_spec_M3.md`](../test_spec/test_spec_M3.md) 與 [`milestones/M3.md`](../milestones/M3.md) 為準。

---

## 1. 範圍 (Scope)

M3 涵蓋兩個驗證層次（共 47 個 Test ID）：
1. **主機開發端（Portable / DEV-PY311，27 個測項）**：
   - Strict Config 驗證與 Schema
   - Null / Mock HAL 與 Lazy Factory
   - 128×128 RGB565 Oled128Renderer（繁中字型與排版）
   - Display Arbiter / Slot 管理與原子刷新
   - Audio Option A 48k/16k 轉換與 Framing
   - Camera / GPIO / Button 的 Host Seams 與 M3 Composition
2. **樹莓派實體端（Target Hardware / RPI-NATIVE，20 個測項）**：
   - ALSA 雙向串流（48k stereo S32_LE ↔ 16k mono S16_LE）與喇叭播放
   - SSD1351 1.5 吋 OLED SPI 原生 C 驅動、雙緩衝與 full-frame latency baseline
   - Sony IMX219 CSI 相機 JPEG / RGB / YUV 擷取
   - `libgpiod` 50ms 防彈跳、GPIO 輸出、實體按鍵短按喚醒與長按關機

---

## 2. 實體硬體清單與 40-Pin GPIO 接線表

### 2.1 硬體規格清單
- **主控**：Raspberry Pi 5 (RP1 I/O Controller, 64-bit Debian 13/Bookworm)
- **音訊**：Google VoiceHAT soundcard / INMP441 (I2S MEMS 麥克風) + MAX98357A (I2S DAC 喇叭擴大機)
- **顯示**：Waveshare 1.5-inch RGB OLED (SSD1351, 128×128, 65K RGB565, 4-wire SPI)
- **相機**：Raspberry Pi Camera Module v2 (Sony IMX219, 8MP, 1080p, 22-pin CSI 軟排線)
- **按鍵**：實體按鈕開關（Conversation Button，一端接 GPIO，一端接 GND）

### 2.2 完整 40-Pin GPIO 接線表

| Physical Pin | BCM GPIO | 預設訊號名稱 | 連接設備 | 設備引腳 | 說明 |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **Pin 1** | - | **3.3V Power** | OLED 模組 | `VCC` | 3.3V 系統電源 |
| **Pin 2** | - | **5V Power** | MAX98357A | `VIN` | 5V 功放擴大機供電 |
| **Pin 6** | - | **GND** | 各模組 | `GND` | 系統共地 |
| **Pin 12** | **BCM 18** | PCM_CLK | I2S (麥克風/DAC) | `BCLK` / `SCK` | I2S 位元時脈 (Bit Clock) |
| **Pin 14** | - | **GND** | 按鈕模組 | `GND` | 按鍵接地迴路 |
| **Pin 16** | **BCM 23** | GPIO 23 | 對話按鈕 | `Signal` / `KEY` | **實體按鈕輸入** (內部上拉電阻) |
| **Pin 18** | **BCM 24** | GPIO 24 | OLED 模組 | `DC` | **OLED 資料/命令切換** (Data/Command) |
| **Pin 19** | **BCM 10** | SPI0_MOSI | OLED 模組 | `DIN` / `MOSI` | **SPI 資料傳輸線** |
| **Pin 20** | - | **GND** | 各模組 | `GND` | 系統共地 |
| **Pin 22** | **BCM 25** | GPIO 25 | OLED 模組 | `RST` | **OLED 硬體重置腳** (Reset) |
| **Pin 23** | **BCM 11** | SPI0_SCLK | OLED 模組 | `CLK` / `SCK` | **SPI 時脈線** |
| **Pin 24** | **BCM 8** | SPI0_CE0_N | OLED 模組 | `CS` | **SPI 片選** (Kernel 管理) |
| **Pin 35** | **BCM 19** | PCM_FS | I2S (麥克風/DAC) | `LRC` / `WS` | I2S 左右聲道幀時脈 (Word Select) |
| **Pin 38** | **BCM 20** | PCM_DIN | INMP441 | `SD` / `DOUT` | I2S 麥克風音訊輸入 |
| **Pin 40** | **BCM 21** | PCM_DOUT | MAX98357A | `DIN` | I2S DAC 喇叭音訊輸出 |

---

## 3. 開發與執行環境建置

### 3.1 主機端（Host / Non-RPi）
需求：Python 3.11+。
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

### 3.2 樹莓派端（Raspberry Pi 5）
從已開啟的 Core worktree 內執行以下命令。
```bash
# 1. 系統底層依賴
sudo apt update && sudo apt install -y python3-picamera2 libasound2-dev libgpiod-dev gpiod

# 2. 建立包含系統套件存取的專屬虛擬環境
cd "$(git rev-parse --show-toplevel)"
python3 -m venv --system-site-packages .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install pytest pytest-asyncio pyyaml numpy pyalsaaudio==0.11.0 samplerate==0.2.4 pillow
.venv/bin/pip install -e .
```

---

## 4. 執行驗證與測試

### 4.1 主機端單元測試（27 DEV IDs）
```bash
# 執行所有非硬體單元測試（自動 deselect 樹莓派專屬測項）
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -m 'not rpi'
```

### 4.2 樹莓派實體硬體驗收（20 RPI Cards）

實體驗收的唯一操作手冊為
[`m3_rpi_validation.md`](m3_rpi_validation.md)。該手冊包含：

- final candidate 完整 40-character SHA 與 clean worktree guard；
- BCM17→BCM27 loopback 及完整硬體接線；
- 20 張 card 的實際刺激、程式斷言與 FAIL 條件；
- current-run Audio / Display 人工 checklist，不接受預填環境變數；
- delivery bundle、logs、JUnit、checksums、media metadata 與 Tester handoff。

舊 SHA `bae36dcb2684a14a129be1e90f3533451d280820` 的 result JSON 已被
`CR_M3_I` 判定 superseded，不得複製或沿用。必須先建立包含 CR 修正的單一
candidate commit，再依實體驗收手冊重跑。

---

## 5. Exit Code 判定表

| Exit Code | 意義 | 處理指引 |
|---:|---|---|
| **0** | 正常執行 / 正常關機 | 驗證通過 |
| **2** | Config 格式或欄位型別錯誤 | 檢查 `config.m3.local.yaml` 欄位型別與路徑 |
| **3** | 硬體初始化失敗 (Startup Error) | 檢查硬體接線、權限或設備佔用 |
| **4** | 執行期嚴重錯誤 (Runtime Fatal) | 檢查底層硬體斷線或 driver panic |

---

## 6. M3 不包含 (Non-goals)

- 不包含真實雲端或本機 LLM 生成（LLM 留在 M4）
- 不包含真實本機 TTS/Piper 語音合成（留在 M4a）
- 不包含真實 MQTT Broker 連線
- 不依賴使用者雲端 Credential 或公開 API Key
