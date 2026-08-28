# REVIEW-LLM-M3-M4-GATE2-DEVELOPMENT-READINESS-R2-001

- **Date**: 2026-08-28
- **From**: Independent Reviewer
- **To**: LLM POC Designer / Technical Lead
- **Status**: `REVISION_REQUIRED / NOT READY FOR IMPLEMENTATION HANDOFF OR PI CREDIT EXECUTION`
- **Reviewed base**: `0638f5ad859627014f7cf0d57882ac394b100466` plus the uncommitted R2 replacement worktree
- **Gate 2A replacement lock SHA-256**: `6b5aa1cad7572cd38304778e2d0a90f30061848727b59db6ddb5b27498c9a4e3`
- **Gate 2B replacement lock SHA-256**: `05c5adfca9d10c3d383a7db51dd2ccfd84d281f8b1b293f33a0e6324f5cad0a1`
- **Review request**: `docs/response/REVIEW-REQUEST-LLM-M3-M4-GATE2-READINESS-R2-001.md`

## 1. Decision and Boundary

The R2 replacement is materially stronger, but it is not yet deterministic or cleanup-safe enough
to hand to Pi execution. The decision is based on three reproducible execution-path defects, not on
new scope or low-value hardening requests.

This review continues to accept the User's prior decisions:

- no hypothetical or adversarial model/Audio artifact substitution checks;
- no additional routine model rehashing beyond the accepted receipt design;
- no real-Audio response-quality, ASR semantic-oracle, TTS quality or complete product-integration
  test; and
- no reopening of the accepted cumulative Gate allocation.

## 2. Verification Performed

- Gate 2 workstation tests: `49 passed`.
- Gate 1 regression tests: `136 passed`; one pre-existing async thread warning was emitted.
- Changed runner/coordinator/adapter/test bytecode compilation: PASS.
- `git diff --check`: PASS.
- Both submitted replacement lock digests match the review request and authenticate the current
  repository artifacts through their lock tests.
- Targeted P5 completion-transition schedule: reproduced an invalid third marker combination.
- Targeted Gate 2B partial-start/stop-failure schedule: reproduced a live owner with no fallback.

The green suites do not close the findings below because their barriers begin after the unsafe
transitions rather than at them.

## 3. Closure Status of the Original Findings

| Original finding | R2 status | Decision basis |
| --- | --- | --- |
| F1 independent fail-closed evidence | `CLOSED` | Both result verifiers recompute dispositions; strengthened schemas and mutation tests reject the reviewed false-PASS cases. |
| F2 failure/invalid-observation separation | `PARTIAL / BLOCKING` | Typed categories exist, but scored post-READY protocol failures still bypass the candidate-failure path. |
| F3 leak and all-domain cleanup | `PARTIAL / BLOCKING` | Leak rules and normal full-start stop fallback are present; partial-start cleanup can still lose every root identity. |
| F4 deterministic P5 timeout | `OPEN / BLOCKING` | The completion event precedes the lock-protected transition, leaving a reproducible scheduler-dependent third mode. |
| F5 data-dependent log hygiene | `CLOSED` | Runtime canaries are scanned in the POC controller/LLM-owned files and only hashes/counts are retained. |

## 4. Blocking Findings

### R2-F1 — P5 completion and timeout arbitration is still non-atomic

**Maps to**: original F4
**Severity**: Blocking

`LiteRtContinuousBackend._chunk()` emits `chunk_completed` while `_state` is still
`ACTIVE_CHUNK` and `_conversation` is still installed. Only the later `finally` block clears the
conversation and changes the state to `BETWEEN_CHUNKS`. A timeout in that window therefore calls
the native cancel for a chunk already declared complete.

The targeted schedule held the `chunk_completed` event, called `cancel()`, then released the worker.
It produced:

```text
state_before_cancel=ACTIVE_CHUNK
cancel_count=1
events=chunk_started,chunk_completed,native_cancel_once,
       conversation_discarded,timeout_between_chunks,continuous_terminal_cancelled
```

This satisfies neither accepted scorer mode: active mode forbids a matching completion, while
between-chunk mode forbids native cancel. The existing test barrier is `_between_chunks_hook`, which
runs only after `_chunk()` has fully returned, so it cannot expose this transition window.

**Required correction**:

1. Add one final lock-protected arbitration after generation/metrics complete and before recording
   chunk completion. If cancel owns the lock first, the chunk must remain incomplete and take the
   one-native-cancel mode. If completion owns it first, it must atomically clear the active
   conversation/change to `BETWEEN_CHUNKS`, then record completion and take the zero-native-cancel
   mode.
2. Do not emit `chunk_completed` before that arbitration, and do not rely on a later `finally` state
   change to define the timeout mode.
3. Add a deterministic test that pauses immediately before this arbitration and another immediately
   after it. Assert the complete scorer marker set, terminal TIMEOUT window, same-child health,
   rebuild and cleanup in both schedules.

