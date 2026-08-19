# M2：VAD、ASR、TTS 隔離候選比較

狀態：`IN_PROGRESS`

Gate 狀態：`GATE 1B ACCEPTED — SENSEVOICE ASR REJECTED BY FROZEN QUALITY GATE / MATCHA TTS PERFORMANCE PASS, REMAINING GATES IN PROGRESS`

## 目標

用 M1 固定的方法比較所有核准候選，淘汰不具交付資格者，為每一類產出可進入真實硬體整合的 finalist；此階段結果仍須通過 M3/M4 才能成為最終 winner。

本 milestone 同時承接
[`DELIVERY-AUDIO-POC-M4A-CONTRACT-001`](../pm_handoff/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md)
Gate 1：POC 先回交 candidate/version/source hash/license/Pi build proposal，只對
Core Designer 書面核准的範圍執行比較。M2 結果是 Gate 2 evidence 的累積，
不是 Core final winner ACK。

2026-08-17 revised contract 所要求的 committed executable plan 已由
[`RESP-AUDIO-M4A-GATE-PLAN-001`](../../poc_audio/deliveries/RESP-AUDIO-M4A-GATE-PLAN-001.md)
提出，且 Core 已在 `dev_agent_m4` commit
`e3d25d1fc70d726d5bd3162cdcb9571b30937587` 以
`DELIVERY-AUDIO-POC-M4A-G1A-PLANNING-ACK-001` 接受 Gate 1A、固定 `zh-TW`、
VAD 範圍與 provenance-only 邊界。POC 已依該邊界準備
[`RESP-AUDIO-M4A-G1B-CANDIDATES-001`](../../poc_audio/deliveries/RESP-AUDIO-M4A-G1B-CANDIDATES-001.md)
exact proposal。Core 已在 `dev_agent_m4` commit
`790c0f86e12422542ef94cacd3c4dd850e346bca` 以
[`DELIVERY-AUDIO-POC-M4A-G1B-CANDIDATE-ACK-001`](../pm_handoff/DELIVERY-AUDIO-POC-M4A-G1B-CANDIDATE-ACK-001.md)
完成逐列 disposition；只有 SenseVoice ASR 與 Matcha TTS 可在 WP2 完成後
build、install、import、load、execute 與 isolated benchmark。

2026-08-18 已依 User 決定恢復 amendment，將 sherpa-onnx Matcha zh/en
列為 TTS primary evaluation candidate。完整 archive 與 16 kHz Vocos 的 GitHub
release asset ID/digest、POC SHA-256、大小及 ModelScope release-time commit/LFS
OID 已互相核對；amended proposal 現提出六個 `REQUEST_AUTHORIZE` rows。Matcha
archive 未內附 LICENSE，且 model card 沒有固定混合中英訓練資料的名稱與條款，
因此 Core legal review 仍是 final-winner blocker。proposal amendment 當時只完成
provenance review，沒有 build、install、import、load、execute、benchmark 或上 Pi；
後續 execution scope 以本頁記錄的 Core Gate 1B ACK 為準。

2026-08-18 Core ACK 已核對 proposal commit
`756ded69dd7b4661fcbac272d4d234c387890fc8`，並事前固定只執行：

- `asr-sherpa-sensevoice-int8-2025-09-09` — ASR primary。
- `tts-sherpa-matcha-zh-en-1.13.5` — TTS primary。

