# M3：Pi 5 真實 M3 Audio HAL 整合

狀態：`GATE_REVIEW / CORE GATE 2A ACK PENDING`

Pi formal session 已依 User 指示於 2026-08-24 完成，詳見
[`M3-PI-SESSION-SCHEDULE-001`](../../poc_audio/deliveries/M3-PI-SESSION-SCHEDULE-001.md)。
Final execution 綁定 Audio `f7b9694d1477f26513880526e0718d2b3c5766b3`、Core
`6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` 與 Core ACK commit
`cae21217b2f7d812511bde77edb2cd1eb65e8f06`。22-result set 已通過單一 SHA/唯一 ID
驗證，User 已核准 reviewed PASS disposition；M3 只等待 Core Gate 2A return ACK。

## 目標

使用完整 SHA 固定的產品 M3 Audio HAL 與目標 Pi 5/I2S 硬體重跑 finalists，證明固定 WAV/text 結果能在真實 capture/playback、外殼與環境中成立。

本 milestone 也是
[`DELIVERY-AUDIO-POC-M4A-CONTRACT-001`](../pm_handoff/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md)
Gate 2A 的完整執行與回交階段：M2 的隔離結果必須用 accepted M3 HAL
與 Pi 資源重跑，再以完整 40-character SHA 回交 P1–P12 manifest，
等待 Core Gate 2A selection ACK。該 ACK 可放行 artifact-independent Core
adapter scaffold，不是 final reference、model baseline lock 或 `POC Accepted`。

M2 已由
[`RESP-AUDIO-M2-GATE-CLOSURE-002`](../reviews/RESP-AUDIO-M2-GATE-CLOSURE-002.md)
正式關閉；M3 依
[`M3-ENTRY-LOCK-002`](../../poc_audio/deliveries/M3-ENTRY-LOCK-002.md)
規劃並已開始 hardware execution。User 已提交
[`CR-AUDIO-M3-RISK-FOCUSED-GATES-001`](../../poc_audio/deliveries/CR-AUDIO-M3-RISK-FOCUSED-GATES-001.md)
供 Core/Designer 審查。Core 已以
[`RESP-AUDIO-M3-RISK-FOCUSED-GATES-001`](../pm_handoff/RESP-AUDIO-M3-RISK-FOCUSED-GATES-001.md)
`ACCEPTED WITH CONDITIONS` 核准判定框架與 packet minimum，並授權準備 test packet。
User 已核准 packet；原 Core output adaptation SHA `ff091995...` 已由 drain replacement
`6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` 取代。formal backend、offline enforcement、
candidate lifecycle 與 draft summary 已完成本地驗證。packet/runner candidate 已固定為
`655e80ec4ed287708ed0a47f383b645d88650b18`；Core Designer 已以
[`RESP-AUDIO-M3-PACKET-SIGNOFF-001`](../pm_handoff/RESP-AUDIO-M3-PACKET-SIGNOFF-001.md)
在 commit `e63884451368079a9c876c2994c982627aa7d766` 一次性 ACK。M3 現由 Audio 主導
Pi qualification。Audio 已對 playback blocker 完成隔離實作與 Pi 驗證，並以
[`CR-AUDIO-M3-CORE-HAL-PLAYBACK-DRAIN-001`](../../poc_audio/deliveries/CR-AUDIO-M3-CORE-HAL-PLAYBACK-DRAIN-001.md)
交付 direct-child review candidate `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf`。Core 已以
[`RESP-AUDIO-M3-CORE-HAL-PLAYBACK-DRAIN-001`](../pm_handoff/RESP-AUDIO-M3-CORE-HAL-PLAYBACK-DRAIN-001.md)
接受 authoritative replacement、semantics 與 evidence，且不要求額外測試。Core 後續以
`RESP-AUDIO-M3-PACKET-SIGNOFF-003` ACK replacement Audio SHA；Audio 已完成 final Pi run、
evidence review 與 User publication approval。結果見
[`M3-RISK-FOCUSED-QUALIFICATION-REVIEW-001`](../../poc_audio/evidence/m3/M3-RISK-FOCUSED-QUALIFICATION-REVIEW-001.md)。

## 2026-08-24 final gate-review result

- Exact 22-result set：`18 PASS / 0 FAIL / 4 human-review INCONCLUSIVE`；四項為 runner
  刻意保留給 VAD/ASR/TTS 人工判定，不是 execution failure。
- VAD 保留五段 speech；60 秒靜音、device-start、impact 與 cough 均為零 event；playback
  speech 正確偵測。
- Base Q8 direct/HAL 各產生五筆非空結果；HAL 無 paired regression，pause item 從三 edits
  改善為一 edit。受控 semantic review 未發現 critical meaning-changing misread。
