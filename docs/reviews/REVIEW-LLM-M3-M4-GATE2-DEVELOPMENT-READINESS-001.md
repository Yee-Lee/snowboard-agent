# REVIEW-LLM-M3-M4-GATE2-DEVELOPMENT-READINESS-001

- **Date**: 2026-08-28
- **From**: Independent Reviewer
- **To**: LLM POC Designer / Technical Lead
- **Status**: `REVISION_REQUIRED / PI CREDIT EXECUTION NOT READY`
- **Target commit**: `0638f5ad859627014f7cf0d57882ac394b100466`
- **Gate 2A lock SHA-256**: `36d6447fe040fcb0f9637decba505c58626e1bd3c66a0a626ce275e14bd3e118`
- **Gate 2B lock SHA-256**: `c8f09ed4e8e0f459afa638c99560f8ffe779c9be1c0352be421feb1dc161d346`
- **Review target**: Gate 2A P2/P3/P4/P5/P8 and Gate 2B P9/P10B executable readiness

## 1. Review Boundary and User Decisions

This review independently checks whether the completed Gate 2 development can produce valid,
reviewable POC evidence. It accepts the previously decided cumulative Gate allocation and does not
reopen Gate 1 carry-forward.

The User explicitly narrowed this review as follows:

- Do not add hypothetical or adversarial model/artifact-substitution checks. Existing accepted
  identities, receipts and controlled operator inputs are trusted for this POC.
- Do not require validation of real Audio response quality, ASR semantic accuracy, TTS content
  quality, or full product-level Audio-to-LLM-to-Audio integration. Gate 2B remains limited to the
  POC-owned combined residency, soak, boundary invocation and cleanup goals.
- Do not expand the POC into the production composition root or Audio model selection.

Accordingly, prior suggestions for extra Audio artifact authentication and full semantic
ASR/LLM/TTS correlation are not findings in this review.

## 2. Verification Performed

- Gate 2 workstation tests: `42 passed`.
- Gate 1 regression tests: `136 passed`.
- Gate 2 runner/coordinator/adapter bytecode compilation: PASS.
- Both Gate 2 lock files authenticate their current repository artifacts.
- Worktree was clean before this review document was added.

These results confirm that the current definitions are internally consistent, but the tests do not
yet close the adjudication and failure-path gaps below.

## 3. Required Findings

### F1 — PASS evidence is not independently fail-closed

**Severity**: Blocking

The Gate 2A result schema mainly requires sample counts. It does not require the contents that make
those samples pass: P2 `valid=true`, P3 deterministic fallback, complete P4 metric fields, the P5
marker invariants, or the P8 nonce/history flags. The existing unit test demonstrates this by using
empty objects for P2/P3/P4/P8 samples while still constructing a schema-valid PASS result.

Gate 2B has the same structural weakness: session metrics and owner peaks are weakly constrained,
and cross-field facts such as `session_id == llm.request_id` are enforced only by the producing
runner, not independently recomputed by the consuming receipt verifier.

**Risk**: A runner regression can report `executed_results=PASS` while its samples do not prove the
same result. A schema-valid receipt chain would then authenticate the runner's assertion instead of
the evidence.

**Required correction**:

1. Add pure, independent `verify_gate2a_result()` and `verify_gate2b_result()` functions that
   recompute every P disposition from sanitized samples and cleanup proof.
2. Use the verifier both before writing a PASS result and when Gate 2B consumes the Gate 2A result.
3. Strengthen schemas with the required per-sample fields and constants. Cross-item uniqueness and
   equality rules that JSON Schema cannot express should remain in the independent verifier.
4. Add negative tests for empty samples, duplicate/missing case IDs, false P2/P3/P8 dispositions,
   invalid P5 markers, missing P4 metrics, mismatched session/request IDs and incomplete owner data.

**Closure evidence**: Every mutated evidence example above is rejected even when its top-level
`executed_results` and `result` fields claim PASS.

### F2 — Candidate failure and invalid observation are conflated

**Severity**: Blocking

Gate 2A catches `OSError`, subprocess errors and packet/probe failures inside P2/P4/P5/P8 observation
paths and commonly converts them directly to the corresponding P-item `FAIL`. Gate 2B similarly
maps any exception after combined sampling starts to P10B `FAIL`, including sampler, PSI, thermal,
filesystem or evidence-collection failures.

This conflicts with the governing result semantics: a candidate FAIL requires a valid observation
of a mandatory rule violation; environment, identity, method or evidence failure is
`INCONCLUSIVE`.

**Required correction**:

1. Introduce explicit error categories such as `CandidateViolation`, `EnvironmentInvalid`,
   `EvidenceInvalid`, `PacketDefect` and `CleanupViolation`.
2. Map only model/protocol/resource outcomes observed under a valid method to candidate FAIL.
3. Map sampler/probe/I/O/identity/method failures to INCONCLUSIVE while retaining partial sanitized
   stage and error-type evidence.
