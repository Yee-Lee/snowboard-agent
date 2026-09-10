---
requestor: Designer
owner: Tester
status: Resolved
severity: Blocking
---

# TR_spec_M4B_V — foundation revision coverage

- Date: 2026-09-10
- Blocking gate: `M4B-FOUNDATION-REVISION`
- Design authority: [`m4b_foundation_revision`](../implement/m4b_foundation_revision.md)
- Requested outcome: create and self-review an independent foundation test specification before any
  Developer package opens

## Review boundary

This request covers only the Core foundation delta approved through `AR_impl_M4B_III`: four-field
`LLMResponse`, WAKE Conversation readiness, primary/post-action-rest routing, sequential Conversation
replacement, lifecycle proof and affected M1/M2 regression. It does not cover the replacement M4B
prompt/parser, token/KV admission, real LLM child protocol, memory/timing evidence or Pi candidate.

`TR_spec_M4B_IV` and historical M4B tests belong to the retired product package and cannot release
this request. Create a separate current authority such as
`docs/test_spec/test_spec_M4B_foundation.md`; do not copy legacy M4B cases or claim their acceptance.

## Required coverage

Please map every case to an exact design section, risk, deterministic stimulus and observable result:

1. Event schema requires explicit `post_action_route`; old positional construction fails closed.
2. WAKE ack/open complete in both orders; neither alone starts perception, ASR or generation.
3. Interrupt/error/shutdown during open converges before session cleanup or a new wake.
4. `KEEP_NEXT`, `REPLACE_NEXT` and `END_SESSION` each have one route for speak/tool/rest.
5. Final non-empty speech completes before one rest phase; empty end performs exactly one rest.
6. Continuing action error uses `default_perceptions`; final action error still rests and ends.
7. Replacement proves close before open, preserves session/monotonic turn identity, never overlaps
   generations, replays no input and invokes no buffer exit policy.
8. Open/close private notices reject stale session/generation/correlation/task identity.
9. R1, proven R2, repeated R2, explicit R3 and missing-proof/Engine-unusable E1 remain distinct.
10. Done-but-unproven lifecycle operations remain convergence targets; Level 2/recovery/Level 3
    boundaries are observable.
11. Existing M1/M2 entrypoints and full regression remain green without deletion, skip or xfail;
    changed assertions are regression only, not proof that historical acceptance covered new behavior.

Race tests use `asyncio.Event` or explicit barriers, not wall-clock sleeps. Foundation coverage must
not require a real model, Pi, Audio device, network, credential or legacy M4B fixture.

## Minimum response

Tester updates this file to `Revised`, links the exact new test-spec sections/Test IDs, lists the
acceptance commands and reports any design ambiguity as a Blocking finding. Do not edit Designer
authority or open Developer entry. Designer will perform the final mapping check; only then may this
review become `Resolved` and the foundation Developer package be routed.

## Tester response — 2026-09-10 (round 3)

**Status**: `Revised`

### Test specification

[`docs/test_spec/test_spec_M4B_foundation.md`](../test_spec/test_spec_M4B_foundation.md)

### Round 3 corrections (B3/B5 only; B1, B2, B4 remain resolved)

| Finding | Test ID | Change |
| :--- | :--- | :--- |
| B3 — R3 classification | FND-CONV-002 | Applied Designer's exact amendment: R3 explicit USER end/reset now parameterizes the three canonical `END_SESSION` outcomes (cross-referencing FND-ACT-003, `flush_to_wake`); R3 interrupt is `InterruptRequested` (`discard`); shutdown is separately labelled as not-R3 (`discard`, terminate process). Requirement 9 coverage map now includes FND-REP-001 and FND-ACT-003. |
| B5 — Regression proof | FND-REG-001 | (a) Tester created and checked in `docs/test_spec/baselines/m4b_foundation_node_ids.txt` (99 node IDs) before Developer entry. (b) Deletion check uses `comm -23` wrapped in `test ! -s` for fail-closed exit. (c) Replaced `grep -rnP` with AST-based structural anti-weakening guard as `m4b_foundation`-marked pytest test: rejects positional args, `**kwargs`, missing keywords; also scans baseline files for skip/xfail decorators and calls. (d) Runtime regression uses `--strict-markers` + JUnit XML with `failures==0`, `errors==0`, `skipped==0`; xfail/xpass must not appear. Static guard separately prevents dormant skip/xfail. |

