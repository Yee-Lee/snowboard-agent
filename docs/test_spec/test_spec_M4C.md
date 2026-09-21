# M4C — Complete Offline Voice-Device Integration Test Specification

## 1. Authority, scope and disposition

**Design authority**: [`docs/milestones/M4C.md`](../milestones/M4C.md)

**Upstream accepted inputs**:
- M4A Audio: Accepted at commit `6c3ba95455dc5c2a152aa230b8ae5915887fe6a9`.
- M4B LLM/Reasoner: Accepted at commit `f87cfa50b9c9415430973076a59c6b1961228090`.
- M4-ERR: Accepted at commit `f572915d0b0d5c52067e9100c5b022e57aefe506`.
- M4C-SS: Closed／Adopted `B2-ONE-LOOKAHEAD-COALESCE`; POC delivery binding commit
  `a492a1416721c73c989dd46067b3e9dd1c24508d`.

**Status**: Current — Tester-owned entry spec for M4C. No implementation or acceptance result
in this document. Developer entry requires this spec to be complete.

**In scope**: `VolumeControlledAudioOutput` decorator and config; `StreamingSpeakControl`
(`B2-ONE-LOOKAHEAD-COALESCE`) portable controller coverage; session no-input streak and
product classification; whole-product scenario composition
(`M4C-S01`–`M4C-S09`); product-quality timeline; M4C regression continuity.

**Out of scope**: barge-in; runtime volume adjustment; Display animation/graphics (留 M7);
camera/look (留 M6); tool/MQTT (留 M5); repeated-session soak; formal latency/memory/thermal
ceilings (留 ALPHA); re-running M4-ERR cause-code matrix in integration; POC pass credit for
any M4C Test ID.

---

## 2. Result vocabulary and execution matrix

### 2.1 Result vocabulary

- **Pass**: every required assertion passes, evidence is present, and tracked-content /
  config / artifact digest agrees. Where USER audible-quality inspection is required, that
  result is also Pass.
- **Fail**: an assertion fails, a forbidden call or artifact occurs, a test is
  skipped / xfail / xpass, or a required USER audible-quality result is missing or Fail.
- **Incomplete**: a required evidence field, measurement, or explicit null reason is absent.
  Incomplete never converts to Pass.
- **Blocked**: the bound tracked content, target, artifact, or required hardware is unavailable
  before execution begins.
- **NeedsHumanReview**: a case requires USER audible-quality inspection, has script status
  Pass and complete captured evidence, but no USER verdict yet. Not Pass; cannot be
  designated by aggregation.

Script-only cases (all cases except S02 timeline-quality and S09/QUALITY_T02) are decided
entirely by automatic assertions and target facts; no separate Developer human-result column
or manual gate is added.

### 2.2 Execution matrix

| Matrix ID | Layer | Required environment | Timeout |
| :--- | :--- | :--- | :--- |
| `PU` | Portable unit | CPython 3.11, 3.12, 3.13; Linux x86_64/aarch64 and macOS arm64; no native/network | 60 s per Test ID |
| `PI` | Portable integration | CPython 3.11, 3.12, 3.13; Linux x86_64/aarch64 and macOS arm64; deterministic adapter/fake seams | 90 s per Test ID |
| `PS` | Portable subprocess | Linux x86_64/aarch64, CPython 3.13 only; fake child in real POSIX process group | 120 s per Test ID |
| `PV` | Pi product verification | Raspberry Pi 5 4 GB, Debian 13 aarch64, CPython 3.13; real LiteRT-LM, Matcha TTS, ALSA I2S speaker, USB microphone; `volume_percent=25`; network disabled; same tracked bytes as pending commit | 60 min per Test-ID sub-run |

Every result record contains: `schema_version`, `test_id`, `case_id`, `base_sha`,
`tracked_content_sha256`, pending-path set, harness/config/artifact digests, target facts,
matrix/platform/Python identity, start/end monotonic timestamps, `status`, and
`evidence_sha256`. Changing any pending byte, harness/config/artifact digest or target fact
invalidates the result. `user_result` is present only for S02 timeline-quality and
S09/QUALITY_T02; all other results are automatic.

