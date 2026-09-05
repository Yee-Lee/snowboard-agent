# Developer Progress ( developer_progress.md )

本文件由 **Developer** 維護，用於紀錄各個 Milestone (M1 ~ M7) 的任務拆包 (Task Breakdown)、工作點數估算 (Story Points) 以及目前的實作進度。

**注意**：
1. 估點與排程不改變 `arch.md` 或 `implement/` 的設計契約，也不降低 `test_spec_M{x}.md` 的驗收門檻。
2. Developer 必須在 [C] 階段的 Test Spec 被審查通過後，才能正式進入本文件的規劃與後續開發。
3. 若估點時發現範圍過大或有實作困難，應開立 `IR_dev` 單據向 Designer 提出重構/切分申請。

---

## M1 ── 純軟體核心

* **總預估點數**：37 SP
### PM Delivery Carry-over Feedback 修訂（2026-08-04）

* **總預估點數**：2 SP
* **修正基線**：Commit SHA `a723b4e0542de8eae0071a91a192104c686152bd`；對照 `PM-OUT-2026-001-R1` (`CR-M1-II`) 所列 5 項議題。
* **修正內容**：
  * `CR-M1-II-002` (Blocking)：移除 [`tests/test_config.py`](../../../tests/test_config.py) 硬編碼之 `/etc/hosts`，改用 `tmp_path` 建立跨平台暫存檔，真正驗證 config format mismatch。
  * `CR-M1-II-003` (Blocking)：移除 [`tests/test_bootstrap.py`](../../../tests/test_bootstrap.py) Windows pipe 無法使用的 `select.select()`，改用背景 `Thread` + `Queue` (timeout 0.1s) 實作跨平台 stream reader。
  * `CR-M1-II-004` (Advisory)：重構 [`tests/milestones/test_m1_foundation.py`](../../../tests/milestones/test_m1_foundation.py)，移除 `from tests.test_* import *` 之 wildcard re-export，消除 full suite 重複收集。Full suite test nodes 由 332 灌水數據縮減為 167 筆真實精確節點（166 unique tests + 1 milestone runner）。
  * `CR-M1-II-005` (Blocking)：對齊 `developer_progress.md` 紀錄、31 個 Test ID 涵蓋率與自驗驗證結果。
* **Developer 自驗數據**：
  * `PYTHONPATH=src python3 -m pytest -p no:cacheprovider -q tests/milestones/test_m1_foundation.py` → `1 passed in 5.40s`
  * `PYTHONPATH=src python3 -m pytest -p no:cacheprovider -q` → `167 passed in 9.66s` (0 Fail / 0 Skip / 0 xfail)

### Customer feedback 送測前修正計畫（2026-08-03）

* **總預估點數**：13 SP
* **修正基線**：目前 HEAD `19b4445`；依 `docs/notes/m1_developer_self_check.md` 所列 10 項設計契約缺陷修正。
* **完成門檻**：缺陷導向回歸測試、M1 milestone entrypoint 與 full suite 全數通過，且無 skip / xfail，才恢復待 Tester 狀態。

| 工作包 | SP | 範圍 | 狀態 |
|---|---:|---|---|
| WP-M1-FB-01 | 3 | Logger extra allowlist/redaction；THINK Exit 驗證；normal Interrupt 不經 ERROR；同步修正 SM/Log 測試 | 完成 |
| WP-M1-FB-02 | 4 | Capability dependencies；catalog 必要 kind seal gate；recovery 僅切 backend owner reference並保證局部 cleanup | 完成 |
| WP-M1-FB-03 | 3 | 公開 `wait_stopped()` fatal handoff；Level 3 僅 bounded logger flush；移除 main 私有 task 存取 | 完成 |
| WP-M1-FB-04 | 2 | Config 相對 Path 基準與安全 `.env` error；統一 owner exception taxonomy | 完成 |
| WP-M1-FB-05 | 1 | EventBus 改為規格 package + public re-export；完整 regression | 完成 |

#### 修正完成與 Developer 自驗（2026-08-03）

