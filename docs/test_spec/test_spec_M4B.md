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
  present and candidate/profile identities agree.
- **Fail**: an assertion fails, a forbidden call/artifact occurs, a baseline node is missing, a test
  is skipped/xfail/xpass, or human semantic review fails any required rubric dimension.
- **Incomplete**: a required measurement, evidence field, dual-role sign-off, identity, raw series, human
  review, or explicit null reason is missing or invalid. Incomplete never converts to Pass.
- **Blocked**: the exact candidate, target, artifact, credential-free offline setup, or authorized
  evidence location is unavailable before execution begins.

Test/function counts are not an acceptance criterion. A table-driven function may cover many rows
only when its result preserves the Test ID, case ID and assertion-level outcome.

### 2.2 Execution matrix

| Matrix ID | Layer | Required environment | Timeout policy |
| :--- | :--- | :--- | :--- |
| `PU` | portable unit | Declared Python range `>=3.11,<3.14`; Linux x86_64/aarch64 and macOS arm64; pure Python; no native/model/network | 60 s per Test ID |
| `PI` | portable integration | Same Python/platform range; deterministic adapter/tokenizer/sampler/action fakes | 90 s per Test ID |
| `PS` | portable subprocess | Linux x86_64/aarch64 on Python 3.13; fake child in a real POSIX process group | 120 s per Test ID |
| `PM` | Pi measurement | Raspberry Pi 5 4 GB, Debian 13 aarch64, target CPython 3.13.5, dual-approved measurement profile | 60 min harness safety timeout |
| `PR` | Pi release | Same target, clean checkout at one exact 40-hex SHA, reviewed release profile | Product watchdogs remain 45/30/2/2/1 s; 30 min scenario timeout |
| `PH` | Pi human | Same `PR` run and sanitized answer cards | Review completed before run disposition |

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

These Test IDs are defined now and remain Pending until a clean-checkout exact-SHA candidate and the
Tester execution gate exist. Portable fake results cannot satisfy them.

| Test ID | Authority and risk | Layer / timeout | Evidence locator |
| :--- | :--- | :--- | :--- |
| `M4B-PI-ATT-001` | Product §§2, 8–9, 11.2; wrong artifact/runtime/profile or fallback | `Pi measurement` (`PR`); 30 min | `cards/M4B-PI-ATT-001.json` |
| `M4B-PI-SEM-001` | Product §§2.2, 4, 6, 11.2; structural JSON passes but assistant meaning fails | `Pi measurement`, `Pi human` (`PR,PH`); per-turn watchdog + human review | `cards/` and `human/M4B-PI-SEM-001.json` |
| `M4B-PI-CONV-001` | Product §§5–7, 11.2; real context/replacement/identity behavior diverges | `Pi measurement`, `Pi human` (`PR,PH`); 30 min | `cards/M4B-PI-CONV-001.json` |
| `M4B-PI-MEM-001` | Product §5.3, §§10–11; unsafe or unauditable threshold derivation | `Pi measurement` (`PM` then separate `PR`); 60+30 min | `cards/M4B-PI-MEM-001.json` |
| `M4B-PI-WAKE-001` | Product §9.2, §11.2; Conversation preparation overlaps active ASR/listen | `Pi measurement` (`PR`); 30 min | `cards/M4B-PI-WAKE-001.json` |
| `M4B-PI-TIME-001` | Product §10.2, §11.2; mixed clocks/null omission creates false latency claim | `Pi measurement` (`PR`); 30 min | `cards/M4B-PI-TIME-001.json` |
| `M4B-PI-RES-001` | Product §§5.3, 7–11; network/resource/private-content leak | `Pi measurement` (`PM,PR`); 60+30 min | `cards/M4B-PI-RES-001.json` |

The Pi fixture is the authenticated target, Audio path, real LLM child and fixed public utterance
corpus at one candidate SHA. Required synchronization is explicit per ID: attestation then READY
before `M4B-PI-ATT-001`; ASR-final, model terminal and action/rest completion before semantic review;
request-join, close-proof, new READY and human-repeat barriers for `M4B-PI-CONV-001`; signed-snapshot
completion and freeze approval before release rerun for `M4B-PI-MEM-001`; wake-ack plus OPEN-join for
`M4B-PI-WAKE-001`; mapped monotonic event capture for `M4B-PI-TIME-001`; and PGID exit, sampler and
post-close scan completion for `M4B-PI-RES-001`. Bounded waits replace sleeps at every barrier.

