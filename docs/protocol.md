# Snowboard child-process protocols

狀態：Audio Protocol v1 Reviewer approved；LLM Protocol v1 Designer complete、queued for single full M4b review，shipping READY identity待Gate 2B final input。

本文件固定 Core controller 與其直接擁有 child 之間的 private wire schema。它不是公開 network API；child 不得 listen socket、連網或接受任意外部 client。Audio runtime baseline 與 artifact identity 見 `model_spec.md`，lifecycle owner 與 recovery 見 `implement/ch_m4a_audio_production.md`。

## 1. Common framing

- Parent 以 `start_new_session=True` 啟動每個 top-level child，使 child PID=PGID；ASR supervisor 的 native whisper descendant 不得建立 nested session/group。
- Control 為單行 UTF-8 JSON，以 `\n` 終止，最大 16 KiB。Object 必須 exact-key、`protocol: 1`；unknown/missing/extra key 一律 protocol error。
- `request_id` 是在單一 child lifetime 內由 parent 配置的正整數，嚴格遞增且不可重用。所有 operation event 帶相同 ID；READY/SHUTDOWN 不帶 request ID。
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

## 4. State / terminal rules

| State | Legal input | Legal output / next state |
| :--- | :--- | :--- |
| STARTING | none | READY→READY；其他→backend failure |
| READY | 該child的BEGIN或GENERATE；SHUTDOWN | operation→BUSY；SHUTDOWN_ACK→STOPPED |
| BUSY capture | FRAME / CANCEL | FRAME_ACCEPTED keeps capture；ENDPOINT keeps BUSY inference；CANCELLED/ERROR→READY |
| BUSY inference/generation | CANCEL | RESULT/PCM/ERROR/CANCELLED→READY；CANCEL_DEFERRED keeps BUSY |
| DESTROYED | none | only RM recovery may spawn and validate replacement |

每個 request 恰允許一個 terminal（`RESULT`、`PCM`、`ERROR`、`CANCELLED`）。`FRAME_ACCEPTED`、`ENDPOINT` 與 `CANCEL_DEFERRED` 是 nonterminal。Terminal 後任何同 request late event 都是 protocol failure；parent 不得跨 request ID 合併 output。

## 5. Test requirements

Portable protocol tests 覆蓋 fragmented read、coalesced header/payload、wrong/duplicate request ID、wrong sequence/length/hash、max boundary、extra key、invalid UTF-8/JSON、BUSY、EOF 與 late terminal。Lifecycle tests 覆蓋 READY mismatch cleanup、cooperative cancel、deferred cancel→force-abort、TERM→KILL→waitpid、nested descendant cleanup、same-owner rebuild 與 next-request success。

Pi evidence 驗 exact real READY fields 與 product lock，但不保存 private `text` 或 PCM；只記 sanitized status、hash、size、latency、PID/exit 與 cleanup count。

## 6. LLM Protocol v1（Designer complete；single full M4b review pending）

本節只固定Core parent與其直接擁有的LLM child之engine-agnostic wire contract。Final engine、model、
quantization、runtime與profile checksum須在M4b Gate 2B final winner ACK後由`model_spec.md`固定；
在此之前不得把POC candidate identity預寫成product READY值。

### 6.1 Parent → child

每次generate先送一個bounded prompt header，再立即送exact UTF-8 payload；sampling、token上限與
model identity均在startup strict config / product lock固定，不得逐request覆寫：

```json
{"protocol":1,"op":"GENERATE","request_id":1,"prompt_utf8_bytes":4096,"prompt_sha256":"<64 hex>"}
```

Header受§1的16 KiB control上限；其後payload不加delimiter，以
`readexactly(prompt_utf8_bytes)`讀取。Prompt必須nonempty、valid UTF-8、無NUL、SHA-256吻合且不超過
256 KiB。Parent在寫pipe前拒絕空值／超限，child在交runtime前驗length/hash/UTF-8；不截斷、
不scan delimiter、不把payload寫入log。

Cooperative cancellation與shutdown：

```json
{"protocol":1,"op":"CANCEL","request_id":1}
```

```json
{"protocol":1,"op":"SHUTDOWN"}
```

### 6.2 Child → parent

READY只在selected runtime/model/profile identity驗證且persistent engine完成載入後送出：

```json
{
  "protocol": 1,
  "event": "READY",
  "pid": 3456,
  "pgid": 3456,
  "runtime_lock_sha256": "<64 hex>",
  "runtime_artifact_sha256": "<64 hex>",
  "model_sha256": "<64 hex>",
  "profile_sha256": "<64 hex>"
}
```

