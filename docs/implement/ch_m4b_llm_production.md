# M4B — replacement LLM / Reasoner product design

狀態：**Designer complete / single-PV Test Spec mapping resolved / Developer implementation open**。

本文件是 M4B cognition/product replacement 的現行 implementation-design authority。它從已核准的
[`m4b_foundation_revision`](m4b_foundation_revision.md) 與 `arch.md` 的 Conversation、route、
R1/R2/R3/E1 契約往下定義可實作產品；不復原或相容舊 M4B-MVA design、fresh-Conversation、
action envelope、fake prewarm 或固定 `8/48/768` recycle 行為。

若 generic Ch 2b / 9 / 10 的 M4B legacy 段落與本文件衝突，以本文件為準。Accepted M4A、通用
EventBus / State Manager / Resource Manager、process isolation、offline/privacy 與 Level 1/2/3
收斂保持有效。

## 1. Scope and product boundary

### 1.1 Included

- Raspberry Pi 5 上的 exact LiteRT-LM / Gemma product identity、離線啟動與 child isolation。
- 一個 Product Session 內重用一個真實 Conversation，並在 cleanup proof 後 sequentially replace。
- listen-only perception projection、V2D2-based system prompt、constrained JSON `text/end` 與安全
  incremental semantic extraction。
- pre-inference input/context/memory admission、Reasoner normalization，以及完整 normal/error outcome
  matrix。
- 新 private LLM child wire、product-profile lock、portable tests 與 Pi evidence contract。
- Audio + LLM vertical slice 的 memory 與 monotonic timing facts，供 M4C 直接消費。

### 1.2 Preserved boundaries

- 每 turn 只有一次 Reasoner inference 與一個 terminal `LLMResponse` Fact。
- Model 只決定短回答 `text` 與對話結束意圖 `end`；Reasoner 才擁有 `action_kind`、
  `post_action_route` 與 `next_perceptions`。
- M4B product profile只實作 `listen` projector 與 `speak/rest` outcome。Generic `read/look/tool`
  capability 契約保留，但不進 M4B real-model acceptance。
- 沒有跨 Product Session memory、transcript store、summary、retrieval、tools 或 vision。
- M4B 只量測 first audio write，不把它稱為 audible onset；M4C 才做整機 Display/State Manager
  composition 與實體 audible-onset acceptance。

### 1.3 Explicit non-scope

- 不設三秒 response target、generation ceiling 或 percentile PASS 門檻。
- 不做 user-supplied personality、任意 prompt suffix、runtime prompt reload 或 prompt presets。
- 不做 context compaction、rejected-input replay、background fake turn 或 prefix-KV snapshot。
- 不讓 LLM 產出 Core action envelope、perception list、tool call、session ID 或 private routing data。

## 2. Frozen product profile surface

### 2.1 Runtime and model identity

| Field | M4B product value |
| :--- | :--- |
| `profile_id` | `core-m4b-cognition-001` |
| candidate / pairing | `CAND-LRT-G4E2B-MOBILE-R1` / `litert-lm-v0.16.0-pi-g2b-r5` |
| target | Raspberry Pi 5 4 GB / Debian 13 aarch64 / CPU / 4 threads |
| Python ABI | target-owned CPython `3.13.5`, SOABI `cpython-313-aarch64-linux-gnu`, MULTIARCH `aarch64-linux-gnu` |
| runtime | LiteRT-LM API `0.16.0`; exact wheel/native identities from `model_spec.md` §6.2 |
| model | `gemma-4-E2B-it.litertlm`; exact source, size and SHA-256 from `model_spec.md` §6.2 |
| sampling | `temperature=0.0`, `top_p=1.0`, CPU threads `4` |
| output reserve | `128` model tokens |
| Engine context | `1024` tokens |
| wire | `snowboard.llm/3`, protocol integer `3` |
| network | disabled before native import and throughout child lifetime |
| prewarm | `none`; no fake message, generation or snapshot |

The product lock repeats every exact identity rather than referring only to a prior digest. POC artifact/config
digests are provenance, not product identity. Missing/extra artifact, alternate endpoint, ABI/runtime/model/hash
mismatch, system-site fallback or network-enabled runtime fails before child spawn.

### 2.2 Exact system prompt

Core bytes, UTF-8 without BOM or trailing newline:

```text
你是「雪板」繁體中文語音助理，只能聽與說，不能看或使用工具。只輸出含 text、end 的 JSON。一般回答的 text 不超過30字且 end=false；明確要求結束時 end=true。語氣：
```

Fixed trusted personality bytes:

```text
溫暖自然，稍帶幽默。
```

| Composition part | POC tokenizer count | SHA-256 |
| :--- | ---: | :--- |
| core | 57 | `8caba35159407882407c1ac1be22c66791ac66236e323bc1b63fa072c1340eec` |
| personality | 9 | `57191898561df177e820a10eed88ad9d47649ba9e5e19c059b554acedda777e5` |
| concatenated system prompt | 66 | `872ae6b6418761b271cd6762c08eeaabe1f20d3a1c4aa72602a09eab1f1eb643` |

