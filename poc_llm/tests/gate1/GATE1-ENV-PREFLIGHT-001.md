# GATE1-ENV-PREFLIGHT-001 — Dual-UTM Offline Viability

- **Packet ID**: `G1-DUAL-UTM-PREFLIGHT-001`
- **Milestone**: M2 pre-entry
- **Status**: `PROPOSED / EXECUTION BLOCKED`
- **Purpose**: select the Ubuntu Gate 1 pre-screen platform using bounded D1/D2/D8 evidence
- **Approver**: Core Designer; User separately authorizes artifacts, paths and operators

## Environments

| Environment ID | Host | Guest | Expected wheel |
| --- | --- | --- | --- |
| `ENV-UTM-ARM64-001` | macOS ARM64 | Ubuntu 24.04 ARM64 | `litert_lm_api-0.16.0-py3-none-manylinux_2_27_aarch64.whl` / SHA-256 `5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00` |
| `ENV-UTM-X8664-001` | macOS x86_64 | Ubuntu 24.04 x86_64 | `litert_lm_api-0.16.0-py3-none-manylinux_2_27_x86_64.whl` / SHA-256 `a5d58ff8e1c14057d6a8c1f0333372bc685361e6311ea87bfa49fc131cb00a95` |

Before execution, bind each environment to its sanitized host OS/architecture, UTM/QEMU version,
hardware-acceleration mode, guest OS/kernel/glibc/Python, vCPU, RAM, disk, swap state, operator,
fresh raw path and exact artifact/dependency checksums. Do not record hostname, account, endpoint,
credential, host fingerprint or key path in Git.

## Authorized scope requested

For each guest, in a new isolated environment and with network disabled during install/test:

1. authenticate the environment record and matching v0.16.0 API wheel checksum;
2. authenticate the predeclared transitive dependency and adapter/binding bundle checksums;
3. install only from the controlled offline bundle and record argv plus argv checksum;
4. import the exact API/native bindings and inspect native shared-library dependencies for missing
   or wrong-architecture entries;
5. run three clean repetitions of adapter initialization without a model and the frozen fake-child
   READY/PING/SHUTDOWN, timeout, cancel and cleanup checks;
6. remove only run-owned temporary state and prove exit `0`, no owned process/group remains and the
   controlled bundle is unchanged.

The exact import and adapter commands must be added to the immutable test request after the acquired
bundle is independently inspected and before Core execution authorization. A command placeholder,
interactive repair, network fallback or package substitution makes the run `INCONCLUSIVE`.

## Result rules

An environment is `PASS` only when its identity is exact, hardware acceleration is authenticated,
all offline artifacts match, installation/import/native linking succeeds, all three lifecycle
repetitions pass and cleanup evidence is complete. Valid wrong-architecture, unresolved native
dependency or repeatable lifecycle failure is `FAIL`. Missing authorization, artifact, identity,
command or evidence is `INCONCLUSIVE`.

The platform disposition is fixed before execution:

- both `PASS`: select Ubuntu ARM64 because it aligns with the product ISA;
- ARM64 `FAIL/INCONCLUSIVE`, x86_64 `PASS`: select Ubuntu x86_64;
- neither `PASS`: no platform selection; return `INCONCLUSIVE` and a change request.

Only one controlled rerun per environment is allowed after a documented environment failure. Keep
the original result and do not compare elapsed time, latency, tokens-per-second or RSS to select the
platform.

## Explicit exclusions

- No model weights are downloaded, transferred or loaded.
- No real generation, candidate manifest, candidate ranking or finalist selection occurs.
- No UTM result is Pi compatibility, Gate 2A or hardware performance evidence.
- No R5 file or protected M1 path is changed.
- Approval of this packet does not start M2 or authorize the later selected-platform/Pi runs.
