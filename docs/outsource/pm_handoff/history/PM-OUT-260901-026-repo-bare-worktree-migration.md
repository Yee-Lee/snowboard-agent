---
requestor: "USER"
owner: "Designer"
status: "Resolved"
created: "2026-09-01"
handoff_id: "PM-OUT-260901-026-repo-bare-worktree-migration"
---

# Core Bare + Worktree 搬移結案紀錄

## 1. 範圍與結果

Core 已搬移至 bare repository 管理的 `core/` worktree。本文件只記錄
Core 的工作目錄、Python 環境與文件路徑修正；所有範例使用相對路徑、
Git 動態解析或通用佔位符，不記錄私人目錄。

`PM-OUT-260901-026` 維持 Resolved / archived；本文件即 Designer 核對回覆，
無另立 ACK。PM handoff 主目錄目前無 Open task / request。

## 2. Core 環境核對

- `git rev-parse --show-toplevel` 可正確解析 Core worktree；
  `git fsck --connectivity-only --no-dangling` 通過。
- SSH `git ls-remote` 可讀取 origin 的 `core` 分支。
- `.venv` activation、pip / pytest shebang 與 editable `sbd` import
  均指向搬移後的 Core worktree；符號連結可解析。
- 本輪未執行產品 regression 或硬體驗收，不能將本次路徑核對視為
  milestone acceptance。

## 3. 文件與本地設定修正

- Core 文件連結改用檔案相對路徑；ResourceManager 導向現有
  `src/sbd/core/resource_manager/manager.py`。
- 審查導覽改指現行 workflow / role 文件，修正 M1 delivery 名稱、
  歸檔文件相對路徑及 PM handoff 索引斷鏈。
- 既有 Audio P4 交付文件的 evidence 連結固定到已 ACK 的 delivery SHA
  `882e2b6ff571eb9d54ec96bae7d3b63338c5965c`；已用 Git object
  驗證兩個目標存在，不改寫 evidence 內容或驗收結論。
- M3 runbook 由 `git rev-parse --show-toplevel` 解析 Core root；
  外部 library 路徑使用通用佔位符，實際值只存於本地設定。
- Git-ignored `config.m4a.acceptance.local.yaml` 的兩個
  `artifact_lock_path` 改為 `requirements/m4a/audio-artifacts.json`。
  已驗證既有 loader 以設定檔所在目錄解析到現有 lock；
  此本機修正不納入 Git。
- 已檢查 Markdown 連結目標與 diff whitespace；文件修正不涉及
  source、tests、config contract 或 candidate identity。

## 4. 裝置與同步前置條件

本工作站未部署 M4A models / isolated runtimes、M3 OLED `libdisplay.so`
或 Pi 裝置節點。這些是 Git 外的 target 輸入；執行裝置驗收前須依
[M4A 診斷 runbook](../../../runbooks/m4a_developer_pi_diagnostic.md) 與
[M3 runbook](../../../runbooks/m3_rpi_validation.md) 準備。本次只修復文件
與可解析的 Core 設定路徑，不下載或重建 target artifacts。

檢查時 Core 未設定 upstream；origin 連線正常。此次檔案修正不變更
tracking 設定，日常同步須明確指定 remote / branch，或另行設定 upstream。
