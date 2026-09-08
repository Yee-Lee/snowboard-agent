# LLM POC Workspace

目前狀態只以 [milestone index](../docs/milestone/README.md) 為準。Gate 1、Gate 2A與Gate 2B POC
execution已完成；User選定Gemma 4 E2B / LiteRT-LM v0.16.0 pairing為POC winner，且Core final ACK
已收到。`M4B-MVA-001` Step 5結果已於`23fb481…`交付；Core其後新增`M4B-MVA-002` dependent
efficiency experiment，比較J/P encoding與D/H Conversation readiness。它不回退舊gate或改寫
MVA-002 machine結果。User已要求POC在P constraint path不支援時繼續bounded solution discovery；
依repository general rule，Pi-specific工作預設在Pi POC workspace直接開發、測試與除錯，完成後
回workstation補齊規劃、commit並push；不需每個任務另取得Pi開發方式例外。benchmark/profile發布
仍由Core文件、exact SHA與User授權控制。

## Layout

- `src/`：reference runtime/child/client source。
- `tests/`：local、fake、protocol 與 integration tests。
- `tools/`：可重現 setup/pre-test/benchmark/evidence 工具。
- `fixtures/`：可提交的非敏感 fixtures 與 catalog/checksum；不放 private prompt/output。
- `evidence/`：sanitized evidence index/summary；raw results 走受控管道。
- `deliveries/`：POC delivery manifests 與 handoff package。
- `contracts/mva/`、`fixtures/mva/`、`tests/mva/`：M4B-MVA專用產品等價surface；不得以舊
  fresh-Conversation/full-envelope contract替代。

工作站更換或context reset時，M4B-MVA續接以
[`HANDOFF-LLM-M4B-MVA-WORKSTATION-001`](../docs/response/HANDOFF-LLM-M4B-MVA-WORKSTATION-001.md)
為完整checkpoint；新工作站仍須重新建立自己的ignored `.workstation-context.md`，不得繼承舊機能力。

2026-09-06 WP01已接續完成，本機execution snapshot及Pi進場前的唯一最新handoff為
[`HANDOFF-LLM-M4B-MVA-PI-ENTRY-001`](../docs/response/HANDOFF-LLM-M4B-MVA-PI-ENTRY-001.md)。
本機測試依賴使用`requirements-mva-workstation.lock`於ignored `.venv`；Pi維持原selected
runtime，不能使用workstation lock替代。執行命令與離線／receipt／reboot／cleanup條件見
[`M4B-MVA-POC-PACKET-001`](tests/mva/M4B-MVA-POC-PACKET-001.md)。

最新bounded efficiency工作以
[`m4b_mva_efficiency.md`](../docs/milestone/m4b_mva_efficiency.md)為執行計畫；目前先做exact
工程實作、Pi-native驗證及User review已完成，結果由
[`DELIVERY-LLM-POC-M4B-MVA-EFFICIENCY-003`](../docs/delivery/DELIVERY-LLM-POC-M4B-MVA-EFFICIENCY-003.md)
送Core revision。J/S2與conditional H為工程建議；listen-only Reasoner可用，但V1不可採用且V2A、
V2B、V2C皆未成為合格prompt。正式candidate與hardware evidence仍須Core freeze後，以clean exact
pushed SHA重跑；既有MVA packet不得被覆寫或冒充新實驗。

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
- `deliveries/POC-llm-DEL-2026-001-R3.md`：User-approved POC winner manifest與Core final handoff。
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

以上段落保留早期R2 packet狀態；後續Gate 1、Gate 2A及Gate 2B已由新revision、授權與R3 winner
manifest取代。歷史catalog validator self-test仍不是candidate evidence。

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

Pi POC workspace預設用於Pi-specific開發、測試與除錯，並可直接修改source；這是general rule，
不需逐任務例外。開始時記錄base SHA，所有run標為`ENGINEERING / NON-FORMAL`，Pi上不得commit/push。完成後只將受控source/test
diff帶回workstation，排除model、cache、raw/private evidence、credential與host資訊，在workstation
審查、重跑applicable checks並補齊plan/packet後commit與push。

正式hardware/benchmark仍使用另一個clean exact-SHA階段：checkout test request指定SHA、執行
pre-test及immutable packet、回收append-only evidence，且正式run中不得臨時修改source。若發現缺陷，
回到Pi development loop修正，再經workstation新commit/push後重跑affected formal cases。

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
