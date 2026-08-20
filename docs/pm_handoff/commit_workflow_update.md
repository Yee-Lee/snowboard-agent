# 開發驗證與 Git Commit 工作原則交接

為確保 POC 團隊與核心團隊之間的開發與驗證歷史保持一致，且具備完整的追溯性，請貴團隊在進行開發與代碼提交時，即日起全面導入以下 Git Commit 整理與協作原則：

## 1. 內部開發與 WIP 收斂 (Candidate Commit)
開發者（或協助開發的 Agent）在本地開發與試錯階段 (Fast Loop) 擁有完全的彈性，可自行管理 WIP commit。但在準備提交跨平台驗證、實體驗證或 Milestone 審核前，**必須將零碎的 WIP 收斂（Squash）成單一、乾淨的 Candidate Commit**。

## 2. 驗證退回不回退 (Append-only 精神)
一旦 Candidate Commit 送出驗證，該 SHA 憑證即視為凍結。
若驗證遭到 Reject 或硬體測試未通過，**嚴禁使用 `git reset` 或 `git rebase` 等方式回退或竄改歷史**。請直接將測試報告或審核 Feedback 文件寫入版本庫，並在原有的失敗代碼之上，繼續疊加新的修正 Commit（WIP on top），最終再將新增的修復內容收斂成下一個新的 Candidate SHA。

請將上述兩項核心守則納入貴團隊的 `AGENTS.md` 或開發工作流規範中。感謝配合！