The runtime must attest these counts with the selected tokenizer during READY. These three composition counts
belong to the prompt dashboard; they must not be added to every later-turn incremental prefill observation.
M4B exposes no config field that can append or replace these bytes. A future personality/capability revision
requires a new profile ID, prompt hashes, semantic evaluation and review.

## 3. Perception projection and normalization

### 3.1 Supported envelope

The real M4B profile accepts exactly one `PerceptionResult` with `kind="listen"` per turn. The projector never
serializes the Core envelope. Model user content is only the normalized transcript string.

The Reasoner first validates, without touching Conversation state:

1. `perception_results` is a tuple of length one.
2. The item has the matching session/turn identity and `kind == "listen"`.
3. `status` is one of `ok | timeout | error`; only `ok` may carry model input.
4. `pending_message_count == 0` for this voice-only profile.
5. Runtime capability checks for `listen` and `speak` are true.

Multiple items, `read/look`, pending external input, unknown status or identity/capability mismatch is
`UNSUPPORTED_INPUT`, a wiring/contract E1. It is not an application retry and must not call the model.

### 3.2 Exact listen normalization

For `status=ok`, `ListenProjector` applies this deterministic order:

1. Require `str`, then apply Unicode NFKC.
2. Reject NUL, surrogate code points and Unicode general category `Cc` except whitespace `TAB/LF/CR`.
3. Replace every maximal run for which `str.isspace()` is true with one U+0020.
4. Remove leading/trailing U+0020.
5. Count Python Unicode code points with `len(normalized_text)`; spaces count.
6. Tokenize that exact string with the child-attested Gemma tokenizer, without a product envelope or hidden
   prefix.

An empty result is a clean R1 no-input outcome. More than 20 normalized code points or more than 32 direct-user
model tokens is the distinct R1 input-limit outcome. No truncation, summarization or partial send is allowed.

`status=timeout` and `status=error` are also clean R1 outcomes because no model-facing mutation has occurred.
Their `text/extra` data is ignored and never logged.

## 4. Model semantic contract and safe extraction

### 4.1 Constrained JSON

The grammar permits exactly one UTF-8 JSON object with keys in this order and no extras:

```json
{"text":"<JSON string>","end":false}
```

- `text` is a JSON string; `end` is a JSON boolean.
- Whitespace outside strings is grammar-fixed to none.
- Duplicate/unknown/missing keys, non-string text, non-boolean end, trailing bytes and invalid UTF-8/escape are
  invalid terminal output.
- After JSON decoding, text uses NFKC and whitespace collapsing from §3.2. NUL, surrogate or disallowed control
  remains invalid.
- `end=false` requires non-empty text. `end=true` permits empty or non-empty text.

For the 30-character product rule, `spoken_length` is the number of normalized non-whitespace code points whose
Unicode general category does not begin with `P`. Symbols, emoji, letters and numbers count. Text with
`spoken_length > 30` is invalid; Reasoner does not truncate it. The action payload preserves the normalized text,
including punctuation.

### 4.2 S2 incremental extraction

The child feeds decoded model bytes to an incremental parser. It may emit `SAFE_TEXT` only after bytes are
unambiguously decoded inside the `text` JSON string. JSON syntax, escapes, partial UTF-8 and `end` are withheld.

Each fragment must be non-empty and ordered. Concatenated fragments must remain an exact prefix of terminal
normalized `text`; terminal validation must prove this relation. The parser may delay at punctuation or a
24-codepoint boundary, but it may never revise emitted text. Invalid terminal output, prefix mismatch or text
after terminal is protocol/semantic failure; M4C streaming consumers cancel the entire generation/TTS/playback
path as required by `arch.md` §2.8.

M4B runs in full-response action mode: it records first-safe time but does not dispatch `SAFE_TEXT` to Speak.
The protocol surface remains ready for M4C's separately reviewed single streaming-speak control.

## 5. Exact admission

### 5.1 Measurement ticket

Admission occurs after normalization and before `GENERATE`. Parent sends `MEASURE` to the active Conversation;
the child uses the same runtime tokenizer and chat renderer as generation and returns an opaque one-use ticket:

```python
@dataclass(frozen=True, slots=True)
class AdmissionSnapshot:
    ticket: str
    session_id: str
    generation: int
    input_sha256: str
    user_tokens: int
    current_kv_tokens: int
    rendered_incremental_tokens: int
    runtime_prefill_tokens: int
    output_reserve_tokens: int
    engine_context_tokens: int
```

`MEASURE` must not append a message, allocate output KV or start inference. Here non-mutating means no semantic
Conversation history/KV/revision change and no native send; the pinned runtime renderer does overwrite its private
`last_rendered_message` scratch member. `ticket` binds the child generation, Conversation revision, exact normalized
input digest and all counts. Any intervening semantic mutation invalidates it. `GENERATE` consumes the ticket once;
missing/reused/stale/mismatched tickets are E1 protocol failures. Before emitting `MEASURED`, the child releases
Python request/tokenizer temporaries; until GENERATE, DISCARD_TICKET or CLOSE resolves the ticket, the native
rendered scratch is the only permitted child-side private-text retention. The ticket ledger itself may retain only
its opaque value, identity, digest, revision and integer counts. The parent supplies exact text again for GENERATE.