### Test IDs (unchanged)

19 Test IDs: FND-EVT-001, FND-EVT-002, FND-WAKE-001, FND-WAKE-002, FND-ACT-001, FND-ACT-002,
FND-ACT-003, FND-REP-001, FND-REP-002, FND-LIFE-001, FND-LIFE-002, FND-LIFE-003, FND-PHASE-001,
FND-R1-001, FND-CONV-001, FND-CONV-002, FND-SM-001, FND-RM-001, FND-REG-001.

### Acceptance commands

Foundation coverage:
```text
pytest -x tests/ -k "m4b_foundation" --timeout=60
```

M1/M2 regression — runtime (FND-REG-001):
```bash
PYTHONPATH=src pytest -x --strict-markers --junit-xml=regression_result.xml \
  tests/milestones/test_m1_foundation.py tests/milestones/test_m2_mock_pipeline.py \
  tests/test_events.py tests/test_state_manager.py tests/test_m2_sm_flows.py \
  tests/test_m2_flows.py tests/test_m2_wrk_003.py --timeout=60
```

M1/M2 regression — node-ID deletion check (FND-REG-001):
```bash
PYTHONPATH=src pytest -o addopts='' --collect-only -q \
  tests/milestones/test_m1_foundation.py tests/milestones/test_m2_mock_pipeline.py \
  tests/test_events.py tests/test_state_manager.py tests/test_m2_sm_flows.py \
  tests/test_m2_flows.py tests/test_m2_wrk_003.py \
  > /tmp/m4b_foundation_post_collection.txt
awk '/::/' /tmp/m4b_foundation_post_collection.txt | LC_ALL=C sort -u \
  > /tmp/m4b_foundation_post_nodes.txt
comm -23 docs/test_spec/baselines/m4b_foundation_node_ids.txt \
  /tmp/m4b_foundation_post_nodes.txt > /tmp/m4b_foundation_missing_nodes.txt
test ! -s /tmp/m4b_foundation_missing_nodes.txt
```

Structural anti-weakening guard (FND-REG-001): implemented as `m4b_foundation`-marked pytest test
(AST-based `LLMResponse` call-site check + skip/xfail scan); included in the foundation coverage
command above.

### Baseline artifact

[`docs/test_spec/baselines/m4b_foundation_node_ids.txt`](../test_spec/baselines/m4b_foundation_node_ids.txt)
— 99 node IDs, produced and checked in by Tester before Developer entry.

### Blocking findings

None.

## Designer coverage mapping check — 2026-09-10

**Disposition**: `Rejected`

The Test IDs cover the requested topics by name, but the following contract contradictions and
non-deterministic acceptance gaps prevent this coverage from releasing the foundation package.

### B1 — WAKE coverage conflates producer wiring with the readiness gate

- **Basis / location**: design §4 requires lifecycle late-fill before the one-time input-producer arm;
  §5.1 instead gates starting a perception worker, listen/ASR or Reasoner generation. The test spec
  `FND-WAKE-001` says to attempt producer arm before readiness and expects the arm to be rejected.
- **Reproducible evidence**: compare `m4b_foundation_revision.md` §4 lines 209–218 and §5.1 lines
  220–233 with `test_spec_M4B_foundation.md` lines 95–98.
- **Expected / actual**: an already wired producer may exist while WAKE waits; no perception task,
  ASR consumption or generation may start. The current case instead requires rejecting producer arm.
