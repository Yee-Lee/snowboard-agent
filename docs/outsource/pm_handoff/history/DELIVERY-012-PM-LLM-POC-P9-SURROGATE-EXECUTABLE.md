# DELIVERY-012-PM-LLM-POC-P9-SURROGATE-EXECUTABLE

- **Date**: 2026-08-23
- **From**: LLM POC Team (M4b)
- **To**: Core Designer and Audio POC Team (M4a)
- **Status**: `EXECUTABLE CORRECTION / INTAKE AND ACK REQUESTED`
- **Supersedes**: `DELIVERY-P9-SURROGATE-SPEC-001` §3 reference implementation and its
  single-process topology wording
- **Preserves**: the accepted envelope and all no-credit boundaries in
  `RESP-LLM-POC-P9-SURROGATE-ENVELOPE-001`
- **Source branch**: `llm`
- **Source identity**: the immutable commit containing this delivery and the locked files below

## 1. Required disposition

Core should replace the non-executable example in `DELIVERY-P9-SURROGATE-SPEC-001` with the locked
artifact in this delivery and issue one corrected ACK/spec to Audio. Audio should intake this exact
artifact and integrate its protocol into the M4A-P9 reservation runner. No team should independently
reimplement the resource generator or tune its production parameters.

The previous example imported `ProcessPoolExecutor` and defined `_cpu_worker`, but never invoked
either one. It therefore held memory and slept, had no inference trigger, produced no 4-core load,
and did not provide a versioned protocol, checksum lock or executable cleanup proof. That example
cannot satisfy the envelope it declares.

## 2. Locked artifact

| File | Purpose | SHA-256 |
| --- | --- | --- |
| `poc_llm/tools/run_p9_residency_surrogate.py` | executable production surrogate | `311466f963bce806b2c89a1c4f5b3275134312e307386c35631eabfb3d21be76` |
| `poc_llm/schemas/p9_residency_surrogate_protocol.schema.json` | command/event protocol | `d5de8fe4144a6c759445f7e45e8867a6bad928177cb28f96d908bbcd59ddb8fe` |
| `poc_llm/harness/p9-residency-surrogate-lock-v1.json` | profile and artifact checksum lock | `d8310132072e822a316521e3bd1cd21e7f0c8396dd49d82c1c6a64a247b7f7f0` |

Artifact ID is `M4B-P9-RESIDENCY-SURROGATE-001`; protocol version is `1.0`. The production CLI has
no resource override flags. The only alternate profile is explicit `--self-test`, uses 16 MiB and
two short workers, emits `evidence_eligible=false`, and is never valid M4A-P9 evidence.

## 3. Corrected topology and envelope

The independently managed unit is one process group, not one operating-system process:

```text
M4B-P9-RESIDENCY-SURROGATE-001 process group
├── supervisor: allocates, touches and holds 2304 MiB; owns JSONL protocol
└── four transient CPU workers: active together for each 6.0 s INFER phase
```

The workers are fresh `exec` processes, so they do not inherit the supervisor's 2304 MiB anonymous
mapping. All members inherit the supervisor process group, and all transient worker PIDs are emitted
in `INFERENCE_STARTED`. The fixed production profile is:

| Field | Frozen value |
| --- | ---: |
| Held anonymous allocation | `2304 MiB` |
| CPU workers | `4` |
| Earliest READY | `6.0 s` after launch |
| READY deadline | `10.0 s` |
| INFER compute duration | `6.0 s` per trigger |
| Graceful worker cleanup bound | `5.0 s` before kill |
| Required target | Pi 5 4GB, Debian 13 aarch64, `swap=0` |
| Primary capacity gate | `MemTotal - MemAvailable <= 3584 MiB` at every sample |

The executable independently rejects non-Linux/non-aarch64 production launches and nonzero
`SwapTotal`. The Audio outer runner remains responsible for authenticating Pi model/RAM, Debian 13,
power/cooling, offline state and exact artifact hashes before launch.

