# M3 Audio Design Changes

> Status: `REFERENCE / NON-AUTHORITATIVE`
>
> This is a historical Designer change proposal for the product M3 Audio HAL.
> It does not set the active POC milestone, gate, or implementation contract.
> Use `docs/milestone/README.md`, the active milestone document, and the
> authoritative M3 requirements for current work. Read this file only when a
> M3/Audio HAL design decision needs its background context.

本文檔整理 M3 開始前必須完成的 Audio 設計修訂。它是 Designer 的修訂清單，不是新的權威契約；正式決策必須同步回 `snowboard-agent/docs/implement/` 、 `snowboard-agent/docs/model_spec.md` 、 `snowboard-agent/docs/milestone.md` 與對應 progress 文件，並依既有 Implement Review 流程確認。

## 1. 目的與邊界

M3 只交付 Raspberry Pi 5 的真實 AudioInput / AudioOutput HAL 與固定 PCM fixture 驗證，不導入真實 VAD、ASR 或 TTS 模型。M3 開始前必須修正正會限制 M4a 選型、或讓 M3 real backend 無法一致實作的契約。

本次需要收斂兩項主要變更：

1. Audio input / output 設定與 PCM 格式分離。
2. VAD 正式納入 `perception/listen` 與 M4a model gate。

兩項都維持 `snowboard-agent/docs/specs/arch.md` 既有邊界： `core/audio` 只處理 PCM，VAD / endpoint / ASR 屬 `perception/listen` 。原則上不需要 Architect 改變架構；若 review 發現必須 改變模組邊界或跨 process 麥克風 ownership ，再另開 Designer -> Architect review。

## 2. DC-1：分離 Audio input / output 設定

### 2.1 現況問題

目前單一 `AudioConfig` 同時提供 AudioInput 與 AudioOutput：

- ASR / VAD 通常使用 16 kHz、mono、16-bit PCM。
- TTS voice 可能原生輸出 16、22.05、24 或 44.1 kHz。
- 現行 cross validation 要求 TTS 與共用 AudioConfig 完全一致，會迫使 TTS 配合 mic 格式，或在 Speak worker 內 resample；後者已被既有契約禁止。
- `core.audio.input` 與 `core.audio.output` 是不同 ResourceKey，卻無法各自指定 device、driver 與格式，亦不利於獨立 fallback / 診斷。
- 文件與 factory 使用 `alsa` ，config validator 使用 `sounddevice` ，real backend 名稱目前不一致。

### 2.2 目標設定模型

Ch 10 應改為 input / output 分離；欄位名稱可在 review 中微調，但必須表達下列資訊：

```python
@dataclass(frozen=True, slots=True)
class PCMFormat:
    sample_rate: int
    channels: int
    bit_depth: Literal[16]

@dataclass(frozen=True, slots=True)
class AudioInputConfig:
    driver: str = mock
    device: str | None = None
    format: PCMFormat = PCMFormat(16_000, 1, 16)
    frame_duration_ms: int = 20

@dataclass(frozen=True, slots=True)
class AudioOutputConfig:
    driver: str = mock
    device: str | None = None
    format: PCMFormat = PCMFormat(16_000, 1, 16)

@dataclass(frozen=True, slots=True)
class AudioConfig:
    input: AudioInputConfig
    output: AudioOutputConfig
```

設計要求：

- Input baseline 維持 16 kHz、mono、16-bit little-endian PCM、20 ms HAL frame。
- Output sample rate 不與 input 綁定；M3 可用固定 fixture 驗證，M4a 再依獲准 TTS voice 固定 local config。
- `frame_duration_ms` 只屬 AudioInput。TTS iterator 的 chunk 大小不是 HAL frame 契約，AudioOutput 必須完整消費任意合法 chunk sequence。
- Input frame bytes 仍須能由 sample rate、channels、bit depth、frame duration 整除計算。
- TTS output format 只需與 `core.audio.output.format` 一致，不需與 input 一致。
- Input / output factory、startup、fallback 與測試各自取得對應 config。
- `core.audio.input` 或 `core.audio.output` 個別失敗時，保留既有 RM null fallback 與 capability 計算規則，不在 HAL 內新增仲裁。

### 2.3 Real backend 命名

建議統一以下語意：

- Config driver : `sounddevice`
- Python library : `sounddevice`
- OS transport : PortAudio -> ALSA
- 實作目錄 : `core/audio/sounddevice/`

`alsa` 不再作為 config driver 名稱，避免把 OS transport 與 Python adapter 混為一談。若 review 決定保留 `alsa` ，則 factory、validator、example config、文件與目錄仍必須全部使用 同一名稱，不得保留 alias。

### 2.4 M3 對應驗收補充

M3 test spec 應能分別觀察：

- AudioInput 在 timeout 內產生格式、frame bytes 與時間順序正確的 PCM。
- 真實 mic PCM 可保存成合法 WAV，供 M4a POC 使用。
- AudioOutput 完整消費固定 PCM iterator，並以指定 output format 開啟裝置。
- Input / output 能獨立 start、stop、重新開啟，不遺留 stream / task / device owner。
- 不存在的 input 或 output device 各自觸發預期 fallback 與 capability 結果。
- 至少驗證 16 kHz output fixture；若目標裝置支援，也驗證 M4a TTS 候選常見的非 16 kHz fixture。實際 M4a baseline rate 仍由 POC 決定。

