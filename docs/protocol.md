# Snowboard child-process protocols

狀態：Audio Protocol v1與LLM Protocol `snowboard.llm/1` Designer draft complete，待 Reviewer 審查。

本文件固定 Core controller 與其直接擁有 child 之間的 private wire schema。它不是公開 network API；child 不得 listen socket、連網或接受任意外部 client。Audio runtime baseline 與 artifact identity 見 `model_spec.md`，lifecycle owner 與 recovery 見 `implement/ch_m4a_audio_production.md`。

## 1. Common framing

- Parent 以 `start_new_session=True` 啟動每個 top-level child，使 child PID=PGID；ASR supervisor 的 native whisper descendant 不得建立 nested session/group。
- Control 為單行 UTF-8 JSON，以 `\n` 終止，最大 16 KiB。Object 必須 exact-key；Audio使用`protocol: 1`，LLM使用`protocol_version: "snowboard.llm/1"`，unknown/missing/extra key一律protocol error。
- `request_id`由parent在單一child lifetime內配置、嚴格遞增且不可重用。Audio為正整數；LLM為符合`^[A-Za-z0-9._:-]+$`且長度1～128的string。所有operation event帶同一ID；READY/PING/PONG/SHUTDOWN不帶request ID。
- Binary payload 只允許在 schema 明列的 header 後立即出現，parent/child 以 `readexactly(payload_bytes)` 讀取。不得 scan delimiter、部分接受或無界 buffer。
- 一次只允許一個 active request。第二個 BEGIN/GENERATE 在第一個 terminal 前以 `BUSY` 拒絕，不排隊。
- IPC text/PCM 可存在於 pipe 與 private process memory，但不得寫入 log/result/evidence。stderr 只允許 sanitized code/stage/PID，不含 command、prompt、transcript、TTS text、PCM 或私人 path。
- EOF、invalid JSON/UTF-8、超限、wrong request ID、wrong payload length、unknown event 或 checksum mismatch 使 parent 視為 backend protocol failure；parent 先完成 termination proof，不把它轉成 empty transcript 或 normal action error。

## 2. ASR Protocol v1

### 2.1 Parent → supervisor

Begin one streaming request：

```json
{"protocol":1,"op":"BEGIN","request_id":1,"format":"16000_mono_s16le","frame_bytes":640}
```

每個 frame 是 JSON header，後面立即接恰 640 raw bytes：

```json
{"protocol":1,"op":"FRAME","request_id":1,"sequence":0,"payload_bytes":640}
```

`sequence` 從零開始逐一遞增。`FRAME` 只在 capture active 時合法，且同時最多一個 frame in flight。Supervisor對每個尚未形成終點的frame回：

```json
{"protocol":1,"event":"FRAME_ACCEPTED","request_id":1,"sequence":0}
```

Parent 收到matching `FRAME_ACCEPTED`才可送下一個frame。當Silero end-silence與完整post-padding都已收齊時，supervisor以`ENDPOINT`取代該frame的ACK；parent不再送frame。這個credit規則避免fast fixture把endpoint之後的PCM預先塞入pipe。

Cooperative cancellation：

```json
{"protocol":1,"op":"CANCEL","request_id":1}
```

Shutdown 只在 READY state 合法：

```json
{"protocol":1,"op":"SHUTDOWN"}
```

### 2.2 Supervisor → parent

READY 只在 Silero 與 persistent native whisper worker 完成載入且 product-lock identities 全部吻合後送出：

```json
{
  "protocol": 1,
  "event": "READY",
  "pid": 1234,
  "pgid": 1234,
  "runtime_lock_sha256": "<64 hex>",
  "vad_model_sha256": "<64 hex>",
  "asr_binary_sha256": "<64 hex>",
  "asr_model_sha256": "<64 hex>",
  "profile_sha256": "<64 hex>"
}
```

Endpoint 關閉 capture，但不暴露 PCM：

```json
{"protocol":1,"event":"ENDPOINT","request_id":1,"captured_frames":120,"bounded_samples":32000,"bounded_pcm_sha256":"<64 hex>"}
```

Successful transcription：

