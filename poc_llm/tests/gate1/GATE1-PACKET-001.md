# GATE1-PACKET-001 — Frozen Ubuntu Candidate Pre-screen

- **Packet ID**: `G1-UBUNTU-PRESCREEN-001`
- **Revision**: `2026-08-17-r1`
- **Status**: `FROZEN SCAFFOLD / EXECUTION NOT AUTHORIZED`
- **Platforms**: Ubuntu x86_64 and Ubuntu aarch64
- **Owner**: POC Test Controller
- **Reviewer**: Technical Lead
- **Approver**: Core Designer
- **Candidate command timeout**: 1800 seconds
- **Terminate grace**: 2 seconds, then SIGKILL and wait
- **Repetitions**: 20 catalog cases × 3 hot repetitions

No Ubuntu benchmark or candidate evidence was produced while preparing this packet.

## Frozen Inputs

The authoritative versions and SHA-256 values are in
`poc_llm/harness/gate1-lock.json`. The catalog contains public synthetic input references and
expected normalized results, not private prompts or raw model output.

## Entry

1. External Gate 0 is recorded complete and Internal M0 is confirmed.
2. Candidate manifests pass `candidate.schema.json`; runtime/model/quantization pairings have
   immutable IDs, exact versions, source/artifact SHA-256, license, offline acquisition and both
   platform commands.
3. Ubuntu x86_64 and native aarch64 owners, clean environments, raw evidence paths, storage and
   download approvals are recorded.
4. Catalog, validator, runner and schemas match the lock file. Any change creates a new packet
   revision and invalidates all affected runs.

## Harness Self-test

From repository root on either Ubuntu platform:

```sh
python3 poc_llm/harness/gate1_validator.py --catalog poc_llm/fixtures/gate1/catalog.json --self-test
```

Expected: exit `0`; JSON `result=PASS`, validator `1.0.0`, zero violations, and catalog SHA-256
`c4b1f29228324848fe5f196a8f6e3e61412daa0ed5fd79ce9c9d04857b4c2796`.

## Candidate Commands

The same command template is frozen for both platforms; only `--platform`, the immutable
candidate manifest and a new operator-approved raw directory differ:

```sh
timeout --signal=TERM --kill-after=5s 1810s python3 poc_llm/tools/run_gate1_prescreen.py --platform ubuntu-x86_64 --candidate-manifest poc_llm/fixtures/gate1/candidates/CAND-ID.json --catalog poc_llm/fixtures/gate1/catalog.json --validator poc_llm/harness/gate1_validator.py --lock poc_llm/harness/gate1-lock.json --raw-dir /approved/raw/G1-RUN-ID
timeout --signal=TERM --kill-after=5s 1810s python3 poc_llm/tools/run_gate1_prescreen.py --platform ubuntu-aarch64 --candidate-manifest poc_llm/fixtures/gate1/candidates/CAND-ID.json --catalog poc_llm/fixtures/gate1/catalog.json --validator poc_llm/harness/gate1_validator.py --lock poc_llm/harness/gate1-lock.json --raw-dir /approved/raw/G1-RUN-ID
```

Before freeze, `CAND-ID`, `G1-RUN-ID` and the absolute raw root are replaced with literal,
validated values. The manifest command is an argv array and is never executed through a shell.

## P2/P3 Expected Results

- Valid cases must return the exact three product keys and the expected `speak/tool/rest` action,
  payload and ordered, deduplicated `listen/read/look` capabilities.
- All 10 failure cases must normalize without raising to apology `speak` with usable `listen`,
  or `rest` when speak/listen is unavailable.
- Every case must pass all three repetitions. Schema/fallback pass rate is 100%; averages cannot
  hide a failed repetition.
- `log_forbidden_hits` must be empty for every run. Any prompt, raw output, payload, credential or
  hidden-context leakage is an immediate `FAIL`.

## Result and Cleanup Rules

- `PASS`: both platforms complete the exact 60-case matrix, hard eligibility/provenance checks,
  validator and cleanup with complete evidence.
- `FAIL`: valid environment shows any mandatory schema, fallback, log, lifecycle, license,
  provenance, offline, command-exit or cleanup violation.
- `INCONCLUSIVE`: wrong architecture, corrupted/missing evidence, runner/tool failure or inability
  to distinguish candidate failure from environment failure.
- `Blocked`: platform, candidate artifact, approval, license or controlled raw location unavailable.
- `Core threshold decision required`: only negotiable performance has complete valid measurements
  but misses the starting target; mandatory failures never use this result.
- A timeout triggers process-group SIGTERM, bounded wait, SIGKILL if needed and wait. Missing exit
  proof is `FAIL`. Raw paths are never reused; cleanup verifies no child/process group remains.

## Fixed Finalist Decision

1. Reject any pairing without `PASS` on both x86_64 and aarch64 mandatory gates.
2. Retain candidates requiring a P4 Core threshold decision, but label the unresolved decision.
3. Rank eligible candidates lexicographically by: lower worst-platform peak RSS, higher
   worst-platform hot tokens/sec, lower worst-platform hot TTFT P95, then candidate ID.
4. Select at most the first two as **proposed Gate 1 finalists**. This is not a Pi provisional
   finalist and never a final winner.
5. If fewer than one eligible pairing remains, submit evidence-backed no-go/change request.

One controlled rerun per candidate/case is allowed after a documented environment correction; the
original result remains. Further reruns require a new packet revision or change request.
