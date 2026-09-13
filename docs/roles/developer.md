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
- 所有開發都讀 [`candidate-process.md`](candidate-process.md)，並把待提交的完整內容同步到 Pi；
  在 Pi 直接執行適用的 portable、整合、原生、硬體與人工測試直到收斂。
- Pi 測試綁定 tracked-only patch/content digest、config 與 artifact digest。任何 source、test、
  runner、dependency 或設定變更都使先前結果失效，必須用新 digest 重跑。

## Exit

- 以實際命令、結果、剩餘 blocker 與 next owner 取代 active 工作摘要，不追加開發日記。
- 完成 snapshot 移入 `docs/status/archive/<milestone>/`；歷史只依 ID/SHA 查詢。
- 只更新 `development.md` 與自己負責的 active review；不得修改 `current.md`。交接直接回覆
  USER／Designer，不新增 checkpoint、handoff 或另一份 progress 文件。
- Pi Verify 尚未完整通過時不得建立任何開發 commit。Verify 通過後，先確認工作站待提交 bytes
  與 Pi 已驗證內容完全一致，再依 `git.md` 取得 USER 授權建立一次 completion commit。
