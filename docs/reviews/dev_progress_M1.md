# Audio POC Developer Progress — M1

本文件由 Developer 維護，用於追蹤 Audio POC M1 工作包、相依、實測交接與完成證據。Designer 於 2026-08-13 依 `DELIVERY-AUDIO-POC-M3-VALIDATION-001` 排定本版工作。

## Current disposition

- Milestone：M1 `CHANGE_REQUESTED`
- 最終交付可達性：`AT_RISK`
- 最新已提交基線：`4b49374b7b5133ce4dd88d23e2c6e04bbff851d4`（40-item fixture Pilot）
- P1：`FAIL`；P2：`PASS`
- Option A：Core Designer 已接受責任邊界，但 implementation selection 尚未核准。
- M2、M3、M4：`NOT_STARTED`
- 下一個獲准工作：P4 implementation validation 與 Formal 60-item fixture completion。

本計畫推進最終繳交清單第 2、4、5、8 節。它不授權修改 Core production source，也不代表 POC 已進入 M3。

## Planning rules

1. POC 只建立探索 runner、deterministic fixtures、tests 與 evidence package；不得把 POC harness 當成產品 backend。
2. 正式硬體 evidence 只能來自 clean Pi checkout 的完整 40-character SHA。Developer 先完成 local tests，Tester 不在同一 evidence run 修改 source。
3. Direct audio test 只使用 ALSA `hw:`，不得以 `plughw:` 隱藏 conversion。
4. `pyalsaaudio==0.11.0` 與 `samplerate==0.2.4` 是起始候選，不是核准 dependency；必須保存版本、source hash、license、runtime identity 與 rejected alternatives。
5. Hardware 結果經 evidence review 後才可標記 `PASS`、`FAIL` 或 `INCONCLUSIVE`；試聽或口頭結果不構成 pass。
6. Raw PCM、私有音訊、大型結果、operator endpoint/account/path、credential 與 binary artifact 不進 Git。
7. Formal latency/resource 量測期間不得同時執行 pre-test、fixture recording 或其他占用 audio device 的工作。

估點口徑：1 SP 約為經驗開發者半天，包含實作、聚焦測試與必要文件。以下為 **38 SP** 規劃基線，約 19 個 Developer 人日；不含硬體操作、Tester/Core review 等待及候選失敗後的替代方案。

## Work package overview

| 工作包 | SP | 主要交付 | 對應 | 相依 | Owner | 狀態 |
| --- | ---: | --- | --- | --- | --- | --- |
| **WP-M1-P4-01** Validation skeleton | 3 | runner/fixture/evidence 目錄、manifest schema、P4 test packet、sanitized config、reproduction command | A01–A10 | Active handoff | Developer | `PLANNED / NEXT` |
| **WP-M1-P4-02** Candidate provenance/build | 4 | source hash、license、dependencies、clean build/install、runtime identity及可重現 failure | A10 | P4-01 | Developer + Tester | `PLANNED` |
| **WP-M1-P4-03** Streaming conversion | 6 | channel policy、valid-bit seam、stateful anti-alias 48→16 kHz、saturating S16、不規則 chunk state/flush | A03–A05 | P4-01、02 | Developer | `PLANNED` |
| **WP-M1-P4-04** Async/lifecycle runner | 5 | heartbeat、bounded ownership、aclose/cancel/failure/idempotent stop、10次reopen及cleanup proof | A06–A07 | P4-03 | Developer | `PLANNED` |
| **WP-M1-P4-05** Target native/valid bits | 4 | Pi direct open、realized format、wiring attestation、known-signal/raw analysis、channel與有效位元mapping | A01–A02 | P4-01、02、clean SHA | Tester + User | `PLANNED` |
| **WP-M1-P4-06** Buffer/xrun/resources | 5 | period/buffer、5分鐘shared-clock run、xrun、10次warm-up、latency、CPU/RSS/temp/throttling | A08–A09 | P4-03～05、clean SHA | Tester | `PLANNED` |
| **WP-M1-P4-07** Return delivery | 3 | A01–A10 disposition、evidence index、七項technical recommendation、完整SHA | P4 return | P4-01～06 | Developer + Tester | `PLANNED` |
| **WP-M1-FIX-01** Formal acquisition | 2 | exact-SHA Pi錄製剩餘60 clips、immutable native WAV、local manifest及verify | 100-item gate | Pilot PASS、hardware slot | Tester + User | `PLANNED` |
| **WP-M1-FIX-02** Fixture review | 3 | native/delivered checksum/metadata、50 ASR references、VAD labels、600秒silence/noise、catalog/metrics review | Frozen gate | FIX-01、P4-03 | Developer + Tester + Designer | `PLANNED` |
| **WP-M1-GATE-01** M1 gate review | 3 | regression、exact-SHA reproduction、Core final ACK、frozen decision、risk/status更新 | M1 exit | P4-07、FIX-02、Core ACK | Designer + Tester | `PLANNED` |
| **合計** | **38** | | | | | |

## Execution order

### Phase 0 — Planning checkpoint

1. 將目前 handoff/status 文件整理為一個可 review 的工作段。
2. Implementation 前清除無關 dirty changes；目前 working tree 不可作為硬體 evidence baseline。
3. 確認 active handoff、目錄與 Test ID 後開始 P4-01。

### Phase 1 — Local and deterministic development

1. **P4-01**：固定 A01–A10 traceability、manifest fields、commands、result states與cleanup counters。
2. **P4-02**：完成候選 provenance；clean target build 前不得宣稱 A10 pass。
3. **P4-03**：使用 deterministic 1 kHz、12 kHz、silence、impulse、clipping及不規則chunks驗證conversion。
4. **P4-04**：加入heartbeat與lifecycle/failure tests，證明conversion/partial-frame state每次reset。
5. 完成聚焦測試與既有M1 regression後建立milestone commit，取得唯一完整SHA。

