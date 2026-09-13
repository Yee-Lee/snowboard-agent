# M4B Replacement Cognition / Product Test Specification

## 1. Authority, scope and disposition

This is the current Tester-owned specification for the clean M4B replacement approved through
[`TR_spec_M4B_VI`](../reviews/history/TR_spec_M4B_VI.md) and amended by the focused
[`TR_spec_M4B_VII`](../reviews/history/TR_spec_M4B_VII.md) ticket-disposal request. It maps the approved behavior in
[`ch_m4b_llm_production`](../implement/ch_m4b_llm_production.md) §§2–11 and
[`snowboard.llm/3`](../protocol.md) §4. It retains the affected Foundation contract in
[`m4b_foundation_revision`](../implement/m4b_foundation_revision.md) §§4–8 and its immutable
99-node regression baseline.

Status: **Specification only — no implementation or acceptance result in this document.**

In scope are the listen-only product profile, prompt and semantic grammar, input/admission and explicit
ticket-disposal policy,
Conversation lifecycle, memory decisions and SM-authorized planned recovery, private child protocol,
privacy/observability, and the later exact-SHA Pi/human evidence procedure.

Out of scope are the retired action envelope, fresh-Conversation-per-turn behavior, fake prewarm,
fixed `8/48/768`, forced 20-session drift, the former 2s/3s response ceiling, M4C streaming speech,
and unrelated Accepted M4A-only acceptance rows. Deterministic fakes prove control semantics only;
they never establish real-model quality, target memory, or target timing.

## 2. Result, matrix and evidence rules

### 2.1 Result vocabulary

- **Pass**: every required assertion and forbidden-call assertion passes, all required evidence is
  present and the automatically attested tracked-content/harness/profile/target/evidence identities agree.
- **Fail**: an assertion fails, a forbidden call/artifact occurs, a baseline node is missing, a test
  is skipped/xfail/xpass, or USER judgment fails a required `M4B-PI-SEM-001` case.
- **Incomplete**: a required measurement, evidence field, identity, raw series, human
  review, or explicit null reason is missing or invalid. Incomplete never converts to Pass.
- **Blocked**: the bound tracked content, target, artifact, credential-free offline setup, or access-controlled
  evidence location is unavailable before execution begins.

Test/function counts are not an acceptance criterion. A table-driven function may cover many rows
only when its result preserves the Test ID, case ID and assertion-level outcome.

`PV` has one final disposition over seven independently executable Pi Test IDs. Every required automated, human
and measurement result must Pass. Any Fail, missing or Incomplete designated result prevents `PV` Pass; a
pre-execution Blocked attempt supplies no `PV` credit. Each Test ID has a fresh setup, unique sub-run ID, private
and public evidence partition and independent outcome. No transcript, state, event, series, card or completion
flag from one Test ID is an input to another. Only the protected tracked-content/harness/profile/target/artifact
tuple and the aggregate `PV` identity are shared.

Every product-executing command is the smallest rerun unit and owns a new sub-run/attempt identity plus empty
private/public partitions. A failed single-command Test ID reruns alone; within `M4B-PI-SEM-001`,
`M4B-PI-WAKE-001` and `M4B-PI-RES-001`, only the failed independently commanded case reruns. Per-Test-ID case
aggregation launches no product behavior. Superseded attempts remain visible but cannot satisfy the designated
result, and the protected tuple remains byte-identical. A stopped, failed, Blocked or Incomplete
`M4B-PI-MEM-001` sub-run publishes no threshold estimate; another Test ID's result neither supplies nor invalidates
an independently complete measurement result.

### 2.2 Execution matrix

| Matrix ID | Layer | Required environment | Timeout policy |
| :--- | :--- | :--- | :--- |
| `PU` | portable unit | Declared Python range `>=3.11,<3.14`; Linux x86_64/aarch64 and macOS arm64; pure Python; no native/model/network | 60 s per Test ID |
| `PI` | portable integration | Same Python/platform range; deterministic adapter/tokenizer/sampler/action fakes | 90 s per Test ID |
| `PS` | portable subprocess | Linux x86_64/aarch64 on Python 3.13; fake child in a real POSIX process group | 120 s per Test ID |
| `PV` | Pi product verification | Raspberry Pi 5 4 GB, Debian 13 aarch64, target CPython 3.13.5; one new aggregate run ID and newly empty private/public roots; automatically attested tracked-content, harness, null-threshold measurement-profile, target and artifact tuple; seven fresh independent sub-runs; USER participation only in the three `M4B-PI-SEM-001` cases | 60 min per Test-ID sub-run; product watchdogs remain 45/30/2/2/1 s; every command has a bounded harness timeout |

`PV` initialization creates the aggregate identity and empty root pair but launches no test. Each Test ID then runs
from its own exact command in §5, may execute in any order, creates a new `sub_run_id` and fresh Product Session
where applicable, and writes only its own private/public partition. Automated Test IDs are #1 and #3–#7;
`M4B-PI-SEM-001` is the only USER-participating Test ID. No Test ID waits for, imports or validates another ID's
evidence. A failed item reruns by itself; unaffected designated results remain valid only while the protected tuple
is unchanged. Finalization reads the seven designated result cards solely to aggregate the one `PV` disposition.

Initialization and every sub-run reject pre-existing output in their target partition and any earlier PM/PR/PH
profile, threshold, partial series, card, transcript, status or digest. No role approval, reviewer identity,
signature or freeze file is an execution input.

USER runtime disposition (2026-09-12): macOS arm64 is diagnostic-only for the current M4B portable
candidate. Formal portable sign-off requires the Linux CPython 3.11/3.12/3.13 matrix; Darwin-only
process-group and CPython 3.11 hardware-diagnostic cancellation failures do not reject the candidate.
Diagnostic exclusions are applied by the execution profile and are not implemented as committed
`skip`/`xfail` controls in protected tests.

Timeouts prevent hangs; they are not response-time PASS ceilings. A timeout is Fail unless the
case explicitly tests a watchdog and observes the required bounded cleanup terminal.

### 2.3 Synchronization and fakes

All async and concurrent cases use named `asyncio.Event`, pipe/queue acknowledgement, child terminal,
task-join, action-complete, close-proof, recovery-ticket and RM-READY barriers. Correctness sleeps,
poll-until-lucky loops and timing-order assumptions are forbidden. Fakes expose call ledgers and fail
if an unexpected model, mutation, speech, recovery, network, file-write or next-request call occurs.

### 2.4 Evidence locator contract

The later runner supplies two existing, access-controlled roots:

- `<public_root>/<candidate_sha>/`: sanitized JUnit, result cards, identity/digest summaries and the
  evidence index.
- `<private_root>/<candidate_sha>/`: raw prompts/answers, process telemetry and memory/timing series;
  never copied into Git or public cards.

Every result record contains `schema_version`, `test_id`, `case_id`, `candidate_sha`, `profile_id`,
`profile_sha256`, matrix/platform/Python identity, start/end monotonic timestamps, `status`, and
`evidence_sha256`. Missing or mismatched identity is Incomplete/Fail. Portable results are located at
`<public_root>/<sha>/portable/<TEST-ID>.{junit.xml,json}`. Pi structural cards are at
`<public_root>/<sha>/cards/<TEST-ID>.json`; human rubrics are at
`<public_root>/<sha>/human/<TEST-ID>.json`; sanitized manifests name private artifacts only by digest
and opaque locator. No card may contain private text, IDs, absolute paths or IPC payloads.

## 3. Portable specification catalog

