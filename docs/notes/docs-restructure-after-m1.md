# NOTE：M1 定版後的 docs 重構

狀態：暫存、非權威文件。此 Note 不修改架構、設計、milestone 或 test gate。

## 時程決策

- 現在只新增精簡 M1 runbook，不進行大範圍 rename / move。
- M1 定版後、M2 開發前，先完成完整搬遷規劃，再以獨立 docs-only change 執行。
- 搬遷不得混入 M1 程式修正，避免干擾 Tester 與 Designer 審查。

## 已確認事項

1. `docs/milestone.md` 是唯一權威 milestone 規格。未來動態文件只能命名為 progress / status / dashboard，不得形成第二份 milestone 定義。
2. 原 `docs/reviews/M1_developer_feedback.md` 不符合 workflow 的審查單命名、requestor / owner 與角色生命週期，已先移至 `docs/notes/legacy/m1-developer-self-review.md`，不得視為合規的 `TR_dev_M1`。完整搬遷時再將必要資訊合併至 Developer status，不偽造既有 provenance。
3. `docs/arch_brief.md` 已無維護需求，暫時保留，列入未來淘汰；不得再把新契約寫入該檔。
4. `test/` / `tests/`、Developer role 路徑、Test ID 範例、`In Revision` 等 typo / stale contract，列入搬遷時統一修正。
5. `reviews/` 應只保存跨角色審查單；implementation、milestone、Developer、Tester 的動態進度應移至獨立 `status/`。
6. 操作文件放在 `runbooks/`，不放進權威 `test_spec/`。

## Agent 閱讀負擔原則

- 角色啟動只要求 `AGENTS.md` 指定的 role 文件與 `workflow.md`；其餘文件依任務按需讀取。
- 未來 `docs/README.md` 只提供目錄地圖、權威順序與「要做什麼就讀哪裡」，不摘要或複製各規格內容。
- README、workflow 與 role 文件應短小、使用 link routing，避免要求每個 agent 預讀完整 arch / implement / test spec。
- `docs/roles/` 路徑目前是 agent bootstrap contract；若搬移，必須在同一變更同步更新 `AGENTS.md`。

## 完整搬遷規劃必備內容

- 現況 → 目標路徑逐檔 mapping 與每類文件 owner
- 唯一權威來源、動態 status、審查單、runbook 的邊界
- 所有內部連結與 literal path 的更新清單
- workflow、roles、AGENTS.md 與 review lifecycle 的同步修正
- active review / history 的遷移與不竄改 provenance 原則
- broken-link、workflow path、review frontmatter 的自動檢查方式
- 搬遷執行順序、驗證命令與可回復策略
