# M4a Audio POC Plan

> Status: `REFERENCE / NON-AUTHORITATIVE`
>
> This is a detailed historical POC planning reference. It does not set the
> active milestone, frozen gate, or delivery status. Use
> `docs/milestone/README.md`, the active milestone document,
> `docs/audio_poc_workflow.md`, and the delivery checklist for current work.
> Read this file only when its candidate or harness background is needed.

本計畫定義 M4a 開始前必須完成的 VAD、ASR、TTS 隔離 POC。目標是在 Raspberry Pi 5 上可重複驗證固定 M4a model baseline，並讓獲選 backend 的核心 wrapper 可以升格為產品實作。

LiteRT-LM 不在本計畫範圍內；其 POC 與 M4b gate 見 `../poc_llm/m4b_llm_poc_plan.md` 。

本文件不是 `model_spec.md` 的替代品。候選、實驗結果與淘汰理由保留於 POC；只有最終獲准的 engine / model / voice / 版本 / checksum / license / 格式與資源門檻寫回 `snowboard-agent/docs/model_spec.md` 。

## 1. 完成期限與成功條件

本 POC 必須在 M4a 定案前完成。它可以在 M3 前先用固定 WAV / text fixture 執行，也可以與 M3 的 Audio HAL 開發平行；真實 mic / speaker 整合與全模型常駐測試等需 M3 通過。

POC 完成時必須產出：

- 一個獲選 VAD baseline及固定 endpoint parameters。
- 一個獲選 ASR engine / model及固定語言 / 文字正規化政策。
- 一個獲選 TTS engine / model / voice及固定 output PCM format。
- 每個 artifact 的來源、精確版本、checksum、license 與再散布條件。
- Pi 5 的安裝、磁碟、RAM、cold / hot latency、RTF、cancel 與 cleanup 認證。
- VAD + ASR + TTS 同時常駐時的總資源與連續 session 認證。
- 可升格的 winner backend wrapper，以及未獲選候選的明確淘汰理由。
- Designer、Developer、Tester 與使用者完成 M4a baseline gate 所需的證據摘要。

沒有精確 artifact、license、checksum、Pi benchmark 或可重複 cleanup 證據，即使單次 demo 成功也不算完成。

## 2. POC 與產品程式的邊界

POC 是 M4a 前的隔離可行性研究，不得直接接入 production composition root、Resource Manager 或 StateManager。為提高重用率，候選 wrapper 必須實作與產品相同的最小 adapter 契約，並把 benchmark orchestration 留在 POC 外殼。

可升格重用：

- native binding / subprocess wrapper
- model loader 與 READY proof
- PCM rechunker / iterator bridge
- child-process request / result client
- cooperative cancel、force-abort 與 descendant exit proof
- 無敏感內容的 metrics collector
- 固定 fixture 與 benchmark harness

不可直接當產品交付：

- benchmark CLI 與實驗流程控制
- 寫死的 model path、device name 或 threshold
- 只支援 happy path、沒有 lifecycle / cancel 的 demo code
- 未經 license / checksum 確認的模型
- 未接 production factory、strict config、RM recovery 與 milestone tests 的 wrapper

升格必須是明確的 M4a integration 工作包，不以複製 POC 檔案視為已完成產品實作。

## 3. 建議目錄與輸出

```
scripts/poc/m4_audio/
├── README.md
├── harness/
│   ├── common.py
│   ├── benchmark_vad.py
│   ├── benchmark_asr.py
│   ├── benchmark_tts.py
│   └── benchmark_residency.py
├── candidates/
│   ├── vad/
│   ├── asr/
│   └── tts/
├── manifests/
│   └── <candidate>.yaml
└── schemas/
    └── result.schema.json
```

模型、私有音訊、生成 WAV 與大型 raw result 不提交 repository。Repository 只保存：

- manifest / checksum / 來源與 license 摘要。
- fixture 規格或可公開的小型 fixture。
- 可重複的 harness 與 sanitized JSON summary。
- 執行命令、硬體 / OS / runtime 版本與判定。

每次結果至少包含：

