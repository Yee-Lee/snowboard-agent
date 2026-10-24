# M4-ERR — Production Error Handling Test Specification

## 1. Authority, scope and disposition

**Design authority**: [`ch_m4_error_handling.md`](../implement/ch_m4_error_handling.md)

**Status**: Test Spec focused revision in progress (IR_dev_M4_ERR_I) — §7 prospective oracle
revision pending final alignment; affected regression (M4-ERR-PI-011, M4-ERR-PI-012), Pi Verify
and commit remain closed until this revision is accepted. Unaffected M4-ERR Developer work may
continue. M4C Test Spec and Developer entry require M4-ERR Accepted.

**Prospective oracle baseline** (IR_dev_M4_ERR_I, revised 2026-09-20): Accepted M4A/M4B artifacts,
original test definitions and verification results remain immutable historical evidence at their
recorded SHA. For candidates containing M4-ERR, this spec prospectively supersedes exactly three
retained expectations embodied in four named functions (see §7). Every other M4A/M4B identity,
lifecycle, cleanup, cancellation, privacy and anti-weakening assertion is preserved unchanged. Two
new Test IDs (`M4-ERR-PI-011`, `M4-ERR-PI-012`) define the prospective oracle and are bound by
candidate tracked-content digest and same-bytes Pi Verify evidence; they do not modify, relabel or
supersede historical SHA records.

In scope: taxonomy audit、`ComponentSystemFault` constructor invariants、`ErrorOccurred` schema、four backend
dispositions、worker/converger sequence、ASR/LLM/TTS/Audio/Button/GPIO/Display component fault matrices、
diagnostics、startup/shutdown/fatal exit codes、privacy redactor sentinel tests、Pi hardware fault injection、
same-bytes content digest verification。

Out of scope: M4C scenario composition、streaming speak selection、barge-in、repeated session/soak、formal
latency/memory/thermal thresholds、remote telemetry、end-user configurable error messages。

---

## 2. Result vocabulary and execution matrix

### 2.1 Result vocabulary

- **Pass**: every required assertion passes, required evidence is present, and
  content/config/artifact digest agrees.
- **Fail**: an assertion fails, a forbidden call/artifact occurs, a test is skipped/xfail/xpass,
  or required evidence is missing or digest mismatches.
- **Incomplete**: a required measurement, evidence field, or explicit null reason is missing. Incomplete never
  converts to Pass.
- **Blocked**: the bound tracked content, target artifact, or required hardware/process is unavailable before
  execution begins.

### 2.2 Execution matrix

| Layer | ID | Environment | Timeout |
| :--- | :--- | :--- | :--- |
| Portable unit | `PU` | Repo-supported Python range; Developer's actual executable environment; no native/network | 60 s per Test ID |
| Portable integration | `PI` | Repo-supported Python range; Developer's actual executable environment; deterministic fakes for child adapters | 90 s per Test ID |
| Portable subprocess | `PS` | Repo-supported Python range on Linux; fake child in real POSIX process group | 120 s per Test ID |
| Pi product verify | `PV` | Raspberry Pi 5 4 GB, Debian 13 aarch64, CPython 3.13; actual ALSA, GPIO, ASR child, LLM child, TTS child; same tracked bytes as pending commit | 30 min per Test ID |

All PV commands bind the same tracked-content digest as the pending commit. Any modification returns to
Developer; affected tests re-run. M4-ERR Developer entry is open after Test Spec completion; M4C Test Spec
and Developer entry remain closed until M4-ERR Accepted; individual test-row Pass does not constitute
milestone acceptance.

---

## 3. Test IDs

### Group A — Taxonomy and publisher closed-set audit (WP1)

---

#### M4-ERR-PU-001 — `ComponentSystemFault` constructor invariants

| Field | Value |
| :--- | :--- |
| Layer | `PU` |
| WP | `M4-ERR-WP1` |
| Design ref | `ch_m4_error_handling.md` §3.1 |
| Timeout | 60 s |

**Steps**

1. Import `ComponentSystemFault` and `BackendDisposition` from `src/sbd/core/faults.py`.
2. Construct valid instances for each of the four `BackendDisposition` values and assert `to_event()` returns
   a valid `ErrorOccurred` with matching `code`, `backend_disposition`, and `recovery_keys`.
3. Assert that `REBUILD_REQUIRED` with no recovery key raises `ValueError` (fail-closed).
4. Assert that `UNPROVEN` with at least one owner candidate key constructs correctly. Assert that
   `UNPROVEN` with zero candidate keys raises `ValueError`; a fault with no owned backend must use
   `NOT_APPLICABLE` instead.
5. Assert that `REUSABLE` or `NOT_APPLICABLE` with a non-empty `recovery_keys` raises `ValueError`.
6. Assert that `where` not matching the Ch 11 namespace pattern raises `ValueError`.
7. Assert that `code` not matching `^[A-Z][A-Z0-9_]{2,63}$` raises `ValueError`.
8. Assert that `safe_summary` containing a newline, `repr(exc)` marker, or any value not declared as a code
   constant raises `ValueError`.
9. Assert that recovery keys are deduplicated and sorted in the produced `ErrorOccurred`.
10. Assert that `raise fault from cause` preserves `__cause__`; `cause` must not appear in `fault.to_event()`.

**Acceptance criteria**

- All ten assertions pass with no skip/xfail.
- `to_event()` output contains `code`, `backend_disposition`, `recovery_keys`; original cause absent.
- Recovery key dedup+sort verified with at least one multi-key case.
- `UNPROVEN` with zero candidate keys → `ValueError`; `NOT_APPLICABLE` accepted without keys.

---

#### M4-ERR-PU-002 — `ErrorOccurred` extended schema and legacy-neutral default

| Field | Value |
| :--- | :--- |
| Layer | `PU` |
| WP | `M4-ERR-WP1` |
| Design ref | `ch_m4_error_handling.md` §3.1 |
| Timeout | 60 s |

**Steps**

1. Construct `ErrorOccurred` with keyword arguments providing `code`, `backend_disposition`, `recovery_keys`.
2. Assert all three new fields are present and typed correctly.
3. Construct `ErrorOccurred` using the legacy-neutral test-helper default; assert `backend_disposition` is not
   `UNCLASSIFIED` when called from a production code path (verified via import-time sentinel).
4. Assert that production publishers (grep `src/` for `ErrorOccurred(`) use keyword construction; fail if any
   positional-only call without explicit `backend_disposition` exists in production code.

**Acceptance criteria**

- Schema fields present and typed.
- Zero production `ErrorOccurred` publishers with `UNCLASSIFIED` disposition.
- Test helper with legacy-neutral default does not raise; production sentinel check passes.

---

#### M4-ERR-PU-003 — Taxonomy class mutual exclusivity