`DISCARD_TICKET` is the explicit non-mutating escape from an outstanding measurement. After exact identity match,
the child calls the existing pinned renderer once with fixed non-private scrub text
`TICKET_SCRUB_TEXT = "__M4B_TICKET_SCRUB__"`. The returned fixed turn rendering replaces native
`last_rendered_message`; child verifies Conversation token count is unchanged and clears its ticket binding. It
does not call native send or invent a runtime clear API. `TICKET_DISCARDED` proves native render scratch
replacement, permanent ticket invalidation and absence of live child/native references to the rejected text; this
is object-lifetime cleanup, not forensic zeroization of freed allocator capacity. Reasoner releases its normalized
text local before issuing DISCARD_TICKET, whose frame is built entirely from the snapshot, and releases the snapshot
after validating the terminal. Only then may it
publish R1. The matching terminal returns the same Conversation to ready state without changing generation,
revision, history or KV. A scrub/count failure, stale/mismatched/duplicate discard, false/missing proof, timeout,
malformed terminal or EOF is E1. Parent obtains PGID destruction proof and may not publish clean R1.
`DISCARD_TICKET` is atomic and has no cooperative CANCEL path.

### 5.2 Token decisions

The hard context equation is:

```text
current_kv_tokens + rendered_incremental_tokens + output_reserve_tokens
    <= engine_context_tokens
```

with `output_reserve_tokens == 128` and `engine_context_tokens == 1024`. All terms are non-negative integers;
the child rejects impossible or internally inconsistent metrics before inference.

- Codepoint-limit rejection (§3.2) returns `speak + KEEP_NEXT` without MEASURE. A codepoint-valid input uses
  non-mutating MEASURE to obtain exact `user_tokens`; `user_tokens > 32` returns the same input-limit outcome and
  must complete matching `DISCARD_TICKET` / `TICKET_DISCARDED` before the parent drops its snapshot and publishes
  R1; its normalized text local is dropped before the snapshot-only discard call. It never uses GENERATE.
  After acknowledged disposal, the same Conversation and revision accept the next turn's MEASURE; repeated
  token-limit rejections follow the same sequence.
- A failed context equation returns application-owned `speak + REPLACE_NEXT`; rejected input is not sent or
  replayed. Replacement starts a clean Conversation and the user must repeat the input.
- For a fresh Conversation, a turn containing exactly one listen of at most 20 normalized code points and at
  most 32 direct-user tokens must report `runtime_prefill_tokens <= 128`. Exceeding 128 is product-profile E1,
  not input-limit or context-limit. Additional future projectors do not inherit this tier.
- Passing the equation authorizes only the bound ticket; it does not guarantee memory admission.

### 5.3 System-memory decision

Immediately before `GENERATE`, the adapter takes one unique-PID memory sample covering Core/controller, ASR,
TTS and LLM owners plus `MemTotal`, `MemAvailable`, swap, temperature and throttling. The eventual release profile
contains two byte thresholds derived from the new vertical slice and adopted through a later design/config delta:

- `min_mem_available_generate_bytes`: minimum for model generation plus the 128-token reserve.
- `min_mem_available_speak_bytes`: minimum for the fixed application notice through TTS/playback.

No source/YAML default is legal for either threshold. A dedicated target measurement harness may use a
`profile_stage="measurement"` profile in which they are null; application composition rejects that stage. Before
native import, the controller and child automatically attest the exact candidate, harness, profile and target
identity. This technical attestation requires no role approval, reviewer identity or authorization file. The
harness enforces `measurement_safety_floor_bytes = 512 * 1024**2` before every new operation and stops on any
swap increase, OOM/kernel fault, throttling, temperature `>=80 C`, identity/sampler loss or cleanup failure. This
is a laboratory stop condition, not a product admission threshold or PASS claim.

From the complete single-session raw series, derive values deterministically:

```text
speak_drop_bytes = max(pre_speak MemAvailable - minimum MemAvailable through Audio completion)
generate_drop_bytes = max(pre_generate MemAvailable - minimum MemAvailable through primary action completion)
min_mem_available_speak_bytes = ceil_mib(512 MiB + speak_drop_bytes)
min_mem_available_generate_bytes = max(
    min_mem_available_speak_bytes,
    ceil_mib(512 MiB + generate_drop_bytes),
)
```

`ceil_mib` rounds upward to a whole multiple of `1024**2` bytes. Missing lifecycle samples or a stopped/failed
run cannot derive a value. The single Pi product-verification stage (`PV`) reports both deterministic estimates,
their evidence locator and exact digests as outputs; no role signature or manual approval record is an input. It
does not mutate the current profile, create release authority or trigger a second native scenario. Designer may
later adopt the estimates in a release-profile revision. Tester then maps the newly introduced threshold behavior,
Developer implements the profile/config delta, and Verify exercises only the directly affected behavior on the
final same bytes through the normal `Design → Test Spec → Developer → Verify` flow. That later delta is not `PR`
and does not repeat the accepted semantic/human/context corpus by default. Only a subsequently adopted release
profile with positive thresholds is legal for normal product composition. The old `48 MiB owner delta` and
`768 MiB MemAvailable` values are rejected legacy keys.