All async and concurrent cases use named `asyncio.Event`, pipe/queue acknowledgement, task-join,
action-complete, and close-proof barriers. Correctness sleeps, poll-until-lucky loops and
timing-order assumptions are forbidden. Fakes expose call ledgers and fail if an unexpected
model, speech, file-write or network call occurs.

Timeouts prevent hangs; they are not response-time PASS ceilings. A timeout is Fail unless the
case explicitly tests a watchdog and observes required bounded cleanup.

### 2.3 Evidence and privacy rules

Public evidence contains only: sequence, length, digest, queue high-water mark, timing node
labels and stable codes. It must not contain: transcript, prompt, raw model output, PCM,
fragment or terminal text, session ID, credential, or complete private path.

---

## 3. Portable specification catalog

| Test ID | Authority and primary risk | Layer / timeout | Evidence locator |
| :--- | :--- | :--- | :--- |
| `M4C-VOL-001` | M4C §Static output volume boundary; scaling mutates iterator or gain applied multiple times | `PU, PI`; 60/90 s | `portable/M4C-VOL-001.*` |
| `M4C-SS-CTRL-001` | M4C-SS §Adopted streaming-speak contract clauses 1–9; B2 controller admits wrong fragment, allows unbounded queue, or leaks owner | `PU, PI, PS`; 60/90/120 s | `portable/M4C-SS-CTRL-001.*` |
| `M4C-SS-EXTRACT-001` | M4C-SS clause 2; punctuation-or-12 boundary, Unicode stability, terminal flush, exact concatenation | `PU`; 60 s | `portable/M4C-SS-EXTRACT-001.*` |
| `M4C-SS-OUTCOME-001` | M4C-SS clauses 5–8; zero-fragment R2, partial-fragment STREAMING_TERMINAL_FAILED, cleanup-unproven, protocol-failed outcomes | `PI`; 90 s | `portable/M4C-SS-OUTCOME-001.*` |
| `M4C-NOINPUT-001` | M4C §Session no-input completion; streak counter, product speech, cross-session isolation, request-code classification | `PU, PI`; 60/90 s | `portable/M4C-NOINPUT-001.*` |
| `M4C-REG-001` | Accepted M4A/M4B/M4-ERR regression baseline; deletion or weakening of covered nodes | `PI`; 180 s suite cap | `portable/M4C-REG-001.*` |

All PU and PI Test IDs run on CPython 3.11, 3.12 and 3.13. PS is Linux/CPython 3.13 only.

---

## 4. Portable cases and acceptance criteria

### M4C-VOL-001 — `VolumeControlledAudioOutput` scaling and composition

Fixture: a byte-exact S16_LE sample bank; `MockAudioOutput` call ledger; injected
`AudioOutputConfig`; `VolumeControl` port probe. All three Python minors required.

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
| `V12` | Portable import and collection: import `VolumeControlledAudioOutput` and `AudioOutputConfig` on CPython 3.11, 3.12 and 3.13 with Pi-only native dependencies unavailable | Import succeeds on all three Python minors; no `ImportError` from ALSA/GPIO/Pi-native modules |

### M4C-SS-CTRL-001 — `StreamingSpeakControl` B2 controller

Fixture: `StreamingSpeakControl` with `MockTTSAdapter`, `MockAudioOutput` call ledger, fragment
barrier, queue depth probe, and `ActionCompleted` capture. Turn correlation `(session_id,
turn_id)` is unique per case. All three Python minors required for PU/PI; PS on CPython 3.13 only.

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
barrier; no Speak/TTS dispatch in these cases. All three Python minors required.

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
All three Python minors required.

