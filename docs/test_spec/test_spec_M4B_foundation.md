# M4B Foundation Test Specification

## Overview and scope

This specification covers the Core foundation delta approved through
[`AR_impl_M4B_III`](../reviews/history/AR_impl_M4B_III.md) and authorised by
[`m4b_foundation_revision`](../implement/m4b_foundation_revision.md). It is the
current Tester authority for `TR_spec_M4B_V`.

**In scope**: four-field `LLMResponse` schema migration, WAKE Conversation
readiness, primary/post-action-rest routing, sequential Conversation
replacement, lifecycle proof semantics, R1/R2/R3/E1 classification and affected
M1/M2 regression.

**Out of scope**: replacement M4B prompt/parser, token/KV admission, real LLM
child protocol, memory/timing evidence, Pi candidate, Display UX, legacy M4B
production/tests. No case in this spec requires a real model, Pi, Audio device,
network, credential or legacy M4B fixture.

**Race control**: all ordering tests use `asyncio.Event` / explicit barriers;
wall-clock `sleep` is prohibited.

**Execution**: `pytest -x tests/ -k "m4b_foundation" --timeout=60`

---

## FND-EVT-001 — LLMResponse four-field schema / fail-closed migration

| Field | Contract |
| :--- | :--- |
| **Design section** | §2.1, §2.2, §9.1 |
| **Risk** | Old three-field positional construction silently produces wrong route |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| Keyword construction — all six canonical outcomes | Construct `LLMResponse` with keyword args for each row in §2.3 table | Object created; `post_action_route` equals supplied value; field order matches §2.1 (`action_kind`, `action_payload`, `post_action_route`, `next_perceptions`) |
| Positional three-field legacy construction | `LLMResponse("speak", {}, ("listen",))` — three positional args without `post_action_route` | `TypeError` raised before object creation; no fallback default |
| No default for `post_action_route` | Construct `LLMResponse(action_kind="speak", action_payload={}, next_perceptions=("listen",))` — omit `post_action_route` | `TypeError`; field is required, not optional |
| Frozen immutability | Attempt to mutate `post_action_route` on a constructed instance | `FrozenInstanceError` |
| PostActionRoute literal exhaustiveness | Values `"KEEP_NEXT"`, `"REPLACE_NEXT"`, `"END_SESSION"` accepted; any other string rejected by SM THINK validation (§2.2 step 3) | SM issues `StateChanged(→ERROR)` for invalid route |
| ActionCompleted schema unchanged | `ActionCompleted` constructor signature unchanged; no `post_action_route` field | Construction succeeds with existing three fields |

---

## FND-EVT-002 — THINK exit validation

| Field | Contract |
| :--- | :--- |
| **Design section** | §2.2 |
| **Risk** | Invalid Fact silently proceeds to ACTION |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| Valid `action_kind` — `speak` | `LLMResponse(action_kind="speak", ...)` with valid payload/route | SM proceeds to ACTION |
| Valid `action_kind` — `tool` | same with `"tool"` | SM proceeds to ACTION |
| Valid `action_kind` — `rest` | `rest + END_SESSION + ()` | SM proceeds to ACTION |
| Invalid `action_kind` | `action_kind="unknown"` | SM self-check E1: `StateChanged(→ERROR)`; no `ErrorOccurred` fabricated |
| Invalid `post_action_route` | `post_action_route="RESTART"` | E1: `StateChanged(→ERROR)` |
| `rest` with non-`END_SESSION` route | `rest + KEEP_NEXT` | E1: `StateChanged(→ERROR)` |
| `rest` with `REPLACE_NEXT` | `rest + REPLACE_NEXT` | E1: `StateChanged(→ERROR)` |
| `speak + KEEP_NEXT` with empty `next_perceptions` | `speak + KEEP_NEXT + ()` | E1: continuing route requires non-empty perceptions after dedup |
| `speak + REPLACE_NEXT` with empty after dedup | perceptions all unregistered kinds | E1: continuing-empty violation |
| `END_SESSION` ignores `next_perceptions` | `speak + END_SESSION + ("listen",)` | SM ignores perceptions; canonical Reasoner must produce `()` but SM tolerates non-empty |
| Payload validation (no mutation) | SM calls `ActionPayloadValidator`; payload dict not mutated | Post-validation payload `is` same object, unmodified |
| Perception dedup — order preserved | `next_perceptions=("listen", "read", "listen", "look")` | Normalized to `("listen", "read", "look")` — first-occurrence order |
| Perception dedup — unregistered filtered | perception kind `"smell"` not registered | Filtered out before dedup; remaining must be non-empty for continuing routes |