## 4. Protocol and required Audio integration

Commands are one JSON object per stdin line:

```json
{"op":"PING"}
{"op":"INFER","request_id":"session-001-turn-001"}
{"op":"SHUTDOWN"}
```

Events are one JSON object per stdout line. A valid lifecycle is:

```text
READY -> PONG -> (INFERENCE_STARTED -> INFERENCE_COMPLETE)+ -> SHUTDOWN_ACK
```

Audio must perform the following exact sequence in its versioned M4A-P9 runner:

1. Verify the source commit, lock, executable and schema checksums before launching anything.
2. Verify Pi 5 4GB, Debian 13 aarch64, `swap=0`, offline state, baseline process ownership,
   temperature and throttling.
3. Launch the surrogate as its own process group and require `READY` within 10 seconds.
4. Start process-tree and `/proc/meminfo` sampling at intervals no greater than one second. Preserve
   raw timestamped `MemTotal`, `MemAvailable`, `SwapTotal`, per-PID RSS/PSS, CPU, threads,
   temperature, throttling, audio xruns and workload latency.
5. Send one `INFER` for every simulated LLM turn and run the corresponding Audio workload while
   the four emitted worker PIDs are alive. Require `INFERENCE_COMPLETE` for the same request ID.
6. Apply the accepted M4A-P9 duration/session catalog without changing this resource profile.
7. Send `SHUTDOWN`; require `SHUTDOWN_ACK`; then apply process-group `SIGTERM -> bounded wait ->
   SIGKILL if needed -> waitpid`. Verify every recorded supervisor/worker PID is absent and baseline
   file-descriptor/device ownership is restored.

`sum(RSS)` is diagnostic only and must not be used as the capacity gate. The supervisor mapping is
private and touched; the four workers are independent executables. The primary capacity value is
always `MemTotal - MemAvailable`.

## 5. Decision rules

- `PASS` requires the unchanged artifact, all required Audio workloads while each INFER phase is
  active, every capacity sample at or below 3584 MiB, no OOM/full memory-pressure event, no
  disqualifying xrun/crash, required thermal/session criteria, and zero residue.
- `FAIL` applies to a valid run with any gate breach, missing INFER overlap, worker failure,
  capacity breach, OOM, incomplete Audio workload or residue.
- `Blocked` applies before execution when the exact artifact is unavailable, the platform is not
  Pi 5 4GB/Debian 13 aarch64, `swap != 0`, required Audio inputs are absent, or the lock differs.
- `INCONCLUSIVE` applies only when evidence validity is lost after a run starts and a deterministic
  pass/fail cannot be established.

This remains an Audio POC resource-reservation result only. It cannot produce LLM M4B-P9/P10B,
Gate 2B, final-winner or product-composition credit.

## 6. Deterministic verification completed by LLM POC

```sh
PYTHONPYCACHEPREFIX=/tmp/llm-p9-pycache \
  python3 -m unittest -v poc_llm.tests.gate2.test_p9_residency_surrogate
```

The regression verifies the frozen production profile, absence of operator tuning flags, checksum
lock, schema event set, bounded invalid-command handling, real concurrent worker PIDs in the same
process group, worker disappearance after INFER, clean shutdown and fail-closed off-target launch.
The small self-test is implementation evidence only; no Pi or M4A-P9 result is claimed.

## 7. Requested one-pass ACK

Core is asked to issue one response that:

1. accepts `M4B-P9-RESIDENCY-SURROGATE-001` and supersedes the defective §3 example;
2. confirms the corrected process-group topology and protocol;
3. directs Audio to vendor or copy the exact locked files without semantic changes;
4. confirms the measurement/cleanup sequence and decision rules above; and
5. names any remaining external prerequisite. If none remains, state that Audio M4A-P9 packet
   integration is unblocked without granting execution PASS or LLM Gate 2 credit.
