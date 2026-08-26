# RESP-LLM-POC-P9-SURROGATE-EXECUTABLE-001

- **Date**: 2026-08-23
- **From**: Core Designer
- **To**: LLM POC Team (M4b) / Audio POC Team (M4a)
- **Status**: `ACCEPTED — M4A-P9 AUDIO INTEGRATION UNBLOCKED`
- **Subject**: Acceptance of M4B-P9-RESIDENCY-SURROGATE-001 executable
- **Reference**: `DELIVERY-012-PM-LLM-POC-P9-SURROGATE-EXECUTABLE`, `P9-SURROGATE-SOURCE-IDENTITY-001`
- **Source Commit Reviewed**: `f18f823146727b50cb3ef15e9e14b51983643406`

## 1. Acceptance of Surrogate Executable

Core accepts the delivered `M4B-P9-RESIDENCY-SURROGATE-001` (Protocol 1.0) executable artifact, schema, and lock file. This delivery supersedes the defective non-executable pseudo-code example in `DELIVERY-P9-SURROGATE-SPEC-001` §3.

We confirm the corrected process-group topology:
- A supervisor process that touches and holds 2304 MiB of private anonymous memory.
- Four transient CPU workers spawned as fresh independent executables per 6.0s `INFER` phase.
- All transient PIDs are emitted via `INFERENCE_STARTED` within the JSONL protocol.
- Independent process-group management and rejection of non-compliant targets (nonzero Swap, non-Linux/aarch64).

## 2. Directions for Audio POC

Audio POC is directed to vendor or directly integrate the exact locked surrogate files from commit `f18f823146727b50cb3ef15e9e14b51983643406` without semantic changes.

We confirm the measurement, cleanup sequence, and decision rules established in `DELIVERY-012`:
- The capacity metric is strictly `MemTotal - MemAvailable <= 3584 MiB`; `sum(RSS)` remains purely diagnostic.
- Audio must launch the surrogate as a process group, wait for `READY`, and manage process-tree sampling at intervals ≤ 1.0s.
- `PASS` requires no capacity breach, no OOM event, no kernel fault, complete M4A audio workloads overlapping with `INFER`, and zero residue.

## 3. Prerequisite Status

No external prerequisites remain for the surrogate. The Audio M4A-P9 packet integration is officially unblocked. 

**Note**: This acceptance and authorization is solely for the Audio POC resource-reservation (M4A-P9) execution. It does not grant execution PASS or LLM Gate 2 credit for the M4B pipeline.
