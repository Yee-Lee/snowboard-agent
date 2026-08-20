# Audio POC Milestone Index

本檔是 milestone 狀態的唯一入口。M0 是 readiness gate，M1–M4 是四個正式交付 milestone。
唯一永久開發分支為 `audio`；已完成 gate 以不可移動的 annotated tag
`m0`、`m1`、……對應其 exact completion commit。

## Current Status

最後更新：2026-08-19
最終交付可達性：`AT_RISK` — M0 readiness gate 與 M1 共同測試基線已全數完成；
Option A P4-A01 至 A10 已獲 Core ACK-004 核准，M4a Gate 0 正式通過；
100 筆 native 與 delivered fixture、VAD timing labels 及 evaluation metrics
已獲 User/Designer 核准並完成凍結（FROZEN）。M1 正式完成（COMPLETE）。
Core 已於 `dev_agent_m4` commit
`e3d25d1fc70d726d5bd3162cdcb9571b30937587` 接受 Gate 1A，固定 `zh-TW`、
VAD scope、provenance-only acquisition 邊界及 P9 surrogate owner/due point。
POC 已在該邊界內完成 Gate 1B exact candidate proposal；metadata review 保留
至少一個 VAD、兩個 ASR 與三個 TTS 的可達路徑；2026-08-18 amendment
加入 User 指定的 Matcha zh/en primary TTS evaluation row，固定 archive、16 kHz
Vocos、runtime wheels 與 ModelScope lineage，但保留訓練資料/notice legal blocker。
Core 已在 `dev_agent_m4` commit
`790c0f86e12422542ef94cacd3c4dd850e346bca` 發出
`DELIVERY-AUDIO-POC-M4A-G1B-CANDIDATE-ACK-001`，只授權 SenseVoice ASR 與
Matcha TTS 兩個 primary rows 進入 offline build 與 isolated Gate 2A。
WP2 shared conformance scaffold 已以 fake-only protocol 完成；兩個 primary 的
clean-Pi artifact preflight、offline runtime install/import 與 focused smoke 已通過。
WP3 full-fixture qualification 已在 Pi SHA
`63c2cc179bb3c2525201da0f7a78d2c50b63d759` 完成：SenseVoice core CER 41.629%、
整體整句正確率 6%，未達 frozen gates 並已 `REJECT`；Matcha first-buffer/RTF
performance gates 通過，但 User quality、lifecycle、network-disabled、resource
growth 與 legal conditions 仍 pending。Product Team 已修訂
`CR-AUDIO-M4A-G1B-ASR-SCOPE-001`：要求以 whisper.cpp 1.9.2 multilingual
small Q8_0、4 threads 作為下一 primary，small Q5_1 僅為事前固定的條件式
resource/latency fallback；hot final-transcript p95 <=1.5 s hard gate 與現有
品質、RTF、資源及 lifecycle 邊界均不放寬。SenseVoice 不再調整，既有
Whisper.cpp base 與 faster-whisper small 維持 deferred；所有新 rows 仍須 Core
exact-row ACK 後才能執行。
本輪未授權 VAD row，與 Audio POC 最終須交付 VAD baseline/no-go 的出口不一致，
已提出 `CR-AUDIO-M4A-G1B-VAD-SCOPE-001`，因此最終交付維持 `AT_RISK`。

| Milestone | 狀態 | 摘要 | 文件 |
| --- | --- | --- | --- |
| M0 | `COMPLETE` | Pi worktree SHA/clean check、environment pre-test、SSH、timeout/cancel/cleanup 與 checksum transfer 已通過；M1 仍須明確進場 | [M0](m0_remote_environment.md) |
| M1 | `COMPLETE` | Option A 實作基準通過 Core ACK-004；100-item fixture (native & delivered)、VAD timing labels 與評測門檻全數凍結 (FROZEN) | [M1](m1_test_and_audio_baseline.md) |
| M2 | `IN_PROGRESS` | WP3 full-fixture：SenseVoice ASR frozen quality `FAIL/REJECT`；Matcha performance `PASS` 但 remaining gates pending；ASR/VAD scope CR 未關閉 | [M2](m2_candidate_evaluation.md) |
| M3 | `NOT_STARTED` | Pi 5/M3 Audio HAL 整合，完成 M4a Gate 2A P1–P12 回交與 selection ACK | [M3](m3_real_hardware_integration.md) |
| M4 | `NOT_STARTED` | Audio POC 20-session 組合認證、Gate 2B final reference/conformance kit 與正式交付 | [M4](m4_combined_validation_and_delivery.md) |

## Core M4a Contract Mapping

| Contract stage | POC milestone disposition |
| --- | --- |
| Contract intake SHA | M1 下一個 reviewable exact SHA 回覆；不單獨建立行政 commit |
| Gate 0：M3 P4 final selection | `PASSED` — Core 發出 `DELIVERY-AUDIO-POC-M3-P4-ACK-004` (ACCEPTED)，核准 Option A 實作基準 |
| Gate 1：planning + candidate authorization | `GATE 1A ACCEPTED / GATE 1B ACCEPTED` — Core commit `790c0f86e12422542ef94cacd3c4dd850e346bca` 只授權 SenseVoice ASR 與 Matcha TTS；其餘 rows 不可執行 |
| Gate 2A：POC qualification/selection | `WP2 COMPLETE / WP3 IN PROGRESS` — full-fixture evidence 已拒絕 SenseVoice、Matcha performance 通過但 remaining gates pending；Product Team 已要求 whisper.cpp small Q8_0 primary、conditional Q5_1、4-thread/1.5 s hard gate exact-row ACK，M3 尚未開始；Gate 2A 不是 final baseline lock |
| Gate 2B：final reference | M4 完成 20 sessions、failure/offline、internal review 與 conformance kit；`POC Accepted` 後 Core 才可固定 final reference |
| Gate 3：Core production implementation | Core repo external follow-up；Gate 2A ACK 後僅可建 scaffold，Gate 2B final reference intake 後才可固定 baseline；不是 Audio POC milestone PASS |

## Status Rules

允許狀態：

- `NOT_STARTED`
- `PLANNED / NEXT`
- `IN_PROGRESS`
- `GATE_REVIEW`
- `COMPLETE`
- `BLOCKED`
- `CHANGE_REQUESTED`

狀態變更時必須同時更新：

1. 最終交付可達性：`ON_TRACK`、`AT_RISK` 或 `NOT_REACHABLE`。
2. 已取得 evidence 與未關閉 exit conditions。
3. 新風險、blocker 或 change request。
4. 下一個獲准工作，不默認展開後續 milestone。

## Governing Documents

- [工作流程與合作方式](../audio_poc_workflow.md)
- [POC 開發指引](../specs/audio_poc_development_guide.md)
- [最終繳交清單](../specs/audio_poc_delivery_checklist.md)
- [M3 Audio 要求](../specs/core_audio_m3_requirements.md)

## Reference Material (Non-authoritative)

- [M3 Audio 設計修訂提案](../poc/poc_audio_m3_design_changes.md)
- [M4a Audio POC 計畫](../poc/poc_audio_m4_audio_poc_plan.md)
