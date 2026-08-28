# M4b Delivery Taxonomy and Cumulative Traceability Crosswalk

狀態：`CONTROLLED / CUMULATIVE GATES ACCEPTED / GATE 2 DEVELOPMENT READINESS APPROVED`

Owner：POC Technical Lead；External acceptance：Core Designer。

## Delivery areas

| ID | Area | Closure meaning |
| --- | --- | --- |
| D1 | Governance and manifest | gate、owner、SHA、finding、receipt與evidence chain可追蹤 |
| D2 | Runtime and model | runtime/model/config、license、checksum與setup固定 |
| D3 | Child protocol and recovery | lifecycle、timeout、cancel、force-abort、waitpid、rebuild固定 |
| D4 | Product output and isolation | schema、fallback、log hygiene、history通過 |
| D5 | Pi performance | P4 raw/P50/P95與resource diagnostics完整 |
| D6 | Stability and combined resources | P10A、P9、P10B與thermal/resource gates通過 |
| D7 | Candidate decisions | Gate 1 finalists、2A provisional、2B final winner權限清楚 |
| D8 | Provenance/offline/review safety | P11/P12、artifact/data boundary與review合規 |

## Cumulative gate crosswalk

| Gate | Internal milestone | Formal P items first executed | Evidence / decision | Owner / approver |
| --- | --- | --- | --- | --- |
| Gate 0 | M0 | none | contract/readiness receipts | POC / PM / Core |
| Gate 1 | M2 | P1, P6, P7, P10A, P11, P12 | `G1-PI-COMPAT-007`; stability/Core-fit；最多2 finalists | Test Controller + Technical Lead / Reviewer + User + Core |
| Gate 2A | M3 | P2, P3, P4, P5, P8 | `G2A-PI-LLM-002`; combine Gate 1 receipt；最多1 provisional finalist | Test Controller + Technical Lead / Reviewer + User + Core |
| Gate 2B | M4 | P9, P10B | `G2B-PI-COMBINED-001`; Accepted Audio；final winner/no-go | Test Controller + Technical Lead / Reviewer + User + Core |
| Gate 3 | Core production | Core `M4B-*` | product exact-SHA acceptance | Core Developer / Tester / Designer |

## P1～P12 ownership

| P | Area | Owning scored packet | Later-stage rule | Current evidence |
| --- | --- | --- | --- | --- |
| P1 | D3 | Gate 1 `007` | 2A/2B do not rescore if identity unchanged | `Accepted Gate 1` |
| P2 | D4 | Gate 2A `002` | 2B only change-affected regression | `Pending Gate 2A / Pi not authorized` |
| P3 | D4 | Gate 2A `002` | P10B outputs observed but not relabelled P3 | `Pending Gate 2A / Pi not authorized` |
| P4 | D5 | Gate 2A `002` | 2B may record hot sanity diagnostic only | `Pending Gate 2A / Pi not authorized` |
| P5 | D3 | Gate 2A `002` | Pi-only; no workstation or routine 2B rerun | `Pending Gate 2A / Pi not authorized` |
| P6 | D3 | Gate 1 `007` | conditional only with same-manifest P7 PASS | `Accepted Gate 1 as P6.1` |
| P7 | D3 | Gate 1 `007` | 2A/2B ordinary cleanup is not P7 rescore | `Accepted Gate 1 as P7.1; Qwen FAIL waiver retained` |
| P8 | D4 | Gate 2A `002` | 2B no routine rerun | `Pending Gate 2A / Pi not authorized` |
| P9 | D6 | Gate 2B `001` | Accepted Audio mandatory; surrogate no credit | `Blocked: Gate 2A receipt / Pi authorization and staging` |
| P10A | D6 | Gate 1 `007` | 2A does not repeat 20-session soak | `Accepted Gate 1` |
| P10B | D6 | Gate 2B `001` | same run as P9 | `Blocked: Gate 2A receipt / Pi authorization and staging` |
| P11 | D8 | Gate 1 `007` | later packets authenticate receipt; drift returns to P11 | `Accepted Gate 1` |
| P12 | D8 | Gate 1 `007` | later run observes current offline state without rescoring accepted P12 | `Accepted Gate 1` |

## Carry-forward invariant

An accepted P item may be consumed later only when its execution commit is an ancestor of the current
clean checkout and its execution-surface lock digest, candidate/runtime/model/config/protocol/fixture
SHA, Pi hardware/OS, `swap=0`, offline envelope and evidence-manifest SHA match. Evidence, ACK,
delivery and milestone-documentation commits may advance `HEAD` without invalidation. Execution
identity mismatch invalidates affected evidence and blocks the consumer. Gate transitions alone never
require a rerun; a changed combined boundary permits only a predeclared focused regression.

Historical `G1-PI-COMPAT-006` remains preserved as packet-defect evidence with no P credit. UTM,
workstation, plan-only and unit-test results never satisfy Pi P items.

All method details and result semantics are controlled by
[M4b Authoritative POC Execution Plan](m4b_execution_plan.md).
