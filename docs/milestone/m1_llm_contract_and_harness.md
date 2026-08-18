# LLM M1：Frozen Contract, Candidate Pairing and Deterministic Harness

狀態：`NOT_STARTED`

## 目標與交付貢獻

在揭露真實 candidate 結果前，凍結 Reasoner/LLM boundary、protocol semantics、
fixtures、metrics、資源門檻與比較方法，固定 runtime/model/quantization 的有效 pairing，
並用 deterministic fake 證明 harness 能正確觀察 failure lifecycle。主要推進
D1、D2、D3、D4、D8。

## Entry Conditions

- External Gate 0 已由 Core Designer 登錄為 `COMPLETE`。
- M0 為 `COMPLETE`，Internal Tester confirmation 為 `PASS`。
- Designer、Internal Tester 與 Technical Lead 的 gate owner/approver 已登錄。
- 正式 checklist/development guide 已收到；若仍未收到，只有不依賴未定語意的
  scaffold 工作可執行，milestone 不得關閉。
- Prompt/output/protocol 與候選 gate 尚未受真實 benchmark 結果影響。

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
- M2 Ubuntu x86/arm64 candidate set、license/source/offline/aarch64 preflight 與固定
  benchmark packet。

## Prohibited in M1

- 不執行或選定真實 candidate winner。
- 不因預期候選能力降低 gate。
- 不修改產品 composition root、StateManager 或 Audio model selection。
