# Candidate and target verification

僅在 milestone 含實體、人工、Pi、原生相依、部署 runtime、權限、效能或資源 gate 時讀取。

## 不可變規則

- 所有開發先在隔離 Pi checkout 收斂；Pi 是 commit 前 Verify 的必要環境，不是 commit 後才進入的 gate。
- Verify 綁定待提交內容的 tracked-only patch/content digest，不要求先建立 provisional commit 或 SHA。
- Candidate SHA 只在 Pi Verify 完整通過、工作站 bytes 核對相同且 USER 核准後建立。建立後不可
  改寫；若仍需修正，保留既有 evidence，以 append fix 產生新 SHA。
- Protected input 包含 `src/`、`tests/`、dependency/lock、config contract、candidate/acceptance
  runner 與 candidate workflow；其中任一變更都使既有 diagnostic、matrix 與 freeze 失效。
- 開發中的失敗 run 與最後 Verify evidence 分離，不得複製、改名或拼接為 PASS。
- 不要求角色互簽、身份證明、文件核准或 authorization JSON；不預設參與者會偽造或變造。
  防止測錯版本只使用自動內容、設定、artifact 與 target identity 核對。

## 最小流程

1. **Design**：Designer 固定實際產品行為與 Pi acceptance boundary，不建立簽核流程。
2. **Test Spec**：Tester 建立直接可執行的 Test IDs、命令與判定；不要求共同簽核。
3. **Developer convergence**：Developer 在 Pi checkout 實作／同步待提交內容，反覆執行 affected
   tests 與 target diagnostics；每次內容變更都更新 content digest。
4. **Verify**：以全新 `verification/<run-id>/` 對最後 content digest 完整執行所有適用 portable
   matrix、整合、runtime、硬體與人工測試。結果必須 0 Fail／Blocked／Skip／XFail，並保存 raw log。
5. **Byte reconciliation**：把已驗證內容同步回工作站，核對 base、tracked-only patch/content digest、
   task paths、config 與 artifact digest 完全相同；差異一律回步驟 3 並重跑 Pi Verify。
6. **Commit**：只有步驟 4、5 通過後，才依 `git.md` 向 USER 提出一次 commit proposal。Commit 後
   只核對 commit tree 對應已驗證內容，不再把 Pi 測試當成候選是否可用的首次驗證。

每個 Verify 命令至少記錄 run ID、base SHA、content digest、命令、平台、Python、起訖時間、
exit code、status 與 raw-log path。任何接線或內容修正都使用新 run ID 與新 digest 重走完整 Verify。
