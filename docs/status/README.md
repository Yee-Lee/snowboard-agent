# Status documents

`status/` 是接手工作的入口，只保存目前狀態；它不重述 architecture、design、milestone 或
test spec 契約。

| File | Owner | Purpose |
|---|---|---|
| [`current.md`](current.md) | Designer only | current stage、gate、next owner、必要讀取路由 |
| [`design.md`](design.md) | Designer | 尚未定案的 design delta 與 review dependency |
| [`development.md`](development.md) | Developer | active work package、affected scope 與最近驗證 |
| [`archive/`](archive/) | provenance | completed/superseded progress 原文；只依 ID/SHA 查詢 |

## Maintenance

- `current.md` 是單一寫入者文件。Architect、Developer、Reviewer、Tester 完成工作後更新各自
  authority/review/evidence 並回報 disposition；只有 Designer 確認狀態轉移後修改 `current.md`。
- `current.md` 只保留一個 current milestone，目標不超過 4,000 字元。
- `design.md`、`development.md` 只保留未完成工作，個別目標不超過 8,000 字元。
- 狀態改變時更新既有列，不追加時間軸；完成快照移入 `archive/<milestone>/`。
- review 詳情留在 `docs/reviews/`，測試證據留在 `docs/outsource/evidence/`，不得複製全文。
- Git history 已能保存逐次文字；status archive 只保留接手仍需定位的 milestone snapshot。
- 一般任務結束不建立新 handoff。只有新 review round、核准的新 authority，或 USER／外部契約
  明確指定唯一 ID artifact 時可新增文件。
