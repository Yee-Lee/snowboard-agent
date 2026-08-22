# M4b Authoritative POC Execution Plan

狀態：`DUAL-UTM PREFLIGHT PACKET PREPARATION AUTHORIZED / EXECUTION NOT AUTHORIZED`

Revision：`2026-08-22-preflight-proposal`

Owner：POC Technical Lead

Approver：Core Designer

本文件是 Gate 1、Gate 2A、Gate 2B work-package 的唯一 authoritative plan。它依
`DELIVERY-LLM-POC-M4B-CONTRACT-001` 2026-08-19 revision 建立；目前沒有 Ubuntu
benchmark、Pi run 或 candidate evidence。

## Result Semantics

所有 package 只可使用：

- `PASS`：指定 exact SHA、frozen packet、有效環境及所有 mandatory criteria 均通過，
  evidence、cleanup、exit proof 完整。
- `FAIL`：有效環境與完整 evidence 證明至少一項 mandatory criterion 違反。
- `INCONCLUSIVE`：環境、SHA、工具、evidence 或執行不完整，無法區分 candidate 與
  infrastructure failure。
- `Blocked`：必要 ACK、platform、artifact、Accepted Audio package、權限或 owner 未就緒。
- `Core threshold decision required`：只用於 P4 完整有效量測未達 negotiable target，
  或 contract 明列需 Core 裁決的 4GB/8GB portability disposition；不能掩蓋 mandatory fail。

沒有 evidence 的項目為 `Pending`，不是執行結果。一次 controlled rerun 後仍無法判定，
必須 re-estimate 並建立 change request；原始結果保留。

## Gate 1 Work Package

### Proposed pre-entry environment package

`G1-DUAL-UTM-PREFLIGHT-001` design and packet preparation are approved by Core. It compares only
offline package and lifecycle viability on two native-ISA virtualized environments:

- macOS ARM64 host / Ubuntu 24.04 ARM64 UTM guest;
- macOS x86_64 host / Ubuntu 24.04 x86_64 UTM guest.

It does not download or load a model, generate output, rank candidates, measure decision-bearing
performance or produce Gate 1/Gate 2 evidence. Both environments use their pinned LiteRT-LM v0.16.0
API wheel and the same predeclared checks. Three clean import/lifecycle repetitions are required;
one controlled rerun is allowed only for an identified environment failure.

The decision rule is frozen before execution: if both pass, select ARM64 because it matches the
product ISA; if ARM64 fails or remains inconclusive while x86_64 passes, select x86_64; if neither
passes, return `INCONCLUSIVE` and a change request. Core has authorized artifact/dependency/binding
preparation; the User must approve controlled paths and operators, then Core must accept the returned
exact executable request before execution. Core separately approves the resulting platform and
affected append-only packet revision before M2 entry.

| Field | Definition |
| --- | --- |
| Package | Current R5 target `G1-X86-PI-COMPAT-005`; platform disposition pending preflight decision |
| Owner / approver | Developer + POC Test Controller / Technical Lead review / Core Designer ACK |
| Dependency | Gate 0 recorded complete；M1 complete；dual-UTM preflight、resulting platform及affected packet revision取得Core ACK；artifact acquisition與pre-screen/Pi執行分別核准 |
| Platform | Ubuntu 24.04 x86_64完整初篩；產品Pi 5 4GB / Debian 13 aarch64 bounded compatibility |
| Entry / exit | Frozen lock + candidate/acquisition manifests → x86一次預選最多2名 → Pi PASS後置filter → Core written ACK |
| Estimate | 3–5 working days after artifacts and both runners are available |
| Re-estimation trigger | Candidate count/pairing/cycle changes、Pi預選者需補位、artifact/storage delta >25%、license或Pi incompatibility |
| Runner / command | Authenticated selected-platform runner + immutable preselection + Pi compatibility + final filter；current R5見 `GATE1-PACKET-005.md`，後續版本依Core裁決 |
| Evidence | Raw outside Git；x86/Pi/aggregate分離schemas與namespace，Gate 1 Pi evidence不得進2A |
| Cleanup | Success requires SHUTDOWN ACK, exit 0 and absent process group; failure uses bounded group TERM→KILL→wait and records proof; unique raw dir |
| Failure / no-go | x86 identity/gate/cleanup failure拒絕preselection；Pi FAIL/INCONCLUSIVE移除但不補第三名；zero retained產生no-go/change request |