其餘 10 rows 均為 `DEFERRED` / `REJECTED`，primary 失敗後也不得自動啟用
fallback。兩個 primary 的五個唯一受控輸入（七個逐列 artifact bindings）已在
workstation 與 Pi 重新核對大小及 SHA-256，全部匹配 manifest。WP2
protocol/schema、fake lifecycle 與 validator scaffold 已完成；Pi artifact
preflight、offline install/import identity 及一筆 ASR/TTS focused smoke 也已通過，見
[`M4A-G1B-WP3-PREFLIGHT-SMOKE-001`](../../poc_audio/evidence/m2/M4A-G1B-WP3-PREFLIGHT-SMOKE-001.md)。
完整 50-item ASR 與 20-prompt TTS 的三次 cold、三次 warm-up 及二十次 hot
qualification 已在 Pi SHA `63c2cc179bb3c2525201da0f7a78d2c50b63d759`
完成。SenseVoice 台灣華語 core CER 41.629%、整體整句正確率 6%，均未達
frozen 20%/70% hard gates，故該 primary 已 `REJECT`；全 20 hot cycles 對每筆
fixture 的 hypothesis hash 都穩定重現。Matcha first-buffer p95 285.098 ms、RTF
p95 0.112776，通過 performance gates，但 User quality、lifecycle、真正斷網、
resource-growth review 與 legal blockers 仍未關閉。見
[`M4A-G1B-WP3-FULL-QUALIFICATION-001`](../../poc_audio/evidence/m2/M4A-G1B-WP3-FULL-QUALIFICATION-001.md)。
SenseVoice 失敗後不得自動啟用 fallback，已提出
[`CR-AUDIO-M4A-G1B-ASR-SCOPE-001`](../../poc_audio/deliveries/CR-AUDIO-M4A-G1B-ASR-SCOPE-001.md)
請 Core 決定授權 exact Whisper.cpp fallback 或接受 ASR no-go。Core 本輪沒有授權 VAD execution row，故 M2 的 VAD
finalist/no-go exit condition 尚無關閉路徑；見
[`CR-AUDIO-M4A-G1B-VAD-SCOPE-001`](../../poc_audio/deliveries/CR-AUDIO-M4A-G1B-VAD-SCOPE-001.md)。
Core ACK 記錄的既有 `samplerate` advisory 已由 POC 以隔離環境重跑完整 suite
關閉（32/32 tests `OK`）；它不是 Gate 2A candidate evidence。

## 對最終交付的貢獻

- 完整 candidate manifest、license/checksum/source 與成功或失敗結果。
- VAD endpoint、ASR 品質、TTS 品質及 latency/resource/lifecycle 比較。
- `advance`/`reject` 判定和 execution-container 初步建議。
- M4a Gate 1 授權記錄與 M4A-P2/P3/P6/P10/P11/P12 的隔離驗證索引。

## 工作大綱

- 先做 license、artifact 可固定、offline、aarch64 安裝進場檢查。
- Gate 1 proposal 先對齊 Core 起始候選：ASR 為 whisper.cpp、Vosk、
  PocketSphinx；TTS 為 Piper、espeak-ng、Coqui TTS。每一列仍須固定
  exact artifact/version/hash/license，不得只交 engine 名稱。
- 既有 SenseVoice、Paraformer 與 sherpa-onnx voice 以 alternative 列入 proposal，
  只有 Core Designer 書面核准後才執行，不靜默取代 contract 清單。
- VAD 維持 Silero VAD ONNX/WebRTC VAD 與相同 endpoint state machine；由於
  Core contract Gate 1 文字只列 ASR/TTS，M2 entry 前須由 PM/Core 書面確認
  VAD 仍依 Audio POC frozen gate 執行。
- 所有候選使用相同 fixture、threads、warm-up、repetitions 與量測工具。
- 驗證 cold/hot、p50/p95、RTF、RSS、disk、CPU、cancel、force-abort、offline 與 cleanup。
- 安排 User 對 TTS voice 做受控主觀品質確認。
- 保留失敗結果，為每個 candidate 記錄 advance/reject 及原因。
- 以 M4A-P1 至 P12 ID 建立 traceability；M2 只能對隔離 fixture/build/
  lifecycle/offline 產生 preliminary evidence，HAL playback、Pi resource 與同時常駐的
  final disposition 留待 M3。

M2 執行分成四個受控步驟：

1. **Gate 1 planning**：`COMPLETE`；Core Gate 1A ACK 已接受 plan 與 D01–D05。
2. **Gate 1 candidate proposal**：`COMPLETE`；Core Gate 1B ACK 已逐列 disposition
   12 rows，只接受 SenseVoice ASR 與 Matcha TTS 兩個 primary execution rows。
3. **Shared conformance scaffold**：`COMPLETE`；
   [`m4a_conformance.py`](../../poc_audio/src/audio_poc/m4a_conformance.py)、
   `m4a_conformance_result` schema 與 fake success/error/timeout/cancel/
   force-abort/reopen runner 已完成；33/33 local tests 與 schema smoke 通過，未載入
   candidate runtime。