* Customer feedback 所列 10 項缺陷均已修正，新增缺陷導向 assert 覆蓋敏感 extra、THINK Exit state ordering、normal Interrupt、capability dependency、seal gate、recovery identity/cleanup、public fatal handoff、Level 3 cleanup、config path/env、exception identity 與 EventBus package API。
* Targeted regression：`55 passed`。
* 官方 `python:3.11-slim` disposable container 先完成 `pip install ".[dev]"`，再執行：
  * `python -m pytest -p no:cacheprovider -q tests/milestones/test_m1_foundation.py` → `154 passed in 8.52s`
  * `python -m pytest -p no:cacheprovider -q` → `308 passed in 12.67s`

### Feedback 修正與 Developer 自驗（2026-08-02）

* Legacy Developer self-review 的 M1-DEV-001 ~ M1-DEV-009 均已完成修正；該紀錄已移出 active reviews，正式結果等待 Tester 依 workflow 獨立驗收。
* M1 Test Spec 共 31 個唯一測項 ID；M1 regression entrypoint 實際收集並通過 149 個 pytest cases，無 skip / xfail。
* 目前 Python 程式碼規模：`src/` 44 檔、3,756 行；`tests/` 14 檔、2,631 行（以 `rg --files ... | xargs wc -l` 計算，包含空行與註解）。
* 在官方 `python:3.11-slim`（Python 3.11.15）隔離環境先執行 `pip install ".[dev]"`，再執行：
  * `python -m pytest -p no:cacheprovider -q tests/milestones/test_m1_foundation.py` → `149 passed in 6.16s`
  * `python -m pytest -p no:cacheprovider -q` → `298 passed in 10.99s`
* 同步修正 `pyproject.toml` 的 setuptools build backend，以及兩個使用 Python 3.12-only Protocol introspection 的測試，確保宣告的 Python ≥ 3.11 安裝與驗收路徑成立。
* 新增精簡 [`M1 development runbook`](../../runbooks/m1-development.md)；完整 docs 搬遷延至 M1 定版後、M2 開發前，前置決策記於 [`docs restructure Note`](../../notes/docs-restructure-after-m1.md)。

### 估點基準

* 1 SP ≈ 一個經驗開發者約半天可完成的可交付單元（含自測）。
* 估點包含 src/ 實作 + 對應的 test/ 撰寫。
* 複雜度考量：async 時序、race condition 測試、跨模組 fake/stub 準備。

---

### 任務清單

#### WP-M1-01：專案骨架與基礎設施 (3 SP)

**範圍**：
- 建立 Python package `src/sbd/` 與子 package 結構
- 建立 `pyproject.toml`（Python ≥ 3.11、pytest 依賴、rpi marker）
- 建立 `tests/` 骨架含 `conftest.py`（註冊 `rpi` marker）
- 建立 `tests/milestones/test_m1_foundation.py` entrypoint
- 建立 `config.example.yaml` 與 `.env.example`

**產出**：
- `src/sbd/__init__.py`, `src/sbd/core/__init__.py`, 各子 package `__init__.py`
- `pyproject.toml`
- `tests/conftest.py`, `tests/milestones/test_m1_foundation.py`
- `config.example.yaml`, `.env.example`

**相依**：無（可最先開工）

**對應測項**：M1-REG-001（部分：marker 註冊、package 結構）

---

#### WP-M1-02：事件 Dataclass 與型別系統 (3 SP)

**範圍**：
- 實作 Ch 1 所有 concrete event dataclass（frozen=True, slots=True）
- 實作 ID 型別別名（SessionId, TurnId, CorrelationId, MessageId）
- 實作 TypeAlias union groups（WorkerFact, StateBroadcast, Signal, Event）
- 實作 State Literal type
- 實作 `ForceAbortReport` frozen control value

**產出**：
- `src/sbd/core/events.py`
- `src/sbd/core/lifecycle.py`（ForceAbortReport）

**相依**：WP-M1-01

**對應測項**：M1-EVT-001, M1-EVT-002

**複雜度備註**：dataclass 數量多（約 12 個），但每個結構簡單；核心風險在 frozen + nested payload 行為合約的測試。

---

#### WP-M1-03：Protocol 介面與 Lifecycle 控制值 (2 SP)

