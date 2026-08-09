# M2：VAD、ASR、TTS 隔離候選比較

> Historical Audio POC record. This is not the active LLM M2; its status and
> result must not be used as the current LLM milestone state.

狀態：`NOT_STARTED`

## 目標

用 M1 固定的方法比較所有核准候選，淘汰不具交付資格者，為每一類產出可進入真實硬體整合的 finalist；此階段結果仍須通過 M3/M4 才能成為最終 winner。

## 對最終交付的貢獻

- 完整 candidate manifest、license/checksum/source 與成功或失敗結果。
- VAD endpoint、ASR 品質、TTS 品質及 latency/resource/lifecycle 比較。
- `advance`/`reject` 判定和 execution-container 初步建議。

## 工作大綱

- 先做 license、artifact 可固定、offline、aarch64 安裝進場檢查。
- VAD：比較 Silero VAD ONNX、WebRTC VAD，使用相同 endpoint state machine。
- ASR：比較核准的 SenseVoice、Paraformer、whisper.cpp 固定 artifact 版本。
- TTS：比較核准的 sherpa-onnx voice、Piper voice，分開記 runtime/voice license。
- 所有候選使用相同 fixture、threads、warm-up、repetitions 與量測工具。
- 驗證 cold/hot、p50/p95、RTF、RSS、disk、CPU、cancel、force-abort、offline 與 cleanup。
- 安排 User 對 TTS voice 做受控主觀品質確認。
- 保留失敗結果，為每個 candidate 記錄 advance/reject 及原因。

## Entry Conditions

- M1 exit gate 通過，gate 與 fixtures 已凍結。
- 候選清單、版本、artifact、license 初審與下載/保存政策核准。
- 敏感 fixture 受控位置可用。

## Exit Gate

- 每個已執行候選都有完整 manifest、結果與判定，失敗沒有被省略。
- 每一類至少有一個達 M2 gate 的 finalist；否則提出該類 no-go/change request。
- Finalists 的 artifact/version/checksum/license、format、threads、timeout 與 wrapper lifecycle 明確。
- TTS finalist 已取得 User 的初步品質回饋。
- M3 真實 Pi/HAL 重測範圍與必要 fixtures 已明確。

## 必要 Evidence

- Candidate manifests 與 eligibility decisions。
- Sanitized per-run results 及 result index。
- VAD/ASR/TTS 品質與資源比較摘要。
- Cancel/force-abort/orphan cleanup proof。
- Offline results、TTS user review 與 rejected-candidate reasons。

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

## Gate Review 問題

M2 結束時必須回答：每類 finalist 是否有合理機會在 pinned M3 HAL、真實 mic/speaker 與三模型同時常駐下達到最終 gate？沒有合理路徑者不得只因單項 demo 成功而 advance。
