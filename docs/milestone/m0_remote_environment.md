# M0：遠端環境與 Evidence Chain Readiness

狀態：`COMPLETE`
性質：前置 readiness gate，不是模型或產品 milestone。

## 目標

證明 Assistant 能在授權範圍內可靠操作目標 Raspberry Pi 5、控制測試 lifecycle、收回未被破壞的結果，讓後續硬體判定具備可信證據鏈。

## 對最終交付的貢獻

- 建立可重現的 Pi 環境盤點與命令記錄方式。
- 建立 evidence 傳輸、checksum、sanitization 與 cleanup 方法。
- 提前辨識 SSH、權限、時間同步、儲存空間或網路造成的交付風險。

## 工作大綱

- 建立 dedicated SSH alias/key 與確認 host fingerprint。
- 驗證非互動短命令、長命令、timeout、cancel、exit code 與重連。
- 驗證檔案雙向傳輸及 checksum 一致。
- 盤點 Pi 型號/RAM、OS、kernel、architecture、disk、clock、temperature 與 throttling。
- 唯讀盤點 ALSA、record/playback devices、driver/module 與目前 audio config。
- 建立遠端測試目錄、evidence 命名及敏感資料規則。
- 盤點必要 sudo 權限；預設不使用 root。
- 視核准情況驗證 reboot 後重連，不將 reboot 視為基本必測。

## Entry Conditions

- 目標 Pi 已上電並連網。
- User 提供可連線 SSH alias；不在聊天或 repo 提供密碼/私鑰。
- User 核准唯讀遠端環境驗證。

## Exit Gate

- SSH 多次連線與命令 exit code 可可靠取得。
- timeout/cancel 後沒有遺留測試 process。
- evidence 傳輸前後 checksum 一致。
- Pi 與 audio environment manifest 可重現產生。
- 權限限制與需要 User 現場操作的項目已明確。
- log/evidence 不含 secret 或敏感音訊內容。
- M1 所需遠端操作不存在未處理 blocker。

## 必要 Evidence

- Sanitized SSH/connectivity log。
- Environment/audio inventory。
- Command control、cancel、cleanup 結果。
- File transfer/checksum 結果。
- 已知限制與 M1 操作 runbook。

## 分工

- Assistant：定義與執行測試、審查 evidence、判定 pass/fail/inconclusive、更新風險。
- User：準備 Pi/SSH、核准外部影響動作、處理必要的現場或特權操作。

## 調整觸發點

- 工作環境無法路由到 Pi，且 VPN/Tailscale/人工 evidence bundle 均不可行。
- SSH 無法安全使用 key/fingerprint。
- 無法可靠取消命令、取得 exit code 或驗證檔案完整性。
- 權限需求超出可接受範圍。

## Gate Review 問題

M0 結束時必須回答：現有遠端工作方式是否足以支撐 M1–M4 的原始 evidence、長時間 benchmark、failure injection 與 cleanup 認證？若否，先提出工作方式調整請求。

## Gate Review Result

結果：`PASS`（2026-08-08）

- Pi POC worktree 與本機 source SHA 一致且兩端 clean；多 POC 環境以
  operator-managed `PI_POC_REPO` 指定目標 checkout。
- Read-only environment pre-test 確認 Pi 5/aarch64、audio device availability、
  no device owner、required tools、disk、temperature 與 throttling。
- Remote exit-code、remote timeout、explicit cancel/cleanup、orphan check、
  two-way SHA-256 transfer 與 temporary-file cleanup 均為 `PASS`。
- M1 所需的 non-interactive privilege 可用；POC commands 仍預設以一般帳號
  執行，只有明確需要時才使用最小必要 privilege。

已觀察一次短暫的 local-network name-resolution failure，重試後恢復且未造成
evidence 遺失。此為後續 session 的 operational risk；每次硬體 session 必須先
run environment pre-test。若重複發生，改用 operator-managed 的穩定 alias 或
local mapping，並保持 connection data 在 Git 之外。

M0 completion 不代表 M1 已開始。M1 仍須依其 entry conditions 重新確認 frozen
gates、M3 dependency path 與 delivery assessment。