Decision order:

1. Sampler failure, swap growth, kernel OOM, thermal throttling or an internally inconsistent ownership sample is
   E1 and does not send.
2. `MemAvailable < min_mem_available_speak_bytes`: return `rest + END_SESSION`, mark planned LLM recycle, and
   do not start TTS or generation.
3. `MemAvailable < min_mem_available_generate_bytes`: return application-owned memory notice
   `speak + END_SESSION`, mark planned recycle, and do not generate.
4. Otherwise consume the measurement ticket with `GENERATE`.

The adapter atomically marks `RECYCLE_PENDING` but cannot schedule recovery from Conversation cleanup proof alone.
After the primary action/rest is terminal and matching cleanup proof exists, SM authorizes the planned same-key
recovery inside its private post-close convergence phase. Adapter/composition then uses the existing narrow
`ScheduleRecovery/WaitRecovery` seam; RM owns rebuild, timeout and barrier mechanics. SM does not clear session
tracking, resume wake admission or return to `IDLE` before READY. The next `open_conversation` also awaits the same
ticket defensively. Planned-recovery failure is supervised Level 3, not a retry Fact.

## 6. Canonical product outcome matrix

All application speech below is fixed code-declared Traditional Chinese, excluded from model prompt/history and
never generated by a second inference.

| Source outcome | Conversation mutation | Canonical `LLMResponse` | Class / continuation |
| :--- | :---: | :--- | :--- |
| listen timeout/error/empty | none | `speak {"text":"我沒聽清楚，請再說一次。"} + KEEP_NEXT + ("listen",)` | R1; keep generation |
| input >20 code points or >32 user tokens | none | `speak {"text":"這句有點長，請縮短後再說一次。"} + KEEP_NEXT + ("listen",)` | R1; keep generation |
| context equation fails | none | `speak {"text":"對話內容已滿，請再說一次。"} + REPLACE_NEXT + ("listen",)` | capacity R2; action then replacement |
| memory blocks generation but permits notice | none | `speak {"text":"系統需要整理，請稍後再試。"} + END_SESSION + ()` | capacity end; cleanup then planned recycle |
| memory blocks notice | none | `rest {} + END_SESSION + ()` | capacity end; cleanup then planned recycle |
| model `text!="", end=false` | sent | `speak {"text": text} + KEEP_NEXT + ("listen",)` | normal; keep Conversation |
| model `text!="", end=true` | sent | `speak {"text": text} + END_SESSION + ()` | R3 model-recognized explicit USER end; final speech then rest |
| model `text=="", end=true` | sent | `rest {} + END_SESSION + ()` | R3 model-recognized explicit USER end |
| post-send invalid semantic / clean generation failure with request terminal proof and Engine usable | sent/tainted | `speak {"text":"剛才沒有成功，請再說一次。"} + REPLACE_NEXT + ("listen",)` | R2; cleanup barrier, no replay |
| repeated replaceable failure | as above | same R2 outcome | never auto-escalates to R3/E1 by count |
| explicit button interrupt | any | no normal cognition Fact | R3 interrupt convergence |
| `UNSUPPORTED_INPUT`, profile/ticket mismatch, protocol desync, worker crash, backend unusable or missing request/cleanup proof | unknown/unsafe | no normal `LLMResponse` | E1; ERROR + Level 1/2/3 |

Before publishing any row, Reasoner validates the action payload using the same `ActionPayloadValidator` instance
as State Manager. `speak` being unavailable is E1 for this required voice-only product, not silent downgrade.

## 7. Python component contract

### 7.1 Product types

```python
@dataclass(frozen=True, slots=True)
class SemanticGeneration:
    text: str
    end: bool
    safe_fragments: tuple[str, ...]
    metrics: GenerationMetrics

@dataclass(frozen=True, slots=True)
class GenerationMetrics:
    user_tokens: int
    current_kv_tokens: int
    rendered_incremental_tokens: int
    runtime_prefill_tokens: int
    decode_tokens: int
    conversation_kv_tokens: int
    llm_send_monotonic_ns: int
    first_safe_text_monotonic_ns: int | None
    terminal_monotonic_ns: int

class ReplaceableGenerationFailure(RuntimeError):
    code: Literal["INVALID_SEMANTIC", "GENERATION_REJECTED", "GENERATION_TIMEOUT"]
    request_terminal_proven: Literal[True]
    engine_usable: Literal[True]

@dataclass(frozen=True, slots=True)
class TicketDiscardProof:
    session_id: str
    generation: int
    conversation_revision: int
    ticket: str
    input_sha256: str
    native_render_scrubbed: Literal[True]
    ticket_invalidated: Literal[True]
    private_input_erased: Literal[True]
    conversation_state: Literal["ready"]

class LLMEngineAdapter(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def open_conversation(self, session_id: str, generation: int) -> ConversationReady | ConversationOpenRejected: ...
    async def measure(self, session_id: str, generation: int, text: str) -> AdmissionSnapshot: ...
    async def discard_ticket(self, snapshot: AdmissionSnapshot) -> TicketDiscardProof: ...
    async def generate(self, snapshot: AdmissionSnapshot, text: str) -> SemanticGeneration: ...
    async def close_conversation(self, session_id: str, generation: int, reason: str) -> ConversationCloseProof: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...
```

