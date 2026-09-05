# M3 Raspberry Pi 5 硬體驗證與測試執行手冊 (Runbook)

本手冊定義 **M3 (Raspberry Pi HAL 與硬體 Bring-up)** 階段在實體硬體上的完整接線、軟體環境配置、驅動建置與 20 個 `RPI-NATIVE` 驗收測項的執行流程。

---

## 1. 實體硬體規格與清單

| 硬體模組 | 晶片 / 型號規格 | 介面協定 | 運作參數 | 說明 |
| :--- | :--- | :--- | :--- | :--- |
| **主控板** | **Raspberry Pi 5** (4GB / 8GB) | SoC BCM2712 + RP1 | aarch64, Linux Kernel 6.12+ | 具備專用 RP1 I/O 控制器與雙 CSI 介面 |
| **音訊輸入/輸出** | **INMP441** (麥克風) + **MAX98357A** (DAC 喇叭)<br>(或 Google voiceHAT SoundCard) | I2S (`hw:0,0`) | 48 kHz / 2-ch / S32_LE (硬體)<br>16 kHz / 1-ch / S16_LE (串流) | 共享 I2S 匯流排，單一 ALSA 設備雙向串流 |
| **顯示螢幕** | **Waveshare 1.5-inch RGB OLED** (SSD1351) | 4-wire SPI (SPI0 CE0) | 128×128, RGB565 MSB-first, 4 MHz | 原生 C 驅動庫 (ABI v1)，雙緩衝 atomic flush |
| **影像相機** | **Raspberry Pi Camera Module v2** (Sony IMX219) | 22-pin CSI (Camera 0/1) | 640×480 @ 85% 品質 (JPEG / RGB / YUV) | 透過 `picamera2` / libcamera 官方子系統驅動 |
| **對話按鈕** | 實體微動開關 / 按鈕模組 | GPIO (`/dev/gpiochip0`) | BCM 23 (Pin 16), Active-Low, 50ms 防彈跳 | 短按喚醒語音 (50~1500ms)，長按關機 (≥1500ms) |

---

## 2. 完整 40-Pin GPIO 實體接線對照表

所有接線必須在**樹莓派斷電關機狀態下**完成，嚴禁帶電插拔 SPI、I2S、CSI 或 GPIO 設備。

| Physical Pin | BCM GPIO | 預設訊號名稱 | 連接設備 | 設備引腳 | 說明 |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **Pin 1** | - | **3.3V Power** | OLED 模組 | `VCC` | 3.3V 系統電源（亦可視 OLED 規格接 5V） |
| **Pin 2** | - | **5V Power** | MAX98357A | `VIN` | 5V 功放擴大機供電 |
| **Pin 6** | - | **GND** | 各模組 | `GND` | 共地接地 |
| **Pin 11** | **BCM 17** | GPIO test output | GPIO loopback | 接 Pin 13 | `M3-GPIOI-001` 專用測試輸出 |
| **Pin 12** | **BCM 18** | PCM_CLK | I2S (麥克風/DAC) | `BCLK` / `SCK` | I2S 位元時脈 (Bit Clock) |
| **Pin 13** | **BCM 27** | GPIO test input | GPIO loopback | 接 Pin 11 | `M3-GPIOI-001` 專用測試輸入；不可接電源 |
| **Pin 14** | - | **GND** | 按鈕模組 | `GND` | 按鍵接地迴路 |
| **Pin 16** | **BCM 23** | GPIO 23 | 對話按鈕 | `Signal` / `KEY` | **實體按鈕輸入** (啟用內部上拉電阻) |
| **Pin 18** | **BCM 24** | GPIO 24 | OLED 模組 | `DC` | **OLED 資料/命令切換** (Data/Command) |
| **Pin 19** | **BCM 10** | SPI0_MOSI | OLED 模組 | `DIN` / `MOSI` | **SPI 資料傳輸線** |
| **Pin 20** | - | **GND** | 各模組 | `GND` | 共地接地 |
| **Pin 22** | **BCM 25** | GPIO 25 | OLED 模組 | `RST` | **OLED 硬體重置腳** (Reset) |
| **Pin 23** | **BCM 11** | SPI0_SCLK | OLED 模組 | `CLK` / `SCK` | **SPI 時脈線** |
| **Pin 24** | **BCM 8** | SPI0_CE0_N | OLED 模組 | `CS` | **SPI 片選** (Kernel 管理，不可重複 claim) |
| **Pin 35** | **BCM 19** | PCM_FS | I2S (麥克風/DAC) | `LRC` / `WS` | I2S 左右聲道幀時脈 (Word Select) |
| **Pin 38** | **BCM 20** | PCM_DIN | INMP441 | `SD` / `DOUT` | I2S 麥克風音訊輸入 |
| **Pin 40** | **BCM 21** | PCM_DOUT | MAX98357A | `DIN` | I2S DAC 喇叭音訊輸出 |