```yaml
candidate_id: ...
kind: vad | asr | tts | residency
engine_version: ...
artifact_name: ...
artifact_checksum: ...
license: ...
platform:
  board: Raspberry Pi 5
  ram_gb: ...
  os: ...
  arch: aarch64
audio_format: ...
runtime:
  threads: ...
  cold_latency_ms: ...
  hot_latency_ms_p50: ...
  hot_latency_ms_p95: ...
  peak_rss_mb: ...
cleanup:
  cooperative_cancel: pass | fail
  force_abort: pass | fail
  orphan_processes: 0
decision: pending | advance | reject
decision_reason: ...
```

## 4. 共同 fixture 與量測規則

### 4.1 Audio fixtures

ASR / VAD 共用同一批經同意取得的 fixture，至少覆蓋：

- 台灣華語短命令。
- 中文為主、夾雜英文詞與縮寫。
- 數字、日期、時間、裝置名稱與常用專有名詞。
- 近距離 / 遠距離及不同說話音量。
- 安靜、風扇聲、一般室內背景音。
- 純靜音、拍手、碰撞與非語音聲音。
- 短句、含自然停頓的句子及超過最大 utterance 的輸入。

第一階段使用固定 WAV 確保所有候選收到完全相同輸入。M3 通過後，再使用目標 I2S mic 錄製的等價 fixture 重跑，禁止以開發機麥克風結果取代 Pi 真實輸入。

### 4.2 TTS fixtures

固定文本至少覆蓋：

- 日常台灣華語句子。
- 數字、金額、日期與時間。
- 中文與英文混合。
- 英文縮寫、產品名與本專案預期出現的專有名詞。
- 短回覆及接近 M4a 最大回覆長度的文本。
- 容易多音或誤讀的字詞清單。

### 4.3 共同規則

- 第一次載入與模型已常駐的 cold / hot 路徑分開量測。
- 至少報 p50 / p95；不以單次最快結果代表候選。
- 固定 CPU thread 數、power mode、散熱條件與背景服務。
- 記錄 peak RSS、模型磁碟大小、CPU、溫度與是否 thermal throttling。
- 網路停用後重跑必要流程，證明主要路徑離線。
- log / summary 不包含 raw PCM、完整 transcript、完整 TTS text 或模型 raw output。
- 敏感 fixture 保留於受控本機，repository 只存 ID、分類與預期結果摘要。

最終 pass threshold 由 Designer 與 Tester 在 POC-0 固定，不得等看到結果後才為偏好的候選 調整門檻。主觀 TTS 品質另外由使用者確認。

## 5. POC-0：契約、門檻與 harness 基線

時機：可立即開始；候選實作前完成。

Owner：Designer 定義契約與選型條件；Tester 定義可重複量測；Developer 建 harness。

工作：

- 依 `m3_design_changes.md` 固定 POC 使用的 AudioInput / AudioOutput format 與 VAD / ASR / TTS 最小 adapter 契約。
- 固定 fixture catalog、敏感資料政策、結果 schema、命令與環境記錄方式。
- 固定每項 metric 的單位、warm-up 次數、重複次數及 pass / elimination 門檻。
- 建立 deterministic fake candidate，先證明 harness 能觀察成功、timeout、error、cancel、force-abort 與 orphan process。
- 定義 candidate manifest；所有模型先完成 license 初審才可下載 / 執行。

產出：共同 harness、result schema、fake baseline 與已簽核的候選清單。

## 6. POC-1：VAD 候選

第一輪候選：

| 候選 | 定位 | 進場條件 |
| --- | --- | --- |
| Silero VAD ONNX | 主要候選；多語、16 kHz、可在 ONNX Runtime 執行 | 固定 artifact / version / checksum / MIT license 認證 |
| WebRTC VAD | 輕量基準組 | 固定實際採用的 maintained binding / version / license；不可只寫演算法名稱 |

每個候選必須使用同一 endpoint state machine，模型只提供 speech observation，避免把候選 自帶的預設切段邏輯誤當產品規格。

量測：

