# Agent entry rules

- 被指派角色（例如「請擔任 Developer」）時，只先讀取 `docs/roles/{role}.md` 與
  `docs/roles/workflow.md`。依其中的 task trigger 再讀相關規格；不得預載整個 `docs/`、
  `reviews/history/`、`outsource/deliveries/archive/` 或 `pm_handoff/history/`。
- 使用者要求「接手／繼續目前工作」時，再讀 `docs/status/current.md`；依其中的 next owner
  與精確路由決定是否載入其他文件。Gate 未開啟即停止，不以歷史推測任務。
- 交接預設只更新既有 owner 文件並在對 USER 的回覆中說明；建立新 Markdown 前先找既有
  authority/status/review。除非 USER 明確要求，或 `review-process.md`／外部交付契約要求
  一份具唯一 ID 的紀錄，不得新增 handoff、progress、summary、ACK 或重複規格文件。
- 未被指派角色時，不需讀角色文件；直接依使用者任務尋找最小必要上下文。
- 歷史文件只用於追查指定 ID、SHA 或決策來源，不是背景必讀，也不得覆蓋現行權威文件。

# Working principles

- 唯一交付流程是 `Design → Test Spec → Developer → Verify`。不得插入角色互簽、重複 review、
  文件核准或 candidate freeze 作為額外 gate；只有產品需求本身明定的真人判讀才保留人工結果。
- Designer 不得預設參與者會偽造、變造或冒用文件／身份，也不得以此假設設計多重簽核、身份
  證明或 authorization JSON。完整性風險以程式自動核對內容 digest、版本、設定與目標環境處理。
- 所有開發內容都必須在 Raspberry Pi 上以待提交的相同 bytes 完成適用的自動、整合、硬體與
  人工測試。Pi 驗證未完成或失敗時不得 commit；不得把首次上機驗證延後到 commit 之後。
- Pi 驗證以 tracked-only patch/content digest、設定與 artifact digest 綁定待提交內容。回工作站後
  必須先確認待提交 bytes 與已驗證內容完全一致；任何差異都回到 Developer 並重新上 Pi 驗證。

# Git safety

- 不得直接修改或存取 `.git/` 內部；版本控制一律使用標準 `git` 命令。
- 準備任何 commit 前，先讀 `docs/roles/git.md`。向 USER 展示完整 subject、60–100 words
  的英文條列 body 與待提交檔案，取得明確同意後才可 commit。
- 只有 `Verify` 已在 Pi 對相同內容完成且證據可定位時，才可準備 commit。
- Candidate 一經 push、送驗或正式驗證即不可改寫；Reject 後只能 append fix。