| Test ID | Exact authority and risk | Layer / matrix | Evidence locator |
| :--- | :--- | :--- | :--- |
| `M4B-NORM-001` | Product §§3.1–3.2, §§5.1–5.2, §6; unsupported or over-limit input mutates Conversation or publishes R1 before ticket disposal | `portable unit`, `portable integration` (`PU,PI`); 60/90 s | `portable/M4B-NORM-001.*` |
| `M4B-PROMPT-001` | Product §§2.1–2.2, §4.1, §9; mutable prompt/profile or permissive grammar changes product identity | `portable unit`, `portable integration` (`PU,PI`); 60/90 s | `portable/M4B-PROMPT-001.*` |
| `M4B-SEM-001` | Product §4.1 and §6; invalid `text/end` or spoken length reaches action | `portable unit` (`PU`); 60 s | `portable/M4B-SEM-001.*` |
| `M4B-S2-001` | Product §4.2; protocol §§4.5, 4.7; unsafe/revised partial text escapes parser | `portable unit`, `portable subprocess` (`PU,PS`); 60/120 s | `portable/M4B-S2-001.*` |
| `M4B-ADM-001` | Product §§5.1–5.2, §7; protocol §§4.3–4.5; MEASURE/disposal mutation, private retention or stale/discarded ticket admits the wrong request | `portable unit`, `portable integration` (`PU,PI`); 60/90 s | `portable/M4B-ADM-001.*` |
| `M4B-PREFILL-001` | Product §5.2; fresh listen-only prefill tier confused with multimodal or 1024 context | `portable integration` (`PI`); 90 s | `portable/M4B-PREFILL-001.*` |
| `M4B-OUTCOME-001` | Product §§5.2, 6 and 7.2; wrong speech owner, disposal ordering, route or fallback changes user-visible behavior | `portable integration` (`PI`); 90 s | `portable/M4B-OUTCOME-001.*` |
| `M4B-CONV-001` | Product §7.2; Foundation §§4–8; history/replacement leaks or session/turn identity resets | `portable integration` (`PI`); 90 s | `portable/M4B-CONV-001.*` |
| `M4B-MEM-001` | Product §5.3, §§9–10; incorrect threshold order/sample policy sends unsafe work | `portable unit`, `portable integration` (`PU,PI`); 60/90 s | `portable/M4B-MEM-001.*` |
| `M4B-REC-001` | Product §5.3; Foundation §7; `AR_impl_M4B_IV`; adapter schedules before SM authorization or recovery failure resumes admission | `portable integration` (`PI`); 90 s | `portable/M4B-REC-001.*` |
| `M4B-WIRE-001` | Product §§5.1, 8–9; protocol §§4.3–4.7; desync/disposal/proof failure leaks child or permits illegal state | `portable subprocess` (`PS`); 120 s | `portable/M4B-WIRE-001.*` |
| `M4B-PRIV-001` | Product §§5.1, 10; protocol §§4.1, 4.3–4.4; rejected private input survives disposal or escapes observability boundaries | `portable unit`, `portable integration` (`PU,PI`); 60/90 s | `portable/M4B-PRIV-001.*` |
| `M4B-REG-001` | Product §11.1(11); Foundation `FND-REG-001`; tests are deleted/weakened or unrelated M4A acceptance is substituted | `portable integration` (`PI`); 180 s suite cap | `portable/M4B-REG-001.*` |

## 4. Portable cases and acceptance criteria

### M4B-NORM-001 — Listen projection, normalization and input limits

Fixture: a ledger-backed Conversation fake starts at revision `r`, plus exact deterministic tokenizer
counts. `MEASURED`, `DISCARDING`, `TICKET_DISCARDED`, `GENERATE`, state mutation, R1 publication and
model-content capture each have separate barriers.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `N01` | One matching `listen/ok`; compatibility characters, mixed Unicode whitespace and edge whitespace | NFKC first, maximal whitespace run becomes one U+0020, edges removed; model content is exactly normalized text; envelope/private IDs never serialized |
| `N02` | TAB/LF/CR whitespace | Accepted then collapsed; counted spaces remain code points |
| `N03` | NUL, surrogate, and each non-whitespace `Cc` class representative | E1 before MEASURE; revision/call ledgers unchanged; no application retry Fact |
| `N04` | Non-`str` text | E1 before normalization/tokenization; zero model calls |
| `N05` | Empty or all-whitespace `ok`; `timeout`; `error` carrying hostile `text/extra` | Exact no-input R1 response; timeout/error payload ignored and absent from logs; no MEASURE/GENERATE/mutation |
| `N06` | Normalized 20 then 21 code points, including spaces and non-BMP symbol | 20 proceeds to token admission; 21 returns exact input-limit R1; no truncation/partial send; Python code-point count used |
| `N07` | Codepoint-valid fake tokenizer results 32 then 33 direct-user tokens | 32 may proceed; 33 enters `MEASURED → DISCARDING`, clears normalized-text local, obtains an exact all-true `TICKET_DISCARDED`, clears snapshot, and only then publishes exact input-limit R1; same session/generation/revision/history/KV; zero GENERATE/native send/semantic mutation |
| `N08` | zero/multiple items; `read/look`; pending external input; wrong session/turn; unknown status; listen/speak capability false | Every row is `UNSUPPORTED_INPUT` E1; no model, mutation or normal `LLMResponse` |

### M4B-PROMPT-001 — Frozen profile, prompt bytes and grammar identity

Fixture: canonical byte constants, a tokenizer double that records exact bytes, strict profile/lock
loader, and READY verifier. Startup side effects are latched behind an authentication barrier.

The exact expected byte composition is the UTF-8 encoding of these two strings with no separator,
BOM or trailing newline:

```text
你是「雪板」繁體中文語音助理，只能聽與說，不能看或使用工具。只輸出含 text、end 的 JSON。一般回答的 text 不超過30字且 end=false；明確要求結束時 end=true。語氣：
溫暖自然，稍帶幽默。
```

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `P01` | Load canonical core, personality and concatenation | Exact UTF-8 bytes, no BOM/newline; SHA-256 equals `8caba35159407882407c1ac1be22c66791ac66236e323bc1b63fa072c1340eec`, `57191898561df177e820a10eed88ad9d47649ba9e5e19c059b554acedda777e5`, `872ae6b6418761b271cd6762c08eeaabe1f20d3a1c4aa72602a09eab1f1eb643`; selected tokenizer counts exactly `57/9/66` |
| `P02` | Insert/remove/change one byte, BOM/newline, personality suffix or YAML override | Fail before child spawn/native import; no fallback/default or user suffix |
| `P03` | Authenticate full product profile and READY | Exact profile/candidate/pairing/runtime/model/ABI, `temperature=0.0`, `top_p=1.0`, threads 4, reserve 128, context 1024, wire 3 and offline flags match field-by-field; SHA-256 of the canonical grammar artifact bytes equals both profile and READY `grammar_sha256`; matching overall digest alone is insufficient |
| `P04` | Extra/missing/alternate profile, endpoint, artifact, system-site dependency or prewarm option | Startup failure with zero child/model/network side effect; POC provenance digest cannot stand in for product identity |
| `P05` | Grammar corpus of canonical objects and one-field mutations | Only ordered, compact `{"text":"<string>","end":<bool>}` accepted; unknown/duplicate/missing/reordered key, external whitespace, wrong type, trailing byte, invalid UTF-8/escape rejected |
| `P06` | Real profile with read, look, tool or external-message input enabled; then generic mock profile with its accepted capabilities | Every real mismatch fails before factory side effects; generic mock behavior remains accepted and is not narrowed |
| `P07` | Real composition missing schedule/wait/sampler seam, or mock composition receiving one; equivalent YAML keys | Real requires all three narrow injected interfaces; mock requires all three null; YAML cannot obtain them |
| `P08` | Four deployment paths missing/non-absolute/non-file, wrong profile ID, or any nonfinite/nonpositive watchdog | Strict failure before workdir/native/child/sampler/RM side effect; exact valid fields proceed |

