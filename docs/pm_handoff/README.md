# PM Handoff Index

本目錄只保留目前仍具約束力的規範與待處理 handoff；已完成且後續責任已由
新文件承接的 transaction record 移至 `history/`。歸檔不代表刪除決策或證據，
引用仍須指向可追溯的歷史文件。

最後更新：2026-08-24

## Authoritative POC Specifications

永久生效之全域開發手冊、架構契約與最終驗收清單已移至專屬規範目錄：
👉 [**`docs/specs/`**](../specs/README.md)

- [Audio POC 最終繳交清單](../specs/audio_poc_delivery_checklist.md)
- [Audio POC 團隊開發指引](../specs/audio_poc_development_guide.md)
- [Core Audio M3 要求](../specs/core_audio_m3_requirements.md)

## Active Handoffs

| Delivery | 狀態 | POC 回覆 / 下一步 |
| --- | --- | --- |
| [Core HAL playback drain CR](../../poc_audio/deliveries/CR-AUDIO-M3-CORE-HAL-PLAYBACK-DRAIN-001.md) / [Core ACK](RESP-AUDIO-M3-CORE-HAL-PLAYBACK-DRAIN-001.md) / [sanitized debug evidence](../../poc_audio/evidence/m3/M3-CORE-HAL-PLAYBACK-DRAIN-DEBUG-001.md) | `ACCEPTED / PACKET UPDATE AUTHORIZED` | Core 已 fast-forward authoritative replacement `6c7fc8c...`，接受 drain semantics/evidence 且不要求額外測試；Audio 只做 mechanical packet identity update 與 final exact-identity sign-off。 |
| [M3 Pi session schedule](../../poc_audio/deliveries/M3-PI-SESSION-SCHEDULE-001.md) | `EXECUTED IN PART / FINAL IDENTITY ACK PENDING` | 2026-08-24 preflight PASS、capture 開始；playback drain blocker 已關閉，後續 formal run 等待 append-only packet/signoff update。 |
| [M3 packet sign-off request](../../poc_audio/deliveries/REQ-AUDIO-M3-PACKET-SIGNOFF-001.md) / [Core ACK](RESP-AUDIO-M3-PACKET-SIGNOFF-001.md) | `HISTORICAL AUTHORIZATION / APPEND-ONLY UPDATE REQUIRED` | runner `655e80ec...`、manifest `ebadd620...65c55` 與 ACK `e638844...` 保持 immutable；因 Core replacement SHA 待定，後續 execution 需新 packet/runner identity 與 exact sign-off。 |
| [Core HAL output adaptation SHA-002](DELIVERY-AUDIO-M3-CORE-HAL-OUTPUT-SHA-002.md) / [original request](../../poc_audio/deliveries/CR-AUDIO-M3-CORE-HAL-OUTPUT-ADAPTATION-001.md) | `SUPERSEDED BY ACCEPTED REPLACEMENT` | `ff091995...` 保持歷史 execution identity；data adaptation 正確，但 success completion 缺 drain。由已接受的 `6c7fc8c...` 承接，不加入 POC resampler。 |
| [P9 executable correction](DELIVERY-012-PM-LLM-POC-P9-SURROGATE-EXECUTABLE.md) / [source identity](P9-SURROGATE-SOURCE-IDENTITY-001.md) / [Core ACK](DELIVERY-015-CORE-P9-SURROGATE-ACK.md) | `CORE ACCEPTED / AUDIO INTEGRATION UNBLOCKED / NOT EXECUTED` | Core ACK commit `caf4f7ba867e4ebc1972df0ade86c605a873a286` 已關閉外部前置；exact artifact 已 vendored/checksum verified。Audio 自行安排 bounded execution，不需再向 Core 要 P9 回覆；尚不得宣稱 P9 PASS 或 LLM Gate 2 credit。 |
| [Core response: M3 risk-focused qualification gates](RESP-AUDIO-M3-RISK-FOCUSED-GATES-001.md) | `ACCEPTED WITH CONDITIONS / PACKET AUTHORIZED` | POC 已 intake 判定框架與 packet minimum，User 已核准 exact packet，runner/local validation 已完成；下一步 commit candidate SHA 並送 Core sign-off。sign-off 前不執行 formal qualification。 |
| [M3 risk-focused qualification packet](../../poc_audio/deliveries/M3-RISK-FOCUSED-QUALIFICATION-TEST-PACKET-001.md) | `EXECUTED IN PART / FINAL IDENTITY ACK PENDING` | 原 packet/runner/sign-off immutable；preflight/capture finding已保留。只更新 exact identities，不放寬 VAD 8、ASR 5、TTS 6、lifecycle 或 22-result gates。 |
| [M3.1 remediation proposal](PROPOSAL_AUDIO_001_M3_1_REMEDIATION.md) / [Core framework response](RESP-AUDIO-M3-1-REMEDIATION-FRAMEWORK-001.md) | `CONDITIONALLY ACCEPTED / CONTINGENCY ONLY` | 不預先啟動。只有 M3 reproducible hard-gate finding、specific root cause 與 Core 事前核准的一個 minimal remediation 同時具備才另建 M3.1 packet。 |
| [M3 risk-focused qualification gates request](../../poc_audio/deliveries/CR-AUDIO-M3-RISK-FOCUSED-GATES-001.md) | `REVIEWED / ACCEPTED WITH CONDITIONS` | 決議由 Core response 承接；只取代 M1 numeric candidate-advance gates 作為 M3 automatic rejection rules。 |
| [Corrected M2 Gate closure request](../../poc_audio/deliveries/REQ-AUDIO-M2-GATE-CLOSURE-002.md) | `REVIEWED / ACCEPTED / M2 COMPLETE` | Reviewer 已接受 method correction、Silero conditional M3 finalist、低音量 target-mic blocker 與 `M3-ENTRY-LOCK-002`；blocking findings 已關閉。見 [`RESP-AUDIO-M2-GATE-CLOSURE-002`](../reviews/RESP-AUDIO-M2-GATE-CLOSURE-002.md)。 |
| [M2 Gate closure request 001](../../poc_audio/deliveries/REQ-AUDIO-M2-GATE-CLOSURE-001.md) | `SUPERSEDED / HISTORY PRESERVED` | 原 VAD no-go disposition 由 closure 002 取代；immutable old run evidence 保留，不再作 candidate rejection 依據。 |
| [M2 Gate review request](../../poc_audio/deliveries/REQ-AUDIO-M2-GATE-REVIEW-001.md) | `CLOSED / RESPONSE ACTIONED` | Reviewer 接受 ASR/TTS 並授權的 VAD 路徑已由 closure 002 完成；原 response 見 [`RESP-AUDIO-M2-GATE-REVIEW-001`](../reviews/RESP-AUDIO-M2-GATE-REVIEW-001.md)。 |
| [ASR post-correction review-note ACK](../../poc_audio/deliveries/ACK-AUDIO-ASR-POST-CORRECTION-001.md) | `ACKNOWLEDGED / M4 REQUIREMENT RECORDED` | 不新增 POC 實作或 milestone；M4 §7 將交付 semantic-mishearing patterns/frequency、prompt trade-off 與 Core decoder/context correction 建議。 |
| [Matcha M2 risk-focused review](../../poc_audio/evidence/m2/M4A-G1B-WP3-MATCHA-RISK-REVIEW-001.md) | `REVIEWED / M3 TTS FINALIST` | Lifecycle、true network-disabled P12、material resource risk 與 User 10-prompt quality 均通過；中位數 5，`tts-013` 為 4 分非 critical 瑕疵。Legal lineage 仍阻擋 redistribution/product/final-winner approval。 |
| [VAD execution scope change request](../../poc_audio/deliveries/CR-AUDIO-M4A-G1B-VAD-SCOPE-001.md) | `CORRECTED EVIDENCE / SILERO CONDITIONAL FINALIST` | 舊 no-go 方法失效但 evidence 保留；corrected WebRTC 不前進，corrected Silero 提為 M3 finalist 並保留低音量 blocker。詳見 [`M2-VAD-METHOD-CORRECTED-QUALIFICATION-002`](../../poc_audio/evidence/m2/M2-VAD-METHOD-CORRECTED-QUALIFICATION-002.md)。 |
| [Audio POC A / B 分組觀察計畫](Audio_POC_AB_experiement.md) | `RESPONSE READY / DATA PACKET COMPLETE` | 40-record sanitized data、A/B/A+B summary、paired outcomes、README 與 reproduction command 已提交；無新 inference，不改 frozen scorecard。見 [`RESP-AUDIO-M2A-AB-SPLIT-001`](../../poc_audio/deliveries/RESP-AUDIO-M2A-AB-SPLIT-001.md)。 |
| [DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003](DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003.md) | `ACCEPTED / ASR M3 DISPOSITION` | Reviewer 已接受 base Q8 primary、small Q8 fallback 與 exact prompt recipe；ASR matrix 保持停止，Common Voice regression 保留為 trade-off。 |
| [POC-AUDIO-PERF-2026-001](POC-AUDIO-PERF-2026-001/feedback.md) | `CLOSED / EVIDENCE PRESERVED` | bounded/native Q8 調查已完成；結果維持原 diagnostic disposition。後續 ASR 比較由 ACK-003 的共同 M2A packet 承接。回覆見 [`RESP-POC-AUDIO-PERF-2026-001`](../../poc_audio/deliveries/RESP-POC-AUDIO-PERF-2026-001.md)。 |
| [commit_workflow_update](commit_workflow_update.md) | `INTEGRATED` | 已將 unpublished WIP squash、Candidate SHA append-only、單一 `audio` branch 與 immutable milestone tags 整合至 [`docs/audio_poc_workflow.md`](../audio_poc_workflow.md) 與 `AGENTS.md`。 |
| [DELIVERY-AUDIO-POC-M4A-G1B-ASR-RECOVERY-ACK-002](DELIVERY-AUDIO-POC-M4A-G1B-ASR-RECOVERY-ACK-002.md) | `SUPERSEDED IN PART / EVIDENCE PRESERVED` | Exact source、artifact/build evidence 與 tested SHAs 保留；conditional Q5 trigger、ASR execution order 與 quality/performance elimination gates 已由 ACK-003 取代。 |
| [DELIVERY-AUDIO-POC-M4A-CONTRACT-001](DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md) | `GATE 1 ACCEPTED / M2A-M2B SCOPE ACKED` | Gate 1 歷史 planning/proposal 保留；ASR comparative funnel 由 ACK-003 承接。VAD 仍由 [`CR-AUDIO-M4A-G1B-VAD-SCOPE-001`](../../poc_audio/deliveries/CR-AUDIO-M4A-G1B-VAD-SCOPE-001.md) 追蹤。 |