- speech-start false accept / false reject。
- 是否切掉第一或最後音節。
- speech-end latency。
- 自然短暫停頓是否被過早切段。
- 純靜音、非語音聲音與背景噪音。
- 20 ms HAL frame 重組為 backend chunk 的成本與正確性。
- reset、cancel、連續 utterance 與長時間輸入的 state cleanup。
- CPU、p95 per-chunk latency、RSS 與是否需要 child isolation。

產出：獲選 VAD 候選與以下固定參數：

```yaml
threshold
pre_roll_ms
speech_start_timeout_ms
end_silence_ms
min_speech_ms
max_utterance_ms
backend chunk samples
```

## 7. POC-2：ASR 候選

第一輪候選控制在三組：

| 候選 | 主要觀察 |
| --- | --- |
| sherpa-onnx SenseVoice int8 | 中文 / 英文能力、ONNX runtime 共用、Pi latency / RSS |
| sherpa-onnx Paraformer small / int8 | 中文短命令、速度與模型大小 |
| whisper.cpp tiny / base multilingual | 台灣華語 / 中英混說品質與 Pi 資源成本 |

每一列仍須在 manifest 固定單一 artifact 與 quantization； `tiny / base` 或 `small / int8` 不是可接受的最終 baseline 描述。

量測：

- 台灣華語 CER 與產品命令整句正確率。
- 中文 / 英文混說、數字、日期、縮寫與專有名詞。
- 空白、噪音、過短 / 過長 utterance。
- 繁體輸出率；若需後處理，固定 TranscriptNormalizer 的規則與成本。
- cold load、hot latency、RTF、peak RSS、artifact size。
- 模型跨 session 常駐且連續呼叫不累積隱藏 history。
- timeout、cooperative cancel、force-abort、child exit proof 與 rebuild 可行性。
- 完全離線與 log redaction。

因 M4a 只發布最終 PerceptionResult ，POC 不以 partial transcript 作為必要條件；streaming backend 可以參加，但不得要求新增產品事件才能完成基本驗收。

產出：獲選 ASR engine / model / 輸入格式 / language / 文字正規化政策 / thread budget / timeout 與 execution-container 決策。

## 8. POC-3：TTS 候選

第一輪候選：

| 候選 | 主要觀察 |
| --- | --- |
| sherpa-onnx VITS / MeloTTS 中文或中英 voice | 中文可懂度、first chunk、ARM runtime 與模型授權 |
| Piper 中文 voice | 輕量度、streaming bridge、engine GPL 與個別 voice license |

每個 engine 必須分開記錄 runtime license 與 voice artifact license；engine 可用不代表 voice 可再散布或商用。

量測：

- 台灣使用者可懂度與腔調接受度。
- 數字、日期、時間、英文縮寫與專有名詞讀音。
- first-chunk latency、完整生成時間、RTF、peak RSS、artifact size。
- iterator 是否能讓 AudioOutput 邊生成邊播放，而非先生成完整 WAV。
- PCM sample rate、channels、bit depth 與 chunk sequence 正確性。
- cooperative cancel 是否停止生成；失敗時 child terminate / kill / waitpid 是否可證明。
- 連續 session 不重載、不增加 RSS、不殘留 iterator / child。
- 完全離線與 log redaction。

產出：一個獲使用者確認的 engine / model / voice ID、原生 PCM output format、thread budget、timeout、execution-container 與授權決策。M4a Speak worker不做隱式 resample。

## 9. POC-4：真實 Audio HAL 整合

前置：M3 已通過。

工作：

- 使用 M3 AudioInput 錄製目標 I2S mic fixture，重跑 VAD / ASR finalist。
- 使用 M3 AudioOutput 播放 TTS finalist 的原生 PCM stream。
- 驗證 device start / stop / reopen、iterator backpressure、underrun / overflow 與 cleanup。
- 驗證 input / output 不同 sample rate 的 local config，不在 Speak 或 Listen 偷偷 resample。
- 使用實際外殼、距離、風扇與預期環境調校 VAD，但變更仍須重跑固定 fixture。

若 WAV POC winner 在真實 I2S 環境不達門檻，回到 finalist 比較；不得降低既定門檻直接放行。