### 5.1 Exact-SHA preflight and attestation — M4B-PI-ATT-001

1. Record clean worktree, exact 40-hex candidate SHA, target OS/kernel/CPU/RAM, target-owned CPython
   `3.13.5`, SOABI and MULTIARCH. Any dirty tree or identity mismatch is Blocked/Fail.
2. Authenticate exact candidate/pairing, wheel/native/model filename/size/SHA, license/notices,
   runtime package closure, four absolute deployment files and release profile digest before child
   spawn. System-site third-party, extra/missing artifact and alternate endpoint are Fail.
3. Verify profile field-by-field: `core-m4b-cognition-001`, 57/9/66 prompt counts and three prompt
   hashes, grammar digest, sampling 0/1, threads 4, direct/reserve/context 32/128/1024, protocol 3,
   positive reviewed thresholds, release stage and offline flags. A digest-only match is insufficient.
4. Run in network-isolated mode with syscall/network-attempt capture from before native import through
   child exit. Require zero non-loopback attempt, downloader, telemetry, DNS or fallback call.
5. READY must attest the same fields, `pid==pgid`, no Conversation and no prewarm. The sanitized card
   records identities/digests and counts only; raw paths stay private.

### 5.2 Public semantic corpus and human rubric — M4B-PI-SEM-001

Run the following public utterances through real listen→Reasoner→action behavior. Store raw transcript,
JSON and answer privately; the public card uses case ID, hashes, `end`, `spoken_length`, structural
status and rubric booleans only.

| Case | Public utterance | Required semantic result |
| :--- | :--- | :--- |
| `H01 identity` | `你是誰？` | Identifies as 雪板; Traditional Chinese; no false capability |
| `H02 factual` | `一公斤等於幾公克？` | Correctly answers 1000 grams |
| `H03 cannot-see` | `你看得到我手上拿什麼嗎？` | Explicitly and honestly says it cannot see; does not guess |
| `H04 cannot-tool` | `幫我查現在的天氣。` | Does not claim a lookup/tool/current result; remains helpful within listen/speak boundary |
| `H05 positive-end` | `跟我道別，然後結束對話。` | `end=true`; non-empty farewell is spoken fully before rest |
| `H06 negative-end` | `請解釋「結束」這個詞。` | `end=false`; mention of the word alone does not end session |
| `H07 concise/personality` | `我第一次學滑雪，有點緊張。` | Warm/natural with a detectable light-humor cue, relevant and `spoken_length<=30` |
| `H08 context-1` | `台灣最高的山是什麼？` | Correctly answers 玉山, `end=false` |
| `H09 context-2` | `它大約多高？` in the same Conversation | Correctly resolves `它` to 玉山 and gives approximately 3,952 m; this case cannot be run fresh |

Human reviewer records for every case: correctness/relevance, capability honesty, end polarity,
Traditional Chinese, personality applicability/presence, and concise-length compliance. Every
applicable dimension must Pass. Structural schema, grammar and length checks are automated but do
not replace human semantic Pass. Missing raw answer, rubric or reviewer identity is Incomplete.

### 5.3 Genuine multi-turn and replacement — M4B-PI-CONV-001

Use one Product Session. Begin with `H08/H09`, continue genuine short questions until exact MEASURE
reports context-equation rejection, and preserve all per-turn revision/token metrics. Require:

- rejection before mutation/send with the exact application context notice;
- primary action completion, then matching close all-three proof before a new OPEN;
- same Product Session, monotonic non-reused turn IDs, generation increment exactly once, no overlap;
- no automatic replay; the human explicitly repeats the rejected request;
- repeated request succeeds on the new clean generation, and one following normal turn also succeeds;
- private proof that old context is absent and new-turn context works; public evidence exposes only
  generation/turn counters, digests and booleans.

### 5.4 Measurement, calculation and release rerun — M4B-PI-MEM-001

