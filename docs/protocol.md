# Snowboard child-process protocols

狀態：Audio Protocol v1保持Accepted；LLM `snowboard.llm/2`為MVA revision draft，待Architecture／Reviewer／profile／Tester簽核。

本文件固定 Core controller 與其直接擁有 child 之間的 private wire schema。它不是公開 network API；child 不得 listen socket、連網或接受任意外部 client。Audio runtime baseline 與 artifact identity 見 `model_spec.md`，lifecycle owner 與 recovery 見 `implement/ch_m4a_audio_production.md`。

## 1. Common framing

- Parent 以 `start_new_session=True` 啟動每個 top-level child，使 child PID=PGID；ASR supervisor 的 native whisper descendant 不得建立 nested session/group。
- Control 為單行 UTF-8 JSON，以 `\n` 終止，最大 16 KiB。Object 必須 exact-key；Audio使用`protocol: 1`，LLM使用`protocol_version: "snowboard.llm/2"`，unknown/missing/extra key一律protocol error。
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

## 4. LLM MVA protocol M4B-MVA — review draft

Status：Architecture / design / measured profile / test-spec approval pending。
[Current M4B design](implement/ch_m4b_llm_production.md)是session與Reasoner policy權威。
本節取代原LLM snowboard.llm/1；Audio §2/§3不變。舊wire只屬歷史candidate，
不得以M4B-MVA frame配舊profile或未更新的R1 cards。Breaking version固定snowboard.llm/2。

### 4.1 Framing and identity

一frame一行UTF-8 JSON，newline前最多16KiB，strict keys、duplicate JSON keys拒絕。
所有frame必有type、protocol_version；下列欄位表列其餘exact keys。
request_id為llm.<child-generation>.<positive-monotonic-counter>；OPEN/GENERATE/CLOSE
共用counter，每個command一個matching terminal。CANCEL引用被取消command ID，不新建operation。
session_id是不透明nonempty string（最多128 ASCII chars），只用於控制比對，不進model prompt/log。
Counter不能用作session identity。Unknown/wrong generation、late/duplicate terminal、
invalid UTF8/extra keys/EOF在非shutdown時均protocol failure，先cleanup再報fatal。

READY identity exact fields：
candidate_id/pairing_revision/platform/runtime_sha256/model_sha256/config_sha256/
core_profile_id/core_profile_sha256。前六欄保留immutable POC lineage；
config_sha256是原POC provenance，core_profile_sha256是實際新Core設定與surface manifest。
新profile須明確包含renderer/semantic schema/token/lifecycle/sampling/tool-disabled identity，
不能沿用原config digest宣稱新契約。Parent按tracked lock比對每欄，mismatch不admit。

### 4.2 Exact command/result shapes

| type | Additional exact fields | Meaning |
| :--- | :--- | :--- |
| READY | state, identity | state=READY_NO_SESSION；no active Conversation |
| OPEN_SESSION | request_id, session_id, facts | facts固定name/role/locale/available_perceptions/available_actions |
| SESSION_OPENED | request_id, session_id, state | state=SESSION_IDLE；已建立該session Conversation |
| GENERATE | request_id, session_id, turn_id, input | turn_id為positive int，session內遞增；input只有perceptions |
| RESULT | request_id, session_id, semantic, metrics, state | state=SESSION_IDLE；semantic exact text/end |
| CLOSE_SESSION | request_id, session_id, reason | reason為rest/interrupt/error/shutdown/capacity |
| SESSION_CLOSED | request_id, session_id, state | state=READY_NO_SESSION；history/KV/reference close proof |
| CANCEL | request_id, session_id | 取消matching active open/generate/close |
| CANCELLED | request_id, session_id, state | state=READY_NO_SESSION；joined worker及Conversation已清 |
| ERROR | request_id, session_id, code, state | 下表分界，無raw exception或private text |
| SHUTDOWN | 無 | 關閉session/Engine與process |
| SHUTDOWN_ACK | 無 | control ACK不等於process已退出；parent仍waitpid |

