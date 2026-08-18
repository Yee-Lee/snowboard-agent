# GATE1-PACKET-003 — Authenticated Fail-Closed Ubuntu Candidate Pre-screen

- **Packet ID**: `G1-UBUNTU-PRESCREEN-003`
- **Revision**: `2026-08-18-r3`
- **Status**: `FROZEN EXECUTABLE PACKET / EXECUTION NOT AUTHORIZED`
- **Platforms**: Ubuntu x86_64 and native Ubuntu aarch64; both mandatory
- **Owner / reviewer / approver**: POC Test Controller / Technical Lead / Core Designer
- **Outer timeout**: 1810 seconds; candidate budget 1800 seconds
- **Request bounds**: READY 10s, normal frame 2s, P5 probe 16s, group TERM/KILL reconciliation 2s per phase
- **P2/P3 matrix**: locked 20 catalog cases × 3 repetitions
- **P4 matrix**: 3 warm-up + 3 cold + 20 hot samples

This packet supersedes `GATE1-PACKET-002` after Core Revision 002. Preparing and testing it did
not run an Ubuntu candidate benchmark, a Pi gate, or produce candidate evidence.

## Frozen Inputs and Identity

`poc_llm/harness/gate1-lock.json` is the sole lock. The runner verifies the catalog, candidate
schema, validator, runner, result schema, selection schema and selector SHA-256 before launch. It
validates and binds the candidate manifest, run ID, platform, canonical argv, and exact
runtime/model/config paths and checksums. Every sanitized platform result must validate against
the locked result schema.

The selector independently reloads the lock, catalog, validator, schemas and supplied candidate
manifests. Eligible evidence must use real 64-hex identities; fixed identities must equal the
loaded lock, candidate identities and per-platform command must equal the supplied manifest, and
both platforms must use the same manifest/pairing. The aggregate validates against the selection
schema.

Python dependencies are frozen in `poc_llm/requirements-gate1.lock`. Raw stderr stays in the
unique operator-approved raw directory outside Git; only its checksum, scan counts and frozen
sentinel IDs enter sanitized evidence.

## Entry Conditions

1. Gate 0 and Internal M0 entry requirements are recorded; candidate execution is separately
   authorized by the designated owners.
2. Candidate/license/provenance review approves the exact manifest and artifacts. Model weights,
   private prompts and raw model output remain outside Git.
3. Both clean Ubuntu platform owners and unique raw paths are recorded. Cross-emulation cannot
   replace native aarch64 evidence without written Core approval.
4. Repository HEAD, lock and all locked artifacts match. Any change creates a new packet revision
   and invalidates affected runs.

## Executable Commands

Run from repository root after replacing only the literal approved manifests, run IDs and paths:

```sh
python3 -m pip install -r poc_llm/requirements-gate1.lock
timeout --signal=TERM --kill-after=5s 1810s python3 poc_llm/tools/run_gate1_prescreen.py --platform ubuntu-x86_64 --run-id G1-RUN-X86-ID --candidate-manifest poc_llm/fixtures/gate1/candidates/CAND-ID.json --lock poc_llm/harness/gate1-lock.json --raw-dir /approved/raw/G1-RUN-X86-ID
timeout --signal=TERM --kill-after=5s 1810s python3 poc_llm/tools/run_gate1_prescreen.py --platform ubuntu-aarch64 --run-id G1-RUN-ARM-ID --candidate-manifest poc_llm/fixtures/gate1/candidates/CAND-ID.json --lock poc_llm/harness/gate1-lock.json --raw-dir /approved/raw/G1-RUN-ARM-ID
python3 poc_llm/tools/select_gate1_finalists.py --lock poc_llm/harness/gate1-lock.json --candidate-manifests poc_llm/fixtures/gate1/candidates/CAND-ID.json --results /approved/sanitized/CAND-ID-x86.json /approved/sanitized/CAND-ID-arm.json
```

Runner stdout is the sanitized result. The raw directory must not exist before the run and must
never be reused.

## Portable Gate Execution