### M4B-SEM-001 — Terminal semantic validation

Fixture: decoded-object validator and shared `ActionPayloadValidator`; no real model.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `S01` | all four `text` empty/non-empty × `end` false/true combinations | Non-empty/false, non-empty/true and empty/true accepted; empty/false rejected; no fabricated text |
| `S02` | JSON escapes for quote, slash, backslash, BMP/non-BMP Unicode and split surrogate escape pair | Decode exactly once, normalize once, preserve action punctuation; malformed/lone escape rejected |
| `S03` | output containing NUL, surrogate or disallowed control after decoding | Invalid semantic; never reaches action/speech |
| `S04` | 30 then 31 countable characters with whitespace/punctuation interspersed | 30 accepted, 31 rejected, no truncation; letters/numbers/symbols/emoji count, whitespace and Unicode category `P*` do not |
| `S05` | `「你好嗎？」` and `嗨🙂！` | `spoken_length` is exactly 3 and 2 respectively |
| `S06` | Valid semantic payload then deliberate action-schema mismatch | Same validator instance used by Reasoner and SM; mismatch is E1 before publication |

### M4B-S2-001 — Incremental UTF-8/JSON extraction

Fixture: byte-chunk matrix feeds the real incremental parser. A fragment barrier captures every
`SAFE_TEXT`; Speak/TTS ledgers remain armed to detect forbidden dispatch.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `X01` | Every byte boundary of a valid multi-byte UTF-8 JSON object, then fully coalesced input | Same terminal object and ordered non-empty fragments for every partition; partial UTF-8 never emitted |
| `X02` | Split before/inside escape sequences and escaped Unicode | JSON syntax/escape bytes withheld; emitted text is decoded semantic content only |
| `X03` | Parser emits multiple fragments | Sequence begins 0 without gaps/duplicates; concatenation is exact prefix of normalized terminal text; fragments never revised |
| `X04` | Prefix mismatch, fragment after terminal, duplicate/late terminal, invalid terminal or trailing bytes | Protocol/semantic E1; generation/TTS path cancelled; no successful RESULT/Facts |
| `X05` | Valid fragments in M4B full-response mode | First-safe time recorded, but zero Speak/TTS dispatch until validated terminal result; M4C streaming behavior not claimed |
| `X06` | Parser delays fragments at punctuation/24-codepoint boundary or emits none before terminal | Both are legal when terminal/prefix proof succeeds; no fixed fragment count or latency assertion is introduced |

### M4B-ADM-001 — Non-mutating admission, ticket binding and explicit disposal

Fixture: child Conversation exposes generation/revision/history/KV/token-count/native-scratch/output-allocation
snapshots, live-object probes and a renderer/native-send call ledger. Parent Reasoner exposes normalized-text,
snapshot, Fact-publication and outbound-frame barriers. `MEASURED`, `DISCARDING`, scrub return,
`TICKET_DISCARDED`, R1 publication, CLOSE and GENERATE are released independently.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `A01` | MEASURE on clean Conversation with unique private canary | Same tokenizer/renderer as generation; exact non-negative fields returned; generation/revision/history/KV/output allocation/native-send unchanged; before MEASURED, Python request/tokenizer temporaries are gone and ticket ledger retains only opaque ticket, identities, input digest, revision and integer counts; native `last_rendered_message` is the sole permitted child-side private-text retention |
| `A02` | Equation totals 896+128=1024 then 897+128=1025, including alternate splits of current/incremental | Inclusive 1024 passes token equation; 1025 returns context R2 before mutation/send; reserve/context fixed 128/1024 |
| `A03` | Negative, boolean, float, overflow/impossible or internally inconsistent metric | Protocol E1 before inference; no coercion |
| `A04` | matching latest ticket and identical text/digest/revision/generation | GENERATE consumes ticket once before native send; successful RESULT increments revision exactly once |
| `A05` | missing, reused, explicitly discarded, stale-revision, wrong-generation, wrong-session, wrong-input-digest or text-mismatch ticket used for GENERATE | E1, zero additional native send and zero mutation; discarded ticket remains permanently invalid even after a later successful MEASURE |
| `A06` | CLOSE from MEASURED with one outstanding ticket | CLOSE destroys ticket and native scratch with Conversation cleanup, returns only the existing all-three true close proof, and later ticket use is rejected; no separate TICKET_DISCARDED is fabricated |
| `A07` | Codepoint-valid 33-token MEASURE, then exact DISCARD_TICKET | Reasoner releases normalized-text local before constructing the snapshot-only frame; request exact-matches new request ID plus session/generation/revision/ticket/input digest; state is `MEASURED → DISCARDING`; renderer is invoked exactly once with `__M4B_TICKET_SCRUB__`; native scratch becomes the fixed scrub rendering; token count, generation, revision, semantic history and KV are byte/value unchanged; zero runtime clear API, GENERATE or native send |
| `A08` | Exact TICKET_DISCARDED after scrub barrier | Terminal repeats exact request/session/generation/revision/ticket/digest, has `native_render_scrubbed=true`, `ticket_invalidated=true`, `private_input_erased=true`, `conversation_state="ready"`; ticket metadata is cleared, no live child/native object retains rejected text, Reasoner releases snapshot, state becomes CONVERSATION_READY, then and only then R1 publishes |
| `A09` | After A08, new short input on same Conversation | New MEASURE and normal GENERATE succeed with unchanged starting generation/revision/history/KV from before rejection; old ticket is still rejected |
| `A10` | Three 33-token rejection/disposal cycles followed by a short input | Every cycle has a distinct exact ticket/discard request and acknowledged cleanup before its R1; same Conversation/revision throughout rejects; final short turn generates normally; no count-based replacement/escalation |
| `A11` | Scrub renderer raises, returns invalid rendering, changes token count or leaves canary reference | E1, no TICKET_DISCARDED/R1/GENERATE/native send; bounded PGID destruction proof required |
| `A12` | Independently mismatch request/session/generation/revision/ticket/digest; stale/duplicate discard; independently false/missing each of the three proofs; extra/malformed/wrong terminal; timeout or EOF, including lost ACK after actual invalidation | Every row is E1, never R1; no terminal substitution or retry; actual child invalidation without an exact observed ACK is insufficient; bounded PGID cleanup and waitpid proof before further admission |
| `A13` | Compare public SM state, Event/Fact unions and `LLMResponse` schema before/after disposal support | Disposal remains private adapter/protocol control; no public state, Event, Fact or `LLMResponse` field/variant is added or emitted |

### M4B-PREFILL-001 — Fresh listen-only prefill tier

Fixture: a newly OPENED generation at revision zero, one normalized listen within both direct limits,
and measured rows at 128 and 129 runtime-prefill tokens.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `F01` | fresh row with `runtime_prefill_tokens=128` and otherwise valid equation | Profile tier passes and admission continues to memory decision |
| `F02` | identical row with `runtime_prefill_tokens=129` | Product-profile E1, not input/context R1/R2; no GENERATE |
| `F03` | second normal turn or non-listen/additional future projector | Fresh listen tier is not applied as a general ceiling; unsupported M4B projector still fails under `N08` |
| `F04` | valid 128 prefill but total equation >1024; valid total but direct tokens 33 | Independent context/input rule still fails; 128 never grants multimodal input or replaces 1024/32 limits |