---

## FND-WAKE-001 — WAKE readiness gate (ack/open both orders)

| Field | Contract |
| :--- | :--- |
| **Design section** | §5.1, §5.2 |
| **Risk** | Perception/ASR/generation starts before Conversation is ready |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| Ack first, open second | Wake ack timer fires → set `wake_ack_ready=True`; then `ConversationReady` arrives | Only after both: SM transitions WAKE → PERCEPTION; `StateChanged(WAKE→PERCEPTION)` published |
| Open first, ack second | `ConversationReady` arrives first; then wake ack timer fires | Same outcome: WAKE → PERCEPTION only after both |
| Ack alone — no perception | Wake ack fires; open never completes | SM stays in WAKE; no PERCEPTION transition; no perception worker/ASR/Reasoner starts |
| Open alone — no perception | `ConversationReady` arrives; ack never fires | SM stays in WAKE; no PERCEPTION transition |
| Initial state at WAKE entry | Session created | `turn_id=0`, `conversation_generation=1`, `model_admission_blocked=True`, `conversation_state="none"→"opening"` |
| `StateChanged(→WAKE)` published | Session enters WAKE | Exactly one `StateChanged(old=IDLE, new=WAKE)` |
| Open task does not block dispatch | Open task is launched but SM dispatch loop continues | SM can process interrupt/shutdown/button during WAKE before open completes |
| No perception/ASR/generation before readiness | Hold both ack and open barriers; enqueue pending input via armed producer | Zero perception-task launches, zero ASR frame consumption, zero `reason()` calls until both barriers release and full readiness predicate is true; pending input remains unconsumed in buffer |

---

## FND-WAKE-002 — Failed open / WAKE interruption

| Field | Contract |
| :--- | :--- |
| **Design section** | §5.3 |
| **Risk** | Failed open leaks session or blocks subsequent wake |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| `ConversationOpenRejected(True, True)` — R2 retry | Open returns `ConversationOpenRejected(cleanup_proven=True, engine_usable=True)` | SM preserves Product Session; increments `conversation_generation`; launches new `open_conversation(session_id, gen+1)`; turn identity not reset |
| `ConversationOpenRejected(False, True)` — E1 | `cleanup_proven=False` | E1: `StateChanged(→ERROR)` |
| `ConversationOpenRejected(True, False)` — E1 | `engine_usable=False` | E1: `StateChanged(→ERROR)` |
| `ConversationOpenRejected(False, False)` — E1 | Both false | E1: `StateChanged(→ERROR)` |
| Exception during open | `open_conversation` raises | E1 |
| Wrong return type | `open_conversation` returns a plain string | E1: wiring/contract error |
| Interrupt during WAKE open | `InterruptRequested` while open task in-flight | SM cancels wake timer, blocks admission; open record converged via §8; cleanup/termination proof required before session clear or new wake |
| Error during WAKE open | `ErrorOccurred`-equivalent while open in-flight | Same convergence: open record cleanup before session tear-down |
| Shutdown during WAKE open | `ShutdownRequested` while open in-flight | Same convergence; no new wake accepted until proof obtained |

---

## FND-ACT-001 — ACTION route: KEEP_NEXT

