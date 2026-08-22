# LLM POC M2 ARM64 UTM Preflight Diagnostic Review Request

- **Delivery ID**: `DELIVERY-010-PM-LLM-POC-M2-ARM64-PREFLIGHT-DIAGNOSTIC-REVIEW`
- **From / via**: LLM POC Team / User-authorized Agent courier via PM
- **To**: Core Team Designer
- **In response to**: `ACK-LLM-M2-DUAL-UTM-PREFLIGHT-PLAN-001`
- **Parent packet**: `G1-DUAL-UTM-PREFLIGHT-001`
- **Environment**: `ENV-UTM-ARM64-001`
- **Review target**: `wip/m2-arm64-preflight` / `265db05776b6bf5fadca5b3c3ab41345aa68819e`
- **Status**: `CORE DISPOSITION REQUESTED / FORMAL ARM64 RESULT NOT YET ACCEPTED`
- **Architecture change**: `No product architecture change`
- **Date**: 2026-08-22

## Decisions requested

Please accept the exact review target as a complete sanitized ARM64 diagnostic/change record, then
choose one formal disposition:

1. **Exception acceptance**: explicitly waive the missing pre-execution Core authorization, exhausted
   rerun budget and baseline/runner binding deviation, and accept the diagnostic `PASS` as the formal
   ARM64 environment-preflight result; or
2. **Corrective rerun (POC recommendation)**: authorize an append-only ARM64 request revision that
   freezes the runner, lock, exact artifact paths/checksums, commands, operator and raw path before
   execution, and grant one new controlled rerun after separate exact-SHA review.

Neither disposition selects the final Ubuntu pre-screen platform. The x86_64 environment remains
unexecuted, so the approved dual-UTM platform rule is not yet complete.

## Attempt history and diagnostic result

| Attempt | Scope | Result | Disposition |
| --- | --- | --- | --- |
| `ENV-UTM-ARM64-001-ATTEMPT-001` | initial runner | `INCONCLUSIVE` | runner incorrectly required loopback-only sysfs despite isolated namespace and empty route table |
| `ENV-UTM-ARM64-001-RERUN-001` | sole controlled rerun | `INCONCLUSIVE` | runner incorrectly required a header line in a completely empty `/proc/net/route`; retry budget exhausted |
| `ENV-UTM-ARM64-001-DIAGNOSTIC-001` | User-authorized diagnostic | `PASS` | retained as diagnostic only pending this Core disposition |

The diagnostic authenticated the pinned ARM64 wheel SHA-256
`5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00` and native library SHA-256
`9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4`.
The native library was ARM64 with complete dynamic linkage. Three independent native-import and
frozen lifecycle repetitions exited `0`; the isolated install was removed and no matching owned
process remained.

Sanitized result SHA-256:
`85102c8d88eaf3db89ecd8a01f931e15aca1720d6f3809c156569881b4e3212b`.
Raw log SHA-256:
`9662b7a5f92bb791d239c9a714ca0849e1ac018e95fff4fddaa043cb4ba684ce`.

No model was downloaded or loaded. No generation, performance ranking, candidate evidence, Pi
evidence or x86_64 artifact was used.

## Formal-evidence deviations

- Core authorized packet preparation but did not authorize real preflight execution. The diagnostic
  had User authorization only.
- The declared execution baseline is `98a854a91f514efa12c3904576c2b652629e0bbd`, while the runner
  and completed result first appear together in review target `265db057...`; the run therefore was
  not against a pre-reviewed immutable runner SHA.
- The executable request still records wheel/dependency/adapter paths and canonical argv as
  unavailable placeholders rather than exact pre-execution identities.
- The single controlled rerun budget was consumed by the second runner defect. The later diagnostic
  cannot silently reset that budget.
- The sanitized diagnostic supports ARM64 package viability, but x86_64 has no corresponding result;
  it cannot independently close the approved dual-UTM selection rule.

## Required corrective revision properties

If Core selects the recommended corrective path, the returned append-only request will:

- bind a clean baseline SHA containing the runner, schema/lock and all result semantics;
- freeze sanitized operator identity, approved wheel/bundle locations, fresh raw/install paths,
  canonical argv and checksums before execution;
- authenticate Ubuntu/kernel/glibc/Python/UTM acceleration and capacity inputs;
- prove both IPv4 and IPv6 network isolation without assuming a loopback-only sysfs view or a route
  header representation;
- bind native import and lifecycle outputs to the exact run and use run-owned PID/process-group
  cleanup proof; and
- retain all three existing attempts as historical diagnostic evidence without relabeling them.

## Changed paths in the review target

- `docs/DOCUMENT_INDEX.md`
- `docs/milestone/README.md`
- `poc_llm/README.md`
- `poc_llm/evidence/gate1/env-preflight-arm64-001.json`
- `poc_llm/tests/gate1/GATE1-ENV-PREFLIGHT-ARM64-001-DIAGNOSTIC-001.md`
- `poc_llm/tests/gate1/GATE1-ENV-PREFLIGHT-ARM64-001-RERUN-001.md`
- `poc_llm/tests/gate1/GATE1-ENV-PREFLIGHT-ARM64-001.md`
- `poc_llm/tools/run_gate1_env_preflight_arm64.py`

## Unchanged boundaries

M2 remains `NOT_STARTED`. R5 exact-SHA acceptance remains held. This delivery does not authorize a
new ARM64 run, x86_64 execution, model acquisition/load, candidate manifest, Gate 1 candidate run,
Pi access, Gate 2 evidence, finalist selection or product integration.
