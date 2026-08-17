# Ch 2a. core HAL Protocol

屬於 `implement.md` 索引 | 對應 `arch.md` §2.3 | 狀態：定稿（IR-final 已通過（2026-08-01）；M3 Audio Option A 語意已接受，實體技術選型待 POC 驗證）

本章定義 `arch.md` §2.3「硬體 HAL」的具體 Protocol 契約—— `core/audio`、`core/display` 底層、`core/camera`、`core/gpio`。所有 HAL 遵守 §2a.1 統一契約；各 HAL 的工作方法（ `frames()` / `capture()` / `register_input()` 等）於各自節次定義。

範圍邊界
- 本章包含：四個 HAL 的 Protocol 方法簽名、資料格式（PCM frame、pixel buffer、image bytes）、Null Object 適用性、Factory 模式
- 不含：
  - `core/display` 仲裁層：Ch 8 (Display 仲裁層協定) ——本章只寫 HAL 底層原語
  - `core/leds` : Ch 2a 略過—— `arch.md` §8.1 標記 LED 表達機制尚未定案； `core/leds/` 目錄暫不落地，見 `../reviews/history/arch_review_implement.md` AR-Impl-4
  - 軟體基礎設施（ `config/` / `logger.py` / `event_bus/` / `state_manager/` ）：由 Ch 3 / Ch 4 / Ch 10 / Ch 11 分別處理
  - Cognition 相關 core：無 HAL—— LiteRT-LM engine adapter 屬 Ch 2b worker 內部 library adapter，不進 `core/`

---

## 2a.1 HAL 統一契約

### Lifecycle 三方法

所有 HAL Protocol 皆宣告 `async def start()` / `async def stop()` 兩方法，語意同 Ch 2 §2.1 lifecycle 定義：

- `start()` : Resource Manager 於啟動階段呼叫；return 時硬體 handle 已就緒。失敗 raise exception；RM 依 §2a.1 Null Object 適用性決定是否改注入 null impl
- `stop()` : RM 於停機階段反向呼叫；return 時硬體 handle 已釋放。要求冪等
- 無 `abort` : HAL 不進 SM in-flight 集合、無「中止當前工作」概念。HAL 若正在服務 in-flight worker，被 `abort` 的是 worker 而非 HAL；worker 的 `abort` 內部負責釋放向 HAL 借用的短期資源（例：關閉 ASR session、釋放獨佔的錄音串流）

與 Ch 2 worker Protocol 的對齊：RM 對「所有可管理資源」（HAL 與 worker）呼叫同名方法，無需分辨類別。舊版 `close()` 命名不採用。

### 工作方法

各 HAL 於 lifecycle 之外宣告自己的工作方法（例：audio 的 `frames()` / `play()` 、display 的 `write_pixels()` 、camera 的 `capture()` 、gpio 的 `register_input()` ）。工作方法簽名依 HAL 本質決定，無統一形式。

### Null Object 適用性

依 `arch.md` §6.8 A，HAL 是否提供 null 實作依「啟動失敗風險」與「上層契約簡化收益」判定：

| HAL | Null 實作 | 判定理由 |
| --- | --- | --- |
| `core/audio` | ✅ 必要 | ALSA 裝置找不到 / PortAudio init 失敗屬正常故障情境；null 讓 listen / speak worker 拿到不會爆的物件，經 P5 降級產出可用 fact |
| `core/display` | ✅ 必要 | SPI init 失敗、驅動 .so 未編譯屬正常故障；null 讓仲裁層與 Presenter/StatusBar 呼叫不爆 |
| `core/camera` | ✅ 必要 | CSI init 失敗屬正常故障；null 讓 look worker 呼叫 `capture()` 後 return `PerceptionResult(status="error")`，session 不中斷 |
| `core/gpio` | ❌ 不提供 | GPIO 為登錄式介面（ `register_input(pin, callback)` ），null 版即「註冊後永不觸發」——等同物理上沒接線的行為，不需獨立類別。register 失敗直接由 RM 記 `capability_of("gpio")=False`，下游 input_events 依此不啟動 |