| Field | Contract |
| :--- | :--- |
| **Design section** | §6.2 table row 1-2 |
| **Risk** | Wrong perceptions used for next turn |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| `speak + KEEP_NEXT` — primary ok | Action worker returns `ActionCompleted(speak, ok)` | Keep Conversation; next PERCEPTION uses normalized `next_perceptions`; `turn_id += 1` |
| `speak + KEEP_NEXT` — primary error | `ActionCompleted(speak, error)` | Keep Conversation; next PERCEPTION uses `default_perceptions` instead; `turn_id += 1` |
| `tool + KEEP_NEXT` — primary ok | `ActionCompleted(tool, ok)` | Same as speak: keep Conversation, use normalized perceptions |
| `tool + KEEP_NEXT` — primary error | `ActionCompleted(tool, error)` | Use `default_perceptions` |
| No post-action rest phase | `KEEP_NEXT` route | No rest record created; no `action_rest` phase |
| Conversation generation unchanged | After KEEP_NEXT completion | `conversation_generation` same as before ACTION |

---

## FND-ACT-002 — ACTION route: REPLACE_NEXT

| Field | Contract |
| :--- | :--- |
| **Design section** | §6.2 table row 3-4, §6.3 |
| **Risk** | Replacement barrier skipped or overlaps generations |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| `speak + REPLACE_NEXT` — primary ok | `ActionCompleted(speak, ok)` | Action completes first; then replacement barrier (§6.3) executes; normalized perceptions used for next turn |
| `speak + REPLACE_NEXT` — primary error | `ActionCompleted(speak, error)` | Replacement still executes; `default_perceptions` used instead |
| `tool + REPLACE_NEXT` — ok | `ActionCompleted(tool, ok)` | Same: action then replacement |
| `tool + REPLACE_NEXT` — error | `ActionCompleted(tool, error)` | Replacement with `default_perceptions` |
| No post-action rest phase | `REPLACE_NEXT` route | No rest phase at all; replacement is not a rest |
| Perceptions selected before barrier | Check that perception list is determined before close/open | Same list used regardless of barrier duration |

---

## FND-ACT-003 — ACTION route: END_SESSION (speak/tool + rest phases)

| Field | Contract |
| :--- | :--- |
| **Design section** | §2.3, §6.2 table row 5-7 |
| **Risk** | Primary and rest phases overlap or rest skipped |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| `speak + END_SESSION` — final non-empty speech | Primary `ActionCompleted(speak, ok)` | Primary record join/remove first; then one `post_action_rest` record created with different `correlation_id`; rest completes → session convergence |
| `tool + END_SESSION` | Primary `ActionCompleted(tool, ok)` | Same: tool completes → one rest phase → session convergence |
| `rest + END_SESSION` — empty end | Only rest, no primary | Exactly one rest phase; no fabricated speech; rest completes → session convergence |
| Primary and rest — different correlation IDs | Observe `InFlightRecord` for both phases | `correlation_id` differs; `phase` is `action_primary` then `action_rest` |
| Primary and rest never coexist | Check in-flight records | Primary record fully joined/removed before rest record created |
| Public state stays ACTION | During both primary and rest | No `StateChanged(ACTION, ACTION)` published; state remains ACTION throughout |
| Final primary error still rests | `ActionCompleted(speak, error)` + `END_SESSION` | Error does not prevent rest; still rests and ends; `default_perceptions` NOT used (session ending) |
| `next_perceptions` completely ignored | `END_SESSION` with `next_perceptions=("listen",)` in Fact | SM ignores them; no perception started after rest |

---

## FND-REP-001 — Sequential replacement barrier

