# Candidate and target verification

僅在 milestone 含實體、人工、Pi、原生相依、部署 runtime、權限、效能或資源 gate 時讀取。

## 不可變規則

- Pi 耦合工作先在隔離 target checkout 收斂；正式 acceptance 不是開發或除錯迴圈。
- Provisional candidate 只是可測的完整 SHA，不代表 freeze、Tester PASS 或 Accepted。
- Candidate SHA 一經 push、送驗或正式驗證即不可改寫；修正 protected input 必須 append
  新 commit、建立新 candidate，並重跑受影響 gate。
- Protected input 包含 `src/`、`tests/`、dependency/lock、config contract、candidate/acceptance
  runner 與 candidate workflow；其中任一變更都使既有 diagnostic、matrix 與 freeze 失效。
- Developer diagnostic 與正式 evidence 分離，不得複製、改名或拼接為 PASS。

## 最小流程

1. **Developer convergence**：先記 affected scope。Pi 耦合工作在 Pi 反覆跑 affected portable
   tests 與 target diagnostics；收斂後以相同 base、task paths、tracked-only patch SHA-256
   單次同步到乾淨工作站，確認 patch bytes 相同並跑一次主要 Python minor portable tests。
2. **Provisional candidate**：Designer 核對 scope；依 `git.md` 取得 USER 同意後建立完整 SHA。
3. **Portable sign-off**：Tester 對指定 SHA 跑正式支援 Python matrix，命令有 timeout，結果須
   0 Fail／Blocked／Skip／XFail。
4. **Candidate review/freeze**：Designer 只查設計對齊與高風險 regression。protected input 變更
   會撤銷 freeze，回到步驟 1。
5. **Target preflight/acceptance**：Tester 或 operator 驗 SHA、clean paths、runtime、hardware、
   artifact/config checksum；以全新 `acceptance/<run-id>/` 完整執行並保存 result 與 raw log。
6. **Reconciliation/acceptance**：Tester 核對 portable 與 target 指向同一 SHA/run；Designer 只確認
   freeze 後無 candidate-affecting 變更，再標記 Accepted。

每個正式命令至少記錄 run ID、40-character SHA、命令、平台、Python、起訖時間、exit code、
status 與 raw-log path。接線修正可保留 SHA，但須用新 run ID 重走 preflight 與完整 acceptance。