- **Impact**: a conforming startup composition could fail the test, or implementation could add an
  unapproved per-session producer-arm mechanism.
- **Preferred fix / minimum acceptance**: replace the case stimulus with held ack/open barriers plus
  pending input, and assert zero perception-task launch, ASR consumption and Reasoner calls until the
  full readiness predicate is true. Keep producer-arm ordering only in `FND-LIFE-001`/`FND-RM-001`.

### B2 — Stale-notice observability contradicts the approved lifecycle contract

- **Basis / location**: design §3.3 requires every identity mismatch to log sanitized context and
  drop the notice. `FND-LIFE-002` says stale generation is dropped silently and does not require the
  log for stale correlation or task identity.
- **Reproducible evidence**: compare design lines 183–186 with test-spec lines 284–288.
- **Expected / actual**: session, generation, correlation and task-identity mismatches all produce a
  sanitized log, are dropped and leave the active session/generation unchanged. Only the session case
  currently states the complete observable.
- **Impact**: the suite could accept missing diagnostics or explicitly require behavior contrary to
  authority.
- **Preferred fix / minimum acceptance**: use the same sanitized-log/drop/no-state-change observable
  for all four stale-identity cases, while asserting no sensitive/raw context is logged.

### B3 — The explicit USER reset/end branch of R3 is not tested

- **Basis / location**: design §8 and required coverage item 6 distinguish explicit USER end/reset
  from interrupt. `FND-CONV-002` supplies `InterruptRequested` for both rows.
- **Reproducible evidence**: compare design lines 321–330 and 368–380 with test-spec lines 399–402.
- **Expected / actual**: one deterministic case must stimulate the actual explicit reset/end input,
  and a separate case must stimulate interrupt; both must close the active generation and end the
  Product Session under their defined buffer policy. The current pair only exercises interrupt.
- **Impact**: requirement 9 is mapped as covered while one required R3 entry route remains untested.
- **Preferred fix / minimum acceptance**: replace the first stimulus with the concrete explicit
  reset/end event or API from the foundation contract; if no such concrete seam exists, report that
  design ambiguity here instead of substituting interrupt.

### B4 — `SessionContext` generation expectation is assigned to the wrong lifecycle point

- **Basis / location**: the data-model default is generation `0`, but WAKE entry creates the Product
  Session with generation `1`. `FND-SM-001` labels its stimulus `New Product Session` while expecting
  generation `0`.
- **Reproducible evidence**: compare design §4 lines 194–204 and §5.1 line 224 with test-spec lines
  425–428; `FND-WAKE-001` itself correctly expects generation `1` at WAKE entry.
- **Expected / actual**: an unattached/default `SessionContext` may assert generation `0`; a newly
  created Product Session at WAKE entry must assert generation `1`.
- **Impact**: literal implementation of the spec would make two current Test IDs disagree and could
  reject the approved WAKE algorithm.
- **Preferred fix / minimum acceptance**: split or relabel the default-context case and add the WAKE
  initialization assertion for generation `1`, with no ambiguous `New Product Session` wording.

### B5 — Regression preservation has no executable proof for deletion, skip or xfail

- **Basis / location**: design §10 item 9 and review requirement 11 require all historical M1/M2
  acceptance tests to remain present and run without deletion, skip or xfail. `FND-REG-001` only runs
  files and describes `Grep all`/`Diff` without exact commands, baselines or failure conditions.
- **Reproducible evidence**: test-spec lines 459–480 and the two acceptance commands in the Tester
  response. Ordinary pytest success does not fail merely because a case was skipped or xfailed, and
  it cannot detect removal of individual historical tests.
- **Expected / actual**: acceptance must deterministically fail on a missing historical node ID,
  skip/xfail outcome or remaining non-explicit `LLMResponse` construction. The current commands can
  return success in those states.
- **Impact**: the migration could obtain a false-green result after weakening Accepted M1/M2
  regression evidence.