> **相機 CSI 排線**：使用 22-pin 軟排線連接至樹莓派 5 的 `CAM/DISP 0` 或 `CAM/DISP 1` 介面，金屬接點朝向主板插槽卡扣方向，插到底後按下固定扣。

---

## 3. 軟體環境建置與依賴安裝

### 3.1 系統底層依賴
```bash
sudo apt update
sudo apt install -y python3-picamera2 libasound2-dev libgpiod-dev gpiod
```

### 3.2 建立 Python 虛擬環境
從已開啟的 Core worktree 內執行以下命令。
為確保虛擬環境能直接調用系統編譯好的 `picamera2` 與 `gpiod`，建立虛擬環境時**必須帶有 `--system-site-packages`**：

```bash
cd "$(git rev-parse --show-toplevel)"
python3 -m venv --system-site-packages .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install pytest pytest-asyncio pyyaml numpy pyalsaaudio==0.11.0 samplerate==0.2.4 pillow
.venv/bin/pip install -e .
```

### 3.3 編譯 SSD1351 OLED 原生 C 驅動庫
原生 C library (`libdisplay.so`) 必須由外部 accepted 原始碼編譯（不放入 Core Git），並確保 SHA256 與 config 一致：
```bash
# 替換為本機 accepted build 的實際路徑（僅存於本地設定）：
SBD_M3_DISPLAY_LIBRARY=/path/to/accepted-display-build/libdisplay.so
# 驗證 checksum：
sha256sum "$SBD_M3_DISPLAY_LIBRARY"
# 預期 SHA256：2dd44a17abd57a195674ddcf12717bbb2759580e81bbf194723507232ad50493
```

---

## 4. 本地端設定檔（`config.m3.local.yaml`）

於樹莓派工作目錄建立 `config.m3.local.yaml`（此檔案包含本地絕對路徑，不納入 Git 版本控制）。將下方 `/path/to/accepted-display-build/libdisplay.so` 佔位符替換為 §3.3 驗證過的 library 路徑：

```yaml
core:
  audio:
    driver: alsa
    input:
      device: hw:0,0
      native_format:
        sample_rate: 48000
        channels: 2
        sample_format: s32_le
      stream_format:
        sample_rate: 16000
        channels: 1
        sample_format: s16_le
      frame_duration_ms: 20
      channel_index: 0
      valid_bits: 24
      valid_bits_alignment: msb
      resampler: samplerate.sinc_best
    output:
      device: hw:0,0
      native_format:
        sample_rate: 48000
        channels: 2
        sample_format: s32_le
      stream_format:
        sample_rate: 48000
        channels: 2
        sample_format: s32_le
  display:
    driver: ssd1351
    profile: DSP-PROFILE-OLED-128
    width: 128
    height: 128
    pixel_format: rgb565
    rotation: 0
    byte_order: msb_first
    frame_buffer_bytes: 32768
    show_session_content: true
    native_library_path: /path/to/accepted-display-build/libdisplay.so
    native_library_sha256: 2dd44a17abd57a195674ddcf12717bbb2759580e81bbf194723507232ad50493
    native_abi_version: 1
    spi_device: /dev/spidev0.0
    spi_speed_hz: 4000000
    spi_mode: 0
    spi_chip_select: 0
    gpio_chip_index: 0
    dc_bcm: 24
    reset_bcm: 25
  camera:
    driver: picamera2
    format: RGB
    width: 640
    height: 480
    quality: 85
  gpio:
    driver: gpiod
    chip: /dev/gpiochip0
    pins:
      conversation:
        pin: 23
        active_low: true
        debounce_ms: 50
input_sources:
  button:
    policy:
      enabled: true
      required: false
    conversation_pin: conversation
    short_press_min_ms: 50
    long_press_min_ms: 1500
```