Gate 1 selects proposed Pi candidates only. It produces neither Gate 2A provisional finalist nor
final winner.

The x86 runner validates lock/candidate/acquisition identities, launches the exact bound argv and
drives portable gates itself. The selector authenticates exact 60-case/P4 evidence, ranks x86 once
and freezes at most two preselected candidates. Only those candidates may run the separate Pi
compatibility packet；Pi PASS is a later eligibility filter and never changes the x86 ranking or
backfills a third candidate. Protocol/fake regressions are test-only and do not start Gate 1.

Revision R5 preserves R4 log/P4/process-group/authentication controls and adds exact platform-keyed
config projection. It remains an immutable review target; the pending preflight proposal does not
rewrite it or authorize its real runners.

## Gate 2A Work Packages — LLM-only Pi 5

Common dependency：Gate 1 Core ACK、same frozen candidate/config/fixture/validator SHA、Pi 5 4GB
mandatory environment（swap=0）、8GB informational environment、operator authorization。

Gate 2A must use a new run ID、independent packet and `evidence/m4b/2a/` namespace. Gate 1 Pi
compatibility output is not accepted as any P1～P12 input or completion proof.

Common platform：Raspberry Pi 5 4GB mandatory；8GB runs use identical configuration and cannot
repair a 4GB mandatory failure。

| Package | P IDs | Owner | Entry / exit | Estimate | Runner / evidence | Cleanup and failure/no-go |
| --- | --- | --- | --- | ---: | --- | --- |
| `G2A-WP01-PROVENANCE` | P11 | Developer prepares; Test Controller executes; Internal Tester confirms | Clean exact SHA, fixed source/model/config/license → reproducible setup manifest | 1 day/candidate | Planned `run_m4b_gate.py --gate 2A --cases P11`; `evidence/m4b/2a/<run>/p11` | Remove only run-owned temp; checksum/license/setup ambiguity = FAIL or INCONCLUSIVE by evidence validity |
| `G2A-WP02-LIFECYCLE` | P1, P5, P6, P7 | Test Controller / Internal Tester | P11 valid, protocol/config frozen → lifecycle, timeout, Level 1/2 and Level 3 outcome evidence | 1.5 days/candidate | Planned runner cases `P1,P5,P6,P7`; `evidence/m4b/2a/<run>/lifecycle` | TERM→wait→KILL→waitpid→rebuild/READY; missing exit proof = FAIL; P6 conditional only when P7 all PASS |
| `G2A-WP03-OUTPUT` | P2, P3, P8 | Test Controller / Internal Tester | Frozen 20-case catalog/validator → 100% schema/fallback/log and history isolation | 1 day/candidate | Gate 1 validator plus Pi adapter; `evidence/m4b/2a/<run>/output` | Any repetition, leakage or hidden history failure = FAIL; no averaging |
| `G2A-WP04-PERF-SOAK-OFFLINE` | P4, P10A, P12 | Test Controller / Internal Tester | Prior 2A packages valid, cooling/power/token envelope frozen, offline approval → raw/P50/P95, 20 LLM-only sessions, offline proof | 2 days/candidate | Planned runner cases `P4,P10A,P12`; `evidence/m4b/2a/<run>/perf-soak-offline` | P4 miss requires Core decision; P10A/P12 mandatory fail causes no-go; cleanup/orphan proof required |
| `G2A-WP05-PROVISIONAL` | 2A aggregate | Technical Lead recommends; Core Designer ACK | All required 2A results reviewed → at most one provisional finalist per reviewed candidate set | 0.5 day | 2A manifest and decision table | No final winner; unresolved mandatory result blocks provisional ACK |

Gate 2A mandatory set is P1/P2/P3/P5/P7/P8/P10A/P11/P12. P6 follows conditional escalation;
P4 must be completely measured. 2A may issue a **provisional finalist ACK only**.

Re-estimate Gate 2A when candidate/config/fixture SHA changes, Pi/cooling differs from packet,
setup exceeds estimate by >25%, any mandatory case requires more than one rerun, or P4 needs a
Core decision. A changed frozen input invalidates all affected packages.

## Gate 2B Work Packages — Accepted Audio + LLM