- **Preferred fix / minimum acceptance**: define the immutable node-ID/count baseline or equivalent
  candidate diff check, an exact no-skip/no-xfail assertion, and the exact call-site scan command and
  failure rule. Keep the named full regression command as the runtime portion.

### Required response

Tester updates the existing test spec and this review, changes status back to `Revised`, and maps the
five corrections to exact cases and acceptance commands. Developer entry remains closed.

## Designer coverage mapping recheck — 2026-09-10 (round 2)

**Disposition**: `Rejected`

| Finding | Disposition | Recheck |
| :--- | :--- | :--- |
| B1 | **Resolved** | `FND-WAKE-001` now holds ack/open barriers with pending input and observes zero perception, ASR consumption and Reasoner calls. Producer wiring remains in lifecycle/RM coverage. |
| B2 | **Resolved** | All four stale identities now require sanitized logging, drop and unchanged active identity. |
| B3 | **Rejected / Revised** | Tester correctly reported that there is no additional reset event, but reclassified normal rest and shutdown as R3. Designer clarified the existing authority below; the spec still needs to apply it. |
| B4 | **Resolved** | Default unattached context generation `0` and WAKE Product Session generation `1` are now distinct cases. |
| B5 | **Rejected / Revised** | The response adds proposed checks, but they do not yet provide an immutable or fail-closed regression proof. |

### B3 remaining correction — classify the existing R3 routes accurately

Designer clarified `m4b_foundation_revision.md` §8 without adding a new event or behavior: explicit
USER end/reset is a Reasoner-produced canonical `END_SESSION` outcome (`speak`, `tool` or `rest`
according to content); interrupt is `InterruptRequested`. Shutdown ends the session but is not R3.

`FND-CONV-002` must therefore stop labelling shutdown as R3 and must not use only `rest + END_SESSION`
as the USER end/reset representative. It may reference/parameterize the three `END_SESSION` cases
already specified by `FND-ACT-003`, but requirement 9's coverage map must make that relationship
explicit. Minimum acceptance is one deterministic R3 mapping for canonical USER `END_SESSION`, one
for interrupt, and a separately labelled shutdown-boundary case.

### B5 remaining correction — make the preservation checks present and fail closed

- `docs/test_spec/baselines/m4b_foundation_node_ids.txt` does not exist. Tester must create and own
  the immutable pre-migration node-ID baseline now, before Developer entry opens; assigning its
  creation to Developer during migration would let the candidate define its own baseline.
- The proposed `comm -23` command returns success even when it prints missing node IDs. Wrap it in an
  assertion that exits non-zero on any output, and generate both sorted inputs from node-ID-only
  records rather than pytest summaries or warnings.
- The proposed `grep -rnP 'LLMResponse\(\s*"'` only finds a same-line string-literal first argument.
  It demonstrably misses the current positional-variable construction in
  `tests/test_state_manager.py:68` and any multiline/aliased call. Use an AST-based assertion (or an
  equivalently complete enumerated call-site baseline) that rejects every positional argument and
  requires explicit `action_kind`, `action_payload`, `post_action_route` and `next_perceptions`
  keywords.
- JUnit `skipped=0` detects executed skips/xfails, but the spec also declares every historical
  `@pytest.mark.skip`, `@pytest.mark.xfail`, `pytest.skip()` or `pytest.xfail()` to be a failure without
  providing the static assertion. Add the executable check or narrow the claim to an authority-
  compliant candidate diff inspection with an exact failure rule.
- A zero-match `grep` exits with status 1, opposite to a normal acceptance-command success. Any
  retained grep must be wrapped so the compliant state exits 0.

### Required response for round 3

Tester corrects only B3/B5 in the existing test spec and review, checks in the pre-migration
baseline, and changes the review back to `Revised`. B1, B2 and B4 remain closed; Developer entry and
the cognition/product package remain closed.

## Exact amendments for Tester round 3

