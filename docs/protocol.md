# Snowboard child-process protocols

狀態：Audio Protocol v1保持Accepted；M4B replacement LLM Protocol
`snowboard.llm/3`已完成原 focused review，並依 `IR_dev_M4B_IV` 修訂 ticket disposal；focused Tester coverage已確認。

本文件固定 Core controller 與其直接擁有 child 之間的 private wire schema。它不是公開 network API；child 不得 listen socket、連網或接受任意外部 client。Audio runtime baseline 與 artifact identity 見 `model_spec.md`，lifecycle owner 與 recovery 見 `implement/ch_m4a_audio_production.md`。

## 1. Common framing

- Parent 以 `start_new_session=True` 啟動每個 top-level child，使 child PID=PGID；ASR supervisor 的 native whisper descendant 不得建立 nested session/group。
- Control 為單行 UTF-8 JSON，以 `\n` 終止，最大 16 KiB。Object 必須 exact-key；Audio使用
  `protocol: 1`，LLM 使用 `protocol: 3`。兩者不接受另一版本或 legacy LLM framing。
- `request_id`由parent在單一child lifetime內配置、嚴格遞增且不可重用，且為正整數。Audio與
  LLM operation event皆帶 matching ID；CANCEL只引用目前active ID而不另配ID；
  READY/PING/PONG/SHUTDOWN不帶 request ID。
- Binary payload 只允許在 schema 明列的 header 後立即出現，parent/child 以 `readexactly(payload_bytes)` 讀取。不得 scan delimiter、部分接受或無界 buffer。
- 一次只允許一個 active request。Audio第二個 BEGIN/GENERATE 在第一個 terminal 前以 `BUSY`
  拒絕；LLM任何reentrant operation是protocol E1。兩者皆不排隊。
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

## 4. LLM Protocol v3 — `snowboard.llm/3`

### 4.1 Identity and common rules

The dedicated LLM child is spawned with PID=PGID and owns the LiteRT-LM Engine, tokenizer, chat renderer,
Conversation and all native requests. Core process owns framing, policy and lifecycle. Text fields are private IPC
data and follow §1 no-log/no-evidence rules.

READY is emitted only after exact ABI/runtime/model/artifact/profile verification, Engine load and tokenizer
attestation, with no Conversation:

```json
{
  "protocol":3,
  "event":"READY",
  "protocol_name":"snowboard.llm/3",
  "pid":3456,
  "pgid":3456,
  "candidate_id":"CAND-LRT-G4E2B-MOBILE-R1",
  "pairing_revision":"litert-lm-v0.16.0-pi-g2b-r5",
  "profile_id":"core-m4b-cognition-001",
  "profile_stage":"release",
  "profile_sha256":"<64 hex>",
  "runtime_sha256":"5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00",
  "native_sha256":"9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4",
  "model_sha256":"181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c",
  "prompt_sha256":"872ae6b6418761b271cd6762c08eeaabe1f20d3a1c4aa72602a09eab1f1eb643",
  "response_schema_locator":"requirements/m4b/semantic-output-v1.schema.json",
  "response_schema_sha256":"796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9",
  "prompt_tokens":66,
  "max_output_tokens":128,
  "engine_context_tokens":1024,
  "temperature":0.0,
  "top_p":1.0,
  "threads":4,
  "min_mem_available_generate_bytes":123456789,
  "min_mem_available_speak_bytes":12345678,
  "conversation_state":"none",
  "network":"disabled"
}
```

Parent compares every field with the authenticated product lock. It does not accept a matching overall digest as
a substitute for field checks. Positive memory values above are schema examples, not product defaults; the release
profile carries the reviewed measured byte values. The dedicated measurement harness instead requires
`profile_stage="measurement"` and both memory fields null; normal application composition rejects that form.
Unknown/extra/missing/mismatched fields terminate and waitpid the process group; the child never falls back to
another model, runtime, profile or endpoint.

### 4.2 Conversation lifecycle

Open one clean Conversation:

```json
{"protocol":3,"op":"OPEN","request_id":1,"session_id":"<private>","generation":1}
```

Successful terminal:

```json
{"protocol":3,"event":"OPENED","request_id":1,"session_id":"<private>","generation":1,"conversation_revision":0}
```

