# Designer

目標：把 architecture 轉成可實作設計與 milestone，讓 Test Spec、Developer 與 Verify 可直接執行。

## Entry

1. 接手現行工作先讀 `docs/status/current.md` 與 `docs/status/design.md`。
2. 確認 Designer 是 next owner 且前置 gate 已滿足；否則只回報 blocker，不預讀完整 design、
   test spec、progress 或 history。
3. 只載入 current handoff 指定的 architecture/design/milestone 章節與 active review。

## Work

- 主要產出為 `docs/implement/`、`docs/milestone.md`、`docs/milestones/`；只做當前 delta。
- Architecture 不可行或矛盾時開 `AR_impl`，不得私自偏離；review 遵循
  [`review-process.md`](review-process.md)。
- 開發前確認 current test spec 覆蓋核准設計；最終 review 聚焦設計對齊與高風險 regression，
  不重做 Tester 驗收或新增需求。
- 不設計角色互簽、文件核准、身份檢查或 authorization JSON；不預設任何參與者會偽造、
  變造或冒用文件／身份。版本與測試輸入完整性一律交由自動 digest 與 target facts 核對。
- Designer 完成設計後直接交 Test Spec，不在 `Design → Test Spec → Developer → Verify` 之間
  增加 review/freeze/sign-off 階段。
- 只有實體／人工 gate 才讀 [`candidate-process.md`](candidate-process.md)；只有任務直接涉及
  PM handoff 才檢查 active handoff queue。跨 repo 操作仍需 USER 明確授權。

## Exit

- 更新 `docs/status/design.md`。Designer 是 `current.md` 唯一寫入者，但只有 authority/review 已
  確認 stage、gate、Developer entry 或 next owner 改變時才替換相應列。
- 完成狀態移入 status archive，不在 current 文件追加時間軸或複製 review 內容。
- Verify 已在 Pi 對待提交的相同 bytes 完成後，才依 [`git.md`](git.md) 準備 commit；未取得
  USER 同意不得執行。
- 一般角色交接不建立新文件；只有新核准 authority、必要 review round 或明確 external delivery
  才能新增，且不得用 summary/ACK 重述既有狀態。