規範：「有實體硬體初始化風險且下游有多個消費者」的 HAL 必須提供 null 子目錄；純登錄型 HAL 可省略。此原則供未來新 HAL 判定用。

### Null 實作契約

Null 實作與 real 實作共享同一 Protocol；差異僅在行為：
- Lifecycle： `start()` / `stop()` 為 no-op（不 raise、不做事）
- 工作方法：以「最無害的格式合法的可 return 值」實現—— `frames()` 產出無限 frame（或依 config timeout 後 return）、 `capture()` return 符合 config format 的合法 blank image（見 §2a.4，JPEG 須為合法 encoded bytes，非全零）、 `write_pixels()` no-op
- 不 raise `NotImplementedError` ：上層拿到 null 不區分 real / null，raise 會破壞 Null Object 語意
- Log 標記：null 實作於 `start()` 時 log info 一次，告知運行於 null 模式；後續工作方法呼叫不 log（避免灌爆 log）

### Factory 模式

每個 HAL 目錄的 `__init__.py` 提供 factory function，依 config 決定 backend：

```python
# 範例：core/audio/__init__.py
from sbd.core.audio.base import AudioInput, AudioOutput

def make_audio_input(cfg) -> AudioInput:
    if cfg.driver == "null":
        from sbd.core.audio.null.input import NullAudioInput
        return NullAudioInput()
    if cfg.driver == "mock":
        from sbd.core.audio.mock.input import MockAudioInput
        return MockAudioInput(cfg.mock_wav_path)
    if cfg.driver == "alsa":
        from sbd.core.audio.alsa.input import AlsaAudioInput
        return AlsaAudioInput(...)
    raise ValueError(f"unknown audio driver: {cfg.driver}")
```

- Lazy import：只在被選中時才 import backend；開發機不裝 `sounddevice` 也能跑（走 mock 或 null）
- null 為顯式 driver 選項：config 可主動選 null（例：測試 headless、缺硬體開發機）；RM 的「real 失敗改用 null」是另一條路徑（RM 主動 fallback）
- mock 與 null 分開：mock 有可控輸入輸出（讀 WAV / 寫 WAV），供開發機與整合測試；null 是絕對無害的 stub，供硬體缺席時的 P5 降級

M3 Display factory 的 real key 固定為 `ssd1351`。Composition root 必須先讓 Ch 10 完成 selected profile、artifact checksum、ABI、SPI、GPIO、rotation、byte order 與 frame-buffer cross validation，才呼叫 factory；factory 只有在 `ssd1351` 分支可 import `sbd.core.display.ssd1351.driver` 或載入 native library。`mock` / `null` 分支不得 probe artifact 或 import native code。SSD1351 adapter 只接收已驗證 config，並在任何 GPIO / SPI claim 前驗 ABI v1 / struct size；失敗交由既有 RM real→null 流程處理。

這個 mapping 屬 chip-specific factory / backend 邊界。共用 `DisplayDevice`、Renderer、Arbiter 與 Resource Manager 不得判斷 SSD1351 pin、SPI 或 ABI 欄位。

### Factory 失敗與 RM Fallback

Resource Manager 建立階段（ `arch.md` §6.1 職責 1 / 3 ）：
1. 呼叫 factory 建立 real 實作 instance
2. 呼叫 `await instance.start()`
3. 若 step 1 / 2 raise exception → RM 改呼叫 factory 建立 null 實作、再 start；記 `capability_map[kind]=False`、log warning
4. 若 null 實作 start 亦失敗 → log fatal、中止啟動（等同 `arch.md` §6.2 啟動失敗）

實作細節（fallback 演算法、 `capability_map` 資料結構）屬 Ch 5 Resource Manager。本節僅規範 HAL 契約要「支援」此 fallback 機制。

---

## 2a.2 core/audio

職責（ `arch.md` §2.3 / §5.2 ）：麥克風串流輸入、喇叭 PCM 輸出；VAD / 段落切割 / ASR 均不在此。

### Protocol 定義