| Field | Value |
| :--- | :--- |
| Layer | `PU` |
| WP | `M4-ERR-WP1` |
| Design ref | `ch_m4_error_handling.md` §2 |
| Timeout | 60 s |

**Steps**

1. For each taxonomy class (request outcome, system fault, optional degradation, cancellation, fatal):
   - Inject a representative synthetic event sequence into a test-double State Manager.
   - Assert that exactly one product path fires (either a `PerceptionResult`/`LLMResponse`/`ActionCompleted`
     Fact, or one `ErrorOccurred`, or a degradation diagnostic, or no event, or fatal exit) — never two paths
     simultaneously.
2. Assert that a `timeout` translated to request outcome only when a terminal/cleanup/reusable proof fixture
   is injected; without proof it must produce a system fault code.
3. Assert that `AdapterError`, `RuntimeError`, or unknown native string alone does not produce a valid
   classification; must be wrapped as `*_UNEXPECTED` + `UNPROVEN`.

**Acceptance criteria**

- No test-double SM receives both a terminal Fact and an `ErrorOccurred` for the same operation.
- Timeout-as-outcome path blocked without proof fixture.
- Unknown exception wraps to `*_UNEXPECTED` + `UNPROVEN`.

---

#### M4-ERR-PU-004 — Production publisher closed-set audit

| Field | Value |
| :--- | :--- |
| Layer | `PU` |
| WP | `M4-ERR-WP1` |
| Design ref | `ch_m4_error_handling.md` §3.1 |
| Timeout | 60 s |

**Steps**

1. Static analysis: scan `src/` for all `ErrorOccurred` publish sites.
2. Assert every site provides an explicit `BackendDisposition` that is not `UNCLASSIFIED`.
3. Assert no site uses broad catch patterns (`except Exception`, `except BaseException`) that suppress the
   original fault without wrapping as `ComponentSystemFault`.
4. Assert no site directly publishes `ErrorOccurred` in a cancellation path (cancelled tasks re-raise
   `CancelledError`; they do not publish a fault event).

**Acceptance criteria**

- Zero `UNCLASSIFIED` publishers.
- Zero unguarded broad-catch suppressors.
- Zero `ErrorOccurred` publications on cancel path.

---

### Group B — Fact/ErrorOccurred mutual exclusivity, cause chain, sanitized projection (WP1/WP2)

---

#### M4-ERR-PU-005 — Fact and ErrorOccurred mutual exclusivity

| Field | Value |
| :--- | :--- |
| Layer | `PU` |
| WP | `M4-ERR-WP1` |
| Design ref | `ch_m4_error_handling.md` §2, §3.2 |
| Timeout | 60 s |

**Steps**

1. In a unit test double, inject a system fault into each worker type (ASR, LLM, TTS, Audio, Button, GPIO).
2. Assert that the worker publishes exactly one `ErrorOccurred` and zero terminal Facts for that operation.
3. Inject a successful request outcome and assert exactly one terminal Fact and zero `ErrorOccurred` events.
4. Assert that `ActionCompleted(error)` is never emitted for a system fault — only for proven-reusable action
   outcomes.

**Acceptance criteria**

- All six worker types: zero dual-publish cases.
- `ActionCompleted(error)` not observed on any system fault path.

---

#### M4-ERR-PU-006 — Cause chain preservation

| Field | Value |
| :--- | :--- |
| Layer | `PU` |
| WP | `M4-ERR-WP1` |
| Design ref | `ch_m4_error_handling.md` §3.1 |
| Timeout | 60 s |

**Steps**

1. Raise a `ComponentSystemFault` using `raise fault from original_cause`.
2. Assert `fault.__cause__` is `original_cause`.
3. Assert `fault.to_event()` does not contain any string representation of `original_cause`.
4. Assert `fault.safe_summary` does not contain `repr(original_cause)` or any dynamic content.

**Acceptance criteria**

- `__cause__` preserved in exception chain.
- Event and summary contain no cause text.

---

#### M4-ERR-PU-007 — Sanitized Display projection

| Field | Value |
| :--- | :--- |
| Layer | `PU` |
| WP | `M4-ERR-WP1` |
| Design ref | `ch_m4_error_handling.md` §4.5, §5 |
| Timeout | 60 s |

**Steps**

1. Call the `code-to-safe-category` pure function with each of the six allowed projection categories
   (`audio`, `asr`, `llm`, `tts`, `input`, `internal`) and assert correct mapping.
2. Call with an unknown code and assert it maps to `internal`.
3. Assert the projection function accepts no mutable state and produces identical output for identical input.
4. Assert the same function is used for both Display projection and log sanitization (shared reference check).

**Acceptance criteria**

- All six categories map correctly.
- Unknown code → `internal`.
- Function is a pure function (no side-effects fixture verifies idempotency).
- Display and log share the same function object.

---

### Group C — Four backend dispositions and completed-task forced Level 2 (WP2)

---

#### M4-ERR-PI-001 — Four backend disposition convergence paths

| Field | Value |
| :--- | :--- |
| Layer | `PI` |
| WP | `M4-ERR-WP2` |
| Design ref | `ch_m4_error_handling.md` §3.2, §3.3 |
| Timeout | 90 s |

**Steps**

1. For `REUSABLE`: inject a fault whose owner fake returns READY with all cleanup proofs. Assert that after
   ERROR convergence, RM rebuild is NOT called and backend is accepted for next admission.
2. For `REBUILD_REQUIRED`: inject a fault with a stable RM key. Assert Level 2 is triggered even when the
   outer task is already `done()`. Assert `begin_recovery()` is called exactly once with that key.
3. For `UNPROVEN`: inject a fault where terminal/cleanup/owner-state proof is absent. Assert Level 2 is forced.
   Assert that if Level 2 cannot produce a complete proof for the key, Level 3 (fatal) is triggered.
4. For `NOT_APPLICABLE`: inject a fault that owns no rebuildable backend. Assert no RM recovery call occurs.
   If a required resource is no longer available, assert publisher is expected to switch to fatal (tested via
   fatal-path fixture).

**Acceptance criteria**

- `REUSABLE`: RM rebuild = 0, backend reused.
- `REBUILD_REQUIRED`: Level 2 forced for completed task; `begin_recovery()` called exactly once with correct key.
- `UNPROVEN` without proof: Level 3 triggered.
- `NOT_APPLICABLE`: RM rebuild = 0.

---

#### M4-ERR-PI-002 — Completed-task fault Level 2 forced path

| Field | Value |
| :--- | :--- |
| Layer | `PI` |
| WP | `M4-ERR-WP2` |
| Design ref | `ch_m4_error_handling.md` §3.3 step 4 |
| Timeout | 90 s |

**Steps**

1. Simulate a worker task that completes (`.done()` returns `True`) but whose fault disposition is
   `REBUILD_REQUIRED`.
2. Assert Ch 6 convergence still harvests the exception and initiates Level 2 for that fault.
3. Assert `force_abort()` targets only the declared fault owner; no other idle workers are affected.