Apply the following text directly; do not reinterpret it as a new design choice.

### 1. Replace the R3 rows in `FND-CONV-002`

```markdown
| R3 — explicit USER end/reset | Parameterize the canonical Reasoner outcomes `speak + END_SESSION + ()`, `tool + END_SESSION + ()`, and `rest + END_SESSION + ()` for an explicit USER end/reset intent | Complete the selected primary/rest phases exactly as FND-ACT-003 specifies; close the active generation; end the same Product Session; `flush_to_wake`; return to IDLE only after all proofs |
| R3 — interrupt | `InterruptRequested` during an active Conversation | Close the active generation; end the Product Session; `discard`; return to IDLE only after all proofs |
| Shutdown boundary — not R3 | `ShutdownRequested` during an active Conversation | Close the active generation; end the Product Session; `discard`; terminate the process only after all proofs |
```

Replace requirement 9's coverage-map row with:

```markdown
| 9. R1, proven R2, repeated R2, explicit R3, missing-proof/Engine-unusable E1 distinct | FND-R1-001, FND-REP-001, FND-REP-002, FND-ACT-003, FND-CONV-002 |
```

### 2. Create the pre-migration node-ID baseline now

Run from the repository root in the project test environment. The `-o addopts=''` is required:
without it, the configured `-q` combines with the command-line `-q` and prints file counts rather
than node IDs.

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

Tester checks in the resulting 99-line baseline as part of the current specification revision,
before Developer entry opens.

### 3. Replace the post-migration deletion check

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

### 4. Replace the grep scan with a structural guard

Add this exact case to `FND-REG-001`:

```markdown
| Structural anti-weakening guard | Parse every `*.py` under `src/` and `tests/` with `ast`; resolve direct or imported aliases of `LLMResponse`; inspect every matching `ast.Call`. Also parse the seven baseline regression files for skip/xfail decorators and calls. | Every `LLMResponse` call has `args == []`, no `**kwargs`, and explicit `action_kind`, `action_payload`, `post_action_route`, `next_perceptions` keywords. The baseline files contain no `pytest.mark.skip`, `pytest.mark.xfail`, `pytest.skip()` or `pytest.xfail()`. Report every violation as `path:line`; any violation fails. |
```

Implement that case as a `m4b_foundation`-marked pytest test. This replaces
`grep -rnP 'LLMResponse\(\s*"'`; do not retain the grep command as an acceptance gate.

### 5. Keep the runtime regression check

Keep the existing full regression pytest command and parse its JUnit XML. Acceptance requires total
`failures == 0`, `errors == 0`, and `skipped == 0`; pytest's xfail/xpass outcomes must not appear.
The static guard above separately prevents dormant skip/xfail code from evading the runtime result.

## Designer coverage mapping check — 2026-09-10 (round 3)

**Disposition**: `PASS / Resolved`

- B1, B2 and B4 remain resolved with no direct regression.
- B3 is resolved: `FND-CONV-002` parameterizes all canonical USER `END_SESSION` outcomes, separates
  interrupt, labels shutdown outside R3 and maps requirement 9 to `FND-ACT-003` plus the R1/R2/R3/E1
  cases.
- B5 is resolved: Tester owns a sorted, unique 99-node pre-migration baseline; the checked-in file
  exactly matches a fresh collection of the seven regression files. The deletion command fails on
  missing nodes, the structural guard covers positional/aliased calls and dormant skip/xfail, and
  runtime acceptance retains the full named regression suite with JUnit outcome checks.
- Coverage remains limited to `M4B-FOUNDATION-REVISION`; no legacy M4B product acceptance, real
  model, Pi, Audio, network or cognition/product rewrite was imported.

The `M4B-FOUNDATION-REVISION` coverage gate is closed. Developer may implement only the source/docs/
tests inventory in the approved foundation design. Tester verification reopens after a Developer
candidate; the cognition/product rewrite remains closed.
