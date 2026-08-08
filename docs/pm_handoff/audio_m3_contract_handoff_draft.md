# Audio POC → Core M3 Audio HAL Contract Handoff — Draft

狀態：`DRAFT / NOT ACCEPTED`
版本：`0.1`
提供方：Audio POC / User as Designer
接收方：Core Team Designer
核心開發位置：本 repository 的 `dev_agent_m2`；不得以 branch 名稱取代最終 SHA。

## 1. 目的與使用時機

本文件是 POC M1 提供給核心團隊的設計輸入，讓核心團隊可開始 M3 Audio HAL
的 API、config、mock/null 與 Pi backend 設計。它不是 POC M3 的 integration
baseline；POC M3 必須等待核心團隊回交通過產品驗收的完整 SHA。

## 2. 已可開始實作的 contract

核心團隊可依下列已確認條件推進；它們與既有
`src/sbd/core/audio` Protocol 及 `core_audio_m3_requirements.md` 一致。

| 領域 | 交接 contract |
| --- | --- |
| 目標硬體 | Raspberry Pi 5；INMP441 mic 與 MAX98357A speaker amplifier，共用 I2S BCLK/LRCK，使用 `googlevoicehat-soundcard` overlay。 |
| Input API | `start()`、`stop()`、`frames() -> AsyncIterator[bytes]`；同一 instance 只有一個 active iterator。 |
| Output API | `start()`、`stop()`、`play(pcm: AsyncIterator[bytes])`；完整消費合法 PCM chunk sequence。 |
| Input PCM target | 16 kHz、mono、16-bit little-endian、20 ms frame；format 固定於 config，不在 frame 內夾帶 metadata。 |
| Output PCM | sample rate 可與 input 不同，最終 rate 由 POC M2 TTS winner 固定；Speak 不得隱式 resample。 |
| 責任邊界 | HAL 僅處理 PCM capture/playback、device lifecycle 與 capability/error。VAD、endpoint、ASR、candidate wrapper 不進 HAL。 |
| Lifecycle | input/output 必須可各自 start、stop、reopen；stop 後不得殘留 stream、task 或 device owner。invalid device 必須有可觀察的 error/fallback/capability 結果。 |
| 不在範圍 | AEC、barge-in、wake word、跨 process mic handoff、真實 VAD/ASR/TTS 整合。 |

## 3. POC 尚待提供、但不阻礙 API 設計的依賴

| Dependency | POC M1/M2 產出 | 影響 |
| --- | --- | --- |
| 原生 PCM capability | `hw:` rate/channel/sample-format matrix、conversion location、xrun 與 lifecycle evidence。 | 阻礙 Pi backend 的最終 acceptance；若 16 kHz target 不可行，須共同 change request。 |
| 實際裝置設定 | Pi 的 card/device identifier、driver/config hash、接線及供電確認。 | 阻礙可重現的 Pi test command；不應硬編碼至 generic source。 |
| TTS output format | M2 winner 的 rate、channels、bit depth、chunk behaviour 與 fixture。 | 不阻礙可配置 Output API；阻礙 POC M3 的 winner playback evidence。 |
| 受控 fixture | 合法 mic WAV 與固定 PCM playback fixture 的 metadata/checksum。 | 阻礙最終 Pi integration evidence。 |

## 4. 核心團隊回交件（POC M3 entry 必要）

核心 M3 完成產品驗收後，請提供：

1. 完整 40-character commit SHA，以及 source、tests、權威文件均可由該 SHA 取得。
2. Pi 5 安裝、driver/device、config、native dependency 與執行命令。
3. Input PCM/frame timing、Output PCM iterator playback、start/stop/reopen、
   invalid device、fallback/capability、cleanup 的自動化或可重複證據。
4. 已知 buffering、sample-rate、shared-clock、xrun 與 ownership 限制。

POC Tester 只會以該完整 SHA 進行 POC M3 integration；若需修改 API、PCM
contract 或 lifecycle 語意，核心團隊與 POC 必須先提出並核准 change request。

## 5. Acceptance record

| Decision | Owner | Status |
| --- | --- | --- |
| Core Team accepts contract v0.1 as M3 design input | Core Team Designer | `PENDING` |
| POC M1 publishes native capability matrix | Audio POC Tester | `PENDING` |
| Core Team supplies accepted M3 baseline SHA | Core Team Designer | `PENDING` |
| POC accepts the SHA for M3 integration | Audio POC Tester / User | `PENDING` |