| Field | Contract |
| :--- | :--- |
| **Design section** | §6.3 |
| **Risk** | Generation overlap, input replay, session/turn identity broken |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| Admission blocked at barrier start | Step 1: primary join complete | `model_admission_blocked=True`; any Reasoner/generate admission rejected |
| THINK record proof | Step 2: check THINK in-flight record | Record has terminal/task join proof before barrier proceeds |
| Close before open | Steps 3→5 | `close_conversation(session_id, old_gen)` completes with full proof before `open_conversation(session_id, new_gen)` starts |
| `ConversationCloseProof` — all three flags true | Close returns proof with `request_terminal_proven=True`, `cleanup_proven=True`, `engine_usable=True` | Old generation claim cleared; proceed to open |
| Close proof — `request_terminal_proven=False` | Missing request terminal proof | E1: leave R2; no new Conversation claimed |
| Close proof — `cleanup_proven=False` | Cleanup not proven | E1 |
| Close proof — `engine_usable=False` | Engine destroyed | E1; no new Conversation claimed |
| Open returns `ConversationReady` | Step 5: matching generation | Admission unblocked; proceed to next PERCEPTION |
| Session preserved | Throughout barrier | Same `session_id`; no session clear/discard/flush |
| Turn monotonic | After replacement | `turn_id += 1`; no reset or reuse |
| Generation incremented | After close, before open | `conversation_generation` incremented exactly once |
| No overlap | Between close proof and open call | No moment where two generations are both claimed |
| No input replay | Barrier does not replay | Rejected input from old Conversation not re-submitted |
| No buffer exit policy | `REPLACE_NEXT` action | No `flush_to_wake` or `discard`; buffer policy is `none` |
| Perceptions from before barrier | Perception list selected pre-barrier | Same normalized (or default for error) perceptions used post-barrier |

---

## FND-REP-002 — Repeated replacement (R2)

| Field | Contract |
| :--- | :--- |
| **Design section** | §6.3, §8 |
| **Risk** | Repeated R2 incorrectly escalates to E1 or R3 |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| Two consecutive replacements | First `REPLACE_NEXT` → barrier → PERCEPTION → THINK → second `REPLACE_NEXT` → barrier | Both succeed; `conversation_generation` increments twice; `turn_id` monotonically increases |
| Three consecutive replacements | Three `REPLACE_NEXT` in sequence | All succeed; no E1/R3 escalation due to count |
| Session identity preserved | Across all replacements | Same `session_id` throughout |
| No count-based escalation | Any number of R2s | R2 count does not trigger E1; only proof failure triggers E1 |

---

## FND-LIFE-001 — Lifecycle port contract and wiring

| Field | Contract |
| :--- | :--- |
| **Design section** | §3.1, §4 |
| **Risk** | Missing control or double-fill silently accepted |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| `set_conversation_lifecycle(control)` — happy path | SM started; control injected before producer arm | Succeeds; SM uses control for all lifecycle operations |
| Missing control | SM start → producer arm without `set_conversation_lifecycle` | `StateManagerWiringError`; startup fails closed |
| `None` control | `set_conversation_lifecycle(None)` | `StateManagerWiringError` |
| Double fill | Call `set_conversation_lifecycle` twice | `StateManagerWiringError` on second call |
| Fill after producer arm | Producer already armed; then fill | `StateManagerWiringError` |
| Control Protocol check | Object passed to `set_conversation_lifecycle` | Must satisfy `runtime_checkable` `ConversationLifecycleControl` Protocol; non-conforming object → `StateManagerWiringError` |
| M1/M2 deterministic fake | M1/M2 composition | Inject deterministic fake implementing `ConversationLifecycleControl`; SM accepts and operates |
| Concurrent lifecycle rejected | Two lifecycle operations simultaneously | Second operation rejected; only one allowed at a time |
| Wrong session/generation reentry | `open_conversation(wrong_session, gen)` | E1: wiring/contract error |

---

## FND-LIFE-002 — Private lifecycle notices and stale identity

| Field | Contract |
| :--- | :--- |
| **Design section** | §3.3 |
| **Risk** | Stale notice from old generation corrupts new session |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| Matching notice accepted | `_ConversationLifecycleCompleted` with correct `(operation, session_id, generation, correlation_id, task_identity)` | SM processes result via `task.result()`; normal lifecycle flow |
| Stale session_id | Notice carries old `session_id` | Sanitized log emitted (no raw/sensitive context); notice dropped; active session and generation unchanged |
| Stale generation | Notice carries old `generation` (e.g., gen 1 arriving after gen 2 started) | Sanitized log emitted (no raw/sensitive context); notice dropped; active session and generation unchanged |
| Stale correlation_id | Notice carries wrong `correlation_id` | Sanitized log emitted (no raw/sensitive context); notice dropped; active session and generation unchanged |
| Stale task identity | Task identity mismatch | Sanitized log emitted (no raw/sensitive context); notice dropped; active session and generation unchanged |
| Single notice per lifecycle task | Done callback | Enqueues exactly one `_ConversationLifecycleCompleted`; no duplicate result notice |
| Result retrieved only after task done | SM dispatch | `task.result()` called only after confirming task done |