| Gate | Executed proof and fail-closed rule |
| --- | --- |
| P1 | Launch exact argv in a new process group; READY within 10s echoes candidate and artifact hashes; PING/PONG and SHUTDOWN/ACK framing; leader exit 0 and group absent without cleanup escalation. |
| P2/P3 | Runner drives the exact 20×3 matrix and locked validator. Candidate log claims are ignored. Runner scans captured stderr and protocol frames using frozen catalog patterns; any hit makes P3/overall `FAIL`. |
| P4 | Frozen 128-input/16-output-token envelope, temperature 0. After 3 warm-ups, runner records cold 3 and hot 20 total latency, TTFT, output tokens and derived generation tok/s raw samples plus P50/P95. |
| P5 | `TIMEOUT_PROBE` binds 15000ms; runner observes 14.5–16s, requires `ERROR/TIMEOUT` + READY, then a successful PING. |
| P6 | Separate START/CANCEL frames bind one operation; CANCEL must return `CANCELLED` + READY within runner-observed 500ms. Unsupported native cancel is `Conditional escalation`. |
| P8 | Five probes use unique current markers; each response echoes only the current marker, denies previous influence and returns READY. |
| P11 | Locked schema/license/provenance, artifact/config, manifest, platform command and READY identities must agree. |

Each P4 phase must have all required raw arrays. TTFT/output values must be finite, bounded and
consistent with runner-observed total time. Tok/s is recomputed from raw values; P50/P95 is
recomputed by the selector. Missing, invalid, inconsistent or altered P4 evidence is non-PASS and
cannot use `Core threshold decision required`. A complete valid hot result that misses either
starting target—TTFT P95 ≤2.5s or generation P50 ≥4.0 tok/s—retains that Core-decision disposition.

## Cleanup and Result Rules

- Cleanup is independent of leader state. If any process-group member remains, the runner sends
  TERM, polls for group absence, sends KILL if required, polls again and reaps the leader.
- Any TERM/KILL needed after an otherwise successful shutdown is a lifecycle `FAIL`, even when the
  runner successfully removes the orphan. Sanitized cleanup records leader exit, wait, TERM/KILL
  actions and final group absence.
- `PASS` requires all portable mandatory gates, eligible P6, complete authenticated evidence,
  runner-owned log hygiene and clean exit without escalation.
- `INCONCLUSIVE` remains limited to invalid environment/tool/evidence distinction; `Blocked`
  means an approved platform/artifact/owner/path is unavailable.

## Both-Platform Finalist Decision

The selector rejects missing/duplicate platforms, unavailable/drifted identities, missing or
mismatched manifests, non-lock artifact identities, duplicate/wrong fixture-repetition sets,
validator failures, log hits, incomplete/inconsistent P4 raw data or summaries, result/gate drift,
violations and cleanup escalation. Eligible pairings rank by lower worst-platform peak RSS, higher
worst-platform hot tok/s P50, lower worst-platform hot TTFT P95, candidate ID and pairing revision.
At most two become **proposed Gate 1 finalists**. Zero eligible pairings produces evidence-backed
no-go. This is not a Gate 2A provisional finalist or final winner.

## Official Self-test and Four Negative Regressions

```sh
PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-pycache python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet
PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-pycache python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet.Gate1PacketTest.test_007_a_runner_owns_log_hygiene
PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-pycache python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet.Gate1PacketTest.test_007_b_missing_cold_metrics_is_non_pass
PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-pycache python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet.Gate1PacketTest.test_007_c_cleanup_reconciles_child_after_leader_exit
PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-pycache python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet.Gate1PacketTest.test_007_d_selector_rejects_unavailable_handcrafted_pass
python3 poc_llm/harness/gate1_validator.py --catalog poc_llm/fixtures/gate1/catalog.json --self-test
```

The suite uses only test doubles and temporary directories. It covers the earlier expected-JSON
printer plus Revision 002 A–D: leaked forbidden stderr despite empty claims, absent cold metrics,
leader-first same-group orphan and two handcrafted all-`UNAVAILABLE` PASS reports. Synthetic
cross-platform copies exercise selector logic only; none is candidate or platform evidence.
