# Audio POC Milestone Index

本檔是 milestone 狀態的唯一入口。M0 是 readiness gate，M1–M4 是四個正式交付 milestone。
唯一永久開發分支為 `audio`；已完成 gate 以不可移動的 `audio_mN` annotated tag
對應其 exact completion commit，避免與其他團隊 tag 混用。M2A/M2B 是 M2 內部
substages，不建立獨立 milestone tag。

## Current Status

最後更新：2026-08-23

最終交付可達性：`AT_RISK`

M0 readiness 與 M1 frozen baseline 已完成。M2 的 SenseVoice、Matcha 及 Whisper
small Q8 歷史 evidence 均保留原產生時的 disposition 與 immutable tested SHA。
SenseVoice 歷史結果為 `REJECT`；Matcha risk-focused M2 screen 已完成，lifecycle、
network-disabled P12 與 User 10-prompt quality 均通過，列為 M3 TTS finalist；legal
lineage 仍阻擋 redistribution/product adoption 與 final-winner approval，但不阻擋
internal offline POC。依 User 核准範圍不做 allocator/page 級微調。small Q8
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
bounded scorecard 已可在完整限制下對外引用。M2 Gate reviewer 已接受 base Q8 primary、
small Q8 fallback 與 exact recipe，並正式授權 WebRTC 2.0.10 primary、Silero 6.2.1
conditional fallback。WebRTC level 3、300/500 ms padding、start/end recall 95%/90%、
boundary 與 false-start gates 已在任何 real result 前固定。WebRTC 及 triggered Silero
初次 run 後查明 WebRTC engine state/scoring 不符產品語意，且 Silero adapter 漏掉官方
64-sample context；舊 no-go 已撤回，immutable SHA/evidence 保留。User 確認 160 ms
startup mask、500/600 ms capture padding 與 pause-one-utterance 語意後，corrected WebRTC
fixed debounce 不前進；corrected Silero 的 end retention 為 98%、silence/noise activation
為 1/10 分鐘，cleanup 與 thermal 均 bounded。User exact-capture audit 確認低音量句首漏字，
提出 Silero conditional M3 finalist 與 target-mic blocker。

Reviewer 已正式接受 `REQ-AUDIO-M2-GATE-CLOSURE-002`。VAD 的 method correction、Silero 作為 conditional finalist、以及 `M3-ENTRY-LOCK-002` 皆已獲准。M2 標記為 `COMPLETE`。Core 隨後以 `RESP-AUDIO-M3-RISK-FOCUSED-GATES-001` 接受 M3 risk-focused gates 與 packet minimum，授權 POC 準備 exact packet；M3.1 remediation framework 亦獲條件式接受，但只有 M3 發現 evidence-backed blocker 後才可另行啟動。最終交付維持 `AT_RISK`（Matcha legal 與 Silero target-mic start-retention risk 尚未關閉），M3 維持 `PLANNED`。

| Milestone | 狀態 | 摘要 | 文件 |
| --- | --- | --- | --- |
| M0 | `COMPLETE` | Pi worktree SHA/clean check、environment pre-test、SSH、timeout/cancel/cleanup 與 checksum transfer 已通過 | [M0](m0_remote_environment.md) |
| M1 | `COMPLETE` | Option A 實作基準通過 Core ACK-004；100-item fixture、VAD timing labels 與 metrics 已凍結 | [M1](m1_test_and_audio_baseline.md) |
| M2 | `COMPLETE` | ASR/TTS/VAD closure 已獲 reviewer 接受；Silero conditional finalist 與 M3-ENTRY-LOCK-002 生效 | [M2](m2_candidate_evaluation.md) |
| M3 | `PLANNED` | Pi 5/M3 Audio HAL qualification；根據 M3-ENTRY-LOCK-002 準備開始實機驗證 | [M3](m3_real_hardware_integration.md) |
| M4 | `NOT_STARTED` | 20-session combined validation、Gate 2B final reference/conformance kit 與正式交付 | [M4](m4_combined_validation_and_delivery.md) |

## Current M2 substage status