---

## 5. Junior Developer 實體重測交接（CR_M3_I）

舊 evidence 的 implementation SHA 為
`bae36dcb2684a14a129be1e90f3533451d280820`，不得沿用。以下測試只能在
CR 修正已提交、Tester 指定單一 candidate SHA 後執行。

### 5.1 Candidate 與工作樹前置檢查

```bash
cd "$(git rev-parse --show-toplevel)"
git status --short
git rev-parse HEAD
git rev-parse --abbrev-ref HEAD
```

`src/`、`tests/`、manual observation helper、`pyproject.toml`、`requirements/`
必須乾淨（含 untracked files）。將 Tester 指定的
完整 40-character SHA 設為：

```bash
export SBD_M3_CANDIDATE_SHA=REPLACE_WITH_40_CHARACTER_SHA
test "$(git rev-parse HEAD)" = "$SBD_M3_CANDIDATE_SHA"
```

runner 也會重做這些檢查；SHA 不符或受測檔案 dirty 時，card 必定 FAIL。

### 5.2 建立本次 evidence bundle

```bash
export SBD_M3_RPI_CONFIG="$(git rev-parse --show-toplevel)/config.m3.local.yaml"
export SBD_M3_EVIDENCE_DIR="$(git rev-parse --show-toplevel)/docs/outsource/evidence/DELIVERY-M3-HARDWARE-VALIDATION-001"
export SBD_M3_MANUAL_DIR="$SBD_M3_EVIDENCE_DIR/manual-current-run"
export SBD_M3_HARDWARE_MANIFEST="$SBD_M3_EVIDENCE_DIR/hardware.json"
export SBD_M3_INTERACTION_TIMEOUT_SECONDS=120
export SBD_M3_DISPLAY_OBSERVATION_SECONDS=5
export SBD_M3_GPIO_OUTPUT_PIN=17
export SBD_M3_GPIO_INPUT_PIN=27
mkdir -p "$SBD_M3_MANUAL_DIR" "$SBD_M3_EVIDENCE_DIR/logs"
cp "$SBD_M3_EVIDENCE_DIR/hardware.template.json" "$SBD_M3_HARDWARE_MANIFEST"
```

先編輯 `hardware.json`，把所有 `REPLACE_*` 改成實際 operator、Pi board
revision、周邊型號及接線。確認 BCM17（Pin 11）只以 jumper 連至 BCM27
（Pin 13）。不得把任何一端接 3.3V / 5V。

### 5.3 每張 card 的刺激與 PASS 條件

