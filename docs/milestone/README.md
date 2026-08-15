# Audio POC Milestone Index

本檔是 milestone 狀態的唯一入口。M0 是 readiness gate，M1–M4 是四個正式交付 milestone。

## Current Status

最後更新：2026-08-15
最終交付可達性：`ON_TRACK` — M0 readiness gate 與 M1 共同測試基線已全數完成；
Option A P4-A01 至 A10 已獲 Core ACK-004 核准，M4a Gate 0 正式通過；
100 筆 native 與 delivered fixture、VAD timing labels 及 evaluation metrics
已獲 User/Designer 核准並完成凍結（FROZEN）。M1 正式完成（COMPLETE），
準備進入 M2 Gate 1 候選評測授權。

| Milestone | 狀態 | 摘要 | 文件 |
| --- | --- | --- | --- |
| M0 | `COMPLETE` | Pi worktree SHA/clean check、environment pre-test、SSH、timeout/cancel/cleanup 與 checksum transfer 已通過；M1 仍須明確進場 | [M0](m0_remote_environment.md) |
| M1 | `COMPLETE` | Option A 實作基準通過 Core ACK-004；100-item fixture (native & delivered)、VAD timing labels 與評測門檻全數凍結 (FROZEN) | [M1](m1_test_and_audio_baseline.md) |
| M2 | `NOT_STARTED` | M4a Gate 0 已通過；待提交 ASR/TTS 候選清單獲取 Gate 1 書面授權後展開候選評測 | [M2](m2_candidate_evaluation.md) |
| M3 | `NOT_STARTED` | Pi 5/M3 Audio HAL 整合，完成 M4a Gate 2 P1–P12 回交與 winner ACK | [M3](m3_real_hardware_integration.md) |
| M4 | `NOT_STARTED` | Audio POC 20-session 組合認證、M4a ACK audit 與正式交付 | [M4](m4_combined_validation_and_delivery.md) |

## Core M4a Contract Mapping

| Contract stage | POC milestone disposition |
| --- | --- |
| Contract intake SHA | M1 下一個 reviewable exact SHA 回覆；不單獨建立行政 commit |
| Gate 0：M3 P4 final selection | `PASSED` — Core 發出 `DELIVERY-AUDIO-POC-M3-P4-ACK-004` (ACCEPTED)，核准 Option A 實作基準 |
| Gate 1：candidate proposal/authorization | `NEXT` — M2 第一個子 gate；待 POC 提交 ASR/TTS 候選清單申請 Core 書面授權 |
| Gate 2：POC validation | M2 累積隔離 evidence；M3 以 accepted HAL/Pi 完成 P1–P12、return SHA 與 winner ACK |
| Gate 3：Core production implementation | Core repo external follow-up；Gate 2 final ACK 後可啟動，不是 Audio POC milestone PASS |

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
