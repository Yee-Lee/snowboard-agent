# LLM M2：Runtime and Model Candidate Evaluation

狀態：`NOT_STARTED`

## 目標與交付貢獻

依 M1 frozen packet，在 Raspberry Pi 5 公平比較 LiteRT-LM runtime/model/quantization
candidates，保留成功與失敗結果，提出 finalists 或 evidence-backed no-go。主要推進
D2、D4、D5、D7、D8。

## Entry Conditions

- M1 `COMPLETE`，contract、candidate manifest、fixtures、metrics 與 gates 均已 frozen。
- 每個 artifact 的來源、license、checksum、quantization 與受控儲存位置已確認。
- Pi checkout 使用可 fetch 的 exact full SHA，pre-test 通過且 worktree clean。
- Candidate/runtime 安裝或 artifact transfer 已另行取得所需核准。

## Work Packet

- 依固定順序與相同 fixture/config 執行 correctness、cold/hot 與 resource runs。
- 測量 cold READY、generation p50/p95、tokens/s、RSS、CPU、disk、threads/processes、
  temperature 與 throttling。
- 驗證合法 action、malformed output/P5、capability、history isolation、offline 與 log hygiene。
- 對 timeout、cancel、crash 與 force-abort 執行固定 fault packet，確認 exit proof/orphan=0。
- 每次變更 runtime、model、quantization 或 frozen parameter 都建立新的 candidate ID。

## Exit Gate

- 所有已執行 candidates 都有完整 manifest、raw evidence index 與 advance/reject 理由。
- 至少一個 finalist 通過全部 M2 gates，或正式提交 no-go/change request。
- 無 cherry-pick repetitions、事後 gate 修改或以 Ubuntu/其他硬體取代 Pi 5 結果。
- Technical Lead 審查 Tester evidence 後做 `PASS`、`FAIL` 或 `INCONCLUSIVE` 判定。

## Necessary Evidence

- Exact SHA、Pi environment、candidate/artifact/config/fixture IDs。
- Raw result checksum、sanitized metrics、exit codes、thermal 與 cleanup proof。
- Candidate comparison、rejected results、risks 與 finalist/no-go recommendation。

## Prohibited in M2

- 不把 benchmark wrapper 直接接入產品 composition root。
- 不修改 M4a Audio baseline或讓模型執行 tool handler。
- 不提交模型、大型 raw result、private prompt/output 或 secret。
