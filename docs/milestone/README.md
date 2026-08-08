# Audio POC Milestone Index

本檔是 milestone 狀態的唯一入口。M0 是 readiness gate，M1–M4 是四個正式交付 milestone。

## Current Status

最後更新：2026-08-08
最終交付可達性：`AT_RISK` — M0 readiness gate 已完成；User/Designer 已批准 `CR-AUDIO-M3-PCM-001` Option A，等待 Core Team 接受；frozen gates 的 Tester verification 與 M3 HAL baseline 亦未完成。

| Milestone | 狀態 | 摘要 | 文件 |
| --- | --- | --- | --- |
| M0 | `COMPLETE` | Pi worktree SHA/clean check、environment pre-test、SSH、timeout/cancel/cleanup 與 checksum transfer 已通過；M1 仍須明確進場 | [M0](m0_remote_environment.md) |
| M1 | `CHANGE_REQUESTED` | P1 `FAIL`、P2 `PASS`；User 已批准 explicit AudioInput adaptation，等待 Core Team 回覆並繼續 fake/harness/fixture | [M1](m1_test_and_audio_baseline.md) |
| M2 | `NOT_STARTED` | VAD/ASR/TTS 隔離候選比較 | [M2](m2_candidate_evaluation.md) |
| M3 | `NOT_STARTED` | Pi 5 真實 M3 Audio HAL 整合 | [M3](m3_real_hardware_integration.md) |
| M4 | `NOT_STARTED` | 組合認證與正式交付 | [M4](m4_combined_validation_and_delivery.md) |

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
- [POC 開發指引](../pm_handoff/audio_poc_development_guide.md)
- [最終繳交清單](../pm_handoff/audio_poc_delivery_checklist.md)
- [M3 Audio 要求](../pm_handoff/core_audio_m3_requirements.md)

## Reference Material (Non-authoritative)

- [M3 Audio 設計修訂提案](../poc/poc_audio_m3_design_changes.md)
- [M4a Audio POC 計畫](../poc/poc_audio_m4_audio_poc_plan.md)
