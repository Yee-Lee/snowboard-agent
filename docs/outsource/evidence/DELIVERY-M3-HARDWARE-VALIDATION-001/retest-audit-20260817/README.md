# M3 2026-08-17 重測稽核證據索引

## 不可恢復的原始證據

觸發 `c545de6ff389b56596fb7c2bb04bc3636a5863d9` 的原始 terminal output、完整
command、exception、kernel / libgpiod版本、當時 config checksum及 HEAD / worktree
snapshot均未保存，現已不可恢復。本目錄不重建或推測不存在的 log。

當時人員事後確認：實體按鈕位於 BCM23，但除錯用 `auto_button.py` 曾讓 local config
留在 BCM27。此設定污染 timeline 保留於
`docs/outsource/responses/OUT-M3-AUDIT-2026-001.md`，並與未證實的
`pinctrl-rp1` 推論分列。

## 可重現替代證據

- `portable-precommit.md`：Python 3.12.3 commit 前 targeted regression命令、環境與結果。
- `../environment/system.json`、`../environment/packages.json`：既有 `cab627...` Pi
  bundle的平台、Python、kernel與gpiod版本。
- `../checksums/SHA256SUMS`：既有 bundle記錄的 config checksum。
- `../logs/button.xml`：既有 bundle的五個 Button nodes；不代表新候選 PASS。

新 exact-SHA candidate及 RPI evidence 尚未建立。舊 bundle不得用來替代本輪修改後的
實績測試。