**Acceptance criteria**

- Completed-task `REBUILD_REQUIRED` triggers Level 2.
- Only the fault owner worker receives `force_abort()`.

---

### Group D — Recovery key audit (WP2)

---

#### M4-ERR-PI-003 — Recovery key dedup, wrong key, missing key

| Field | Value |
| :--- | :--- |
| Layer | `PI` |
| WP | `M4-ERR-WP2` |
| Design ref | `ch_m4_error_handling.md` §3.3 steps 6–7 |
| Timeout | 90 s |

**Steps**

1. Inject a `REBUILD_REQUIRED` fault with duplicate recovery keys; assert `ErrorOccurred.recovery_keys`
   contains the deduplicated sorted set.
2. Level 2 reports a key that is NOT in the fault's declared keys; assert `ConvergenceFatalError` is raised.
3. Level 2 omits a key that IS declared; assert `ConvergenceFatalError` is raised.
4. Level 2 reports an extra key belonging to a different owner; assert `ConvergenceFatalError` is raised.
5. Level 2 provides correct keys with complete termination/waitpid/fd/device-release proof; assert
   `begin_recovery()` is called and no fatal error occurs.

**Acceptance criteria**

- Dedup+sort verified in event.
- Wrong key, missing key, extra-owner key → `ConvergenceFatalError`.
- Correct proof → `begin_recovery()` called once.

---

#### M4-ERR-PI-004 — RM rebuild success and recovery failure exit 4

| Field | Value |
| :--- | :--- |
| Layer | `PI` |
| WP | `M4-ERR-WP2` |
| Design ref | `ch_m4_error_handling.md` §3.3 step 7, §5 |
| Timeout | 90 s |

**Steps**

1. Inject a valid `REBUILD_REQUIRED` fault; simulate RM `begin_recovery()` succeeding; assert system returns
   to IDLE without exit.
2. Inject a valid `REBUILD_REQUIRED` fault; simulate RM `begin_recovery()` failing; assert exit code 4 and
   first-root traceback contains only one cause entry.
3. Assert that on recovery failure, no second `ErrorOccurred` or second ERROR recovery cycle is initiated.

**Acceptance criteria**

- Successful recovery: IDLE reached, no exit.
- Failed recovery: exit 4, single-root traceback.
- No second ERROR recovery on fatal path.

---

### Group E — Component fault matrices (WP3–WP6)

---

#### M4-ERR-PI-005 — ASR fault matrix

| Field | Value |
| :--- | :--- |
| Layer | `PI` |
| WP | `M4-ERR-WP3` |
| Design ref | `ch_m4_error_handling.md` §4.2 |
| Timeout | 90 s |

**Steps**

For each row in the table below, inject the described condition into the ASR adapter fake and assert the
exact expected outcome:

| Case | Injected condition | Expected code | Expected disposition | Expected product path |
| :--- | :--- | :--- | :--- | :--- |
| ASR-1 | finite input empty | — (request outcome) | — | `PerceptionResult` with `timeout`/`error`; child READY |
| ASR-2 | `NO_SPEECH` | — (request outcome) | — | `PerceptionResult`; child READY |
| ASR-3 | `MULTIPLE_UTTERANCES` | — (request outcome) | — | `PerceptionResult`; child READY |
| ASR-4 | caller frame contract violation | `ASR_FRAME_CONTRACT_VIOLATION` | `UNPROVEN` | `ErrorOccurred`; no "re-speak" hint |
| ASR-5 | child `INVALID_FRAME` | `ASR_FRAME_CONTRACT_VIOLATION` | `UNPROVEN` | `ErrorOccurred` |
| ASR-6 | native `INFERENCE_REJECTED` | `ASR_INFERENCE_FAILED` | `REBUILD_REQUIRED` + ASR key | `ErrorOccurred`; Level 2 |
| ASR-7 | protocol mismatch / EOF | `ASR_PROTOCOL_FAILED` | `REBUILD_REQUIRED` + ASR key | `ErrorOccurred`; Level 2 |
| ASR-8 | child crash | `ASR_PROTOCOL_FAILED` | `REBUILD_REQUIRED` + ASR key | `ErrorOccurred`; Level 2 |
| ASR-9 | ALSA capture failure | `AUDIO_CAPTURE_FAILED` | `UNPROVEN` | `ErrorOccurred`; Level 3 if no hook |
| ASR-10 | operation timeout, READY proof complete | — (request outcome) | — | timeout Fact |
| ASR-11 | operation timeout, proof incomplete | `ASR_TIMEOUT_UNPROVEN` | `UNPROVEN` | `ErrorOccurred`; Level 2 or 3 |

Additional assertion: ASR supervisor must distinguish at least: native inference failure, supervisor
invariant, cancel, and process termination. Unknown code from child → protocol fault, not `INFERENCE_REJECTED`.

**Acceptance criteria**

- All eleven cases produce exact expected code and disposition.
- No broad-catch compression of all `BaseException` to `INFERENCE_REJECTED`.
- Cancel path does not emit `ErrorOccurred`.

---

#### M4-ERR-PI-006 — LLM fault matrix

| Field | Value |
| :--- | :--- |
| Layer | `PI` |
| WP | `M4-ERR-WP4` |
| Design ref | `ch_m4_error_handling.md` §4.3 |
| Timeout | 90 s |

**Steps**

For each row, inject into LLM adapter/Reasoner fake and assert exact outcome:

| Case | Injected condition | Expected code / path | Proof requirement |
| :--- | :--- | :--- | :--- |
| LLM-1 | capacity / input limit | R1/R2 normal Fact | terminal + Conversation cleanup + `engine_usable=True` |
| LLM-2 | `ReplaceableGenerationFailure`, proof complete | R2 Fact; no `ErrorOccurred` | typed code + proof retained |
| LLM-3 | invalid ticket / profile / revision | `LLM_PROTOCOL_FAILED` + `UNPROVEN` + LLM key | `ErrorOccurred` |
| LLM-4 | child crash / backend unusable | `LLM_BACKEND_FAILED` + `REBUILD_REQUIRED` + LLM key | Level 2 |
| LLM-5 | request/close/discard proof missing | `LLM_CLEANUP_UNPROVEN` + `UNPROVEN` + LLM key | Level 2 or 3 |
| LLM-6 | observer/sampler failure affects admission | `LLM_OBSERVATION_FAILED` + `UNPROVEN` + LLM key | Level 2 or 3 |
| LLM-7 | SM receives illegal `LLMResponse` | `ReasonerContractViolation`; ERROR; no fatal | no fake `ErrorOccurred` |

Additional assertions:
- R1/R2 proof does not degrade under broad catch: injecting a broad-catch wrapper must not suppress `cause`.
- `LLM_PROTOCOL_FAILED` must preserve `__cause__` in exception chain.
- System-fault recovery must not be disguised as planned recycle; inject a planned-recycle fake and assert
  SM authorization is required.

