# M2：VAD、ASR、TTS 隔離候選比較

狀態：`IN_PROGRESS`

Gate 狀態：`M2A COMPLETE / OBSERVATIONS REVIEWED / THREE-ROW SHORTLIST — M2B IN PROGRESS / MATCHA REMAINING GATES IN PROGRESS / VAD ROW NOT AUTHORIZED`

## 目標

以 M1 frozen fixtures 與共同量測方法完成候選比較，先在 M2A 建立 ASR
landscape scorecard 與二至三列 shortlist，再只對 shortlist 進行 M2B 單變因最佳化，
提出 primary、fallback 與 exact pipeline recipe。TTS 既有 qualification 同步關閉
remaining gates；VAD 必須取得獨立 scope 決定。M2 結果仍須通過 M3/M4，才可能成為
final baseline。

本 milestone 承接
[`DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003`](../pm_handoff/DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003.md)。
Core/User 已於 2026-08-21 接受把 Audio M2 拆成兩個內部 substage：
`M2A Baseline Survey` 與 `M2B Optimization Feasibility`。兩者不建立各自的 milestone
tag；只有整個 M2 的 reviewed outcome 關閉後才能完成 M2。

ACK-003 只取代 ACK-001/ACK-002 的 **ASR execution order** 與
**quality/performance elimination gates**。既有 candidate evidence、artifact identity、
offline boundary、bounded execution、cleanup requirements 與 immutable tested SHA
全部保留；歷史結果維持產生當時的 `PASS`、`FAIL`、`REJECT` 或 diagnostic 標籤，
不得回溯重標。

被部分取代的歷史決策仍可由
[`ACK-001`](../pm_handoff/DELIVERY-AUDIO-POC-M4A-G1B-CANDIDATE-ACK-001.md) 與
[`ACK-002`](../pm_handoff/DELIVERY-AUDIO-POC-M4A-G1B-ASR-RECOVERY-ACK-002.md)
追溯；未關閉的 real VAD execution boundary 由
[`CR-AUDIO-M4A-G1B-VAD-SCOPE-001`](../../poc_audio/deliveries/CR-AUDIO-M4A-G1B-VAD-SCOPE-001.md)
持續追蹤。

## Current control boundary

| 工作流 | 狀態 | 現行邊界 |
| --- | --- | --- |
| M2A ASR baseline survey | `COMPLETE / OBSERVATIONS REVIEWED` | 六個 required rows 已形成單一 scorecard；small Q8、base Q5、medium Q5 為三列 shortlist，沒有 PASS/FAIL/winner 判定 |
| M2B ASR optimization | `IN_PROGRESS / BASE PROMPT REVIEWED` | beam 不保留；base Q8 固定 domain prompt 在 dev 回復目標詞，holdout 無誤插且淨少 1 edit，但一筆一般華語退步；暫列 P0+greedy+prompt primary recipe |
| TTS Matcha qualification | `IN_PROGRESS` | 既有 performance evidence 保留；User quality、lifecycle、network-disabled、resource growth 與 legal conditions 尚未關閉 |
| VAD candidate evaluation | `CHANGE_REQUESTED` | ACK-003 未授權 real VAD engine row；只可用 frozen labels 比較 endpoint/padding，不得 build/load/benchmark Silero、WebRTC VAD 或其他 VAD candidate |

M2A/M2B 的 CER、sentence correctness、latency、RTF 與 RSS 是 trade-off observation
及最終比較評分，不是單項淘汰 gate。Artifact mismatch、unknown provenance/license、
runtime network access、OOM、bounded timeout 或 incomplete cleanup 仍須 fail closed，
並保留實際 observation；它們不得被包裝成 quality rejection。

### M2A authorized ASR rows

所有 row 在第一次 load 前必須固定 exact filename、upstream immutable revision、byte
size、SHA-256、engine/model license/notice 與受控位置。Whisper rows 共用既有
whisper.cpp `1.9.2` CPU-only native aarch64 closure：

| Row | Baseline role |
| --- | --- |
| `asr-whispercpp-small-q8_0-1.9.2` | 既有 reference；保留舊 evidence，只重跑共同 M2A packet 所需比較 |
| `asr-whispercpp-small-q5_1-1.9.2` | small Q8 quantization trade-off |
| `asr-whispercpp-base-q5_1-1.9.2` | low-resource / low-latency reference |
| `asr-whispercpp-medium-q5_0-1.9.2` | higher-capacity quality reference |
| `asr-whispercpp-large-v3-turbo-q5_0-1.9.2` | optional same-cost-class probe；只有記錄 resource 或 schedule 理由才可省略 |

