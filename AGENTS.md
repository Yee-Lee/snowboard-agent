當被指派角色時（如「請擔任 XXX」），AI 須立刻用 `view_file` 讀取 `docs/roles/{xxx}.md`（小寫）的原則與限制，並閱讀 `docs/roles/workflow.md` 以遵循工作流程規範。

- 所有 AI 在準備任何 `git commit` 前，無論是否被指派角色，均須先讀取 `docs/roles/workflow.md` 的 Git Commit Message 規範，並在取得 USER 明確確認前展示完整的標題、Body 與待提交檔案。

- Git 操作原則：禁止直接修改或存取 `.git/` 目錄內部的檔案與結構；所有 Git 版本控制操作必須一律使用標準 `git` 命令執行。執行 `git commit` 前，必須先向使用者（USER）確認，獲得同意後方可執行提交。

- 開發驗證與 Commit 整理：
  1. 開發者 (Agent) 自行管理本地 WIP commit，送交驗證前須收斂。
  2. 驗證遭 Reject 的 SHA 不要求回退，應直接記錄 Feedback 並向前疊加修正 (Append-only)。

- Core 只維持一條永久開發分支 `core`；不再為 milestone 建立 `dev_agent_m*` 或其他長期分支。舊分支僅作歷史參考，不刪除、不改寫。
- Candidate SHA 一旦 push、送驗或用於正式驗證即不可變；禁止 amend、rebase、reset 或 force-push 改寫該 SHA，Reject 後只能 append fix 產生新 candidate。
- Milestone 只在正式 Accepted 後對 completion commit 建立小寫 annotated tag `core_m1`、`core_m2`、……；tag 不得刪除、重建或移動。M0 不是 Core milestone，不建立 `core_m0`。
