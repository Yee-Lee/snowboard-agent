# M4b Delivery Taxonomy and Traceability Crosswalk

狀態：`CONTROLLED / GATE0-R1`

Owner：POC Technical Lead

External approver：Core Designer

最後更新：2026-08-18

本檔是 External Gate、Internal Milestone、Delivery Area、M4B-P1～P12、delivery item、
evidence 狀態與 owner 的唯一 crosswalk。其他 milestone、receipt、manifest 與 result
只能引用本檔的 ID；不得重新定義 D1–D8 或建立第二份 P1～P12 映射。

## Delivery Areas

| ID | 名稱 | 結案語意 |
| --- | --- | --- |
| D1 | Governance and Delivery Manifest | Gate、milestone、owner、SHA、finding、artifact 與 evidence 可追蹤 |
| D2 | Reproducible Runtime and Model | runtime/model/quantization/config、source、license、checksum 與 setup 固定 |
| D3 | Prompt Boundary and Child Protocol | output/protocol、request lifecycle、cancel/abort/recovery 與 exit proof 固定 |
| D4 | Functional and Isolation Evidence | output quality、validation、history isolation、failure 與 log hygiene 有效 |
| D5 | Pi 5 Performance and Resource Evidence | latency、throughput、RSS、CPU、disk、process/thread 與 Pi environment 可重現 |
| D6 | M4a Combined and Thermal Validation | Accepted M4a SHA 共存、20 sessions、thermal/soak 與 cleanup 通過 |
| D7 | Winner or No-go Decision | 所有候選 advance/reject 理由完整，唯一 winner 或 no-go 經核准 |
| D8 | Data, Artifact, Offline and Review Safety | offline、provenance、敏感資料與 raw/sanitized evidence 邊界合規 |

## Gate and Milestone Crosswalk

| External Gate | Internal work | Primary areas | Delivery item | Current evidence state | Owner / approver |
| --- | --- | --- | --- | --- | --- |
| Gate 0 | Administrative receipt | D1, D8 | `G0-RECEIPT-R1` | `Submitted; pending PM/Core record` | POC Team / PM recorder / Core Designer |
| Gate 0 | Initial manifest | D1, D8 | `G0-MANIFEST-R1` | `Submitted; non-executed fields Pending/Blocked` | POC Technical Lead / Core Designer |
| Pre-Gate 1 | M0 readiness | D1, D5, D8 | `M0-PACKET-001` | `Packet prepared; run Pending` | Developer + Test Controller / Internal Tester |
| Gate 1 | M1 frozen harness and pairing | D1, D2, D3, D4, D8 | `G1-CANDIDATE-MATRIX-R1` | `Pending` | POC Technical Lead / Core Designer |
| Gate 1 | M2 Ubuntu x86/arm64 pre-screen | D2, D4, D5, D7, D8 | `G1-UBUNTU-PRESCREEN-R1` | `Blocked by Gate 0 recording and runner readiness` | POC Test Controller / Core Designer |
| Gate 2 | M3 Pi candidate and child validation | D2, D3, D4, D5, D7, D8 | `G2-PI-VALIDATION-R1` | `Blocked by Gate 1 ACK` | POC Test Controller / Core Designer |
| Gate 2 | M4 combined validation and delivery | D1–D8 | `G2-COMBINED-DELIVERY-R1` | `Blocked by Gate 1 ACK and Accepted M4a SHA` | POC Test Controller + Technical Lead / Internal Tester + Core Designer |

## M4B Test Crosswalk

每個 Contract Test ID 只在本表指定一個 primary delivery area 與一個 primary internal
milestone；相關輔助 evidence 可被其他 area 引用，但不得改變 owner 或結案語意。

| Test ID | Primary area | Internal milestone | Delivery item | Required evidence summary | Current state | Execution owner / acceptance owner |
| --- | --- | --- | --- | --- | --- | --- |
| M4B-P1 | D3 | M3 | `G2-P01-CHILD-LIFECYCLE` | READY ≤10s、JSONL framing、clean shutdown | `Pending` | Test Controller / Internal Tester + Core Designer |
| M4B-P2 | D4 | M3 | `G2-P02-SINGLE-TURN` | 非空 result、合法 JSON intent | `Pending` | Test Controller / Internal Tester + Core Designer |
| M4B-P3 | D4 | M3 | `G2-P03-OUTPUT-QUALITY` | 20 prompts、leakage/亂碼/repetition 與格式率 | `Pending` | Test Controller / Internal Tester + Core Designer |
| M4B-P4 | D5 | M3 | `G2-P04-PERFORMANCE` | Pi TTFT p50/p95、tokens/sec | `Pending` | Test Controller / Internal Tester + Core Designer |
| M4B-P5 | D3 | M3 | `G2-P05-TIMEOUT` | 15s timeout、error code、process 不 hang | `Pending` | Test Controller / Internal Tester + Core Designer |
| M4B-P6 | D3 | M3 | `G2-P06-CANCEL` | cooperative cancel ≤500ms、恢復 READY | `Pending` | Test Controller / Internal Tester + Core Designer |
| M4B-P7 | D3 | M3 | `G2-P07-FORCE-ABORT` | SIGTERM/SIGKILL、waitpid、recovery、orphan=0 | `Pending` | Test Controller / Internal Tester + Core Designer |
| M4B-P8 | D4 | M3 | `G2-P08-HISTORY-ISOLATION` | 5 次 single-turn、無 KV/history pollution | `Pending` | Test Controller / Internal Tester + Core Designer |
| M4B-P9 | D6 | M4 | `G2-P09-COMBINED-RSS` | Accepted M4a 共存、RSS/CPU/temperature snapshot | `Blocked: M4a SHA` | Test Controller / Internal Tester + Core Designer |
| M4B-P10 | D6 | M4 | `G2-P10-THERMAL-SOAK` | 20 sessions、<80°C、無 throttling/leak | `Blocked: M4a SHA` | Test Controller / Internal Tester + Core Designer |
| M4B-P11 | D2 | M3 | `G2-P11-PROVENANCE` | clean Pi setup、versions、checksums、licenses | `Pending` | Developer + Test Controller / Internal Tester + Core Designer |
| M4B-P12 | D8 | M4 | `G2-P12-OFFLINE` | 網路停用、完整 inference、無 external call/token | `Pending authorization` | Test Controller / Internal Tester + Core Designer |

## Aggregate Decision Items

- D1 由 Gate 0 manifest 開始，持續追蹤每個 delivery item、exact SHA 與 evidence state。
- D7 不新增替代 Test ID；它聚合 M4B-P1～P12 的有效結果、rejected candidates 與
  performance exception，產出唯一 winner 或 evidence-backed no-go。
- Ubuntu pre-screen 只決定最多兩個 finalist，不產生 M4B-P1～P12 的 Pi `PASS`。
- Hardware 結果必須經 Internal Tester confirmation；POC self-test 或 Technical Lead
  review 不能單獨支撐正式 acceptance。