## History

| Delivery | 歸檔理由 | 後續承接 |
| --- | --- | --- |
| [DELIVERY-AUDIO-POC-M3-ACK-001](history/DELIVERY-AUDIO-POC-M3-ACK-001.md) | 初始 M3 contract acceptance 已完成；P1/P2 已有 evidence 與後續決定。 | P1/Option A 決定見歷史 `ACK-002`；P4 由歷史 `VALIDATION-001` 與 `ACK-004` 承接，P3 由 `core_audio_m3_requirements.md` 約束。 |
| [DELIVERY-AUDIO-POC-M3-ACK-002](history/DELIVERY-AUDIO-POC-M3-ACK-002.md) | Option A 責任邊界與可觀察結果的方向決定已完成。 | P4 implementation validation 由歷史 `VALIDATION-001` 執行，並由歷史 `DELIVERY-AUDIO-POC-M3-P4-ACK-004` 正式核准。 |
| [DELIVERY-AUDIO-POC-M3-VALIDATION-001](history/DELIVERY-AUDIO-POC-M3-VALIDATION-001.md) | Option A 實作驗證要求已由 POC 完整回交（A01~A10 PASS + Manifest + 決策表）。 | 由歷史 [DELIVERY-AUDIO-POC-M3-P4-ACK-004](history/DELIVERY-AUDIO-POC-M3-P4-ACK-004.md) 正式核准結案。 |
| [DELIVERY-AUDIO-POC-M3-P4-ACK-003](history/DELIVERY-AUDIO-POC-M3-P4-ACK-003.md) | 中介收件確認（receipt disposition），指出缺件之 Blocking Finding。 | 已由正式核准的 [DELIVERY-AUDIO-POC-M3-P4-ACK-004](history/DELIVERY-AUDIO-POC-M3-P4-ACK-004.md) 取代。 |
| [RESP-AUDIO-M3-P4-REPRO-002](history/RESP-AUDIO-M3-P4-REPRO-002.md) | Core 核准 A10 clean-Pi rerun Option 2 之回覆。 | 已由 `CR-AUDIO-M3-P4-REPRO-002` 與 `P4-A10-RERUN-002` 執行並通過驗證。 |
| [DELIVERY-AUDIO-POC-M3-P4-ACK-004](history/DELIVERY-AUDIO-POC-M3-P4-ACK-004.md) | Core 已正式核准 P4 Option A 選型基準（`pyalsaaudio 0.11.0` + `samplerate 0.2.4 sinc_best`），M4a Gate 0 正式通過。 | 由已凍結之 M1 共同測試基線與 M3 real hardware integration 承接。 |
| [DELIVERY-AUDIO-POC-M4A-CONTRACT-001 (initial revision)](history/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md) | 初版在 Gate 0 關閉後曾歸檔；2026-08-17 修訂版已重新成為 active handoff。 | 以 active contract 與 `RESP-AUDIO-M4A-GATE-PLAN-001` 為本輪決策來源。 |

只有在決定已完成、未結責任已明確轉載到 active 文件，且 repo 內引用已更新後，
handoff 才可移入 `history/`。