**Acceptance criteria**

- All seven cases produce exact code/disposition.
- R1/R2 proof non-degradation verified with broad-catch injection.
- Unauthorized recovery-as-planned-recycle is rejected.

---

#### M4-ERR-PI-007 — TTS and Audio output fault matrix

| Field | Value |
| :--- | :--- |
| Layer | `PI` |
| WP | `M4-ERR-WP5` |
| Design ref | `ch_m4_error_handling.md` §4.4 |
| Timeout | 90 s |

**Steps**

| Case | Injected condition | Expected code | Expected disposition | Notes |
| :--- | :--- | :--- | :--- | :--- |
| TTS-1 | TTS native generation failure | `TTS_GENERATION_FAILED` | `REBUILD_REQUIRED` + TTS key | Level 2 |
| TTS-2 | TTS protocol / PCM identity failure | `TTS_PROTOCOL_FAILED` | `REBUILD_REQUIRED` + TTS key | Level 2 |
| TTS-3 | TTS child crash | `TTS_PROTOCOL_FAILED` | `REBUILD_REQUIRED` + TTS key | Level 2 |
| TTS-4 | audio output write / drain failure | `AUDIO_PLAYBACK_FAILED` | `UNPROVEN` | Level 3 if non-recoverable |
| TTS-5 | cancellation during speak | no `ActionCompleted`; no `ErrorOccurred` | — | cleanup proof verified |
| TTS-6 | valid-text input, TTS failure | `TTS_GENERATION_FAILED`; no retry hint | — | no `ActionCompleted(error)` |

Additional assertion: `ActionCompleted(ok)` only emitted after TTS iterator completes AND AudioOutput drain
succeeds. Any system fault must not be downgraded to `ActionCompleted(error)`.

**Acceptance criteria**

- All six cases produce exact code/disposition.
- `ActionCompleted(error)` absent on all system fault paths.
- Cancellation path: no Fact, no `ErrorOccurred`, only cleanup proof.

---

#### M4-ERR-PI-008 — Button and GPIO fault matrix

| Field | Value |
| :--- | :--- |
| Layer | `PI` |
| WP | `M4-ERR-WP6` |
| Design ref | `ch_m4_error_handling.md` §4.1 |
| Timeout | 90 s |

**Steps**

| Case | Injected condition | Expected code | Expected disposition | Notes |
| :--- | :--- | :--- | :--- | :--- |
| BTN-1 | legal short/long press | existing signal | — | not error |
| BTN-2 | bounce / stale event | DEBUG log + drop | — | no `ErrorOccurred` |
| BTN-3 | button callback exception, GPIO still registered | `BUTTON_CALLBACK_FAILED` | `REUSABLE` | one `ErrorOccurred`; active session → ERROR |
| BTN-4 | GPIO edge read / registration ownership corruption | `GPIO_EVENT_READ_FAILED` | `UNPROVEN` | Level 3 if no recovery hook |
| BTN-5 | startup chip/line acquisition failure | `StartupError` rollback | — | exit 3 |

Additional assertions:
- GPIO driver does not swallow callback exception in detached task logger only; callback task failure
  must be observable via Event Bus or fatal path.
- Error diagnostic does not contain pin consumer or host path beyond known namespace.

**Acceptance criteria**

- All five cases produce exact code/disposition.
- Callback exception observable via Event Bus/fatal; not only `logger.exception()` in detached task.
- Diagnostic namespace check passes.

---

#### M4-ERR-PI-009 — Display optional degradation

| Field | Value |
| :--- | :--- |
| Layer | `PI` |
| WP | `M4-ERR-WP6` |
| Design ref | `ch_m4_error_handling.md` §4.5 |
| Timeout | 90 s |

**Steps**

1. Inject a Display native write/show runtime failure.
2. Assert exactly one `DISPLAY_RENDER_DISABLED` ERROR diagnostic is emitted.
3. Assert rendering is atomically disabled; subsequent write intents become no-ops.
4. Assert the Display does NOT attempt to show its own error on the already-failed surface.
5. Assert the static capability map is not updated (Display reports its own disabled state only via the
   single diagnostic).
6. Assert that voice error convergence is not blocked when Display is disabled.
7. Assert Display caller hint validation failures produce only a `DisplayHintError` WARNING/drop, not an
   `ErrorOccurred`.

**Acceptance criteria**

- Exactly one `DISPLAY_RENDER_DISABLED` diagnostic on first runtime failure.
- No subsequent Display writes succeed.
- Voice convergence completes independently of Display state.
- Caller hint failure → WARNING/drop only.

---

### Group F — Exit codes and startup/shutdown (WP6)

---

#### M4-ERR-PU-008 — Exit code matrix

| Field | Value |
| :--- | :--- |
| Layer | `PU` |
| WP | `M4-ERR-WP6` |
| Design ref | `ch_m4_error_handling.md` §5 |
| Timeout | 60 s |

**Steps**

1. Inject an invalid config; assert process exits with code 2.
2. Inject a resource startup failure; assert reverse rollback is completed, root cause is preserved in log,
   and process exits with code 3.
3. Inject a recovery failure / Level 2 proof failure / Bus invariant; assert exit code 4 with first-root
   single traceback in log.
4. Inject a normal shutdown sequence; assert all stop failures are logged per Ch 11 and continued, and
   process exits with code 0.
5. Inject a termination proof failure during shutdown; assert process does NOT exit 0 (runtime fatal path).
6. Assert that on exit 4 path, no second `ErrorOccurred` is published and no second ERROR recovery cycle
   is initiated.

**Acceptance criteria**

- Exact exit codes: config invalid=2, startup=3, fatal=4, normal=0.
- Single-root traceback on exit 4.
- Termination-proof failure during shutdown → non-zero exit.
- No double ERROR recovery on fatal path.

---

#### M4-ERR-PS-001 — Startup rollback sequence in subprocess

| Field | Value |
| :--- | :--- |
| Layer | `PS` |
| WP | `M4-ERR-WP6` |
| Design ref | `ch_m4_error_handling.md` §5 |
| Timeout | 120 s |

**Steps**

1. In a real POSIX process group, start a product-equivalent subprocess with a fake that fails resource
   acquisition after partial startup (e.g., after Button/GPIO but before ASR child).
2. Assert reverse rollback occurs (resources acquired after failure point are released in reverse order).
3. Assert process exits with code 3.
4. Assert root cause appears in log exactly once.
5. Assert no `ErrorOccurred` event is published during startup fatal path.

**Acceptance criteria**

- Reverse rollback order verified via log sequence.
- exit 3.
- Root cause in log exactly once.
- No `ErrorOccurred` during startup fatal.

---

### Group G — Privacy sentinel (WP1/WP7)

---

#### M4-ERR-PU-009 — Privacy redactor sentinel