| Substage / parallel track | 狀態 | Exit contribution |
| --- | --- | --- |
| M2A Baseline Survey | `COMPLETE / OBSERVATIONS REVIEWED` | 六個 required rows、單一 scorecard、small Q8/base Q5/medium Q5 shortlist；A/B 40-record supplemental packet 已提交 intake |
| M2B Optimization Feasibility | `COMPLETE / ACCEPTED FOR M3` | Reviewer 接受 base Q8 primary、small Q8 fallback，均為 P0+greedy+固定 prompt；Common Voice +1 edit regression 保留為 trade-off |
| Matcha TTS qualification | `COMPLETE / M3 FINALIST` | lifecycle、P12、10-prompt quality 與 material resource risk 均通過；legal limitation 保留至 redistribution/product/final-winner 決策 |
| VAD scope and evaluation | `COMPLETE / SILERO CONDITIONAL FINALIST` | Corrected Silero start/end retention 78%/98%、silence/noise activation 1/10 分鐘；低音量句首漏字保留為 M3 target-mic blocker，不增加 tuning matrix |

## Core M4a Contract Mapping

| Contract stage | POC milestone disposition |
| --- | --- |
| Contract intake SHA | Gate 1 planning/proposal 與既有 ACK intake 可由 committed SHA 追溯；ACK-003 intake 隨本次 milestone 修正提交 |
| Gate 0：M3 P4 final selection | `PASSED` — Core ACK-004 已接受 Option A 實作基準 |
| Gate 1：planning + initial authorization | `ACCEPTED / SUPERSEDED IN PART` — Gate 1A、ACK-001 與 ACK-002 歷史授權及 evidence 保留；ASR execution order 與 elimination gates 由 ACK-003 取代 |
| M2A：baseline survey | `COMPLETE / REVIEWED` — 六個 required rows 與 exact 8+12 PCM 形成單一 scorecard；shortlist 為 small Q8、base Q5、medium Q5 |
| M2B：optimization feasibility | `ACCEPTED FOR M3` — Reviewer 接受 base Q8 primary、small Q8 fallback 與 prompt recipe；完整 delta/regression 保留，不是 production lock |
| Gate 2A：POC qualification/selection | `COMPLETE FOR M3` — ASR, TTS, VAD 皆已完成評估並指定 M3 finalist；完整 qualified selection 仍待 M3 target/HAL qualification 完成。 |
| Gate 2B：final reference | M4 完成 20 sessions、failure/offline、internal review 與 conformance kit；`POC Accepted` 後 Core 才可固定 final reference |
| Gate 3：Core production implementation | M2A 期間只允許 generic scaffold；M2B reviewed selection 後才可 provisional candidate integration；M4 final handoff 後才可 production lock |

## Open risks and next authorized work

- `NEXT`：User 已核准 `M3-RISK-FOCUSED-QUALIFICATION-TEST-PACKET-001`；runner/local
  validation 已完成並固定 candidate SHA
  `655e80ec4ed287708ed0a47f383b645d88650b18`。`REQ-AUDIO-M3-PACKET-SIGNOFF-001`
  正提交 Core Designer；sign-off 前不得執行 formal M3 hardware qualification。
- `IMPLEMENTATION`：packet machine validator、11-case local fake lifecycle、formal
  HAL/finalist backends、offline namespace enforcement 與 22-result draft summary 已完成；
  portable suite 176 項通過。Core output adaptation 已固定為
  `ff09199583644a8f0822153e371589f52ae821a0`；POC execution SHA 已切定，下一步取得
  Core packet sign-off。
- `CLOSED BLOCKER`：Core 已在 AudioOutput 內完成 16 kHz mono S16_LE → 48 kHz
  stereo S32_LE adaptation；User 接受剩餘 Core test coverage 為非阻塞風險。POC 不增加
  自有 resampler，formal hardware execution 仍等待 packet sign-off。
- `ARTIFACT RECEIVED / CORE ACK PENDING / NON-BLOCKING FOR AUDIO M3`：已收到固定
  `M4B-P9-RESIDENCY-SURROGATE-001`、protocol、source SHA 與 checksum，附件 regression
  6 項通過。等待 Core corrected ACK 後才整合/執行 P9；不阻擋 M3，也不產生 LLM credit。
- `CONTINGENCY`：M3.1 framework 已條件式接受；只有可重現 hard-gate finding、明確
  root-cause evidence 與 Core 事前核准的一個 minimal remediation 同時具備才啟動。
- `RISK`：Silero 在 M2 corrected run 的低音量句首 retention 未達 frozen 95% start gate；
  M3 必須在 pinned target mic/HAL 驗證，必要時只提一個 fixed front-end gain 並檢查
  clipping、silence、impact-noise、ASR 與 cleanup regression，不展開 tuning matrix。
- `RISK`：Matcha risk-focused screen 已通過；`tts-013` 的 `start` 有輕微發音瑕疵，
  User 給 4 分且未判 critical。Legal lineage 仍須在 redistribution、product adoption
  或 Gate 2B final-winner approval 前關閉。
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
