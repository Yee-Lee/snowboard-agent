# LLM POC Workspace

目前狀態只以 [milestone index](../docs/milestone/README.md) 為準：External Gate 0 R2
已由 Core Designer 對 `0d415d...` 複驗並登錄 `COMPLETE`；Internal M0、M1 已完成，M2
為 `PLANNED`。本文件不另行建立狀態；M1 授權只涵蓋 frozen contract/schema/fixture、
candidate pairing preflight 與 deterministic fake，不包含真實 candidate benchmark、
安裝 runtime、下載模型或提前執行 Pi Gate 2A。

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

## M0 Packet Retained from R1

- `deliveries/POC-llm-DEL-2026-001-R1.md`：實際 Initial Manifest。
- `pyproject.toml`、`requirements-m0.lock`：Python 3.11+ standard-library-only setup/lock。
- `src/llm_poc_m0/dummy_child.py`：deterministic lifecycle child。
- `tools/run_m0_dummy_packet.py`：local timeout/terminate/kill/wait cleanup runner。
- `tests/m0/M0-TEST-REQUEST-001.md`：immutable packet draft 與受控 Pi runbook。
- `evidence/m0/m0-evidence.schema.json`：sanitized evidence schema。

## Core 2026-08-18 R2 and 2026-08-19 Platform Revision Artifacts

- `deliveries/POC-llm-DEL-2026-001-R2.md`：015 複驗 Initial Manifest。
- `tests/gate1/GATE1-PACKET-003.md`：authenticated fail-closed Ubuntu packet；supersedes packet 002。
- `tests/gate1/GATE1-PACKET-005.md`、`harness/gate1-lock-v5.json`：platform-keyed x86/Pi
  strict-config projection replacement；exact SHA `190a827b...` 已送 Core review，真實執行未授權。
- `fixtures/gate1/catalog.json`：20-case P2/P3 catalog；每 case 3 repetitions。
- `harness/gate1_validator.py`、`harness/gate1-lock.json`：validator v1.0.0 與 checksums。
- `tools/run_gate1_x86_prescreen_v5.py`、`tools/run_gate1_pi_compat_v5.py`、
  `tools/select_gate1_finalists_v5.py`：目前只執行 authenticated pre-launch projection；
  在 real execution authorization 前固定回傳 `INCONCLUSIVE`。Revision 004 工具只保留回歸。
- `tools/run_m4b_gate.py`：Gate 2A/2B frozen case-set plan validator；不執行 hardware。
- `tools/run_p9_residency_surrogate.py`、`harness/p9-residency-surrogate-lock-v1.json`：
  Audio M4A-P9 使用的 locked 2304 MiB／4-worker executable surrogate；`--self-test`只作
  小型protocol regression，不是Pi、M4A-P9或LLM Gate 2B evidence。
- `tools/run_gate1_pi_compat_v6.py`與`tools/run_gate2a_pi.py`：已凍結的Pi 5 executable
  packet controllers；只可在Core review/ACK、clean Pi 5 4GB/Debian 13/swap=0和operator
  authorization都到位後執行。workstation只允許其deterministic fake regressions。
- Revision 005 以 `candidate-v5.schema.json`、`acquisition-v5.schema.json` 與平台投影固定
  logical candidate 及各平台 config/runtime/model/dependency/adapter identity。
- `tests/gate1/test_gate1_packet.py`保留revision-003回歸；`test_gate1_packet_v4.py`覆蓋
  immutable preselection、Pi filter、no-backfill、cleanup與Gate 2 carry-over rejection；
  `test_gate1_packet_v5.py` 覆蓋 platform-keyed identity 與 R4 evidence rejection。

Gate 1、Gate 2A、Gate 2B 仍未獲准執行；catalog validator self-test 不是 candidate evidence。

## Proposed Dual-UTM Environment Preflight

兩台可用 Ubuntu 24.04 環境分別是 native-ISA ARM64 UTM 與 x86_64 UTM。現階段不依 schema
慣性或 VM 效能推測先選平台；`tests/gate1/GATE1-ENV-PREFLIGHT-001.md` 提議以 pinned API
wheel、offline dependency closure、native binding import與fake-child lifecycle做 bounded 比較。
Core 已例外接受隔離的 ARM64 diagnostic SHA `265db057...` 為 formal environment `PASS`，
並保留前兩次 runner-defect `INCONCLUSIVE`。ARM64 是 primary track；x86_64為獨立
portability/fallback且不阻擋 ARM64。兩個 WIP branches可在 immutable commands與stop conditions
下完成 approved workstation scope；Pi、Gate 2、finalist與product integration仍未授權。

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

ARM64 UTM到產品Pi的可攜identity、sanitized results、API/runner陷阱、Gate 1 compatibility與
Gate 2A重新執行邊界，集中在
[`DELIVERY-011-PM-LLM-POC-M2-ARM64-TO-PI-TRANSITION`](../docs/delivery/DELIVERY-011-PM-LLM-POC-M2-ARM64-TO-PI-TRANSITION.md)。
Pi operator應先讀該文件，不需回查UTM `/tmp` raw history；但它是pending scope request，不是
Pi execution authorization或Gate 2 evidence。

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
