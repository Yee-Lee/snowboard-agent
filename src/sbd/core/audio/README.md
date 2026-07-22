# 🔊 Raspberry Pi 5 I2S 音訊配置指南 (MAX98357A + INMP441)

本文件詳細說明如何在 **Raspberry Pi 5** 上，透過 I2S 介面同時連接與共用 **MAX98357A** (I2S DAC / 喇叭放大器) 與 **INMP441** (I2S 全向數位麥克風)，實現高品質的全雙工語音互動。

---

## 💡 共用時脈原理 (Clock Sharing)

I2S (Inter-IC Sound) 是一種同步序列音訊介面，主要包含以下三條核心訊號線：
1. **BCLK (Bit Clock)**：位元時脈線，由主控端 (RPi 5) 產生。
2. **LRCK / WS (Left/Right Clock / Word Select)**：聲道選擇時脈，決定當前傳輸的是左聲道還是右聲道。
3. **DATA / SD**：音訊數據線。

由於 MAX98357A (輸出) 與 INMP441 (輸入) 在系統中一個負責「播音」一個負責「錄音」，它們可以**共用相同的 BCLK 與 LRCK/WS 時脈訊號**。這樣不僅節省了樹莓派的 GPIO 腳位，還能確保錄音與播音的採樣率完全同步。

兩者唯一的差別在於**數據線是獨立的**：
- **MAX98357A (輸出)**：接收來自樹莓派的數據，連接至樹莓派的 **DOUT** (GPIO 21)。
- **INMP441 (輸入)**：傳送數據給樹莓派，連接至樹莓派的 **DIN** (GPIO 20)。

---

## 📌 實體接線對照表 (Wiring Map)

請依照下表將 **MAX98357A** 與 **INMP441** 連接至 Raspberry Pi 5 的 40-Pin GPIO：