## 3. DC-2：將 VAD 納入 Listen 與 M4a gate

### 3.1 現況問題

現行 Listen 把無文字或整體 timeout 映射成 `PerceptionResult(status=timeout)` ，但沒有：

- VAD library adapter 契約。
- speech start / speech end 的 endpoint state machine。
- pre-roll、尾端靜音、最短語音與最長 utterance 設定。
- VAD model 的版本、授權、checksum 與 Pi benchmark gate。

若不補齊，Developer 必須自行決定切段方式，Tester 也無法區分「沒有說話」、「切掉首尾音節」與「ASR timeout」。

### 3.2 責任與資料流

VAD 必須位於 `perception/listen` ，不進 `core/audio` ：

```
AudioInput.frames()
  -> PCM rechunker
  -> VAD adapter + endpoint state machine
  -> bounded utterance iterator
  -> ASRAdapter.transcribe()
  -> PerceptionResult
```

責任分工：

- Audio HAL : 只產生固定格式 PCM frame。
- PCM rechunker : 將 20 ms HAL frame 重組為 VAD backend 要求的 chunk，不改變全域 HAL frame duration。
- VAD adapter : 對 chunk 產生 speech observation；不發布 Event Bus event。
- Endpoint state machine : 管理 pre-roll、speech start、尾端靜音、min/max duration。
- ASR adapter : 只消費有界 utterance iterator並輸出最終 transcript。
- Listen worker : 擁有 timeout、cancel、cleanup 與唯一 terminal Fact。

### 3.3 VAD 契約要求

Ch 2b 應新增最小 `VADAdapter` ，確切 signature 於 Implement Review 收斂，但必須涵蓋：

- `start()` / `stop()` 與每次 utterance 的 reset。
- 接受符合 input format 的 PCM chunk，回傳可供 endpoint 判定的 speech observation。
- 若 backend 有 native thread / child，提供 `abort()` / `force_abort()` 與 completion proof。
- 不持有 AudioInput、不自行發布 Fact、不解讀 session / turn ID。
- 不把 speech probability、raw PCM 或 transcript 寫入一般 log。

### 3.4 Config 目標

Ch 10 應把目前含糊的 `listen.adapter` 改為明確的 `listen.vad` 與 `listen.asr` ：

```yaml
perception:
  listen:
    enabled: true
    required: true
    vad:
      driver: mock
      model_path: null
      threshold: null
      pre_roll_ms: null
      speech_start_timeout_ms: null
      end_silence_ms: null
      min_speech_ms: null
      max_utterance_ms: null
    asr:
      driver: mock
      model_path: null
      language: null
```

上例的 null 表示數值仍由 M4a Audio POC 決定；正式 schema 不得接受缺少有效 default 的 產品設定。完成 POC、固定 baseline 後，再把核准值寫入 model profile / example config。

現有 `whisper` / `piper` driver literal 只是候選偏向，與「M4a 模型尚未選型」不一致。M3 前的 schema 修訂不得把任何 POC 候選宣告為產品 baseline；可暫時只允許 `mock` ，或由 review 決定 可擴充但仍受 registry 驗證的名稱機制。最終 real driver 名稱只在 M4a baseline 核准後加入產品 config。

### 3.5 Model 與 milestone 同步

- `model_spec.md` : M4a Local Voice baseline 增加 VAD engine / artifact / 版本 / license / checksum / input format / endpoint parameters / Pi benchmark / cancel cleanup。
- `milestone.md` M3 : 仍明確排除真實 VAD / ASR / TTS；增加可供 POC 使用的 mic fixture capture 證據。
- `milestone.md` M4a : 範圍增加 VAD + endpoint；驗收增加純靜音、不切首尾、尾端停頓、max utterance、cancel cleanup。
- `test_spec.md` : 由 Tester 在 M4a 定案前建立穩定 Test ID，不由本文件代寫。

## 4. 不在本次修訂內

- 選定 VAD、ASR、TTS 的最終 engine / model / voice。
- 實作或驗收真實模型 backend。
- 語音播放期間的 barge-in、AEC 或同時錄放音。
- Wake daemon / KWS 與跨 process mic handoff；它們仍屬 M6。
- 「喚醒詞 + 命令」連續說話的 buffered PCM handoff。若產品需要此 UX，需在 M6 前交 Architect 裁定。

## 5. M3 進場前完成清單

- [ ] Ch 2a 已定義 input / output 分離設定與 PCM 規則。
- [ ] Ch 2b 已定義 VAD / endpoint / ASR 的責任與 cancel 語意。
- [ ] Ch 10 schema、strict loader、validator、defaults 與 example config 已同步。
- [ ] real audio driver 名稱在文件、factory 與 validator 一致。
- [ ] model spec 已把 VAD 納入 M4a baseline gate，但未提前選定候選。
- [ ] milestone 的 M3 排除與 M4a VAD 範圍已同步。
- [ ] Reviewer 已確認 implement 修訂。
- [ ] Tester 已接手 M3 Audio HAL 的新驗收需求。
- [ ] `m4_audio_poc_plan.md` 的 POC-0 契約與重測格式可供團隊使用。