| Case | Stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `O01` | Zero fragments admitted; inject `ReplaceableGenerationFailure` with complete typed request-terminal and `engine_usable=True` proof | Existing fixed R2 `REPLACE_NEXT` outcome; one `ActionCompleted` with route `REPLACE_NEXT`; no partial Speak; `END_SESSION` not permitted for this case |
| `O02` | One or more fragments admitted; terminal text does not start with admitted prefix | `STREAMING_TERMINAL_FAILED + REUSABLE`; generation, queue, TTS and Audio cancelled; no `LLMResponse` or `ActionCompleted(ok)` |
| `O03` | Fragments admitted; one or more cleanup proof components missing (request terminal / stream cleanup / Conversation cleanup / `engine_usable`) | `LLM_CLEANUP_UNPROVEN + UNPROVEN + LLM key`; no `ActionCompleted(ok)` |
| `O04` | Identity / intent / wire inconsistency (`session_id`, `turn_id`, or correlation mismatch) | `LLM_PROTOCOL_FAILED + UNPROVEN + LLM key`; no normal Fact |
| `O05` | Control closed without any admitted fragment; zero owner | Owner count = 0; no Fact; no Error; control closed cleanly |
| `O06` | Terminal-only degradation: no pre-terminal fragment admitted; complete terminal text used as single final fragment via B2 terminal-only path | One `synthesize` call with complete terminal text; one `ActionCompleted(ok)`; no A-mode retry; no duplicate |

### M4C-NOINPUT-001 — Session no-input streak and product classification

Fixture: one Product Session with fake Listen/ASR seam; streak counter probe; fixed-speech
ledger; `PerceptionResult.extra` capture. All three Python minors required.

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

### M4C-REG-001 — Regression continuity and anti-weakening

Fixture: candidate diff against `base_sha` determines the affected symbol set; the accepted
regression/Test ID inventory from M4A (`6c3ba954...`), M4B (`f87cfa50...`) and M4-ERR
(`f572915d...`) is the node baseline. Indirect callers discovered through the diff are
included; import-only affected-test discovery is not sufficient.
All three Python minors required.

| Case | Stimulus | Required assertions and forbidden effects |
| :--- | :--- | :--- |
| `G01` | AST scan of `src/**/*.py` and `tests/**/*.py` | No direct/aliased skip, xfail, `pytest.skip/xfail`, false-constant assertion or marker omission affecting any existing M4A/M4B/M4-ERR/Foundation Test ID |
| `G02` | Run all M4A/M4B/M4-ERR/Foundation regression nodes whose production dependency is changed or shared by the M4C delta (via candidate diff) | failures=0, errors=0, skipped=0; no xfail/xpass; exact collected node list published |
| `G03` | `VolumeControlledAudioOutput` inserted between M4A `AudioOutput` and `Speak` in composition | M4A portable acceptance nodes still pass; no new direct `AudioOutput` caller bypasses the decorator in product wiring |
| `G04` | Portable import and collection for pure-Python modules (`StreamingSpeakControl`, `AudioOutputConfig`, no-input streak counter) on CPython 3.11, 3.12 and 3.13 with Pi-only native dependencies unavailable | Import and pytest collection succeed on all three Python minors without Pi-native dependencies |

---

## 5. Pi product verification — whole-product scenarios

These Test IDs are pending until the automatically bound tracked content, target, implemented
harness and Tester execution gate exist. Portable fake results cannot satisfy them.

Initialize one aggregate `PV` identity:

```text
python3.13 scripts/run-m4c-pv.py init \
  --pv-run-id <NEW_PV_RUN_ID> \
  --public-root <NEW_EMPTY_PUBLIC_ROOT> \
  --private-root <NEW_EMPTY_PRIVATE_ROOT> \
  --binding-manifest <BINDING_JSON>
```

`init` fails unless both roots are newly empty and the binding manifest automatically attests:
`base_sha`, `tracked_content_sha256`, pending-path set, harness/config/artifact digests, and
target facts including `volume_percent=25` and network disabled. No role authorization,
reviewer identity, signature or freeze artifact is an execution input.

### 5.1 Fixed sub-run catalog

The finalizer requires exactly **17 fresh sub-runs** over **9 aggregate Test IDs**:

```text
S01: START_IDLE            (1 sub-run)
S02: NORMAL_END            (1 sub-run)
S03: TWO_TIMEOUTS          (1 sub-run)
S04: PERCEPTION, THINK, ACTION     (3 sub-runs)
S05: APP_EXIT              (1 sub-run)
S06: PERCEPTION_ASR_INFERENCE, THINK_LLM_CHILD_EXIT, ACTION_TTS_CHILD_EXIT  (3 sub-runs)
S07: DISPLAY_DEGRADE       (1 sub-run)
S08: LLM_READY_MISMATCH_FATAL      (1 sub-run)
S09: LIVE_ELIGIBLE_L02, QUALITY_T02, QUEUED, SYNTHESIZING, PLAYING  (5 sub-runs)
```

