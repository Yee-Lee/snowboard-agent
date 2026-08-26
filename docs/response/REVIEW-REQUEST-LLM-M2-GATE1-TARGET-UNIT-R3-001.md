# REVIEW-REQUEST-LLM-M2-GATE1-TARGET-UNIT-R3-001

- **Date**: 2026-08-26
- **From**: LLM POC Technical Lead
- **To**: Independent Reviewer
- **Status**: `TARGETED RE-REVIEW WAIVED BY USER / TEST-ONLY FIX AUTHORIZED`
- **Parent approval**: `ACK-LLM-M2-CUMULATIVE-GATES-R2-APPROVE`
- **Affected scope**: one negative-test setup and its lock entry only
- **Requested disposition**: `APPROVE` or itemized `REVISE`

## Target pre-execution finding

Before changing Pi swap/network or loading a model, the reviewed Gate 1 pure suite was run on the
physical Pi. Thirteen tests passed and
`test_receipt_detects_metadata_drift_without_rehash` failed because the test rewrote an equal-size
temporary file and restored its mode within one Pi `/tmp` timestamp tick. The filesystem reported
the same final stat tuple, so the test did not actually create the drift it expected to detect.

This is a nondeterministic negative-test setup, not a candidate result, runner result, artifact
failure or P1–P12 evidence. Formal Gate 1 did not start.

## Minimal revision

The test now calls `os.utime()` after the same-size rewrite and sets atime/mtime two seconds beyond
the authenticated mtime. The assertion still exercises the same production
`verify_model_receipt()` path and still requires `ArtifactAuthenticationError`; it merely guarantees
that the negative fixture has observable metadata drift on filesystems with coarse timestamp update
behavior.

Changed execution-surface files:

- `poc_llm/tests/gate1/test_gate1_pi_packet_v7.py`
- `poc_llm/harness/gate1-pi-compat-lock-v7.json`

Unchanged: runner, adapter, authentication implementation, schemas, configs, candidates, models,
runtime, thresholds, result semantics and all P work packages.

R3 execution-surface SHA-256:
`568aa791ae572080ede637dc941887d8eee73553539e9ec3dc54a9979f92adc5`.

## Verification

Workstation complete affected suite:

```text
Ran 25 tests in 4.275s
OK
```

Physical Pi isolated debug copy at the R2 source plus only the two changed files:

```text
Ran 14 tests in 0.256s
OK
568aa791ae572080ede637dc941887d8eee73553539e9ec3dc54a9979f92adc5  gate1-pi-compat-lock-v7.json
```

The temporary Pi debug copy was removed afterward. The reviewed checkout remains at
`b5690bbbef50ce37af356fd29b88ab920207c38e`, clean and unexecuted.

## Required judgment

Confirm that the deterministic timestamp drift preserves the originally approved negative-test
intent and that no production/acceptance behavior changed. `APPROVE` authorizes an append-only R3
candidate commit; formal Pi execution still requires that exact new SHA to be pushed and checked out.

## User disposition

The User explicitly authorized direct commit and Gate 1 continuation after reviewing the explanation
that this is a deterministic negative-fixture correction only. No additional reviewer round is
required. The append-only R3 SHA and replacement execution-surface digest must still be pushed,
relayed to Core and matched on the Pi before formal execution.