### M4B-OUTCOME-001 — Canonical policy matrix

Fixture: parameterized Reasoner with mutation ledger, sampler, semantic result/failure and capability
fakes; SM/action completion barriers assert phase order. Every row validates the exact four-field
`LLMResponse` and exact Traditional Chinese application text from product §6.

| Case family | Stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `O01` | timeout/error/empty, codepoint-limit, then measured token-limit rows | exact application-owned `我沒聽清楚，請再說一次。` or `這句有點長，請縮短後再說一次。` respectively, with `speak + KEEP_NEXT + ("listen",)`; codepoint rejection performs no MEASURE, while token rejection publishes only after exact TICKET_DISCARDED; generation/revision/history/KV unchanged and zero model mutation |
| `O02` | context equation failure | exact `對話內容已滿，請再說一次。` + `REPLACE_NEXT`; zero rejected-input send/replay |
| `O03` | memory blocks generation but permits notice | exact `系統需要整理，請稍後再試。` + `END_SESSION`; zero model generation; final primary speech then exactly one rest |
| `O04` | memory blocks notice | `rest {}` + `END_SESSION`; zero TTS and generation; exactly one rest |
| `O05` | model non-empty/false | model text owns speech payload; `KEEP_NEXT`; no application paraphrase or second inference |
| `O06` | model non-empty/true | model text spoken, then exactly one rest and `END_SESSION`; primary/rest records never overlap |
| `O07` | model empty/true | direct single rest + `END_SESSION`; no fabricated speech |
| `O08` | each allowed REQUEST_FAILED code with terminal proof and usable Engine | exact `剛才沒有成功，請再說一次。` + `REPLACE_NEXT`; tainted generation closed; no replay |
| `O09` | two and three consecutive proven replaceable failures | identical R2 each time; no count escalation to R3/E1 |
| `O10` | button interrupt | no normal cognition Fact; R3 convergence |
| `O11` | unsupported input, mismatch/desync/crash/unusable backend/missing proof/unavailable Speak | no normal response or silent downgrade; E1 and Level 1/2/3 path |
| `O12` | token-limit discard held at scrub/terminal barrier, then failed or released | While held, zero R1 Fact/action; failure takes E1 with no normal Fact; only exact acknowledged disposal releases one canonical input-limit R1 |

### M4B-CONV-001 — Conversation continuity and replacement

Fixture: one Product Session with a fake Conversation holding visible turn markers. Barriers are
`action_done`, `request_joined`, `close_proven`, `open_ready` and `next_perception_allowed`.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `C01` | two successful normal turns | same child, Conversation object, generation and increasing revision; second fake response proves first-turn context was present |
| `C02` | context reject before native send | old revision/history unchanged; action completes before close; rejected input absent from old/new Conversation |
| `C03` | successful replacement | exact order block admission → request terminal/join → close all-three proof → generation+1 → clean open → READY → next perception; never two claims |
| `C04` | first repeated request after replacement, then following turn | user repeats explicitly; request succeeds on new generation; subsequent normal turn also succeeds; system never auto-replays |
| `C05` | replacement across action error/success | preselected normalized/default perceptions preserved; same Product `session_id`; monotonic `turn_id` never resets/reuses; no buffer flush/discard |
| `C06` | stale session/generation/correlation/task completion | dropped with sanitized diagnostic; active generation/session unchanged |

### M4B-MEM-001 — Memory decision and release-profile policy

Fixture: injected release profile thresholds `0 < S <= G`, unique-PID sampler snapshots and independent
model/TTS/recovery ledgers. Values are synthetic and cannot claim Pi memory acceptance.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `M01` | For `S<G`, MemAvailable `G`, `G-1`, `S`, `S-1`; then a valid `S==G` profile | `G` and above GENERATE; `[S,G)` exact notice/end; below `S` silent rest/end; equal thresholds are accepted and have no notice band; comparisons are strict `<`; exactly one healthy unique-PID sample is taken immediately before permitted GENERATE |
| `M02` | sampler exception/identity loss, duplicate PID, inconsistent totals, swap growth, OOM, throttling or invalid temperature sample | E1, no send/TTS/recovery scheduling |
| `M03` | measurement profile through normal AppConfig; release null/nonpositive/reversed thresholds | fail before composition side effects; only dedicated measurement loader accepts null thresholds |
| `M04` | YAML/source attempts to set threshold/sampling/prompt/grammar/context/offline values | unknown/rejected; canonical profile remains unchanged |
| `M05` | legacy `product_config_path`, recycle keys or literal fixed 8/48/768 policy | strict rejection before spawn; no compatibility alias |

### M4B-REC-001 — Planned-recovery authorization and supervision

Fixture: real SM convergence logic with fake Adapter and RM seams. The fake records
`mark_pending`, primary/rest terminal, close proof, SM authorization, schedule, wait and READY. Each
step is held by an explicit barrier.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `R01` | memory capacity result | Adapter atomically marks one `RECYCLE_PENDING`; zero `ScheduleRecovery` calls at mark time |
| `R02` | matching close/cleanup proof arrives while primary action or rest is held | cleanup proof alone schedules zero recovery |
| `R03` | release primary/rest terminal after full proof | SM authorizes exactly one same-key recovery in private post-close phase; Adapter/composition invokes seam only after authorization |
| `R04` | hold recovery wait before RM READY | session tracking retained, wake admission blocked, state not IDLE, new/open requests and ticket waiters do not proceed |
| `R05` | RM returns matching READY | barrier releases once; session clears/resumes wake/IDLE only afterward; defensively waiting next open can now succeed |
| `R06` | RM timeout, exception, wrong key/identity or unusable replacement | Level 3; no next request, no stranded ticket waiter, no false READY/normal Fact |
| `R07` | duplicate close/notice/authorization | one recovery maximum; stale duplicate rejected without state change |

### M4B-WIRE-001 — `snowboard.llm/3` state, proof and process cleanup

Fixture: actual fake child subprocess with PID=PGID, controllable descendants and bytewise framing.
Parent/child request and process-exit barriers replace sleeps.