---

## FND-LIFE-003 — Done-but-unproven lifecycle convergence

| Field | Contract |
| :--- | :--- |
| **Design section** | §3.3 (paragraphs on done-but-unproven) |
| **Risk** | Unproven record silently removed; cleanup skipped |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| Task done but `cleanup_proven=False` — record retained | Lifecycle task completes but result lacks proof | `InFlightRecord` NOT removed; remains as E1 convergence target |
| Level 1 abort succeeds | `abort()` returns successfully on unproven record | Becomes cleanup proof per worker contract; SM marks `cleanup_proven=True` and removes record |
| Level 1 abort timeout → Level 2 | `abort()` times out | Escalate to `force_abort()` |
| Level 2 `force_abort()` succeeds | `force_abort()` returns + outer task done + `ForceAbortReport` | Combined proof accepted; record marked proven and removed |
| Level 2 timeout/exception → Level 3 | `force_abort()` fails | Level 3 escalation |
| Outer task done alone insufficient | Task done but no cleanup proof | Record not removed; abort still required |
| Converger must call abort | `cleanup_proven=False` on lifecycle record | Converger invokes `abort()`; does not skip cleanup because outer task is done |

---

## FND-PHASE-001 — InFlightRecord phase and completion mode

| Field | Contract |
| :--- | :--- |
| **Design section** | §3.3 |
| **Risk** | Phase mismatch or wrong completion mode applied |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| Worker phases use `worker_fact` completion | `perception`, `think`, `action_primary`, `action_rest` phases | `completion_mode="worker_fact"`; require terminal Fact + task done |
| Lifecycle phases use `private_result` completion | `conversation_open`, `conversation_close` phases | `completion_mode="private_result"`; require matching private result + task done + required proof |
| Lifecycle record `kind` values | Open record | `kind="conversation.open"` |
| Lifecycle record `kind` values | Close record | `kind="conversation.close"` |
| Cancel timeout per-kind override | Lifecycle record with `kind="conversation.open"` | Per-kind cancel timeout applied if configured; otherwise default |
| No new timeout config in this revision | Check config surface | Revision does not add new timeout configuration options |

---

## FND-R1-001 — R1 application retry

| Field | Contract |
| :--- | :--- |
| **Design section** | §6.1, §8 |
| **Risk** | Retry after Conversation mutation accepted as R1 |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| Clean R1 retry | `speak + KEEP_NEXT` application response; input did not mutate Conversation | Keep generation; normal ACTION; same Conversation used |
| R1 is normal cognition Fact | Application retry Fact | It is a standard `LLMResponse` with `speak + KEEP_NEXT + non-empty next_perceptions` |
| `UNSUPPORTED_INPUT` not R1 | Wiring returns unsupported input | Must go to E1, not R1 |
| Wiring failure not R1 | Wiring error during retry | E1 |
| Cannot prove no mutation — E1 | Retry after possible Conversation mutation | E1; no R1 claim |

---

## FND-CONV-001 — Session convergence with Conversation close

