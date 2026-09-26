# M4C — Complete Offline Voice-Device Integration Test Specification

## 1. Authority, scope and disposition

**Design authority**: [`docs/milestones/M4C.md`](../milestones/M4C.md)

**Upstream accepted inputs**:
- M4A Audio: Accepted at commit `6c3ba95455dc5c2a152aa230b8ae5915887fe6a9`.
- M4B LLM/Reasoner: Accepted at commit `f87cfa50b9c9415430973076a59c6b1961228090`.
- M4-ERR: Accepted at commit `f572915d0b0d5c52067e9100c5b022e57aefe506`.
- M4C-SS: Closed／Adopted `B2-ONE-LOOKAHEAD-COALESCE`; POC delivery binding commit
  `a492a1416721c73c989dd46067b3e9dd1c24508d`.

**Status**: Current — Tester-owned streamlined executable authority for M4C Developer and Verify.

**In scope**: `VolumeControlledAudioOutput` decorator and config; `StreamingSpeakControl`
(`B2-ONE-LOOKAHEAD-COALESCE`) portable controller coverage; session no-input streak and
product classification; whole-product scenario composition (`M4C-S01`–`M4C-S05`); focused
streaming-fault and Display-degradation integration; directly affected regression continuity.

**Out of scope**: barge-in; runtime volume adjustment; Display animation/graphics (留 M7);
camera/look (留 M6); tool/MQTT (留 M5); repeated-session soak; formal latency/memory/thermal
ceilings (留 ALPHA); re-running M4-ERR cause-code matrix in integration; POC pass credit for
any M4C Test ID.

---

## 2. Result vocabulary and execution matrix

### 2.1 Result vocabulary

- **Pass**: every required product-risk assertion passes.
- **Fail**: an assertion fails, a forbidden product effect occurs, or execution does not reach the
  required terminal state.
- **Incomplete**: execution ends without enough direct observation to decide a required assertion.
  Incomplete never converts to Pass.
- **Blocked**: the bound tracked content, target, artifact, or required hardware is unavailable
  before execution begins.

All current Test IDs are decided by automatic assertions. The completed S02 product run already
contains the single necessary audible-product observation; no standalone S09 human result or
second quality playback is required.

### 2.2 Execution matrix

| Matrix ID | Layer | Required environment | Timeout |
| :--- | :--- | :--- | :--- |
| `PU` | Portable unit | Project workstation environment and target Pi CPython 3.13; no hardware or network required | 60 s per Test ID |
| `PI` | Portable integration | Project workstation environment and target Pi CPython 3.13; real product logic with deterministic adapter/fake seams | 90 s per Test ID |
| `PS` | Portable subprocess | Linux x86_64/aarch64, CPython 3.13 only; fake child in real POSIX process group | 120 s per Test ID |
| `PV` | Pi product verification | Raspberry Pi 5 4 GB, Debian 13 aarch64, CPython 3.13; real LiteRT-LM, Matcha TTS and ALSA I2S speaker; `volume_percent=25`; network disabled; same pending bytes as the commit candidate | 60 min per Test-ID sub-run |

Portable runs need only pytest outcome and failure output. Pi scenario results retain the stable
counts, booleans and state codes required by their oracle. Source/config/model/artifact/evidence
digests are not startup behavior, Test ID assertions or per-run work. If content identity must be
checked at transfer or candidate preparation, the operator performs one independent diagnostic.

All async and concurrent cases use named `asyncio.Event`, pipe/queue acknowledgement, task-join,
operation-complete, and resource-release barriers. Correctness sleeps, poll-until-lucky loops and
timing-order assumptions are forbidden. Fakes expose call ledgers and fail if an unexpected
model, speech, file-write or network call occurs.

Timeouts prevent hangs; they are not response-time PASS ceilings. A timeout is Fail unless the
case explicitly tests a watchdog and observes required bounded cleanup.

### 2.3 Evidence and privacy rules

Public evidence contains only the stable counts, booleans, timing labels and codes needed by a Pi
oracle. It must not contain transcript, prompt, raw model output, PCM, fragment or terminal text,
session ID, credential, or complete private path.

---

## 3. Portable specification catalog

