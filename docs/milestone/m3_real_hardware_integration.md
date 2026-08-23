# M3：Pi 5 真實 M3 Audio HAL 整合

狀態：`PLANNED`

## 目標

使用完整 SHA 固定的產品 M3 Audio HAL 與目標 Pi 5/I2S 硬體重跑 finalists，證明固定 WAV/text 結果能在真實 capture/playback、外殼與環境中成立。

本 milestone 也是
[`DELIVERY-AUDIO-POC-M4A-CONTRACT-001`](../pm_handoff/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md)
Gate 2A 的完整執行與回交階段：M2 的隔離結果必須用 accepted M3 HAL
與 Pi 資源重跑，再以完整 40-character SHA 回交 P1–P12 manifest，
等待 Core Gate 2A selection ACK。該 ACK 可放行 artifact-independent Core
adapter scaffold，不是 final reference、model baseline lock 或 `POC Accepted`。

M2 已由
[`RESP-AUDIO-M2-GATE-CLOSURE-002`](../reviews/RESP-AUDIO-M2-GATE-CLOSURE-002.md)
正式關閉；M3 依
[`M3-ENTRY-LOCK-002`](../../poc_audio/deliveries/M3-ENTRY-LOCK-002.md)
規劃，但尚未開始 hardware execution。User 已提交
[`CR-AUDIO-M3-RISK-FOCUSED-GATES-001`](../../poc_audio/deliveries/CR-AUDIO-M3-RISK-FOCUSED-GATES-001.md)
供 Core/Designer 審查；其 disposition 與 exact test packet 固定前，不執行 formal
qualification。

## 對最終交付的貢獻

- Pi 5/M3 HAL、真實 mic fixture、原生 TTS PCM playback 的正式 evidence。
- Start/stop/reopen、device failure、backpressure、xrun、cancel 與 cleanup 認證。
- 每類一個 hardware-qualified winner，或 evidence-backed no-go。
- M4A-P1–P12 可重現 manifest、Gate 2A selection ACK 與 M4 Gate 2B
  final reference 所需的 hardware-qualified ASR/TTS 建議。

## 工作大綱

- 固定 M3 HAL 產品 repo 與完整 commit SHA。
- 記錄 Pi 型號/RAM、OS、kernel、driver、mic/speaker、接線、外殼、距離與噪音環境。
- 用 M3 AudioInput 錄製等價 fixture，重跑 VAD/ASR finalists。
- 將 TTS finalist 的原生 PCM iterator 送入 M3 AudioOutput。
- 驗證 input/output 不同設定、半雙工 ownership 及不得在 Listen/Speak 隱式 resample。
- 測 start/stop/reopen、invalid device、backpressure、underrun/overflow、timeout/cancel/force-abort 與 cleanup。
- 記錄 Pi latency、RTF、RSS、CPU、temperature 與 throttling。
- 若固定 fixture winner 在真實裝置失敗，回到 finalist 比較，不降低 gate。
- 執行 M4A-P1–P8：ASR HAL frame 對齊/品質、TTS native PCM 與完整播放、
  ASR/TTS 個別 Pi resource/thermal。
- 執行 M4A-P9：使用 Core 核准且 versioned/checksummed 的 deterministic
  M4b residency surrogate 進行 co-residency 資源量測。本項只是 CPU/RSS/thermal
  budget evidence，不在 Audio POC 實作、選型或驗收 LiteRT-LM。
- 在 accepted HAL/Pi 重跑 M4A-P10–P12 lifecycle、clean build/license 與 offline，
  並沿用較嚴格的 Audio POC ASR/TTS frozen quality gate。
- 完成 contract 規定的 decision table、manifest 與 return delivery，回交完整
  SHA 後等待 Core Gate 2A selection ACK；final reference 由 M4 Gate 2B 完成。

## Entry Conditions

- M2 finalists 與對應 artifact 全部固定。
- M4a Gate 1 Core 書面核准、candidate scope 與 M4A-P1–P12 traceability
  已由 M2 完整 SHA 定位。
- M3 Audio HAL 已通過其產品驗收並提供 source/tests/docs/完整 SHA。
- 目標 Pi、mic、speaker、外殼及真實測試環境可用。
- User 可進行現場距離、噪音與聲音確認。
- M4A-P9 使用的 versioned deterministic M4b residency surrogate 身份、
  checksum、命令、RSS/thread/CPU envelope 與 decision rule 已由 Core/PM
  確認，且不導入 Audio 產品程式。

## Exit Gate

- VAD/ASR finalists 已用目標 mic fixture 重跑並達 frozen gate。
- TTS finalist 已以原生 PCM sequence 經真實 AudioOutput 播放並達 gate。
- Device lifecycle、failure、xrun/backpressure、cancel 與 cleanup evidence 完整。
- Pi performance/resource/thermal evidence 完整，未以 Ubuntu/開發機結果取代。
- 每類產生一個 hardware-qualified winner；任何 no-go 或 fallback 都有正式決策。
- M4 組合所需 format、endpoint、threads、timeout 與 execution-container 已固定。
- M4A-P1–P12 每項的 PASS/FAIL/INCONCLUSIVE、raw evidence path、cleanup 與
  reproduction command 已由 return SHA 定位。
- Core Designer 已發 Gate 2A selection ACK，或明確發出
  evidence-backed no-go/補件要求；未取得 ACK 時 M3 不得標為 `COMPLETE`。
  Final reference 與 `POC Accepted` 仍由 M4 Gate 2B 關閉。

## 必要 Evidence

- M3 HAL repo/完整 SHA 與 Pi hardware/environment manifest。
- 真實 mic fixture metadata/checksum 與受控位置。
- VAD/ASR/TTS hardware run results。
- Playback sequence、xrun/backpressure、device lifecycle 與 cleanup proof。
- Latency/resource/thermal summary 與 rejected finalist reasons。
- M4a Gate 2A manifest/decision table/return SHA 與 Core selection ACK。

## 不做的工作

- 不修改產品 HAL 來掩蓋 POC candidate 缺陷；需要改 HAL 時走其正式 change/review 流程。
- 不加入 barge-in/AEC。
- 不以 `plughw` 隱藏未記錄的格式轉換。
- 不因真實硬體結果較差而調低 frozen gate。
- 不將 M4A-P9 資源 stub 擴張成 LiteRT-LM candidate 比較、產品整合或
  M4b 驗收。

## 調整觸發點

- M3 HAL SHA/契約/裝置行為無法滿足 POC 前提。
- 固定 WAV finalist 在真實 mic/speaker 全部失敗。
- Shared-clock 或 device ownership 使必要 lifecycle 無法成立。
- Thermal、RSS、RTF 或 latency 顯示 M4 組合不可能達標。
- M4A-P9 所需 surrogate 無 version/checksum/可重現來源，或 Core 要求超出資源模擬
  而實作/驗收 LLM。
- Contract quality gate 與已凍結 Audio POC gate 不一致；取較嚴格者，
  若無法同時達成則提出 change request。

## Gate Review 問題

M3 結束時必須回答：固定 winners 是否已具備在同一 Pi 5 同時常駐並完成至少 20 sessions 的可信資源與 lifecycle 路徑？若答案是否定或證據不足，先提出 fallback/no-go，不直接進 M4。
