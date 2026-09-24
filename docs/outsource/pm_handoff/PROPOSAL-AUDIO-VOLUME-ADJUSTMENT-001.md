# PROPOSAL-AUDIO-VOLUME-ADJUSTMENT-001: Audio Output 軟體音量調整機制提案

- **ID**: `PROPOSAL-AUDIO-VOLUME-ADJUSTMENT-001`
- **Owner**: Audio / Product / Designer
- **Status**: Accepted into M4C design with reduced scope / 2026-09-16
- **Target Component**: `core/audio`, `adjustments/volume`, `core/config`, `core/display`
- **Date**: 2026-09-14

---

## 0. Core disposition

USER與Designer採納startup-static software output volume進M4C，但不採納本提案原始三階段作為
本輪交付。現行authority是`docs/milestones/M4C.md`、`docs/implement/ch02a_core_hal.md`與
`docs/implement/ch10_config.md`；本文件保留input provenance，不覆蓋它們。

採納範圍：

- M4C composition建立單一`VolumeControlledAudioOutput` decorator；既有`AudioOutput` Protocol、
  raw factory、ALSA direct `hw:` negotiation、Speak與format adapter契約不變。
- `AudioOutputConfig.volume_percent`為startup-static非bool integer `0..100`；schema default `100`，
  M4C real product config明確固定`25`。
- decorator提供獨立`VolumeControl` port作未來注入點；本輪沒有runtime caller。
- scaling沿用M4B quarter-gain已驗證的sign-preserving truncation toward zero，不採原提案對負值
  不對稱的`floor`公式。

延後範圍：GPIO音量鍵、Display `volume` slot更新、OSD、runtime config reload、持久化與獨立
mute state。原提案的`default_volume=50`、擴充`AudioOutput` Protocol及把scaling直接放進ALSA／
format adapter均被此disposition取代。完整M4C design與Test Spec完成前不開Developer entry。

---

## 1. 背景與問題陳述 (Background & Problem Statement)

1. **硬體限制（MAX98357A 無硬體 Mixer）**：
   - 目前系統的音訊輸出端使用 **MAX98357A**（I2S DAC / Class D 擴大機，參見 `docs/runbooks/m3-development.md`）。
   - MAX98357A 是純 I2S 晶片，沒有 I2C/SPI 等控制匯流排。Linux ALSA 驅動無法為其提供硬體音量暫存器控制（無 Hardware Mixer / Master 控制項）。
2. **Direct `hw:0,0` 規範**：
   - 專案在設定檔（如 `config.example.yaml` 與 `docs/runbooks/m3_rpi_validation.md`）及測試規範中，明確要求使用 `device: hw:0,0` 直連底層 ALSA 裝置。
   - 直連 `hw:` 會繞過 ALSA 使用者空間的 `softvol` 等外掛，導致在 Raspberry Pi 上執行 `amixer` 或 `alsamixer` 時無法調整音量（報錯找不到 Master 控制項）。
3. **現行輸出問題**：
   - 在 5V 功放供電與 3W/5W 喇叭規格下，未加衰減的 100% 輸出會造成聲音過大與爆音。
   - 先前在上機驗證腳本 `scripts/run-m4b-pv.py` 中，為解決此問題而特別實作了臨時的 `_QuarterVolumeAudioOutput`，在記憶體中將 PCM sample 直接除以 4（25% 音量）。
4. **現行架構現況**：
   - `src/sbd/core/audio/base.py` 的 `AudioOutput` Protocol 僅有 `start()`, `stop()`, `play()`，缺少音量相關 API。
   - `src/sbd/` 尚未建立架構文件預留的 `adjustments/` 模組。

---

## 2. 目標 (Objectives)

1. **零硬體依賴之軟體音量控制（Software PCM Scaling）**：
   在不依賴 ALSA mixer 與硬體暫存器的前提下，於軟體層對 PCM 採樣點進行數位縮放，相容現行 direct `hw:0,0` 規範。
2. **對齊系統架構規範**：
   - 依據 `docs/arch.md` §2.5 與 §5.4，將音量實體鍵納入 `adjustments/volume`，不進 State Machine (SM)，直控 `core/audio`。
   - 依據 `docs/implement/ch08_display_arbiter.md` §6，將音量數值回饋至 Display Arbiter 的 `volume` slot。
3. **配置化支援**：
   在 `AudioConfig` 中支援預設音量（`default_volume`）與靜音設定。

---

## 3. 分階段落地方案 (Phased Implementation Plan)

