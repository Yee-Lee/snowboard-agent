# Audio POC Milestone Index

本檔是 milestone 狀態的唯一入口。M0 是 readiness gate，M1–M4 是四個正式交付 milestone。
唯一永久開發分支為 `audio`；已完成 gate 以不可移動的 annotated tag 對應其 exact
completion commit。M2A/M2B 是 M2 內部 substages，不建立獨立 milestone tag。

## Current Status

最後更新：2026-08-23

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

後續 A/B grouping handoff 已從 immutable small Q8 與 base Q8 sanitized formal rows
完成 40-record 可重算 packet，沒有新 inference 或 retrospective filtering。small Q8
在 B 相對 A 的整句率增加 50 percentage points、CER 改善 16.952227 points；base Q8
整句率無 A/B gap、CER 改善 3.675334 points。A 的 exact outcomes 集中在兩筆一般
Taiwan Mandarin，domain categories 皆未 exact；這只形成 domain-handling 假設，不宣稱
語料、講者或錄音品質因果，也不改 M2A frozen scorecard/shortlist。

M2B 只允許 M2A shortlist 進場，且每次 probe 相對 named baseline 只改一個變因；
輸出 primary、fallback、exact recipe 與 benefit/cost/regression delta table，交由
Core/User comparative review。C-v1 formal task-adjusted scoring 已在 Pi 完成，raw CER
保留；固定 prompt 改善 Internal，但兩個模型的 Common Voice adjusted edits 均增加 1，
此 external regression 不隱藏。User audio review 發現一筆 frozen reference mismatch；
append-only erratum 已套用且原始 evidence 保留。24 筆 blind-first audit 已完成：23 筆
label confirmed、1 筆 erratum，無 audio-quality、speaker-slip 或 pending findings；
bounded scorecard 已可在完整限制下對外引用。User 已選定 WebRTC 2.0.10 primary、
Silero 6.2.1 conditional fallback；但 Core ACK、exact WebRTC/endpoint profile 與
aggregate start/end recall gate 尚未固定，故 real-engine execution hold 仍有效。
ACK-003 的 frozen-label endpoint/padding 比較不能取代 VAD finalist/no-go evidence。
因此即使 ASR funnel 已有新路徑，最終交付仍維持 `AT_RISK`，M3 不得提前開始。

| Milestone | 狀態 | 摘要 | 文件 |
| --- | --- | --- | --- |
| M0 | `COMPLETE` | Pi worktree SHA/clean check、environment pre-test、SSH、timeout/cancel/cleanup 與 checksum transfer 已通過 | [M0](m0_remote_environment.md) |
| M1 | `COMPLETE` | Option A 實作基準通過 Core ACK-004；100-item fixture、VAD timing labels 與 metrics 已凍結 | [M1](m1_test_and_audio_baseline.md) |
| M2 | `IN_PROGRESS` | M2A 已 reviewed；M2B ASR primary/fallback、C dev/holdout 與 exact recipe 已送 gate review，Matcha、VAD 仍未關閉 | [M2](m2_candidate_evaluation.md) |
| M3 | `NOT_STARTED` | Pi 5/M3 Audio HAL qualification；等待 M2 comparative provisional selection 與完整進場條件 | [M3](m3_real_hardware_integration.md) |
| M4 | `NOT_STARTED` | 20-session combined validation、Gate 2B final reference/conformance kit 與正式交付 | [M4](m4_combined_validation_and_delivery.md) |

## Current M2 substage status

| Substage / parallel track | 狀態 | Exit contribution |
| --- | --- | --- |
| M2A Baseline Survey | `COMPLETE / OBSERVATIONS REVIEWED` | 六個 required rows、單一 scorecard、small Q8/base Q5/medium Q5 shortlist；A/B 40-record supplemental packet 已提交 intake |
| M2B Optimization Feasibility | `GATE_REVIEW / SCORECARD REVIEWED` | base Q8 primary、small Q8 fallback 均為 P0+greedy+固定 prompt；24-item audit、erratum-corrected raw/adjusted scorecard、RTF 與 exact recipe 已齊，可在 bounded scope 下引用 |
| Matcha TTS remaining qualification | `IN_PROGRESS` | User quality、offline、lifecycle、resource growth、legal disposition |
| VAD scope and evaluation | `CHANGE_REQUESTED` | User primary/fallback strategy 已記錄；Core ACK、exact profile 與 recall gate 尚待補齊，未獲 execution row |

## Core M4a Contract Mapping

| Contract stage | POC milestone disposition |
| --- | --- |
| Contract intake SHA | Gate 1 planning/proposal 與既有 ACK intake 可由 committed SHA 追溯；ACK-003 intake 隨本次 milestone 修正提交 |
| Gate 0：M3 P4 final selection | `PASSED` — Core ACK-004 已接受 Option A 實作基準 |
| Gate 1：planning + initial authorization | `ACCEPTED / SUPERSEDED IN PART` — Gate 1A、ACK-001 與 ACK-002 歷史授權及 evidence 保留；ASR execution order 與 elimination gates 由 ACK-003 取代 |
| M2A：baseline survey | `COMPLETE / REVIEWED` — 六個 required rows 與 exact 8+12 PCM 形成單一 scorecard；shortlist 為 small Q8、base Q5、medium Q5 |
| M2B：optimization feasibility | `GATE REVIEW` — base Q8 primary、small Q8 fallback、prompt recipe 與完整 delta/regression 已提出；不是 production lock |
| Gate 2A：POC qualification/selection | `IN PROGRESS` — 歷史 evidence 保留；須完成 M2A/M2B review、TTS disposition、VAD 路徑與 M3 target/HAL qualification，才能形成 qualified selection |
| Gate 2B：final reference | M4 完成 20 sessions、failure/offline、internal review 與 conformance kit；`POC Accepted` 後 Core 才可固定 final reference |
| Gate 3：Core production implementation | M2A 期間只允許 generic scaffold；M2B reviewed selection 後才可 provisional candidate integration；M4 final handoff 後才可 production lock |

## Open risks and next authorized work

- `NEXT`：ASR M2B execution matrix 已停止；Core/User review base Q8 primary、small Q8
  fallback、exact prompt recipe、formal bounded C-v1 task-scoring boundary，以及保留
  Common Voice prompt regression 的完整 delta table。
- `BLOCKER`：目前沒有 ASR fixture、required artifact 或 runtime blocker。
- `RISK`：VAD User strategy 已記錄，但 Core ACK、exact WebRTC/endpoint profile 與
  aggregate start/end recall gate 未關閉；real-engine execution 仍未獲完整授權。
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
