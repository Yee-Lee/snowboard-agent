# M4b Delivery Taxonomy and Traceability Crosswalk

狀態：`CONTROLLED / CORE-2026-08-19-R2`

Owner：POC Technical Lead

External approver：Core Designer

本檔是 External Gate、Internal Milestone、D1–D8、M4B-P1～P12、evidence 與 owner 的
唯一 crosswalk。Gate 2A 只能產生 provisional finalist；Gate 2B 全部 mandatory gate
通過後，Core Designer 才能決定 final winner。

## Delivery Areas

| ID | Unique area | Closure meaning |
| --- | --- | --- |
| D1 | Governance and Delivery Manifest | Gate、owner、SHA、finding、artifact 與 evidence 可追蹤 |
| D2 | Reproducible Runtime and Model | runtime/model/quantization/config、license、checksum 與 setup 固定 |
| D3 | Child Protocol and Recovery | lifecycle、timeout、Level 1/2/3、waitpid 與 recovery 固定 |
| D4 | Product Output and Isolation | P2/P3、fallback、log hygiene、history isolation 有效 |
| D5 | Pi Performance | P4 固定方法、raw/P50/P95、RSS/CPU/disk evidence 完整 |
| D6 | Combined Resource and Soak | Accepted Audio、P9、P10A/P10B、thermal/resource gate 通過 |
| D7 | Provisional/Final Decision | 2A provisional 與 2B final winner/no-go 權限清楚 |
| D8 | Provenance, Offline and Review Safety | P11/P12、artifact/data 邊界與獨立 review 合規 |

## Gate Crosswalk

| External gate | Internal milestone | Primary areas | P IDs | Evidence / decision | Owner / approver |
| --- | --- | --- | --- | --- | --- |
| Gate 0 | M0 administrative/readiness mapping；狀態仍分離 | D1, D8 | N/A | revision receipt、R2 manifest、committed packets | POC Team / PM / Core Designer |
| Gate 1 | M1 frozen harness + M2 x86/Pi compatibility | D1, D2, D3, D4, D5, D8 | x86 portable P1/P2/P3/P4/P5/P6/P8 + P11；Pi `G1-PI-COMPAT-004` | x86一次預選最多2名、Pi PASS後置filter、無2A credit、Core ACK | Test Controller / Core Designer |
| Gate 2A | M3 LLM-only Pi | D2, D3, D4, D5, D6, D7, D8 | P1～P8、P10A、P11、P12 | 4GB mandatory；provisional finalist ACK only | Test Controller + Technical Lead / Internal Tester + Core Designer |
| Gate 2B | M4 Audio+LLM combined | D3, D4, D5, D6, D7, D8 | P9、P10B、required 2A regression | Accepted Audio package、4GB combined、final winner ACK | Test Controller + Technical Lead / Internal Tester + Core Designer |
| Gate 3 | Core production M4b | Core-owned | Core `M4B-*` | product exact-SHA acceptance | Core Developer / Tester / Designer |

## Test Crosswalk

| Test | Primary area | Gate / milestone | Classification | Evidence state | Decision owner |
| --- | --- | --- | --- | --- | --- |
| P1 | D3 | 2A/M3；2B regression | Mandatory | `Pending` | Internal Tester + Core Designer |
| P2 | D4 | Gate 1 portable；2A/M3；2B regression | Mandatory, 100% | Catalog/validator prepared；runs `Pending` | Internal Tester + Core Designer |
| P3 | D4 | Gate 1 portable；2A/M3；2B catalog regression | Mandatory, no leakage | Catalog/validator prepared；runs `Pending` | Internal Tester + Core Designer |
| P4 | D5 | Gate 1 sample；2A/M3；2B hot sanity | Negotiable performance | `Pending` | Core threshold decision if target missed |
| P5 | D3 | Gate 1 portable；2A/M3；2B regression | Mandatory | `Pending` | Internal Tester + Core Designer |
| P6 | D3 | Gate 1 portable；2A/M3 | Conditional escalation | `Pending` | Eligible only when P7 fully passes |
| P7 | D3 | 2A/M3；2B regression | Mandatory | `Pending` | Internal Tester + Core Designer |
| P8 | D4 | Gate 1 portable；2A/M3；2B regression | Mandatory | `Pending` | Internal Tester + Core Designer |
| P9 | D6 | 2B/M4 | Mandatory for final winner | `Blocked: Accepted Audio package` | Internal Tester + Core Designer |
| P10A | D6 | 2A/M3 | Mandatory for provisional finalist | `Pending` | Internal Tester + Core Designer |
| P10B | D6 | 2B/M4 | Mandatory for final winner | `Blocked: Accepted Audio package` | Internal Tester + Core Designer |
| P11 | D8 | Gate 1 provenance；2A/M3；2B hash regression | Mandatory | `Pending` | Internal Tester + Core Designer |
| P12 | D8 | 2A/M3；2B regression | Mandatory | `Pending authorization` | Internal Tester + Core Designer |

## Required 2A Regression in 2B

- Always rerun P1、P2、P5、P7、P8、P11、P12 against the identical candidate/config/fixture SHA.
- P3 is rerun through P10B’s same 20-case catalog; P4 hot values are recorded as sanity evidence.
- Any runtime/model/config/protocol/fixture change invalidates the affected 2A baseline and triggers
  a full affected rerun, not a narrowed regression.

All result semantics and work-package details are controlled by
[M4b Authoritative POC Execution Plan](m4b_execution_plan.md).
