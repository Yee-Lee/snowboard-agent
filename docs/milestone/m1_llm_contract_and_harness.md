# LLM M1：Frozen Contract, Candidate Pairing and Deterministic Harness

狀態：`GATE_REVIEW`

## 目標與交付貢獻

在揭露真實 candidate 結果前，凍結 Reasoner/LLM boundary、protocol semantics、
fixtures、metrics、資源門檻與比較方法，固定 runtime/model/quantization 的有效 pairing，
並用 deterministic fake 證明 harness 能正確觀察 failure lifecycle。主要推進
D1、D2、D3、D4、D8。

## Entry Conditions

- External Gate 0 已由 Core Designer 登錄為 `COMPLETE`。
- M0 為 `COMPLETE`，Internal Tester confirmation 為 `PASS`。
- Designer、Internal Tester 與 Technical Lead 的 gate owner/approver 已登錄。
- Core 已確認完整 M1 authority set，且沒有缺少額外 standalone development guide。
- Prompt/output/protocol 與候選 gate 尚未受真實 benchmark 結果影響。

## Entry Review Record

- Entry review date：2026-08-19。
- User confirmed internal review passed；Internal M0 已在 `eeb00e341056ccef77c10ae8ca4bcbbbfa683d39`
  標示為 `COMPLETE`，且 workstation、`origin/llm`、Pi clean checkout 已對齊該 SHA。
- Core Designer 的 Gate 0 R2 ACK 接受 planning/regression packet；2026-08-19 platform
  change ACK 另批准以 `G1-X86-PI-COMPAT-004` 取代 packet 003；Core 已於
  `a99009fd5378d987411f37686814c84a1cb2a713` 完成 exact-SHA intake 並接受 Revision 004。
- 本次授權只涵蓋 contract/schema/fixture/pairing preflight 與 deterministic fake tests。
  Packet 的真實 Ubuntu candidate execution 仍標示 `EXECUTION NOT AUTHORIZED`；Pi 也不得
  提前執行 Gate 2A。
- 2026-08-20 Core 以 `DELIVERY-LLM-POC-M1-FREEZE-REVISION-001` 確認完整 authority
  set，不需再進行 checklist discovery；R1 exact candidate 被拒絕，須以單一 append-only
  replacement 修正四項 finding。

## Work Packet

- 固定 PromptBuilder input、capability view、`speak/tool/rest` schema、validator 與 P5 fallback。
- 固定 single-turn/history-isolation、log hygiene 與 strict-config 語意。
- 定義 protocol version、READY、GENERATE、RESULT、CANCEL、ERROR、SHUTDOWN、
  request ID、deadline 與 completion/exit proof。
- 建立 candidate manifest、fixture catalog、result/evidence schemas 與 deterministic fake。
- 為每個 runtime/model/quantization/config pairing 配發固定 candidate ID；記錄 exact
  version、source/archive SHA-256、artifact SHA-256、quantization method、license、offline
  取得方法與 aarch64 compatibility preflight。
- 固定 candidate identity、warm-up、repetitions、cold/hot、p50/p95、tokens/s、RSS、
  CPU、disk、thermal 與 validity gate 的量測方法。
- Fake 覆蓋 success、malformed output、timeout、cancel、stale/duplicate result、crash、
  force-abort、rebuild、shutdown 與 orphan=0。

## Exit Gate

- Designer 明確批准 contract 與不可協商 validity/resource/cleanup gates。
- Tester 批准 test packet、fixtures、metrics、schema 與 evidence completeness rules。
- Deterministic fake tests 可重現且所有 lifecycle/cleanup assertions 通過。
- Candidate manifest 能區分 runtime/model/quantization/config 的每一個新 run。
- M2 不需要看到候選結果後再補定義或調整門檻。

## Necessary Evidence

- Frozen decision record、approver、日期與版本。
- Protocol/output/config schema 與 fixtures checksum。
- Fake run commands、results、fault matrix 與 cleanup proof。
- M2 Ubuntu 24.04 x86完整初篩、最多兩名不可變preselection、產品Pi compatibility、
  license/source/offline/aarch64 acquired-bundle proof 與固定 benchmark packet。