Clean open rejection is terminal and legal only after the failed object is unusable and cleaned:

```json
{"protocol":3,"event":"OPEN_REJECTED","request_id":1,"session_id":"<private>","generation":1,"code":"OPEN_REJECTED","cleanup_proven":true,"engine_usable":true}
```

Any false proof flag maps to E1 rather than R2. OPENED means the Conversation is exclusively claimed, contains
only the fixed system prompt, accepts MEASURE and has no user/assistant turn.

Close reasons are exactly `replace_context`, `replace_generation_failure`, `session_end`, `interrupt`, `error`,
`shutdown` or `memory_pressure`:

```json
{"protocol":3,"op":"CLOSE","request_id":8,"session_id":"<private>","generation":1,"reason":"replace_context"}
```

The child discards any unconsumed measurement ticket, proves the native request terminal, destroys
Conversation-local history/KV/references, and returns:

```json
{"protocol":3,"event":"CLOSED","request_id":8,"session_id":"<private>","generation":1,"request_terminal_proven":true,"cleanup_proven":true,"engine_usable":true}
```

Only all-three-true is a replacement proof. For session end, false proof remains an E1 convergence target and may
require Level 2/RM recovery. CLOSED returns the child to Engine READY with no Conversation; allocator PSS need not
drop immediately.

### 4.3 Non-mutating measurement

With one active clean/usable Conversation, parent requests exact tokenizer/renderer counts:

```json
{"protocol":3,"op":"MEASURE","request_id":2,"session_id":"<private>","generation":1,"text":"<private normalized listen text>","input_sha256":"<64 hex>","output_reserve_tokens":128}
```

Terminal response:

```json
{
  "protocol":3,
  "event":"MEASURED",
  "request_id":2,
  "session_id":"<private>",
  "generation":1,
  "conversation_revision":0,
  "input_sha256":"<64 hex>",
  "ticket":"<opaque 128-bit lowercase hex>",
  "user_tokens":10,
  "current_kv_tokens":0,
  "rendered_incremental_tokens":84,
  "runtime_prefill_tokens":84,
  "output_reserve_tokens":128,
  "engine_context_tokens":1024
}
```

MEASURE must not append a semantic message, allocate output KV or call generation. Counts are exact non-negative
integers from the same tokenizer/chat renderer as GENERATE. `conversation_revision` is monotonic within one
generation and increments exactly once after a successful RESULT. Non-mutation here means unchanged semantic
history/KV/revision and no native send: the pinned renderer necessarily replaces its private
`last_rendered_message` scratch. Before MEASURED the child releases Python request/tokenizer temporaries; while the
ticket is outstanding, that native rendered scratch is the only permitted child-side private-text retention. The
ticket ledger contains only opaque value, identity, digest, revision and integer counts. Parent supplies text again
for GENERATE. CLOSE destroys the Conversation and any outstanding ticket/scratch.

### 4.4 Explicit ticket disposal

When product admission rejects a measured input while keeping the Conversation, parent must dispose of the exact
outstanding ticket:

```json
{"protocol":3,"op":"DISCARD_TICKET","request_id":3,"session_id":"<private>","generation":1,"conversation_revision":0,"ticket":"<opaque 128-bit lowercase hex>","input_sha256":"<64 hex>"}
```

The child exact-matches all binding fields, records current Conversation token count, and invokes the already
pinned native renderer once with fixed non-private scrub text `"__M4B_TICKET_SCRUB__"`. The returned fixed turn
rendering replaces native `last_rendered_message` and token count must remain unchanged. The child then clears
ticket binding metadata and emits the terminal:

```json
{"protocol":3,"event":"TICKET_DISCARDED","request_id":3,"session_id":"<private>","generation":1,"conversation_revision":0,"ticket":"<opaque 128-bit lowercase hex>","input_sha256":"<64 hex>","native_render_scrubbed":true,"ticket_invalidated":true,"private_input_erased":true,"conversation_state":"ready"}
```