| Field | Contract |
| :--- | :--- |
| **Design section** | §7 |
| **Risk** | Session ends without Conversation cleanup proof |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| Normal rest end — close ready Conversation | `rest + END_SESSION` completes; Conversation is ready | Session-end close launched; `ConversationCloseProof` with all flags `True` → session tracking cleared; resume wake; return to IDLE |
| Buffer policy — normal rest | Normal rest session end | `flush_to_wake` |
| Buffer policy — interrupt | `InterruptRequested` during active session | `discard` |
| Buffer policy — error | E1 during active session | `discard` |
| Buffer policy — shutdown | `ShutdownRequested` | `discard` |
| Buffer policy — replacement | `REPLACE_NEXT` in progress | `none` (no flush/discard) |
| Open not yet claimed — no extra close | Open failed; cleanup already covered by abort | No redundant close operation |
| Close proof missing — E1/Level 2 | Session-end close returns incomplete proof | E1 → Level 2 escalation |
| Level 2 destroyed backend | Engine destroyed during session-end close | Existing RM recovery barrier used |
| In-flight empty before lifecycle close | Workers still active | Workers converged first (existing SessionConverger); then lifecycle close |
| All proofs required before IDLE | Lifecycle proof + in-flight empty + recovery barrier | Only when all three satisfied: clear session, resume wake, → IDLE |
| Convergence phase order | `_PendingConvergence` | `workers → conversation_close → recovery → complete` |

---

## FND-CONV-002 — R3 explicit end and E1 boundary

| Field | Contract |
| :--- | :--- |
| **Design section** | §7, §8 |
| **Risk** | E1 and R3 confused; missing proof silently accepted |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| R3 — explicit USER end/reset | Parameterize the canonical Reasoner outcomes `speak + END_SESSION + ()`, `tool + END_SESSION + ()`, and `rest + END_SESSION + ()` for an explicit USER end/reset intent | Complete the selected primary/rest phases exactly as FND-ACT-003 specifies; close the active generation; end the same Product Session; `flush_to_wake`; return to IDLE only after all proofs |
| R3 — interrupt | `InterruptRequested` during an active Conversation | Close the active generation; end the Product Session; `discard`; return to IDLE only after all proofs |
| Shutdown boundary — not R3 | `ShutdownRequested` during an active Conversation | Close the active generation; end the Product Session; `discard`; terminate the process only after all proofs |
| E1 — missing proof | Any lifecycle operation returns without required proof | `StateChanged(→ERROR)`; Level 1/2/3 escalation per §3.3 |
| E1 — wiring/protocol failure | `open_conversation` returns wrong type | `StateChanged(→ERROR)` |
| E1 — worker crash | Worker task raises unhandled exception | `StateChanged(→ERROR)` |
| E1 — backend unusable | `engine_usable=False` in any proof | `StateChanged(→ERROR)` |
| E1 — illegal Fact | THINK validation fails per §2.2 | `StateChanged(→ERROR)`; SM does not fabricate `ErrorOccurred` |
| E1 does not directly enter Level 3 | E1 from schema violation alone | Level 1 attempted first; Level 3 only after Level 2 proof failure |
| Repeated R2 never becomes E1 | Multiple successful replacements | No escalation based on count |
| Repeated R2 never becomes R3 | Multiple successful replacements | No automatic session end |

---

## FND-SM-001 — SessionContext data model integrity

| Field | Contract |
| :--- | :--- |
| **Design section** | §4 |
| **Risk** | Cross-phase state leak or stale action_completed flag reuse |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| Default `SessionContext` values (unattached) | `SessionContext` constructed without session | `conversation_generation=0`, `conversation_state="none"`, `wake_ack_ready=False`, `model_admission_blocked=True`, `post_action_route=None`, `normalized_next_perceptions=()`, `action_phase="none"` |
| WAKE-initialized Product Session | SM creates Product Session and enters WAKE (§5.1) | `conversation_generation=1`, `turn_id=0`, `model_admission_blocked=True`, `conversation_state` transitions to `"opening"` |
| `turn_id` monotonic across replacement | Two replacements in same session | `turn_id` never decreases; never reuses a value; not reset by replacement |
| `action_phase` transitions | Through primary and rest | `none → primary → none → post_action_rest → none` |
| `action_completed` not reused cross-phase | Phase completion data | Attributed to matching in-flight record; cleared when phase ends |
| `post_action_route` set after THINK | THINK validation passes | `post_action_route` set to validated value from `LLMResponse` |
| `normalized_next_perceptions` set after THINK | THINK with continuing route | Set to deduplicated, filtered tuple |
| `conversation_state` transitions | Through lifecycle | `none → opening → ready → closing → none` |
| Reasoner `reason()` gets `conversation_generation` | SM calls Reasoner | Keyword-only `conversation_generation` argument passed; value matches current session generation |
| Reasoner not called if not ready | `conversation_state != ready` or `model_admission_blocked` | SM does not invoke `reason()` |

