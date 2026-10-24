# LLM POC M2 ARM64 UTM Preflight Acceptance and Direct-Continuation Request

- **Delivery ID**: `DELIVERY-010-PM-LLM-POC-M2-ARM64-PREFLIGHT-DIAGNOSTIC-REVIEW`
- **From / via**: LLM POC Team / User-authorized Agent courier via PM
- **To**: Core Team Designer
- **In response to**: `ACK-LLM-M2-DUAL-UTM-PREFLIGHT-PLAN-001`
- **Parent packet**: `G1-DUAL-UTM-PREFLIGHT-001`
- **Environment**: `ENV-UTM-ARM64-001`
- **Review target**: `wip/m2-arm64-preflight` / `265db05776b6bf5fadca5b3c3ab41345aa68819e`
- **Status**: `CORE EXCEPTION ACCEPTANCE AND BOUNDED CONTINUATION REQUESTED`
- **Architecture change**: `No product architecture change`
- **Date**: 2026-08-22

## Decisions requested

Please:

1. accept the exact review target as the complete sanitized ARM64 diagnostic/change record;
2. explicitly waive the missing pre-execution Core authorization, exhausted rerun budget and
   baseline/runner binding deviation, and accept the diagnostic `PASS` as the formal ARM64
   environment-preflight result without another corrective ARM64 rerun;
3. revise the dual-UTM disposition so an ARM64 `PASS` is sufficient to select ARM64 as the primary
   Ubuntu pre-screen track; x86_64 remains an independent portability/fallback track and does not
   block ARM64 progress;
4. authorize the bounded ARM64 and x86_64 WIP branch workflow below through completion of their
   approved workstation scopes, without a new Core round trip for every preparation step; and
5. permit a reviewed, sanitized integration commit back to `llm` only after both branch owners report
   their results and the Technical Lead confirms the merge boundary.

This request asks Core to accept disclosed deviations rather than hide or rewrite them. The original
two `INCONCLUSIVE` attempts remain permanent evidence history.

## Requested bounded direct-continuation scope

| Track | Branch | Requested authority | Completion boundary |
| --- | --- | --- | --- |
| ARM64 primary | `wip/m2-arm64-preflight` | append-only runner/lock/config/adapter refinement; controlled runtime/model artifact preparation; immutable ARM64 Ubuntu candidate pre-screen execution under predeclared commands and stop conditions | sanitized environment/candidate result, raw checksums, cleanup proof and Technical Lead review |
| x86_64 portability/fallback | `wip/m2-x86_64-preflight` | independent x86_64 environment packet, controlled artifacts and bounded portability/pre-screen execution using the same logical candidate identities | sanitized x86_64 result, raw checksums, cleanup proof and Technical Lead review |

Each track must remain based on `llm` SHA `98a854a91f514efa12c3904576c2b652629e0bbd` or a later
Core-accepted common baseline, preserve append-only attempt history, keep artifacts/raw evidence
outside Git and stop on identity drift, missing authorization, dirty/reused paths, unbounded process,
network fallback or cleanup failure. A branch result may be `PASS`, `FAIL` or `INCONCLUSIVE`; no
branch may suppress an unsuccessful attempt or alter the other track's evidence.

The later integration into `llm` must contain only reviewed source, locks, packets and sanitized
evidence. It must not merge model/runtime binaries, raw logs, private paths, credentials or host
identity. Branch completion and merge do not themselves start M2 or close External Gate 1; milestone
and gate status still require their named reviews.

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

For direct continuation, the append-only branch work will:

- bind each subsequent run to a clean branch SHA containing the runner, schema/lock and all result semantics;
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
new ARM64 run, x86_64 execution, model acquisition/load or Gate 1 candidate run unless Core explicitly
accepts the bounded direct-continuation scope above. Pi access, Pi compatibility execution, Gate 2
evidence, finalist selection and product integration remain excluded even if direct continuation is
approved.
