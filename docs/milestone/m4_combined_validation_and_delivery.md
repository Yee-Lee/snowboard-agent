# M4：組合認證與正式交付

狀態：`PLANNED / ENTRY CONDITIONS MET`

Core 已於 commit `5aac035d25f6498c3c0affe1ace4afd7de8f7254` 正式關閉 M3 / Gate 2A，
並確認 Silero VAD、whisper.cpp base-Q8 ASR 與 Matcha TTS 為 M4 finalists。M4 尚未
開始 execution；下一步由 Audio 建立 internal M4 packet，先執行已接受的 P9 surrogate，
再進行 20-session combined/offline/failure-injection Gate 2B work。P9 未執行前沒有 PASS
或 LLM credit。

## 目標

證明 M3 hardware-qualified winners 在同一 Pi 5 離線、同時常駐、連續 session 與 failure injection 下仍符合 gate，並形成可進入 internal review 的完整 delivery package。

M4 也會 audit
[`DELIVERY-AUDIO-POC-M4A-CONTRACT-001`](../pm_handoff/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md)
Gate 1/Gate 2A ACK、winner/no-go 與 return SHA，並作為 Gate 2B final reference
與 portable conformance kit 的完整執行/回交階段；Core Gate 3 production implementation/
acceptance 屬 Core repo 後續工作，不得被 Audio POC 自行宣告完成。

## 對最終交付的貢獻

M4 關閉剩餘 delivery checklist，產出最終 winner/no-go、組合認證、sanitized evidence、產品化建議與完整交付 SHA。

## 工作大綱

- VAD、ASR、TTS 同時常駐，固定 thread/resource budget。
- 執行至少 20 個固定 pipeline sessions：VAD -> ASR -> deterministic/mock Reasoner -> TTS。
- 記錄總 RSS/swap/threads/load time、端到端 latency、溫度、頻率與 throttling。
- 分別在 VAD、ASR、TTS 注入 timeout/cancel/force-abort，確認 child/iterator/thread/stream/device owner 為零。
- 關閉網路重跑主要 pipeline。
- 若組合失敗，依既定順序評估較小 artifact、quantization、threads 或 lifecycle；不得改產品契約或降低 gate。
- Audit candidate manifests、license、checksums、fixtures、results、Pi/M3 SHA、資料安全與 rejected candidates。
- Audit M4a contract intake SHA、Gate 1 planning/candidate authorization、Gate 2A
  P1–P12 manifest/return SHA 與 Core selection ACK。
- 建立 portable conformance kit：candidate lock/provenance/license index、shared protocol/
  schema/vector/validator、lifecycle/offline/resource method、20-session result 與 known risks。
- 準備 delivery manifest、evidence index、winner/no-go、已知風險與產品化 integration 工作包。
- 依 Reviewer 的 ASR post-correction note，在 delivery package §7 彙整 M2A/M2B
  systematic semantic-mishearing patterns 與頻率；排除 LLM 可直接理解的數字、日期、
  百分比等格式差異。保留 raw baseline 與 fixed-prompt 的 Internal benefit/Common Voice
  regression，建議 Core 後續評估 decoder bias 或 context-aware post-decoder correction；
  不在 POC 實作/驗證 static lexicon 或新增 milestone。
- 進行 internal review，追蹤並關閉 blocking findings。

## Entry Conditions

- M3 每類已有 hardware-qualified winner，或已有核准的 no-go 處理方案。
- ASR/TTS 已取得 M4a Gate 2A selection ACK，或有
  核准的 no-go/change request。
- 所有 winner artifact、format、endpoint、threads、timeout、execution-container 固定。
- 組合 gate、session fixtures、failure injection 與 evidence 方法已確認。

## Exit Gate

- 至少 20 個固定 sessions 全部有結果且符合 frozen gate。
- 三模型同時常駐的 resource/latency/thermal evidence 完整。
- VAD/ASR/TTS 各階段 failure injection 後無資源殘留。
- 無網路主要 pipeline 可完成。
- VAD/ASR/TTS 各有唯一最終 winner，或明確且核准的 no-go。
- Delivery checklist 每一項都有 evidence、N/A 理由或正式 change request。
- Delivery manifest、evidence index、完整 repo/baseline SHA 與產品化建議完成。
- Repo 經資料安全 audit，不含模型、大型 raw result、私有音訊、敏感 transcript 或 secret。
- M4a Gate 1/2A/2B 所有決策、ACK 與完整 SHA 已納入 delivery/evidence
  index；Core Gate 3 清楚標為 external follow-up，不假裝為 POC PASS。
- Portable conformance kit 與 final handoff ID/full SHA 已直接回交 Core intake。
- 狀態先標記為 `Ready for internal review`；只有 findings 關閉、Designer
  核准且 Core 書面收件後才標記 Gate 2B `POC Accepted`。

## 必要 Evidence

- Residency/20-session/failure-injection/offline results。
- Total resource、latency、thermal 與 cleanup proof。
- Final candidate comparison、winner/no-go decisions、TTS User confirmation。
- Delivery manifest、evidence index、license/checksum/source index。
- Productization boundary、integration estimate、known risks 與 rejected candidates。
- ASR semantic-mishearing pattern/frequency report、prompt-bias 已知效果與 regression，
  以及由 Core 接手的 decoder/context correction 建議；format normalization 不列為
  acoustic recognition error。
- Review findings 及 closure evidence。
- M4a contract intake/Gate 1/Gate 2A ACK chain、Gate 2B final handoff SHA、
  portable conformance kit 與 Core Gate 3 handoff 索引。

## 不做的工作

- 不在本 milestone 直接把 winner 接入產品主線。
- 不在 POC repo 執行或驗收 Core M4a Gate 3 production backend，也不以
  POC `Ready for internal review` 取代 Core Tester exact-SHA acceptance。
- 不用簡報、demo 或摘要數字取代原始 evidence。
- 不刪除失敗 session 或 rejected candidates。
- 不因接近交付期限降低 gate。

## 調整觸發點

- 任一 winner 在組合常駐、failure injection、offline 或 thermal gate 失敗。
- Delivery checklist 有項目沒有 owner 或可行的關閉路徑。
- License/redistribution 或資料安全 audit 出現 blocking issue。
- Review finding 需要改變既定契約、硬體或 baseline。

## Gate Review 問題

M4 結束時必須逐項回答最終 delivery checklist 是否有可重現證據。任何未關閉項目都必須使狀態保持 `AT_RISK`/`NOT_REACHABLE`，或形成正式 change request；不得只因 demo 可用而宣告完成。
