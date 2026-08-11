當被指派角色時（如「請擔任 XXX」），AI 須立刻用 `view_file` 讀取 `docs/roles/{xxx}.md`（小寫）的原則與限制，並閱讀 `docs/roles/workflow.md` 以遵循工作流程規範。

- 所有 AI 在準備任何 `git commit` 前，無論是否被指派角色，均須先讀取 `docs/roles/workflow.md` 的 Git Commit Message 規範，並在取得 USER 明確確認前展示完整的標題、Body 與待提交檔案。

- Git 操作原則：禁止直接修改或存取 `.git/` 目錄內部的檔案與結構；所有 Git 版本控制操作必須一律使用標準 `git` 命令執行。執行 `git commit` 前，必須先向使用者（USER）確認，獲得同意後方可執行提交。
