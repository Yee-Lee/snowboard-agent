# ARM64 Preflight Diagnostic ACK Intake

- **Record ID**: `RESP-LLM-M2-ARM64-PREFLIGHT-DIAGNOSTIC-001`
- **Incoming ACK**: `ACK-LLM-M2-ARM64-PREFLIGHT-DIAGNOSTIC-001`
- **Accepted target**: `265db05776b6bf5fadca5b3c3ab41345aa68819e`
- **Status**: `ARM64 FORMAL PASS ACCEPTED / BOUNDED WIP CONTINUATION AUTHORIZED`
- **Date**: 2026-08-22

## Accepted disposition

Core accepted the exact target as the complete sanitized ARM64 diagnostic/change record and waived,
for this instance only, the missing pre-execution Core authorization, exhausted rerun budget and
baseline deviation. The diagnostic `PASS` is the formal ARM64 environment-preflight result; no
corrective ARM64 rerun is required. The two earlier `INCONCLUSIVE` attempts remain permanent history.

ARM64 is the primary Ubuntu pre-screen track. x86_64 remains an independent portability/fallback
track and does not block ARM64 progress.

## Authorized WIP workflow

- `wip/m2-arm64-preflight`: complete the approved ARM64 workstation scope.
- `wip/m2-x86_64-preflight`: complete the independent x86_64 portability/fallback scope.
- Both tracks may perform append-only runner/lock/config/adapter refinement, controlled artifact
  preparation and immutable Ubuntu candidate pre-screen execution under predeclared commands and
  stop conditions without a new Core round trip for every preparation step.
- Stop on identity drift, missing authority, dirty/reused paths, network fallback, unbounded process
  or cleanup failure. Preserve every `PASS`, `FAIL` and `INCONCLUSIVE` attempt.
- Keep binaries, models, raw logs, private paths, credentials and host identities outside Git.

Only after both owners report results and Technical Lead confirms the sanitized merge boundary may
the reviewed integration be merged to `llm`, subject to User Git authorization.

## Unchanged boundaries

M2 remains `NOT_STARTED`; R5 acceptance remains held. Pi access/execution, Gate 2 evidence, finalist
selection and product integration are not authorized.