```json
{"protocol":1,"event":"RESULT","request_id":1,"text":"<private UTF-8 transcript>","language":"zh-TW","latency_ms":1325.0}
```

Normal cooperative cancel terminal：

```json
{"protocol":1,"event":"CANCELLED","request_id":1}
```

若 cancellation 在不可合作取消的 native inference 開始後抵達，supervisor 送出 nonterminal `CANCEL_DEFERRED`。Blocking inference/generation必須在child擁有的單一background execution slot執行，使control loop仍能接收CANCEL；該slot不允許第二個operation。Parent `abort()` 保持 pending；Ch 6 Level 1 timeout 後對完整 process group 呼叫 `force_abort()`。

Recoverable request rejection 使用 stable code；temp cleanup 完成後同一 child 回 READY：

```json
{"protocol":1,"event":"ERROR","request_id":1,"code":"NO_SPEECH"}
```

允許的 ASR request code 為 `INVALID_FRAME`、`NO_SPEECH`、`MULTIPLE_UTTERANCES`、`INFERENCE_REJECTED`。Crash、identity mismatch、protocol error 與 cleanup failure 不是 request ERROR。

Clean shutdown：

```json
{"protocol":1,"event":"SHUTDOWN_ACK"}
```

ACK 後 supervisor 關閉 native worker、證明 descendant exit、刪除 temp data 並 exit zero；parent 仍必須 waitpid supervisor。

## 3. TTS Protocol v1

### 3.1 Parent → worker

```json
{"protocol":1,"op":"GENERATE","request_id":1,"text":"<private UTF-8 text>","voice_id":"matcha-zh-en-default-sid-0"}
```

`text` 必須 nonempty、無 NUL 且符合 common 16 KiB control limit；只接受固定 voice ID。

Cancel 與 shutdown：

```json
{"protocol":1,"op":"CANCEL","request_id":1}
```

```json
{"protocol":1,"op":"SHUTDOWN"}
```

### 3.2 Worker → parent

READY 只在 exact runtime/acoustic/Vocos/profile validation 與 engine load 完成後送出：

```json
{
  "protocol": 1,
  "event": "READY",
  "pid": 2345,
  "pgid": 2345,
  "runtime_lock_sha256": "<64 hex>",
  "acoustic_model_sha256": "<64 hex>",
  "vocoder_sha256": "<64 hex>",
  "profile_sha256": "<64 hex>"
}
```

成功 generation 先送一個 header，後面立即接 exact raw PCM。`payload_bytes` 必須為正偶數、不超過 64 MiB、等於 `sample_count * 2` 且 SHA-256 吻合：

```json
{
  "protocol": 1,
  "event": "PCM",
  "request_id": 1,
  "sample_rate_hz": 16000,
  "channels": 1,
  "sample_format": "S16_LE",
  "sample_count": 32000,
  "payload_bytes": 64000,
  "pcm_sha256": "<64 hex>"
}
```

`CANCELLED`、`CANCEL_DEFERRED`、`ERROR` 與 `SHUTDOWN_ACK` 的 lifecycle meaning 同 §2.2。允許的 TTS request code 為 `INVALID_TEXT`、`GENERATION_REJECTED`、`INVALID_PCM`；identity、protocol、crash 與 cleanup failure 仍是 backend failure。

## 4. LLM startup / readiness lifecycle

本節以Accepted R3 winner manifest固定M4b child protocol。Exact model/runtime/config identity見
`model_spec.md` §6；以下lifecycle、token、deadline與exact-key wire schema不得退回「Engine建好
即READY」。

### 4.1 Startup states

```text
STARTING
  -> AUTHENTICATED
  -> ENGINE_LOADED
  -> PREWARMING
  -> INFERENCE_READY
```

- 靜態runtime/model/config/chat-template/schema先在startup timing外完成checksum與strict identity
  驗證；READY路徑不得重新hash完整model。
- `ENGINE_LOADED`只表示LiteRT-LM Engine建構完成，不接受GENERATE、不解除RM recovery
  barrier，也不使`LLMEngineAdapter.start()` return。
- 每次child process/service start都必須執行一次固定、公開、非敏感pre-warm。它必須經過與
  production相同的chat template、model tokenizer、rendered-token檢查、constrained-output與
  disposable `Conversation`；不得用fake backend或不同prompt path代替。