The real adapter owns one dedicated child/PGID and serializes all operations. Runtime/native objects never enter
Core process memory. Adapter exceptions are typed as clean input/capacity outcome, replaceable post-send outcome,
or unsafe backend/protocol failure; Reasoner must not infer safety from exception text.

### 7.2 Reasoner and lifecycle control

`Reasoner.control` returns a dedicated `ConversationLifecycleControl` facade backed by the same adapter. Resource
Manager late-fills that facade into State Manager after Reasoner READY. Lifecycle and `reason()` share a single
operation lock and generation state, but have separate outer tasks/SM in-flight records.

- `open_conversation` waits for any planned-recovery ticket, then issues one clean OPEN. READY Engine has no
  Conversation and prepared objects may not carry history or be claimed by another session.
- `reason()` verifies the SM-provided generation, projects input, measures, samples memory, and performs at most
  one GENERATE. For measured token-limit R1 it clears normalized text, issues the snapshot-only `discard_ticket`, awaits
  and validates the proof, clears its snapshot, and only then publishes exactly one canonical Fact. Disposal
  failure is E1, never R1.
- `close_conversation` first proves any active request terminal, then closes/destroys Conversation-local history,
  KV and references. Only the typed foundation proof can release the claim.
- `abort/force_abort` obey Ch 2b/6 terminal and descendant-exit rules. Cancel never publishes a normal Fact.

Conversation replacement preserves Product `session_id` and monotonic `turn_id`, increments generation, loses
all Conversation-local history/KV, and never replays the rejected input. Session close deletes all content; no
transcript, prompt or model output is written to disk.

## 8. Private child protocol

[`protocol.md`](../protocol.md) §4 defines `snowboard.llm/3` framing, state machine and exact messages. The product
rules required here are:

- READY verifies immutable install/product profile and reports Engine ready with no Conversation.
- OPEN/CLOSE identify `(session_id, generation)`; at most one Conversation is claimed.
- MEASURE is non-mutating and returns a one-use admission ticket; DISCARD_TICKET invalidates it without changing
  the Conversation; GENERATE is the only mutating inference command.
- `SAFE_TEXT` is nonterminal; `RESULT`, `REQUEST_FAILED`, `CANCELLED`, `OPEN_REJECTED` and `CLOSED` have the
  terminal/proof meanings defined there.
- Invalid framing/identity/order, EOF, duplicate terminal, late output, ticket mismatch or missing cleanup proof
  is E1. Parent obtains process-group termination and waitpid proof before RM rebuild.

## 9. Config, locks and startup

### 9.1 Config surface

`CognitionConfig.llm` retains only deployment paths and operational watchdogs:

```python
@dataclass(frozen=True, slots=True)
class LLMConfig:
    driver: Literal["mock", "litert_lm"] = "mock"
    runtime_python: Path | None = None
    model_path: Path | None = None
    product_profile_path: Path | None = None
    artifact_lock_path: Path | None = None
    profile_id: str | None = None
    child_ready_timeout_seconds: float = 45.0
    generation_timeout_seconds: float = 30.0
    terminal_grace_seconds: float = 2.0
    child_terminate_timeout_seconds: float = 2.0
    child_kill_wait_timeout_seconds: float = 1.0
```

Sampling, prompt, grammar, token/context limits, profile stage, memory thresholds, offline flags and artifact hashes are not YAML
knobs. They live in the canonical product profile/artifact lock and are cross-checked field by field plus digest.
`product_config_path`, `recycle_max_inference_attempts`, `recycle_owner_pss_delta_mib` and
`recycle_min_mem_available_mib` are rejected unknown legacy keys.

Portable/mock config keeps all paths/profile null and must not import LiteRT-LM. Product composition with the real
driver requires four absolute files, exact `profile_id`, `profile_stage="release"`, both positive byte thresholds,
finite positive watchdogs, the narrow schedule/wait recovery callables and target sampler before any side effect.
Only the dedicated measurement script may accept `profile_stage="measurement"`; it cannot be loaded by normal
`AppConfig` composition.

Real `core-m4b-cognition-001` composition additionally requires `perception.read.enabled=false`,
`perception.look.enabled=false`, `action.tool.enabled=false` and the external-message input source disabled.
Button and/or voice-wake may select the architectural `[listen]` first turn. Generic mock/M1/M2 compositions keep
their accepted read/look/tool behavior; these cross-field restrictions apply only when this real product profile
is selected. `UNSUPPORTED_INPUT` remains a defensive E1 if wiring violates the startup gate.

### 9.2 Startup order and readiness

1. Parse strict config and authenticate ABI, model/runtime artifacts, licenses and canonical product profile.
2. Validate profile fields and digests, including release stage, exact prompt counts, grammar, sampling,
   context/output values, memory thresholds, wire version and network-disabled flags.
3. Spawn the dedicated child as a new process group in an offline environment.
4. Child imports runtime, loads Engine, verifies exact tokenizer/prompt counts, and sends READY.
5. Parent verifies every READY field. Mismatch terminates/waitpids the group and fails startup.
6. Reasoner becomes READY with zero Product Sessions and zero Conversations. There is no generation prewarm.