```python
# src/sbd/core/audio/base.py
from typing import AsyncIterator, Protocol

class AudioInput(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    def frames(self) -> AsyncIterator[bytes]:
        """Yield PCM frames until the async iterator is closed."""

class AudioOutput(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    async def play(self, pcm: AsyncIterator[bytes]) -> None:
        """Consume PCM frames from the async iterator and play until iterator is exhausted."""
```

注意： `frames()` 本身是同步方法、return `AsyncIterator[bytes]` ——呼叫者以 `async for frame in audio_input.frames():` 消費。這使得 worker 可以在 `abort` 時透過 `AsyncIterator.aclose()` 主動中斷串流，符合 `arch.md` §6.5 收斂契約。

### PCM 格式與轉換邊界

Ch 10 分開描述硬體 `native_format` 與 HAL 對上層承諾的 `stream_format`。`AudioInput.frames()` 只輸出 `stream_format`；native metadata 不隨 frame 傳遞。M3 selected input 的 delivered contract 固定為 16 kHz、mono、S16_LE、20 ms，因此每 frame 為 320 samples / 640 bytes。

兩種格式不同時，只允許由 real `core/audio` backend 依已驗證 config 做顯式 adaptation；`perception/listen`、VAD 與 ASR 不得再 resample、downmix 或改 sample format。Config、startup log、capability 與 test evidence 必須同時列出 native / stream format、channel policy、resampler 與 frame accumulator。`mock` / `null` 直接產生 stream format，不模擬硬體 native format。

`bytes` 內容為 raw PCM、little-endian、interleaved（多聲道時）。同一 `AudioInput` instance 的 stream format 由 `start()` 固定，運作中不得 renegotiate。任何 native format 不符、未宣告的轉換、`plughw:` 或其他隱式 ALSA conversion 都是 startup failure。

### 麥克風獨佔切換的實作面

`arch.md` §5.2 規範 `voice_wake` 與 `perception/listen` 不同時錄音，由 SM 協調。`arch.md` P4 / §5.2 同時明定 `input_events/voice_wake` 只是獨立 wake daemon 的 IPC client，跨 process 介面可序列化、不共享 Python 物件狀態。實作面因此區分「主 process 的 `AudioInput` 」與「 daemon 持有的麥克風」兩個不同 owner：

- 主 process 的 `AudioInput` 只服務 `perception/listen` ：Resource Manager 於本 process 建立一個 `AudioInput` ，供 listen worker 錄使用者語音。voice_wake daemon 是另一個 process，不共享此 instance，也不由主 process 直接 `aclose()` 其 iterator——跨 process 無法共用 Python iterator。
- `frames()` 的本地獨佔性：同一 `AudioInput` 於任一時刻僅允許一個活躍的 `frames()` iterator——後者呼叫時，若前者未 `aclose()` ，raise `RuntimeError("AudioInput already streaming")` 。此規則只約束本 process 內 listen worker 對其 iterator 的生命週期，與 daemon 無關。
- 切換協定走可序列化的控制動詞：SM 在 WAKE Entry 先 `await wake_listener.suspend()` ，該呼叫 return 代表 daemon 已停止錄音並釋放 ALSA 裝置；之後 listen 才呼叫本 process `frames()` 取得 iterator。真正回 IDLE 後 SM `await wake_listener.resume()` 讓 daemon 重新偵測喚醒詞。 `WakeListenerControl` 的 Protocol、owner、建立與注入位置由 Ch 4 §2.1 正式定義；跨 process wire schema 見 `docs/protocol.md` （延後產出）。
- 不由 audio HAL 做仲裁：HAL 只負責「拒絕本 process 第二個 iterator」；daemon 與 listen 之間誰該讓出麥克風，由 SM 透過 `WakeListenerControl` 的 suspend / resume 時序決定（SM 醒來反應時序 `arch.md` §4.3）。 `voice_wake` 未啟動時 SM 注入的 control 為 `None` ，主 process listen 直接獨佔麥克風。

### Backend 目錄