The finalizer rejects a missing, duplicate, extra, or mismatched variant. A missing sub-run
partition is Incomplete for that Test ID and prevents `pv_status=Pass`.

`user_result` is required for exactly two sub-runs: `S02/NORMAL_END` (timeline quality) and
`S09/QUALITY_T02` (speech quality). All other sub-run results are automatic.

### 5.2 Execution matrix

| Test ID | Variant / sub-run | Human result | Evidence locator |
| :--- | :--- | :--- | :--- |
| `M4C-PI-S01` | `START_IDLE` | automatic | `<public_root>/<pv_run_id>/M4C-PI-S01/` |
| `M4C-PI-S02` | `NORMAL_END` | `user_result` (timeline quality) | `<public_root>/<pv_run_id>/M4C-PI-S02/` |
| `M4C-PI-S03` | `TWO_TIMEOUTS` | automatic | `<public_root>/<pv_run_id>/M4C-PI-S03/` |
| `M4C-PI-S04` | `PERCEPTION`, `THINK`, `ACTION` | automatic | `<public_root>/<pv_run_id>/M4C-PI-S04/` |
| `M4C-PI-S05` | `APP_EXIT` | automatic | `<public_root>/<pv_run_id>/M4C-PI-S05/` |
| `M4C-PI-S06` | `PERCEPTION_ASR_INFERENCE`, `THINK_LLM_CHILD_EXIT`, `ACTION_TTS_CHILD_EXIT` | automatic | `<public_root>/<pv_run_id>/M4C-PI-S06/` |
| `M4C-PI-S07` | `DISPLAY_DEGRADE` | automatic | `<public_root>/<pv_run_id>/M4C-PI-S07/` |
| `M4C-PI-S08` | `LLM_READY_MISMATCH_FATAL` | automatic | `<public_root>/<pv_run_id>/M4C-PI-S08/` |
| `M4C-PI-S09` | `LIVE_ELIGIBLE_L02`, `QUALITY_T02`, `QUEUED`, `SYNTHESIZING`, `PLAYING` | `user_result` for `QUALITY_T02` only; others automatic | `<public_root>/<pv_run_id>/M4C-PI-S09/` |

### 5.3 Common Pi execution requirements

- All sub-runs execute with network disabled and `volume_percent=25`.
- Display profile: `IDLE=待命`, `WAKE=準備中`, `PERCEPTION=接收中`, `THINK=思考中`,
  `ACTION=回應中`, `ERROR=錯誤`; IDLE clears Main; shutdown holds Blank.
- THINK Main shows final ASR text; ACTION Main shows only terminal-validated answer (no
  streaming provisional fragment).
- Public evidence must not contain: transcript, prompt, raw model output, PCM, session ID,
  credential, or complete private path.
- Success endpoints: cleanup-complete `IDLE`, graceful `exit 0`, or explicitly listed Level 3
  `exit 4`. No other terminal state is Pass.

### 5.4 M4C-PI-S01 — Startup and IDLE

```text
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S01 --variant START_IDLE \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup
```

| Observation | Required assertion |
| :--- | :--- |
| Application starts; required resources become READY | No Conversation created before WAKE; no audio capture before WAKE |
| Display | Status=`待命` within bounded timeout; Main empty; display open |
| Terminal | IDLE; application waiting for button |

### 5.5 M4C-PI-S02 — Normal two-turn session and graceful close

```text
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S02 --variant NORMAL_END \
  --utterance-1 '你是誰？' --utterance-2 '請結束對話。' \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup
```

| Observation | Required assertion |
| :--- | :--- |
| Conversation created | Only after WAKE; not before short-press |
| Turn 1 THINK | Main shows final ASR text for「你是誰？」|
| Turn 1 ACTION | Main shows terminal-validated answer; audio played; shown text equals spoken text |
| Turn 2 (`end=true`) | Non-empty answer: played to completion then REST; empty answer: direct REST |
| Session/Conversation cleanup | Matching close proof; bounded owner cleanup |
| Final state | IDLE; Status=`待命`; Main empty |