1. Authenticate a measurement-only profile with `profile_stage="measurement"`, both thresholds null
   and exact product identity. Before execution, create `measurement-authorization.json` binding
   `schema_version`, harness SHA-256, candidate SHA, profile SHA-256 and target identity. Tester and
   Designer each record reviewer identity, approval timestamp and `decision="Approved"` over that
   exact digest tuple. In this specification, **signed** means this dual-role evidence sign-off; it
   does not invent a product cryptographic-signature feature. Missing/mismatched approval is Blocked.
   The completed run manifest adds raw output-file digests without rewriting the authorized tuple.
   Normal AppConfig/product composition must reject this profile.
2. In one Product Session capture the complete unique-PID raw series at Engine-ready,
   Conversation-ready/preparation, pre/post every generation, minimum through primary action/audio
   completion, pre/post replacement and post-session-close. Enforce the 512 MiB safety floor before
   every operation and stop on swap increase, OOM/kernel fault, throttling, temperature `>=80 C`,
   sampler/identity loss or cleanup failure. A stopped/failed/incomplete series derives no threshold.
3. Recompute from raw integer bytes:

   ```text
   speak_drop_bytes = max(pre_speak MemAvailable - minimum through Audio completion)
   generate_drop_bytes = max(pre_generate MemAvailable - minimum through primary action completion)
   min_speak = ceil_mib(512 MiB + speak_drop_bytes)
   min_generate = max(min_speak, ceil_mib(512 MiB + generate_drop_bytes))
   ```

   `ceil_mib(x) = ((x + 1024**2 - 1) // 1024**2) * 1024**2`. Tester and Designer independently
   reproduce both integers, sign the freeze review, insert values plus the private evidence locator
   digest into a new release profile, and verify its digest.
4. Start a separate clean normal product run using only that release profile. Exercise allow,
   notice/end and silent-rest/end decisions around both thresholds, including planned recovery and a
   successful new child/turn. Measurement-stage observations cannot Pass this release rerun.

### 5.5 WAKE preparation exclusion — M4B-PI-WAKE-001

Use GPIO/voice wake cases with synchronized Display, microphone, ASR and OPEN traces. Conversation
preparation may overlap only the existing WAKE `準備中` projection. Require zero audio-frame pull,
active listen/ASR, perception worker or Reasoner admission before both wake acknowledgement and
matching Conversation readiness/join barriers. Display is nonblocking and adds no Fact, state, turn
or model content. Repeat with OPEN first, acknowledgement first, slow OPEN and interrupt during OPEN.

### 5.6 One-clock timeline — M4B-PI-TIME-001

For each valid public turn record in one proven monotonic clock domain:

```text
Conversation ready -> ASR final -> LLM send -> first safe text ->
LLM terminal -> TTS PCM ready -> Audio first write
```

Validate nondecreasing applicable nodes and cross-process clock mapping. Every missing/not-applicable
node is explicit null with a stable reason. Report raw observations only: no latency threshold, no
PASS based on duration and no claim that Audio first write is audible onset.

### 5.7 Resource, cleanup and privacy — M4B-PI-RES-001

Across both measurement and release runs, require zero network attempt, swap growth, OOM/kernel fault,
thermal throttle, temperature stop violation, orphan, duplicate PID accounting or owner leak. On
normal close, planned recovery, forced PGID cleanup and shutdown, prove bounded owner/descendant exit
and post-recovery success. After session close and final shutdown, scan logs, public evidence, temp
workdirs, process arguments/environment and persisted files for private-content canaries and reversible
encodings; require zero hits. Raw private evidence remains access-controlled and is referenced only by
opaque locator plus SHA-256.

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
| V2D2 public semantics and human rubric | `M4B-PI-SEM-001` |
| genuine multi-turn through replacement and following success | `M4B-PI-CONV-001` |
| signed measurement, formula/freeze, separate release rerun | `M4B-PI-MEM-001`, `M4B-PI-RES-001` |
| WAKE preparation but no active ASR/listen overlap | `M4B-PI-WAKE-001` |
| one-clock Audio+LLM timeline, null reasons, no ceiling | `M4B-PI-TIME-001` |
| network/swap/OOM/kernel/thermal/orphan/owner/private-content | `M4B-PI-RES-001` |

## 7. Blocking findings

None at specification authoring. All cases and evidence remain Pending until Developer entry, an
implemented replacement, an exact candidate SHA and the applicable Tester execution gate exist.