| Test ID | Authority and primary risk | Layer / timeout | Evidence locator |
| :--- | :--- | :--- | :--- |
| `M4C-VOL-001` | M4C §Static output volume boundary; scaling mutates iterator or gain applied multiple times | `PU, PI`; 60/90 s | `portable/M4C-VOL-001.*` |
| `M4C-SS-CTRL-001` | M4C-SS §Adopted streaming-speak contract clauses 1–9; B2 controller admits wrong fragment, allows unbounded queue, or leaks owner | `PU, PI, PS`; 60/90/120 s | `portable/M4C-SS-CTRL-001.*` |
| `M4C-SS-EXTRACT-001` | M4C-SS clause 2; punctuation-or-12 boundary, Unicode stability, terminal flush, exact concatenation | `PU`; 60 s | `portable/M4C-SS-EXTRACT-001.*` |
| `M4C-SS-OUTCOME-001` | M4C-SS clauses 5–8; zero-fragment R2, partial-fragment STREAMING_TERMINAL_FAILED, cleanup-unproven, protocol-failed outcomes | `PI`; 90 s | `portable/M4C-SS-OUTCOME-001.*` |
| `M4C-NOINPUT-001` | M4C §Session no-input completion; streak counter, product speech, cross-session isolation, request-code classification | `PU, PI`; 60/90 s | `portable/M4C-NOINPUT-001.*` |
| `M4C-DISPLAY-001` | Display failure during a real voice-control vertical must not enter ERROR or interrupt LLM→TTS→Audio | `PI`; 90 s | `tests/test_m4c_s07_tryrun.py` |
| `M4C-REG-001` | Directly affected Accepted M4A/M4B/M4-ERR behavior regresses under the M4C delta | `PI`; 180 s suite cap | pytest result |

PU/PI run once on the project workstation and once on the same pending bytes on target Pi. PS runs
on Linux/CPython 3.13. M4C does not create an operating-system/Python cross-product gate.

---

## 4. Portable cases and acceptance criteria

### M4C-VOL-001 — `VolumeControlledAudioOutput` scaling and composition

Fixture: a byte-exact S16_LE sample bank; `MockAudioOutput` call ledger; injected
`AudioOutputConfig`; `VolumeControl` port probe.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `V01` | `volume_percent=100` with known S16_LE samples | Bit-exact passthrough; no scaling arithmetic applied; chunk length unchanged |
| `V02` | `volume_percent=0` | Every sample is 0 (silence); chunk length unchanged |
| `V03` | `volume_percent=25` (M4C product config value; schema default is `100`) with positive, negative and zero S16_LE samples | Sign-preserving truncation toward zero; output magnitude ≤ input magnitude for each sample; no clipping; chunk length unchanged |
| `V04` | Boundary values: `volume_percent=1` and `volume_percent=99` | Scaling applied; chunk length unchanged; zero samples remain zero |
| `V05` | Invalid config: `volume_percent` outside `0..100` (e.g. -1, 101, 100.5, None) | Rejected at construction or config load before any `AudioOutput` side effect |
| `V06` | Partial / odd-length S16_LE buffer (e.g. 1 byte, 3 bytes) | Fail-closed; no partial-sample write to underlying `AudioOutput`; upstream iterator unmodified |
| `V07` | Chunk-by-chunk streaming: 10 consecutive chunks at `volume_percent=25` | Each chunk processed independently; no cross-chunk state accumulation; `audio_first_write` observation point timing unchanged vs passthrough |
| `V08` | cancel / drain propagation: cancel during mid-stream | Cancel propagates transparently to underlying `AudioOutput`; no extra gain step |
| `V09` | Exercise `VolumeControl` port seam directly without injecting an `adjustments/volume` runtime module | Port exists and accepts volume instance without error; no Event/Signal/Fact published; State Manager state unchanged |
| `V10` | Production composition: assert exactly one `VolumeControlledAudioOutput` wraps the raw `AudioOutput` in the product wiring | Exactly one decorator instance in composition; no double-wrapping; no second gain application on any product path |
| `V11` | `volume_percent` field absent from config (schema default `100`) | Behavior identical to explicit `volume_percent=100`; bit-exact passthrough |
| `V12` | Portable import and collection with Pi-only native dependencies unavailable | `VolumeControlledAudioOutput` and `AudioOutputConfig` import without loading ALSA/GPIO/Pi-native modules |

### M4C-SS-CTRL-001 — `StreamingSpeakControl` B2 controller

