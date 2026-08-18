# Core Team → Audio POC Team: M4a Gate 1B Focused Candidate ACK

- **Delivery ID**: `DELIVERY-AUDIO-POC-M4A-G1B-CANDIDATE-ACK-001`
- **Related contract**: `DELIVERY-AUDIO-POC-M4A-CONTRACT-001`, revision `2026-08-17 / PM-OUT-260817-016`
- **Reviewed response**: `poc_audio/deliveries/RESP-AUDIO-M4A-G1B-CANDIDATES-001.md`
- **Reviewed POC branch / commit**: `dev_audio_m2` / `756ded69dd7b4661fcbac272d4d234c387890fc8`
- **Status**: `ACCEPTED — TWO PRIMARY EXECUTION ROWS ONLY`
- **Owner**: Core Team Designer
- **User decision**: `Accepted 2026-08-18 — limit Gate 2A execution to one ASR and one TTS primary`
- **Architecture change**: `No`

## 1. Disposition and execution budget

Core接受本Gate 1B proposal的identity、provenance與受控artifact邊界，但不授權六個
技術可行rows全部執行。為控制build、Pi與人工品質評估成本，本ACK在揭露任何candidate
結果前固定兩個primary execution rows：SenseVoice ASR與Matcha TTS。其餘可行rows維持
fallback-only `DEFERRED`；只有primary依既有frozen gate失敗且Core另發新的逐列ACK後，
POC才能啟用fallback。

這是事前縮小candidate scope，不修改M1 frozen fixture、品質／資源／lifecycle門檻，
也不把Gate 1B eligibility誤作Gate 2A `PASS`、selection ACK、Gate 2B final reference或
Core production baseline。

## 2. Exact-SHA intake verification

- POC工作樹乾淨，`origin/dev_audio_m2`正好解析為
  `756ded69dd7b4661fcbac272d4d234c387890fc8`。
- POC保存的Core contract與Core revision SHA-256同為
  `96dbdec72e331ec4a611d1f2bdd8509667e59c17a06933f89e091f81a75d34ef`。
- POC引用的G1A relay commit `e3d25d1fc70d726d5bd3162cdcb9571b30937587`與目前Core
  durable commit `6fe09257304a2eb56723a5e8e8d4ad94d9f41963`之ACK內容SHA-256均為
  `d4762840d468d7f0aa7968e3e5cd56098bb1258956dcab55771dfa43f80c19d1`。
- Manifest含12個唯一rows：原請求6個Authorize、3個Defer、3個Reject；JSON Schema與
  Gate 1B兩項artifact-independent regression tests通過。
- 已核對31個受控source/model/voice/wheel檔案之size與SHA-256。Silero另列的
  `controlled://audio-poc/gate1b/models/silero_vad.onnx`未materialize，因此該row維持
  `DEFERRED`；不得以source archive內可能存在的副本取代manifest locator。
- 完整歷史fake suite在本工作站因未安裝`samplerate`於既有fixture-delivery test報錯；
  本次變更的Gate 1B專屬tests與schema皆通過。此為Advisory，不是candidate authorization
  或Gate 2A evidence。

## 3. Row-by-row Gate 1B decision

| Candidate row | Decision | Binding reason / condition |
| :--- | :--- | :--- |
| `vad-silero-onnx-6.2.1` | **DEFERRED** | Python 3.13 aarch64 `onnxruntime`完整wheel closure未固定，且manifest指定的獨立ONNX controlled locator缺檔 |
| `vad-webrtc-2.0.10` | **DEFERRED — fallback only** | 技術上可進isolated evaluation，但本輪不執行VAD candidate；VAD仍在HAL外且非M4a production baseline必要輸出 |
| `asr-whispercpp-base-q5_1-1.9.2` | **DEFERRED — fallback only** | Exact CPU build path可行；只在SenseVoice依frozen gate失敗並取得新Core ACK後啟用，final reference前仍需model provenance / notice review |
| `asr-vosk-small-cn-0.22` | **DEFERRED** | Python dependency與offline aarch64 wheel closure未固定 |
| `asr-pocketsphinx-zh-unavailable-5.1.1` | **REJECTED** | Exact official registry無中文／`zh-TW` model artifact，engine-only row不能滿足產品語言 |
| `asr-sherpa-sensevoice-int8-2025-09-09` | **ACCEPTED — ASR primary** | 只授權manifest exact two-wheel runtime、int8 archive及固定`zh-TW` fixture進offline build與Gate 2A；不得換artifact或runtime fetch；Gate 2B前補齊upstream license notice |
| `asr-sherpa-paraformer-zh-small-2024-03-09` | **REJECTED** | Model archive與exact upstream metadata均無可接受license聲明 |
| `tts-piper-chaowen-medium-1.7.0` | **DEFERRED** | Voice衍生自non-commercial lineage的風險及中文dependency closure未解 |
| `tts-espeak-ng-cmn-1.52.0` | **DEFERRED — fallback only** | Minimal source build可行，但本輪不執行；若日後啟用須另ACK並保留GPL／bundled-data obligations及既有User品質gate |
| `tts-coqui-baker-unavailable-0.27.5` | **REJECTED** | 沒有與current engine相容的exact Baker artifact，Torch/transitive closure也未固定 |
| `tts-sherpa-melo-zh-en-1.13.5` | **DEFERRED — fallback only** | Exact runtime/model與MIT notice可行；只在Matcha失敗並取得新Core ACK後啟用，44.1 kHz native PCM不得被隱式resample |
| `tts-sherpa-matcha-zh-en-1.13.5` | **ACCEPTED — TTS primary** | 只授權manifest exact two-wheel runtime、acoustic archive與16 kHz Vocos進isolated Gate 2A；sample representation與ordered S16_LE boundary須實測；缺少archive內LICENSE及training-data lineage仍阻擋final winner / redistribution |

## 4. Authorized and prohibited actions

### Authorized after this ACK is committed and directly delivered

- 只對`asr-sherpa-sensevoice-int8-2025-09-09`與
  `tts-sherpa-matcha-zh-en-1.13.5`執行proposal所列offline build/install/import及
  isolated Gate 2A comparison。
- 將build輸出、新產生wheel/binary、actual native format、runtime dependency與license
  notice重新hash並綁定新的POC candidate SHA；原始或大型artifact維持Git外受控。
- 依既有M1 frozen fixture、metric、repeat、timeout、cleanup與evidence schema執行；保留
  所有FAIL / INCONCLUSIVE結果。

### Still prohibited

- Build、install、import、load、execute或benchmark任何`DEFERRED`／`REJECTED` row。
- Primary失敗後自動切換fallback；必須先保存failure並回交change request，由Core另發
  exact-row ACK。
- 把本ACK稱為candidate PASS、Gate 2A selection、`POC Accepted`、production dependency
  lock或model / voice baseline freeze。
- 將Matcha的repository metadata解讀為final redistribution/legal acceptance；在training-data
  lineage與notice未獲User/Core書面裁決前，它不能成為Gate 2B final winner。

## 5. Required next return

Audio POC先執行兩個primary的M2 isolated qualification，再依原plan進M3 target/HAL Gate 2A。
回交須提供committed path、branch、完整40-character SHA、candidate/result manifest、commands、
fixture revision、raw evidence checksum、actual PCM、quality/resource/lifecycle/offline結果與
cleanup proof。Core收到後才判斷Gate 2A selection；本ACK不預先保證任一primary會advance。