**Product-quality timeline** (Turn 1 and Turn 2): Record monotonic timestamps for:

```
button_acceptance → conversation_ready → asr_final → llm_send →
first_safe_text → llm_terminal → tts_first_pcm →
audio_first_write → physical_audible_onset → final_audible_sample
```

Assert nondecreasing order of all applicable nodes. Every missing/not-applicable node is
explicit null with stable reason. No duration establishes a PASS ceiling.

**USER audible-quality inspection**: Speech is understandable at approximately 25 % volume;
no clipping; no duplicate, missing or reordered content; no disruptive artificial boundary.
VAD observation: note any tail truncation, missing words, or excess silence (reproducible
problems only trigger focused delta; no unilateral parameter change during verification).
`user_result` binds the exact `pv_run_id`, `sub_run_id`, `base_sha` and `tracked_content_sha256`.

### 5.6 M4C-PI-S03 — Consecutive no-input and automatic session close

```text
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S03 --variant TWO_TIMEOUTS \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup
```

Stimulus: two consecutive real product Listen windows with no speech until the configured listen
timeout; both outcomes must be `timeout` (not `NO_SPEECH`).

| Observation | Required assertion |
| :--- | :--- |
| First `timeout` | Fixed speech「我沒聽清楚，請再說一次。」played; same Session/Conversation; LLM not called |
| Second `timeout` | No retry speech; no LLM call; `rest + END_SESSION` |
| Cleanup | Conversation close proof; bounded owner cleanup |
| Final state | IDLE; Status=`待命`; Main empty |

### 5.7 M4C-PI-S04 — Interrupt (3 sub-runs)

Three fresh sub-runs:

```text
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S04 --variant PERCEPTION \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup

python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S04 --variant THINK \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup

python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S04 --variant ACTION \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup
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
  --binding-manifest <BINDING_JSON> --fresh-setup
```

| Observation | Required assertion |
| :--- | :--- |
| Long press from IDLE/READY | No new Session accepted after exit signal |
| Reverse cleanup | All child/HAL owners exit within bounded timeout |
| Display | Final blank |
| Process exit | `exit 0`; no orphaned processes in PGID |

### 5.9 M4C-PI-S06 — Recoverable fault (3 sub-runs)

Three fresh sub-runs with fixed fault codes:

```text
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S06 --variant PERCEPTION_ASR_INFERENCE \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup

python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S06 --variant THINK_LLM_CHILD_EXIT \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup

python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S06 --variant ACTION_TTS_CHILD_EXIT \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup
```

| Variant | Injected fault | Required fault code | Required terminal |
| :--- | :--- | :--- | :--- |
| `PERCEPTION_ASR_INFERENCE` | `asr.inference.rejected` during active real ASR inference | `ASR_INFERENCE_FAILED + REBUILD_REQUIRED + backend.perception.listen.asr` | Rebuild READY; final IDLE |
| `THINK_LLM_CHILD_EXIT` | `llm.child.exit` during active GENERATE | `LLM_BACKEND_FAILED + REBUILD_REQUIRED + backend.cognition.reasoner.llm` | Rebuild READY; final IDLE |
| `ACTION_TTS_CHILD_EXIT` | `tts.child.exit` during active synthesize | `TTS_PROTOCOL_FAILED + REBUILD_REQUIRED + backend.action.speak.tts` | Rebuild READY; final IDLE |

All variants: no fabricated normal Fact; ERROR safe summary; no user retry prompt; no second
Session required; M4-ERR cause-code matrix not re-run.

### 5.10 M4C-PI-S07 — Display degradation

```text
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S07 --variant DISPLAY_DEGRADE \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup
```

| Observation | Required assertion |
| :--- | :--- |
| Display runtime failure injected during normal Session | Display latches disabled per existing contract |
| Voice main path | Continues without entering ERROR; normal LLM→TTS→Audio path completes |
| Process exit code | Unchanged by Display failure |
| Final state | Session cleanup → IDLE |

