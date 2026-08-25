# M4：組合認證與正式交付

狀態：`COMPLETE / POC ACCEPTED`

Core 已於 commit `5aac035d25f6498c3c0affe1ace4afd7de8f7254` 正式關閉 M3 / Gate 2A，
並確認 Silero VAD、whisper.cpp base-Q8 ASR 與 Matcha TTS 為 M4 finalists。User 已於
2026-08-25 核准 internal M4 plan、固定 20-session catalog，以及先 P9、後獨立 combined
run 的執行順序。Machine-readable packet、schema、fail-closed validator 與 local fake
runner 已建立；20 個 persistent fake sessions、三 domain 共 12 個 failure/recovery cases
與完整 regression 已本地驗證。這些結果不是 Pi、P9 或 Gate 2B evidence，formal mode 仍
fail closed。candidate `79185f992dd1510a9e8298242cec66b237081c52` 已在 Pi 以 pinned
Core SHA 與三個對齊後的隔離 runtime 執行 P9。正式結果仍為待 User 確認的 draft `FAIL`：
完整 Audio session 需 `8.459 s`，其中 ASR 單段 `6.028 s`，已超過 immutable P9 worker
的 `6.0 s` lifetime；另有 controller OpenBLAS thread delta `+3`。User 已判定原 P9
不符合實際非串流使用順序，並指示 Audio POC 提出 P9.1。現由
`P9.1-REALISTIC-TURN-RESIDENCY-DESIGN-001` 已獲 User 明確確認並取代原 P9。packet、runner、
Audio residency proof、partial failure evidence 與 controller thread policy 已完成修改。
P9.1 reviewed PASS 前不得繼續 independent 20-session run。

首次 P9.1 candidate 已正確完成 sessions 01–07，session 08 因 catalog 誤納 M2 已知
hard-failure `asr-pause-037` 而停止，cleanup 全零。User 已核准
`M4-P9.1-CATALOG-CORRECTION-001`，以同類別下一筆且既有 M2 evidence 證明為單一完整 capture
的 `asr-pause-038` 取代；其餘 19 筆、candidate 與 gates 不變。下一步建立新 SHA 從 session 01
完整重跑，不繼承 partial PASS。

catalog 修正後的 candidate `d36490f62679f50a3c109c4a10e80f7ee45221ad` 曾完成全部 20
sessions 且 cleanup 全零，但背景 resource sampler 在 transient P9 PID 結束時發生
`ProcessLookupError` 後停止，runner 又以固定值誤報 sampling interval。該 draft PASS 已依
`M4-P9.1-SAMPLER-RACE-001` 拒絕且不發布。append-only 修正以 `0.25 s` monotonic schedule
取樣、驗證實際 gap 不超過 `0.5 s`、容忍 PID exit race，並在 sampler thread 失敗時讓正式
run fail closed；完整 212-test regression 已通過。User 已授權此次修正形成的下一個唯一
candidate SHA，該 candidate 必須從 session 01 重跑，不繼承任何 partial PASS。

candidate `ffcfaa85c9db98333b5ec879f22515bf870b19d1` 隨後完成全部 20 sessions、cleanup
全零、peak used `3330.422 MiB`、zero swap 且無 throttling，但 888 筆 resource records
有一筆 `0.532864 s` completion timestamp gap。檢查確認 timestamp 原在同步 `/proc`
collection 後才記錄，錯把 collection cost 混入 sampling interval。append-only 修正改為
在 collection 前記錄 timestamp，另存 collection duration；`0.25 s` schedule 與較嚴格的
`0.5 s` continuity gate 均不變。完整 213-test regression 已通過，User 已授權此修正產生的
下一個唯一 candidate SHA 與正式重跑；舊 draft FAIL 不取得 partial credit。

User 已確認 candidate `8be3bc095b504b8eab1dfeb21b94173728b9656f` 的 reviewed P9.1
`PASS`。同一 Audio/Core SHA 的 independent combined run 完成 20/20 sessions、offline、
cleanup 全零、peak used `979.109 MiB`、peak temperature `58.95 °C` 且無 throttling。
failure executor baseline 修正形成 candidate
`26f33a3c371eee61df46924432839d0fa9ee3bf8`，完整重跑 VAD/ASR/TTS 各四種模式；12/12
均達 expected terminal，12/12 same-finalist recovery SUCCESS，每個 injection、recovery 及
final cleanup 全零。User 在取得 consolidated results 後指示完成報告、交付 Core 並等待回覆，
因此三份結果正式納入 `POC-audio-DEL-2026-001-R1`。Pi 已恢復原 zram、確認無 worker/device
owner、`throttled=0x0` 後關機。

Gate 2B technical execution 已完成。Core Designer response
`docs/outsource/responses/RESP-AUDIO-M4-GATE2B-001.md` 於 Core commit
`be19b70b1dd91674e7ff981eb9d6b2dca9741f54` 接受 corrected Audio SHA
`ca51bce9b4e205d9c9faf004d41c27169f108a3f`、三個 final references 與 portable kit；
blocking findings 為零並明確批准 M4 closure。Matcha pinned Apache-2.0 授權已接受，
未具名 training-data lineage 為 User-owned Accepted Risk，component notice bundle 為 Gate 3
packaging obligation。M4 因此標記 `COMPLETE / POC Accepted`；Gate 3 technical acceptance
仍屬 Core 後續範圍。

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

目前已觸發第一項：同一 clean Audio/Core SHA 的受控 P9 run 可重現完整 session 超過
surrogate worker lifetime。User 已指示以符合 `VAD -> ASR -> LLM -> TTS` 實際順序的 P9.1
取代原方法；設計確認前不得實作或執行，也不得以 client timeout 規避。

## Gate Review 問題

M4 結束時必須逐項回答最終 delivery checklist 是否有可重現證據。任何未關閉項目都必須使狀態保持 `AT_RISK`/`NOT_REACHABLE`，或形成正式 change request；不得只因 demo 可用而宣告完成。