**範圍**：
- 實作 Ch 2 的 Protocol interfaces：InputSource, Perception, Action, Adaptor
- 實作 Reasoner 的 concrete module 簽名（M1 只有骨架）
- 定義 lifecycle 方法簽名（start, stop, abort, force_abort）
- 建立最小 conforming fake 以供後續 WP 裝配測試

**產出**：
- `src/sbd/input_events/base.py`
- `src/sbd/perception/base.py`
- `src/sbd/action/base.py`
- `src/sbd/adaptor/base.py`
- `src/sbd/cognition/reasoner.py`（簽名骨架）
- `tests/fakes/` 目錄下的 fake implementations

**相依**：WP-M1-02（依賴事件型別）

**對應測項**：M1-CON-001

---

#### WP-M1-04：Event Bus (5 SP)

**範圍**：
- 實作 direct-call dispatch（exact concrete type 匹配，snapshot 隔離）
- 實作 subscription token（Subscription identity、重複檢測、冪等解除）
- 實作派送順序保證（同型 handlers 依註冊順序逐一 await）
- 實作延後 error fallback（handler 失敗 → 待原事件 fan-out 後依序 publish ErrorOccurred）
- 實作 fatal latch（ErrorOccurred handler 再失敗 → FatalDispatchError → latch）
- 實作 `wait_fatal()` 通道
- 處理 CancelledError 穿透（不 fallback）

**產出**：
- `src/sbd/core/event_bus.py`（或 `src/sbd/core/event_bus/` package）

**相依**：WP-M1-02（依賴 Event, ErrorOccurred 型別）

**對應測項**：M1-BUS-001, M1-BUS-003, M1-BUS-004

**複雜度備註**：⚠️ 高。延後 fallback 鏈的非遞迴保證、dual-channel fatal latch 的 async 同步、snapshot 隔離在 handler 內增刪訂閱的正確性，皆需仔細的 race condition 測試。估 150–250 行實作 + 300+ 行測試。

---

#### WP-M1-05：Config Schema、Loader 與 Validation (5 SP)

**範圍**：
- 實作 immutable frozen dataclass schema（AppConfig 及所有 sub-config）
- 實作 SecretValue 封裝（`__repr__` / `__str__` mask, `reveal()`）
- 實作 strict YAML overlay loader（unknown key 拒絕、leaf 覆寫）
- 實作 custom `.env` parser（SBD_ prefix、無 shell expansion）
- 實作 precedence chain：default → YAML → .env → process env
- 實作 cross-field validation（audio math、GPIO uniqueness、timeout namespace、perception kinds）
- 實作 example file CI 驗證路徑
- 結果 immutable（MappingProxyType freeze）

**產出**：
- `src/sbd/core/config/` package（`__init__.py`, `models.py`, `defaults.py`, `loader.py`, `env.py`, `validate.py`）
- `config.example.yaml`（更新為完整 schema）
- `.env.example`

**相依**：WP-M1-01

**對應測項**：M1-CFG-001, M1-CFG-002, M1-CFG-004, M1-CFG-005

**複雜度備註**：⚠️ 高。嚴格遞迴 merge 不使用 Pydantic；cross-field validation 規則多（audio math 精確除法、namespace 互斥）；SecretValue redaction 與 .env parser 各有邊界情況。估 500–800 行實作。

---

#### WP-M1-06：Logger、Error Observer 與 Redaction (4 SP)

**範圍**：
- 實作 stdlib logging 雙階段初始化（bootstrap stderr → configure_logging）
- 實作 structured LogRecord schema
- 實作 text / JSON lines 兩種 formatter（fail-safe JSON encoder）
- 實作 RotatingFileHandler 選擇邏輯
- 實作 LoggerAdapter with_context
- 實作 `ErrorLoggingObserver`（canonical ErrorOccurred → 1 筆 ERROR log、sanitize where、redact/truncate error text）
- 實作 redaction patterns（password, token, api_key, authorization）
- 實作 truncation（512 code points, newline escape）

**產出**：
- `src/sbd/core/logger.py`
- `src/sbd/core/error_observer.py`

