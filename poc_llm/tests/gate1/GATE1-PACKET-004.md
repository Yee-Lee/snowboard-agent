# GATE1-PACKET-004 — x86 Full Pre-screen and Product-Pi Compatibility

- **Packet ID**: `G1-X86-PI-COMPAT-004`
- **Revision**: `2026-08-19-r4`
- **Status**: `FROZEN REPLACEMENT PACKET / CORE INTAKE PENDING / REAL EXECUTION NOT AUTHORIZED`
- **x86 platform**: Ubuntu 24.04 x86_64 full portable pre-screen
- **Compatibility platform**: Raspberry Pi 5 4GB / Debian 13 aarch64, bounded try-run only
- **Owner / reviewer / approver**: POC Test Controller / Technical Lead / Core Designer
- **x86 outer timeout**: 1810 seconds; candidate budget 1800 seconds
- **Pi bounds**: offline install 300s, model READY 180s, request 30s, bounded group cleanup
- **P2/P3 matrix**: locked 20 catalog cases × 3 repetitions
- **P4 matrix**: 3 warm-up + 3 cold + 20 hot samples

This packet implements the approved 2026-08-19 contract revision and
`DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CHANGE-ACK-001`. It replaces
`G1-UBUNTU-PRESCREEN-003` only after Core accepts the returned exact SHA. Packet 003 remains
historical and must not be used for new revision-004 evidence.

## Frozen identity

`poc_llm/harness/gate1-lock-v4.json` is the sole revision-004 lock. It authenticates:

- candidate and acquisition schemas;
- catalog and validator;
- x86 wrapper and frozen portable runner core;
- Pi compatibility runner;
- separate x86, Pi compatibility and aggregate selection schemas;
- two-stage selector and Gate 2 carry-over guard.

One candidate ID/pairing revision binds one logical runtime version/source SHA-256, model,
quantization, config and protocol identity. The acquisition manifest separately binds the exact x86
and Pi runtime/dependency artifacts and install commands. Platform-native SHA-256 values may differ;
the logical candidate identity may not.

## Stage 1 — Ubuntu 24.04 x86_64 full pre-screen

For every approved candidate, the x86 runner executes the frozen portable P1/P2/P3/P4/P5/P6/P8
subset and P11 provenance checks. It retains the existing fail-closed rules for authenticated
identity, runner-owned log scanning, complete cold/hot P4 samples, bounded timeout/cancel,
history isolation, shutdown and process-group cleanup.

P4 is mandatory evidence completeness and x86 candidate-comparison data. It does not establish Pi
acceptance performance. The runner command is:

```sh
timeout --signal=TERM --kill-after=5s 1810s \
  python3 poc_llm/tools/run_gate1_x86_prescreen_v4.py \
  --run-id G1-X86-RUN-ID \
  --candidate-manifest poc_llm/fixtures/gate1/candidates/CAND-ID.json \
  --lock poc_llm/harness/gate1-lock-v4.json \
  --raw-dir /approved/raw/G1-X86-RUN-ID
```

The raw directory must not exist before execution and may not be reused.

## Stage 2 — immutable x86 preselection

The selector authenticates all candidate manifests, acquisition manifests and x86 results, then
ranks eligible candidates once by lower x86 peak RSS, higher hot generation P50, lower hot TTFT P95,
candidate ID and pairing revision. It emits at most two preselected candidates before any Pi run:

```sh
python3 poc_llm/tools/select_gate1_finalists_v4.py \
  --stage preselect --selection-cycle-id G1-CYCLE-ID \
  --lock poc_llm/harness/gate1-lock-v4.json \
  --candidate-manifests poc_llm/fixtures/gate1/candidates/CAND-A.json poc_llm/fixtures/gate1/candidates/CAND-B.json \
  --x86-results /approved/sanitized/CAND-A-x86.json /approved/sanitized/CAND-B-x86.json \
  > /approved/sanitized/G1-CYCLE-ID-preselection.json
```