---

## FND-RM-001 — Resource Manager Conversation control late-fill

| Field | Contract |
| :--- | :--- |
| **Design section** | §4 (set_conversation_lifecycle), §9.1 |
| **Risk** | Startup without lifecycle control silently proceeds |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| RM provides control before producer arm | RM calls `set_conversation_lifecycle(control)` after SM start, before producers | SM accepts; operations use this control |
| RM provides Reasoner's control property | `worker.cognition.reasoner` control property or instance implements Protocol | Protocol check passes at `runtime_checkable` level |
| RM fails to provide — startup fail | SM start → producer arm → no fill | `StateManagerWiringError`; startup halted |
| No null/optional bypass | Attempt to pass None or skip | Error; no bypass path exists |

---

## FND-REG-001 — M1/M2 full regression

| Field | Contract |
| :--- | :--- |
| **Design section** | §9.2, §10 item 9 |
| **Risk** | Foundation migration breaks existing accepted behavior |
| **Suite marker** | `m4b_foundation` |
| **Timeout** | 60 s |

### Cases

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| All existing M1 entrypoints green | Run `tests/milestones/test_m1_foundation.py` | All tests pass |
| All existing M2 entrypoints green | Run `tests/milestones/test_m2_mock_pipeline.py` | All tests pass |
| `test_events.py` regression | Run `tests/test_events.py` | All tests pass |
| `test_state_manager.py` regression | Run `tests/test_state_manager.py` | All tests pass |
| `test_m2_sm_flows.py` regression | Run `tests/test_m2_sm_flows.py` | All tests pass |
| `test_m2_flows.py` regression | Run `tests/test_m2_flows.py` | All tests pass |
| `test_m2_wrk_003.py` regression | Run `tests/test_m2_wrk_003.py` | All tests pass |
| Changed assertions are regression only | Diff of assertion changes | Updated assertions only verify existing accepted behavior against new schema; not proof that historical tests cover new foundation behavior |

### Executable anti-deletion / anti-skip proof

**Node-ID baseline**: Tester owns the immutable pre-migration node-ID baseline at
[`docs/test_spec/baselines/m4b_foundation_node_ids.txt`](../test_spec/baselines/m4b_foundation_node_ids.txt)
(99 node IDs, checked in before Developer entry). It was produced by:

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
  > /tmp/m4b_foundation_pre_collection.txt
awk '/::/' /tmp/m4b_foundation_pre_collection.txt | LC_ALL=C sort -u \
  > docs/test_spec/baselines/m4b_foundation_node_ids.txt
test "$(wc -l < docs/test_spec/baselines/m4b_foundation_node_ids.txt)" -eq 99
```

**Post-migration deletion check** (fail-closed):

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
test ! -s /tmp/m4b_foundation_missing_nodes.txt
```

Any command failure or non-empty missing-node file is `FND-REG-001: FAIL`. New node IDs are allowed;
missing or renamed baseline node IDs are not.

**Runtime regression check**: run the full regression suite and parse JUnit XML:

```bash
PYTHONPATH=src pytest -x --strict-markers --junit-xml=regression_result.xml \
  "${regression_files[@]}" --timeout=60
```

Acceptance: parse `regression_result.xml`; assert `failures == 0`, `errors == 0`, `skipped == 0`.
Pytest xfail/xpass outcomes must not appear.

