# REVIEW-LLM-M3-M4-GATE2-DEVELOPMENT-READINESS-R3-001

- **Date**: 2026-08-28
- **From**: Independent Reviewer
- **To**: LLM POC Designer / Technical Lead
- **Status**: `REVISION_REQUIRED / MILESTONE COMMIT NOT APPROVED / PI NOT AUTHORIZED`
- **Reviewed base**: `0638f5ad859627014f7cf0d57882ac394b100466` plus the submitted R3 replacement worktree
- **Gate 2A lock SHA-256**: `e8eaebcbc8c69bb85b94b7491f945b01b353ae30c45d0244ea7d147b5c674aab`
- **Gate 2B lock SHA-256**: `a95f9669bc4caa17a7fbd14242f48a54a02411c9fd8b0972a6a9758be21ca910`
- **Responds to**: `docs/response/REVIEW-REQUEST-LLM-M3-M4-GATE2-READINESS-R3-001.md`

## 1. Decision and Scope

R3 closes the partial-start cleanup defect, but the P5 cancel side effect and the actual scored
protocol classification are still not fail-closed. The replacement therefore cannot yet be
committed as the approved Gate 2 execution surface.

This is a targeted review of R2-F1 through R2-F3 only. It does not reopen original F1/F5, add model
substitution assumptions, require Audio-quality/full-integration testing, or change the cumulative
Gate allocation.

## 2. Verification Performed

- Gate 2 workstation tests: `55 passed`.
- Gate 1 regression tests: `136 passed`; the same pre-existing async thread warning remains.
- Changed Python bytecode compilation: PASS.
- `git diff --check`: PASS.
- Both submitted lock digests match the R3 request and all referenced repository artifact hashes.
- R2-F3 partial-start and post-allocation cleanup paths were independently inspected and their
  targeted tests reproduced successfully.
- Targeted P5 lifetime schedule reproduced native cancel running after conversation close.
- Targeted scored-path injections reproduced `BrokenPipeError` and shutdown timeout as
  `INCONCLUSIVE`, plus a valid candidate failure being masked by a later rebuild observation error.

## 3. R2 Finding Closure Status

| R2 finding | R3 status | Decision basis |
| --- | --- | --- |
| R2-F1 P5 completion/cancel arbitration | `PARTIAL / BLOCKING` | The state decision is atomic, but the native cancel side effect is outside the protected conversation lifetime and its success marker is premature. |
| R2-F2 actual scored protocol classification | `PARTIAL / BLOCKING` | `PiPacketFailure` is mapped correctly, but ordinary post-READY pipe/shutdown exceptions and mixed-stage precedence still produce the wrong disposition. |
| R2-F3 partial-start owner cleanup | `CLOSED` | Attempted domains are registered before start, live roots are captured per domain or after partial allocation, fallback runs, and partial proof is retained before sampling. |

## 4. Blocking Findings

### R3-F1 — Native cancel execution is not protected by the completion arbitration

**Maps to**: R2-F1
**Severity**: Blocking

`cancel()` decides under `_lock` that the conversation is active, sets
`_native_cancel_invoked=True`, then releases the lock before emitting `native_cancel_once` and
calling `conversation.cancel_process()`. The worker can acquire the lock in between, observe the
cancel flag, enter `finally`, clear and close the conversation, after which the cancel thread calls
the native API on the closed object.

A deterministic schedule paused the cancel thread at the current `native_cancel_once` event and
released the worker. It produced:

```text
closed_before_native_call=True
events=chunk_started,native_cancel_once,conversation_discarded,
       continuous_terminal_cancelled
cancel_errors=RuntimeError:cancel after close
```

The marker is emitted before the native call, so the scorer can count one successful native cancel
even though the call failed. With `timeout_requested` already set, the child can still emit TIMEOUT;
this leaves a false-PASS path for the active-chunk mode.

**Required correction**:

1. Keep the conversation lifetime protected until `cancel_process()` finishes, either by invoking
   it while holding the state lock or by an explicit cancel-in-flight handshake that prevents
   `finally` from closing the conversation.
2. Emit `native_cancel_once` only after the native call succeeds. A raised native cancel must be
   observable as a failed marker/mode and cannot satisfy P5 PASS.
3. Add the exact opposing-lifetime test: pause after cancel wins arbitration but before the native
   call, let the worker attempt finalization, and prove the conversation remains open until one
   successful cancel completes. Then assert TIMEOUT, active-mode markers, same-child health,
   rebuild and zero residue.

**Reference implementation solution**:

Use a `threading.Condition` backed by the existing state lock and add
`_native_cancel_in_flight` plus `_native_cancel_succeeded`. Do not hold the state lock while calling
the native runtime, because the native call may wait for the generation thread; instead, reserve the
conversation lifetime before releasing the lock and make finalization wait for that reservation.

```python
# __init__
self._condition = threading.Condition(self._lock)
self._native_cancel_in_flight = False
self._native_cancel_succeeded = False

def cancel(self) -> None:
    with self._condition:
        self._cancel_requested = True
        conversation = self._conversation
        should_cancel = (
            self._state == "ACTIVE_CHUNK"
            and conversation is not None
            and not self._native_cancel_invoked
        )
        if not should_cancel:
            return
        self._native_cancel_invoked = True
        self._native_cancel_in_flight = True

    cancel_error = None
    try:
        conversation.cancel_process()
    except Exception as error:
        cancel_error = error

    # Publish the observed native outcome while finalization is still blocked.
    # The finally prevents a logging failure from stranding the worker.
    try:
        event("native_cancel_once" if cancel_error is None else "native_cancel_failed")
    finally:
        with self._condition:
            self._native_cancel_succeeded = cancel_error is None
            self._native_cancel_in_flight = False
            self._condition.notify_all()
```

The `_chunk()` `finally` block must wait before clearing or closing the same conversation:

```python
with self._condition:
    while self._native_cancel_in_flight and self._conversation is conversation:
        self._condition.wait()
    if self._conversation is conversation:
        self._conversation = None
    self._state = "BETWEEN_CHUNKS"
conversation.close()
```

Add `native_cancel_failed` to the marker evidence/schema/verifier. Active-mode PASS must require
`native_cancel_once == 1` and `native_cancel_failed == 0`; boundary-mode PASS must require both
counts to be zero. Reset all three native-cancel fields at the start of each request. This design
makes the marker describe a completed native call rather than an attempted call and prevents close
from overtaking it.

The regression test must block inside the native call, not inside the success marker. While blocked,
assert that the generation thread cannot close the conversation. After releasing the native call,
assert success marker count `1`, failure marker count `0`, close count `1`, no cancel-thread error,
and the complete P5 terminal/recovery/rebuild proof. A second test injects a native exception and
requires failure marker `1`, success marker `0` and P5 FAIL.

**Closure evidence**: cancel-first always performs exactly one successful native call before close;
completion-first always closes before cancel can claim the active mode and performs zero native
cancels.

### R3-F2 — The scored exception boundary and disposition precedence remain incomplete

**Maps to**: R2-F2
**Severity**: Blocking

The new wrappers convert only `PiPacketFailure`. Several normal post-READY candidate failures use
different concrete exceptions before `read_frame()` can create that type:

- A child that has closed its protocol pipe can make `send()` raise `BrokenPipeError`. Both Gate 2A
  and Gate 2B `scored_generate()` currently propagate it as a generic environment error, producing
  `INCONCLUSIVE` instead of candidate FAIL.
- P5 PING has the same broken-pipe path through `scored_pong()`.
- `close_child()` can raise `subprocess.TimeoutExpired` when a READY child does not exit after its
  shutdown exchange. `scored_close_child()` does not translate it, so failed candidate shutdown is
  also `INCONCLUSIVE` despite the R3 request claiming a typed shutdown boundary.

The targeted outputs were:

```text
gate2a scored_generate BrokenPipeError INCONCLUSIVE
gate2b scored_generate BrokenPipeError INCONCLUSIVE
p5 scored_pong BrokenPipeError INCONCLUSIVE
p5 scored_close_child TimeoutExpired INCONCLUSIVE
```

There is also a result-combination error. `p5_runner_disposition()` checks any observation or
rebuild-observation error before any candidate error. A valid primary no-terminal candidate failure
followed by an unrelated rebuild-start observation error is therefore changed to `INCONCLUSIVE`:

```text
candidate_error=PiPacketFailure
rebuild_observation_error=PiPacketFailure
result=INCONCLUSIVE
```

