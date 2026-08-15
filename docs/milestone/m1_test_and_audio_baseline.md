# M1：共同測試基線與 co-I2S Capability

狀態：`CHANGE_REQUESTED`

Frozen-gate decision record：[M1 Frozen-Gate Draft](m1_frozen_gates_draft.md)
（狀態為 `DESIGNER_APPROVED / NOT FROZEN`；真實 candidate run 尚未獲准。）

Developer progress：[Audio POC Developer Progress — M1](../reviews/dev_progress_M1.md)
（P4、Formal 60-item fixture 與 M1 gate review 的工作拆包及執行順序。）

受控例外：[CR-M1-PILOT-PREFLIGHT-001](../../poc_audio/deliveries/CR-M1-PILOT-PREFLIGHT-001.md)
允許以已完成的 40-item Pilot 進行 ASR input/runtime `OBSERVATION` preflight；
它不是 candidate comparison，且不改變 M1/M2 gate。

Core-team handoff：[Audio M3 Contract v1](../../poc_audio/deliveries/audio_m3_contract_v1.0.md)
（核心 M3 的設計輸入；不是 POC M3 integration baseline。）

Current hardware finding：[M1 Native Audio Evidence](../../poc_audio/evidence/m1/M1-NATIVE-AUDIO-001.md)
— P1 `FAIL`, P2 `PASS`; proposed resolution：[CR-AUDIO-M3-PCM-001](../../poc_audio/deliveries/CR-AUDIO-M3-PCM-001.md)。

Current harness finding：[M1 Deterministic Fake Evidence](../../poc_audio/evidence/m1/M1-FAKE-001.md)
— exact-SHA workstation and Pi reproduction `PASS`; all five lifecycle paths
returned zero cleanup counters.

Current fixture-recorder finding：[M1 Fixture Recorder Evidence](../../poc_audio/evidence/m1/M1-FIXTURE-RECORDER-001.md)
— exact-SHA Pi dry run `PASS`; explicit authorization guard, 100-item plan,
and no-WAV safety boundary verified. No fixture audio has been recorded.

Current two-stage finding：[M1 Fixture Stage Evidence](../../poc_audio/evidence/m1/M1-FIXTURE-STAGE-001.md)
— exact-SHA Pi dry run `PASS`; Pilot selects 40 items and Formal selects the
remaining 60 without lowering the 100-item formal gate.

Current Pilot pre-recording finding：[M1 Pilot Pre-recording Evidence](../../poc_audio/evidence/m1/M1-FIXTURE-PILOT-000.md)
— native capture channel 0 is usable and channel 1 silence is expected from
the L/R wiring; raw replay audibility is `INCONCLUSIVE` and required the
controlled monitoring diagnostic below.

Current monitoring finding：[M1 Fixture Monitoring Evidence](../../poc_audio/evidence/m1/M1-FIXTURE-MONITOR-001.md)
— temporary +12 dB dual-mono monitoring `PASS` with zero clipping; Pilot may
resume with immutable raw capture. Background noise and playback-stop transient
remain recorded observations for Formal fixture and M3 AudioOutput review.

Current Pilot collection finding：[M1 Fixture Pilot Evidence](../../poc_audio/evidence/m1/M1-FIXTURE-PILOT-001.md)
— 40 / 40 native files, labels, checksum/metadata, representative human review,
and cleanup `PASS`. Formal completion remains required before freezing.

Current Formal collection finding：[M1 Formal Fixture Evidence](../../poc_audio/evidence/m1/M1-FIXTURE-FORMAL-001.md)
— the remaining 60 clips complete a native 100-item set with 50 ASR references,
600 seconds of non-speech, checksums and cleanup `PASS`; delivered-format/catalog
and metric freeze review remain required.

Current Formal fixture review：[M1 Formal Fixture Sampling](../../poc_audio/evidence/m1/M1-FIXTURE-FORMAL-SAMPLING-001.md)
— exact 60-item complement technical review and User/Designer 10 / 10 speech
listening sample are `PASS WITH OBSERVATION`; seven isolated near-full-scale
source samples remain a non-blocking review observation.