Only an exact terminal with all three proof booleans true returns the unchanged Conversation to
`CONVERSATION_READY`. Generation, revision, history and KV remain unchanged. The old ticket can never authorize
later GENERATE. `private_input_erased` proves no live child/native object reference retains the rejected text; it
does not claim forensic zeroization of freed allocator capacity. Reasoner releases its normalized-text local before
issuing snapshot-only DISCARD_TICKET and its snapshot after validating the terminal, both before returning R1.
Scrub/render failure, token-count change,
stale/mismatched/duplicate discard, wrong identity, false/missing proof or another terminal is E1.
DISCARD_TICKET is a bounded atomic metadata operation and does not accept CANCEL. If its terminal times out, is
malformed, or is lost to EOF, parent cannot claim disposal or return a clean product outcome: it terminates/kills
and waitpids the PGID through the existing E1 boundary. If invalidation occurred but its acknowledgement was lost,
that destruction remains the only safe convergence.

### 4.5 Generation and semantic terminals

Parent may generate only with the latest bound ticket and identical private text/digest:

```json
{"protocol":3,"op":"GENERATE","request_id":3,"session_id":"<private>","generation":1,"conversation_revision":0,"ticket":"<opaque 128-bit lowercase hex>","text":"<private normalized listen text>","input_sha256":"<64 hex>"}
```

The ticket is consumed before native send and can never be reused. While generation is active, the child may emit
ordered semantic fragments:

```json
{"protocol":3,"event":"SAFE_TEXT","request_id":3,"sequence":0,"text":"<private decoded semantic fragment>","monotonic_ns":123456789}
```

`sequence` begins at zero without gaps or duplicates. SAFE_TEXT is nonterminal and must follow the S2 prefix rules
in `implement/ch_m4b_llm_production.md` §4.2.

Successful terminal:

```json
{
  "protocol":3,
  "event":"RESULT",
  "request_id":3,
  "session_id":"<private>",
  "generation":1,
  "conversation_revision":1,
  "text":"<private normalized semantic text>",
  "end":false,
  "user_tokens":10,
  "current_kv_tokens":0,
  "rendered_incremental_tokens":84,
  "runtime_prefill_tokens":84,
  "decode_tokens":20,
  "conversation_kv_tokens":104,
  "llm_send_monotonic_ns":123400000,
  "first_safe_text_monotonic_ns":123456789,
  "terminal_monotonic_ns":123500000
}
```

The child sends RESULT only after constrained JSON terminal validation by a duplicate-aware JSON decoder when raw
JSON is exposed, or direct exact response-schema validation when LiteRT-LM returns an already-decoded mapping,
plus safe-fragment prefix proof and native request join. `first_safe_text_monotonic_ns` is null when no fragment
was emitted. Metrics must match the consumed
ticket and be monotonic/nondecreasing; impossible values are protocol failure.

A post-send failure may use the normal R2 path only after native terminal/join proof and while Engine remains
usable:

```json
{"protocol":3,"event":"REQUEST_FAILED","request_id":3,"session_id":"<private>","generation":1,"code":"INVALID_SEMANTIC","request_terminal_proven":true,"engine_usable":true,"terminal_monotonic_ns":123500000}
```

Allowed codes are `INVALID_SEMANTIC`, `GENERATION_REJECTED` and `GENERATION_TIMEOUT`. This terminal taints the
Conversation: only CLOSE/CANCEL convergence is legal next. False proof, unknown code, runtime exception, Engine
loss or any output that cannot reach this terminal is E1 and requires parent cleanup; it is not encoded as a
normal request error.

### 4.6 Cancel and shutdown

Cooperative cancel names the active OPEN/MEASURE/GENERATE/CLOSE request:

```json
{"protocol":3,"op":"CANCEL","request_id":3}
```

If the active native/lifecycle operation cannot yet stop, the child emits nonterminal:

```json
{"protocol":3,"event":"CANCEL_DEFERRED","request_id":3}
```

After operation terminal/join:

```json
{"protocol":3,"event":"CANCELLED","request_id":3,"operation":"GENERATE","request_terminal_proven":true,"operation_cleanup_proven":true,"engine_usable":true,"conversation_state":"tainted"}
```

CANCEL is accepted at most once per active request. `operation` is exactly `OPEN | MEASURE | GENERATE | CLOSE`;
DISCARD_TICKET is deliberately absent because §4.4 makes it atomic and uncancellable.
All three proof booleans must be true for a cooperative operation stop; false/missing proof is E1 and the record
remains a convergence target. Resulting state is fixed by operation:

- cancelled OPEN cleans the unclaimed object and returns `conversation_state="none"` / `ENGINE_READY`;
- cancelled MEASURE invalidates its ticket without mutation and returns
  `conversation_state="ready"` / `CONVERSATION_READY`;
- cancelled GENERATE proves the request stopped but leaves Conversation
  `conversation_state="tainted"` / `TAINTED`, so session convergence must CLOSE it;
- cancelled CLOSE cannot prove Conversation cleanup and therefore uses
  `operation_cleanup_proven=false`, `conversation_state="tainted"`; it is E1 and escalates through the existing
  lifecycle convergence rather than returning to a usable state.

Parent `abort()` remains pending until a valid CANCELLED and outer operation completion. If the control loop or
native request cannot provide proof before Level 1 timeout, parent terminates/kills and waitpids the whole PGID
under Level 2; it does not fabricate CANCELLED, CLOSED or RESULT.

SHUTDOWN is legal only with no Conversation and no active request:

```json
{"protocol":3,"op":"SHUTDOWN"}
```

```json
{"protocol":3,"event":"SHUTDOWN_ACK"}
```

ACK means Engine/runtime resources are closed and no descendant remains; child then exits zero and parent still
waitpids it. Shutdown with an active Conversation is a parent contract error except after Level 2 destruction.

### 4.7 State machine and failure boundary

| Child state | Legal parent input | Legal output / next state |
| :--- | :--- | :--- |
| `STARTING` | none | READY → `ENGINE_READY`; other output/EOF → E1 |
| `ENGINE_READY` | OPEN, SHUTDOWN | OPEN → `OPENING`; SHUTDOWN_ACK → `STOPPED` |
| `OPENING` | one matching CANCEL | OPENED → `CONVERSATION_READY`; OPEN_REJECTED / valid CANCELLED → `ENGINE_READY`; CANCEL_DEFERRED stays |
| `CONVERSATION_READY` | MEASURE, CLOSE | MEASURE → `MEASURING`; CLOSE → `CLOSING` |
| `MEASURING` | one matching CANCEL | MEASURED → `MEASURED`; valid CANCELLED → `CONVERSATION_READY`; CANCEL_DEFERRED stays |
| `MEASURED` | DISCARD_TICKET, GENERATE, CLOSE | DISCARD_TICKET → `DISCARDING`; GENERATE → `GENERATING`; CLOSE discards ticket → `CLOSING` |
| `DISCARDING` | none | exact TICKET_DISCARDED → `CONVERSATION_READY`; timeout/EOF/other output → E1 |
| `GENERATING` | one CANCEL | SAFE_TEXT stays; RESULT → `CONVERSATION_READY`; REQUEST_FAILED/CANCELLED → `TAINTED`; CANCEL_DEFERRED stays |
| `TAINTED` | CLOSE | CLOSE → `CLOSING` |
| `CLOSING` | one matching CANCEL | CLOSED → `ENGINE_READY`; CANCELLED with incomplete Conversation cleanup → E1/parent convergence; CANCEL_DEFERRED stays |
| `DESTROYED` | none | only RM recovery may spawn and fully validate replacement |

Wrong state/order, BUSY/reentrant operation, request/session/generation/revision mismatch, stale/reused ticket,
unknown/extra/missing key, overlong line, invalid JSON/UTF-8, EOF, duplicate/late terminal, fragment sequence/prefix
failure or output after terminal is protocol E1. Parent sanitizes the diagnostic, blocks admission and obtains
termination/cleanup proof before replacement/recovery.

## 5. Audio state / terminal rules

本表只適用 §2/§3 Audio；LLM 使用 §4.7 的獨立狀態機。

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

LLM v3 portable tests另須覆蓋完整 state table、OPEN/CLOSE proof、MEASURE non-mutation、exact count
boundaries、ticket binding/one-use/disposal、SAFE_TEXT fragmentation/prefix、RESULT metrics、REQUEST_FAILED/CANCEL
proof、wrong identity/revision/generation、PGID cleanup及recovery後下一個child成功。不得沿用舊
session、capacity、prewarm或fixed-recycle測試語意。Audio測試要求不變。
