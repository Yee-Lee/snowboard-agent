# M4b Delivery Taxonomy and Cumulative Traceability Crosswalk

狀態：`CONTROLLED / GATE 2B USER-CLOSED / GEMMA POC WINNER / CORE FINAL ACK PENDING`

Owner：POC Technical Lead；External acceptance：Core Designer。

## Delivery areas

| ID | Area | Closure meaning |
| --- | --- | --- |
| D1 | Governance and manifest | gate、owner、SHA、finding、receipt與evidence chain可追蹤 |
| D2 | Runtime and model | runtime/model/config、license、checksum與setup固定 |
| D3 | Child protocol and recovery | lifecycle、timeout、cancel、force-abort、waitpid、rebuild固定 |
| D4 | Product output and isolation | schema、fallback、log hygiene、history通過 |
| D5 | Pi performance | P4 raw/P50/P95與resource diagnostics完整 |
| D6 | Stability and combined resources | P10A、P9、P10B、thermal/resource結果與任何waiver完整保留 |
| D7 | Candidate decisions | Gate 1 finalists、2A provisional、2B POC winner與Core final ACK權限清楚 |
| D8 | Provenance/offline/review safety | P11/P12、artifact/data boundary與review合規 |

## Cumulative gate crosswalk

| Gate | Internal milestone | Formal P items first executed | Evidence / decision | Owner / approver |
| --- | --- | --- | --- | --- |
| Gate 0 | M0 | none | contract/readiness receipts | POC / PM / Core |
| Gate 1 | M2 | P1, P6, P7, P10A, P11, P12 | `G1-PI-COMPAT-007`; stability/Core-fit；最多2 finalists | Test Controller + Technical Lead / Reviewer + User + Core |
| Gate 2A | M3 | P2, P3, P4, P5, P8 | final machine dispositions immutable；User選Gemma model finalist；Core ACK pending | Test Controller + Technical Lead / User / Core |
| Gate 2B | M4 | P9, P10B | Attempt 006 machine FAIL retained；User known-defect waiver selects Gemma POC winner；Core final ACK pending | Test Controller + Technical Lead / User / Core |
| Gate 3 | Core production | Core `M4B-*` | product exact-SHA acceptance | Core Developer / Tester / Designer |

## P1～P12 ownership

| P | Area | Owning scored packet | Later-stage rule | Current evidence |
| --- | --- | --- | --- | --- |
| P1 | D3 | Gate 1 `007` | 2A/2B do not rescore if identity unchanged | `Accepted Gate 1` |
| P2 | D4 | Gate 2A `002` | failed pairing cannot enter 2B；new revision uses held-out qualification | `Gemma FAIL 3/30; Qwen FAIL 0/30; immutable` |
| P3 | D4 | Gate 2A `002` | safety boundary remains independently mandatory | `PASS both candidates` |
| P4 | D5 | Gate 2A `002` | 2B may record hot sanity diagnostic only | `Gemma PASS; Qwen Core threshold decision required` |
| P5 | D3 | Gate 2A `002` | Pi-only; no workstation or routine 2B rerun | `PASS both candidates` |
| P6 | D3 | Gate 1 `007` | conditional only with same-manifest P7 PASS | `Accepted Gate 1 as P6.1` |
| P7 | D3 | Gate 1 `007` | 2A/2B ordinary cleanup is not P7 rescore | `Accepted Gate 1 as P7.1; Qwen FAIL waiver retained` |
| P8 | D4 | Gate 2A `002` | current FAIL retained；new integration qualification before 2B | `FAIL both; DEPENDENCY_LIMITED_BY_P2; no observed prior-state leak` |
| P9 | D6 | Gate 2B `001` | Accepted Audio mandatory; surrogate no credit; waiver never rewrites machine score | `FAIL; PSS resident-retention defect; User waiver / POC winner` |
| P10A | D6 | Gate 1 `007` | 2A does not repeat 20-session soak | `Accepted Gate 1` |
| P10B | D6 | Gate 2B `001` | same run as P9 | `FAIL through shared resource predicate; 20/20 functional; User waiver / POC winner` |
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