facts strings：name/role各nonblank且<=128 codepoints，locale exact zh-TW。
M4 actions exact [speak,rest]、perceptions exact [listen]；不可加入tool/handler。
未具speak/listen的產品profile不啟動LLM對話，Reasoner依能力走rest。
input.perceptions為一筆kind=listen、status=ok/timeout/error、text string <=4096 codepoints；
空或非ok通常由Reasoner在inference前P5，child仍strict驗projection。
No history transcript、pending IDs、raw rendered prompt、tool schema或arbitrary controls。
Session facts與本turn text都屬private pipe資料；只可記profile/case ID及sanitized timing。

semantic與模型輸出同形：end=false要求nonblank text，end=true要求text=""；
text上限由新profile output envelope限制，wire另<=4096 codepoints。
metrics exact keys ttft_ms/ttc_ms/new_input_tokens/output_tokens/kv_tokens。
時間為finite nonnegative non-bool number；native TTFT不可取得時允許null並標該端點無證據，
不得填0冒充量測。TTC以child monotonic完整generate量測，含create若尚未建立；
完整Core caller TTC另由parent/Reasoner量測。token為nonnegative non-bool int，
成功normal output必須output_tokens>0；上下限依新profile，不能假設prefill永遠<=128。
初始control timeout、generation、grace、token/capacity數字在profile freeze後才供formal execution。

### 4.3 State and failure semantics

READY_NO_SESSION只接受OPEN_SESSION/SHUTDOWN。
SESSION_IDLE只接受同session GENERATE/CLOSE_SESSION/SHUTDOWN；
第二個不同session OPEN以SESSION_MISMATCH拒絕，不自動取代。GENERATING/OPENING/CLOSING只接受matching CANCEL。
所有native call在可取消的單一worker執行，control loop仍能收cancel；native取消最多一次。
Thread join與Conversation清除失敗時FATAL；不以假SESSION_CLOSED解除barrier。
重複close在相同session已關閉且未開新session時回matching SESSION_CLOSED；
新session存在時舊close以SESSION_MISMATCH拒絕，不關閉或修改新Conversation。
Wrong/later turn identity拒絕，不容許重送generate造成第二次inference。

| code | State / retained context | Product interpretation |
| :--- | :--- | :--- |
| INPUT_TOO_LARGE | SESSION_IDLE；send_message前拒絕、context完整 | bounded fallback/listen |
| CONTEXT_LIMIT | READY_NO_SESSION；close完整 | session end/rest |
| TIMEOUT / GENERATION_FAILED / INVALID_OUTPUT | READY_NO_SESSION；dirty Conversation discard完整 | session end/rest；不silent replay |
| SESSION_MISMATCH | 原READY_NO_SESSION或SESSION_IDLE不變，ERROR回被拒command的session_id | control contract error，不當正常回答；不關閉另一session |
| BUSY / INVALID_REQUEST / PROTOCOL_ERROR / CLEANUP_FAILED | FATAL | destructive cleanup/recovery，不能P5掩蓋 |

External cancel收斂期間不publish正常LLMResponse；已close的session仍等SM end通知才解除
product ownership。Parent low-capacity detection可在收到RESULT後close session、
轉成本地SessionEnded disposition，再由Reasoner rest；不可交付result後silent recycle。
SHUTDOWN時不做recovery；ACK後仍須bounded TERM/KILL/waitpid/IPC cleanup。
Generation/grace期限分開，late RESULT不轉成功；operational timeout不等於產品2–3秒目標。

### 4.4 Readiness and pre-warm

READY只表示已驗identity、Engine與必要profile readiness，且無產品Conversation。
首次startup與same-boot replacement分開，mandatory disposable prewarm不再是通用要求。
Measured profile選定的prewarm須走產品template/schema、驗下一筆收益、close並丟棄其history。
Cold startup無產品SLA；operations仍有bounded watchdog。完整recovery 10秒目標從RM接收
request到barrier解除，驗證與prewarm不得排除。部署快路徑依M4B design §5，不自行跳過hash。

## 5. Audio state / terminal rules

本表適用§2/§3 Audio；LLM M4B-MVA依§4獨立state machine。

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

LLM M4B-MVA需驗session open/reuse/close、所有exit路徑、dirty-context結束、exact version與identity、
Reasoner text/end policy、capacity reserve、可選prewarm與完整recovery accounting。
自動schema/cleanup不取代人工語意；詳細修訂見[TR_spec_M4B_IV](reviews/TR_spec_M4B_IV.md)。