| Case family | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `W01` | exact READY then each missing/extra/mismatched field | exact READY enters ENGINE_READY with no Conversation; any mismatch terminates/kills and waitpids whole PGID; no fallback |
| `W02` | OPEN/OPENED and OPEN_REJECTED proof matrix | identity/revision/state exact; clean rejection requires cleanup+usable; false proof is E1 |
| `W03` | MEASURE/MEASURED and GENERATE/SAFE_TEXT/RESULT | legal `CONVERSATION_READY → MEASURING → MEASURED → GENERATING → CONVERSATION_READY` transitions, request/session/generation/revision/ticket/metrics exact; RESULT only after native join/prefix proof |
| `W04` | each allowed REQUEST_FAILED code and every false/unknown variant | only true terminal proof + usable Engine enters TAINTED/R2; otherwise E1/cleanup |
| `W05` | CANCEL once during OPEN/MEASURE/GENERATE/CLOSE, with deferred and proof matrices | exact allowed operation/state mapping excludes DISCARD_TICKET; second/mismatched cancel rejected; cancelled CLOSE incomplete proof escalates; no fabricated terminal or normal cognition Fact |
| `W06` | CLOSE each legal reason and proof combination, including from MEASURED | only all-three true returns ENGINE_READY/none; MEASURED close destroys outstanding ticket/native scratch with Conversation cleanup and later use fails; no TICKET_DISCARDED is fabricated; invalid reason/proof is E1 |
| `W07` | SHUTDOWN from ENGINE_READY versus active Conversation/request | READY-only ACK, child zero exit and waitpid; active shutdown rejected except after Level 2 destruction |
| `W08` | wrong order, BUSY/reentry, malformed/overlong framing, invalid JSON/UTF-8, EOF, duplicate/late/output-after-terminal | deterministic protocol §4.7 E1, admission blocked, sanitized diagnostic, bounded PGID cleanup |
| `W09` | child ignores TERM and owns nested descendant; then RM recovery | TERM→KILL bounded waits prove owner and descendants gone; successful fully attested new child handles OPEN/MEASURE/GENERATE/CLOSE |
| `W10` | Exact DISCARD_TICKET/TICKET_DISCARDED exchange after MEASURED | Exact request/session/generation/revision/ticket/digest and all three true proofs; `MEASURED → DISCARDING → CONVERSATION_READY`; fixed scrub renderer called once, token count unchanged, ticket cleared/permanently invalid, no GENERATE/native send/runtime clear |
| `W11` | Each discard request identity mismatch; stale/duplicate; scrub/render/count failure; false/missing proof; malformed/wrong terminal; timeout/EOF | E1 from MEASURED or DISCARDING, never R1; no success terminal accepted; parent terminates/kills and waitpids PGID before admission/recovery |
| `W12` | CANCEL or OPEN/MEASURE/DISCARD/GENERATE/CLOSE/SHUTDOWN during DISCARDING; racing interrupt | DISCARDING accepts no command or CANCEL; reentry is E1. Interrupt waits for exact disposal terminal and then converges, or timeout/EOF takes the same bounded E1 PGID-cleanup boundary; no normal R1 races ahead |

### M4B-PRIV-001 — Redaction and independent dashboards

Fixture: canary transcript/prompt/raw JSON/semantic/fragment/session/path/IPC values injected through
success and every error path; live-object probes cover parent locals, child Python temporaries, ticket
ledger and native render scratch; log/evidence/workdir scanner runs after disposal and cleanup barriers.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `V01` | success, validation error, child stderr, exception and cleanup | no canary/private value or reversible encoding in logs, exceptions, public cards or dashboards; only allowed digest/profile/candidate/version/code/counters/proofs |
| `V02` | prompt composition evidence | once-per-profile row contains only profile ID, exact three counts/hashes; not copied into per-turn prefill |
| `V03` | runtime/context evidence | exact §10.2 fields, projected total consistent, no prompt or semantic text |
| `V04` | memory evidence | unique-PID owner/system fields and lifecycle point complete; open delta not added again to combined peak |
| `V05` | timing with missing/not-applicable first-safe/TTS/audio node | one monotonic domain; explicit null plus stable reason; no wall-clock reconstruction, PASS ceiling or audible-onset claim |
| `V06` | post-close filesystem/process scan | no transcript, prompt, output, IPC payload, temp workdir or orphaned private content remains |
| `V07` | 33-token canary through MEASURED and acknowledged disposal | Before MEASURED, child request/tokenizer temporaries are absent and only native scratch may retain canary; before DISCARD_TICKET, Reasoner normalized-text local is absent and frame contains snapshot fields only; before R1, snapshot/ticket binding are gone, native scratch contains only fixed scrub rendering and no live parent/child/native object retains canary |
| `V08` | Inspect ticket ledger and scrub call | Ledger never retains raw input, rendered content or private IDs beyond protocol-required opaque identity/digest fields; scrub input is exactly public `__M4B_TICKET_SCRUB__`, called once, not logged as private evidence and never sent to model |
| `V09` | Every disposal failure/timeout/EOF followed by bounded destruction | No R1/public success artifact, rejected canary or stale ticket survives in live objects, sanitized evidence, replacement child or post-cleanup filesystem; forensic zeroization of freed allocator capacity is explicitly not claimed |

### M4B-REG-001 — Retained coverage and anti-weakening

The immutable Foundation baseline is exactly
[`baselines/m4b_foundation_node_ids.txt`](baselines/m4b_foundation_node_ids.txt), currently 99 sorted
node IDs. Candidate verification uses the following fail-closed comparison, with commands executed
from the clean candidate checkout:

```bash
regression_files=(
  tests/milestones/test_m1_foundation.py
  tests/milestones/test_m2_mock_pipeline.py
  tests/test_events.py
  tests/test_state_manager.py
  tests/test_m2_sm_flows.py
  tests/test_m2_flows.py
  tests/test_m2_wrk_003.py
)
PYTHONPATH=src pytest -o addopts='' --collect-only -q "${regression_files[@]}" \
  > /tmp/m4b_foundation_post_collection.txt
awk '/::/' /tmp/m4b_foundation_post_collection.txt | LC_ALL=C sort -u \
  > /tmp/m4b_foundation_post_nodes.txt
comm -23 docs/test_spec/baselines/m4b_foundation_node_ids.txt \
  /tmp/m4b_foundation_post_nodes.txt > /tmp/m4b_foundation_missing_nodes.txt
test "$(wc -l < docs/test_spec/baselines/m4b_foundation_node_ids.txt)" -eq 99
test ! -s /tmp/m4b_foundation_missing_nodes.txt
```

Acceptance records `baseline_count=99`, `retained_count=99`, `missing_count=0`, plus SHA-256 of all
three lists. Any command error, duplicate baseline line, unsorted input or missing node is Fail.

Additional cases:

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `G01` | AST scan of all `src/**/*.py` and `tests/**/*.py`, plus pytest collection metadata | Foundation four-field constructor guard remains; no direct/aliased skip, xfail, `pytest.skip/xfail`, false constant assertion, deselection or marker omission affecting the 99 nodes or new M4B IDs |
| `G02` | run 99-node regression with strict markers and JUnit | failures=0, errors=0, skipped=0; no xfail/xpass; every baseline node appears once |
| `G03` | run complete `test_spec_M4B_foundation` focused implementation | all Foundation Test IDs Pass; replacement tests do not substitute for them |
| `G04` | dependency/diff inventory for candidate | all existing M1/M2/Foundation and shared config/SM/RM tests that import a changed symbol execute; report exact collected node list and zero skip |
| `G05` | M4A affected-boundary selection | run only existing portable nodes whose production dependency is changed or shared by M4B composition, unique-PID resource sampling, offline environment, privacy scan, process-group cleanup, TTS final-speech completion or Audio+LLM timeline; publish selector rationale and node list; do not rerun Pi M4A-only quality/latency acceptance |
| `G06` | compare candidate test inventory to pre-development exact SHA | deleted/renamed/weakened affected node or removed assertion is Fail unless an upstream approved authority explicitly replaces it; new nodes allowed |

## 5. Pi structural and human evidence plan

These Test IDs are defined now and remain Pending until the automatically bound tracked content, authenticated
target, implemented harness and Tester execution gate exist. Portable fake results cannot satisfy them. Initialize
one aggregate `PV` identity without launching a test:

```text
python3.13 scripts/run-m4b-pv.py init --pv-run-id <NEW_PV_RUN_ID> --public-root <NEW_EMPTY_PUBLIC_ROOT> --private-root <NEW_EMPTY_PRIVATE_ROOT> --binding-manifest <BINDING_JSON>
```

