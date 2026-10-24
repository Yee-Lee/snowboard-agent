# Legacy：M1 Developer 內部程式碼檢查

> 本文件是歷史 Developer self-review 紀錄，不是 `docs/roles/workflow.md` 定義的跨角色審查單，不具備 Tester 驗收或 `TR_dev_M1` 效力。

審閱日期：2026-08-02
範圍：`src/`、`tests/`、M1 milestone / test spec。
結論：**M1 不應標示為「開發完成」或交 Tester 驗收。**目前測試的綠燈不能證明 M1 契約；State Manager、資源管理與程序收斂主線尚未完成。

## Developer 修正紀錄（2026-08-02）

本輪已完成內部檢查所列阻擋與高優先項目；最初結論與證據保留於下方供追溯。正式結果仍須由 Tester 依 test spec 與 workflow 獨立驗收。

| ID | 修正結果 | 驗證證據 |
|---|---|---|
| M1-DEV-001 | 以真實 barrier / observable assertion 重建 SM 測試，涵蓋原六項契約及 invariant、stale timer、validator、action、recovery gate。 | `tests/test_state_manager.py`：11 passed；M1 entrypoint 已納入。 |
| M1-DEV-002 | 完成 Fact + task-done join、result collection、reasoner response validation、action dispatch、turn continuation 與 fatal invariant。 | SM normal/error paths 由 11 個測試覆蓋。 |
| M1-DEV-003 | 統一 idempotent stop、fatal handoff、stopped event；bootstrap 加入一次性 SIGINT/SIGTERM bridge 與 first-root supervisor。 | bootstrap 測試覆蓋 exit 0/2/3/4、SIGINT、SIGTERM 與單一 CRITICAL。 |
| M1-DEV-004 | 完成 coherence gate、start/stop/recovery timeout、sealed catalog controlled replacement、dependency-order recovery 與 shutdown cleanup。 | `tests/test_resource_manager.py`：16 passed。 |
| M1-DEV-005 | 新增無硬體/網路依賴的 M1 composition，並以 subprocess 嚴格驗證 bootstrap exit code 與 rollback/fatal/signal。 | `tests/test_bootstrap.py`：6 passed；不再接受多種任意結果。 |
| M1-DEV-006 | ports 改為與正式實作一致的窄 Protocol（records + trigger、ticket wait API、validator/external/wake control）。 | SM fake ports 與 production implementation 共用同一呼叫契約。 |
| M1-DEV-007 | convergence 測試改用 `asyncio.Event` / completion barrier，不再用 wall-clock sleep 推測競態。 | `tests/test_convergence.py`：9 passed。 |
| M1-DEV-008 | loader 對 bool/int/float 採 exact-type，補 Literal、tuple/list、mapping 與 timeout bool 的遞迴負向驗證。 | config + convergence targeted suite：19 passed。 |
| M1-DEV-009 | SM 直接使用正式 shared `WorkerCatalog`，catalog 增加 perception/action 分類與 sealed query。 | 移除重複的 duck-typed catalog 宣告。 |

其他清理：RM 不再硬編碼未來 M2 HAL Null classes；fallback 由 `ResourceSpec.null_factory` 提供。`pyproject.toml` build backend 改為標準 `setuptools.build_meta`，並移除測試對 Python 3.12-only `__protocol_attrs__` 的依賴。

### Developer 最終自驗

在官方 `python:3.11-slim`（Python 3.11.15）內將唯讀工作區複製至 disposable directory，先以 `pip install ".[dev]"` 正式安裝，再執行：

* M1 entrypoint：`149 passed in 6.16s`
* full suite：`298 passed in 10.99s`
* M1 Test Spec：31 個唯一測項 ID；entrypoint 無 skip / xfail。

## 驗證紀錄

* 目前執行環境沒有 `python` 指令；直接使用規格命令無法收集測試。以 `python3` 執行時為 Python 3.12.3，且專案尚未安裝為 package，必須暫時加入 `PYTHONPATH=src`。
* 排除 bootstrap entrypoint 後，執行其餘 M1 模組得到 `121 passed, 1 warning`。此結果不是 M1 Pass：`tests/test_state_manager.py` 的六個測項皆為空 `pass`，沒有任何 assert。
* 對官方 M1 entrypoint 作 12 秒上限測試：`timeout 12s env PYTHONPATH=src python3 -m pytest -q tests/milestones/test_m1_foundation.py` 未完成，只輸出 58% 的點狀進度。它卡在 bootstrap 測試，符合下列 shutdown/supervision 缺口。
* 正式驗收仍須在 Python 3.11 的已安裝開發環境重跑；但必須先修復本文件的阻擋項目。

## 阻擋項目