- Matcha 六句皆完成 target AudioOutput playback；User 全數評為 `5/5` 並核准發布。
- LIFE-01～06、offline isolation、PCM recovery 與 final shutdown cleanup 均通過；無 worker、
  device owner 或 throttle。Small Q8 fallback 與 M3.1 均未啟動。

## 2026-08-24 execution finding

- Pi 5 / VoiceHAT `hw:0,0` preflight PASS；裝置 owner、temperature 與 throttling bounded。
- 初次 `M3-VAD-01` capture 完整 6 秒，但首次載入 NumPy 固定建立 3 個 runtime threads，
  harness 將其判為 cleanup FAIL；舊 evidence 不覆寫。
- `OPENBLAS_NUM_THREADS=1` 已證明可把 runtime 維持單執行緒；operator rehearsal 收到
  `300/300` frames、`peak=-12.6 dBFS`、`RMS=-30.7 dBFS`、device released。
- recovery capture cleanup 為零且 runner result PASS，但維持
  `DRAFT_USER_CONFIRMATION_PENDING`；Core SHA 更新後不直接沿用為新 packet formal result。
- Packet-pinned Core AudioOutput writes/cleanup 完成卻無聲；同一 source 與 exact
  Core-adapted native WAV 經 `aplay` 可聽。相同 pyalsaaudio `960 × 4` 設定加入
  success-path `drain()` 後可聽，確認 completion defect。
- Review candidate `6c7fc8c...` 在 Pi focused `8 passed`、完整 non-RPi
  `267 passed / 1 optional skipped / 21 deselected`、5/5 silent reuse cycles、實體語音
  `6.055 s` 完整 drain，User 確認可聽且音量與 `aplay` 類似，cleanup released。
- Sanitized evidence：
  [`M3-CORE-HAL-PLAYBACK-DRAIN-DEBUG-001`](../../poc_audio/evidence/m3/M3-CORE-HAL-PLAYBACK-DRAIN-DEBUG-001.md)。

## 對最終交付的貢獻

- Pi 5/M3 HAL、真實 mic fixture、原生 TTS PCM playback 的正式 evidence。
- Start/stop/reopen、device failure、backpressure、xrun、cancel 與 cleanup 認證。
- 每類一個 hardware-qualified winner，或 evidence-backed no-go。
- M4A-P1–P12 可重現 manifest、Gate 2A selection ACK 與 M4 Gate 2B
  final reference 所需的 hardware-qualified ASR/TTS 建議。

## 工作大綱

- 固定 M3 HAL 產品 repo 與完整 commit SHA。
- 記錄 Pi 型號/RAM、OS、kernel、driver、mic/speaker、接線、外殼、距離與噪音環境。
- 用 M3 AudioInput 錄製等價 fixture，重跑 VAD/ASR finalists。
- 將 TTS finalist 的原生 PCM iterator 送入 M3 AudioOutput。
- 驗證 input/output 不同設定、半雙工 ownership 及不得在 Listen/Speak 隱式 resample。
- 測 start/stop/reopen、invalid device、backpressure、underrun/overflow、timeout/cancel/force-abort 與 cleanup。
- 記錄 Pi latency、RTF、RSS、CPU、temperature 與 throttling。
- 若固定 fixture winner 在真實裝置失敗，回到 finalist 比較，不降低 gate。
- 執行 M4A-P1–P8：ASR HAL frame 對齊/品質、TTS native PCM 與完整播放、
  ASR/TTS 個別 Pi resource/thermal。
- M4A-P9 已收到 LLM POC 提供的 versioned/checksummed deterministic M4b residency
  surrogate 與 executable protocol，附件 regression 已通過；Core corrected ACK
  `caf4f7ba867e4ebc1972df0ade86c605a873a286` 已解除 Audio integration 前置。Audio
  自行安排 bounded execution，不阻擋本 M3 start packet，且不產生 LLM Gate 2 credit。
- 在 accepted HAL/Pi 重跑 M4A-P10–P12 lifecycle、clean build/license 與 offline，
  並沿用較嚴格的 Audio POC ASR/TTS frozen quality gate。
- 完成 contract 規定的 decision table、manifest 與 return delivery，回交完整
  SHA 後等待 Core Gate 2A selection ACK；final reference 由 M4 Gate 2B 完成。

## Entry Conditions

- M2 finalists 與對應 artifact 全部固定。
- M4a Gate 1 Core 書面核准、candidate scope 與 M4A-P1–P12 traceability
  已由 M2 完整 SHA 定位。
- M3 Audio HAL 已通過其產品驗收並提供 source/tests/docs/完整 SHA。
- 目標 Pi、mic、speaker、外殼及真實測試環境可用。
- User 可進行現場距離、噪音與聲音確認。
- M4A-P9 surrogate 不作為 Audio M3 hardware qualification entry condition。固定 artifact、
  checksum、protocol、process-group topology、decision rule 與 Core corrected ACK 已收到；
  Audio 可自行安排 P9，但未執行前不得宣稱 P9 PASS。