Core design-correction delivery：[DELIVERY-AUDIO-POC-M3-DESIGN-CORRECTION-001](../../poc_audio/deliveries/DELIVERY-AUDIO-POC-M3-DESIGN-CORRECTION-001.md)
（User/Designer 已批准 Option A；Core Designer 已接受方向，仍須完成 P4。）

Core direction decision：[DELIVERY-AUDIO-POC-M3-ACK-002](../pm_handoff/history/DELIVERY-AUDIO-POC-M3-ACK-002.md)
— Option A responsibility boundary accepted; binding、resampler、valid-bit
mapping、buffering 與 async I/O 尚未獲准。

Core validation requirement：[DELIVERY-AUDIO-POC-M3-VALIDATION-001](../pm_handoff/history/DELIVERY-AUDIO-POC-M3-VALIDATION-001.md)
（P4-A01 至 P4-A10、decision table、manifest 與 reproducible evidence 要求已全數滿足並結案歸檔。）

Latest P4 live evidence：[P4 A06–A09](../../poc_audio/evidence/m3_option_a/P4-A06-A09-001.md)
— async/lifecycle/endurance/resource evidence at
`55085162fbcdbb027f0958e945918874e5df6828` is `PASS`.

Latest P4 clean-build evidence：[P4 A10 rerun](../../poc_audio/evidence/m3_option_a/P4-A10-RERUN-002.md)
— Core-approved Option 2 replay at
`de3b0bab4daaf47f62956d4b27f6697b3d4fa823` is `PASS`; the reproducibility
[request](../../poc_audio/deliveries/CR-AUDIO-M3-P4-REPRO-002.md) is closed.

Core Final Selection ACK：[DELIVERY-AUDIO-POC-M3-P4-ACK-004](../pm_handoff/DELIVERY-AUDIO-POC-M3-P4-ACK-004.md)
— Core Designer 已審查完整 [P4 return packet](../../poc_audio/deliveries/DELIVERY-AUDIO-POC-M3-OPTION-A-VALIDATION-001.md)
並正式發出 `ACCEPTED — M3 AUDIO REAL PACKAGE MAY START`；Option A 實作基準正式核准，
M4a Gate 0 已解除。歷史中介收件確認見 [ACK-003](../pm_handoff/history/DELIVERY-AUDIO-POC-M3-P4-ACK-003.md)。

Active Core M4a contract：[DELIVERY-AUDIO-POC-M4A-CONTRACT-001](../pm_handoff/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md)
— 本 contract Gate 0 已由 Core ACK-004 通過；待 POC 提交 ASR/TTS 候選清單申請 Gate 1 授權。

## 目標

在執行真實候選前凍結比較方法與 gate，並把既有 co-I2S 實驗轉為可重現的硬體 capability 基線。M1 結束後，候選比較不能因偏好某候選而改變規則。

## 對最終交付的貢獻

- 建立 lockfile、harness、result schema、fixture catalog、candidate manifest 與 deterministic fake。
- 建立 success、timeout、error、cancel、force-abort、orphan cleanup 的共同證據方法。
- 確認目標 INMP441/MAX98357A、shared-clock、PCM 與 device lifecycle 的已知能力和限制。

## 工作大綱

- 決定 repo/evidence/delivery 的實際目錄與可重現命令。
- 定義最小 VAD、ASR、TTS adapter/lifecycle 契約。
- 凍結 metric 定義、warm-up、repetitions、threads、cold/hot 與品質/資源 gate。
- 建 fixture catalog 與敏感資料政策。
- 建 deterministic fake，先驗證 harness 的 success/failure/cancel/cleanup。
- 對 commit `6e85ecce2738a7041c3ba7dc1d5f0944ecf1fc6c` 及後續腳本做可沿用性盤點。
- 在目標 Pi 重新量測 `hw:` capability；將 `plughw:` 自動轉換列為明確變因。
- 驗證 input/output 個別 start/stop/reopen、sequential 不同 rate，以及 shared-clock concurrent capability。
- 明確記錄半雙工產品路徑與同時錄放 capability 的邊界；不擴張為 AEC/barge-in。
- 取得合法 mic WAV fixture 與 metadata/checksum。

## Entry Conditions

