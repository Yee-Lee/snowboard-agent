# LLM M0：Environment and Evidence-Chain Readiness

狀態：`NOT_STARTED`

性質：前置 readiness gate；不是 runtime/model benchmark，也不是 hardware baseline。

## 目標與交付貢獻

證明 workstation 能以 exact SHA、clean Pi worktree、受控命令 lifecycle 與完整
evidence chain 支撐後續 LiteRT-LM 測試。主要推進 delivery areas D1、D5、D8。

舊 Audio M0 可作 runbook 參考，但其 `PASS` 不會轉移到本 milestone。

## Entry Conditions

- User 明確核准開始 M0 與唯讀 Pi 操作；在此之前保持 `NOT_STARTED`。
- M0 test packet 已列出允許命令、expected outputs、timeout、cancel、cleanup 與 evidence schema。
- 要驗證的完整 commit SHA 已固定，workstation source clean，Pi 可 checkout 相同 SHA。
- Operator-managed SSH alias/key/host fingerprint 已就緒且不寫入 repo 或 evidence。
- 目標 Pi 已上電；任何需要安裝、下載、reboot、網路停用或 privilege 的動作另行核准。

## Work Packet

- 唯讀盤點 Pi 5 型號/RAM、OS、kernel、aarch64、glibc、disk、memory/swap、CPU、
  temperature、throttling 與 clock policy。
- 驗證 non-interactive SSH、exit code、timeout、explicit cancel、重連與 cleanup。
- 驗證 workstation/Pi repo full SHA 相同且兩端 worktree clean。
- 使用小型無敏感資料的 marker 驗證雙向 transfer 與 SHA-256；完成後清理 temporary files。
- 使用 deterministic dummy child 驗證 terminate/kill/waitpid、process-group 與 orphan=0；
  不載入真實模型。
- 盤點後續 runtime/model 所需 toolchain 與 aarch64 compatibility，但不在 M0 安裝或下載。
- 記錄 raw evidence 的受控位置與 sanitized index 產生方法。

## Exit Gate

- 所有 mandatory test packet 項目均有完整 command、timestamp、exit code 與 result。
- Exact-SHA/clean-worktree、remote command control、transfer checksum 與 cleanup 均已證明。
- Pi inventory 足以判斷 M1/M2 的 setup 與 benchmark 是否可執行。
- Secret、endpoint、credential、private prompt/model content 未進 Git 或 sanitized evidence。
- 未關閉問題已標成 blocker、risk 或 change request，且不被重試掩蓋。
- Technical Lead 依 workflow 完成 evidence review，將結果標記為 `PASS`、`FAIL` 或
  `INCONCLUSIVE`；只有 `PASS` 可以關閉 M0。

## Necessary Evidence

- M0 test request 與 test packet version。
- Sanitized environment/command-control inventory。
- Exact SHA、clean check、transfer checksum 與 child cleanup proof。
- Raw evidence location/checksum、sanitized evidence index 與 review decision。
- Risks、blockers、adjustment requests 與下一個獲准工作。

## Prohibited in M0

- 不下載或提交 model artifact。
- 不安裝、選定或 benchmark 真實 runtime/model。
- 不執行正式 latency/resource/offline gate。
- 不修改 Pi worktree，不把診斷腳本當作產品 child protocol。
- 不因舊 Audio M0 通過而跳過本 milestone review。