4. **Authorized comparison**：`FULL FIXTURE QUALITY/PERFORMANCE REVIEWED / REMAINING TTS GATES IN PROGRESS`；
   只執行兩個 primary。SenseVoice 已因 frozen ASR quality hard gates `REJECT`；
   Matcha latency/RTF 通過，但 User quality、lifecycle、network-disabled、resource
   growth 與 legal conditions 尚待關閉。ASR fallback 等待新 Core ACK。

## Entry Conditions

- M1 exit gate 通過，gate 與 fixtures 已凍結。
- M4a contract Gate 0 已以 Core P4 final selection ACK 關閉，且 contract
  intake 已記錄 POC 完整 SHA。
- PM relay/ACK 回傳路徑、candidate proposal template 與 Core decision owner 已確認。
- 敏感 fixture 受控位置可用。

真實 candidate execution 的 Gate 1B 子 gate已對兩個 primary 滿足：proposal
已列版本、artifact、source SHA-256、dependency、license/notice 與 Pi build
steps，且 Core Designer 已書面核准 ASR/TTS scope。WP2 exit 已滿足；WP3 的固定
fixture checksum、乾淨 test SHA、受控 artifact preflight 與 focused smoke 已完成，
full-fixture quality/performance 已完成；TTS remaining gates 尚未完成，ASR fallback
執行邊界等待 `CR-AUDIO-M4A-G1B-ASR-SCOPE-001`，VAD 執行邊界仍待
`CR-AUDIO-M4A-G1B-VAD-SCOPE-001` 決策。

## Exit Gate

- 每個已執行候選都有完整 manifest、結果與判定，失敗沒有被省略。
- 每一類至少有一個達 M2 gate 的 finalist；否則提出該類 no-go/change request。
- Finalists 的 artifact/version/checksum/license、format、threads、timeout 與 wrapper lifecycle 明確。
- TTS finalist 已取得 User 的初步品質回饋。
- M3 真實 Pi/HAL 重測範圍與必要 fixtures 已明確。
- Gate 1 ACK、核准 candidate list 與每個 M4A Test ID 的 preliminary/
  pending 狀態可由固定 SHA 定位；未在 M2 完成的 HAL/Pi 項目不得標為 PASS。

## 必要 Evidence

- Candidate manifests 與 eligibility decisions。
- Sanitized per-run results 及 result index。
- VAD/ASR/TTS 品質與資源比較摘要。
- Cancel/force-abort/orphan cleanup proof。
- Offline results、TTS user review 與 rejected-candidate reasons。
- Core Gate 1 ACK、candidate scope、language/VAD boundary decision 與 M4A-P1–P12
  traceability matrix。

## 不做的工作

- 不接 product composition root、RM 或 SM。
- 不為淘汰候選做無限調參或產品化。
- 不因候選表現修改 frozen gate。
- 不把開發機結果當 Pi 5 驗收。

## 調整觸發點

- 任一類所有候選在 eligibility 或 frozen gate 淘汰。
- Artifact/license 無法固定，或模型不能合法商用/再散布。
- Wrapper 無法提供可靠 cancel/force-abort/exit proof。
- Pi 5 資源預估已明顯無法支撐 M4 同時常駐。
- Core 不核准 contract 起始候選、現有 alternative 或 VAD 執行邊界。
- M4A-P3/P6 的 contract 門檻低於 Audio POC frozen gate；此時維持較嚴格的
  CER/整句正確率與 TTS User 品質 gate，不得因新 contract 放寬。

## Gate Review 問題

M2 結束時必須回答：每類 finalist 是否有合理機會在 pinned M3 HAL、真實 mic/speaker 與三模型同時常駐下達到最終 gate？沒有合理路徑者不得只因單項 demo 成功而 advance。

Gate 1B review 已回答：Core 只接受 SenseVoice ASR 與 Matcha TTS，並正式
defer/reject 其餘 10 rows。這只解除兩個 exact rows 的 execution prohibition；
manifest native format 與 build recipe 仍從 `DECLARED_UNVERIFIED_GATE_1B` /
`NOT_EXECUTED_GATE_1B` 開始，必須由 WP3 evidence 實測，不得因 ACK 標為 PASS。
