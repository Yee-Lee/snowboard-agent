# Audio POC Milestone Index

本檔是 milestone 狀態的唯一入口。M0 是 readiness gate，M1–M4 是四個正式交付 milestone。
唯一永久開發分支為 `audio`；已完成 gate 以不可移動的 annotated tag 對應其 exact
completion commit。M2A/M2B 是 M2 內部 substages，不建立獨立 milestone tag。

## Current Status

最後更新：2026-08-21

最終交付可達性：`AT_RISK`

M0 readiness 與 M1 frozen baseline 已完成。M2 的 SenseVoice、Matcha 及 Whisper
small Q8 歷史 evidence 均保留原產生時的 disposition 與 immutable tested SHA。
SenseVoice 歷史結果為 `REJECT`；Matcha performance evidence 已取得，但 User quality、
lifecycle、network-disabled、resource growth 與 legal conditions 尚未關閉；small Q8
舊 diagnostic 不構成 formal qualification 或 selection。

Core/User 已於 2026-08-21 接受
[`DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003`](../pm_handoff/DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003.md)。
ACK-003 將 Audio M2 拆成 `M2A Baseline Survey` 與
`M2B Optimization Feasibility`，並取代 ACK-001/ACK-002 的 ASR execution order
與 quality/performance elimination gates。CER、sentence correctness、latency、RTF、
RSS 在 M2A/M2B 改為 comparative observations；歷史 evidence 不回溯重標。

M2A baseline survey 已完成：八個 authorized/optional ASR rows 的 official artifact、
runtime identity、budget 與 deterministic fixture-selection rules 已固定並有本地 validator/
tests。Common Voice 26.0 `zh-TW` CC0-1.0 已由 User-authenticated download 取得，exact
12 source clips 已保存於 Git-ignored controlled evidence，且 sanitized source lock 記錄
member path、size 與逐檔 SHA-256。Pi 上 frozen labels、delivered manifest 與 50 ASR WAV
已傳回並驗證，exact internal eight source lock 亦已固定。Internal 8 以 frozen bounds
連續裁切並保留 pause；Common Voice 12 以 pinned GStreamer/mpg123 runtime 衍生，20 筆
16 kHz mono S16_LE WAV、duration 與 checksum 已鎖定。六個 required candidate rows
已在 Pi 完成 bounded execution，並形成單一 comparative scorecard。Review 選出
small Q8、base Q5、medium Q5 三列 shortlist；沒有下 `PASS`、`FAIL`、winner 或
production baseline 判定。small Q5 與其他反直覺結果均保留兩次 diagnostic recheck，
且 diagnostic 不會混入正式 scorecard。

M2B 只允許 M2A shortlist 進場，且每次 probe 相對 named baseline 只改一個變因；
輸出 primary、fallback、exact recipe 與 benefit/cost/regression delta table，交由
Core/User comparative review。VAD real-engine row 仍未獲授權；ACK-003 只允許以 frozen
labels 比較 endpoint/padding effects，不能取代 VAD finalist/no-go evidence。因此即使
ASR funnel 已有新路徑，最終交付仍維持 `AT_RISK`，M3 不得提前開始。

| Milestone | 狀態 | 摘要 | 文件 |
| --- | --- | --- | --- |
| M0 | `COMPLETE` | Pi worktree SHA/clean check、environment pre-test、SSH、timeout/cancel/cleanup 與 checksum transfer 已通過 | [M0](m0_remote_environment.md) |
| M1 | `COMPLETE` | Option A 實作基準通過 Core ACK-004；100-item fixture、VAD timing labels 與 metrics 已凍結 | [M1](m1_test_and_audio_baseline.md) |
| M2 | `IN_PROGRESS` | M2A scorecard/shortlist 與首個 M2B probe 已 reviewed；C 來源與 PCM 已鎖定、尚未 inference；其餘 M2B、Matcha、VAD 未關閉 | [M2](m2_candidate_evaluation.md) |
| M3 | `NOT_STARTED` | Pi 5/M3 Audio HAL qualification；等待 M2 comparative provisional selection 與完整進場條件 | [M3](m3_real_hardware_integration.md) |
| M4 | `NOT_STARTED` | 20-session combined validation、Gate 2B final reference/conformance kit 與正式交付 | [M4](m4_combined_validation_and_delivery.md) |