`init` fails unless both roots are newly empty and the binding manifest automatically attests the tracked content,
harness, measurement profile, target and artifacts. The seven Test IDs then run independently in any order. Each
exact command below requires a new sub-run ID, fresh setup and new empty per-ID partitions. Angle-bracket values are
execution inputs, not optional flags. No wrapper or retired launcher may replace these commands.

| Test ID | Authority and risk | Layer / timeout | Evidence locator |
| :--- | :--- | :--- | :--- |
| `M4B-PI-ATT-001` | Product §§2, 8–9, 11.2; stale input or wrong content/artifact/runtime/profile/target/root/fallback | automated `PV` sub-run; 60 min | `<public_root>/<pv_run_id>/M4B-PI-ATT-001/<sub_run_id>/` |
| `M4B-PI-SEM-001` | Product §§2.2, 4, 6, 11.2; real answer meaning is unacceptable to USER | three USER-participating fresh-Conversation cases; 60 min Test-ID cap | `<public_root>/<pv_run_id>/M4B-PI-SEM-001/<sub_run_id>/` |
| `M4B-PI-CONV-001` | Product §§5–7, 11.2; automated context/replacement/identity behavior diverges | automated `PV` sub-run; 60 min | `<public_root>/<pv_run_id>/M4B-PI-CONV-001/<sub_run_id>/` |
| `M4B-PI-MEM-001` | Product §5.3, §§10–11; independent series is incomplete/unsafe or estimate is unauditable | automated `PV` sub-run; 60 min | `<public_root>/<pv_run_id>/M4B-PI-MEM-001/<sub_run_id>/` |
| `M4B-PI-WAKE-001` | Product §9.2, §11.2; scripted preparation overlaps active ASR/listen | automated `PV` sub-run; 60 min | `<public_root>/<pv_run_id>/M4B-PI-WAKE-001/<sub_run_id>/` |
| `M4B-PI-TIME-001` | Product §10.2, §11.2; fresh fixed-audio timeline has mixed clocks or omitted nulls | automated `PV` sub-run; 60 min | `<public_root>/<pv_run_id>/M4B-PI-TIME-001/<sub_run_id>/` |
| `M4B-PI-RES-001` | Product §§5.3, 7–11; independent network/resource/cleanup/privacy case fails | automated `PV` sub-run; 60 min | `<public_root>/<pv_run_id>/M4B-PI-RES-001/<sub_run_id>/` |

Every command starts its own Engine/child and Product Session where applicable and tears them down before emitting
its result. It reads only the protected binding manifest and its own case fixtures. Controller, child, result card
and private manifest repeat the aggregate `pv_run_id`, unique `sub_run_id`, exact protected tuple and own partition
identity. No Test ID consumes another ID's transcript, turn, state, event, resource series, card or completion flag.
Bounded named barriers replace correctness sleeps and poll-until-lucky loops.

### 5.1 Run bootstrap and automatic attestation — M4B-PI-ATT-001

Exact command:

```text
python3.13 scripts/run-m4b-pv.py run --test-id M4B-PI-ATT-001 --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> --public-partition <NEW_EMPTY_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
```

| Case | Stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `A01-NEW-ROOTS` | Start the ATT command against its new partitions and aggregate initialization record | aggregate roots were empty at initialization; ATT partitions are empty before this sub-run writes; earlier result, partial series, card, profile, threshold, transcript, status or digest is neither selected nor referenced |
| `A02-BOUND-TUPLE` | Attest before native import, then compare this sub-run's controller, child READY, result card and manifest | one tracked-content, harness, measurement-profile, target, artifact and partition tuple agrees field-for-field and by digest; untracked, dirty-but-unbound or otherwise unaccounted input is Fail |
| `A03 target-runtime` | Inspect the authenticated target and target-owned interpreter | Raspberry Pi model, Debian/OS/kernel, CPU/RAM, CPython `3.13.5`, ABI, SOABI and MULTIARCH exactly match; identity loss or mismatch is Fail |
| `A04 artifacts` | Inventory model, runtime closure, wheel/native/artifact lock, deployment files and notices | exact filenames, sizes and digests agree; deployment paths and licenses/notices are present; missing, extra, system-site, alternate-endpoint or fallback input is Fail |
| `A05 profile-ready` | Compare the profile field-by-field and receive READY | profile ID and `profile_stage="measurement"`; both thresholds null; 57/9/66 prompt counts and three prompt hashes; exact prompt, grammar, tokenizer, sampling 0/1, threads 4, direct/reserve/context 32/128/1024, protocol 3 and offline fields agree; READY repeats the tuple with `pid == pgid`, no Conversation and no prewarm |
| `A06 obsolete-stage-negative` | Scan tracked content and exercise runner/schema negative inputs for the removed selection surface | no separate-PM bundle validator/export, `pm_complete`/`pr_complete`/`ph_complete` or equivalent flags, PM-to-PR purpose marker, release-rerun path, PH launch/validation path or temporary `run-pi-one-turn.sh`, `run-pi-two-turns.sh`, `run-pi-voice.sh` launcher can select, seed or validate `PV`; retained attestation/sampling/replacement/privacy/human/cleanup mechanisms remain reachable only through the canonical entry |

Run this independent sub-run with syscall/network-attempt capture from before native import through its child exit.
ATT records only its own bound identity, preflight facts and assertion results. Public cards contain identities,
digests and counts only; raw paths and environment data remain private. No ATT output gates another Test ID.

### 5.2 Three independent USER semantic cases — M4B-PI-SEM-001

Create one `M4B-PI-SEM-001` sub-run ID, then execute exactly these three case commands. Each command starts a
fresh Engine/child and fresh Conversation in new empty case-attempt partitions, records one real
listen→Reasoner→action answer and closes before the next case:

```text
python3.13 scripts/run-m4b-pv.py run-semantic-case --test-id M4B-PI-SEM-001 --case-id S01-IDENTITY --utterance '你是誰？' --pv-run-id <PV_RUN_ID> --sub-run-id <SEM_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup --fresh-conversation
python3.13 scripts/run-m4b-pv.py run-semantic-case --test-id M4B-PI-SEM-001 --case-id S02-ENGLISH --utterance '想要英文進步應該怎麼做？' --pv-run-id <PV_RUN_ID> --sub-run-id <SEM_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup --fresh-conversation
python3.13 scripts/run-m4b-pv.py run-semantic-case --test-id M4B-PI-SEM-001 --case-id S03-SEVEN-DAYS --utterance '為什麼一個星期有七天？' --pv-run-id <PV_RUN_ID> --sub-run-id <SEM_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup --fresh-conversation
```

Only these three cases require USER speech and judgment. Store the audio, transcript, constrained JSON and answer
privately. Public evidence contains the case ID, attempt ID, capture digests and USER `Pass`/`Fail` verdict only.
Answer meaning is human-only: no structural status, automatic semantic assertion, keyword/personality heuristic,
rubric dimension automation or model-as-judge may accept or reject the answer. Automation may verify only that the
bound recording and evidence write completed. Recording failure or USER Fail reruns only that case, explicitly and
with a new case-attempt ID; it never reuses its failed Conversation and never causes another Test ID to run.

### 5.3 Genuine multi-turn and replacement — M4B-PI-CONV-001

Exact fully automated command:

```text
python3.13 scripts/run-m4b-pv.py run --test-id M4B-PI-CONV-001 --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> --public-partition <NEW_EMPTY_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
```

This command creates its own Product Session and uses no semantic-case state, evidence, USER speech or human
judgment.

