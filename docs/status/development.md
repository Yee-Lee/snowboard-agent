# Current development status

- Owner: Developer
- Scope: `M4B-FOUNDATION-REVISION` only
- Entry: **Developer correction complete / ready for Tester verification**
- Completed work package: `CR-M4B-001` and `CR-M4B-002`
- Next owner: **Tester** for independent candidate verification

## Correction result

- `InFlightRecord` now stores request-terminal proof, cleanup proof, Engine usability and Level 2
  force-abort proof independently. Known-unusable Engines always enter Level 2; an empty destroyed
  backend identity fails closed, while a valid stable key is passed unchanged to RM recovery.
- `StateManager._lifecycle_e1()` now advances an existing `conversation_close` convergence to the
  recovery phase, waits for recovery before IDLE, preserves shutdown precedence, and never starts a
  new generation after invalid replacement proof.
- Deterministic cases now cover incomplete and unusable open/close results, exact recovery keys,
  recovery barriers, Level 1/2/3, full continuing/ending action matrices, invalid THINK facts, WAKE
  failure/interruption, stale identity, R1 boundaries, wiring and admission/generation behavior.
- The AST guard now resolves direct imports, import aliases, qualified module attributes and
  transitive simple assignment aliases. Signature failure is tested without a real positional
  constructor call.

## Implemented result

- Added required four-field `LLMResponse`, keyword-only Reasoner generation seam, Conversation
  lifecycle port/private notices, WAKE readiness join, sequential replacement, post-action rest,
  session-end close and done-but-unproven convergence handling.
- Resource Manager now late-fills required lifecycle control after worker/catalog readiness and
  before producer arm; M1/M2 use deterministic lifecycle controls.
- Added `tests/test_m4b_foundation.py` with 68 barrier-driven cases and the AST structural
  anti-weakening guard. All affected construction/signature call sites were migrated without
  deleting, renaming, skipping or xfail-marking baseline nodes.
- Synchronized `ch01_events.md`, `ch02_contracts.md`, `ch04_state_manager.md`,
  `ch05_resource_manager.md` and `ch06_cancel.md`; legacy M4B-MVA session-control text is tombstoned.

Excluded cognition/product implementation, M4B scripts, requirements, prompt/parser policy and real
target behavior were not adopted or redesigned. Their test call sites received compile-only schema /
generation migration where required.

## Test IDs

`FND-EVT-001`, `FND-EVT-002`, `FND-WAKE-001`, `FND-WAKE-002`, `FND-ACT-001`,
`FND-ACT-002`, `FND-ACT-003`, `FND-REP-001`, `FND-REP-002`, `FND-LIFE-001`,
`FND-LIFE-002`, `FND-LIFE-003`, `FND-PHASE-001`, `FND-R1-001`, `FND-CONV-001`,
`FND-CONV-002`, `FND-SM-001`, `FND-RM-001`, `FND-REG-001`.

## Verification evidence

```bash
timeout 60s env PYTHONPATH=src pytest -o addopts='' -q tests/test_m4b_foundation.py
PYTHONPATH=src pytest -o addopts='' --collect-only -q tests/milestones/test_m1_foundation.py tests/milestones/test_m2_mock_pipeline.py tests/test_events.py tests/test_state_manager.py tests/test_m2_sm_flows.py tests/test_m2_flows.py tests/test_m2_wrk_003.py
PYTHONPATH=src pytest -x --strict-markers --junit-xml=/tmp/m4b_foundation_regression_result.xml tests/milestones/test_m1_foundation.py tests/milestones/test_m2_mock_pipeline.py tests/test_events.py tests/test_state_manager.py tests/test_m2_sm_flows.py tests/test_m2_flows.py tests/test_m2_wrk_003.py
timeout 120s env PYTHONPATH=src pytest -o addopts='' -q tests/ -x
python3 -m compileall -q src tests
git diff --check
```

- Focused foundation: **68 passed in 4.72 s**; outer 60-second limit passed.
- Baseline runtime/JUnit: **99 passed**, `failures=0`, `errors=0`, `skipped=0`.
- Anti-deletion: immutable baseline **99**, post-migration baseline nodes **99**, missing **0**.
- Full repository: **770 passed, 2 skipped, 29 deselected** in 74.77 s; both skips are pre-existing
  M3 audio tests whose optional `samplerate` dependency is absent in this environment.
- `python3 -m compileall -q src tests` and `git diff --check`: PASS.

The specified `--timeout=60` pytest option is not available in the current system Python. The dev
extra now declares `pytest-timeout>=2.3`; the focused gate was equivalently bounded by the shell
`timeout 60s`. No implementation blocker remains. Cognition/product rewrite remains closed and is
not claimed by this foundation result.
