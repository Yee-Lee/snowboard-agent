# LLM POC Workspace

目前狀態只以 [milestone index](../docs/milestone/README.md) 為準：External Gate 0 已由
POC Team 提交、等待 PM/Core 登錄；Internal M0 仍為 `NOT_STARTED`。本文件不另行建立
狀態，也不代表已核准連線 Pi、安裝 runtime、下載模型或開始測試。

## Layout

- `src/`：reference runtime/child/client source。
- `tests/`：local、fake、protocol 與 integration tests。
- `tools/`：可重現 setup/pre-test/benchmark/evidence 工具。
- `fixtures/`：可提交的非敏感 fixtures 與 catalog/checksum；不放 private prompt/output。
- `evidence/`：sanitized evidence index/summary；raw results 走受控管道。
- `deliveries/`：POC delivery manifests 與 handoff package。

Gate 0 R1 已加入 minimal M0 executable packet、test request 與 evidence schema；它們
目前只可作 local/fake validation。Packet 存在不代表 M0 已啟動，也不能用 Audio POC
工具或結果替代 LLM M0。

## Gate 0 R1 Artifacts

- `deliveries/POC-llm-DEL-2026-001-R1.md`：實際 Initial Manifest。
- `pyproject.toml`、`requirements-m0.lock`：Python 3.11+ standard-library-only setup/lock。
- `src/llm_poc_m0/dummy_child.py`：deterministic lifecycle child。
- `tools/run_m0_dummy_packet.py`：local timeout/terminate/kill/wait cleanup runner。
- `tests/m0/M0-TEST-REQUEST-001.md`：immutable packet draft 與受控 Pi runbook。
- `evidence/m0/m0-evidence.schema.json`：sanitized evidence schema。

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