### 階段一：Core Audio HAL 軟體音量與 Config 支援（Minimal Viable Delta）

這是最核心且優先級最高的部分，能立即解決「系統無法調音量」的問題。

1. **更新 `AudioConfig` (`src/sbd/core/config/models.py`)**：
   - 在 `AudioOutputConfig` 加入音量欄位：
     ```python
     default_volume: int = 50  # 0 ~ 100 百分比，預設 50%
     ```
2. **擴充 `AudioOutput` Protocol (`src/sbd/core/audio/base.py`)**：
   - 增加音量查詢與設定介面：
     ```python
     @runtime_checkable
     class AudioOutput(Protocol):
         async def start(self) -> None: ...
         async def stop(self) -> None: ...
         async def play(self, pcm: AsyncIterator[bytes]) -> None: ...
         def set_volume(self, volume: int) -> None: ...  # 0 ~ 100
         def get_volume(self) -> int: ...
     ```
3. **實作 `AlsaAudioOutput` 數位縮放 (`src/sbd/core/audio/alsa/output.py`)**：
   - 在播放串流轉換時（或直接在 `StreamFormatAdapter`），套用音量比例乘數。
   - 支援 0% 至 100% 的 sample 縮放（注意防範數值溢位與 clipping，可採軟體乘除或查表）：
     $$\text{sample}_{\text{out}} = \text{clamp}\left(\left\lfloor \text{sample}_{\text{in}} \times \frac{\text{volume}}{100} \right\rfloor, -32768, 32767\right)$$
4. **Mock 與單元測試補齊**：
   - 在 `src/sbd/core/audio/mock/` 與 `tests/` 補齊 `set_volume` / `get_volume` 驗證與邊界測試（0%, 100%, 負值/超標 exception）。

---

### 階段二：Display Arbiter 狀態聯動（Feedback & Visibility）

1. **對接既有 `volume` Slot**：
   - `DisplayArbiter` 已經預留了 `"volume"` slot（`docs/implement/ch08_display_arbiter.md`）。
   - 建立 volume state observer，當音量被變更時，呼叫 `arbiter.write_status_slot("volume", f"V:{vol}%")`。
2. **開機狀態初始化**：
   - 系統啟動時以 `default_volume` 初始化 slot 顯示。

---

### 階段三：GPIO 實體按鈕直控 (`adjustments/volume`)

1. **建立 `src/sbd/adjustments/volume.py`**：
   - 訂閱 `core/gpio` 的特定 pin 事件（例如 Volume Up / Volume Down 按鈕）。
   - 短按（如 +5% / -5%）與長按（快速連續步進），直接呼叫 `audio_output.set_volume(...)`。
   - 嚴格遵守 `docs/arch.md` §2.5 原則：**完全不發送 Signal 給 State Machine**，不影響語音對話流程。
2. **OSD Overlay 評估（可選 / 未來定案）**：
   - 依 `docs/arch.md` §8.1 評估是否引入按鍵觸發的短暫覆蓋音量條（OSD）。

---

## 4. 技術細節與影響評估 (Technical Impact & Considerations)

1. **CPU 耗損評估**：
   - 在 Raspberry Pi 5（四核心 Cortex-A76）上，對 16 kHz mono 或 48 kHz stereo 的 20ms chunk 做簡單數值縮放，耗時在微秒級（< 0.05ms），對即時音訊延遲與 CPU 負載影響極低。
2. **架構無破壞性（Zero Breaking Change to Native Negotiation）**：
   - 依然使用 direct `hw:0,0`，不需改用 ALSA dmix/softvol 虛擬驅動，完全保證現有 M3/M4 硬體資格驗證（HW qualification）與低延遲優勢。
3. **音量曲線（Volume Curve）**：
   - 初版可採線性縮放（Linear scaling）。
   - 若人耳聽感在低音量區間變化不顯著，後續可平滑升級為對數 / 感知聽覺曲線（Logarithmic/Perceptual curve: $y = x^2$ 或 dB 對數表）。

---

## 5. 待裁決事項 (Decisions Requested)

1. **切入時機**：
   - 是否將「階段一（Core Audio 軟體音量 + Config）」作為近期 M4 交付或專屬 Work Package (WP) 納入實作？
2. **預設音量值裁定**：
   - 是否以 `default_volume = 50` 作為標準預設值？
3. **是否需要音量持久化（Volume Persistence）**：
   - 初版音量是否僅需記憶於記憶體內（重開機回到 `default_volume`），或需落盤至 local state / storage？