Common dependency：Gate 2A provisional finalist ACK and Core-recorded Accepted Audio POC final
handoff ID/full SHA/kit. Missing Audio input is `Blocked`; surrogate is debug-only.

| Package | P IDs | Owner | Entry / exit | Estimate | Runner / evidence | Cleanup and failure/no-go |
| --- | --- | --- | --- | ---: | --- | --- |
| `G2B-WP01-INTAKE-REGRESSION` | P1, P2, P5, P7, P8, P11, P12 regression | Developer verifies package; Test Controller runs; Internal Tester confirms | Same 2A candidate/config/fixture, Accepted Audio SHA/kit, 4GB swap=0 → baseline hashes and mandatory regression PASS | 1 day | Planned `run_m4b_gate.py --gate 2B --cases P1,P2,P5,P7,P8,P11,P12`; `evidence/m4b/2b/<run>/regression` | Baseline drift = Blocked; valid regression failure revokes final eligibility and returns to 2A review |
| `G2B-WP02-RESIDENCY` | P9 | Test Controller / Internal Tester | Regression valid → Core parent + LLM + real ASR/TTS residency measurements | 1 day | Planned runner `--cases P9`; `evidence/m4b/2b/<run>/residency` | `system_used > 3584 MiB`、OOM、full pressure stall增加或swap≠0 = FAIL；sum RSS僅diagnostic；missing Audio = Blocked |
| `G2B-WP03-COMBINED-SOAK` | P3 regression through catalog, P10B; P4 hot sanity | Test Controller / Internal Tester | P9 valid, same 20-case catalog → 20 ASR fixture→LLM→TTS sessions, 5s interval | 1.5 days | Planned runner `--cases P3,P4-HOT,P10B`; `evidence/m4b/2b/<run>/combined-soak` | ≥80°C, throttling, crash, leak, schema/fallback/log or owner residue = FAIL |
| `G2B-WP04-FINAL-DECISION` | 2A + 2B aggregate | Technical Lead recommends; Core Designer decides | All mandatory 2A, regression, P9 and P10B reviewed → final winner ACK or no-go | 0.5 day | Combined manifest, full SHA and decision matrix | Only Core Designer may issue final winner; unresolved threshold or mandatory result blocks decision |

The fixed 2A regression subset covers lifecycle/framing, product schema, timeout, force-abort,
history, provenance and offline behavior. P3 is exercised in P10B’s same catalog; P4 hot values are
sanity evidence. Any runtime/model/config/protocol/fixture change triggers full affected 2A rerun.

Re-estimate Gate 2B when Accepted Audio SHA/kit changes, combined process tree differs, 4GB resource
headroom falls below 10%, soak needs more than one rerun, or Core changes threshold semantics.

## Gate 2 Command Contract Self-test

The committed runner currently validates the frozen case plan only and cannot execute hardware:

```sh
python3 poc_llm/tools/run_m4b_gate.py --gate 2A --cases P1,P2,P3,P4,P5,P6,P7,P8,P10A,P11,P12 --plan-only
python3 poc_llm/tools/run_m4b_gate.py --gate 2B --cases P1,P2,P3,P4-HOT,P5,P7,P8,P9,P10B,P11,P12 --plan-only
```

Expected：exit `0`、`result=PLAN_VALID`、`execution_performed=false`。Removing `--plan-only`
returns exit `3` / `Blocked` until an exact candidate SHA、hardware adapter、evidence destination
and execution authorization are bound. This prevents the planning packet from being mistaken for
Gate 2 evidence; implementation of the real hardware adapter is an explicit package entry dependency.

## Currently Unresolved Core Decisions

- Exact dual-UTM operators, User-approved controlled offline wheel/dependency paths, immutable
  commands and raw paths must be returned for separate Core execution authorization; R5 exact-SHA
  acceptance remains held until platform evidence is reviewed.
- Which Ubuntu pre-screen platform and affected append-only packet revision are accepted after the
  preflight result.
- P4 actual Pi measurements may require Core threshold disposition; method is frozen, acceptance is not.
- A 4GB miss with valid 8GB results cannot become winner without an explicit Core contract exception.
- Exact Accepted Audio final handoff ID/SHA/kit is pending and blocks Gate 2B.
- Candidate/runtime/model/quantization pairings remain undecided until Gate 1 manifests are submitted.
