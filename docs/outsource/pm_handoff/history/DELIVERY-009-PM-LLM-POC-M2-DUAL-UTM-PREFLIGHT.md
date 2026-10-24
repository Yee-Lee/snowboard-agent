# LLM POC M2 Dual-UTM Environment Preflight Change Request

- **Delivery ID**: `DELIVERY-009-PM-LLM-POC-M2-DUAL-UTM-PREFLIGHT`
- **From / via**: LLM POC Team / User-authorized Agent courier via PM
- **To**: Core Team Designer
- **Affected contract**: `DELIVERY-LLM-POC-M4B-CONTRACT-001`
- **Affected review request**: `DELIVERY-008-PM-LLM-POC-M2-GATE1-R5-REVIEW`
- **Proposed packet**: `G1-DUAL-UTM-PREFLIGHT-001`
- **Review target**: `llm` / `4b36ca2a342fde1ea0341fdee3c7a02446587c34`
- **Status**: `CORE DECISION REQUESTED / PREFLIGHT AND REAL EXECUTION BLOCKED`
- **Architecture change**: `No product architecture change`
- **Date**: 2026-08-22

## Decisions requested

Please:

1. hold the R5 exact-SHA acceptance requested by DELIVERY-008 until the environment preflight is
   reviewed;
2. approve the bounded dual-UTM preflight design and its fixed platform-disposition rule;
3. authorize preparation and inspection of the exact LiteRT-LM v0.16.0 ARM64/x86_64 API wheels,
   offline dependency closures and adapter/binding bundles in User-approved controlled paths; and
4. permit the POC to return an immutable executable test request with exact commands, operators and
   raw paths for a separate execution authorization.

This staged request does not ask Core to accept ARM64 or x86_64 in advance. It avoids selecting a
Gate 1 workstation from schema history or unverified performance assumptions.

## Newly confirmed environment topology

Only two Ubuntu 24.04 workstations are available:

| Environment ID | Host | UTM guest | Intended preflight artifact |
| --- | --- | --- | --- |
| `ENV-UTM-ARM64-001` | macOS ARM64 | Ubuntu 24.04 ARM64 | pinned LiteRT-LM v0.16.0 aarch64 API wheel and dependency/binding bundle |
| `ENV-UTM-X8664-001` | macOS x86_64 | Ubuntu 24.04 x86_64 | pinned LiteRT-LM v0.16.0 x86_64 API wheel and dependency/binding bundle |

Both use native-ISA guests, but neither has yet supplied authenticated UTM acceleration, guest,
capacity, artifact, offline-install, native-linking or lifecycle evidence. Neither is a product Pi.

## Frozen preflight and selection rules

The proposed packet verifies exact environment identity, hardware acceleration, controlled capacity,
artifact/dependency checksums, offline isolated install, native binding load, three adapter/fake-child
lifecycle repetitions and cleanup. One controlled rerun per environment is allowed only for an
identified environment failure, with the original result retained.

No model is downloaded or loaded. No generation, latency/tokens-per-second comparison, candidate
ranking, finalist selection or Pi/Gate 2 claim occurs.

The platform rule is fixed before execution:

- both environments `PASS`: select Ubuntu ARM64 for product-ISA alignment;
- ARM64 `FAIL/INCONCLUSIVE` and x86_64 `PASS`: select Ubuntu x86_64;
- neither `PASS`: select neither and return `INCONCLUSIVE` plus a change request.

After evidence review, the POC will return the selected platform and affected append-only Gate 1
packet revision for separate Core acceptance. Real candidate execution remains independently blocked.

## Changed paths in the review target

- `docs/milestone/README.md`
- `docs/milestone/m2_llm_candidate_evaluation.md`
- `docs/milestone/m4b_execution_plan.md`
- `docs/response/ACK-LLM-M2-DUAL-UTM-PREFLIGHT-PLAN-001.md`
- `poc_llm/README.md`
- `poc_llm/tests/gate1/GATE1-ENV-PREFLIGHT-001.md`

## Evidence and authority boundary

This revision contains planning and a proposed packet only. No preflight command, artifact download,
model acquisition, Ubuntu run, Pi access, candidate evidence or hardware result occurred. M2 remains
`NOT_STARTED`; the current Core contract remains authoritative until Core issues a written decision.