**Closure evidence**: repeated controlled arbitration on both sides can produce only the two frozen
valid modes; the reproduced completed-plus-native-cancel combination is impossible.

### R2-F2 — Actual scored protocol failures do not use the typed result matrix

**Maps to**: original F2 and F4
**Severity**: Blocking

The shared exception classes and abstract matrix are sound, but the runners do not translate the
actual scored request path into those classes:

- Gate 2A P5 `generate()` raises `PiPacketFailure` for deadline, EOF, invalid JSONL or an invalid
  protocol frame. The catch stores `p5_observation_error`, and the scorer unconditionally returns
  `INCONCLUSIVE`. Therefore the frozen no/late-terminal P5 failure can never reach the existing
  `NO_TERMINAL -> FAIL` scoring test through the real runner path.
- Gate 2B has the same split. `CombinedLlmDomain` maps a returned bad terminal to
  `CandidateViolation`, but a post-READY LLM deadline/EOF/invalid frame escapes as
  `PiPacketFailure`; the outer runner relabels it `EnvironmentInvalid`, making an entered combined
  run `INCONCLUSIVE` rather than a P10B candidate failure.
- P5 rebuild exceptions take the opposite blanket path: any caught exception makes `rebuild_ok`
  false and therefore P5 FAIL, even when the exception is an invalid environment/evidence
  observation. This is still category conflation, just in the other direction.

This finding concerns ordinary candidate crash/hang/protocol behavior under the frozen POC method;
it does not assume malicious model replacement.

**Required correction**:

1. Translate only post-READY, scored candidate timeout/EOF/invalid-frame outcomes into a typed
   `CandidateViolation` (or a typed subclass). Keep preflight, identity, sampler, probe, filesystem
   and evidence failures INCONCLUSIVE.
2. Make P5 no/late terminal use its frozen FAIL rule through the actual runner path. Classify
   same-child/rebuild failures by their typed cause rather than by one blanket boolean or catch.
3. Add runner-path fault tests, not only direct disposition-function tests: P5 no terminal and late
   terminal must FAIL; a P5 infrastructure/probe failure must remain INCONCLUSIVE; an entered Gate
   2B LLM request deadline/EOF/invalid frame must FAIL P10B; sampler/probe failure must remain
   INCONCLUSIVE.

**Closure evidence**: the actual runner calls produce the same disposition as the typed matrix for
each injected fault, with no fabricated terminal object used to bypass `generate()`/`read_frame()`.

### R2-F3 — Partial startup loses owner roots before cleanup

**Maps to**: original F3
**Severity**: Blocking

The coordinator appends a domain only after `start()` returns, and does not populate
`started_roots` until all four starts and the full residency check succeed. If a later domain start
fails, earlier successfully started domains enter cleanup with `root=None`. If one of their
cooperative stops also fails, the fallback is explicitly skipped because it has no root PID.

A targeted schedule with VAD started, ASR start failing and VAD stop failing produced:

```text
started_roots={}
vad_alive=True
forced=[]
cleanup_proof.root_pid=None
cleanup_proof.process_group_absent=False
```

The existing per-domain stop-failure test starts all four domains successfully first, so roots have
already been captured and this path is not covered. On the real runner, `combined_entered` also
remains false before sampler start, so the partial cleanup proof is not copied into the sanitized
result.

**Required correction**:

1. Track every attempted domain before awaiting `start()`. Immediately after each successful start,
   validate and persist its root before starting the next domain.
2. If `start()` raises after partially creating an owner, query its residency identity and include
   any live root in the same reverse cooperative/fallback cleanup path.
3. Never skip bounded fallback for a live POC-owned domain merely because full four-domain residency
   was not reached. Preserve partial cleanup proof even when sampling never started.
4. Add a deterministic partial-start test: a later start fails, an earlier stop fails, the earlier
   root is force-cleaned and all owners are absent. Add the start-raises-after-becoming-live variant
   if the domain contract permits partial allocation.

**Closure evidence**: every startup position combined with an injected stop failure ends with all
attempted/started POC-owned groups absent and a sanitized non-PASS cleanup proof.

## 5. Single-Round Resubmission Gate

Do not change F1/F5 or expand the Audio/model scope. Submit one replacement that addresses only the
three findings above, updates both locks and removes the premature claims of an atomic P5 state
machine and complete all-domain cleanup until the new tests pass.

Before re-review, provide:

1. the existing 49 Gate 2 tests plus the new transition, actual-runner-classification and
   partial-start cleanup tests;
2. all 136 Gate 1 regressions;
3. bytecode compilation, `git diff --check` and lock-digest verification; and
4. one exact clean replacement commit and lock pair, with Pi execution still unauthorized.

No physical-Pi credit run, benchmark publication, candidate proposal or implementation handoff is
approved by this review.