| Case | Stimulus | Observable result |
| :--- | :--- | :--- |
| Structural anti-weakening guard | Parse every `*.py` under `src/` and `tests/` with `ast`; resolve direct or imported aliases of `LLMResponse`; inspect every matching `ast.Call`. Also parse the seven baseline regression files for skip/xfail decorators and calls. | Every `LLMResponse` call has `args == []`, no `**kwargs`, and explicit `action_kind`, `action_payload`, `post_action_route`, `next_perceptions` keywords. The baseline files contain no `pytest.mark.skip`, `pytest.mark.xfail`, `pytest.skip()` or `pytest.xfail()`. Report every violation as `path:line`; any violation fails. |

Implement the structural anti-weakening guard as a `m4b_foundation`-marked pytest test. This
replaces the previous `grep -rnP` command; do not retain the grep as an acceptance gate.

---

## Test ID → Design section cross-reference

| Test ID | Design §§ | TR_spec_M4B_V item |
| :--- | :--- | :--- |
| FND-EVT-001 | §2.1, §2.3, §9.1 | 1 |
| FND-EVT-002 | §2.2 | 1, 4 |
| FND-WAKE-001 | §5.1, §5.2 | 2 |
| FND-WAKE-002 | §5.3 | 3 |
| FND-ACT-001 | §6.2 rows 1-2 | 4, 6 |
| FND-ACT-002 | §6.2 rows 3-4, §6.3 | 4, 7 |
| FND-ACT-003 | §2.3, §6.2 rows 5-7 | 4, 5 |
| FND-REP-001 | §6.3 | 7 |
| FND-REP-002 | §6.3, §8 | 7, 9 |
| FND-LIFE-001 | §3.1, §4 | 8, 9 |
| FND-LIFE-002 | §3.3 | 8 |
| FND-LIFE-003 | §3.3 | 10 |
| FND-PHASE-001 | §3.3 | 10 |
| FND-R1-001 | §6.1, §8 | 9 |
| FND-CONV-001 | §7 | 5, 6, 10 |
| FND-CONV-002 | §7, §8 | 9, 10 |
| FND-SM-001 | §4 | 4, 7 |
| FND-RM-001 | §4, §9.1 | 8 |
| FND-REG-001 | §9.2, §10 item 9 | 11 |

---

## TR_spec_M4B_V coverage map

| TR_spec_M4B_V requirement | Covering Test IDs |
| :--- | :--- |
| 1. Event schema explicit `post_action_route`; positional fails closed | FND-EVT-001, FND-EVT-002, FND-REG-001 |
| 2. WAKE ack/open both orders; neither alone starts perception/ASR/generation | FND-WAKE-001 |
| 3. Interrupt/error/shutdown during open converges before cleanup or new wake | FND-WAKE-002 |
| 4. `KEEP_NEXT`, `REPLACE_NEXT`, `END_SESSION` each have one route for speak/tool/rest | FND-ACT-001, FND-ACT-002, FND-ACT-003, FND-EVT-002 |
| 5. Final non-empty speech → one rest; empty end → exactly one rest | FND-ACT-003 |
| 6. Continuing action error uses `default_perceptions`; final error still rests and ends | FND-ACT-001, FND-ACT-003, FND-CONV-001 |
| 7. Replacement: close before open, session/turn identity, no overlap/replay/buffer exit | FND-REP-001, FND-REP-002, FND-ACT-002, FND-SM-001 |
| 8. Stale session/generation/correlation/task identity rejected | FND-LIFE-001, FND-LIFE-002, FND-RM-001 |
| 9. R1, proven R2, repeated R2, explicit R3, missing-proof/Engine-unusable E1 distinct | FND-R1-001, FND-REP-001, FND-REP-002, FND-ACT-003, FND-CONV-002 |
| 10. Done-but-unproven lifecycle → convergence target; Level 2/recovery/Level 3 boundaries | FND-LIFE-003, FND-PHASE-001, FND-CONV-001 |
| 11. Existing M1/M2 entrypoints and full regression green; no delete/skip/xfail | FND-REG-001 |

---

## Blocking findings

None. Designer clarified R3 classification in round 2: explicit USER end/reset is a
Reasoner-produced canonical `END_SESSION` outcome; interrupt is `InterruptRequested`; shutdown
is not R3. All routes are now covered with distinct cases and buffer policies.
