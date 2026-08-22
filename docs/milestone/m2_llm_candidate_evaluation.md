# LLM M2：x86 Candidate Pre-screen, Pi Compatibility and Gate 1 Submission

狀態：`NOT_STARTED`

## 目標與交付貢獻

依 M1 frozen packet 在 Ubuntu 24.04 x86_64 執行完整 pairing 初篩，一次預選最多兩名，
再於產品 Debian 13 Pi 執行 bounded compatibility try-run，只保留Pi `PASS`者並提交
External Gate 1 candidate proposal。主要推進 D2、D4、D5、D7、D8。

x86與Gate 1 Pi compatibility只用於Gate 1 selection，不得取代任何Gate 2A M4B-P1～P12 evidence。

## Entry Conditions

- External Gate 0 已由 Core Designer 登錄為 `COMPLETE`，M1 為 `COMPLETE`。
- Candidate matrix 已為每個 runtime/model/quantization/config pairing 配發不可變 ID。
- Exact version、source/archive SHA-256、model/artifact SHA-256、quantization method、license、
  offline 取得方法、transitive dependencies 與 aarch64 compatibility preflight 已固定。
- Ubuntu 24.04 x86 runner與產品Pi的OS/architecture、owner、storage/memory及執行方式已
  登錄；任何下載、安裝、artifact transfer或network切換已另行核准。
- Benchmark packet、fixtures、metrics、淘汰規則、重跑上限與 evidence schema 已 frozen。

## Work Packet

Authoritative repository packet：`poc_llm/tests/gate1/GATE1-PACKET-005.md`。Frozen catalog、
validator、platform-projection runners、schemas 與 checksums 由
`poc_llm/harness/gate1-lock-v5.json` 控制。真實執行須待 Core 接受 R5 exact SHA 並另行授權。

- 在x86對每個有效pairing執行完整portable packet，依固定排序一次預選最多兩名；只對
  預選者執行產品Pi compatibility，`FAIL/INCONCLUSIVE`同cycle不得以第三名補位。
- 每個 run 記錄 runner environment、candidate/config/fixture IDs、命令、開始/結束時間、
  exit code、artifact checksum、raw evidence checksum 與 cleanup proof。
- 初篩 metrics 至少包含 setup success、READY/generate smoke、JSON intent 格式率、
  timeout/cancel/cleanup observability、latency/tokens-per-second sample、RSS 與 disk footprint。
- 固定淘汰條件：license/source/checksum 不完整、無可重現 offline setup、arm64 incompatibility、
  lifecycle/cleanup failure、無法產生合法 single-turn output，或超出 frozen hard resource gate。
- Performance 未達起始目標但未觸犯 hard gate 時保留實測值，由 Designer 比較；不得事後
  改 gate。Environment failure 記為 `INCONCLUSIVE`，不能直接淘汰 candidate。
- 依 validity、correctness、resource headroom、reproducibility 與風險排序，最多保留兩個
  finalists；提交 candidate matrix、license table、rejected reasons 與 Gate 1 request。

## Exit Gate

- 每個pairing都有固定ID、x86 evidence state；預選者另有Pi compatibility state與理由。
- 最多兩個 finalists 通過所有 frozen Ubuntu hard gates，或提交 evidence-backed no-go／
  change request；不得把 `INCONCLUSIVE` 當成 `PASS` 或任意淘汰。
- POC Technical Lead 完成 evidence review，Internal Tester 確認 packet/result 完整性。
- Core Designer 對 candidate proposal 與最多兩個 proposed finalists 發出 External Gate 1
  書面 ACK；在 ACK
  到位前 M2 可進 `GATE_REVIEW`，但 M3/Pi Gate 2A 必須保持 `NOT_STARTED / BLOCKED`。

## Necessary Evidence

- Candidate matrix、pairing IDs、versions、source/artifact checksums、license 與 offline method。
- Ubuntu x86 environment與產品Pi compatibility commands、exit、metrics/observations、raw
  evidence checksums、selection cycle與cleanup。
- 淘汰矩陣、最多兩個 finalists、residual risks、Internal Tester confirmation 與 Gate 1 request。
- Core Designer Gate 1 ACK，或尚未核准時的明確 `GATE_REVIEW / BLOCKED` 狀態。

## Owner, Schedule and Retry Limit

- Developer：setup、runner 與 local self-test；POC Test Controller：immutable Ubuntu runs。
- Technical Lead：evidence review 與 finalist recommendation；Internal Tester：完整性確認；
  Core Designer：Gate 1 approver。
- Runner 可用後預估 3–5 個工作日；artifact download/storage 依 candidate matrix 另行核准。
- 每個 candidate/case 最多一次 controlled rerun；原始結果保留。超過上限須提出 change request。

## Prohibited in M2

- 不在 R5 exact-SHA acceptance 與 execution authorization 前開始真實 x86/Pi Gate 1 run；
  不在 Gate 1 finalist ACK 前開始 Raspberry Pi 5 Gate 2A benchmark。
- 不以 Ubuntu 結果宣告 Pi M4B-P1～P12 `PASS`、Gate 2A provisional finalist 或 final winner。
- 不提交模型、大型 raw result、private prompt/output、endpoint、credential 或 secret。
- 不因結果不佳更改 pairing ID、fixture、metric、淘汰規則或只發布最好一次。