```
src/sbd/core/audio/
├── __init__.py          # factory: make_audio_input / make_audio_output
├── base.py              # AudioInput / AudioOutput Protocol
├── null/
│   ├── __init__.py
│   ├── input.py         # NullAudioInput : frames() 產出無限靜音 frame
│   └── output.py        # NullAudioOutput : play() 消費 iterator 但不輸出
├── mock/
│   ├── __init__.py
│   ├── input.py         # 從 WAV 檔讀 PCM
│   └── output.py        # 寫 WAV 或 no-op
└── alsa/
    ├── __init__.py
    ├── input.py         # direct ALSA capture + input adaptation；binding 待 POC gate
    └── output.py        # direct ALSA playback；binding 待 POC gate
```

### Null 實作行為

- `NullAudioInput.frames()` : 以 config 定義的 frame 大小產出全 `\x00` bytes、 `asyncio.sleep(frame_duration)` 模擬即時串流； `aclose()` 立即結束
- `NullAudioOutput.play(pcm)` : `async for _ in pcm: pass` ——消費完 iterator 立即 return，模擬即時播放

### M3 Real Backend 目標硬體（Pi 5 ALSA）

來源：`DELIVERY-AUDIO-POC-M3-ACK-001`、`DELIVERY-AUDIO-POC-M3-ACK-002`、`DELIVERY-AUDIO-POC-M3-VALIDATION-001`、`CR-AUDIO-M3-PCM-001` 與 `M1-NATIVE-AUDIO-001`。ACK-002 接受 Option A 的產品契約與責任邊界，但不把尚未在 Pi 驗證的 binding、resampler、buffering 或 async I/O 模式視為已核准實作。

| 項目 | 規格 |
|---|---|
| 目標裝置 | Raspberry Pi 5 |
| 麥克風 | INMP441（I2S 數位麥克風） |
| 喇叭擴大器 | MAX98357A（I2S Class D Amplifier） |
| 匯流排 | I2S，BCLK / LRCK 共用 |
| Overlay | `googlevoicehat-soundcard`（`/boot/config.txt` 啟用） |
| Direct ALSA device | Pi local config；POC P2 baseline 為 `hw:0,0`，禁止 `plughw:` |
| Input native format | 48 kHz、stereo、S32_LE container；有效位元數 / alignment與channel index須由POC P4 target evidence確認後寫入local config |
| Input stream format | 16 kHz、mono、S16_LE、20 ms；320 samples / 640 bytes |
| Input adaptation | HAL-owned channel select → S32/24-bit normalization → anti-alias 3:1 resample → saturating S16 → exact-frame accumulator |
| Output native format | 48 kHz、stereo、S32_LE |
| Output stream format | M3 fixture 與 native format 相同；P3 TTS winner 前不做 output adaptation |
| Backend driver | `alsa/` 目錄；direct ALSA binding、resampler 與 I/O 模式待 POC validation gate |

#### Option A 必要語意

1. Backend 以 direct ALSA `hw:` device開啟48 kHz / 2-channel / S32_LE capture / playback，並核對requested與realized device / rate / channels / format。Actual不完全相同時`start()`失敗，不得接受coercion。
2. 對每個interleaved frame取local config指定的channel `0`或`1`。S32_LE container的有效mic bits數、alignment與scale須由target evidence確認後固定；另一channel不得混入，除非未來另立change request。
3. 48→16 kHz轉換必須為具anti-alias filter的stateful streaming resampler。禁止naive sample dropping、每chunk重建resampler或以整段離線轉換取代串流行為。
4. Resampler可輸出不等長chunk；backend以私有accumulator組成精確320-sample frame，再做round + saturating S16_LE。不得以padding、截斷或timing sleep隱藏錯長度。
5. `frames()` iterator `aclose()`、cancel、read failure、`stop()` 與 reopen 都必須關閉 ALSA stream，丟棄 partial frame，重置 resampler / clip counter / accumulator。新 session 不得帶入舊 filter state。
6. Startup INFO log 與 capability record只列 sanitized device identifier、native / stream formats、channel index、resampler implementation/version；不得記錄 raw PCM。Unsupported format 或 dependency 缺失走既有 RM real→null fallback。