4. Add fault-injection tests for thermal, PSI, sampler, protocol I/O and evidence-write failures,
   plus separate tests proving a real terminal/schema/history violation remains FAIL.

**Closure evidence**: The result matrix has one tested example for every error category and no broad
`except` branch can change infrastructure failure into candidate FAIL.

### F3 — P10B does not evaluate leak and does not guarantee cleanup after domain-stop failure

**Severity**: Blocking

The continuous Gate 2B sampler enforces capacity, temperature, PSI, OOM and owner presence, but its
PASS calculation has no session-correlated memory-slope or early/late comparison. A combined run can
therefore grow on every session and still PASS while remaining below 3584 MiB during the 20-session
window.

On an exception, the runner has an explicit final force-cleanup fallback only for the LLM child.
The coordinator attempts to stop all started domains, but a domain whose `stop()` raises has no
second bounded cleanup path and no complete wait/absence proof. This review does not require Audio
semantic validation; it requires only that processes actually started by the POC cannot remain
after success or failure.

**Required correction**:

1. Capture a stable resource point after every session and reuse the already frozen P10A leak
   calculations: sessions 6–20 PSS/system-used slopes `<=4.0 MiB/session`, and sessions 16–20 medians
   no more than `64 MiB` above sessions 1–5. Record combined and per-owner diagnostics without adding
   Audio quality gates.
2. Preserve every started owner root before shutdown. After cooperative reverse stop, apply a
   bounded owner-specific termination/wait fallback to any still-live POC-owned process group.
3. Emit sanitized cleanup proof for VAD, ASR, TTS and LLM and require final process-group absence and
   zero Audio-device owners for PASS.
4. Add a below-capacity linear-leak test and one stop-failure/residue test per domain.

**Closure evidence**: A 5 MiB/session leak fails even when peak memory is below the capacity gate;
every injected stop failure ends with all owned groups absent and a non-PASS result.

### F4 — P5 has a chunk-boundary timeout race

**Severity**: Blocking

The P5 continuous backend clears the active conversation after a chunk closes, then checks the
cancel flag before starting the next chunk. If the 15-second timer fires in that interval, there is
no active conversation to cancel. The current scorer nevertheless requires one native cancel event
and requires `chunk_started > chunk_completed`, so the same candidate behavior can PASS or FAIL
depending only on scheduler timing.

**Required correction**:

1. Make outer-timeout, active-chunk and terminal transitions one lock-protected state machine.
2. Predeclare two valid timeout observations: an active chunk receives exactly one native cancel;
   a between-chunk timeout atomically stops continuation with zero native cancels because no worker
   is active. Both paths must emit TIMEOUT in the fixed window, never emit early RESULT, recover the
   same child, rebuild and leave zero residue.
3. Add a deterministic barrier test that fires the timer after chunk close and before the next chunk
   starts, plus the existing active-generation cancel case.

**Closure evidence**: Repeating both controlled schedules cannot change the P5 disposition through
thread timing alone.

### F5 — LLM-owned log hygiene checks are not data-dependent

**Severity**: Major

The Gate 2 scanners search only a fixed list of generic strings. They do not search for the public
fixture canaries, P8/Gate 2B nonce/trap values or other POC-known boundary markers actually used in
the current run. This can miss a regression that logs a prompt or model response without using one
of the fixed phrases.

This finding is limited to POC controller and LLM-owned logs. It does not require inspection of real
Audio content or validation of Audio-domain logs.

**Required correction**:

1. Build the scan set at runtime from the frozen public fixture canaries and current nonce/trap
   values, keeping the values only in memory.
2. Scan all POC controller and LLM-owned stdout/stderr files; sanitized evidence stores only the
   scan disposition and hashes, never the matched content.
3. Add negative tests that leak a current P2/P8/Gate 2B canary without any existing generic forbidden
   phrase and require P3/P10B to fail as applicable.

**Closure evidence**: Static and runtime-specific leakage are both detected without persisting
prompt, transcript or model text in Git evidence.

## 4. Findings Explicitly Not Raised

To keep the POC focused, the Designer should not add work for the following items in response to
this review:

- adversarial or malicious model/Audio artifact substitution;
- additional routine model rehashing beyond the accepted receipt design;
- ASR recognition-quality or semantic-oracle scoring;
- TTS voice/content-quality scoring;
- proof of product-level end-to-end Audio behavior or production composition-root integration;
- reconsideration of the approved cumulative Gate allocation.

## 5. Single-Round Closure Plan

Submit one bounded replacement revision containing the two runners, P5 adapter, Gate 2B resource
and coordinator helpers, both result schemas, both locks and the new negative tests. The replacement
must keep the same P-item allocation and scope decisions above.

Before targeted re-review, run:

1. all Gate 2 tests, including every new negative/fault-injection case;
2. all Gate 1 regressions;
3. bytecode compilation and lock-digest verification; and
4. a clean-worktree check.

No physical-Pi credit execution should start until these five findings are closed against one exact
replacement commit and lock pair. Workstation tests remain definition evidence only.