| Test ID | Junior 操作 | 程式必須斷言；任一不符即 FAIL |
| :--- | :--- | :--- |
| M3-AUDI-001 | 無人工刺激；保持音訊接線 | direct `hw:` 48k/2/S32_LE、3 個 640-byte capture frame、960-frame playback 完整消費 |
| M3-AUDI-002 | 無 | 不存在 device 經 RM 轉 NullAudioInput；audio=False；WARNING 含 device；App start/stop 完成 |
| M3-AUDI-003 | 聆聽 3 秒 440 Hz tone；在等待期間於第二 terminal 寫 checklist | 真正呼叫 `AudioOutput.play()`；audible / no_pop / no_noise 全部為 pass |
| M3-AUDI-004 | 測試期間保持安靜且不啟動其他錄音程式 | warm-up 後每 cycle 100 幀、3/3 reopen、aclose/cancel/read failure 清理、無本 process ALSA owner；記錄 raw latency / CPU / RSS / temperature / throttling |
| M3-CAMI-001 | 鏡頭前保持正常照明 | JPEG 可 decode 且尺寸符合 config |
| M3-CAMI-002 | 無須拔 CSI；card 注入 deterministic missing-CSI start failure | RM real→null、camera=False、WARNING、App 繼續 |
| M3-CAMI-003 | 鏡頭前保持正常照明 | RGB / I420 長度正確且 live sensor buffer 非全零 |
| M3-GPIOI-001 | 確認 BCM17→BCM27 jumper | 真實 output→input edge、快速反相被 debounce、unregister 後無 callback、重複 unregister no-op |
| M3-GPIOI-002 | 無 | GPIO start failure 不建立 NullGPIO；gpio=False；input.button 不啟動；WARNING；App 繼續 |
| M3-BTN-001 | 顯示 node 後短按一次 | ButtonPressed duration 合法；IDLE→WAKE→PERCEPTION；shutdown 後無 task |
| M3-BTN-002 | 測試進入 PERCEPTION 後短按一次 | 執行 interrupt 等價收斂；session / in-flight 清空並回 IDLE |
| M3-BTN-003 | 長按超過 `long_press_min_ms` 後放開 | ShutdownRequested；SM graceful stop；exit code 0 |
| M3-BTN-004 | card 進入 recovered ERROR 後短按一次 | 不經 IDLE，直接 ERROR→WAKE 並建立新 session |
| M3-BTN-005 | recovery-active 時短按一次；測試繼續等待後再短按一次 | 第一次維持 ERROR / recovery barrier；第二次進 WAKE |
| M3-DSPI-001 | 目視可選，不作 PASS 依據 | `write_main` 經 arbiter 恰一組 clear→write_pixels→show |
| M3-DSPI-002 | 依序觀察 5 秒 boot blank、IDLE「待命」、shutdown blank；第二 terminal 寫 checklist | lifecycle owner 真正執行三階段，三項人工 check 全 pass |
| M3-DSPI-003 | 無須拔線；card 使用 missing artifact | RM real→null、display=False、WARNING、主流程完成 |
| M3-DSPI-004 | 無 | 兩次 start→arbiter write_main→stop；handle / buffer / SPI/GPIO fd / thread 全釋放；重複 stop no-op |
| M3-DSPI-005 | 觀察 RGBW 四象限與向上箭頭，再觀察中文／ABC／123；第二 terminal 寫 checklist | rotation 0、無鏡像、RGB 正確、文字可讀、無明顯 flicker |
| M3-DSPI-006 | 無 | warm-up 10 次後 100 個 raw latency；每次 <1 s；記錄 P50/P95/max，不推論 FPS |

### 5.4 人工 checklist（只限三張 EV-MANUAL card）

不得事先放置 `PASS` 檔。pytest 顯示對應 card 並完成當次聲音／畫面刺激後，
在第二個 terminal 執行相應命令。若有照片／影片，透過 `--media` 記錄不含個資的
repository-relative metadata path；沒有媒體仍會寫出空 list。

```bash
.venv/bin/python scripts/record_m3_observation.py M3-AUDI-003 \
  --operator JUNIOR_NAME --output-dir "$SBD_M3_MANUAL_DIR" \
  audible=pass no_pop=pass no_noise=pass

.venv/bin/python scripts/record_m3_observation.py M3-DSPI-002 \
  --operator JUNIOR_NAME --output-dir "$SBD_M3_MANUAL_DIR" \
  boot_blank=pass idle_text_readable=pass shutdown_blank=pass

.venv/bin/python scripts/record_m3_observation.py M3-DSPI-005 \
  --operator JUNIOR_NAME --output-dir "$SBD_M3_MANUAL_DIR" \
  arrow_up=pass no_mirror=pass rgb_correct=pass text_readable=pass no_flicker=pass
```

若任何觀察不通過，必須填 `=fail`；card 會失敗，不得改寫為 PASS。

### 5.5 分組執行（保留 log 與 JUnit）

建議先刪除 `manual-current-run/M3-*.json` 的舊本次暫存檔，再逐組執行；
不要刪除 repo 內舊 evidence。每組 return code 必須為 0。