- Pre-warm成功後先`close()` Conversation、清除Python/shared reference並丟棄output、KV與
  history；只有absence/cleanup assertion成立才進`INFERENCE_READY`。
- wire event可繼續命名`READY`以維持common framing相容，但其唯一合法語意是
  `INFERENCE_READY`。Engine load完成不得提前emit READY。
- Pre-warm duration屬startup availability；記入sanitized engine-load/pre-warm timing與public
  prompt digest，不計入第一個使用者request latency，也不得log prompt/output text。

### 4.2 Token and output boundaries

- Parent/child以該exact model tokenizer驗chat-template rendered input，超過128 tokens時在
  inference前fail closed；runtime benchmark回報的`prefill_tokens`也必須在`1..128`。
- Output ceiling為128 tokens；Engine capacity為1024 tokens。兩者不得與rendered input limit
  混用。
- Constrained output、Reasoner schema validation、current-turn action / capability binding與product
  allowlist是獨立判定；pre-warm或token limit通過不能替代任一項。Gate 2B
  narrow harness的current / forbidden / prior literal是不可改寫的POC evidence，不是Core
  generic renderer的production欄位或Gate 3 exact-literal contract。
- 每次user operation建立fresh single-turn Conversation並在`finally` deterministic close；不得
  跨request/session重用Conversation、hidden history或KV state。

### 4.3 Watchdogs and terminal observation

- Engine-load/pre-warm、first-token、generation與terminal observation使用不同deadline/telemetry；
  不以單一outer timeout混合歸因。
- scored/production generation deadline為15秒。Child deadline到期後必須停止generation並emit
  typed `TIMEOUT`/`ERROR` terminal。
- Parent最多另等2秒terminal-observation-only grace以接收child-owned terminal；grace內收到的
  late generation result仍是timeout，不得轉Pass或normal result。
- deadline/cancel路徑須先辨識專用Cancelled型別，再處理其`RuntimeError`等父類；測試必須
  capture worker outcome、join thread/process並禁止unhandled-thread warning false-pass。
- child破壞或Engine recycle後，replacement同樣從AUTHENTICATED重走load + mandatory pre-warm；
  recovery barrier只在新child `INFERENCE_READY`後解除。

### 4.4 Exact wire schema

Selected Pi wire authority是execution SHA`0c755...`的
`poc_llm/contracts/m1/protocol-frame-pi.schema.json`，SHA-256
`e1af3bc5f83f1456d393d30acd9bcf9b9a8a7f91cbdcbe7aa0136a17c275301e`。LLM frame一律使用
`protocol_version="snowboard.llm/1"`。READY只在§4.1完成後送出；
`state="READY"`等同`INFERENCE_READY`：

```json
{
  "type": "READY",
  "protocol_version": "snowboard.llm/1",
  "state": "READY",
  "identity": {
    "candidate_id": "CAND-LRT-G4E2B-MOBILE-R1",
    "pairing_revision": "litert-lm-v0.16.0-pi-g2b-r5",
    "platform": "pi-debian13-aarch64",
    "runtime_sha256": "5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00",
    "model_sha256": "181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c",
    "config_sha256": "c4557b018733ce8a2f4aa46b375cc7dafb31fbd8c363271deb1156c651e5171e"
  }
}
```

Parent以structured `ReasoningInput`送GENERATE，不傳已rendered prompt；child才套用frozen chat
template並執行tokenizer boundary。`input` exact schema沿用Ch 2b：perceptions最多16筆、
`pending_message_count >= 0`，capabilities分為unique perceptions/actions/tools；tool只傳name、
description與JSON input schema，不傳handler。POC schema authority是execution SHA
`0c75536e6ee99b502c59438989ca852194648946`的
`poc_llm/contracts/m1/prompt-input.schema.json`，SHA-256
`aca834bb448f88dfb403c74c427b5462922ccf23f4f26c1944c47d5731522de6`：

```json
{
  "type": "GENERATE",
  "protocol_version": "snowboard.llm/1",
  "request_id": "llm.1.1",
  "input": {
    "perceptions": [{"kind":"listen","status":"ok","text":"<private>"}],
    "pending_message_count": 0,
    "capabilities": {
      "perceptions": ["listen"],
      "actions": ["speak","rest"],
      "tools": []
    }
  }
}
```