| Case | Stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `C01-FIRST` | Script submits `請簡短介紹台灣。` | one structurally successful real-model generation completes; record revision, generation, turn and token metrics; do not score answer meaning |
| `C02-FILL-nnnn` | Script submits labelled `請再補充一點。` turns with monotonically increasing four-digit labels | each admitted turn is structurally successful without semantic scoring; preserve every revision/generation/token metric until exact MEASURE rejects one labelled request |
| `C03-REJECT` | Observe the first exact context-equation rejection | rejection occurs before mutation/send; the complete fixed application context notice is the only primary response; the rejected label and text are recorded; no automatic replay occurs |
| `C04-REPLACE` | Complete the notice and replace the Conversation | action completes before matching three-part close proof; no OPEN precedes proof; Product Session and monotonic non-reused turn IDs persist; generations never overlap and increment exactly once |
| `C05-RESUBMIT` | Script explicitly resubmits the exact rejected labelled `請再補充一點。` text after new READY | request succeeds structurally on the clean generation; private evidence proves old-context absence; no semantic scoring |
| `C06-FOLLOWING` | Script submits `請簡短說明台灣的地理位置。` | one following normal turn succeeds structurally in the replacement Conversation; no USER input or judgment |

### 5.4 Complete measurement series and estimates — M4B-PI-MEM-001

Exact fully automated command:

```text
python3.13 scripts/run-m4b-pv.py run --test-id M4B-PI-MEM-001 --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> --public-partition <NEW_EMPTY_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
```

This sub-run creates its own Engine, Product Session, Conversation, sampler and raw series. Its scripted lifecycle
uses `請簡短介紹台灣。`, labelled `請再補充一點。` turns through exact context rejection and replacement, the
explicit rejected-text resubmission, one structurally successful following turn and final close. It neither reads
`M4B-PI-CONV-001` evidence nor waits for a semantic/human result.

| Case | Stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `M01-PROFILE` | Load the automatically attested profile through this harness and separately attempt normal AppConfig composition | profile identity agrees, `profile_stage="measurement"` and both thresholds are null; normal AppConfig rejects it; no role authorization, reviewer identity, signature, approval or freeze artifact is accepted |
| `M02-LIFECYCLE` | Execute the complete independent scripted lifecycle above | Engine, Conversation, every generation/action/Audio boundary, replacement, following turn and final close all complete under this sub-run ID; no other Test ID's event or status is referenced |
| `M03-SERIES` | Sample every lifecycle boundary | complete unique-PID, `MemTotal`, `MemAvailable`, swap, temperature and throttling values exist at Engine-ready, Conversation-ready/preparation, before/after every generation, through every action/Audio completion, before/after replacement and after session close; duplicate/missing PID or sampler/identity loss is Fail |
| `M04-STOPS` | Evaluate the safety predicate before every new operation | enforce the 512 MiB floor and stop on swap growth, OOM/kernel fault, throttling, temperature `>=80 C`, sampler/identity loss or cleanup failure; no operation begins after a stop condition |
| `M05-ESTIMATES` | Recompute from this sub-run's unchanged integer series | only a complete valid MEM sub-run derives both drops and estimates; a stopped, failed, Blocked or Incomplete attempt emits explicit nulls with a stable reason; record exact inputs, outputs and digests without mutating a profile or launching another run |

For `M05-ESTIMATES`, recompute exactly:

```text
speak_drop_bytes = max(pre_speak MemAvailable - minimum through Audio completion)
generate_drop_bytes = max(pre_generate MemAvailable - minimum through primary action completion)
min_speak = ceil_mib(512 MiB + speak_drop_bytes)
min_generate = max(min_speak, ceil_mib(512 MiB + generate_drop_bytes))
```

`ceil_mib(x) = ((x + 1024**2 - 1) // 1024**2) * 1024**2`. Preserve the complete raw private series and
sanitized inputs, results and digests. The pair is `PV` evidence output only; it creates no release-profile
authority and exercises no threshold decision rows in this run.

### 5.5 WAKE preparation exclusion — M4B-PI-WAKE-001

Execute the four cases separately. Each command owns a new case sub-run ID, attempt ID and empty evidence
partitions:

```text
python3.13 scripts/run-m4b-pv.py run-wake-case --test-id M4B-PI-WAKE-001 --case-id W01-OPEN-FIRST --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup --production-wake-path
python3.13 scripts/run-m4b-pv.py run-wake-case --test-id M4B-PI-WAKE-001 --case-id W02-ACK-FIRST --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup --production-wake-path
python3.13 scripts/run-m4b-pv.py run-wake-case --test-id M4B-PI-WAKE-001 --case-id W03-SLOW-OPEN --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup --production-wake-path
python3.13 scripts/run-m4b-pv.py run-wake-case --test-id M4B-PI-WAKE-001 --case-id W04-INTERRUPT-OPEN --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup --production-wake-path
```

The commands drive the actual production GPIO/voice wake ingress and production Display, microphone, ASR, OPEN
and Conversation-readiness path. The harness may control ordering at the real ingress/barriers, but direct state
mutation, bypassed production wiring or a pure mock-only path is Fail and cannot produce a designated case card.
USER speech, button action and judgment are forbidden inputs.

| Case | Wake/order stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `W01-OPEN-FIRST` | Scripted GPIO wake; OPEN becomes ready before wake acknowledgement | both barriers correlate to the same wake; no active listen path begins until both complete |
| `W02-ACK-FIRST` | Scripted voice wake; acknowledgement arrives before OPEN | both barriers correlate to the same wake; no active listen path begins until both complete |
| `W03-SLOW-OPEN` | Scripted GPIO wake with bounded delayed OPEN | preparation may overlap only WAKE `準備中`; no premature active listen path occurs |
| `W04-INTERRUPT-OPEN` | Scripted voice wake interrupted while OPEN is pending | pending preparation closes without audio pull, active listen/ASR, perception worker or Reasoner admission |

For every row, before both wake acknowledgement and matching Conversation-ready/join barriers require zero
audio-frame pull, active listen/ASR, perception worker or Reasoner admission. Display is nonblocking and adds no
product Fact, state, turn or model content. Each case emits its own outcome and can be rerun alone with new case
identities and partitions. Combine designated case cards without product execution:

```text
python3.13 scripts/run-m4b-pv.py aggregate-cases --test-id M4B-PI-WAKE-001 --pv-run-id <PV_RUN_ID> --public-partition <WAKE_AGGREGATE_PUBLIC_PARTITION> --private-partition <WAKE_AGGREGATE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON>
```

### 5.6 One-clock timeline — M4B-PI-TIME-001

Exact fully automated command:

```text
python3.13 scripts/run-m4b-pv.py run --test-id M4B-PI-TIME-001 --audio-fixture tests/fixtures/m4b/pv/short-taiwan.wav --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> --public-partition <NEW_EMPTY_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
```

`T01-FIXED-AUDIO` uses only the bound fixed-audio fixture containing `請簡短介紹台灣。` and runs a fresh real
Audio→ASR→model→TTS→Audio path. Record the fixture filename, size and digest, require one structurally successful
turn without semantic scoring, and accept no USER speech or evidence from another Test ID. `T02-CLOCK-MAP` proves
controller/child monotonic mapping with bounded capture and no wall-clock substitution. `T03-NODE-ORDER` records:

```text
Conversation ready -> ASR final -> LLM send -> first safe text ->
LLM terminal -> TTS PCM ready -> Audio first positive write
```

Validate nondecreasing applicable nodes and cross-process clock mapping. Every missing/not-applicable
node is explicit null with a stable reason under `T04-NULL-REASON`. Report raw observations only: no latency
threshold, no PASS based on duration and no claim that Audio first positive write is audible onset. This Test ID
uses only its own fresh fixed-audio events and terminates its own child after capture.