| ID | 嚴重度 | Finding 與證據 | 影響 / 建議修正 |
|---|---|---|---|
| M1-DEV-001 | Critical | `tests/test_state_manager.py:4-38` 的 M1-SM-001~006 均只呼叫含 `pass` 的 coroutine。這違反 Test Spec 的所有 SM 可觀察結果與 Developer「真實 Assert」約束。 | 移除空測試，依 `test_spec_M1.md` / Ch 4 用 Event barrier 建立真實測試；至少覆蓋 subscription、Fact+done join、stale/duplicate、wake timer、reasoner 正規化、convergence 後 in-flight gate。未完成前不得聲稱 M1 100% 通過。 |
| M1-DEV-002 | Critical | State Manager 的 normal flow 尚未完成：`src/sbd/core/state_manager/manager.py:350-357` 明確留下「needs to be fixed」，而 `_TaskCompleted` 在 233 行已刪除 record，導致 perception facts 無處保存；`_enter_action()` 在 373-375 行直接回 IDLE，完全未啟動 action worker。 | 依 Ch 4 重新完成 Result collection、LLM response 驗證、action dispatch、turn continuation 和 Fact+task-done join。不要靠先移除 in-flight record 來推進 phase。 |
| M1-DEV-003 | Critical | Error/shutdown 主線無法正確收斂：`StateManager.stop()` 在 93-104 行定義後又於 134-145 行覆寫，後者不會 set `_stopped_event`；而 dispatch loop 160-161 行吞掉 `StateManagerInvariantViolation` 等一般例外，只記 log 後繼續。`main.py:89-107` 只等待 bus fatal / `sm.wait_stopped()`，沒有 SIGINT/SIGTERM bridge。 | 保留單一 idempotent `stop()`，確保所有正常 shutdown 都 set stopped；只把可處理錯誤導向 ERROR convergence，真正 SM invariant / worker contract error 必須傳到 supervisor 映射 exit 4；加入只 publish 一次的 signal bridge，並測試 SIGINT 後 exit 0。 |
| M1-DEV-004 | High | Resource Manager 的關鍵契約未實作：`_startup_coherence_gate()` 是 `pass`（269-272 行）；`start()`、`stop_all()`、recovery 沒有使用 config 的 per-resource timeout；recovery 在 catalog 已 `seal()` 後仍於 334-335 行 `register()`，必然 raise。 | 實作必要 source/default-perception coherence gate；將 config timeout 套用在 start/stop/rebuild；以 catalog 的受控 replacement API 更新既有 worker，不在 seal 後 register。補 rollback、recovery failure/timeout、dependency order 與 shutdown recovery 測試。 |
| M1-DEV-005 | High | Bootstrap 目前沒有註冊任何資源（`main.py:67-76`），卻以空 catalog 啟動 SM；之後 89-96 行無條件等待永遠不會完成的 stopped/fatal task。`tests/test_bootstrap.py:17-30` 一個測試把不存在的 config path 當成 config error（loader 的語意是缺檔採 default），另一個更允許 `SUCCESS` 或 `STARTUP_ERROR`。 | 建立 M1 fake-resource composition，明確選擇「預設 config 缺檔」語意並相應測試；以 subprocess 驗證 0/2/3/4，而不是允許任意成功或失敗。 |

## 高優先修正項目

| ID | 嚴重度 | Finding 與證據 | 建議 |
|---|---|---|---|
| M1-DEV-006 | High | `src/sbd/core/state_manager/ports.py:18-27` 的 `SessionConverger` / `RecoveryControl` Protocol 與實作不相容：Protocol 的 `converge(trigger)` 不接 records，實作需 `(records, trigger)`；Protocol 要 `wait_ready()`，RM 提供的是 `wait_recovery(ticket)`。 | 以 Ch 4 的正式窄介面定義單一 Protocol，讓 SM 只依此型別與 fake 驗證。移除或修正不相容的 dead interface，避免 M2 裝配時才發生 runtime error。 |
| M1-DEV-007 | High | Convergence 測試以多處 `asyncio.sleep()` 猜測 task 時序，例如 `tests/test_convergence.py:85-118`。Test Spec 明定 async race 必須用 `asyncio.Event` / 明確 barrier，不能用 wall-clock sleep。 | 為 abort start、outer task completion、force-abort completion 建立 fake barrier；斷言平行啟動、timeout 與 completion proof，而不是靠執行機器速度。 |
| M1-DEV-008 | Medium | Config loader 的型別檢查不可靠：`loader.py` 的 bool 分支內層條件不可達，且 `validate.py` 用 `isinstance(value, (int, float))` 接受 `True` / `False` 作為 timeout（Python bool 是 int）。 | 對 bool、int、float 分別使用 `type(value) is ...` 驗證；針對 `wake.ack_seconds: true`、timeout bool、Literal / tuple 元素型別補負向測試。 |
| M1-DEV-009 | Medium | `state_manager/manager.py:24-30` 重新宣告一個 duck-typed `WorkerCatalog`，與 `resource_manager.catalog.WorkerCatalog` 重複且沒有強制 sealed / registered 契約。 | 改用共用 Protocol 或直接匯入正式 catalog 型別；避免兩套 API 漸行漸遠。 |

## 多餘或應延後的實作

* `ResourceManager` 內硬編碼 `NullAudioInput` / `NullDisplay` 等 class，並忽略 `ResourceSpec.null_factory`。這使 M1 核心綁死未來 M2 HAL 名稱，也重複了 HAL 層責任。M1 可驗證「factory 提供 real→null fallback」的編排；具體 mock/null backend 應留在 M2 Ch 2a。
* 未使用的欄位與未接線控制流（例如 `_state_manager`、`_recovery_generation`、`_pending_convergence_trigger`）應在重做收斂流程時保留為完整模型，否則刪除；不要留半成品 state，因為它會製造「看似有 recovery」的錯覺。

## 建議修復順序

1. 將 `developer_progress.md` 的 M1 狀態改為「修正中」，不要先開始 M2。
2. 先替 M1-SM-001~006 與 M1-BOOT-001 / M1-LOG-004 寫會失敗的真實測試（barrier-based）。
3. 完成 State Manager 的單一 inbox、join、Action、convergence、shutdown 與 fatal handoff，再接好 main supervisor / signal bridge。
4. 完成 RM coherence、timeout、recovery replacement 與 rollback，移除 M2 HAL 具體類別耦合。
5. 將整合依賴安裝到 Python 3.11 venv，依序執行 M1 entrypoint、完整 pytest 與 `python -m sbd.main` 的 SIGINT subprocess smoke；所有命令全通過後才交 Tester。
