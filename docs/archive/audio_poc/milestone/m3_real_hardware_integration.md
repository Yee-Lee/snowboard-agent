# M3：Pi 5 真實 M3 Audio HAL 整合

> Historical Audio POC record. This is not the active LLM M3; its status and
> result must not be used as the current LLM milestone state.

狀態：`NOT_STARTED`

## 目標

使用完整 SHA 固定的產品 M3 Audio HAL 與目標 Pi 5/I2S 硬體重跑 finalists，證明固定 WAV/text 結果能在真實 capture/playback、外殼與環境中成立。

## 對最終交付的貢獻

- Pi 5/M3 HAL、真實 mic fixture、原生 TTS PCM playback 的正式 evidence。
- Start/stop/reopen、device failure、backpressure、xrun、cancel 與 cleanup 認證。
- 每類一個 hardware-qualified winner，或 evidence-backed no-go。

## 工作大綱

- 固定 M3 HAL 產品 repo 與完整 commit SHA。
- 記錄 Pi 型號/RAM、OS、kernel、driver、mic/speaker、接線、外殼、距離與噪音環境。
- 用 M3 AudioInput 錄製等價 fixture，重跑 VAD/ASR finalists。
- 將 TTS finalist 的原生 PCM iterator 送入 M3 AudioOutput。
- 驗證 input/output 不同設定、半雙工 ownership 及不得在 Listen/Speak 隱式 resample。
- 測 start/stop/reopen、invalid device、backpressure、underrun/overflow、timeout/cancel/force-abort 與 cleanup。
- 記錄 Pi latency、RTF、RSS、CPU、temperature 與 throttling。
- 若固定 fixture winner 在真實裝置失敗，回到 finalist 比較，不降低 gate。

## Entry Conditions

- M2 finalists 與對應 artifact 全部固定。
- M3 Audio HAL 已通過其產品驗收並提供 source/tests/docs/完整 SHA。
- 目標 Pi、mic、speaker、外殼及真實測試環境可用。
- User 可進行現場距離、噪音與聲音確認。

## Exit Gate

- VAD/ASR finalists 已用目標 mic fixture 重跑並達 frozen gate。
- TTS finalist 已以原生 PCM sequence 經真實 AudioOutput 播放並達 gate。
- Device lifecycle、failure、xrun/backpressure、cancel 與 cleanup evidence 完整。
- Pi performance/resource/thermal evidence 完整，未以 Ubuntu/開發機結果取代。
- 每類產生一個 hardware-qualified winner；任何 no-go 或 fallback 都有正式決策。
- M4 組合所需 format、endpoint、threads、timeout 與 execution-container 已固定。

## 必要 Evidence

- M3 HAL repo/完整 SHA 與 Pi hardware/environment manifest。
- 真實 mic fixture metadata/checksum 與受控位置。
- VAD/ASR/TTS hardware run results。
- Playback sequence、xrun/backpressure、device lifecycle 與 cleanup proof。
- Latency/resource/thermal summary 與 rejected finalist reasons。

## 不做的工作

- 不修改產品 HAL 來掩蓋 POC candidate 缺陷；需要改 HAL 時走其正式 change/review 流程。
- 不加入 barge-in/AEC。
- 不以 `plughw` 隱藏未記錄的格式轉換。
- 不因真實硬體結果較差而調低 frozen gate。

## 調整觸發點

- M3 HAL SHA/契約/裝置行為無法滿足 POC 前提。
- 固定 WAV finalist 在真實 mic/speaker 全部失敗。
- Shared-clock 或 device ownership 使必要 lifecycle 無法成立。
- Thermal、RSS、RTF 或 latency 顯示 M4 組合不可能達標。

## Gate Review 問題

M3 結束時必須回答：固定 winners 是否已具備在同一 Pi 5 同時常駐並完成至少 20 sessions 的可信資源與 lifecycle 路徑？若答案是否定或證據不足，先提出 fallback/no-go，不直接進 M4。
