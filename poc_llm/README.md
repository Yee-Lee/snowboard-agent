# LLM POC Workspace

目前 milestone：M0 `NOT_STARTED`。本文件只說明 workspace 與受控執行規則；不代表
已核准連線 Pi、安裝 runtime、下載模型或開始測試。

## Layout

- `src/`：reference runtime/child/client source。
- `tests/`：local、fake、protocol 與 integration tests。
- `tools/`：可重現 setup/pre-test/benchmark/evidence 工具。
- `fixtures/`：可提交的非敏感 fixtures 與 catalog/checksum；不放 private prompt/output。
- `evidence/`：sanitized evidence index/summary；raw results 走受控管道。
- `deliveries/`：POC delivery manifests 與 handoff package。

目前只有目錄 scaffold，尚無獲准的 M0 executable packet。不要用 Audio POC 工具或
結果替代 LLM M0。

## Before Any M0 Run

1. 確認 [milestone index](../docs/milestone/README.md) 已在 entry review 後把 M0 改成
   `IN_PROGRESS`；若仍為 `NOT_STARTED`，只可維護計畫與 packet。
2. 確認 M0 test request 列出 exact full SHA、允許命令、timeout/cancel/cleanup、
   expected results、evidence path 與敏感資料規則。
3. 確認 workstation source clean，目標 SHA 已經依 User 核准完成 commit/push，Pi 能
   fetch 並 checkout 同一 SHA。
4. 使用 operator-managed SSH config/alias/key/host fingerprint。endpoint、account、
   credential、key path 與 connection config 不得寫入 Git。
5. 任何安裝、下載、artifact transfer、網路切換、reboot 或 privilege 操作另行核准。

## Pi Worktree Policy

Pi checkout 是 clean deployment/test worktree，不是開發來源。Tester 只能 checkout
test request 指定的完整 SHA、執行 pre-test 與 immutable packet、回收 evidence；
不得在 Pi 修改 source 或調整 gate。

正式 run 前必須驗證：

- Workstation/Pi full SHA 相同。
- 兩端 worktree clean。
- Candidate/artifact/config/fixture/schema IDs 與 test request 相符。
- Raw evidence 位置受控，repo 只接收 sanitized index。

## Model and Evidence Safety

不要提交 model、大型 artifact/raw result、private prompt/perception/output/tool payload、
secret 或連線資訊。Git 只保存 artifact source/version/license/checksum、受控取得方法、
schemas、非敏感 fixtures 與 sanitized summaries。

完整工作方式見 [LLM POC workflow](../docs/llm_poc_workflow.md)。