Core product projection另固定下列比JSON Schema更窄的canonical invariant：

- `input` exact keys為`perceptions/pending_message_count/capabilities`；不得含session、turn、
  correlation、pending message ID、`PerceptionResult.extra`或任何handler/control；
- perception exact keys為`kind/status/text`，kind依`listen/read/look`排序且不可重複，status只允許
  `ok/timeout/error`，text是最多4096 code point的string；Ch 1的`None`映射成空string但status不變；
- pending count是非bool integer；perception/action arrays分別依`listen/read/look`與
  `speak/tool/rest` canonical order，無duplicate；`rest`必須存在；
- tool依name排序且name不可重複；每筆exact keys為`name/description/input_schema`，name符合Ch 9
  dotted pattern、description非空、input schema是Ch 9已驗證的closed JSON object；
- `tool` action與tools須同時存在或同時缺席；`speak/tool`只有在至少一個available perception時可列入；
- parent在write前完成上述驗證，以`ensure_ascii=False, sort_keys=True`和compact separators編碼，
  newline前UTF-8仍須`<=16 KiB`。排序只固定sender bytes；receiver不得依賴JSON member order。

本地well-formed private content超過4096 code point／16 KiB時，在write前形成sanitized
`ReasoningInputTooLarge`且child side effect為零；它是Reasoner可走P5的input-boundary結果，不得
偽裝成IPC protocol failure。Unknown/duplicate kind、negative count、invalid static tool schema或缺rest
則是`ReasoningInputContractError`，走ERROR而非P5；空content的static projection超過16 KiB須在startup
preflight fatal。

成功result只帶Ch 9可正規化的`speak/tool/rest` response與sanitized metrics。Base response authority
是同一execution SHA的`poc_llm/contracts/m1/response.schema.json`，SHA-256
`4be45ee60f603d7349ff5fb29b667d6e59970dd0be3ce9176c03e923e0a6fca2`。Metrics exact keys為
`init_ms`、`ttft_ms`、`prefill_tokens`、`prefill_tokens_per_second`、`decode_tokens`、
`decode_tokens_per_second`、`kv_tokens`；`prefill_tokens`須在1～128、`decode_tokens`在1～128、
`kv_tokens`在1～1024，否則parent拒絕result：

```json
{
  "type": "RESULT",
  "protocol_version": "snowboard.llm/1",
  "request_id": "llm.1.1",
  "response": {
    "action_kind": "speak",
    "action_payload": {"text":"<private validated text>"},
    "next_perceptions": ["listen"]
  },
  "metrics": {
    "init_ms": 0.0,
    "ttft_ms": 500.0,
    "prefill_tokens": 64,
    "prefill_tokens_per_second": 120.0,
    "decode_tokens": 32,
    "decode_tokens_per_second": 10.0,
    "kv_tokens": 96
  },
  "state": "READY"
}
```

`metrics`在wire可省略以相容schema，但production parent必須要求它存在並套用上述boundary；
缺失不得當作成功。所有時間/rate必須是finite、非bool number；時間`>=0`，token rate`>0`。
Response exact action規則：`speak` payload只有nonblank `text`且
`next_perceptions`非空；`tool` payload只有合法dotted `name`與object `arguments`且
`next_perceptions`非空；`rest` payload與`next_perceptions`皆空。Parent仍須用Ch 9 product
validator及capability/tool allowlist再次驗證，child自稱valid不具權威。

Control與terminal：

```json
{"type":"CANCEL","protocol_version":"snowboard.llm/1","request_id":"llm.1.1"}
{"type":"CANCELLED","protocol_version":"snowboard.llm/1","request_id":"llm.1.1","state":"READY"}
{"type":"ERROR","protocol_version":"snowboard.llm/1","request_id":"llm.1.1","code":"TIMEOUT","state":"READY"}
{"type":"PING","protocol_version":"snowboard.llm/1"}
{"type":"PONG","protocol_version":"snowboard.llm/1","state":"READY"}
{"type":"SHUTDOWN","protocol_version":"snowboard.llm/1"}
{"type":"SHUTDOWN_ACK","protocol_version":"snowboard.llm/1"}
```