**相依**：WP-M1-04（ErrorLoggingObserver 需要 EventBus）, WP-M1-05（LogConfig）

**對應測項**：M1-LOG-001, M1-LOG-002, M1-LOG-003, M1-LOG-004（部分）

---

#### WP-M1-07：State Manager (8 SP)

**範圍**：
- 實作 6 狀態（IDLE/WAKE/PERCEPTION/THINK/ACTION/ERROR）的完整轉移
- 實作單一 unbounded inbox（asyncio.Queue + InboxItem）
- 實作 public event guard（白名單 + terminal Fact validation）
- 實作 private notice（_TaskCompleted, _WakeAckElapsed, _RecoveryCompleted）
- 實作 SessionContext 管理（session_id, wake_source, turn_id, selected_perceptions 等）
- 實作 InFlightRecord（correlation_id 綁定、done callback 隔離）
- 實作 Fact + Task-Done join barrier（雙重完成條件）
- 實作 stale/duplicate Fact 過濾（WARNING/drop）
- 實作 no-Fact-return fatal invariant（StateManagerInvariantViolation）
- 實作 wake source → first turn mapping（button/wake→listen, external→read）
- 實作 next_perceptions 正規化（unknown 移除、duplicate 去重、rest 忽略）
- 實作 injected fake port 介面（FX-M1-PORTS：ActionPayloadValidator、ExternalMessageControl、WakeListenerControl）
- 實作 convergence request → in-flight empty gate → flush/discard 邏輯
- 實作 recovery barrier 等待

**產出**：
- `src/sbd/core/state_manager/` package（`__init__.py`, `manager.py`, `session.py`, `inflight.py`, `guards.py`, `notices.py`）

**相依**：WP-M1-02, WP-M1-04（EventBus）, WP-M1-03（Protocol 介面用於 fake worker）

**對應測項**：M1-SM-001, M1-SM-002, M1-SM-003, M1-SM-004, M1-SM-005, M1-SM-006

**複雜度備註**：🔴 最高。SM 是 M1 最大的單一模組（預估 700–1000 行），涉及 6 個測項、async inbox 消費迴圈、join barrier 時序、多路 convergence path、fake port 注入。需要精心設計的 FX-BARRIER-WORKER fixture 來測試 Fact 與 task-done 的各種排列。

---

#### WP-M1-08：Resource Manager (6 SP)

**範圍**：
- 實作 ResourceSpec、ResourceRecord、ResourceKey 資料結構
- 實作 registry preflight validation（uniqueness、self-dep、cycle detection via Kahn's）
- 實作 StartPhase enum 與 phase-ordered startup
- 實作 scoped ResourceResolver（undeclared/not-ready guard）
- 實作 DAG-ordered startup 含 real → null fallback（audio/display/camera）
- 實作 startup rollback（reverse order stop、failure 不阻後續）
- 實作 WorkerCatalog（empty inject → populate → seal → runtime lookup）
- 實作 capability map（P1 + P2 推導、freeze via MappingProxyType）
- 實作 startup coherence gate
- 實作 recovery ticket & barrier（begin_recovery、RecoveryHook、wait_recovery、generation 管理）
- 實作 reverse stop（stop_all、per-resource timeout、failure report）
- 實作 prepare_shutdown（cancel active recovery）

**產出**：
- `src/sbd/core/resource_manager/` package

**相依**：WP-M1-02, WP-M1-04, WP-M1-05（config 中的 resource timeout、required flag）

**對應測項**：M1-RM-001, M1-RM-002, M1-RM-003, M1-RM-004, M1-RM-005, M1-RM-006

**複雜度備註**：🔴 高。涉及 6 個測項、26 個子測試點。Kahn's DAG 排序、real→null fallback 流程、recovery barrier 的 async 協調、capability map freeze 時序，皆需大量 call log 驗證測試。估 400–600 行實作 + 500–800 行測試。

---

#### WP-M1-09：三級收斂 (Converger) (4 SP)

