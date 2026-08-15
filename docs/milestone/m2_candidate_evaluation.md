# M2：VAD、ASR、TTS 隔離候選比較

狀態：`NOT_STARTED`

## 目標

用 M1 固定的方法比較所有核准候選，淘汰不具交付資格者，為每一類產出可進入真實硬體整合的 finalist；此階段結果仍須通過 M3/M4 才能成為最終 winner。

本 milestone 同時承接
[`DELIVERY-AUDIO-POC-M4A-CONTRACT-001`](../pm_handoff/history/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md)
Gate 1：POC 先回交 candidate/version/source hash/license/Pi build proposal，只對
Core Designer 書面核准的範圍執行比較。M2 結果是 Gate 2 evidence 的累積，
不是 Core final winner ACK。

## 對最終交付的貢獻

- 完整 candidate manifest、license/checksum/source 與成功或失敗結果。
- VAD endpoint、ASR 品質、TTS 品質及 latency/resource/lifecycle 比較。
- `advance`/`reject` 判定和 execution-container 初步建議。
- M4a Gate 1 授權記錄與 M4A-P2/P3/P6/P10/P11/P12 的隔離驗證索引。

## 工作大綱

- 先做 license、artifact 可固定、offline、aarch64 安裝進場檢查。
- Gate 1 proposal 先對齊 Core 起始候選：ASR 為 whisper.cpp、Vosk、
  PocketSphinx；TTS 為 Piper、espeak-ng、Coqui TTS。每一列仍須固定
  exact artifact/version/hash/license，不得只交 engine 名稱。
- 既有 SenseVoice、Paraformer 與 sherpa-onnx voice 以 alternative 列入 proposal，
  只有 Core Designer 書面核准後才執行，不靜默取代 contract 清單。
- VAD 維持 Silero VAD ONNX/WebRTC VAD 與相同 endpoint state machine；由於
  Core contract Gate 1 文字只列 ASR/TTS，M2 entry 前須由 PM/Core 書面確認
  VAD 仍依 Audio POC frozen gate 執行。
- 所有候選使用相同 fixture、threads、warm-up、repetitions 與量測工具。
- 驗證 cold/hot、p50/p95、RTF、RSS、disk、CPU、cancel、force-abort、offline 與 cleanup。
- 安排 User 對 TTS voice 做受控主觀品質確認。
- 保留失敗結果，為每個 candidate 記錄 advance/reject 及原因。
- 以 M4A-P1 至 P12 ID 建立 traceability；M2 只能對隔離 fixture/build/
  lifecycle/offline 產生 preliminary evidence，HAL playback、Pi resource 與同時常駐的
  final disposition 留待 M3。

M2 執行分成兩個子 gate：

1. **Gate 1 proposal**：只整理 candidate manifest、license/source/build 提案與
   language/VAD boundary 問題；不下載大型 artifact、不執行真實 candidate run。
2. **Authorized comparison**：只在 Core Designer 書面 ACK 後，對 ACK 明列範圍
   執行 fixture benchmark 與 preliminary Gate 2 evidence。

## Entry Conditions

- M1 exit gate 通過，gate 與 fixtures 已凍結。
- M4a contract Gate 0 已以 Core P4 final selection ACK 關閉，且 contract
  intake 已記錄 POC 完整 SHA。
- PM relay/ACK 回傳路徑、candidate proposal template 與 Core decision owner 已確認。
- 敏感 fixture 受控位置可用。

真實 candidate execution 的子 gate 還必須滿足：Gate 1 proposal 已列版本、
artifact、source SHA-256、transitive dependency、license/notice 與 Pi build
steps，且 Core Designer 已書面核准 candidate scope、產品語言/voice
與 VAD 執行邊界。

## Exit Gate

- 每個已執行候選都有完整 manifest、結果與判定，失敗沒有被省略。
- 每一類至少有一個達 M2 gate 的 finalist；否則提出該類 no-go/change request。
- Finalists 的 artifact/version/checksum/license、format、threads、timeout 與 wrapper lifecycle 明確。
- TTS finalist 已取得 User 的初步品質回饋。
- M3 真實 Pi/HAL 重測範圍與必要 fixtures 已明確。
- Gate 1 ACK、核准 candidate list 與每個 M4A Test ID 的 preliminary/
  pending 狀態可由固定 SHA 定位；未在 M2 完成的 HAL/Pi 項目不得標為 PASS。

## 必要 Evidence

- Candidate manifests 與 eligibility decisions。
- Sanitized per-run results 及 result index。
- VAD/ASR/TTS 品質與資源比較摘要。
- Cancel/force-abort/orphan cleanup proof。
- Offline results、TTS user review 與 rejected-candidate reasons。
- Core Gate 1 ACK、candidate scope、language/VAD boundary decision 與 M4A-P1–P12
  traceability matrix。

## 不做的工作

- 不接 product composition root、RM 或 SM。
- 不為淘汰候選做無限調參或產品化。
- 不因候選表現修改 frozen gate。
- 不把開發機結果當 Pi 5 驗收。

## 調整觸發點

- 任一類所有候選在 eligibility 或 frozen gate 淘汰。
- Artifact/license 無法固定，或模型不能合法商用/再散布。
- Wrapper 無法提供可靠 cancel/force-abort/exit proof。
- Pi 5 資源預估已明顯無法支撐 M4 同時常駐。
- Core 不核准 contract 起始候選、現有 alternative 或 VAD 執行邊界。
- M4A-P3/P6 的 contract 門檻低於 Audio POC frozen gate；此時維持較嚴格的
  CER/整句正確率與 TTS User 品質 gate，不得因新 contract 放寬。

## Gate Review 問題

M2 結束時必須回答：每類 finalist 是否有合理機會在 pinned M3 HAL、真實 mic/speaker 與三模型同時常駐下達到最終 gate？沒有合理路徑者不得只因單項 demo 成功而 advance。
