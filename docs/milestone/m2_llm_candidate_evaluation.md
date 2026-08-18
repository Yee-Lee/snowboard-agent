# LLM M2：Ubuntu Candidate Pre-screen and Gate 1 Submission

狀態：`NOT_STARTED`

## 目標與交付貢獻

依 M1 frozen packet 在 Ubuntu x86/arm64 執行 runtime/model/quantization pairing 初篩，
保留成功與失敗 evidence，以固定淘汰規則選出最多兩個 Raspberry Pi 5 finalists，並
提交 External Gate 1 candidate proposal。主要推進 D2、D4、D5、D7、D8。

Ubuntu 結果只用於 Gate 1 finalist selection，不得取代任何 M4B-P1～P12 Pi evidence。

## Entry Conditions

- External Gate 0 已由 Core Designer 登錄為 `COMPLETE`，M1 為 `COMPLETE`。
- Candidate matrix 已為每個 runtime/model/quantization/config pairing 配發不可變 ID。
- Exact version、source/archive SHA-256、model/artifact SHA-256、quantization method、license、
  offline 取得方法、transitive dependencies 與 aarch64 compatibility preflight 已固定。
- Ubuntu x86 與 arm64 runner 的 OS/architecture、owner、available storage/memory 與執行
  方式已登錄；任何下載、安裝或 artifact transfer 已另行核准。
- Benchmark packet、fixtures、metrics、淘汰規則、重跑上限與 evidence schema 已 frozen。

## Work Packet

Authoritative executable packet：`poc_llm/tests/gate1/GATE1-PACKET-001.md`。Frozen catalog、
validator、runner、schemas 與 checksums 由 `poc_llm/harness/gate1-lock.json` 控制。

- 在 x86 與 arm64 對每個有效 pairing 執行相同 setup、smoke、format、lifecycle、offline
  preflight 與輕量 performance packet，保存每次有效/無效結果。
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

- 每個 pairing 都有固定 ID、x86/arm64 evidence state 與 advance/reject 理由。
- 最多兩個 finalists 通過所有 frozen Ubuntu hard gates，或提交 evidence-backed no-go／
  change request；不得把 `INCONCLUSIVE` 當成 `PASS` 或任意淘汰。
- POC Technical Lead 完成 evidence review，Internal Tester 確認 packet/result 完整性。
- Core Designer 對 candidate proposal 與最多兩個 proposed finalists 發出 External Gate 1
  書面 ACK；在 ACK
  到位前 M2 可進 `GATE_REVIEW`，但 M3/Pi Gate 2A 必須保持 `NOT_STARTED / BLOCKED`。

## Necessary Evidence

- Candidate matrix、pairing IDs、versions、source/artifact checksums、license 與 offline method。
- Ubuntu x86/arm64 environment、commands、exit codes、metrics、raw evidence checksums 與 cleanup。
- 淘汰矩陣、最多兩個 finalists、residual risks、Internal Tester confirmation 與 Gate 1 request。
- Core Designer Gate 1 ACK，或尚未核准時的明確 `GATE_REVIEW / BLOCKED` 狀態。

## Owner, Schedule and Retry Limit

- Developer：setup、runner 與 local self-test；POC Test Controller：immutable Ubuntu runs。
- Technical Lead：evidence review 與 finalist recommendation；Internal Tester：完整性確認；
  Core Designer：Gate 1 approver。
- Runner 可用後預估 3–5 個工作日；artifact download/storage 依 candidate matrix 另行核准。
- 每個 candidate/case 最多一次 controlled rerun；原始結果保留。超過上限須提出 change request。

## Prohibited in M2

- 不在 Gate 1 ACK 前開始 Raspberry Pi 5 candidate benchmark 或 Gate 2A 測試。
- 不以 Ubuntu 結果宣告 Pi M4B-P1～P12 `PASS`、Gate 2A provisional finalist 或 final winner。
- 不提交模型、大型 raw result、private prompt/output、endpoint、credential 或 secret。
- 不因結果不佳更改 pairing ID、fixture、metric、淘汰規則或只發布最好一次。