The same masking also occurs for primary failures that do not populate `candidate_error`: a late
terminal, invalid timeout markers, or failed same-child health followed by a rebuild observation
error all currently return `INCONCLUSIVE`. This erases an already validly observed mandatory failure
and conflicts with the packet's explicit `candidate generation error, wrong/late terminal, hang or
failed recovery = FAIL` rule.

**Required correction**:

1. At the post-READY scored pipe boundary, translate candidate-owned broken-pipe/closed-stream
   outcomes into `CandidateViolation` in both runners. Do not broadly relabel unrelated filesystem,
   sampler or probe errors.
2. Extend the P5 PING and shutdown wrappers to classify candidate-owned pipe closure and bounded
   shutdown timeout as candidate/cleanup violations. Preserve true pre-READY and environment
   failures as `INCONCLUSIVE`.
3. Make P5 disposition stage-aware: independently adjudicate the complete primary stage first,
   including terminal timing/type, timeout markers and same-child recovery. Return a primary FAIL or
   INCONCLUSIVE immediately. Only when the primary stage is PASS may rebuild candidate/observation
   errors or rebuild health decide the final result. Apply the identical algorithm in the independent
   evidence verifier.
4. Add actual wrapper/disposition tests for Gate 2A and 2B broken pipe, P5 PING broken pipe,
   shutdown timeout, primary-candidate-plus-rebuild-observation, and a control proving an unrelated
   probe/sampler `OSError` remains `INCONCLUSIVE`.

**Reference implementation solution**:

Create one narrow helper for errors that can only arise from the authenticated post-READY protocol
pipe. Do not add generic `OSError` or `subprocess.SubprocessError` to it.

```python
SCORED_PIPE_ERRORS = (
    PiPacketFailure,
    BrokenPipeError,
    ConnectionResetError,
)

def scored_generate(*args, **kwargs):
    try:
        return generate(*args, **kwargs)
    except SCORED_PIPE_ERRORS as error:
        raise CandidateViolation(
            "post-READY scored protocol failure"
        ) from error