ACK-002 的 Q5 conditional trigger 已移除；small Q5、base Q5、medium Q5 可獨立執行，
不再等待 small Q8 結果。HAT 與 accelerator-specific models 仍在 scope 外。

非 Whisper families 各選一個 exact official representative；只要 family 與 license
boundary 不變，不需再向 Core 逐列 round-trip：

| Family | Authorized representative | Purpose |
| --- | --- | --- |
| sherpa-onnx | 一個 aarch64-compatible int8 streaming bilingual `zh-en` Zipformer 或 Paraformer | streaming 與 code-switch comparison |
| Vosk | `vosk-model-small-cn-0.22` + official native/runtime API | low-resource Pi 與 dynamic-vocabulary potential |
| Qwen3-ASR via sherpa-onnx | `Qwen3-ASR-0.6B` int8 | optional load + minimal inference feasibility；bounded timeout/OOM 即停止 |

PocketSphinx、HAT、cloud APIs 與 unpinned community conversions 不在 scope。Fun-ASR
Nano 或其他大型 runtime 只有在 M2A 證明已授權 families 留下 material capability gap
後，才能另提書面 scope request。

### M2A common low-cost packet

所有 rows 必須使用同一份先提交、後執行的 packet：

1. 八筆事前固定 internal fixtures：Taiwan Mandarin、code-switch、number/date、
   product-term 各兩筆，包含一筆最長 bounded item。
2. 十至十五筆在看到 candidate output 前固定的 Common Voice `zh-TW` clips；記錄
   dataset version、clip IDs、license 與 derived 16 kHz mono PCM checksums。
3. 每筆一次 unscored warm-up、一次 scored inference；不執行 cold matrix、20-run
   repetition、soak 或 full lifecycle campaign。
4. 事前固定 row-level budget 與 per-item timeout。Timeout/OOM 記 observation 並停止
   浪費性執行，不重寫成 quality rejection。
5. 記錄 transcript、normalized CER、exact-sentence diagnostic、number/product-term
   correctness、load time、latency、RTF、peak RSS、disk/runtime identity 與 cleanup。

M2A 只產出一張 comparative scorecard 與二至三列 shortlist。

### M2B optimization feasibility

只有 M2A shortlist 可以進入 M2B。每個 probe 必須相對 named baseline 只改一個變因，
並同時保留 raw 與 adjusted transcript/result identity：

| Track | Authorized probes | Required comparison |
| --- | --- | --- |
| Front-end / endpoint | raw、DC removal、fixed gain、noise suppression、AGC、frozen-label endpoint/padding；signal audit 支持時才可 dereverb | same WAV + same engine/profile；signal metrics、ASR delta、CPU/RSS/latency cost |
| Decoder/runtime | greedy/beam、initial prompt、grammar、dynamic vocabulary/keyword boost、context policy、token suppression、supported native/flash-attention/BLAS | 每列一變因；quality categories + latency/RTF/RSS |
| Number/domain | number/date canonicalization、product alias table、intent/slot parser、engine vocabulary controls | exact numeric/entity value、false correction、unsafe silent correction、latency |
| Recovery | LLM-assisted correction、low-confidence confirmation | 保留 raw transcript，分別評分 corrected value、invented value、clarification outcome |
| External sanity | 重用 frozen Common Voice subset | 偵測 internal product phrases 以外的 overfit/regression |

AEC 與 barge-in 不在 scope。DSP 必須是明確的 `perception/listen` front-end stage，
不得進入 Audio HAL、隱藏 resampling 或改變已接受的 AudioInput stream contract。

M2B 回傳 primary finalist、one fallback、exact pipeline recipe，以及每個保留最佳化的
benefit/cost/regression delta table。Quality/performance metrics 用來排序，但不會單獨
阻止 comparative selection；provisional selection 由 Core/User 決定。

## Historical evidence preserved

- Gate 1A planning、Gate 1B initial proposal 與 shared conformance scaffold 已完成；
  fake success/error/timeout/cancel/force-abort/reopen runner 及 schema evidence 保留。
- SenseVoice 在 Pi SHA `63c2cc179bb3c2525201da0f7a78d2c50b63d759` 的歷史
  qualification 為 core CER 41.629%、overall sentence correctness 6%，並依當時
  frozen gates 標為 `REJECT`；ACK-003 不回溯改寫。