The preselection file is immutable input to the Pi runner and final selector. Pi `FAIL`,
`INCONCLUSIVE` or missing evidence never permits third-ranked backfill in the same cycle. A new
cycle/revision and written authorization are required to change the Pi run set.

## Stage 3 — product-Pi compatibility try-run

Only preselected candidates may run `G1-PI-COMPAT-004`. The runner requires the product Raspberry
Pi 5 4GB / Debian 13 aarch64, exact clean POC SHA, approved fresh raw/isolated paths, acquired
aarch64 bundle checksums and an operator-provided network-disabled proof. It executes isolated
offline install/import, exact runtime/model/config READY, PING, one minimal deterministic generation,
SHUTDOWN ACK, exit `0`, orphan `0` and isolated-environment cleanup.

```sh
python3 poc_llm/tools/run_gate1_pi_compat_v4.py \
  --selection-cycle-id G1-CYCLE-ID --run-id G1-PI-RUN-ID \
  --candidate-manifest poc_llm/fixtures/gate1/candidates/CAND-ID.json \
  --preselection /approved/sanitized/G1-CYCLE-ID-preselection.json \
  --lock poc_llm/harness/gate1-lock-v4.json \
  --network-disabled-proof /approved/raw/network-disabled-proof.json \
  --raw-dir /approved/raw/G1-PI-RUN-ID \
  --isolated-dir /approved/isolated/G1-PI-RUN-ID
```

Pi compatibility outcomes are `PASS`, `FAIL` or `INCONCLUSIVE` only. Swap, memory, disk and elapsed
values are informational. A compatibility result is not an M4B-P1–P12, performance, resource,
thermal, offline-product, provisional-finalist or winner result.

## Stage 4 — final Gate 1 proposal

The final selector recomputes the x86 ranking, requires the exact preselection file, rejects Pi
evidence for any non-preselected candidate and retains only Pi compatibility `PASS` candidates:

```sh
python3 poc_llm/tools/select_gate1_finalists_v4.py \
  --stage final --selection-cycle-id G1-CYCLE-ID \
  --lock poc_llm/harness/gate1-lock-v4.json \
  --candidate-manifests poc_llm/fixtures/gate1/candidates/CAND-A.json poc_llm/fixtures/gate1/candidates/CAND-B.json \
  --x86-results /approved/sanitized/CAND-A-x86.json /approved/sanitized/CAND-B-x86.json \
  --preselection /approved/sanitized/G1-CYCLE-ID-preselection.json \
  --pi-results /approved/sanitized/CAND-A-pi.json /approved/sanitized/CAND-B-pi.json
```

At most two candidates can be proposed. Zero retained candidates is an evidence-backed no-go or
change-request outcome, not authorization to run a third candidate.

## Gate 2 non-inheritance

Gate 2A requires a new packet, run ID and evidence namespace, the same accepted candidate identity,
Pi `swap=0`, and complete P1–P8/P10A/P11/P12 execution. `run_m4b_gate.py` rejects any Gate 1 packet
ID, run ID or evidence namespace supplied as Gate 2 input. Revision-004 Pi compatibility evidence
cannot be copied, renamed or credited to Gate 2A.

## Official deterministic regressions

```sh
PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-v4-pycache \
  python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet_v4
PYTHONPYCACHEPREFIX=/tmp/llm-poc-g1-v3-pycache \
  python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet
python3 poc_llm/harness/gate1_validator.py \
  --catalog poc_llm/fixtures/gate1/catalog.json --self-test
```

Revision 004 regressions cover x86 max-two preselection, Pi PASS filtering, Pi FAIL/INCONCLUSIVE,
third-candidate backfill, forged/missing identity, unapproved platform, incomplete P4 arrays,
dirty/reused raw path, Pi cleanup/orphan failure and Gate 1-to-Gate 2 evidence carry-over. All test
artifacts are deterministic doubles and are never candidate or hardware evidence.

## Authorization boundary

Core currently authorizes repository revision and deterministic regression only. Runtime/model
download, artifact acquisition/transfer/install, real x86 execution, Pi compatibility execution,
network switching, privilege changes and Gate 2A remain separately unauthorized.