#### POC validation gate

`pyalsaaudio`、`samplerate/libsamplerate`及其他候選方案目前都只是探索候選，不是Core dependency decision。Audio POC依`DELIVERY-AUDIO-POC-M3-VALIDATION-001`在目標Pi交付reproducible harness與比較證據，至少涵蓋direct native open、有效位元解析、streaming anti-alias品質、exact framing、buffering、event-loop responsiveness、cancel / reopen、xrun、CPU / RSS / latency及license / build可重現性。

Core Designer在收到POC完整40-character SHA後才核准binding、resampler、版本、hash、system dependency、buffer參數與async I/O模式。Developer在此之前可以實作Protocol、mock/null、native / stream config schema與fake-source conversion seam；不得開始Audio real backend、加入production dependency lock，或把任一候選套件寫成M3 selected baseline。POC產生的wheel / `.so`不得搬入Core Git；最終採用後仍由target Pi依核准lock build / install。

#### Acceptance boundary

- P1 native 16 kHz capability已由 `M1-NATIVE-AUDIO-001` 判定 FAIL；Option A是已核准的product direction，不得把P1改寫成native PASS。
- P2 direct device / overlay config / wiring evidence已 PASS；實際 device、channel、config copy與 hash 仍由 Core Pi local deployment提供。
- P4 Option A implementation feasibility為`POC VALIDATION PENDING`；它阻擋Audio real backend package start與M3 Audio acceptance，但不阻擋其他M3 HAL、Audio mock/null或schema工作。
- P3 TTS winner format仍 Pending M4a；它不阻擋 M3 AudioInput，但在完成前禁止替 AudioOutput 新增隱式 resample。
- POC gate PASS後，Core M3 Pi驗收仍須對exact implementation SHA記錄direct native probe、每幀640 bytes、alias rejection、CPU / RSS / latency、xrun、cancel / stop / reopen與owner cleanup；POC evidence不能取代Core Tester驗收。


---

## 2a.3 core/display 底層 HAL

職責（ `arch.md` §2.3 / §5.3 ）：低階顯示原語（ clear / write pixels / show ）；不含仲裁、不含 pixel format 高階轉換、不含觸控（若面板含觸控另設事件源，屬未定案，見 `arch.md` §8.1 相關項）。

本節僅定義底層 HAL Protocol；仲裁層四動作（ write_status_slot / write_main / request_fullscreen / release_fullscreen ）於 Ch 8 定義；仲裁層依賴本節的 DisplayDevice 契約。

### Protocol 定義

```python
# src/sbd/core/display/base.py
from typing import Protocol

class DisplayDevice(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    def clear(self) -> None:
        """清空 back buffer ( 不觸發顯示更新 ) 。"""
        ...

    def write_pixels(self, buf: bytes) -> None:
        """把 pixel buffer 寫入 back buffer ( 不觸發顯示更新 ) 。

        buf 格式 ( 單色 bit-packed / RGB565 / RGB888 ) 由 driver 自行解讀；
        長度必須等於該面板的 buffer size ，否則 raise ValueError 。
        """
        ...

    def show(self) -> None:
        """把 back buffer flush 到面板 ( 觸發實際顯示更新 ) 。"""
        ...

    def size(self) -> tuple[int, int]:
        """return (width, height) ，供仲裁層與 renderer 計算佈局用。"""
        ...
```

設計要點
- 雙緩衝語意： clear / write_pixels 只動 back buffer； show 才 flush 到面板——避免半熟畫面出現、允許仲裁層於 flush 前組合多個區域
- 同步方法： clear / write_pixels / show / size 為同步——ctypes 呼叫本身是同步 C，包成 async 只會多一層 overhead 且無 await 點
- `size()` 為方法而非屬性：Protocol 慣例上屬性用 `@property` 亦可；使用方法避免 Protocol runtime check 對屬性支援不一致的問題
- M4c起SSD1351正常`stop()`須在native handle仍有效時best-effort present恰好一個全零RGB565 full frame，再釋放handle、GPIO與SPI資源；present失敗不得阻止cleanup，重複`stop()`不得再次present或close。此為chip-specific lifecycle責任，不改`DisplayDevice`公開API，也不要求Null/Mock做硬體present。