**範圍**：
- 實作 SessionConverger 類別
- 實作 Level 1 parallel abort（per-kind timeout、asyncio.shield）
- 實作 Level 2 force_abort（escalated targets only、strict dual-proof）
- 實作 Level 3 ConvergenceFatalError 觸發
- 實作 ForceAbortReport 聚合（deduplicate、sort、validate backend key）
- 實作 ConvergenceResult 回傳與 SM 整合
- 實作 reentry fatal 保護
- 實作 CancelledError 穿透（原樣傳出、不補 Error）

**產出**：
- `src/sbd/core/state_manager/convergence.py`（或 `src/sbd/core/convergence.py`）

**相依**：WP-M1-02（ForceAbortReport）, WP-M1-03（abort/force_abort 介面）, WP-M1-07（SM 整合介面）

**對應測項**：M1-CAN-001, M1-CAN-002, M1-CAN-003

**複雜度備註**：⚠️ 高。shielded parallel cancellation 與嚴格 dual-proof Level 2 的 async 超時行為需要仔細的時序測試。禁止 `task.cancel()` fallback 使得異常路徑較為細膩。估 200–300 行實作 + 300–450 行測試。

---

#### WP-M1-10：main.py Bootstrap、Supervision 與整合驗收 (4 SP)

**範圍**：
- 實作 `src/sbd/main.py` 的 bootstrap 流程（config load → logger → EventBus → RM → SM 裝配）
- 實作 fatal supervision loop（asyncio.wait FIRST_COMPLETED：bus.wait_fatal, sm.wait_stopped, signal bridge）
- 實作 exit code 映射（0/2/3/4）
- 實作 shutdown cleanup（RM stop_all、logger flush with timeout）
- 以 fake worker 裝配完成端到端 bootstrap 驗證
- 確保 M1 entrypoint 與 full suite 不 import Pi-only / 網路 / Ch7 / Ch9 concrete

**產出**：
- `src/sbd/main.py`
- `tests/milestones/test_m1_foundation.py`（完整整合測試）

**相依**：WP-M1-01 ~ WP-M1-09 全部（最後整合）

**對應測項**：M1-LOG-004, M1-BOOT-001, M1-REG-001

**複雜度備註**：⚠️ 中高。需要 DEV-PROC level 的 subprocess 驗證 exit code（或 isolated asyncio.run）；fatal supervision 的 race-free 測試需 asyncio.Event barrier。

---

### 相依關係圖

```
WP-M1-01 (骨架)
  ├── WP-M1-02 (事件) ─────────────────┐
  │     ├── WP-M1-03 (Protocol)        │
  │     ├── WP-M1-04 (EventBus) ───────┤
  │     │     └── WP-M1-06 (Logger) ◄──┤── WP-M1-05 (Config)
  │     │                              │
  │     ├───────────── WP-M1-07 (SM) ◄─┤
  │     ├───────────── WP-M1-08 (RM) ◄─┘
  │     └── WP-M1-09 (Converger) ◄── WP-M1-03, WP-M1-07
  │
  └── WP-M1-05 (Config) ── 與 WP-M1-02 平行
                    │
                    └── WP-M1-10 (main.py) ◄── 全部
```

### 建議開發順序

| 順序 | 工作包 | SP | 可平行性 |
|:---:|:---|:---:|:---|
| 1 | WP-M1-01 骨架 | 3 | — |
| 2a | WP-M1-02 事件 | 3 | ↔ 與 2b 平行 |
| 2b | WP-M1-05 Config | 5 | ↔ 與 2a 平行 |
| 3 | WP-M1-03 Protocol | 2 | — |
| 4 | WP-M1-04 EventBus | 5 | — |
| 5 | WP-M1-06 Logger | 4 | — |
| 6a | WP-M1-07 SM | 8 | ↔ 與 6b 平行（部分） |
| 6b | WP-M1-08 RM | 6 | ↔ 與 6a 平行（部分） |
| 7 | WP-M1-09 Converger | 4 | — |
| 8 | WP-M1-10 main.py | 4 | — |
| | **合計** | **37** | |

### 風險識別

