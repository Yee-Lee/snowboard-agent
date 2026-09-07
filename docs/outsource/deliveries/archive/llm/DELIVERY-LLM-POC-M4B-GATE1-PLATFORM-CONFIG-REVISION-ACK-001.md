# Core Designer → LLM POC Team: Gate 1 Platform-Config Revision ACK

- **Delivery ID**: `DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CONFIG-REVISION-ACK-001`
- **In response to**: `DELIVERY-007-PM-LLM-POC-M2-GATE1-PLATFORM-CONFIG-CHANGE-REQUEST`
- **Finding**: `M2-G1-PLATFORM-CONFIG-001`
- **Affected packet**: `G1-X86-PI-COMPAT-004`
- **Reviewed POC branch / exact commit**: `llm` / `341ccc012d87847fed1d3a68e5ef7cc68eb872ba`
- **From**: Core Team Designer
- **To**: LLM POC Team
- **Date**: 2026-08-21
- **Status**: `ACCEPTED — R5 REPOSITORY REVISION AUTHORIZED / REAL EXECUTION BLOCKED`
- **Architecture change**: `No`

## 1. Designer decision

Core accepts the finding. Packet R4 cannot authenticate one logical candidate across both required
platforms because its candidate schema exposes only one config artifact while each strict config
contains a platform-specific runtime path, model path, runtime checksum and platform value. The
acquisition schema already separates runtime/dependency artifacts, but neither candidate identity nor
READY/result authentication selects a correspondingly platform-specific config.

The LLM POC Team is authorized to produce one append-only repository revision named
`G1-X86-PI-COMPAT-005`. R4 remains immutable historical input and must not be used for real candidate
evidence. R5 acceptance will require a separate Core review of the returned exact SHA.

This decision does not authorize a real x86 run, Pi access/transfer/install/run, network switching,
Gate 1 finalist status, Gate 2A, model baseline selection or Core product integration.

## 2. M1 freeze preservation

The accepted M1 candidate `830d0b4ed2d41406c789bb110ed84b7553f330a4` remains frozen. R5 must
not modify the following protected M1 scope:

- `poc_llm/contracts/m1/`;
- `poc_llm/harness/m1_contract_boundary.py` and `m1_contract_validator.py`;
- M1 fixtures, tests and `m1-contract-lock.json`.

The existing strict-config schema remains the schema for one concrete platform config. Gate 1 R5
must add its platform-set schema and projection in Gate 1-owned paths. Each runner selects exactly one
platform entry and constructs the existing M1 boundary input from that authenticated entry. If the
POC determines that a protected M1 path must change, it must stop and submit a separate append-only M1
freeze revision; this ACK does not authorize such a change.

## 3. Required R5 identity model

R5 must preserve one logical `candidate_id` and `pairing_revision`, while authenticating physical
deployment identity independently for `ubuntu-x86_64` and `pi-debian13-aarch64`.

### 3.1 Candidate manifest

Replace the singular candidate `config` with an exact-key platform map:

```text
configs.ubuntu-x86_64              = {path, sha256}
configs.pi-debian13-aarch64        = {path, sha256}
```

The candidate manifest keeps the shared logical runtime name/version/source checksum, model
name/version/checksum, quantization, license, protocol/fixture identity and pairing revision. R5
schema/validator enforcement must reject a missing platform, an extra platform, a singular legacy
config field and the same config checksum reused for two non-identical platform configs.

### 3.2 Acquisition manifest

Each acquisition `platforms.<platform>` entry must authenticate:

- runtime artifact path and SHA-256;
- dependency bundle path and SHA-256;
- adapter/binding bundle path and SHA-256;
- deployed model path and SHA-256;
- offline install argv and argv checksum.

The deployed model path may differ by platform, but its byte checksum must equal the shared logical
model checksum. A platform-native model conversion is a different pairing identity unless separately
approved.

### 3.3 Runner and READY/result binding

Each x86/Pi runner must fail closed in this order:

1. authenticate the R5 lock, candidate manifest and acquisition manifest;
2. select only the config and acquisition entry matching the runner platform;
3. hash the actual strict-config file and match `configs.<platform>.sha256`;
4. validate strict config platform, runtime/model paths and checksums against the selected acquisition
   entry and shared logical identities;
5. authenticate dependency and adapter/binding bundle checksums before launch;
6. require READY platform/runtime/model/config identity to equal the selected projection;
7. bind the sanitized result to candidate-manifest SHA, acquisition-manifest SHA, selected config,
   dependency, adapter/binding, command and lock identities.

There is no fallback to the other platform config. Cross-platform absolute paths, config hashes,
READY identities or result identities are invalid, not `INCONCLUSIVE` evidence.

## 4. Required locked packet and regressions

The returned packet must add new versioned R5 schemas/runners/lock without rewriting R4 files. The R5
lock must include at least the packet, candidate/acquisition schemas, x86 and Pi runners, result and
selection schemas, selector, validator, catalog and Gate 2 carry-over guard.

Deterministic regressions must retain the accepted R4 max-two/no-backfill/evidence-separation coverage
and prove rejection of:

- missing, extra or legacy singular config entries;
- swapped x86/Pi config path or checksum;
- wrong actual config hash, runtime path, model path or artifact checksum;
- mismatched dependency or adapter/binding bundle;
- candidate/pairing/config/acquisition manifest drift;
- cross-platform READY or result identity;
- a runner selecting a platform other than its own;
- forged R4 evidence presented as R5 evidence;
- Gate 1 evidence presented as Gate 2A credit.

Synthetic fixtures may use separate absolute temporary paths per platform. They are regression input
only and must not be labeled candidate, x86 or Pi evidence.

## 5. Return and authorization boundary

Return one committed R5 packet with:

1. response/delivery path and complete changed-path list;
2. branch and immutable 40-character commit SHA supplied after commit;
3. R5 self-test, negative-regression and retained R4/M1 regression commands, exit codes and summary;
4. confirmation that protected M1 paths are unchanged from the frozen candidate;
5. confirmation that no real x86/Pi execution or new Gate 2 evidence occurred;
6. remaining capacity, controlled-path, operator, Pi access and execution blockers.

Repository-only schema, lock, runner, fixture and deterministic-test work is authorized. Existing
User-authorized controlled acquisition evidence may be preserved, but it is not candidate or hardware
evidence. Candidate manifests and real Gate 1 execution remain blocked until Core accepts the exact R5
packet and the applicable environment/operator authorizations are recorded.