State Manager later opens the first Conversation in WAKE. Existing Display `SCN-STATE` presents `WAKE` as
`準備中`; this is the selected application-owned preparation UX. It is optional/nonblocking display output, adds
no state/Fact/turn/model content, and Conversation readiness remains the only model gate. Active listen/ASR starts
only after readiness.

## 10. Privacy and observability

### 10.1 Forbidden data

Logs, exception strings, evidence and profile dashboards must not contain transcript, prompt bytes, model raw
JSON, semantic text, safe fragments, session IDs, absolute private paths or IPC payload. Allowed identity is
digest/profile/candidate/version; allowed failure detail is stable code, stage, request/generation counters and
boolean proof state.

### 10.2 Separate dashboards

Prompt-composition dashboard records profile ID and the core/personality/combined token counts and hashes once.
Runtime/context rows separately record, per public case and turn:

```text
conversation_generation, turn_index, input_codepoints, user_tokens,
current_kv_tokens, rendered_incremental_tokens, runtime_prefill_tokens,
output_reserve_tokens, projected_total_tokens, admission_result,
decode_tokens, terminal_conversation_kv_tokens
```

Memory rows use one timestamped sample with unique PID accounting:

```text
Core/controller, VAD, ASR, TTS, LLM PSS/RSS/CPU/thread,
combined unique-PID PSS, MemTotal, MemAvailable, system-used, swap,
temperature, throttling, conversation generation and lifecycle point
```

The prior combined peak `2,382.969 MiB` already includes Conversation allocation and is comparison provenance;
the approximately `252.83 MiB` open delta must not be added to it again.

Timing rows use one monotonic clock domain and record:

```text
Conversation ready -> ASR final -> LLM send -> first safe text ->
LLM terminal -> TTS PCM ready -> Audio first write
```

Missing/not-applicable nodes are explicit nulls with a reason. No duration is reconstructed from wall-clock or
different processes without a proven clock mapping. Values are observations for later review, not current PASS
ceilings; Audio first write is not audible onset.

## 11. Verification contract

### 11.1 Portable coverage request

Tester must independently specify at least:

1. exact normalization, codepoint/token boundaries `20/21` and `32/33`, envelope exclusion and no mutation;
2. prompt bytes/counts/hashes, fixed personality, grammar, `text/end` combinations and 30 spoken-character rule;
3. fragmented/coalesced UTF-8/JSON S2 extraction, escapes, prefix proof, invalid/late/duplicate terminal;
4. MEASURE non-mutation, exact equation boundaries, ticket one-use/stale/input-digest/generation checks, plus
   acknowledged token-limit discard, same-revision next MEASURE, repeated rejection and discard failure barriers;
5. fresh listen-only `runtime_prefill <=128` invariant and proof that it is not a multimodal/context ceiling;
6. every row of §6, including application/model speech ownership, final-speak-then-rest and repeated R2;
7. same Conversation across normal turns; context rejection before mutation; close-before-open replacement,
   following successful turn, no replay and Product Session/turn continuity;
8. memory allow/notice/silent decisions with injected new-profile thresholds, sampler failure and planned-recovery
   supervision; assert legacy `8/48/768` keys are rejected;
9. child READY/open/measure/discard/generate/cancel/close/shutdown state machine, proof flags, PGID cleanup and
   next-child success after recovery;
10. logging/privacy redaction and separate prompt/runtime/memory/timing schemas;
11. all affected M1/M2/Foundation/M4A regressions retained with no delete/skip/xfail substitution.

Tests use explicit barriers/events, not wall-clock sleeps. Portable semantic tests use deterministic fakes; they
do not claim real-model quality.

### 11.2 Single Pi product verification (`PV`)

One `PV` stage over one tracked-content digest produces one aggregate disposition, but its seven Test IDs are
independently executable sub-runs rather than one chained scenario. Every Test ID has its own command, fresh setup,
sub-run ID and evidence partition, and repeats automatic attestation of the common content/target/artifact tuple.
No Test ID consumes another Test ID's transcript, model state, resource series, threshold, card or completion flag.
A failed or incomplete Test ID is rerun alone under a new attempt ID; completed siblings remain usable only while
the protected content and common attested tuple are unchanged. Partial attempts are retained as diagnostics but
never merged into the active result. The stage contains these seven explicit test groups:

M4B does not deliver a user-facing one-click product launcher; that belongs to M4C whole-product integration.
Tester specifies one exact executable verification command per Test ID/case. Those commands may share one PV
harness/library, but they are acceptance tooling rather than a parallel product entrypoint or shell-launcher family.
Each command resolves the locked target deployment, performs automatic attestation, creates the fresh
sub-run/evidence partition, executes one bounded case, performs cleanup and reports the evidence locator. It must
not require authorization files or select diagnostic/PM/PR/PH modes. Each `M4B-PI-SEM-001` command opens one
microphone window, completes one answer and exits after cleanup with `NeedsHumanReview`; it never assigns the
semantic verdict.

