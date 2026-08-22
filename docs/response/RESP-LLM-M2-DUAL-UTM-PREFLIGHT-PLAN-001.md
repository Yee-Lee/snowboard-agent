# M2 Dual-UTM Environment Preflight Assessment

- **Record ID**: `RESP-LLM-M2-DUAL-UTM-PREFLIGHT-PLAN-001`
- **Incoming ACK**: `ACK-LLM-M2-DUAL-UTM-PREFLIGHT-PLAN-001`
- **Date**: 2026-08-22
- **Scope**: M2 pre-entry / Gate 1 Ubuntu runner selection
- **Status**: `DESIGN AND PACKET PREPARATION APPROVED / REAL EXECUTION BLOCKED`
- **Delivery contribution**: D1, D2 and D8

## Core disposition

Core approved the bounded dual-UTM design and the fixed platform rule. R5 exact-SHA acceptance
remains held until preflight evidence is completed and reviewed. The POC may prepare and inspect the
exact LiteRT-LM v0.16.0 ARM64/x86_64 API wheels, offline dependency closures and adapter/binding
bundles in User-approved controlled paths.

Core did not authorize preflight execution. The next return must be an immutable executable test
request with exact commands, operators and raw paths for separate authorization.

## Fixed disposition

1. Both environments pass: select ARM64 for product-ISA alignment.
2. ARM64 is `FAIL` or `INCONCLUSIVE` and x86_64 passes: select x86_64.
3. Neither passes: return `INCONCLUSIVE` and a change request.

## Remaining preparation

- Record sanitized host/guest/UTM acceleration and capacity identities for both environments.
- Obtain User approval for controlled artifact and fresh raw evidence paths and identify operators.
- Acquire and independently verify only the approved API wheels, dependency closures and
  adapter/binding bundles; do not download or load models.
- Freeze exact offline install, import, native-linking, lifecycle and cleanup commands plus their
  checksums in an immutable executable request.

M2 remains `NOT_STARTED`. No preflight command, model download, candidate execution, Pi access or
hardware result is authorized by this intake.