### 5.11 M4C-PI-S08 — Recovery fatal (exit 4)

```text
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S08 --variant LLM_READY_MISMATCH_FATAL \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup
```

Stimulus: fire `llm.child.exit`; replacement child returns READY with `profile_id` different
from `core-m4b-cognition-001`.

| Observation | Required assertion |
| :--- | :--- |
| No false IDLE or new Session accepted | Automatic; no fabricated recovery |
| Cleanup | Bounded; sanitized single root; no raw exception string in public evidence |
| Process exit | Exactly `exit 4` |

### 5.12 M4C-PI-S09 — Streaming speak (5 sub-runs)

Five fresh sub-runs:

```text
# Live eligible turn
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S09 --variant LIVE_ELIGIBLE_L02 \
  --utterance '天空為什麼是藍色的？' \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup

# Fixed quality sample
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S09 --variant QUALITY_T02 \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup

# Interrupt variants — three fresh sub-runs, one per variant
python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S09 --variant QUEUED \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup

python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S09 --variant SYNTHESIZING \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup

python3.13 scripts/run-m4c-pv.py run \
  --test-id M4C-PI-S09 --variant PLAYING \
  --pv-run-id <PV_RUN_ID> --sub-run-id <NEW_SUB_RUN_ID> \
  --public-partition <NEW_EMPTY_PUBLIC_PARTITION> \
  --private-partition <NEW_EMPTY_PRIVATE_PARTITION> \
  --binding-manifest <BINDING_JSON> --fresh-setup
```

**`LIVE_ELIGIBLE_L02`** (`天空為什麼是藍色的？`):

If the real LiteRT-LM produces no pre-terminal fragment for this input, the sub-run is
**Incomplete** (must not switch to A-mode or any alternative path).

Required automatic assertions when at least one pre-terminal fragment is produced:

| Observation | Required assertion |
| :--- | :--- |
| Same-clock node ordering | `first_safe_text → tts_first_pcm → audio_first_write → physical_audible_onset` nondecreasing |
| Onset before terminal | `physical_audible_onset` timestamp strictly precedes `llm_terminal` timestamp |
| Acoustic uncertainty | Measured clock-to-acoustic mapping uncertainty ≤ 50 ms; `llm_terminal − physical_audible_onset` strictly greater than that measured uncertainty |
| B2 path | Only `B2-ONE-LOOKAHEAD-COALESCE`; no A-mode or second full-response path |
| Spoken text vs terminal | Spoken digest matches terminal-validated answer digest; no provisional fragment shown in Display |

Model text and audio remain private; public evidence contains only lengths, digests, timings and verdicts.

**`QUALITY_T02`** — fixed controlled trace (real Matcha / Audio):

```text
fragments = 「因為太陽光穿過大氣，」 + 「藍光被散射，」 + 「所以天空看起來是藍色的。」
terminal  = 「因為太陽光穿過大氣，藍光被散射，所以天空看起來是藍色的。」
```

Script verifies: exact three fragments in sequence; concatenation equals terminal text;
one `ActionCompleted(ok)`; audio played without duplicate/missing/reorder.

**USER audible-quality inspection (`user_result` required)**. USER answers exactly three questions:

1. Is the speech understandable?
2. Is any content duplicated or missing?
3. Does any artificial boundary disrupt understanding?

Pass requires: **yes / no / no**. Model text and audio remain private; public record contains
only USER verdicts, counts, digests and the bound tuple. `user_result` binds the exact
`pv_run_id`, `sub_run_id`, `base_sha` and `tracked_content_sha256`.

**Interrupt variants** (`QUEUED`, `SYNTHESIZING`, `PLAYING`) — fresh setup each:

| Variant | Short press at | Required assertions |
| :--- | :--- | :--- |
| `QUEUED` | Fragment in queue, not yet synthesizing | Queue cleared; no synthesis; no `ActionCompleted(ok)`; no later fragment or normal-success leak; cleanup → IDLE |
| `SYNTHESIZING` | During `synthesize` call | Synthesis aborted; no `ActionCompleted(ok)`; no cross-session leak; cleanup → IDLE |
| `PLAYING` | During audio playback | Playback stopped; no further synthesis; no `ActionCompleted(ok)`; cleanup → IDLE |