1. **`M4B-PI-ATT-001` — content, target and artifact identity**
   - Create a new run ID and newly empty private/public evidence roots. Reject any prior PM/PR/PH result, partial
     series, card, frozen profile, threshold, transcript, status or digest as an input to `PV`.
   - Bind the tracked-content digest, harness digest, evidence root and measurement-profile digest before native
     import; require the same tuple in the controller, child and final manifest.
   - Record and verify Raspberry Pi model, OS/kernel, CPU/RAM, target CPython 3.13.5, ABI, SOABI and MULTIARCH.
   - Verify model, runtime closure, wheel/native files, artifact lock, deployment paths and license/notices by exact
     filename, size and digest; reject extra, missing, system-site or alternate-endpoint inputs.
   - Verify profile ID/stage, exact prompt bytes/counts/hashes, grammar, tokenizer, sampling, thread count,
     direct/reserve/context limits, protocol version and offline flags field by field rather than by digest alone.
   - READY must repeat the bound identity, prove `pid == pgid`, zero Conversation and no generation prewarm.
     Any mismatch, dirty/unbound input or fallback is Fail before product behavior is credited.

2. **`M4B-PI-SEM-001` — real-model semantics and human rubric**
   - Use exactly three independent spoken cases, each with a fresh Conversation, case ID and separate evidence:
     `S01-IDENTITY` = `你是誰？`; `S02-ENGLISH` = `想要英文進步應該怎麼做？`;
     `S03-SEVEN-DAYS` = `為什麼一個星期有七天？`.
   - The human checks only the answer for that case: the first identifies the assistant as 雪板; the second gives
     relevant, practical English-learning advice; the third gives a coherent explanation of the seven-day week.
     A failure or recording problem reruns only that case and never the other two.
   - There is no automatic semantic judge, heuristic scorer or model-as-judge. The runner only preserves the
     spoken input, ASR transcript, constrained JSON, answer, run identity and evidence needed for human review;
     the human result is the semantic sub-result.
   - Raw transcript, JSON and answer remain private. Public evidence contains case ID, digests and the recorded
     human result without exposing private content or reviewer-identity approval metadata.

3. **`M4B-PI-CONV-001` — genuine context admission and replacement**
   - Start a fresh, independent Product Session with no input or evidence from the three semantic cases. The script
     submits `請簡短介紹台灣。` through the real Reasoner/worker/model path and requires one structurally successful
     answer; it makes no semantic judgment.
   - The script then sends `請再補充一點。` as clearly labelled new explicit turns through the same real path until
     exact MEASURE rejects the context equation. Preserve revision, generation and token metrics for every turn.
   - Prove rejection occurs before mutation or send, the fixed application notice completes, and matching
     three-part close proof is present before the next OPEN.
   - Preserve the same Product Session, monotonic non-reused turn IDs, one generation increment and zero overlap
     between old and new Conversations. Production must never replay the rejected request automatically.
   - After new-Conversation readiness, the script issues a new explicit input event carrying the rejected test
     text; this is a new stimulus, not production replay. It and one following explicit normal test turn must reach
     successful generation. No answer-semantic judgment or human speech is required. Private evidence proves old
     context absence, while public evidence exposes only counters, digests and booleans.

4. **`M4B-PI-MEM-001` — complete resource series and threshold estimates**
   - This is a fresh, fully automated sub-run with no microphone input, human judgment or evidence from another
     Test ID. It may share sampler code but not state, series or disposition with another test.
   - Use the automatically attested measurement profile with both thresholds null; normal AppConfig composition
     must reject that profile, and no role authorization/signature artifact is accepted.
   - Capture unique-PID ownership plus `MemTotal`, `MemAvailable`, swap, temperature and throttling at Engine-ready,
     Conversation-ready/preparation, before/after every generation, through action/Audio completion, before/after
     replacement and after session close.
   - Before every operation enforce the 512 MiB safety floor and stop on swap growth, OOM/kernel fault, throttling,
     temperature `>= 80 C`, duplicate/missing PID, sampler/identity loss or cleanup failure.
   - Only a complete valid series may produce `speak_drop_bytes`, `generate_drop_bytes`,
     `min_mem_available_speak_bytes` and `min_mem_available_generate_bytes` using the exact §5.3 integer formula.
     Record inputs, results and digests; the estimates do not mutate a profile and do not trigger another run.

5. **`M4B-PI-WAKE-001` — preparation/listen exclusion**
   - This is a fully automated Pi sub-run with no human trigger or judgment. The script drives controlled GPIO/voice
     wake stimuli through the actual production wake/readiness path and correlates Display, microphone, ASR and
     OPEN traces with explicit wake-ack and Conversation-ready barriers; a pure mock-only path cannot Pass.
   - Conversation preparation may overlap only the existing WAKE `準備中` projection. Before both barriers,
     require zero audio-frame pull, active listen/ASR, perception worker and Reasoner admission.
   - Execute four separately rerunnable cases with fresh setup and evidence: `W01-OPEN-FIRST`, `W02-ACK-FIRST`,
     `W03-SLOW-OPEN` and `W04-INTERRUPT-OPEN`. Display remains nonblocking and adds no Fact, state, turn or model
     content. The script assigns Pass/Fail from trace assertions; no button press, wake-word speech or visual
     inspection is required from the USER.