## Current Evidence and Open Exit Conditions

- R1 [`M1-FROZEN-CONTRACT-001`](../response/ACK-M1-FROZEN-CONTRACT-001.md) 已由 Core 在
  exact SHA `0b5a92872f8a695b145b389168111420cd2592c5` 拒絕；該 SHA 保持 immutable，且不再是
  freeze candidate。
- R2 [`M1-FREEZE-CANDIDATE-002`](../response/RESP-DELIVERY-LLM-POC-M1-FREEZE-REVISION-001.md)
  已由 Core Revision 002 關閉 `M1-FREEZE-001/002/004`；R2 exact SHA
  `93b34c14d5ee0f767ee16dd0fbbbb72e18775760` 因 post-FATAL false-pass 未獲 freeze。
- R3 [`M1-FREEZE-003-R2`](../response/RESP-DELIVERY-LLM-POC-M1-FREEZE-REVISION-002.md)
  只修改 lifecycle validator、六類 post-FATAL direct regression 與兩個 lock hashes。Exact
  review target `llm` / `830d0b4ed2d41406c789bb110ed84b7553f330a4` 的 self-test
  `PASS`、targeted 20/20、combined 35/35；已由
  [`DELIVERY-006`](../delivery/DELIVERY-006-PM-LLM-POC-M1-FREEZE-CANDIDATE-R3.md) 請求
  locked-scope review。
- Core repo 的 `DELIVERY-LLM-POC-M1-FREEZE-R3-ACK-001` 已由 Designer freeze 同一 exact
  SHA、關閉唯一 blocker 且不新增 blocker；目前 candidate-affecting paths 與 frozen SHA
  無差異。POC intake record：
  [`ACK-DELIVERY-LLM-POC-M1-FREEZE-R3-001`](../response/ACK-DELIVERY-LLM-POC-M1-FREEZE-R3-001.md)。
- `M1-FAKE-001`：Gate 1 deterministic suite 6/6 與 validator self-test 通過；僅為 POC
  Team fake/regression observation，不是 candidate evidence 或 Internal Tester confirmation。
- `G1-CANDIDATE-PREFLIGHT-001`：已從官方 metadata 固定 LiteRT-LM v0.16.0 的兩平台
  wheel SHA-256，以及 Gemma4-E2B、Qwen2.5-1.5B、Qwen2.5-0.5B 的 upstream revision、
  artifact SHA-256、size 與 license proposal。
- Forward Gate 1/M2 dependency：artifact/dependency bundle、source/archive checksum、candidate
  adapter、strict config instance 與實體 manifest 尚未取得；Designer ACK 明確表示這些不再
  阻擋 M1 freeze，但未授權真實 candidate run。
- `G1-X86-PI-COMPAT-004`：candidate/acquisition identity、x86/Pi/aggregate schemas、一次
  max-two preselection、Pi eligibility filter、no-backfill與Gate 2 carry-over guard已形成；
  Core 已確認 revision-004 regressions 9/9、retained revision-003 regressions 6/6、validator
  self-test `PASS` 與 Gate 2A/2B plan validation `PLAN_VALID`；packet revision 已完成。
- Forward Gate 1/M2 authorization：workstation x86 owner/raw path、artifact acquisition與real
  execution尚未批准；Pi try-run另需x86 preselection、artifact transfer/install、
  network-disabled與cleanup授權。這些不是 M1 Tester sign-off 的新增條件。
- Open：只待 Internal Tester 對 frozen exact SHA、lock、self-test、20/20、35/35 與
  candidate-path immutability 獨立 sign-off；完成前 M1 不得標示 `COMPLETE` 或建立 `m1` tag。

## Prohibited in M1

- 不執行或選定真實 candidate winner。
- 不因預期候選能力降低 gate。
- 不修改產品 composition root、StateManager 或 Audio model selection。