All variants: no duplicate, missing, reorder or late output; no normal success; no owner leak.

### 5.13 PV aggregation and finalization

After all 17 designated sub-run results exist:

```text
python3.13 scripts/run-m4c-pv.py finalize \
  --pv-run-id <PV_RUN_ID> \
  --public-root <PUBLIC_ROOT> \
  --private-root <PRIVATE_ROOT> \
  --binding-manifest <BINDING_JSON>
```

`pv_status=Pass` only when:
- All 17 catalog entries each have exactly one automatically designated, non-superseded
  result with script status Pass.
- `user_result=Pass` for `S02/NORMAL_END` and `S09/QUALITY_T02`.
- All designated results share the identical protected tuple (`base_sha`,
  `tracked_content_sha256`, pending-path set, harness/config/artifact digests, target facts).

**Attempts vs. designated results.** Each sub-run command creates one attempt. The finalizer
selects exactly one *designated* (non-superseded) result per catalog entry from all attempts
present under that `pv_run_id`. Retrying a failed sub-run atomically marks the previous
same-tuple attempt for that catalog entry as *superseded*; the new attempt becomes the
designated result for that entry. Superseded attempts remain as evidence but are not counted
among the 17 designated results and cannot satisfy any catalog entry.

The finalizer rejects: a missing designated result for any catalog entry; duplicate active
designations for the same catalog entry; an extra attempt whose catalog entry is not in the
17-variant catalog; a tuple mismatch between any attempt and the protected tuple; or a
supersession chain that is ambiguous or cyclic. A superseded attempt with a different
protected tuple is Blocked and cannot be reactivated.

---

## 6. Requirement traceability

| M4C design section | Portable Test IDs | Pi sub-run variants |
| :--- | :--- | :--- |
| Static output volume boundary | `M4C-VOL-001` | `S02/NORMAL_END` (audible quality), `S09/LIVE_ELIGIBLE_L02`, `S09/QUALITY_T02` |
| B2 streaming-speak controller | `M4C-SS-CTRL-001` | `S09/LIVE_ELIGIBLE_L02`, `S09/QUALITY_T02`, `S09/QUEUED`, `S09/SYNTHESIZING`, `S09/PLAYING` |
| Fragment extraction / punctuation-or-12 | `M4C-SS-EXTRACT-001` | `S09/LIVE_ELIGIBLE_L02` |
| Streaming-speak outcome / error taxonomy | `M4C-SS-OUTCOME-001` | `S04/ACTION`, `S06/ACTION_TTS_CHILD_EXIT` |
| Session no-input streak | `M4C-NOINPUT-001` | `S03/TWO_TIMEOUTS` |
| Startup / IDLE | — | `S01/START_IDLE` |
| Normal two-turn session and close | — | `S02/NORMAL_END` |
| Interrupt (PERCEPTION / THINK / ACTION) | `M4C-SS-CTRL-001` C14–C16 | `S04/PERCEPTION`, `S04/THINK`, `S04/ACTION` |
| Application exit | — | `S05/APP_EXIT` |
| Recoverable fault (whole-product) | — | `S06/PERCEPTION_ASR_INFERENCE`, `S06/THINK_LLM_CHILD_EXIT`, `S06/ACTION_TTS_CHILD_EXIT` |
| Display degradation | — | `S07/DISPLAY_DEGRADE` |
| Recovery fatal / exit 4 | — | `S08/LLM_READY_MISMATCH_FATAL` |
| Streaming speak eligible live proof | — | `S09/LIVE_ELIGIBLE_L02` |
| Streaming speak B2 quality | — | `S09/QUALITY_T02` |
| Streaming speak interrupt | `M4C-SS-CTRL-001` C14–C16 | `S09/QUEUED`, `S09/SYNTHESIZING`, `S09/PLAYING` |
| Regression continuity | `M4C-REG-001` | all Pi sub-runs |
| Product-quality timeline | — | `S02/NORMAL_END`, `S09/LIVE_ELIGIBLE_L02` |