```

Use the same tuple in Gate 2A `scored_pong()` and Gate 2B `scored_generate()`. If invalid UTF-8 can
escape `read_frame()` as `UnicodeError`, normalize it to `PiPacketFailure("candidate emitted invalid
JSONL")` inside `read_frame()` so every invalid frame uses the same typed boundary.

For P5 shutdown, classify only the post-READY protocol/exit failures owned by the child:

```python
SCORED_CLOSE_ERRORS = SCORED_PIPE_ERRORS + (subprocess.TimeoutExpired,)

def scored_close_child(process, validator):
    try:
        return close_child(process, validator)
    except SCORED_CLOSE_ERRORS as error:
        raise CandidateViolation(
            "post-READY candidate cleanup failure"
        ) from error
```
Keep `start_p5()` and rebuild `start_child()` outside these wrappers so pre-READY failure remains
`INCONCLUSIVE`.

Replace the current class-wide precedence in both `p5_runner_disposition()` and
`verify_gate2a_result()` with a two-stage adjudication. Reuse the frozen scorer with
`rebuild_ok=True` to adjudicate all primary terminal/marker/health facts before considering any
rebuild outcome:

```python
def p5_primary_disposition(
    terminal, elapsed_ms, *, markers_ok, health_ok,
    candidate_error, observation_error,
):
    if candidate_error is not None:
        return "FAIL"
    if observation_error is not None:
        return "INCONCLUSIVE"
    return p5_result_disposition(
        terminal,
        elapsed_ms,
        markers_ok=markers_ok,
        health_ok=health_ok,
        rebuild_ok=True,
    )

primary = p5_primary_disposition(...)
if primary != "PASS":
    return primary
if rebuild_candidate_error is not None:
    return "FAIL"
if rebuild_observation_error is not None:
    return "INCONCLUSIVE"
return "PASS" if rebuild_ok else "FAIL"
```

This preserves both exception-based primary failures and semantic primary failures such as
wrong/late terminal, invalid markers and failed health. It also prevents a rebuild result from
adjudicating a primary operation whose observation was already invalid. The independent verifier
must compute the same `primary` value from sanitized fields before reading rebuild fields; otherwise
the producing runner and consuming receipt can disagree.

Add a table-driven test with at least these rows:

| Primary stage | Rebuild stage | Expected P5 |
| --- | --- | --- |
| candidate exception | observation invalid | `FAIL` |
| wrong/late terminal, invalid markers or failed health | observation invalid | `FAIL` |
| observation invalid or early-result packet defect | any rebuild outcome | `INCONCLUSIVE` |
| primary PASS | rebuild candidate violation | `FAIL` |
| primary PASS | rebuild observation invalid | `INCONCLUSIVE` |
| primary PASS | protocol-valid but unhealthy rebuild | `FAIL` |
| primary PASS | healthy rebuild | `PASS` |

Patch the real wrapper dependencies for `BrokenPipeError`, `ConnectionResetError`, PING pipe
closure and `subprocess.TimeoutExpired`; assert `CandidateViolation` and final FAIL. Separately
inject an `OSError` into a pre-READY/probe/sampler call and assert that it never enters these scored
wrappers and remains `INCONCLUSIVE`.

**Closure evidence**: scheduling a candidate pipe closure before versus after request write cannot
change FAIL to INCONCLUSIVE, and a later invalid observation cannot erase a prior authenticated
candidate failure.

## 5. Experimental Verifiability of the Proposed Solution

The reference `Condition` handshake and stage-aware precedence above were executed in an independent
workstation prototype during this review. The lifetime experiment blocked the native call, started
conversation finalization concurrently, and rejected any close before the native call was released.
Both success and injected-failure branches completed without deadlock:

```text
native_failure=false events=native_cancel_once closed_after_call=true cancel_calls=1
native_failure=true events=native_cancel_failed closed_after_call=true cancel_calls=1
```

The corrected two-stage precedence table was also executed directly:

```text
primary FAIL + rebuild observation           => FAIL
primary FAIL + rebuild candidate             => FAIL
primary INCONCLUSIVE + rebuild candidate     => INCONCLUSIVE
primary PASS + rebuild candidate             => FAIL
primary PASS + rebuild observation           => INCONCLUSIVE
primary PASS + unhealthy rebuild             => FAIL
primary PASS + healthy rebuild               => PASS
```

This confirms that the solution itself is implementable, terminates under both native outcomes, and
has an experimentally distinguishable success/failure signal. It does not claim that the current
production source is fixed; the current source still reproduces R3-F1/F2.

The replacement implementation must turn the prototype into repository tests with these controlled
barriers and assertions:

1. **Cancel-success lifetime experiment**: block inside fake `cancel_process()`, signal that the
   worker reached finalization, assert `conversation.closed is False`, release native cancel, then
   require exactly one success marker, no failure marker, one close and no live threads.
2. **Cancel-failure experiment**: inject native exception, require zero success markers, one failure
   marker, eventual one close and P5 FAIL. The test must not treat a timer-thread exception or marker
   emitted before the call as success.
3. **Completion-first control**: release completion arbitration before cancel; require one completed
   chunk, zero success/failure native-cancel markers and boundary TIMEOUT mode.
4. **Protocol exception matrix**: inject `BrokenPipeError` and `ConnectionResetError` at Gate 2A
   GENERATE/PING and Gate 2B GENERATE, plus `TimeoutExpired` at P5 shutdown; require typed
   `CandidateViolation` and final FAIL. Inject pre-READY/probe/sampler `OSError` controls and require
   `INCONCLUSIVE`.
5. **Disposition precedence matrix**: execute every row above through both
   `p5_runner_disposition()` and `verify_gate2a_result()` and require identical results.
6. **Protocol integration experiment**: run the fake backend through `Child` with a short controlled
   outer timer. For cancel-first and completion-first schedules, require a correlated `ERROR/TIMEOUT`
   terminal, valid marker mode, same-child PING/generation health, fresh rebuild health and clean
   shutdown. This closes the gap between backend-only marker tests and the actual protocol terminal.

All workstation experiments are definition/implementation evidence only. After reviewer approval
and an exact milestone commit, the physical Pi run remains necessary to validate the real
LiteRT-LM native call and earn P5/P10B credit; the workstation experiment does not substitute for
that hardware evidence.

**Sufficiency commitment for the Developer**:

Within the frozen review boundary, the reference implementation and six experiments above are
sufficient to pass the next development-readiness review. Approval does not depend on a particular
spelling of helper names, but it does require all observable invariants below:

| Finding | Sufficient closure gate |
| --- | --- |
| R3-F1 | Native cancel and conversation close cannot overtake each other; success is recorded only after one completed native call; native failure is separately recorded and cannot PASS; cancel-first and completion-first both pass the full protocol integration experiment. |
| R3-F2 | Every listed post-READY pipe/shutdown fault is typed as candidate FAIL; unrelated environment/probe faults remain INCONCLUSIVE; complete primary-stage adjudication precedes rebuild adjudication; runner and independent verifier agree for every matrix row. |
| Regression/identity | All existing and new Gate 2 tests, all Gate 1 regressions, compilation, diff check and both updated lock checks pass on one exact worktree. |

Meeting this table closes every currently known review blocker. The next review will verify these
declared invariants and will not add model-substitution, Audio-quality, full-integration or other
scope-expanding requirements.

## 6. Single-Round Resubmission Gate

Keep R2-F3 and original F1/F5 unchanged. Submit one narrowly bounded replacement for the two
findings above, update both locks, and rerun:

1. all 55 existing Gate 2 tests plus the native-lifetime and scored-exception/precedence tests;
2. all 136 Gate 1 regressions;
3. bytecode compilation, `git diff --check` and both lock-digest checks; and
4. targeted re-review against one exact worktree and lock pair.

No milestone commit/push, physical-Pi credit execution, benchmark publication or candidate proposal
is approved by this review. No other unfinished review item remains outside R3-F1 and R3-F2.