## Current M2 substage status

| Substage / parallel track | 狀態 | Exit contribution |
| --- | --- | --- |
| M2A Baseline Survey | `COMPLETE / OBSERVATIONS REVIEWED` | 六個 required rows、單一 scorecard、small Q8/base Q5/medium Q5 shortlist |
| M2B Optimization Feasibility | `IN_PROGRESS / PADDING HOLDOUT PENDING` | Internal dev padding probe 已 reviewed；P300 以微弱混合 delta 單獨進入 P0 對照 holdout，Common Voice 尚未執行 |
| Matcha TTS remaining qualification | `IN_PROGRESS` | User quality、offline、lifecycle、resource growth、legal disposition |
| VAD scope and evaluation | `CHANGE_REQUESTED` | Real VAD finalist 或 evidence-backed no-go；目前未獲 execution row |

## Core M4a Contract Mapping

| Contract stage | POC milestone disposition |
| --- | --- |
| Contract intake SHA | Gate 1 planning/proposal 與既有 ACK intake 可由 committed SHA 追溯；ACK-003 intake 隨本次 milestone 修正提交 |
| Gate 0：M3 P4 final selection | `PASSED` — Core ACK-004 已接受 Option A 實作基準 |
| Gate 1：planning + initial authorization | `ACCEPTED / SUPERSEDED IN PART` — Gate 1A、ACK-001 與 ACK-002 歷史授權及 evidence 保留；ASR execution order 與 elimination gates 由 ACK-003 取代 |
| M2A：baseline survey | `COMPLETE / REVIEWED` — 六個 required rows 與 exact 8+12 PCM 形成單一 scorecard；shortlist 為 small Q8、base Q5、medium Q5 |
| M2B：optimization feasibility | `IN PROGRESS` — 只對 shortlist 做一變因 probes；回傳 primary/fallback proposal 與 exact recipe，不是 production lock |
| Gate 2A：POC qualification/selection | `IN PROGRESS` — 歷史 evidence 保留；須完成 M2A/M2B review、TTS disposition、VAD 路徑與 M3 target/HAL qualification，才能形成 qualified selection |
| Gate 2B：final reference | M4 完成 20 sessions、failure/offline、internal review 與 conformance kit；`POC Accepted` 後 Core 才可固定 final reference |
| Gate 3：Core production implementation | M2A 期間只允許 generic scaffold；M2B reviewed selection 後才可 provisional candidate integration；M4 final handoff 後才可 production lock |

## Open risks and next authorized work

- `NEXT`：base Q8 quantization probe 已完成；依三列 shortlist 繼續最少必要的一變因
  probes，形成 primary/fallback、exact recipe 與完整 delta table。
- `BLOCKER`：目前沒有 ASR fixture、required artifact 或 runtime blocker。
- `RISK`：VAD real-engine execution scope 未獲授權，M2 與最終 VAD baseline/no-go
  仍無關閉路徑。
- `RISK`：Matcha User quality、offline、lifecycle、resource growth 與 legal conditions
  尚未關閉。
- `RISK`：大型/optional rows 可能受 Pi resource 或 schedule 限制；省略必須留下
  evidence-backed reason。
- `RISK`：Vosk upstream source/model 為 Apache-2.0，但官方 0.3.45 aarch64 wheel
  METADATA 標示 license `UNKNOWN` 且未附 notice；完整 dependency closure 已固定，僅供
  internal survey，若進入 shortlist 仍須在再散布或產品採用前完成 legal review。
- `BOUNDARY`：M2A observations 不得標成 PASS/FAIL/winner；歷史 results 不得重標。
- `BOUNDARY`：Artifact mismatch、unknown provenance/license、runtime network access、
  OOM、bounded timeout 或 incomplete cleanup 仍 fail closed 並保留 observation。

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