### Buffer 格式

由具體 driver 決定（各 chip 有各自 pixel encoding）。上層若需通用繪圖，透過 `core/display/renderer.py` （ `DisplayRenderer` ，Ch 8 §2 / §4 定義，屬 core/display HAL 上層薄殼、不放 adaptor）做 pixel format 轉換。此落點與 `arch.md` P3 / §5.3 一致。

buf 長度驗證由 driver 內部實現；長度不符時 raise `ValueError` ——不容錯，避免 chip 收到破碎資料。

### Backend 目錄

```
src/sbd/core/display/
├── __init__.py          # factory: make_display(cfg)
├── base.py              # DisplayDevice Protocol
├── null/
│   ├── __init__.py
│   └── driver.py        # NullDisplay : 所有方法 no-op，size() return (0, 0)
├── mock/
│   ├── __init__.py
│   └── driver.py        # 開發機用：可 dump buffer 到檔案供 debug
└── <chip>/
    ├── __init__.py      # 每個控制晶片一個獨立子目錄（例：ssd1306/、ssd1351/）
    ├── driver.py        # ctypes wrapper
    ├── README.md        # chip datasheet 與支援解析度
    └── native/          # C driver 專屬（`libgpiod` / SPI）
        ├── include/
        ├── src/
        ├── Makefile
        └── build/<lib>.so # gitignored
```

### Chip 目錄組織原則

- 目錄名 = 控制晶片型號（ ssd1306 / ssd1351 / st7789 ），不用面板行銷名
- 同 chip 不同解析度共用 driver，解析度透過 constructor 參數傳入
- Chip driver 內部 C 實作與編譯流程屬 Ch 5 / Ch 11 涵蓋（native lib 未編譯時 factory 應自動 fallback null）

### Null 實作行為

- `NullDisplay` ： clear / write_pixels / show 皆 no-op； `size()` return `(0, 0)` 供上層判斷 null 狀態時避免除零

### 觸控與其他輸入

若面板含觸控，觸控事件源不屬本 Protocol—— DisplayDevice 只管顯示。觸控源目前無使用情境，暫不定案（ `arch.md` §2.3 ）。

---

## 2a.4 core/camera

職責（ `arch.md` §2.3 / §2.6 look ）：向 CSI 相機請求單張畫面。串流拍攝、視頻錄影不在本 agent 使用情境（ P2 ）。

### Protocol 定義

```python
# src/sbd/core/camera/base.py
from typing import Protocol

class Camera(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    async def capture(self) -> bytes:
        """觸發一次拍攝，return 一張影像的 raw bytes 。

        Format ("JPEG" / "RGB" / "YUV") 由 config 決定；同一 Camera instance 的所有 capture()
        return 同一格式。enum casing 與預設值與 Ch 10 §7 `CameraConfig` 完全一致。
        """
        ...
```

設計要點
- 單張拍攝：符合 perception/look 「拍一張、送分析」節奏（ `arch.md` §2.6 ）
- `capture()` 為 async：CSI 拍攝含曝光時間（幾十 ms 到幾百 ms），async 讓 look worker 等待期間不阻塞 event loop
- 無 stream API：P2「無使用情境不進契約」；未來若加入 gesture recognition 等需求，再擴 `stream()` 方法
- 無 timeout 參數： `capture()` 本身完成時間短且可預測；若需硬性中止走 `arch.md` §6.5 收斂機制（worker `abort` ）

### Image 格式

由 config （ Ch 10 §7 `CameraConfig` ）決定，enum casing / 預設值以 Ch 10 為唯一權威：
- `format` : `"JPEG"` / `"RGB"` / `"YUV"` （大寫），預設 `"RGB"`
- `width` / `height` : int，預設 `640` / `480`
- `quality` : int ( 僅 JPEG )，預設 `85`