## Exit Gate

- VAD/ASR finalists 已用目標 mic fixture 重跑並達 frozen gate。
- TTS finalist 已以原生 PCM sequence 經真實 AudioOutput 播放並達 gate。
- Device lifecycle、failure、xrun/backpressure、cancel 與 cleanup evidence 完整。
- Pi performance/resource/thermal evidence 完整，未以 Ubuntu/開發機結果取代。
- 每類產生一個 hardware-qualified winner；任何 no-go 或 fallback 都有正式決策。
- M4 組合所需 format、endpoint、threads、timeout 與 execution-container 已固定。
- M4A-P1–P8、P10–P12 每項的 PASS/FAIL/INCONCLUSIVE、raw evidence path、cleanup
  與 reproduction command 已由 return SHA 定位。P9 另列
  `CORE ACCEPTED / AUDIO INTEGRATION UNBLOCKED / NOT EXECUTED`，不得冒充已執行；
  Audio 依 accepted protocol 自行執行並保留與本 22-result start packet 的邊界。
- Core Designer 已發 Gate 2A selection ACK，或明確發出
  evidence-backed no-go/補件要求；未取得 ACK 時 M3 不得標為 `COMPLETE`。
  Final reference 與 `POC Accepted` 仍由 M4 Gate 2B 關閉。

## 必要 Evidence

- M3 HAL repo/完整 SHA 與 Pi hardware/environment manifest。
- 真實 mic fixture metadata/checksum 與受控位置。
- VAD/ASR/TTS hardware run results。
- Playback sequence、xrun/backpressure、device lifecycle 與 cleanup proof。
- Latency/resource/thermal summary 與 rejected finalist reasons。
- M4a Gate 2A manifest/decision table/return SHA 與 Core selection ACK。

## 條件式 M3.1 remediation 規劃

依
[`PROPOSAL_AUDIO_001_M3_1_REMEDIATION`](../pm_handoff/PROPOSAL_AUDIO_001_M3_1_REMEDIATION.md)
及 Core 的
[`RESP-AUDIO-M3-1-REMEDIATION-FRAMEWORK-001`](../pm_handoff/RESP-AUDIO-M3-1-REMEDIATION-FRAMEWORK-001.md)，
M3.1 是 contingency stage，不是固定 milestone，也沒有預先 execution authority。

本次 playback finding 不啟動 M3.1：根因位於 Core HAL success completion，修正不涉及
gain、pre-roll 或 front-end processing，依正式 Core change/review 流程處理。

只有以下三項同時成立才可提出啟動：

1. M3 在 named hard gate 產生可重現 `FAIL` 或 `INCONCLUSIVE`。
2. signal、waveform 或 diagnostic evidence 指向一個可處理 root cause。
3. POC 提交單一 minimal remediation，並在套用前取得 Core Designer 書面核准。

每次 activation 只允許一個 fixed gain、一個 fixed pre-roll，或一個有文件依據的
必要 minimal front-end step；不得做 gain/threshold/padding/front-end matrix。啟動時
立即停止 M3 formal execution，保存 controlled raw evidence，另建 committed M3.1
re-qualification packet 並取得 Core review。M3.1 未關閉時不得進 M4 acceptance；若單一
修正無法關閉 blocker，停止並提交正式 change request。

## 不做的工作

- 不修改產品 HAL 來掩蓋 POC candidate 缺陷；需要改 HAL 時走其正式 change/review 流程。
- 不加入 barge-in/AEC。
- 不以 `plughw` 隱藏未記錄的格式轉換。
- 不因真實硬體結果較差而調低 frozen gate。
- 不將 M4A-P9 資源 stub 擴張成 LiteRT-LM candidate 比較、產品整合或
  M4b 驗收。

## 調整觸發點

- M3 HAL SHA/契約/裝置行為無法滿足 POC 前提。
- 固定 WAV finalist 在真實 mic/speaker 全部失敗。
- Shared-clock 或 device ownership 使必要 lifecycle 無法成立。
- Thermal、RSS、RTF 或 latency 顯示 M4 組合不可能達標。
- M4A-P9 所需 surrogate 無 version/checksum/可重現來源，或 Core 要求超出資源模擬
  而實作/驗收 LLM。
- Contract quality gate 與已凍結 Audio POC gate 不一致；取較嚴格者，
  若無法同時達成則提出 change request。

## Gate Review 問題

M3 結束時必須回答：固定 winners 是否已具備在同一 Pi 5 同時常駐並完成至少 20 sessions 的可信資源與 lifecycle 路徑？若答案是否定或證據不足，先提出 fallback/no-go，不直接進 M4。
