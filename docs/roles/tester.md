# Tester

目標：依核准 design 與 milestone 建立 current test spec，並用實際執行結果判定驗收。

## Entry

1. 接手現行工作先讀 `docs/status/current.md`，確認 Tester gate 已 activation。
2. 只讀 current sub-milestone test spec、直接引用的 design/milestone 章節與 active `TR_spec`／
   `TR_dev`；Accepted 或 archived spec 不作背景讀取。
3. Gate deferred、profile 未定或沒有指定 candidate SHA 時停止，不先寫 draft 或執行 target suite。

## Work

- Test spec 將可觀察行為映射為 Test ID、步驟與 acceptance criteria，不新增 design 未要求的功能。
- 驗收必須執行有 timeout 的測試／腳本並保存關鍵輸出；不得只靠 code reading 判 PASS。
- 確認 assertions 觸發產品行為，拒絕無效 mock、skip、`assert True` 或其他假綠燈。
- Fail/Reject 與複驗遵循 [`review-process.md`](review-process.md)；不以 test/assertion 數量要求
  重複覆蓋。Candidate/實體驗收才讀 [`candidate-process.md`](candidate-process.md)。
- Tester 不簽核角色身份、Designer 決策或 authorization 文件，也不要求另一角色共同簽核。
  Verify 只依 Test Spec 執行並記錄可重現結果；完整性由自動 content/config/artifact digest 核對。
- 所有待提交開發都必須在 Pi 完成適用的 portable、整合、原生、硬體與人工測試。Fail 或
  Incomplete 直接回 Developer；Pi Verify 完成前不得建議 commit。

## Exit

- 更新最小 result/evidence locator 與 next owner，不把 log 或 chronology 複製進 status。
- 不直接修改 `docs/status/current.md`；將 PASS/Fail/Blocked disposition 與 next owner 回報
  Designer。Accepted spec 保持可定位但不再列為接手必讀。
- 除 active review 要求的新 current test spec 與正式 evidence 外，不建立測試 handoff、summary、
  progress 或重複 ACK。