| Field | Value |
| :--- | :--- |
| Layer | `PU` |
| WP | `M4-ERR-WP1`, `M4-ERR-WP7` |
| Design ref | `ch_m4_error_handling.md` §5 |
| Timeout | 60 s |

**Steps**

Inject each sentinel into the privacy redactor test fixture and assert it does NOT appear in any of:
Event payload, structured log fields, Display projection output.

| Sentinel | Description |
| :--- | :--- |
| `TRANSCRIPT_SENTINEL` | fake transcript fragment |
| `PROMPT_SENTINEL` | fake prompt string |
| `PCM_SENTINEL` | fake PCM bytes repr |
| `PAYLOAD_SENTINEL` | fake request/response payload |
| `FILESYSTEM_SENTINEL` | fake filesystem locator path |
| `NEWLINE_SENTINEL` | literal `\n` embedded in summary |

1. For each sentinel, construct a `ComponentSystemFault` whose `safe_summary` or `__cause__` contains the
   sentinel.
2. Assert `to_event()` output does not contain the sentinel.
3. Feed the `ErrorOccurred` through the log formatter; assert structured log output does not contain
   the sentinel.
4. Feed the fault code through the Display projection function; assert Display output does not contain
   the sentinel.

**Acceptance criteria**

- Zero sentinel appearances in Event, log, or Display output for all six sentinels.
- `safe_summary` containing a raw sentinel is rejected at construction time (`ValueError`).

---

### Group H — Pi hardware fault injection (WP7)

---

#### M4-ERR-PV-001 — ALSA capture fault injection on Pi

| Field | Value |
| :--- | :--- |
| Layer | `PV` |
| WP | `M4-ERR-WP7` |
| Design ref | `ch_m4_error_handling.md` §4.2, §5 |
| Timeout | 30 min |
| Platform | Raspberry Pi 5 4 GB, actual ALSA backend |

**Steps**

1. With product running from same tracked bytes as pending commit, activate the product's deterministic
   ALSA capture test seam to inject a capture failure during an active Listen session. The seam must target
   the actual ALSA backend identity; it must not require kernel fault injection or physical device removal
   as a prerequisite.
2. Assert `AUDIO_CAPTURE_FAILED` + `UNPROVEN` fault is emitted.
3. Assert Level 3 fatal is reached and process exits 4 (no `core.audio.input` recovery hook on Pi).
4. Assert raw ALSA device error does not appear in product log's structured fields or Event payload;
   only the sanitized `AUDIO_CAPTURE_FAILED` code is logged.
5. Verify tracked-content digest matches pending commit digest.
6. Verify actual ALSA backend identity against the expected value declared in the test seam.

**Acceptance criteria**

- `AUDIO_CAPTURE_FAILED` + `UNPROVEN` → exit 4.
- No raw ALSA error string in product Event/log.
- Content digest matches.
- Actual backend identity verified against declared value.

---

#### M4-ERR-PV-002 — GPIO fault injection on Pi

| Field | Value |
| :--- | :--- |
| Layer | `PV` |
| WP | `M4-ERR-WP7` |
| Design ref | `ch_m4_error_handling.md` §4.1 |
| Timeout | 30 min |
| Platform | Raspberry Pi 5 4 GB, actual GPIO backend |

**Steps**

1. With product running from same tracked bytes, activate the product's deterministic GPIO callback
   test seam to inject a callback exception during an active session. The seam must target the actual
   GPIO backend identity; it must not require physical GPIO line release as a prerequisite.
2. Assert `BUTTON_CALLBACK_FAILED` + `REUSABLE` is published exactly once via Event Bus.
3. Assert the active session enters ERROR state.
4. Assert the exception is NOT only swallowed by a detached `logger.exception()` call.
5. Activate the GPIO edge-read failure test seam.
6. Assert `GPIO_EVENT_READ_FAILED` + `UNPROVEN`; if no recovery hook, assert Level 3 / exit 4.
7. Verify actual GPIO backend identity against the expected value declared in each test seam.
8. Verify tracked-content digest.

**Acceptance criteria**

- `BUTTON_CALLBACK_FAILED` observable on Event Bus.
- `GPIO_EVENT_READ_FAILED` without recovery hook → exit 4.
- Actual GPIO backend identity verified.
- Content digest matches.

---

#### M4-ERR-PV-003 — ASR child fault injection on Pi

| Field | Value |
| :--- | :--- |
| Layer | `PV` |
| WP | `M4-ERR-WP7` |
| Design ref | `ch_m4_error_handling.md` §4.2 |
| Timeout | 30 min |
| Platform | Raspberry Pi 5 4 GB, actual ASR child process |

**Steps**

1. Inject native `INFERENCE_REJECTED` from the real ASR child.
2. Assert `ASR_INFERENCE_FAILED` + `REBUILD_REQUIRED` + ASR key; Level 2; RM begins rebuild.
3. After successful rebuild, assert system returns to READY for the next Listen operation (same-baseline
   READY proof: new successful ASR interaction completes).
4. Kill the ASR child process abruptly.
5. Assert `ASR_PROTOCOL_FAILED` + `REBUILD_REQUIRED` + ASR key; Level 2; RM rebuilds.
6. After rebuild, assert same-baseline READY proof.
7. Verify tracked-content digest.

**Acceptance criteria**

- Both injection paths produce correct code/disposition.
- After each rebuild: same-baseline READY proof passes.
- Content digest matches.

---

#### M4-ERR-PV-004 — LLM child fault injection on Pi

| Field | Value |
| :--- | :--- |
| Layer | `PV` |
| WP | `M4-ERR-WP7` |
| Design ref | `ch_m4_error_handling.md` §4.3 |
| Timeout | 30 min |
| Platform | Raspberry Pi 5 4 GB, actual LLM child process |

**Steps**

1. Kill the LLM child process during an active LLM request.
2. Assert `LLM_BACKEND_FAILED` + `REBUILD_REQUIRED` + LLM key; Level 2.
3. After successful RM rebuild, assert same-baseline READY proof (next Reasoner request succeeds).
4. Inject a request/close/discard proof failure (simulate by intercepting cleanup acknowledgement).
5. Assert `LLM_CLEANUP_UNPROVEN` + `UNPROVEN`; Level 2; if proof still unavailable, assert Level 3.
6. Verify tracked-content digest.

**Acceptance criteria**

- `LLM_BACKEND_FAILED` path: rebuild + READY proof.
- `LLM_CLEANUP_UNPROVEN` path: Level 3 if no proof.
- Content digest matches.

---

#### M4-ERR-PV-005 — TTS child fault injection on Pi

| Field | Value |
| :--- | :--- |
| Layer | `PV` |
| WP | `M4-ERR-WP7` |
| Design ref | `ch_m4_error_handling.md` §4.4 |
| Timeout | 30 min |
| Platform | Raspberry Pi 5 4 GB, actual TTS child process |

