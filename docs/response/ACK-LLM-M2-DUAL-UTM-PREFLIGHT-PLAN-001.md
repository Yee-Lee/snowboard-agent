# M2 Dual-UTM Environment Preflight Assessment

- **Record ID**: `ACK-LLM-M2-DUAL-UTM-PREFLIGHT-PLAN-001`
- **Date**: 2026-08-22
- **Scope**: M2 pre-entry / Gate 1 Ubuntu runner selection
- **Status**: `PROPOSED / CORE AND EXECUTION AUTHORIZATION REQUIRED`
- **Delivery contribution**: D1, D2 and D8

## Finding

The two available Ubuntu 24.04 workstations are UTM guests on different host architectures:

- `ENV-UTM-ARM64-001`: macOS ARM64 host / Ubuntu 24.04 ARM64 guest;
- `ENV-UTM-X8664-001`: macOS x86_64 host / Ubuntu 24.04 x86_64 guest.

Neither environment has been authenticated for Gate 1. Existing records from another workstation
do not prove that the pinned wheels, dependencies or runtime bindings exist on either guest. Choosing
x86_64 only because R5 names it, or choosing ARM64 only because the product Pi is ARM64, would both
precede evidence.

## Proposed resolution

Run `G1-DUAL-UTM-PREFLIGHT-001` before M2 entry. The packet checks exact guest identity, native-ISA
virtualization, controlled capacity, pinned wheel/dependency checksums, offline isolated install,
native binding load and bounded adapter/fake-child lifecycle. It excludes model acquisition/load,
generation, latency/tokens-per-second ranking and all candidate/Pi/Gate 2 claims.

The fixed disposition is:

1. Both environments pass: select ARM64 for product-ISA alignment.
2. ARM64 is `FAIL` or `INCONCLUSIVE` and x86_64 passes: select x86_64.
3. Neither passes: return `INCONCLUSIVE` and request artifact/runtime remediation.

One controlled rerun is permitted only after an identified environment failure; original evidence
is retained. After review, the POC returns the selected platform and an append-only affected packet
revision for separate Core acceptance.

## Boundary

R5 implementation SHA `190a827b4c82279e4300af6075e2eeb52b91cd54` remains immutable. Its
exact-SHA acceptance request should be held until Core decides this preflight request. M2 remains
`NOT_STARTED`; no candidate manifest, model download, real generation, Pi access or hardware result
is authorized by this assessment.