ERROR code只允許`BUSY`、`INVALID_REQUEST`、`TIMEOUT`、`GENERATION_FAILED`、
`CANCEL_FAILED`、`PROTOCOL_ERROR`。`BUSY` state=`GENERATING`；`TIMEOUT`／
`GENERATION_FAILED`完成request cleanup後state=`READY`；`CANCEL_FAILED`／`PROTOCOL_ERROR`
state=`FATAL`並進Level 2 termination/rebuild，不得同child繼續。`INVALID_REQUEST`可在READY或
GENERATING拒絕該frame，但不得改變目前active request。每個request恰有一個RESULT、CANCELLED
或ERROR terminal；late/duplicate/wrong-ID frame皆protocol failure。

Core parent對code的產品映射固定為：

- write前local input rejection、active request的`INVALID_REQUEST/READY`（例如rendered input
  超過128 token）、`TIMEOUT/READY`與`GENERATION_FAILED/READY`，只有在Conversation/reference
  cleanup已證明且child確實回READY時才是Reasoner可翻譯的P5結果；explicit backend refusal若runtime
  有typed signal，也正規化成`GENERATION_FAILED/READY`，wire不新增private refusal text；
- `BUSY`、active request收到`INVALID_REQUEST/GENERATING`，或production parent收到任何第二request
  rejection，代表single-flight/desync違約並走protocol failure，不可P5；
- `CANCELLED`由取消來源決定：Reasoner自身deadline可在cleanup後P5，session interrupt/shutdown則
  不publish fallback Fact；
- `CANCEL_FAILED`、`PROTOCOL_ERROR`、wrong/late/duplicate frame、EOF或cleanup未證明一律fatal，
  terminate/waitpid並交RM recovery。

## 5. State / terminal rules

| State | Legal input | Legal output / next state |
| :--- | :--- | :--- |
| STARTING | none | READY→READY；其他→backend failure |
| READY | 該child的BEGIN或GENERATE；SHUTDOWN | operation→BUSY；SHUTDOWN_ACK→STOPPED |
| BUSY capture | FRAME / CANCEL | FRAME_ACCEPTED keeps capture；ENDPOINT keeps BUSY inference；CANCELLED/ERROR→READY |
| BUSY inference/generation | CANCEL | RESULT/PCM/ERROR/CANCELLED→READY；CANCEL_DEFERRED keeps BUSY |
| DESTROYED | none | only RM recovery may spawn and validate replacement |

每個 request 恰允許一個 terminal（`RESULT`、`PCM`、`ERROR`、`CANCELLED`）。`FRAME_ACCEPTED`、`ENDPOINT` 與 `CANCEL_DEFERRED` 是 nonterminal。Terminal 後任何同 request late event 都是 protocol failure；parent 不得跨 request ID 合併 output。

## 6. Test requirements

Portable protocol tests 覆蓋 fragmented read、coalesced header/payload、wrong/duplicate request ID、wrong sequence/length/hash、max boundary、extra key、invalid UTF-8/JSON、BUSY、EOF 與 late terminal。Lifecycle tests 覆蓋 READY mismatch cleanup、cooperative cancel、deferred cancel→force-abort、TERM→KILL→waitpid、nested descendant cleanup、same-owner rebuild 與 next-request success。

Pi evidence 驗 exact real READY fields 與 product lock，但不保存 private `text` 或 PCM；只記 sanitized status、hash、size、latency、PID/exit 與 cleanup count。

LLM portable/target tests另須覆蓋：Engine-loaded但pre-warm未完成時拒絕GENERATE、pre-warm
failure不emit READY、pre-warm Conversation/output/KV/reference清除、每次restart/rebuild重跑、
rendered 129-token pre-inference拒絕、runtime prefill >128拒絕、128-token boundary success、
schema/marker各自fail closed、15秒generation與2秒terminal-only grace不混判，以及cancel subclass
不被父類包裝且zero unhandled-thread warning。Pi evidence只保存timing/token counts/public digest與
terminal/cleanup identity，不保存pre-warm或user prompt/output。
