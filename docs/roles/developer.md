# Developer

目標：依核准設計與 current test spec 拆包、實作並提供真實 regression tests。

## Entry

1. 接手現行工作先讀 `docs/status/current.md` 與 `docs/status/development.md`。
2. `Developer entry` 不是 Open、沒有 active work package，或前置 review/test spec 未完成時，
   立即停止；不得靠舊 progress、R1 spec 或既有 code 猜測工作。
3. Entry 開啟後，只讀工作包引用的 milestone/design 章節、current sub-milestone test spec、
   affected symbols 與 Test IDs。

## Work

- 編輯前在 `development.md` 記 affected paths、Test IDs、估點與驗證命令，再修改 `src/`、`tests/`。
- 不私改 design API；無法落實時開 `IR_dev` 並遵循 [`review-process.md`](review-process.md)。
- 測試必須執行產品邏輯並有有效 assertions；修正以 finding、直接影響面與 regression 為界。
- 只有 Pi／硬體／原生相依／runtime／權限／效能／資源工作才讀
  [`candidate-process.md`](candidate-process.md)；純 portable 工作不載入該流程。

## Exit

- 以實際命令、結果、剩餘 blocker 與 next owner 取代 active 工作摘要，不追加開發日記。
- 完成 snapshot 移入 `docs/status/archive/<milestone>/`；歷史只依 ID/SHA 查詢。
- 只更新 `development.md` 與自己負責的 active review；不得修改 `current.md`。交接直接回覆
  USER／Designer，不新增 checkpoint、handoff 或另一份 progress 文件。
- 未經 USER 授權，不建立 candidate 或 completion commit。
