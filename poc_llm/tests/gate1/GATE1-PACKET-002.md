# GATE1-PACKET-002 — Fail-Closed Ubuntu Candidate Pre-screen

- **Packet ID**: `G1-UBUNTU-PRESCREEN-002`
- **Revision**: `2026-08-18-r2`
- **Status**: `FROZEN EXECUTABLE PACKET / EXECUTION NOT AUTHORIZED`
- **Platforms**: Ubuntu x86_64 and native Ubuntu aarch64; both mandatory
- **Owner / reviewer / approver**: POC Test Controller / Technical Lead / Core Designer
- **Outer timeout**: 1810 seconds; candidate budget 1800 seconds
- **Request bounds**: READY 10s, normal frame 2s, P5 probe 16s, TERM grace 2s then KILL/wait
- **P2/P3 matrix**: 20 catalog cases × 3 repetitions
- **P4 matrix**: 3 warm-up + 3 cold timings + 20 hot samples

This packet supersedes `GATE1-PACKET-001`. Preparing and testing it did not run an Ubuntu
candidate benchmark, a Pi gate, or produce candidate evidence.

## Frozen Inputs and Identity

`poc_llm/harness/gate1-lock.json` is the sole lock. Before candidate launch, the runner verifies
the SHA-256 of the catalog, candidate schema, validator, runner, result schema, selection schema
and selector. It validates the candidate manifest against the locked schema, then binds the run ID,
platform, canonical argv checksum, manifest checksum and runtime/model/config paths and checksums.
Paths escaping the repository fail closed. The command is an argv array and never uses a shell.

Candidate manifests also bind exact version, quantization, license, offline capability, aarch64
compatibility and both platform commands. The same manifest SHA and pairing revision must appear in
both platform results. Every runner result is validated against the locked result schema before it
is emitted; the aggregate decision is validated against the locked selection schema.

Python dependencies are frozen in `poc_llm/requirements-gate1.lock`. Raw stderr and any future
candidate-private material stay in the unique operator-approved raw directory outside Git.

## Entry Conditions

1. Gate 0 and Internal M0 entry requirements are recorded; candidate execution is separately
   authorized by the designated owners.
2. Candidate/license/provenance review approves the exact manifest and artifacts. Model weights,
   private prompts and raw model output remain outside Git.
3. Both clean Ubuntu platform owners and unique raw paths are recorded. Cross-emulation cannot
   replace native aarch64 evidence without written Core approval.
4. Repository HEAD, lock and all locked artifacts match; any change requires a new packet revision
   and invalidates affected runs.

## Executable Commands

Run from repository root after replacing only the literal approved manifest, run ID and raw path:

```sh
python3 -m pip install -r poc_llm/requirements-gate1.lock
timeout --signal=TERM --kill-after=5s 1810s python3 poc_llm/tools/run_gate1_prescreen.py --platform ubuntu-x86_64 --run-id G1-RUN-X86-ID --candidate-manifest poc_llm/fixtures/gate1/candidates/CAND-ID.json --lock poc_llm/harness/gate1-lock.json --raw-dir /approved/raw/G1-RUN-X86-ID
timeout --signal=TERM --kill-after=5s 1810s python3 poc_llm/tools/run_gate1_prescreen.py --platform ubuntu-aarch64 --run-id G1-RUN-ARM-ID --candidate-manifest poc_llm/fixtures/gate1/candidates/CAND-ID.json --lock poc_llm/harness/gate1-lock.json --raw-dir /approved/raw/G1-RUN-ARM-ID
python3 poc_llm/tools/select_gate1_finalists.py --lock poc_llm/harness/gate1-lock.json --results /approved/sanitized/CAND-ID-x86.json /approved/sanitized/CAND-ID-arm.json
```

The output of each runner is the sanitized result to store through the controlled evidence path.
The raw directory must not exist before the run and must never be reused.

## Portable Gate Execution

| Gate | Executed proof and fail-closed rule |
| --- | --- |
| P1 | Launch exact argv in a new process group; READY within 10s must echo candidate and runtime/model/config hashes; PING/PONG and SHUTDOWN/ACK framing; exit 0 and no process group. |
| P2/P3 | Runner issues all 20 fixture IDs × 3 repetitions itself. The locked validator requires exact product JSON, expected valid/fallback behavior and no forbidden log hits. Candidate-supplied prebuilt bulk JSON is not accepted. |
| P4 | Runner sends frozen `public.synthetic.benchmark.fixed-v1`, input envelope 128 tokens, max output 16, temperature 0; records 3 warm-up, 3 cold and 20 hot wall-clock/TTFT/token/RSS samples plus P50/P95. |
| P5 | `TIMEOUT_PROBE` binds 15000ms; runner-observed elapsed must be 14.5–16s, response must return `ERROR/TIMEOUT` + READY, and a following PING must succeed. |
| P6 | A `START_CANCEL_PROBE` must enter GENERATING; the separate CANCEL for the bound operation ID must return `CANCELLED` + READY within runner-observed 500ms. Unsupported native cancel is `Conditional escalation`, never silently PASS. |
| P8 | Five sequential probes use distinct current markers; each response must echo only the current marker, deny previous-marker influence and return READY. |
| P11 | Locked manifest/schema, license/provenance fields, exact artifact/config checksums, platform command and READY identity must all agree. |

P4 starting targets are TTFT P95 ≤2.5s and effective generation throughput P50 ≥4.0 tok/s.
A complete measurement below target is `Core threshold decision required`, never an automatic PASS
or no-go. Raw/P50/P95 samples remain available for candidate comparison and Core disposition.

## Cleanup and Result Rules

- On success, explicit shutdown must return exit 0; the runner checks that the process group is
  absent. On any failure, timeout or exception it sends group TERM, waits two seconds, sends KILL
  if needed, waits again and records exit/process-group proof.
- `PASS` requires valid identity/schema plus portable hard gates P1/P2/P3/P5/P8/P11, complete P4,
  eligible P6 and cleanup. `FAIL` records a candidate/mandatory violation in a valid environment.
- `INCONCLUSIVE` is limited to an invalid environment/tool/evidence distinction such as wrong host
  architecture. `Blocked` means an approved platform/artifact/owner/path is unavailable.
- `Core threshold decision required` is limited to complete P4 evidence below the frozen starting
  target. Pending or incomplete gates cannot use this outcome.

## Both-Platform Finalist Decision

The selector rejects missing/duplicate platform results, schema-invalid reports, any stable identity
drift, incomplete 60-case/P4 matrices, violations, mandatory gate failure or incomplete exit/cleanup.
Eligible same-pairing results are ranked lexicographically by lower worst-platform peak RSS, higher
worst-platform effective tok/s P50, lower worst-platform TTFT P95, candidate ID and pairing revision.
Only the first two become **proposed Gate 1 finalists**. P4 misses retain their Core-decision label.
Zero eligible pairings produces evidence-backed `FAIL`/no-go. This is neither a Gate 2A provisional
finalist nor a final winner.

## Self-test and False-PASS Regression

```sh
PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-pycache python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet
python3 poc_llm/harness/gate1_validator.py --catalog poc_llm/fixtures/gate1/catalog.json --self-test
```

The first command runs a protocol-complete test double, the exact expected-JSON-printer regression,
both-platform selector simulation and deterministic max-two check only in temporary directories.
The printer must return runner `FAIL`, nonzero exit, complete failure cleanup, and must never appear
in `proposed_finalists`. Synthetic cross-platform copies test aggregation logic only and are not
candidate or platform evidence.