format 選擇由 look worker 依 vision library 需要決定，透過 config 靜態指定；不允許 runtime 切換（切換需 stop → start）。Camera factory 與 config 使用同一組大寫 enum 比較，不做大小寫轉換。

### Backend 目錄

```
src/sbd/core/camera/
├── __init__.py          # factory: make_camera(cfg)
├── base.py              # Camera Protocol
├── null/
│   ├── __init__.py
│   └── driver.py        # NullCamera : capture() return 固定 blank image bytes
├── mock/
│   ├── __init__.py
│   └── driver.py        # 從檔案路徑 pool 循環讀圖
└── picamera2/
    ├── __init__.py
    └── driver.py        # 主要 backend ( Raspberry Pi 官方 CSI stack )
```

### Null 實作行為

- `NullCamera.capture()` ：依 config format return 符合該格式的合法 blank image bytes，使下游 decoder / Vision mock 不因格式無效 raise：
  - RGB : `width*height*3` 全零 bytes ( raw interleaved ) 。
  - YUV : `width*height*3//2` bytes ( I420 ; Y 平面全 `0x00` 、 U/V 平面全 `0x80` 中性色 ) ，長度與 driver 對該 format 宣告的 raw buffer 一致。
  - JPEG : 一張以相同 width / height / quality 產生的合法 JPEG encoded blank image ( 全黑 ) ，而非定長全零 bytes——後者不是合法 JPEG，會使下游 JPEG decoder raise。
- look worker 收到 blank image 後，vision library 通常回 `PerceptionResult(status="error", text=None)` 或降級文本；null 的無害語意不轉成下游解析 exception 。

外部依賴： `picamera2` ( RPi 官方套件 ) ；開發機無此套件時 factory 選 mock / null 。

---

## 2a.5 core/gpio

職責（ `arch.md` §2.3 / §5.4 ）：集中管理 GPIO pin 存取；一 pin 一訂閱者的登錄式介面。避免多模組爭搶同一 pin。

### Protocol 定義

```python
# src/sbd/core/gpio/base.py
from typing import Awaitable, Callable, Literal, Protocol
from dataclasses import dataclass

Edge = Literal["rising", "falling", "both"]
Direction = Literal["in", "out"]

@dataclass(frozen=True, slots=True)
class GPIOEvent:
    pin: int
    edge: Literal["rising", "falling"]
    at: float                 # monotonic timestamp

GPIOCallback = Callable[[GPIOEvent], Awaitable[None]]

class GPIO(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    async def register_input(
        self,
        pin: int,
        edge: Edge,
        callback: GPIOCallback,
        debounce_ms: int = 0,
    ) -> None:
        """註冊 input pin 的邊緣觸發 callback 。

        - 同一 pin 已註冊 → raise ValueError ( 一 pin 一訂閱者，見 arch.md §5.4 )
        - debounce_ms > 0 ：兩次連續事件間隔小於此值時，第二次被吞掉
        - callback 於獨立 asyncio task 內執行，避免阻塞 gpio event loop
        """
        ...

    async def unregister(self, pin: int) -> None:
        """解除 pin 註冊；未註冊 pin 呼叫為 no-op ( 冪等 ) 。"""
        ...

    async def set_output(self, pin: int, value: bool) -> None:
        """設定 output pin 電平。若 pin 未先以 output 模式初始化，raise ValueError 。"""
        ...

    async def configure_output(self, pin: int, initial: bool = False) -> None:
        """初始化 output pin ；重複 configure 同一 pin raise ValueError 。"""
        ...
```

設計要點
- 一 pin 一訂閱者：於 `register_input` 明確 raise，符合 `arch.md` §5.4 ；「一 pin 多訂閱者」屬 `arch.md` §8.1 未定案
- async callback : `Callable[[GPIOEvent], Awaitable[None]]`
  - GPIO 訂閱者本身在 async 世界（ `input_events/button` 需 await `asyncio.sleep()` 判斷長按門檻、需 publish 到 event bus ）
  - 若用同步 callback，訂閱者必須 `asyncio.create_task()` 包裝——強迫每個訂閱者寫同一段模板，集中在 core/gpio 處理更乾淨
  - `libgpiod` 2.x 常用 pattern：line event fd 透過 `loop.add_reader()` 掛到 asyncio event loop，事件到達時 spawn task 呼叫 callback
