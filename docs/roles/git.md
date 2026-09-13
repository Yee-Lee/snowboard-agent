# Git delivery rules

僅在準備 commit、candidate、tag、push 或歷史整理時讀取。

## Safety and history

- 不頻繁 commit；只有待提交內容已在 Pi 完成 Verify 的交付點才可建立。
- 不直接讀寫 `.git/` 內部；所有版本控制操作使用標準 `git` 命令。
- Core 只維持永久分支 `core`。舊 milestone／development branches 只供歷史參考，
  不刪除、不改寫。
- 未提交 WIP 先在 Pi 測試並以完整 content digest 綁定。Candidate SHA 一旦建立、push 或交付，
  禁止 amend、rebase、reset 或 force-push；若後續發現問題，保留 evidence，以 append fix 產生新 SHA。
- Milestone 僅在正式 Accepted 後，對 completion commit 建立不可移動的小寫 annotated tag
  `core_m1`、`core_m2`……；tag 不得刪除、重建或改指其他 SHA，M0 不建 tag。
  Delivery/evidence 仍記完整 40-character SHA。

## Commit approval and message

Commit 前必須向 USER 展示 subject、完整 body 與檔案清單，取得明確同意後才能執行。

在展示 commit proposal 前，必須先提供同一份待提交內容的 Pi Verify evidence locator、content
digest、測試命令與結果。Pi 未執行、未完整通過、evidence 無法定位，或工作站 staged bytes 與
已驗證 digest 不同時，一律不得 commit。Commit 後只允許核對 commit tree 與已驗證內容相同；
不得把首次 Pi 執行安排在 commit 後，也不得以「先 commit 再看 Pi 是否失敗」作為開發流程。

- Subject：`{work-type}{milestone/stage}: {title}`，例如
  `docs[M4A]: handoff — archive accepted Audio input`。
- work type：`feat`、`fix`、`docs`、`test`、`refactor`、`chore`。
- 外部往返的 title category 可用 `handoff`、`ack`、`review`、`response`、`plan`、`evidence`。
- Body：英文 `-` 條列，合計 60–100 words；說明修改與原因，必要時引用 Handoff/Finding ID。
- 依實質內容選 work type；不得用 `docs` 隱藏 source、test、dependency、config 或 runner 變更。

Commit 前人工檢查 `git diff --cached`，確認不含 credential、私人家目錄、host identity、
工作站型號／OS、原始私有測試內容或大型 payload。涉及 Pi／POC evidence 時執行
`python scripts/privacy_gate.py scan-staged`；標準化公開 evidence JSON 加 `--strict-evidence`。
`Yee.Lee` 與 `yeelee.tw@gmail.com` 是已核准的公開 identity。
