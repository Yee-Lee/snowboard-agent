# M1：共同測試基線與 co-I2S Capability

狀態：`CHANGE_REQUESTED`

Frozen-gate decision record：[M1 Frozen-Gate Draft](m1_frozen_gates_draft.md)
（狀態為 `DESIGNER_APPROVED / NOT FROZEN`；真實 candidate run 尚未獲准。）

Core-team handoff：[Audio M3 Contract v1](../../poc_audio/deliveries/audio_m3_contract_v1.0.md)
（核心 M3 的設計輸入；不是 POC M3 integration baseline。）

Current hardware finding：[M1 Native Audio Evidence](../../poc_audio/evidence/m1/M1-NATIVE-AUDIO-001.md)
— P1 `FAIL`, P2 `PASS`; proposed resolution：[CR-AUDIO-M3-PCM-001](../../poc_audio/deliveries/CR-AUDIO-M3-PCM-001.md)。

Core design-correction delivery：[DELIVERY-AUDIO-POC-M3-DESIGN-CORRECTION-001](../../poc_audio/deliveries/DELIVERY-AUDIO-POC-M3-DESIGN-CORRECTION-001.md)
（User/Designer 已批准 Option A，等待 Core Team 回覆。）

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

Blocking M1 / real candidate entry：

- Core Team 接受或有界修訂 `CR-AUDIO-M3-PCM-001`，確認明確的 AudioInput
  conversion boundary。
- 完成 lockfile、harness、result/candidate schema 與 deterministic fake，並由
  Tester 重現 success/failure/timeout/cancel/cleanup。
- 完成 fixture catalog、授權/checksum、normalization/label 與 metric definition
  review，使 frozen gate 可標為 `FROZEN`。

目前不阻擋 M1、但會阻擋後續階段：

- Core M3 real backend 的完整 accepted SHA：阻擋 POC M3 entry，不阻擋 M1/M2。
- P3 TTS output PCM format：由 M2 winner 產生，阻擋最終 AudioOutput
  cross-validation，不阻擋目前 M1。

## 必要 Evidence

- Environment/lockfile 及 setup/smoke 命令。
- Frozen gate decision record。
- Fixture catalog 與 result/candidate schemas。
- Fake candidate success/failure/cancel/cleanup results。
- Pi/co-I2S environment、capability、WAV metadata、xrun 與 device cleanup results。
- M3 HAL dependency status。

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
