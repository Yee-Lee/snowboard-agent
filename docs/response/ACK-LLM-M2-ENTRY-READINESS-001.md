# M2 Gate 1 Entry-Readiness Assessment

- **Record ID**: `ACK-LLM-M2-ENTRY-READINESS-001`
- **Date**: 2026-08-21
- **Scope**: M2 / Gate 1 candidate proposal, x86 pre-screen and product-Pi compatibility
- **Baseline reviewed**: `llm` / `f84b83f99d3957514e6ad953b5df6301aea5428b`
- **Status**: `BLOCKED — ENTRY REVIEW NOT REQUESTED`

## User Authorization Recorded

On 2026-08-21, the User authorized controlled artifact acquisition, checksum verification, local
strict-adapter/config development and preparation of the approved x86/Pi runners. This authorization
does not replace a Core Gate 1 finalist ACK, does not authorize Gate 2A, and does not disclose or
create any operator endpoint, credential or raw-evidence path.

## Delivery Contribution

This assessment advances M2 entry preparation for D1, D2, D4, D5, D7 and D8. It does not start
M2, issue a candidate manifest, authorize artifact acquisition, or establish a hardware result.

## Ready Repository Inputs

- `G1-X86-PI-COMPAT-004`, its lock, schemas, x86/Pi runners, selector and deterministic regressions
  are frozen and Core-accepted for repository-only validation.
- `G1-CANDIDATE-PREFLIGHT-001` fixes three proposed LiteRT-LM v0.16.0 pairings and records known
  model/wheel checksums, license metadata and the intended two-stage selection rule.
- The 20-case catalog, result schemas and Gate 1-to-Gate 2 evidence carry-over guard are present.

## Entry Conditions Still Open

| Required item | Current state | Owner / required authorization |
| --- | --- | --- |
| Exact candidate and acquisition manifests | Not issued; no `fixtures/gate1/candidates/` directory exists. | POC after approved acquisition and local checksum verification. |
| Runtime source/archive, wheel/dependency bundle and model artifacts | Not acquired; Git intentionally contains no artifacts. | User authorization for controlled acquisition, storage and checksum verification. |
| Strict config and LiteRT-LM protocol adapter | Not implemented or artifact-bound. | POC work after the selected bundle is available. |
| Ubuntu 24.04 x86 runner, fresh raw path and capacity record | Potential workstation only; no owner/path authorization recorded. | User / POC Test Controller. |
| Product Pi 5 compatibility target, fresh isolated path and network-disabled proof | Platform is known, but access, transfer, installation and run authorization are absent. | User / operator. |
| Real x86 or Pi execution | Explicitly unauthorized by the governing contract and Packet 004. | Core/User written authorization. |

## Capacity Finding

The reviewed filesystem had 5.8 GiB free before acquisition. The verified primary model, two API
wheels and source archive now occupy about 2.9 GiB, leaving about 3.5 GiB. The three proposed model
files alone total approximately 4.4 GiB, before platform wheel/dependency bundles, isolated installs
or raw evidence. It is not a safe controlled location for the complete first-round artifact bundle.
A capacity-approved location or staged acquisition plan that preserves reproducibility is required
before candidate manifests or real x86 pre-screen runs can be issued.

## Verified Acquisition Progress

For `CAND-LRT-G4E2B-MOBILE-R1`, the official model, x86/aarch64 LiteRT-LM API wheels and source
archive are present only in the Git-ignored controlled location. The model and both wheel SHA-256
values match `G1-CANDIDATE-PREFLIGHT-001`; the source archive SHA-256 is recorded as
`4a790f5c56e3622891d0784c2b153e53ba2d2a140f739e8dc6bff71613b78e07`. An isolated x86 API import
has succeeded without loading the model. This is acquisition evidence, not candidate or hardware
evidence.

## Newly Identified Packet Blocker

[`M2-G1-PLATFORM-CONFIG-001`](RESP-LLM-M2-GATE1-PLATFORM-CONFIG-FINDING-001.md) shows that the
frozen single-config candidate schema cannot truthfully bind the required x86 and Pi strict configs.
Core must issue an approved schema/lock/runner revision before any candidate manifest or real Gate 1
run can be valid.

## Minimum Authorization Package Requested Before Entry Review

1. Approve the exact candidate artifact set and controlled, Git-ignored storage location; permit
   download/acquisition, license/source retention and independent SHA-256 verification.
2. Name the x86 and product-Pi operators, approve fresh raw/isolated evidence paths and confirm
   sufficient storage for the selected artifacts plus raw evidence.
3. Approve offline artifact transfer/install and the Pi network-disabled proof procedure. No Pi
   Gate 2A work, swap change, reboot or privilege change is included.
4. After the above is complete, authorize a separate M2 entry review and test request. Only then may
   the milestone index change from `PLANNED` to `IN_PROGRESS`.

## Boundary

Until every entry condition and the required authorization are present, allowed work remains limited
to repository-only deterministic regression and planning. Any missing or unverifiable environment or
evidence condition is `INCONCLUSIVE` for a future run, never a candidate `FAIL` or `PASS`.