- Debounce 位置：由 core/gpio 統一處理；訂閱者不必自己實作
- Callback 隔離：於獨立 task 執行——callback raise 不影響其他 pin 的事件派發；exception 由 core/gpio 兜底 publish `ErrorOccurred(where="core.gpio.callback.<pin>", ...)` ( `arch.md` §6.7 HAL 分層責任)
- 無 null 實作（ §2a.1 ）：register 失敗 RM 記 `capability_of("gpio")=False` ；下游 `input_events` 依此不啟動

### set_output / configure_output 用途

- `configure_output` ：LED / 家電控制的 pin 初始化——設定為 output 模式、初始電平
- `set_output` ：於 configure 後改變電平； action/tool 派發家電命令時使用
- LED 相關： `core/leds/` 目錄不落地、Protocol 未定義（見 `arch.md` §8.1 「LED 顯示機制」）；LED 若需要基本控制能力，暫由使用者透過 `configure_output` + `set_output` 直接操作 pin。正式 LED HAL 契約、表達架構、與 `arch.md` §5.3 仲裁機制的關係，待 `arch.md` §8.1 LED 顯示機制定案

### Backend 目錄

```
src/sbd/core/gpio/
├── __init__.py          # factory: make_gpio(cfg)
├── base.py              # GPIO Protocol + GPIOEvent dataclass
├── mock/
│   ├── __init__.py
│   └── driver.py        # 開發機用：可用 API 手動觸發假事件
└── gpiod/
    ├── __init__.py
    └── driver.py        # libgpiod 2.x 綁定
```

### Mock 實作重點

- 提供 `MockGPIO.simulate_event(pin, edge)` 供測試主動觸發假事件——這是測試用 API，Protocol 不宣告
- 用 mock backend 時，button / adjustments 等訂閱者運行邏輯不變、測試可完全在開發機執行

外部依賴： `gpiod` ( libgpiod 2.x Python bindings ) ；RPi 系統套件 `libgpiod2` 。開發機 factory 選 mock 。

---

## 2a.6 檔案落點總覽

Ch 2a 對應目錄樹：

```
src/sbd/core/
├── audio/
│   ├── __init__.py          # factory
│   ├── base.py              # AudioInput / AudioOutput Protocol
│   ├── null/ {input.py, output.py}
│   ├── mock/ {input.py, output.py}
│   └── alsa/ {input.py, output.py}
├── display/
│   ├── __init__.py          # factory
│   ├── base.py              # DisplayDevice Protocol
│   ├── null/driver.py
│   ├── mock/driver.py
│   └── <chip>/ {driver.py, native/}
├── camera/
│   ├── __init__.py          # factory
│   ├── base.py              # Camera Protocol
│   ├── null/driver.py
│   ├── mock/driver.py
│   └── picamera2/driver.py
└── gpio/
    ├── __init__.py          # factory
    ├── base.py              # GPIO Protocol + GPIOEvent
    ├── mock/driver.py
    └── gpiod/driver.py
```

### 未列項目

- `core/leds/` : 本章不落地（見章首範圍邊界、 `../reviews/history/arch_review_implement.md` AR-Impl-4 ）
- `core/config/` / `core/logger.py` / `core/event_bus/` / `core/state_manager/` : 由 Ch 3 / Ch 4 / Ch 10 / Ch 11 涵蓋

### Import 慣例

- Worker 只 import `base.py` 的 Protocol，不 import backend 具體實作
- Factory 於 `__init__.py` 內 lazy import backend—— `from sbd.core.audio import make_audio_input` 不觸發任何 backend 載入
- Backend 內部若需共用工具，開 `_common.py` 私有 module；不對外 export