Phase 1 exit：

- alias attenuation至少40 dB，raw calculation可重現；
- steady-state每次yield 320 samples / 640 bytes；
- no wrap、no sample dropping、no per-chunk converter rebuild；
- cancel/failure/reopen後task/thread/fd/ALSA-owner counters為零；
- runner、fixtures、config與manifest皆可由exact SHA定位。

### Phase 2 — Pi hardware sessions

每個session前執行 `environment_pre_test.sh`，確認Pi worktree clean且等於指定SHA。正式量測開始後不再執行會干擾audio/CPU/device的工具。

#### Session A — Functional/native validation

- 執行 **P4-05**：A01 direct `hw:` open與A02 known-signal valid-bit analysis。
- 在Pi重跑conversion、heartbeat、cancel/failure/reopen。
- Native format或valid-bit evidence不符時標記`FAIL`或`INCONCLUSIVE`，不得調整gate。

#### Session B — Endurance/resource validation

- 執行 **P4-06**：固定period/buffer/blocking model，完成至少5分鐘capture adaptation及shared-clock playback。
- 保存xrun、latency raw/P50/P95/max、CPU、RSS、temperature、throttling與heartbeat worst gap。
- 每條failure/cancel與正常結束都執行cleanup check。

#### Session C — Formal fixture completion

- 與resource session分開執行 **FIX-01**，收集剩餘60 clips。
- 保留native 48 kHz/stereo/S32_LE source與checksum；monitor-gain WAV或`plughw:`輸出不得取代immutable source。
- 執行 `--verify --stage formal`；raw audio留在Git-ignored受控位置。

Phase 2 exit：

- A01–A10每項都有status、command、raw evidence path與cleanup result；
- Formal set達100 unique IDs、50 ASR references、600秒silence/noise；
- operator資料、raw PCM與binary wheel/so均未進Git。

### Phase 3 — Review and return

1. **FIX-02**：套用已驗證的valid-bit/conversion policy，完成transformed metadata/checksum、labels/references與metric review。
2. **P4-07**：完成binding、resampler、valid-bit、buffering、async I/O、deployment與residual-risk recommendation。
3. Tester從clean checkout重跑指定packet；Developer不在該evidence run修改source。
4. 回交 `DELIVERY-AUDIO-POC-M3-OPTION-A-VALIDATION-001.md`及完整SHA。
5. 等待Core final selection ACK；POC自驗不得直接解除Core exact-SHA acceptance。
6. **GATE-01**：更新milestone index、remaining-delivery、risks與必要adjustment request；所有M1 exit conditions關閉後才可評估M2 entry。

## Completion gates

### P4

- A01–A10無缺項；未執行標`Pending`、環境不足標`Blocked`、證據不足標`INCONCLUSIVE`。
- Candidate exact version、source SHA-256、license/notice、build command與runtime identity完整。
- Valid-bit mapping由wiring、known signal及raw analysis共同支持。
- Filter state跨不規則chunk保存；flush/startup/partial-output semantics明確。
- Async model不busy-poll；至少10次reopen及所有failure/cancel path無殘留。
- 回交SHA可重建source、tests、文件與sanitized evidence index。

### Formal fixture

- 100 expected files、unique IDs、native/delivered SHA-256及格式/時長metadata齊全。
- 50 ASR references、VAD speech/pause labels、至少600秒silence/noise完成。
- Internal-only授權仍有效；raw audio不進Git。
- `metrics_v1.md`在任何real candidate result揭露前完成Designer/Tester freeze。

### M1 exit

- P4回交經Core final selection ACK關閉implementation selection gate。
- Fixture catalog、authorization/checksum、labels與metrics均為`FROZEN`。
- Harness/fake、native capability、P4 conversion與cleanup evidence可由固定SHA重現。
- M2可使用相同固定WAV/text、metrics、threads、warm-up及量測方式。
- Milestone index仍是唯一狀態入口，不得只更新本文件後宣告M1完成。

## Risks and re-estimation

| 風險 | 緩解/動作 |
| --- | --- |
| 候選無法clean Pi build或license不可接受 | 保存failure與hash；提出替代binding/resampler，不直接加入production lock |
| Valid-bit alignment不確定 | A02維持`INCONCLUSIVE`，不依datasheet猜測 |
| Native call無法可靠cancel | 使用bounded owner與join/close proof；無界阻塞候選淘汰或提出替代 |
| Shared-clock長跑xrun或資源累積 | 保存raw時間序列與root cause；改參數視為新run並完整重測 |
| P4與Formal競用硬體 | 分成Session A/B/C，不在resource run錄音或執行pre-test |
| 等待Core final ACK | M1維持`CHANGE_REQUESTED / AT_RISK`，必要時提出調整請求 |

以下情況必須重估：替代候選增加超過3 SP；valid-bit需要新硬體或driver變更；40 dB alias、exact framing、async或cleanup無候選可達；Formal需重新授權/重錄Pilot；硬體或Core時程使最終delivery不可達。

## Progress log

### 2026-08-13 — Designer scheduling

- ACK-002已接受Option A方向；implementation selection仍待P4與Core final ACK。
- P4-A01至P4-A10列為POC action，完成前阻擋Core Audio real backend。
- 40-item Pilot維持`PASS`；Formal剩餘60 clips與catalog/labels/metrics review未完成。
- 本次只完成工作拆包；尚未開始P4 implementation或新的Pi evidence run。
- Handoff/status整理尚未形成新commit；不得以目前working tree作正式硬體baseline。