6. **`M4B-PI-TIME-001` — one-clock Audio/LLM timeline**
   - This is a fresh, fully automated sub-run with no human speech, judgment or evidence from another Test ID. A
     fixed audio fixture traverses the actual Audio input, ASR, Reasoner, real model, TTS and Audio output path;
     pure timestamp fakes cannot Pass.
   - For that turn record `Conversation ready → ASR final → LLM send → first safe text → LLM terminal → TTS PCM
     ready → Audio first positive write` in one proven monotonic clock domain.
   - Verify nondecreasing nodes and cross-process clock mapping. Missing or inapplicable nodes must be explicit null
     with a stable reason; no timestamp may be silently omitted.
   - Report observations only. There is no response-time Pass ceiling, and first write is not claimed as audible
     onset.

7. **`M4B-PI-RES-001` — offline, safety, cleanup and privacy**
   - Split into eight independently executable automated cases; each has fresh setup, case ID, evidence partition
     and outcome, and a failure reruns only that case:
     - `R01-OFFLINE`: zero non-loopback network, downloader, telemetry, DNS and fallback attempt from before native
       import through exit.
     - `R02-HEALTH`: zero swap growth, OOM/kernel fault, throttling and temperature-stop violation.
     - `R03-PID`: complete unique-PID ownership with no duplicate, missing owner or owner leak.
     - `R04-NORMAL-CLOSE`: bounded owner/descendant exit after normal Conversation/session close.
     - `R05-RECOVERY`: correct planned-recovery order, bounded old-child exit, matching new READY and a usable
       following child/turn.
     - `R06-FORCED-CLEANUP`: forced PGID cleanup boundedly reaps every descendant.
     - `R07-SHUTDOWN`: final shutdown leaves no owner, child, waiter, task or resource handle.
     - `R08-PRIVACY`: zero private-canary/reversible-encoding hits across logs, public evidence, temporary paths,
       process arguments, environment and persisted files. Raw evidence remains access-controlled and public
       evidence uses opaque locators plus SHA-256 only.

The seven Pi evidence Test IDs remain independently visible at assertion level and share only the top-level `PV`
content/target identity and aggregate disposition; their commands, state and evidence partitions remain separate.
`PM`, `PR` and `PH` are not aliases or sequential M4B gates. The threshold estimates
are evidence outputs rather than release-profile authority; their later adoption follows the focused ordinary
pipeline described in §5.3 without a default replay of the accepted real Audio/model/context/human corpus.
Any required assertion that is Fail, Blocked, missing or Incomplete fails the combined `PV`; test-function counts
or success in another group cannot substitute for the missing per-Test-ID result.

The Developer implementation delta for this merge removes the obsolete three-stage selection surface:

- separate-PM bundle validation/export and any PM-to-PR purpose marker;
- `pm_complete`, `pr_complete` and `ph_complete` result flags or equivalent three-stage completion state;
- separate release-rerun and PH launch/validation paths;
- temporary `run-pi-one-turn.sh`, `run-pi-two-turns.sh` and `run-pi-voice.sh` diagnostic launchers;
- any ability to import an earlier PM/PR/PH profile, threshold, partial series, card, transcript, status or digest
  into the new `PV` entry.

It does not replace the removed temporary launchers with another M4B one-click shell entry. Reusable execution
logic belongs in the shared PV harness invoked by Tester-owned exact per-Test-ID commands; M4C remains the sole
owner of the eventual one-click product startup.

The merge retains and routes shared automatic attestation, measurement, resource sampling, Conversation
replacement, human-rubric, privacy and cleanup mechanisms through one entry. Historical records may remain as
history, but active Pi target/evidence roots must contain none of their outputs when a new `PV` begins.

The old 20-separate-session drift experiment, fake first-turn prewarm and fixed recycle-count test are prohibited.

## 12. Cutover inventory and gate

The cognition/product rewrite owns:

```text
src/sbd/cognition/{llm.py,llm_child_protocol.py,prompt_builder.py,reasoner.py}
src/sbd/cognition/litert_lm/
scripts/m4b_*
requirements/m4b/
tests/test_m4b_*
tests/m4b_*
tests/fakes/m4b_llm_child.py
docs/implement/ch02b_workers.md §3
docs/implement/ch10_config.md §6 and M4B tests
docs/protocol.md §4 and LLM protocol tests
```

Developer replaces these surfaces from this design and the approved test spec; path survival does not imply
legacy behavior reuse. Temporary legacy code/test/design inventory is removed at cutover only after replacement
portable and Pi verification; Git remains the historical reference.

Developer entry is open after focused architecture/review PASS, the resolved ticket-disposal coverage in
`TR_spec_M4B_VII`, the single-PV authority revision and the resolved mapping in `TR_spec_M4B_VIII`. Developer now
implements the shared PV harness, independent commands/case reruns and obsolete-stage cleanup. Real product
verification uses the automatically attested measurement profile and produces threshold estimates as evidence;
it does not require a pre-frozen release profile or accept legacy candidate/POC observations as substitutes.