- Matcha 同一 packet 的 first-buffer p95 285.098 ms、RTF p95 0.112776；performance
  gates 當時通過，但 remaining gates 尚未關閉。
- Whisper small Q8 在 Pi SHA `1b29f685de64970f6abbc12a0820a2ef4ec0a444` 的兩次
  partial diagnostic 為 core CER 9.502262%、sentence correctness 28%、hot p95
  11.080 s、RTF p95 1.831987、peak RSS 554 MiB；此 packet 仍是 gate-ineligible
  historical diagnostic，未完成的 20-repetition run 不會補標成 formal evidence。
- `POC-AUDIO-PERF-2026-001` 的 bounded/native evidence 位於 Pi SHA
  `fd51a4f36da61fa9af7e210c7dec0170b0cffcbc`：50 fixtures x 2 hot cycles 的
  latency p50/p95 4.042/4.139 s、RTF p50/p95 1.307/1.933、peak RSS
  555.438 MiB、overall sentence correctness 34%。small Q8 依當時 rules 未 advance；
  ACK-003 只要求它為共同 M2A packet 重跑可比較的一次 scored inference。

完整 sanitized historical evidence 分別見
[`M4A-G1B-WP3-FULL-QUALIFICATION-001`](../../poc_audio/evidence/m2/M4A-G1B-WP3-FULL-QUALIFICATION-001.md)、
[`M4A-G1B-ASR-RECOVERY-Q8-PARTIAL-001`](../../poc_audio/evidence/m2/M4A-G1B-ASR-RECOVERY-Q8-PARTIAL-001.md)
與 [`POC-AUDIO-PERF-2026-001`](../../poc_audio/evidence/m2/POC-AUDIO-PERF-2026-001/README.md)。

## 對最終交付的貢獻

- 完整 candidate manifest、license/checksum/source、成功與中止結果。
- M2A comparative scorecard、shortlist reasoning 與 external sanity subset。
- M2B primary/fallback proposal、exact recipe 與單變因 optimization delta table。
- TTS remaining qualification，以及 VAD scope/finalist 或 evidence-backed no-go 路徑。
- M4a authorization、M4A-P2/P3/P6/P10/P11/P12 preliminary evidence 與 M3 重測範圍。

## 受控執行順序

1. **ACK-003 intake**：`COMPLETE`；M2A/M2B 邊界、歷史 evidence preservation 與
   Core implementation release boundary 已記入 milestone。
2. **M2A packet**：`COMPLETE`；八個 rows 的 official
   artifact/runtime identities、row/item budgets、schema、validator、tests 與 deterministic
   selector 已準備。Common Voice 26.0 `zh-TW` CC0-1.0 exact 12 source clips 已取得，
   sanitized source lock 已記錄 member path、size 與逐檔 SHA-256。Pi 上 frozen labels、
   delivered manifest 與 50 ASR WAV 已傳回驗證，internal exact eight source lock 已固定。
   Derived 8+12 PCM、conversion runtime、duration、checksums 與 sanitized exact index
   已鎖定；六個 required rows 已完成 exact artifact/runtime preflight 與執行，兩個
   optional rows 以 resource/scope 理由省略。
3. **M2A execution/scorecard**：`COMPLETE / REVIEWED`；共同 packet scorecard 與
   small Q8、base Q5、medium Q5 shortlist 已記錄，不下 PASS/FAIL/winner 判定。詳見
   [`M4A-M2A-COMPARATIVE-SCORECARD-001`](../../poc_audio/evidence/m2/M4A-M2A-COMPARATIVE-SCORECARD-001.md)。
4. **M2B optimization**：`IN_PROGRESS / C DEV PROBES REVIEWED`；首個量化 probe 已
   reviewed。C 已事前確認 16 筆 Internal 與 8 筆 Common Voice，dev/holdout 各 12
   筆且與 M2A 無 fixture/speaker 重疊；Pi exact SHA 已分開建立 Internal
   P0/P300/P500 與 Common Voice full-clip PCM lock。Internal padding、Common Voice
   dev baseline、base Q8 beam=3/5 probes 已執行；base 保留 P0+greedy，holdout 仍封存。
   下一步只對 shortlist 繼續一變因 probes，完成 primary、fallback、recipe
   與 delta table，送 Core/User comparative review。詳見
   [`M2B-C-SOURCE-SELECTION-001`](../../poc_audio/deliveries/M2B-C-SOURCE-SELECTION-001.md)。