```bash
.venv/bin/python -m pytest -vv -m rpi tests/test_m3_audi_001_002_003_004_rpi.py \
  --log-file="$SBD_M3_EVIDENCE_DIR/logs/audio.log" \
  --junitxml="$SBD_M3_EVIDENCE_DIR/logs/audio.xml"

.venv/bin/python -m pytest -vv -m rpi tests/test_m3_cami_001_002_003_rpi.py \
  --log-file="$SBD_M3_EVIDENCE_DIR/logs/camera.log" \
  --junitxml="$SBD_M3_EVIDENCE_DIR/logs/camera.xml"

.venv/bin/python -m pytest -vv -m rpi tests/test_m3_gpioi_001_002_rpi.py \
  --log-file="$SBD_M3_EVIDENCE_DIR/logs/gpio.log" \
  --junitxml="$SBD_M3_EVIDENCE_DIR/logs/gpio.xml"

.venv/bin/python -m pytest -vv -m rpi tests/test_m3_btn_001_002_003_004_005_rpi.py \
  --log-file="$SBD_M3_EVIDENCE_DIR/logs/button.log" \
  --junitxml="$SBD_M3_EVIDENCE_DIR/logs/button.xml"

.venv/bin/python -m pytest -vv -m rpi tests/test_m3_dspi_001_002_003_004_005_006_rpi.py \
  --log-file="$SBD_M3_EVIDENCE_DIR/logs/display.log" \
  --junitxml="$SBD_M3_EVIDENCE_DIR/logs/display.xml"
```

按鈕若來不及依文字操作，可用 `-k test_m3_btn_00N` 單卡重跑；重跑仍必須是
同一 SHA，且 card 會以該次開始／結束時間覆寫。

---

## 6. M3 總驗收閘門與交回 Tester

完成 20 張 card 後執行：

```bash
.venv/bin/python -m pytest -vv -m "not rpi"

.venv/bin/python -m pytest -vv -m rpi \
  tests/milestones/test_m3_rpi_hal.py::test_m3_rpi_hardware_acceptance_gate \
  --log-file="$SBD_M3_EVIDENCE_DIR/logs/milestone-rpi.log" \
  --junitxml="$SBD_M3_EVIDENCE_DIR/logs/milestone-rpi.xml"
```

hardware gate 會重跑 20 張卡，並驗證每份 result 都是 `status=Pass`、同一 branch
與 `$SBD_M3_CANDIDATE_SHA`，且 20 張 Markdown card 皆存在。交回 Tester 前再檢查：

因 gate 會重新執行，三張 EV-MANUAL card 也必須在 gate 當次重新觀察並由第二個
terminal 重新執行 §5.4；前一次時間戳不會被接受。

```bash
find "$SBD_M3_EVIDENCE_DIR/cards" -name 'M3-*.md' | sort
find "$SBD_M3_EVIDENCE_DIR/results" -name 'M3-*.json' | sort
.venv/bin/python -m json.tool "$SBD_M3_EVIDENCE_DIR/manifest.json"
```

Junior Developer 只交付 raw run、cards、logs 與 observation；不得自行把 M3 標成
Accepted。Tester 必須在同一 exact SHA 獨立核對 0 Fail / 0 Blocked / 0 Skip /
0 XFail、47-ID disposition 與 evidence index，產出 repo 內 Tester sign-off 後，才交
Designer 複審 `CR_M3_I`。

---

## 7. 常見問題與排除指南 (FAQ / Troubleshooting)

1. **`Device or resource busy` (Errno 16)**：
   - 表示前一個測試尚未釋放 GPIO 或 ALSA 設備。
   - 解決方法：執行 `pkill -f pytest` 清理殘留行程。
2. **OLED 螢幕字型出現方框 `□`**：
   - 渲染器已修正 missing glyph 判斷（空白字元跳過缺失檢查），確認使用最新 `src/sbd/core/display/renderer.py`。
3. **按鍵事件無反應**：
   - 檢查接線是否在 **Physical Pin 16 (BCM 23)** 與 **GND (Pin 14/20)**。
   - 執行 `gpiodetect` 確認 chip 名稱為 `gpiochip0`。
4. **相機找不到設備**：
   - 執行 `rpicam-hello --list-cameras` 檢查是否有偵測到 `imx219`。若無，請關機重新插拔 CSI 軟排線。