Fixture: `StreamingSpeakControl` with `MockTTSAdapter`, `MockAudioOutput` call ledger, fragment
barrier, queue depth probe, and `ActionCompleted` capture. Turn correlation `(session_id,
turn_id)` is unique per case.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `C01` | Single non-empty fragment admitted then terminal | Exactly one `TTSAdapter.synthesize` call; one `AudioOutput.play/drain`; one `ActionCompleted(ok)`; queue current depth = 0 after drain; queue high-water mark = 1 after admission |
| `C02` | Two fragments admitted before first dequeue (both already in queue when B2 dequeues) | B2 makes exactly one `TTSAdapter.synthesize` call with exact `head + lookahead` concatenation; not two independent syntheses; one logical Speak operation; one `ActionCompleted(ok)` |
| `C03` | Admit third fragment while queue holds 2 (256-byte aggregate ≤ limit) | Producer backpressure applied; third admitted only after first consumed; no drop, no reorder, no unbounded task; queue never exceeds 2 items |
| `C04` | Fragment that would push queue aggregate past 256 UTF-8 bytes | Producer backpressure; oversized fragment not dropped silently; queue depth never exceeds 2 items; aggregate byte count never exceeds 256 |
| `C05` | B2 dequeues head when only one lookahead is already in queue; a third fragment is not yet queued | Batch = head + one lookahead; third fragment not pulled into same batch; no wait for future |
| `C06` | Non-empty fragment then terminal; verify prefix and equality | Admitted concatenation is an exact prefix of terminal normalized text before terminal flush; after terminal validation, admitted concatenation equals terminal normalized text; no addition of admitted text to terminal text |
| `C07` | Terminal text does not start with admitted concatenation prefix (`not terminal_text.startswith(admitted_prefix)`) | Cancel generation, queue, TTS iterator and Audio playback; `STREAMING_TERMINAL_FAILED + REUSABLE`; no `LLMResponse` or `ActionCompleted(ok)` |
| `C08` | Empty fragment attempted | Fail closed; no `synthesize` call; no `ActionCompleted(ok)` |
| `C09` | Duplicate (sequence gap = 0) fragment | Fail closed; E1 |
| `C10` | Out-of-order fragment (sequence gap > 1) | Fail closed; E1 |
| `C11` | Oversize fragment (> 256 UTF-8 bytes) | Fail closed; no `synthesize`; no `ActionCompleted(ok)` |
| `C12` | Post-terminal fragment (fragment after terminal validation) | Fail closed; existing Speak operation unaffected; no duplicate ActionCompleted |
| `C13` | Stale-operation fragment (wrong `(session_id, turn_id)`) | Dropped with sanitized diagnostic; no effect on active operation |
| `C14` | Short press while fragment in queue but not yet synthesizing | Admission closed immediately; queue cleared; no synthesize for queued items; no normal `ActionCompleted(ok)`; owner cleared; no cross-session leak |
| `C15` | Short press while `TTSAdapter.synthesize` is in progress | Synthesis aborted; remaining queue items not processed; no `ActionCompleted(ok)`; owner cleared |
| `C16` | Short press while `AudioOutput.play` is in progress | Playback stopped; no further synthesis; no `ActionCompleted(ok)`; owner cleared |
| `C17` | Shutdown signal at any phase (queued / synthesizing / playing) | Admission closed; in-flight TTS/Audio stopped; no `ActionCompleted(ok)` for active turn; no cross-turn pollution |
| `C18` | The TTS adapter raises `TTSGenerationError` during native generation after the Speak operation is active | `TTS_GENERATION_FAILED + REBUILD_REQUIRED + backend.action.speak.tts`; admission closed; Audio playback cancelled; no `ActionCompleted(ok)` |
| `C19` | TTS watchdog expires without terminal/cleanup proof | `TTS_PROTOCOL_FAILED + REBUILD_REQUIRED + backend.action.speak.tts`; bounded cleanup; no hang; no `ActionCompleted(ok)` |
| `C20` | Short-press cancellation: cooperative TTS abort times out; bounded force-abort succeeds | No fault Fact; no normal Fact; `ForceAbortReport` proves TTS owner stopped; no `ActionCompleted(ok)` |
| `C21` | Late old-operation callback (previous turn's `ActionCompleted` arrives after new turn starts) | Rejected with sanitized diagnostic; new turn's operation unaffected |
| `C22` | Control closed with no admitted fragment | Control closed cleanly; owner count = 0; no spurious Fact or event |

### M4C-SS-EXTRACT-001 — Fragment extraction boundary and normalization

Fixture: byte-chunk matrix feeding the real incremental parser; `SAFE_TEXT` fragment capture
barrier; no Speak/TTS dispatch in these cases.

| Case | Deterministic stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `E01` | Text emitted at punctuation boundary (。！？…) before 12 codepoints | Fragment emitted at punctuation; does not wait for 12-codepoint accumulation |
| `E02` | Text without punctuation: exactly 12 normalized codepoints accumulated | Fragment emitted at 12; not before |
| `E03` | Text without punctuation: 11 codepoints accumulated, then terminal flush | Fragment emitted at terminal; no pre-terminal fragment |
| `E04` | Unicode combining sequence split across chunks | Fragment not emitted until combining sequence is stable; no partial combining sequence in output |
| `E05` | Escape sequence split across chunks | JSON syntax bytes withheld; emitted text is decoded semantic content only |
| `E06` | Non-BMP codepoints (4-byte UTF-8) at 12-codepoint boundary | Codepoints counted by Unicode scalar value; boundary correct |
| `E07` | B2 dequeues head when exactly one lookahead is already in queue; second lookahead not yet available | Batch = head + one lookahead; second lookahead processed in next dequeue cycle |
| `E08` | No lookahead available at dequeue time | Batch = head only; no wait for future fragment |
| `E09` | `end=true` terminal with non-empty text not yet emitted as fragment | Full terminal text flushed as final fragment; no partial-commit; prefix equality holds |
| `E10` | Whitespace-only text after normalization at boundary | No fragment emitted; no fabricated text |

### M4C-SS-OUTCOME-001 — Streaming speak outcome coverage

Fixture: parameterized Reasoner with fragment ledger, TTS/Audio fakes and SM barriers. Each
case verifies exactly one logical operation and zero or one legitimate terminal Fact.

| Case | Stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `O01` | Zero fragments admitted; inject `ReplaceableGenerationFailure` with complete typed request-terminal and `engine_usable=True` proof | Existing fixed R2 `REPLACE_NEXT` outcome; one `ActionCompleted` with route `REPLACE_NEXT`; no partial Speak; `END_SESSION` not permitted for this case |
| `O02` | One or more fragments admitted; terminal text does not start with admitted prefix | `STREAMING_TERMINAL_FAILED + REUSABLE`; generation, queue, TTS and Audio cancelled; no `LLMResponse` or `ActionCompleted(ok)` |
| `O03` | Fragments admitted; one or more cleanup proof components missing (request terminal / stream cleanup / Conversation cleanup / `engine_usable`) | `LLM_CLEANUP_UNPROVEN + UNPROVEN + LLM key`; no `ActionCompleted(ok)` |
| `O04` | Identity / intent / wire inconsistency (`session_id`, `turn_id`, or correlation mismatch) | `LLM_PROTOCOL_FAILED + UNPROVEN + LLM key`; no normal Fact |
| `O05` | Control closed without any admitted fragment; zero owner | Owner count = 0; no Fact; no Error; control closed cleanly |
| `O06` | Terminal-only degradation: no pre-terminal fragment admitted; complete terminal text used as single final fragment via B2 terminal-only path | One `synthesize` call with complete terminal text; one `ActionCompleted(ok)`; no A-mode retry; no duplicate |
| `O07` | Worker emits a safe partial fragment, then returns a proven replaceable invalid-semantic terminal | Partial output is never converted into normal terminal success; the typed failure remains eligible for the existing O02 mapping |
| `O08` | LLM emits a partial fragment, then raises `LLM_BACKEND_FAILED` | Streaming control and future playback are cleared; exactly one LLM fault; no `LLMResponse` or successful `ActionCompleted` |
| `O09` | TTS raises `TTS_PROTOCOL_FAILED` while StreamingSpeak owns queued/inflight fragments | Pending bytes, inflight fragments, PCM and owner are cleared before one fault is exposed; no audio or successful `ActionCompleted` |

### M4C-NOINPUT-001 — Session no-input streak and product classification

Fixture: one Product Session with fake Listen/ASR seam; streak counter probe; fixed-speech
ledger; `PerceptionResult.extra` capture.

| Case | Stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `N01` | First listen timeout in a Session | Streak = 1; fixed speech「我沒聽清楚，請再說一次。」played; same Session/Conversation retained; LLM not called |
| `N02` | Second consecutive listen timeout (streak = 2) | No retry speech; no LLM call; `rest + END_SESSION`; full cleanup; back to IDLE |
| `N03` | First `NO_SPEECH` ASR stable code | Streak = 1; same speech and Session behavior as N01 |
| `N04` | First listen completed but usable text empty | Streak = 1; same speech and Session behavior as N01 |
| `N05` | Valid non-empty listen result after streak = 1 | Streak reset to 0 before LLM admission; LLM called normally |
| `N06` | Session cleanup: end Session after streak = 1, start new Session | New Session starts with streak = 0; no inherited retry state |
| `N07` | `MULTIPLE_UTTERANCES` ASR code | Fixed speech「請一次只說一句。」played; listen re-attempted; streak not incremented |
| `N08` | `INFERENCE_REJECTED` (legacy): treated as system fault | Not counted in no-input streak; no user-facing retry prompt; ERROR / recovery path per M4-ERR |
| `N09` | `INVALID_FRAME`: internal contract failure | E1 / ERROR path; not a no-input event; streak unchanged |
| `N10` | Backend system fault during PERCEPTION | Not counted in no-input streak; no retry prompt; ERROR / recovery per M4-ERR |
| `N11` | ASR stable code stored in `PerceptionResult.extra["asr_error_code"]` | Sanitized stable code present; no exception string, transcript, PCM, or native diagnostic in field |

### M4C-DISPLAY-001 — Display degradation isolation

Fixture: real Event Bus, State Manager, Reasoner, Speak, Rest and SessionDisplay with deterministic
voice backends. The fake Display succeeds through startup and WAKE, then raises once when THINK
projects final ASR text.

| Case | Stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `D01` | One Display `show()` failure during THINK in a normal two-turn Session | Rendering latches disabled with one `DISPLAY_RENDER_DISABLED`; no later device call, `ErrorOccurred` or ERROR state; both LLM→TTS→Audio turns complete and cleanup reaches IDLE |

### M4C-REG-001 — Directly affected regression continuity

Fixture: run the accepted M4A/M4B/M4-ERR tests that directly exercise production symbols changed
by M4C or their immediate product wiring. Do not turn source scanning, an exact test-file inventory,
skip-marker policing or evidence packaging into product assertions.

| Case | Stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `G01` | Run directly affected accepted regression nodes | failures=0 and errors=0; a skipped test does not provide coverage for the changed behavior |
| `G02` | `VolumeControlledAudioOutput` product composition | Exactly one wrapper is present and no product Speak path bypasses it |
| `G03` | Import and collect the changed pure-Python surfaces without Pi-only dependencies | Workstation and target-Pi environments import and collect successfully |

---

## 5. Pi product verification — whole-product scenarios

Portable results cannot replace the real Pi product paths below. S01–S05 contain seven hardware
sub-runs; S06–S09 are not Pi catalog entries.

Initialize one aggregate `PV` identity:

```text
python3.13 scripts/run-m4c-pv.py init \
  --pv-run-id <NEW_PV_RUN_ID> \
  --public-root <NEW_EMPTY_PUBLIC_ROOT> \
  --private-root <NEW_EMPTY_PRIVATE_ROOT>
```

`init` creates the result roots. Product configuration is passed explicitly to each run. It does
not calculate or validate content digests; any necessary transfer/candidate comparison is a separate
operator diagnostic rather than a Test ID assertion.

### 5.1 Fixed sub-run catalog

The Pi catalog contains exactly **7 sub-runs** over **5 Test IDs**:

```text
S01: START_IDLE            (1 sub-run)
S02: NORMAL_END_B2         (1 sub-run)
S03: TWO_TIMEOUTS          (1 sub-run)
S04: PERCEPTION, THINK, ACTION     (3 sub-runs)
S05: APP_EXIT              (1 sub-run)
```

The finalizer requires one designated Pass for each catalog entry and rejects an unknown or
duplicate active variant. No human-result field is part of this catalog.

### 5.2 Execution matrix

| Test ID | Variant / sub-run | Human result | Evidence locator |
| :--- | :--- | :--- | :--- |
| `M4C-PI-S01` | `START_IDLE` | automatic | `<public_root>/<pv_run_id>/M4C-PI-S01/` |
| `M4C-PI-S02` | `NORMAL_END_B2` | automatic | `<public_root>/<pv_run_id>/M4C-PI-S02/` |
| `M4C-PI-S03` | `TWO_TIMEOUTS` | automatic | `<public_root>/<pv_run_id>/M4C-PI-S03/` |
| `M4C-PI-S04` | `PERCEPTION`, `THINK`, `ACTION` | automatic | `<public_root>/<pv_run_id>/M4C-PI-S04/` |
| `M4C-PI-S05` | `APP_EXIT` | automatic | `<public_root>/<pv_run_id>/M4C-PI-S05/` |

### 5.3 Common Pi execution requirements

- All sub-runs execute with network disabled and `volume_percent=25`.
- Display profile: `IDLE=待命`, `WAKE=準備中`, `PERCEPTION=接收中`, `THINK=思考中`,
  `ACTION=回應中`, `ERROR=錯誤`; IDLE clears Main; shutdown holds Blank.
- THINK Main shows final ASR text; ACTION Main shows only terminal-validated answer (no
  streaming provisional fragment).
- Public evidence must not contain: transcript, prompt, raw model output, PCM, session ID,
  credential, or complete private path.
- Success endpoints: cleanup-complete `IDLE` or graceful `exit 0` as specified by the scenario.

### 5.4 M4C-PI-S01 — Startup and IDLE

```text
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S01 --variant START_IDLE \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --config <PRODUCT_CONFIG> --fresh-setup
```

| Observation | Required assertion |
| :--- | :--- |
| Application starts; required resources become READY | No Conversation created before WAKE; no audio capture before WAKE |
| Display | Status=`待命` within bounded timeout; Main empty; display open |
| Terminal | IDLE; application waiting for button |

### 5.5 M4C-PI-S02 — Normal two-turn session and graceful close

```text
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S02 --variant NORMAL_END_B2 \
  --utterance-1 '天空為什麼是藍色的？' --utterance-2 '請結束對話。' \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --config <PRODUCT_CONFIG> --fresh-setup
```

| Observation | Required assertion |
| :--- | :--- |
| Conversation created | Only after WAKE; not before short-press |
| Turn 1 THINK | Main shows final ASR text; at least one pre-terminal `SAFE_TEXT` is admitted to the unique B2 control |
| Turn 1 ACTION | Only `B2-ONE-LOOKAHEAD-COALESCE`; terminal-validated answer is displayed and played; private oracle compares the actual shown/spoken/terminal values and exposes only equality booleans; no A-mode or second full-response path |
| Turn 2 (`end=true`) | Non-empty answer: played to completion then REST; empty answer: direct REST |
| Session/Conversation cleanup | The active Session ends, affected operations finish and no late output is accepted |
| Final state | IDLE; Status=`待命`; Main empty |

**Automatic B2 timeline** (Turn 1): Record monotonic timestamps for:

```
button_acceptance → conversation_ready → asr_final → llm_send →
first_safe_text → tts_first_pcm → audio_first_write → llm_terminal
```

Assert the listed causal order. No duration establishes a PASS ceiling.

### 5.6 M4C-PI-S03 — Consecutive no-input and automatic session close

```text
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S03 --variant TWO_TIMEOUTS \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --config <PRODUCT_CONFIG> --fresh-setup
```

Stimulus: two consecutive real product Listen windows with no speech until the configured listen
timeout; both outcomes must be `timeout` (not `NO_SPEECH`).

| Observation | Required assertion |
| :--- | :--- |
| First `timeout` | Fixed speech「我沒聽清楚，請再說一次。」played; same Session/Conversation; LLM not called |
| Second `timeout` | No retry speech; no LLM call; `rest + END_SESSION` |
| Cleanup | The active Session ends and no retry, LLM call or late playback remains |
| Final state | IDLE; Status=`待命`; Main empty |

### 5.7 M4C-PI-S04 — Interrupt (3 sub-runs)

Three fresh sub-runs:

```text
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S04 --variant PERCEPTION \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --config <PRODUCT_CONFIG> --fresh-setup

python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S04 --variant THINK \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --config <PRODUCT_CONFIG> --fresh-setup

python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S04 --variant ACTION \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --config <PRODUCT_CONFIG> --fresh-setup
```

| Variant | Interrupt point | Required assertions |
| :--- | :--- | :--- |
| `PERCEPTION` | Short press during active ASR listen | Audio capture stopped; no LLM call; short-press interrupt convergence completes (not fabricated as a system fault); Conversation and owner cleanup complete; no old-operation normal success |
| `THINK` | Short press during LLM generation | Generation cancelled; no normal `LLMResponse`; no `ActionCompleted(ok)`; cleanup complete |
| `ACTION` | Short press during TTS/audio playback | Playback stopped; no further synthesis; no `ActionCompleted(ok)` for interrupted turn; cleanup complete |

All variants: no cross-session leakage; final state IDLE; Main cleared.

### 5.8 M4C-PI-S05 — Application exit (long press)

```text
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S05 --variant APP_EXIT \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --config <PRODUCT_CONFIG> --fresh-setup
```

| Observation | Required assertion |
| :--- | :--- |
| Long press from IDLE/READY | No new Session accepted after exit signal |
| Reverse cleanup | All child/HAL owners exit within bounded timeout |
| Display | Final blank |
| Process exit | `exit 0`; no orphaned processes in PGID |

### 5.9 PV aggregation and finalization

After all 7 designated sub-run results exist:

```text
python3.13 scripts/run-m4c-pv.py finalize \
  --pv-run-id <PV_RUN_ID> \
  --public-root <PUBLIC_ROOT> \
  --private-root <PRIVATE_ROOT>
```

`pv_status=Pass` only when:
- All 7 catalog entries each have exactly one designated result with script status Pass.
- The final pending content has completed all applicable Pi automated/integration verification.
- If candidate identity needs confirmation before commit preparation, the operator performs one
  independent comparison; it is not a product Test ID or repeated sub-run assertion.

**Attempts vs. designated results.** Each sub-run command creates one attempt. The finalizer
selects exactly one *designated* (non-superseded) result per catalog entry from all attempts
present under that `pv_run_id`. Retrying a failed sub-run atomically marks the previous
attempt for that catalog entry as *superseded*; the new attempt becomes the
designated result for that entry. Superseded attempts remain diagnostic history but are not counted
among the 7 designated results and cannot satisfy any catalog entry.

The finalizer rejects: a missing designated result for any catalog entry, duplicate active
designations, an unknown catalog entry, or an ambiguous supersession chain.

---

## 6. Requirement traceability

| M4C design section | Portable Test IDs | Pi sub-run variants |
| :--- | :--- | :--- |
| Static output volume boundary | `M4C-VOL-001` | `S02/NORMAL_END_B2` |
| B2 streaming-speak controller | `M4C-SS-CTRL-001` | `S02/NORMAL_END_B2`, `S04/ACTION` |
| Fragment extraction / punctuation-or-12 | `M4C-SS-EXTRACT-001` | `S02/NORMAL_END_B2` |
| Streaming-speak outcome / error taxonomy | `M4C-SS-OUTCOME-001` O01–O09 | `S04/ACTION` |
| Session no-input streak | `M4C-NOINPUT-001` | `S03/TWO_TIMEOUTS` |
| Display degradation isolation | `M4C-DISPLAY-001` | — |
| Startup / IDLE | — | `S01/START_IDLE` |
| Normal two-turn session and close, eligible B2 proof | — | `S02/NORMAL_END_B2` |
| Interrupt (PERCEPTION / THINK / ACTION) | `M4C-SS-CTRL-001` C14–C16 | `S04/PERCEPTION`, `S04/THINK`, `S04/ACTION` |
| Application exit | — | `S05/APP_EXIT` |
| Recoverable backend fault baseline | `M4C-SS-OUTCOME-001` O08/O09 plus Accepted M4-ERR | — |
| Recovery fatal / exit 4 | Accepted M4B/M4-ERR regressions | — |
| Streaming speak B2 audible path | — | `S02/NORMAL_END_B2` |
| Streaming speak interrupt | `M4C-SS-CTRL-001` C14/C15 | `S04/ACTION` |
| Regression continuity | `M4C-REG-001` | affected Pi paths only |
| Automatic B2 timeline | — | `S02/NORMAL_END_B2` |