Streaming chunk為nonterminal；`sequence`從0逐一遞增，`text`可存在於private pipe但不得log：

```json
{"protocol":1,"event":"CHUNK","request_id":1,"sequence":0,"text":"<private UTF-8 chunk>"}
```

每個CHUNK受16 KiB control上限；parent另以256 KiB aggregate UTF-8上限收集。超限、錯序、空chunk、
invalid UTF-8、wrong request ID或terminal後chunk均為protocol failure，不回傳partial output。

Successful terminal不重送完整文字，只驗證parent已收集內容的identity：

```json
{
  "protocol": 1,
  "event": "RESULT",
  "request_id": 1,
  "finish_reason": "stop",
  "chunk_count": 3,
  "output_utf8_bytes": 512,
  "output_sha256": "<64 hex>"
}
```

`finish_reason`只允許`stop`、`max_tokens`、`refused`。Parent驗chunk count、aggregate byte count與
SHA-256後才建立`LLMGeneration`；不吻合是protocol failure。`refused`與空白aggregate由Reasoner
走P5 fallback；`max_tokens`仍須通過完整product validator，不代表截斷JSON可接受。

Normal cooperative cancel terminal：

```json
{"protocol":1,"event":"CANCELLED","request_id":1}
```

若selected runtime沒有可靠native cancel，child回nonterminal：

```json
{"protocol":1,"event":"CANCEL_DEFERRED","request_id":1}
```

此時parent `abort()`保持pending；child即使native generation稍後自然完成也必須丟棄output並回
CANCELLED，不得再回CHUNK / RESULT。Ch 6 Level 1 timeout後由`force_abort()`終止完整process group。

可恢復request error清除request-local conversation後回READY：

```json
{"protocol":1,"event":"ERROR","request_id":1,"code":"GENERATION_REJECTED"}
```

允許code為`INVALID_PROMPT`、`GENERATION_REJECTED`、`OUTPUT_LIMIT`。Identity mismatch、invalid
framing、engine crash、EOF、cleanup failure或hidden-history reset failure不是request ERROR。

Clean shutdown：

```json
{"protocol":1,"event":"SHUTDOWN_ACK"}
```

ACK後child釋放engine、清request-local state並exit zero；parent仍須waitpid。

若child在BUSY時收到第二個GENERATE，防禦性拒絕該新request且保留原active request：

```json
{"protocol":1,"event":"BUSY","request_id":2,"active_request_id":1}
```

BUSY只終結被拒絕的第二個request；child須先bounded read並丟棄該request已宣告的prompt payload，
避免pipe失去frame alignment，且不得把它交runtime。原active request仍依自己的CHUNK / terminal
完成。正常parent adapter以single-flight lock保證不送出此序列，portable negative test仍須覆蓋
child防線。

### 6.3 LLM state and terminal rules

| State | Legal input | Legal output / next state |
| :--- | :--- | :--- |
| STARTING | none | READY→READY；其他→backend failure |
| READY | GENERATE；SHUTDOWN | GENERATE→BUSY；SHUTDOWN_ACK→STOPPED |
| BUSY | CANCEL；defensive second GENERATE | CHUNK keeps BUSY；RESULT/ERROR/CANCELLED→READY；CANCEL_DEFERRED keeps BUSY；BUSY只拒絕second request |
| DESTROYED | none | only RM recovery may spawn and validate replacement |

每個accepted request恰允許一個terminal（RESULT、ERROR、CANCELLED）；BUSY是未被接受之second
request的唯一terminal。CHUNK與CANCEL_DEFERRED是nonterminal。第二個GENERATE不排隊；terminal後
任何同request frame、cross-request sequence或late output都是backend protocol failure。

### 6.4 LLM protocol test requirements

Portable tests覆蓋fragment/coalesce、prompt length/hash/UTF-8與max prompt/chunk/aggregate boundary、
extra/missing key、wrong/duplicate request ID、chunk sequence、byte count/hash、unknown finish reason、
BUSY discard/alignment、EOF、late terminal、CANCELLED、CANCEL_DEFERRED及sanitized stderr。
Lifecycle tests覆蓋READY mismatch cleanup、
persistent child + fresh conversation、TERM→KILL→waitpid、descendant cleanup、same-lock rebuild與
next-request success。

Pi evidence驗real READY與product lock、engine load count、five-turn history isolation及cleanup count；
只保存sanitized status、output hash/size、latency、PID/exit與artifact checksum，不保存prompt、CHUNK、
完整model output或tool payload。