### 5.7 Resource, cleanup and privacy — M4B-PI-RES-001

Execute the eight cases separately. Each command owns a new case sub-run ID, attempt ID, sampler/canaries where
applicable and empty evidence partitions:

```text
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R01-OFFLINE --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R02-HEALTH --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R03-PID --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R04-NORMAL-CLOSE --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R05-RECOVERY --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R06-FORCED-CLEANUP --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R07-SHUTDOWN --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
python3.13 scripts/run-m4b-pv.py run-resource-case --test-id M4B-PI-RES-001 --case-id R08-PRIVACY --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_CASE_SUB_RUN_ID> --case-attempt-id <NEW_CASE_ATTEMPT_ID> --public-partition <NEW_EMPTY_CASE_PUBLIC_PARTITION> --private-partition <NEW_EMPTY_CASE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON> --fresh-setup
```

Every command creates and tears down a fresh Engine/child/Product Session as applicable and uses no event, series,
card or completion flag from another RES case or Test ID.

| Case | Fresh scripted scope | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `R01-OFFLINE` | Capture attempts before native import through one structural turn and exit | zero non-loopback network, downloader, telemetry, DNS, alternate-endpoint or fallback attempt |
| `R02-HEALTH` | Run one complete generation/action/Audio/close lifecycle with resource sampling | zero swap growth, OOM/kernel fault, throttle or temperature-stop violation; operation stops at `>=80 C` or the 512 MiB laboratory floor |
| `R03-PID` | Sample all controller/ASR/TTS/LLM owners through one lifecycle | every live owner appears exactly once by unique PID; duplicate/missing PID, identity loss, owner leak or sampler loss is Fail |
| `R04-NORMAL-CLOSE` | Complete one normal Conversation and Product Session close | matching three-part proof precedes bounded owner/descendant cleanup; zero orphan remains |
| `R05-RECOVERY` | Script one planned-recovery authorization and rebuild | primary action/rest and matching close proof precede SM authorization; recovery order is correct; new READY and one following structural turn succeed |
| `R06-FORCED-CLEANUP` | Force the bound child PGID into its cleanup path | bounded forced-PGID owner/descendant exit and owner convergence occur; no rebuild or following-turn assertion belongs to this case |
| `R07-SHUTDOWN` | Invoke final product shutdown with live sampler and child | bounded owner/descendant and sampler exit; no owner leak or process retains the case partitions |
| `R08-PRIVACY` | Inject private canaries, complete a structural turn/close/shutdown, then scan | logs, public evidence, temporary paths, argv/environment and persisted files contain zero raw canary or reversible-encoding hit; raw evidence remains access-controlled and public locators are opaque and digested |

Each case emits its own outcome and public/private card pair. Failure reruns only that case with new case identities
and empty partitions; all other designated RES case cards remain unaffected while protected bytes are unchanged.
Public evidence contains only that case's assertion outcomes, counts, digests and opaque locators. Combine the
eight designated case cards without product execution:

```text
python3.13 scripts/run-m4b-pv.py aggregate-cases --test-id M4B-PI-RES-001 --pv-run-id <PV_RUN_ID> --public-partition <RES_AGGREGATE_PUBLIC_PARTITION> --private-partition <RES_AGGREGATE_PRIVATE_PARTITION> --binding-manifest <BINDING_JSON>
```

### 5.8 One disposition and later threshold adoption

After seven designated results exist, aggregate without launching product behavior:

```text
python3.13 scripts/run-m4b-pv.py finalize --pv-run-id <PV_RUN_ID> --public-root <PUBLIC_ROOT> --private-root <PRIVATE_ROOT> --binding-manifest <BINDING_JSON>
```

The final manifest exposes each Test ID, case and assertion independently, plus `automated_status` for #1/#3–#7,
`human_status` for #2 and `measurement_status` for #4. It reports `pv_status=Pass` only when all seven designated
Test-ID results Pass against the identical protected tuple. Aggregate counts, another Test ID or a superseded
attempt cannot fill a missing result. Failure leaves unrelated designated evidence intact; only the failed
single-command Test ID or failed SEM/WAKE/RES case reruns, with a fresh setup/attempt identity and no
protected-byte change. A valid MEM result
retains its independently derived estimates even while another Test ID awaits correction; an invalid MEM attempt
has null estimates and cannot be designated.

Successful estimates remain evidence outputs. Later adoption is a new focused
`Design → Test Spec → Developer → Verify` delta, is not named `PR`, does not treat this `PV` as release-profile
authority and does not repeat the accepted semantic/human/context corpus by default. Its coverage is limited to
behavior directly affected by the adopted threshold values, followed by same-bytes Pi verification.

## 6. Requirement traceability

| Product §11.1 group | Portable Test IDs |
| :--- | :--- |
| 1. normalization/envelope/boundaries/no mutation | `M4B-NORM-001` |
| 2. prompt/grammar/text-end/spoken length | `M4B-PROMPT-001`, `M4B-SEM-001` |
| 3. UTF-8/JSON S2 extraction | `M4B-S2-001`, `M4B-WIRE-001` |
| 4. MEASURE/equation/ticket/disposal | `M4B-NORM-001`, `M4B-ADM-001`, `M4B-OUTCOME-001` |
| 5. fresh prefill tier | `M4B-PREFILL-001` |
| 6. canonical outcome rows | `M4B-OUTCOME-001` |
| 7. Conversation continuity/replacement | `M4B-CONV-001` |
| 8. memory and planned recovery | `M4B-MEM-001`, `M4B-REC-001` |
| 9. complete child protocol including DISCARDING and next child | `M4B-WIRE-001` |
| 10. redaction, disposal lifetime and separate schemas | `M4B-PRIV-001` |
| 11. retained M1/M2/Foundation/M4A regression | `M4B-REG-001` |

| Product §11.2 evidence requirement | Pi/human Test IDs |
| :--- | :--- |
| artifact/runtime/ABI/profile/prompt/grammar, offline/no fallback | `M4B-PI-ATT-001`, `M4B-PI-RES-001` |
| three independent fresh-Conversation USER cases with human-only semantic verdicts | `M4B-PI-SEM-001` |
| fresh fully automated multi-turn context rejection, replacement, resubmission and following success | `M4B-PI-CONV-001` |
| automatic attestation, independent complete measurement series and deterministic estimate evidence; no release rerun | `M4B-PI-ATT-001`, `M4B-PI-MEM-001` |
| four fresh scripted WAKE orderings with no USER trigger and no active ASR/listen overlap | `M4B-PI-WAKE-001` |
| fresh fixed-audio real Audio/ASR/model/TTS/Audio timeline, null reasons and no ceiling | `M4B-PI-TIME-001` |
| eight fresh automated offline/health/PID/cleanup/recovery/shutdown/privacy cases | `M4B-PI-RES-001` |

## 7. Blocking findings

`TR_spec_M4B_VIII` remains Revised pending Designer confirmation. This correction retains accepted B2/B3/B5 and
addresses the remaining B1/B4 mapping: WAKE W01–W04 and RES R01–R08 now have independent product-executing
commands, fresh setup, sub-run/attempt identity, empty evidence partitions, individual outcomes and single-case
reruns; WAKE requires the real production wake/readiness path, and R06 ends at forced-PGID descendant cleanup.
This is a Test Spec revision only. All cases and evidence remain Pending until Developer entry, an implemented
harness, bound tracked content and the applicable Tester execution gate exist; no product test ran and no `PV`
PASS is claimed.