| 訊號名稱 | MAX98357A (喇叭) 腳位 | INMP441 (麥克風) 腳位 | Raspberry Pi 5 實體引腳 (Pin #) | RPi 5 GPIO 編號 | 說明 / 備註 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **VCC (5V)** | **VIN** | - | **Pin 2 / 4** | 5V | MAX98357A 建議接 5V 驅動，音量與動態較為充足 |
| **VDD (3.3V)**| - | **VDD** | **Pin 1 / 17** | 3.3V | ⚠️ **INMP441 務必接 3.3V**，接 5V 會燒毀 |
| **GND** | **GND** | **GND** | **Pin 6 / 9 / 14 / 20 / 34** | GND | 共同接地 |
| **BCLK** | **BCLK** | **SCK / BCLK** | **Pin 12** | **GPIO 18** | **共線分接** (位元時脈) |
| **LRCK / WS** | **LRC** | **WS / LCLK** | **Pin 35** | **GPIO 19** | **共線分接** (聲道/欄位時脈) |
| **DATA OUT** | **DIN** | - | **Pin 40** | **GPIO 21** | 音訊輸出 (樹莓派發出訊號) |
| **DATA IN** | - | **SD** | **Pin 38** | **GPIO 20** | 音訊輸入 (樹莓派接收訊號) |
| **L/R Select**| - | **L/R** | - | - | 接 **GND** (設定為左聲道) |

> 💡 **接線提示：**
> * **共線分接 (Y-Split)**：你可以使用麵包板、杜邦線分接，或是直接將兩組設備的 BCLK 焊接在一起，LRCK/WS 焊接在一起，再接到樹莓派對應的 Pin 腳。
> * **L/R 腳位**：INMP441 的 `L/R` (Left/Right) 腳位決定其輸出的聲道。將其接地 (GND) 會使麥克風輸出在左聲道，這對單聲道語音識別 (ASR) 非常重要。

---

## 🛠️ 軟體配置與驅動載入

在 Raspberry Pi 5 上 (預設採用 Debian Bookworm OS)，硬體管理機制使用 `RP1` 晶片，軟體設定步驟如下：

### Step 1. 編輯設定檔
開啟終端機，編輯 `/boot/firmware/config.txt` (請注意，RPi 5 的設定檔已移至此處)：
```bash
sudo nano /boot/firmware/config.txt
```

### Step 2. 啟用 I2S 與音訊卡驅動
在檔案的最下方加入以下設定（如果原本有 `dtparam=audio=on` 建議註解掉，以避免內建 HDMI 音訊干擾預設音效卡）：

```ini
# 停用內建耳機/HDMI 音效卡 (選用，可避免卡號混淆)
# dtparam=audio=on

# 啟用樹莓派的 I2S 核心介面
dtparam=i2s=on

# 載入 Google VoiceHAT 驅動 (此驅動同時定義了 I2S 播放與錄音，完美契合此共用方案)
dtoverlay=googlevoicehat-soundcard
```

*存檔離開 (按 `Ctrl + O`、`Enter`，再按 `Ctrl + X`)*

### Step 3. 重啟系統
重啟樹莓派使設定生效：
```bash
sudo reboot
```

---

## 🔍 驗證裝置狀態

重啟完成後，請在終端機執行以下指令確認系統已成功識別驅動與音訊卡：

### 1. 檢查播放裝置 (喇叭)
```bash
aplay -l
```
輸出中若出現類似以下字樣，代表輸出驅動成功：
```text
card 0: sndrpi_googlevoicehat [snd_rpi_googlevoicehat_soundcard], device 0: Google VoiceHAT SoundCard ...
```

### 2. 檢查錄音裝置 (麥克風)
```bash
arecord -l
```
輸出中若出現相同的音效卡裝置，代表輸入驅動成功：
```text
card 0: sndrpi_googlevoicehat [snd_rpi_googlevoicehat_soundcard], device 0: Google VoiceHAT SoundCard ...
```

---

## 🧪 獨立硬體測試腳本

我們在 `hw/audio/test/` 目錄下提供了兩個現成的 Bash 測試腳本，可以用來一鍵測試實際的喇叭播放與麥克風錄音。

### 🔊 測試喇叭播放 (Output Test)
執行以下指令，系統會自動尋找 `voicehat` 或 `MAX98357A` 裝置，並播放測試語音：
```bash
chmod +x hw/audio/test/test_speaker.sh
./hw/audio/test/test_speaker.sh
```
*如果你聽到喇叭發出「Front Left」、「Front Right」的測試語音，代表喇叭硬體與接線運作完美！*

### 🎙️ 測試麥克風錄音 (Input Test)
執行以下指令，系統會錄製 5 秒鐘的音訊，並詢問你是否要立即播放。此腳本在錄音後會自動調用 Python 腳本 `amplify.py` 進行音訊的數位放大：
```bash
chmod +x hw/audio/test/test_mic.sh
./hw/audio/test/test_mic.sh [放大倍率]
```
> 💡 **範例**：若想將錄製音訊放大 1.5 倍，可執行 `./hw/audio/test/test_mic.sh 1.5`。若不指定倍率，預設為不放大（1.0 倍）。  
> ⚠️ **前置準備**：由於放大功能使用 NumPy 進行矩陣運算，執行前請確保系統已安裝 `numpy` 套件（`pip install numpy`）。

*如果錄音與重播的聲音清晰、沒有雜音，代表麥克風與喇叭的接線、設定皆正確。*

---

## ⚠️ 常見問題與排障 (Troubleshooting)

### Q1: 錄音時出現 "arecord: pcm_read:2031: read error: Input/output error" 或錄出來全是靜音/雜音？
* **格式不相容**：INMP441 是一款 24-bit 的高精準度 MEMS 麥克風，但在樹莓派上硬體驅動通常需要指定為 `S32_LE` (32-bit) 格式（實際上取樣 24-bit 填充至 32-bit 容器）。如果使用低位元的 `S16_LE` 可能會產生雜音甚至無法錄音。
* 如果遇到該問題，可修改 `test_mic.sh` 內的錄音格式為 `S32_LE`，並設定取樣率為 `48000` 或 `44100` 再次嘗試：
  ```bash
  arecord -D plughw:0,0 -d 5 -c 2 -r 48000 -f S32_LE test.wav
  ```
* **接線鬆脫**：請特別檢查 **BCLK (SCK)** 與 **LRCK (WS)** 的共用分接線路，任何一線接觸不良或接錯，都會導致 I2S 時脈同步失敗而報錯。

### Q2: 喇叭音量太小，該如何調整？
* MAX98357A 是硬體解碼放大晶片，本身沒有硬體混音器 (Hardware Mixer) 控制音量。
* 你可以使用 `alsamixer` 在終端機中將軟體音量 (Playback Volume) 調至最大，或者使用 `amixer` 命令：
  ```bash
  amixer sset 'PCM' 100%
  ```
* 在 Python 程式中，也可以透過修改 Pydub 或其他音訊庫的軟體增益 (Gain) 來放大音訊訊號。

### Q3: 聲音出現斷斷續續、卡頓或爆音？
* 建議在音訊播放與錄音指令中，使用 `plughw:X,Y` 替代 `hw:X,Y`。`plughw` 會自動在 ALSA 軟體層進行採樣率與格式轉換，相容性與穩定性更好，能有效降低因格式不符造成的爆音與抖動。