- M0 exit gate 通過。
- Designer/Tester 或被授權的對應角色可凍結 gate。
- 目標 Pi、mic、speaker、接線與預期外殼資訊可取得。

## Exit Gate

- 可重現環境、schema、fixture catalog、manifest 與 fake baseline 完成。
- 所有 gate 在真實候選結果揭露前固定並記錄決策者。
- Harness 能正確觀察 timeout、cancel、force-abort 與 cleanup。
- co-I2S capability matrix、格式轉換位置、shared-clock 限制與 lifecycle evidence 完成。
- M2 可在相同固定 WAV/text 和量測方法下公平執行。
- M3 所需的 M3 HAL SHA/交付來源已有 owner 與取得路徑；若尚未交付，明確列為依賴風險。

## 目前 Blocking 與非 Blocking 依賴

Blocking M1 exit / M2 candidate entry：

- Formal native acquisition、exact-complement technical review 與分層人工聽檢已完成；
  完成 delivered-format checksum/metadata、normalization/label、catalog 與 metric
  definition review，使 frozen gate 可標為 `FROZEN` 並執行 M1 exit review。
- 將 `DELIVERY-AUDIO-POC-M4A-CONTRACT-001`、`DELIVERY-AUDIO-POC-M3-P4-ACK-004`
  與本 milestone 規劃一併納入 reviewable exact SHA，由 PM 回覆 POC intake SHA。

已核准的受控開發例外：

- 40-item Pilot 可依 `CR-M1-PILOT-PREFLIGHT-001` 用於診斷性的 ASR preflight，
  驗證 native-to-ASR preparation 與 candidate runtime 是否可行。結果僅為
  `OBSERVATION`，不得改寫上述 blocking、宣告 candidate 結果或展開 M2。

已關閉的 M1 baseline 與 P4 驗證項目：

- lockfile、harness、result/candidate/fixture schema 與 deterministic fake 已完成；
  Tester 已在相同完整 SHA 重現 success、error、timeout、cancel、force-abort，且
  cleanup counters 全為 0（`M1-FAKE-001`）。
- P4-A01 至 P4-A10 evidence、machine-readable P4 return packet、manifest-relative
  raw retention/config/result paths 與七項 decision table 已獲 Core Designer
  發出 `DELIVERY-AUDIO-POC-M3-P4-ACK-004` 正式核准，M3 Audio real backend 與
  M4a Gate 0 已正式解除！

目前不阻擋 M1、但會阻擋後續階段：

- Core M3 real backend 的完整 accepted SHA：阻擋 POC M3 entry，不阻擋 M1/M2。
- P3 TTS output PCM format：由 M2 winner 產生，阻擋最終 AudioOutput
  cross-validation，不阻擋目前 M1。
- M4a Gate 1 candidate authorization：只有 Gate 0/P4 final selection ACK 後才能申請，
  阻擋 M2 真實 candidate run，不授權在 M1 提前 benchmark。

## 必要 Evidence

- Environment/lockfile 及 setup/smoke 命令。
- Frozen gate decision record。
- Fixture catalog 與 result/candidate schemas。
- Fake candidate success/failure/cancel/cleanup results。
- Pi/co-I2S environment、capability、WAV metadata、xrun 與 device cleanup results。
- M3 HAL dependency status。
- P4 binding/resampler、valid-bit mapping、signal quality、exact framing、async、
  lifecycle、xrun、resource 與 clean-build/license evidence。

## 不做的工作

- 不替真實候選做效能優化。
- 不宣告任何 VAD/ASR/TTS winner。
- 不把 diagnostic shell script 當作產品 HAL。
- 不新增 AEC、barge-in 或 wake-word 行為。

## 調整觸發點

- 產品要求的 PCM/lifecycle 與 co-I2S 實際能力衝突。
- 必須依賴未記錄的 `plughw` conversion 才能運作。
- 無法在看到候選前凍結品質或資源 gate。
- M3 HAL 沒有明確 owner、契約或完整 SHA 交付路徑。

## Gate Review 問題

M1 結束時必須回答：若照目前 harness、gate、硬體能力與 M3 依賴前進，最終 Pi 5、cleanup、offline 與 delivery manifest 是否仍有可行關閉路徑？