5. **Parallel TTS/VAD closure**：Matcha remaining gates 持續；real VAD row 等待獨立
   scope ACK，不能以 frozen-label endpoint simulation 取代。
6. **M2 gate review**：只在 M2A/M2B reviewed outcome、TTS disposition、VAD
   finalist/no-go 路徑與 M3 target scope 都可由 committed SHA 追溯時進行。

M2A 進行期間，Core 只可處理 generic ASR protocol、fake adapter、schema、runner 與
config placeholder。只有 M2B reviewed selection 後，才可作 named primary/fallback
candidate-specific provisional integration；production dependency lock 必須等 Audio M4
`POC Accepted` final handoff。

## Entry Conditions

- M1 exit gate 已通過，fixtures 與既有量測定義已凍結。
- M4a Gate 0、Gate 1A、initial Gate 1B 與 shared conformance scaffold 已完成。
- ACK-003 已書面授權 M2A rows 與 M2B probe categories。
- PM relay/ACK path、Core decision owner 與敏感 fixture 受控位置可用。
- 每個 row 在 first load 前仍須完成 exact identity/provenance/license preflight。
- Common Voice exact 12 與 internal exact 8 的 source identities、derived PCM、runtime 與
  checksums 已鎖定；每個 row 仍須在 first load 前通過 artifact/runtime/license preflight。

## Exit Gate

- M2A 所有實際執行 rows 有完整 identity、command、bounded observation、cleanup proof
  與單一 comparative scorecard；optional row 的省略理由已記錄。
- M2A 已提出二至三列 shortlist，沒有使用單項 threshold 作 PASS/FAIL 或 winner 標籤。
- M2B 只對 shortlist 完成一變因比較，並提出 primary、fallback、exact recipe 與
  benefit/cost/regression delta table。
- Core/User 已 review comparative provisional selection；未宣稱 production lock。
- TTS candidate 有明確 finalist/no-go disposition，且 User quality、offline、lifecycle、
  resource 與 legal conditions 有 evidence 或 blocking risk。
- VAD 有已授權 finalist/no-go 路徑；在 ACK-003 未授權 real VAD row 的現況下，此項仍
  未滿足，M2 不得完成。
- M3 real Pi/HAL 重測範圍、fixtures、artifact identities 與必要 M4A preliminary/pending
  traceability 可由 committed full SHA 定位。

## 必要 Evidence

- ACK-003 intake、branch 與完整 40-character SHA。
- Exact artifact/runtime identities、fixture/Common Voice index、license、commands、
  row/item budgets 與受控 artifact locations。
- M2A scorecard、M2B optimization delta table、primary/fallback proposal 與 known risks。
- Sanitized per-run results、timeout/OOM/error records、offline boundary 與 cleanup proof。
- TTS User review/remaining disposition、VAD scope decision 與 M4A-P1–P12 traceability。
- 模型、large results、private audio、raw sensitive transcripts 均留在 Git 外，只提交
  checksum 與受控位置。

## 不做的工作

- 不建立 M2A/M2B milestone tag，也不默認開始 M3。
- 不接 product composition root、RM、SM、AEC、barge-in、HAT 或 cloud API。
- 不 build/load/benchmark 尚未另行授權的 real VAD candidate。
- 不把 M2A observations 標成 PASS/FAIL/winner，不回溯改寫舊 evidence。
- 不在 Audio HAL 放入 DSP，不作 hidden resampling。
- 不把開發機結果當 Pi 5 或 M3 HAL 驗收。

## 調整觸發點

- Artifact/license/provenance 無法固定、runtime 需連網、OOM/timeout 無法 bounded，或
  cleanup proof 不完整。
- M2A 已授權 families 仍留下 material capability gap，需要 Fun-ASR Nano 或其他
  large runtime 的新 scope decision。
- M2B probe 改變 candidate identity、family/license boundary 或超出一變因設計。
- VAD execution scope 持續未決，使 final VAD baseline/no-go 無法交付。
- Matcha User quality、offline、lifecycle、resource 或 legal blocker 無法關閉。
- Pi 5 資源預估明顯無法支撐 M4 同時常駐。

## Gate Review 問題

M2 結束時必須回答：M2A landscape、M2B recipe、TTS disposition 與 VAD 路徑，是否讓
primary/fallback 在 pinned M3 HAL、真實 mic/speaker 與三模型同時常駐下仍有合理的
最終交付路徑？M2A score 高不等於 Gate 2A selection，單項 demo 成功也不構成 advance。