## 10. POC-5：組合資源與長時間測試

單項 winner 必須在下列模型同時常駐時再驗證：

```
VAD + ASR + TTS
```

工作：

- 記錄所有 process 的總 RSS、swap、CPU thread 與模型載入時間。
- 固定 thread budget，避免 VAD、ASR 與 TTS backend oversubscription。
- 執行至少 20 個固定 fixture session：VAD -> ASR -> deterministic/mock Reasoner -> TTS。
- 記錄整體 wake-to-result / speech-end-to-ASR / ASR-to-first-audio latency。
- 觀察溫度、頻率與 thermal throttling。
- 在 VAD、ASR、TTS 各階段注入 timeout / cancel，確認無 orphan child、未關 iterator或 ALSA owner。
- 停用網路重跑主線。

若總資源超出預算，依序考慮較小 artifact、quantization、thread budget 或模型 lifecycle；不得由 POC 擅自改變 SM / RM / worker 契約。

## 11. 候選判定與 M4a baseline gate

判定順序：

1. License、離線、artifact 可固定、aarch64 可安裝；任一失敗即淘汰。
2. 契約與 cleanup：start / stop / cancel / force-abort 無法證明者淘汰。
3. 品質門檻：VAD endpoint、ASR 品質、TTS 可懂度未達門檻者淘汰。
4. 效能與資源：比較 hot p95、RTF、RSS、磁碟與溫度。
5. 組合測試：VAD、ASR 與 TTS 同時常駐後仍須通過。
6. 使用者確認 TTS voice、license 與整體延遲取捨。
7. Designer 將唯一獲選 baseline 寫回 `model_spec.md` ；候選比較不推入權威文件。

M4a 開始前 gate：

- [ ] VAD / ASR / TTS 各有唯一獲准 baseline。
- [ ] engine、artifact、version、quantization、checksum 與 license 完整。
- [ ] input / output PCM format 與 endpoint parameters 固定。
- [ ] Pi 5 cold / hot / p95 / RTF / RSS / disk / thermal 認證完成。
- [ ] cancel / force-abort / exit proof 與 execution-container 決策完成。
- [ ] 組合常駐至少 20 session 認證完成。
- [ ] M4a test spec 已由 Tester 建立。
- [ ] Developer 已依獲選 wrapper提供產品 integration 估點與工作包。
- [ ] 使用者已確認 TTS voice、license、品質與資源成本。
- [ ] Designer 已更新 model spec 與 milestone dashboard並完成 M4a 定案流程。

## 12. Winner 升格流程

```
POC wrapper
  -> baseline approved
  -> 搬入對應 src/sbd backend 目錄
  -> 加入 strict config 與 lazy factory
  -> 登錄 RM resource / backend rebuild
  -> 接 Listen / Speak worker
  -> 補 unit lifecycle / cancel / P5 tests
  -> 補 M4a Pi milestone tests
  -> Tester 正式驗收
```

建議產品落點依最終候選決定，例如：

```
src/sbd/perception/listen/<vad_backend>/
src/sbd/perception/listen/<asr_backend>/
src/sbd/action/speak/<tts_backend>/
```

如果 native inference 是 blocking 且無可靠 cooperative cancel，winner 必須使用 persistent child process；其 READY、request、result / PCM、cancel、error、shutdown 與 exit proof schema 須在產品 backend 實作前寫入 `snowboard-agent/docs/protocol.md` 並完成 review。

## 13. 角色分工

| 角色 | 責任 |
| --- | --- |
| Designer | 契約、候選不可放寬條件、門檻、結果收斂、model baseline與 M4a gate |
| Developer | POC harness、candidate wrapper、Pi benchmark、sanitized evidence與升格估點 |
| Tester | fixture / 量測可重複性、failure / cancel 證據、M4a 正式 Test ID；不以 demo 代替驗收 |
| Reviewer | Implement 契約修訂與產品升格介面的設計審查 |
| User | 目標硬體、TTS voice主觀品質、license / 商用限制與資源取捨確認 |