**Steps**

1. Kill the TTS child process during an active speak operation.
2. Assert `TTS_PROTOCOL_FAILED` + `REBUILD_REQUIRED` + TTS key; Level 2.
3. After successful RM rebuild, assert same-baseline READY proof (next speak request succeeds).
4. Inject an audio output device drain failure (ALSA drain blocked).
5. Assert `AUDIO_PLAYBACK_FAILED` + `UNPROVEN`; if ALSA non-recoverable, assert Level 3 / exit 4.
6. Verify tracked-content digest.

**Acceptance criteria**

- TTS kill path: rebuild + READY proof.
- ALSA drain failure: Level 3 if non-recoverable.
- Content digest matches.

---

### Group I — Content digest and composition audit (WP7)

---

#### M4-ERR-PU-010 — Tracked-only content digest binding

| Field | Value |
| :--- | :--- |
| Layer | `PU` |
| WP | `M4-ERR-WP7` |
| Design ref | `ch_m4_error_handling.md` §7 item 9 |
| Timeout | 60 s |

**Steps**

1. Compute the tracked-only content digest of all files in `src/sbd/core/` and the relevant component paths.
2. Assert the digest is deterministic across two consecutive computations on the same working tree.
3. Assert the digest changes when any tracked file is modified.
4. Assert the digest does not change when an untracked file is added.
5. Assert production config and artifact identity fields are non-empty and stable across restarts with the
   same artifact.

**Acceptance criteria**

- Digest deterministic.
- Modified tracked file → digest changes.
- Untracked add → digest unchanged.
- Config/artifact identity stable.

---

#### M4-ERR-PI-010 — Composition audit — M4 production fault-mapping boundaries

| Field | Value |
| :--- | :--- |
| Layer | `PI` |
| WP | `M4-ERR-WP7` |
| Design ref | `ch_m4_error_handling.md` §1, §3.3 |
| Timeout | 90 s |

**Steps**

Audit only the M4 production fault-mapping boundaries in `src/sbd/` (i.e., the `except` clauses that
translate raw native/protocol/HAL exceptions into taxonomy outcomes). The following catch patterns are
explicitly exempt and must not be flagged:

- Cancellation path: re-raises `CancelledError` unchanged.
- Request outcome path: already-proven terminal catch (e.g., `NO_SPEECH`, capacity limit).
- Display optional degradation catch (single `DISPLAY_RENDER_DISABLED` path).
- Startup rollback catch (`StartupError` reverse-rollback chain).
- Bounded cleanup catch (explicit cleanup acknowledgement with proof).

For the remaining M4 fault-mapping catch sites, assert:

1. Every site wraps the exception as a typed `ComponentSystemFault` using `raise fault from cause`,
   preserving the original cause in `__cause__`.
2. Zero lossy mappings: no `except Exception:` or `except BaseException:` that raises a non-typed
   `RuntimeError` or `AdapterError` without a `ComponentSystemFault` wrapper.
3. Zero unguarded broad catches that suppress the exception with `pass` or `logger.exception()` only
   in a detached task (i.e., no observable fault path).

**Acceptance criteria**

- All M4 fault-mapping catch sites produce a typed `ComponentSystemFault` with preserved `__cause__`.
- Zero lossy mappings in fault-mapping boundaries.
- Zero unobservable exception suppressions at fault-mapping sites.
- All exempt catch patterns (cancellation, request outcome, Display degradation, startup rollback,
  bounded cleanup) are not flagged.

---

## 4. Test ID index

| Test ID | Layer | WP | Coverage |
| :--- | :--- | :--- | :--- |
| `M4-ERR-PU-001` | PU | WP1 | `ComponentSystemFault` constructor invariants |
| `M4-ERR-PU-002` | PU | WP1 | `ErrorOccurred` extended schema |
| `M4-ERR-PU-003` | PU | WP1 | Taxonomy mutual exclusivity |
| `M4-ERR-PU-004` | PU | WP1 | Production publisher closed-set audit |
| `M4-ERR-PU-005` | PU | WP1 | Fact/ErrorOccurred mutual exclusivity |
| `M4-ERR-PU-006` | PU | WP1 | Cause chain preservation |
| `M4-ERR-PU-007` | PU | WP1 | Sanitized Display projection |
| `M4-ERR-PU-008` | PU | WP6 | Exit code matrix |
| `M4-ERR-PU-009` | PU | WP1/WP7 | Privacy redactor sentinel |
| `M4-ERR-PU-010` | PU | WP7 | Tracked-only content digest |
| `M4-ERR-PI-001` | PI | WP2 | Four backend disposition convergence |
| `M4-ERR-PI-002` | PI | WP2 | Completed-task fault Level 2 forced |
| `M4-ERR-PI-003` | PI | WP2 | Recovery key dedup/wrong/missing |
| `M4-ERR-PI-004` | PI | WP2 | RM rebuild success and recovery failure exit 4 |
| `M4-ERR-PI-005` | PI | WP3 | ASR fault matrix (11 cases) |
| `M4-ERR-PI-006` | PI | WP4 | LLM fault matrix (7 cases) |
| `M4-ERR-PI-007` | PI | WP5 | TTS/Audio fault matrix (6 cases) |
| `M4-ERR-PI-008` | PI | WP6 | Button/GPIO fault matrix (5 cases) |
| `M4-ERR-PI-009` | PI | WP6 | Display optional degradation |
| `M4-ERR-PI-010` | PI | WP7 | Composition audit — M4 fault-mapping boundaries (exempt: cancel/outcome/degradation/startup/cleanup) |
| `M4-ERR-PI-011` | PI | WP5 | TTS typed fault, no-admission-before-recovery — prospective B1 oracle (§7) |
| `M4-ERR-PI-012` | PI | WP1/WP4/WP5 | Cause chain + typed completion-callback fault — prospective B2 oracle (§7) |
| `M4-ERR-PS-001` | PS | WP6 | Startup rollback in subprocess |
| `M4-ERR-PV-001` | PV | WP7 | Pi ALSA fault injection |
| `M4-ERR-PV-002` | PV | WP7 | Pi GPIO fault injection |
| `M4-ERR-PV-003` | PV | WP7 | Pi ASR child fault injection + READY proof |
| `M4-ERR-PV-004` | PV | WP7 | Pi LLM child fault injection + READY proof |
| `M4-ERR-PV-005` | PV | WP7 | Pi TTS child fault injection + READY proof |

---

## 5. WP coverage traceability