| 風險 | 影響 | 對應工作包 | 緩解策略 |
|:---|:---|:---|:---|
| SM inbox 消費迴圈的 async 時序難以測試 | M1-SM-001~006 可能需要大量 fixture | WP-M1-07 | 先定義 FX-BARRIER-WORKER fixture 框架，以 asyncio.Event 做明確 barrier，不用 sleep |
| Config cross-field validation 規則多 | 遺漏驗證項導致 runtime 才發現錯誤 | WP-M1-05 | 採 table-driven test 逐條對照 Ch 10 §5–§14 |
| Converger 的 shielded task 行為難以重現 | Level 2 timeout race 不穩定 | WP-M1-09 | 使用注入式 fake worker 控制 abort/force_abort 時序 |
| RM recovery barrier 與 SM 交互 | recovery 未完成時 SM 誤回 IDLE | WP-M1-08 + WP-M1-07 | 整合測試中以 call log 驗證 barrier set/clear 順序 |
| main.py exit code 需 subprocess 驗證 | pytest 內 asyncio.run 無法真實模擬 process exit | WP-M1-10 | 以 `subprocess.run` 啟動獨立 process 檢查 returncode |

### Test Spec 覆蓋對照

| 測項 ID | 對應工作包 | 驗收重點 |
|:---|:---|:---|
| M1-EVT-001 | WP-M1-02 | frozen/slots、欄位、nested sentinel、union 分類 |
| M1-EVT-002 | WP-M1-02 | UUID 格式、turn 遞增、correlation 隔離 |
| M1-CON-001 | WP-M1-03 | Protocol smoke、in-flight 邊界、ForceAbortReport |
| M1-BUS-001 | WP-M1-04 | exact-type、snapshot、順序、token lifecycle |
| M1-BUS-003 | WP-M1-04 | handler 失敗不阻斷、延後 ErrorOccurred |
| M1-BUS-004 | WP-M1-04 | CancelledError 穿透、fatal latch、wait_fatal |
| M1-SM-001 | WP-M1-07 | 訂閱/解除、callback enqueue、transition 不交錯 |
| M1-SM-002 | WP-M1-07 | Fact + task done join barrier |
| M1-SM-003 | WP-M1-07 | stale/duplicate Fact、no-Fact fatal |
| M1-SM-004 | WP-M1-07 | wake source mapping、timer 取消 |
| M1-SM-005 | WP-M1-07 | validator 正規化、next_perceptions 去重 |
| M1-SM-006 | WP-M1-07 | in-flight empty gate、flush/discard、recovery wait |
| M1-RM-001 | WP-M1-08 | preflight validation（graph 非法拒絕） |
| M1-RM-002 | WP-M1-08 | phase+DAG start、late-fill port |
| M1-RM-003 | WP-M1-08 | real→null fallback、coherence gate |
| M1-RM-004 | WP-M1-08 | catalog seal/freeze、Reasoner 限制查詢 |
| M1-RM-005 | WP-M1-08 | recovery barrier、capability 不變 |
| M1-RM-006 | WP-M1-08 | rollback/stop reverse order |
| M1-CAN-001 | WP-M1-09 | L1 parallel abort、per-kind timeout |
| M1-CAN-002 | WP-M1-09 | L2 dual-proof、禁止 task.cancel |
| M1-CAN-003 | WP-M1-09 | report 聚合、reentry fatal、CancelledError |
| M1-CFG-001 | WP-M1-05 | precedence、immutable、no global state |
| M1-CFG-002 | WP-M1-05 | cross-field validation table-driven |
| M1-CFG-004 | WP-M1-05 | SecretValue redaction、.env 安全 |
| M1-CFG-005 | WP-M1-05 | example file CI 驗證 |
| M1-LOG-001 | WP-M1-06 | handler 唯一、JSON parse、rotation |
| M1-LOG-002 | WP-M1-06 | ErrorOccurred observer、P5 WARNING |
| M1-LOG-003 | WP-M1-06 | redaction、truncation |
| M1-LOG-004 | WP-M1-06 + WP-M1-10 | fatal supervision、SM violation 區分 |
| M1-BOOT-001 | WP-M1-10 | exit code 2/3/4/0、rollback、flush timeout |
| M1-REG-001 | WP-M1-01 + WP-M1-10 | marker、import 隔離、無 skip/xfail |

---