| WP | Design requirement | Test IDs |
| :--- | :--- | :--- |
| WP1 | Shared fault types, ErrorOccurred schema, safe projection, publisher migration | PU-001–007, PU-009, PI-012 |
| WP2 | WorkerRuntime, task exception harvest, Converger, SM/RM handoff | PI-001–004 |
| WP3 | ASR supervisor/adapter, Listen, Audio input | PI-005, PV-003 |
| WP4 | LLM adapter/Reasoner/Conversation | PI-006, PV-004, PI-012 |
| WP5 | TTS/Speak/Audio output | PI-007, PV-005, PI-011, PI-012 |
| WP6 | Button/GPIO, Display, logging, main supervision | PI-008–009, PS-001, PU-008 |
| WP7 | Composition audit, portable integration, Pi fault injection, same-bytes verify | PI-010, PU-010, PV-001–005 |

---

## 6. §7 handoff requirement traceability

| Design §7 item | Test IDs |
| :--- | :--- |
| 1. taxonomy and publisher closed-set audit | PU-003, PU-004 |
| 2. Fact/ErrorOccurred mutual exclusivity, cause chain, sanitized projection | PU-005, PU-006, PU-007 |
| 3. four backend dispositions, completed-task forced Level 2 | PI-001, PI-002 |
| 4. recovery key dedup, wrong/missing key, RM rebuild, recovery failure exit 4 | PI-003, PI-004 |
| 5. ASR 4-class, LLM R1/R2/E1, TTS/Audio, Button/GPIO, Display matrix | PI-005–009 |
| 6. config=2, startup=3, normal shutdown=0, runtime fatal=4, first-root single traceback | PU-008, PS-001 |
| 7. transcript/prompt/PCM/payload sentinel absence in Event/log/Display | PU-009 |
| 8. Pi ALSA, GPIO, ASR child, LLM child, TTS child fault injection; READY proof | PV-001–005 |
| 9. tracked-only content digest, production config/artifact identity | PU-010 |
| IR_dev_M4_ERR_I §1.1 — prospective supersession of same-child reuse (B1) | PI-011 |
| IR_dev_M4_ERR_I §1.1 — prospective supersession of `__cause__ is None` and untyped observer escape (B2) | PI-012 |

---

## 7. Prospective oracle revisions — IR_dev_M4_ERR_I affected assertions

This section is authoritative for M4-ERR candidates only. It does not alter historical M4A/M4B
SHA records, test definitions, or archived evidence.

**Scope**: Two Test IDs (`M4-ERR-PI-011`, `M4-ERR-PI-012`) together replace exactly three
retained expectations embodied in four named functions:

| Retained function | File | Expectation superseded |
| :--- | :--- | :--- |
| `test_m4a_tts_002_persistent_error_reopen_and_next_success` | `tests/test_m4a_tts_002.py` | same-child reuse after TTS fault (B1) |
| `test_m4a_tts_002_every_whitelisted_error_reopens_same_child` | `tests/test_m4a_tts_002.py` | same-child reuse after TTS fault (B1) |
| `test_product_fatal_boundary_has_no_normal_fact_and_sanitized_traceback` | `tests/test_m4b_p5_001.py` | `__cause__ is None` on mapped fault (B2) |
| `test_V01_completion_callback_failure_reaches_worker_supervision` | `tests/test_m4b_priv_001.py` | untyped `ObservationError` escapes supervision (B2) |

Every M4A/M4B assertion not listed above — including all other `test_m4a_tts_002` cases,
`test_m4b_p5_001` cases, `test_m4b_priv_001` cases, the 99-node Foundation baseline, all G01–G04
and G07–G10 protections, and all other lifecycle, cleanup, cancellation, privacy and
anti-weakening checks — is preserved without modification.

---

### M4-ERR-PI-011 — TTS system-fault typed disposition and no-admission-before-recovery (replaces B1)

| Field | Value |
| :--- | :--- |
| Layer | `PI` |
| WP | `M4-ERR-WP5` |
| Design ref | `ch_m4_error_handling.md` §3.1, §3.2, §4.4 |
| Replaces | `test_m4a_tts_002_persistent_error_reopen_and_next_success`, `test_m4a_tts_002_every_whitelisted_error_reopens_same_child` |
| Timeout | 90 s |

**Context**: The two replaced functions required `GENERATION_REJECTED` (and every `TTS_ERROR_CODES`
member) to produce an `AdapterRejected` request-level outcome, with the same child remaining READY
and accepting the next request. Under M4-ERR §3.2 `REBUILD_REQUIRED`, any native TTS generation
failure, protocol, PCM or child failure must raise a typed `ComponentSystemFault` with the stable
TTS key; the child is destroyed immediately and no new admission may occur before RM rebuild.

These two functions are **included** in G05 execution; their G06 AST-identity comparison against
SHA `54c506713082b1ea95cfa331f08b7124dcfa0316` is exempted (see §7.1). All other `test_m4a_tts_002`
functions execute unchanged with their existing assertions.

**Exact code mapping** (design ref §4.4):

| Injected native code | Expected `ComponentSystemFault.code` |
| :--- | :--- |
| `GENERATION_REJECTED` | `TTS_GENERATION_FAILED` |
| `INVALID_TEXT` | `TTS_PROTOCOL_FAILED` |
| `INVALID_PCM` | `TTS_PROTOCOL_FAILED` |
| any other code in `TTS_ERROR_CODES` (protocol/child class) | `TTS_PROTOCOL_FAILED` |

**Steps**

1. Inject `GENERATION_REJECTED` into a `MatchaTTSAdapter` deterministic fake (equivalent stimulus
   to the replaced `test_m4a_tts_002_persistent_error_reopen_and_next_success`).
2. Assert `synthesize()` raises `ComponentSystemFault` with `code="TTS_GENERATION_FAILED"`,
   `backend=REBUILD_REQUIRED`, and `recovery_keys` containing exactly `TTS_KEY`.
3. Assert `fault.__cause__` is the original adapter error object (object identity).
4. Assert `child.state is ChildState.DESTROYED` immediately after the fault.
5. Assert a second `synthesize()` call before recovery raises a "not ready" error (e.g.,
   `AdapterUnavailable`) — no new request is admitted to the destroyed child.
6. Parameterize over every code in `TTS_ERROR_CODES` (equivalent stimulus to the replaced
   `test_m4a_tts_002_every_whitelisted_error_reopens_same_child`): for each code, inject the
   error and assert the exact code mapping above, `REBUILD_REQUIRED` disposition with `TTS_KEY`,
   child `DESTROYED`, and no second admission before rebuild.
7. After `force_abort()` and `rm.begin_recovery((TTS_KEY,))` with a fresh child factory:
   assert `rm.recovery_ready()` becomes `True`; the rebuilt adapter is `ChildState.READY`; the
   replacement child (not the original) accepts the next `synthesize()` and returns PCM.

**Acceptance criteria**

- Exact typed fault code per the mapping table above for every `TTS_ERROR_CODES` member.
- `REBUILD_REQUIRED` disposition with `TTS_KEY` on every fault; `fault.__cause__` is the
  original exception (object identity).
- Child `DESTROYED` immediately after each fault; no second request admitted before rebuild.
- Post-rebuild: replacement child `start_count == 1`; `synthesize()` returns PCM.
- All other `test_m4a_tts_002` cases pass with existing assertions unchanged.

---

### M4-ERR-PI-012 — Typed-fault cause chain and sanitized public boundary (replaces B2)

| Field | Value |
| :--- | :--- |
| Layer | `PI` |
| WP | `M4-ERR-WP1`, `M4-ERR-WP4`, `M4-ERR-WP5` |
| Design ref | `ch_m4_error_handling.md` §3.1, §3.3, §5 |
| Replaces | `test_product_fatal_boundary_has_no_normal_fact_and_sanitized_traceback` (all eight parametrize cases), `test_V01_completion_callback_failure_reaches_worker_supervision` |
| Timeout | 90 s |

**Context**

*B2-part-1 — `__cause__` suppression in fatal boundary*: The replaced parametrized function
asserted `error.__cause__ is None` for all eight `problem` cases. Under M4-ERR §3.1, every
production fault mapping uses `raise fault from cause`; `fault.__cause__` must be the original
exception object where a cause exists. The public fatal output path uses the product's single
first-root type/code-only renderer (not Python's generic chained formatter); raw cause text must
not appear in any public output.

*B2-part-2 — Observer exception typed mapping*: The replaced function expected an untyped
`ObservationError` to reach worker supervision directly. Under M4-ERR, the completion-callback
failure is mapped to a `ComponentSystemFault(code="SPEAK_UNEXPECTED", backend=UNPROVEN)` raised
from the original `ObservationError`; the public `ErrorOccurred` event is sanitized.

These two functions have their G06 AST-identity comparison against SHA
`54c506713082b1ea95cfa331f08b7124dcfa0316` exempted (see §7.1). All other `test_m4b_p5_001` and
`test_m4b_priv_001` functions execute unchanged.

**Steps — Part 1: fatal boundary cause chain**

Run with the same eight `problem` parametrize inputs (`untyped`, `fatal`, `proof`, `prefix`,
`semantic`, `capability`, `unsupported`, `generation`) and equivalent stimuli.

1. For each `problem`, exercise the Reasoner with the corresponding stimulus (same as replaced function).
2. Assert `LLMFatalError` is raised (same as before).
3. Assert `responses == []` and `len(errors) == 1` (unchanged).
4. Assert `fault.__cause__` per the exact per-case table below:

| `problem` | Expected `fault.__cause__` |
| :--- | :--- |
| `untyped` | is the original `ValueError("PRIVATE-OUTPUT-CANARY")` (object identity) |
| `fatal` | is the original `LLMFatalError("PRIVATE-OUTPUT-CANARY")` (object identity) |
| `proof` | is the original `ReplaceableGenerationFailure("INVALID_SEMANTIC")` (object identity) |
| `prefix` | `__cause__ is None` — malformed SemanticGeneration fails the local prefix contract; no chained source exception |
| `semantic` | `__cause__ is None` — local contract check, no chained source exception |
| `capability` | `__cause__ is None` — local state check, no chained source exception |
| `unsupported` | `__cause__ is None` — local state check, no chained source exception |
| `generation` | `__cause__ is None` — local state check, no chained source exception |

5. Call the product's sanitized first-root renderer (not `traceback.format_exception`) on the
   `LLMFatalError` and assert:
   - Output contains at most one root entry (type name and/or safe code only).
   - `"PRIVATE-OUTPUT-CANARY"` is absent from the rendered output.
   - The generic Python chained formatter (`traceback.format_exception`) is NOT used as the
     public renderer; assert the product renderer is called instead.
6. Assert `traceback.format_exception(error)` is NOT used as evidence of public output (this
   step validates the implementation does not rely on generic chained formatting for public paths).

**Steps — Part 2: completion-callback typed fault observable via Event Bus**

1. Construct a `Speak` worker with the same `TTS`, `Output` and `Bus` fakes as the replaced
   function; `on_completion` raises `ObservationError()`.
2. Execute `speaker.execute("PRIVATE_SESSION", 1, 1, {"text": "PRIVATE_CANARY"})`.
3. Assert `ComponentSystemFault` with `code="SPEAK_UNEXPECTED"` and `backend=UNPROVEN` is
   raised — not a bare `ObservationError`.
4. Assert `fault.__cause__` is the original `ObservationError` instance (object identity).
5. Assert `len(events) == 1` and `isinstance(events[0], ErrorOccurred)`.
6. Assert `"PRIVATE_CANARY" not in repr(events)` (unchanged).
7. Assert `speaker._pcm is None` (unchanged).

**Acceptance criteria — Part 1**

- All eight parametrize cases: `LLMFatalError` raised; `responses == []`; `len(errors) == 1`.
- `__cause__` matches the per-case exact table above (object identity for `untyped`/`fatal`/
  `proof`; `is None` for `prefix`/`semantic`/`capability`/`unsupported`/`generation`).
- Product's sanitized first-root renderer is called; its output is canary-free for all eight cases.
- Generic Python chained formatter is not used as the public renderer.

**Acceptance criteria — Part 2**

- `ComponentSystemFault(code="SPEAK_UNEXPECTED", backend=UNPROVEN)` raised.
- `fault.__cause__` is the original `ObservationError` (object identity).
- Exactly one `ErrorOccurred` on Event Bus; `PRIVATE_CANARY` absent from event repr.
- `speaker._pcm is None`.

**Scope note**: All other `test_m4b_p5_001` cases
(`test_m4b_p5_001_fatal_adapter_error_is_not_translated_to_fallback`,
`test_m4b_p5_001_local_contract_error_publishes_error_without_llm_write`,
`test_m4b_p5_001_outer_timeout_keeps_generation_alive_for_typed_abort`,
`test_cancelled_product_has_no_normal_fact_O10`, `test_fragments_never_dispatch_before_terminal_X05`,
`test_fresh_prefill_is_profile_tier`, `test_invalid_admission_counts_are_fatal`) and all other
`test_m4b_priv_001` cases execute without modification and their existing assertions continue
to pass.

---

### 7.1 G06 AST-identity exemption for the four affected functions

The four named functions above have their G06 AST-identity comparison against SHA
`54c506713082b1ea95cfa331f08b7124dcfa0316` exempted for M4-ERR candidates only. The existing
G06 criterion — "upstream approved authority explicitly replaces it" — is satisfied by
`ch_m4_error_handling.md` §1.1 and this Test Spec §7. Every other function in every covered
file remains subject to full G06 immutability protection; no other G06 protection is weakened.

The two `test_m4a_tts_002` affected functions are **included** in G05 execution (not excluded);
G05 runs all M4A_FILES nodes and the two affected functions must pass `M4-ERR-PI-011` oracle
assertions. G05 selector rationale must name these two functions and their updated oracle.

This overlay applies only within `test_spec_M4_ERR.md`; `test_spec_M4B.md` is not modified.


