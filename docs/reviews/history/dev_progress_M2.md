# Developer Progress ( dev_progress_M2.md )

本文件由 **Developer** 維護，用於紀錄各個 Milestone (M1 ~ M7) 的任務拆包 (Task Breakdown)、工作點數估算 (Story Points) 以及目前的實作進度。

**注意**：
1. 估點與排程不改變 `arch.md` 或 `implement/` 的設計契約，也不降低 `test_spec_M{x}.md` 的驗收門檻。
2. Developer 必須在 [C] 階段的 Test Spec 被審查通過後，才能正式進入本文件的規劃與後續開發。
3. 若估點時發現範圍過大或有實作困難，應開立 `IR_dev` 單據向 Designer 提出重構/切分申請。

---


## M2 ── Mock 對話垂直切片

### 進場與估點基準（2026-08-05）

* TR_spec_M2_I 已 Resolved，Designer 簽核 100% 覆蓋且無 Blocking finding，M2 正式進入 [D] 開發。
* M1 基線已於本 workspace 重跑：milestone entrypoint 1 passed，full suite 167 passed。
* 沿用 M1 口徑：1 SP 約為經驗開發者半天，包含產品實作、真實 assert、聚焦測試與必要回歸。
* M2 基準估點為 **60 SP**（依既有口徑約 30 人日），不含 Tester 獨立驗收、Designer 最終 review 與未知退件。M1 已完成的 config、SM、RM、WorkerCatalog 與 convergence 只計 M2 整合增量。

---

### 工作包總覽

| 工作包 | SP | 範圍與主要交付 | 主要 Test ID | 相依 | 狀態 |
| :--- | ---: | :--- | :--- | :--- | :--- |
| **WP-M2-01** 測試骨架 | 3 | M2 entrypoint；mock HAL/worker/message/app fixtures；barrier/call-log；Pi-only import guard；Test ID 追溯骨架 | M2-REG-001（部分） | M1 PASS | 完成（2026-08-07） |
| **WP-M2-02** Payload 與 ToolRegistry | 5 | JSON-compatible validator；三種 exact schema；sealed registry；defensive schemas；side-effect-free validate 與 exactly-once dispatch | M2-PAY-001、M2-PAY-002 | WP-M2-01 | 完成（2026-08-07） |
| **WP-M2-03** External message | 8 | source/store/control/consumer；overflow；ownership；begin/consume/close race；flush/discard/stop | M2-MSG-001、M2-MSG-002、M2-MSG-004、M2-MSG-005 | WP-M2-01 | 完成（2026-08-07） |
| **WP-M2-04** Mock/null HAL | 8 | Audio/Display/Camera/GPIO Protocol；null/mock backend；lazy factory；格式、iterator、debounce 契約 | M2-HAL-001、M2-HAL-002、M2-HAL-004 | WP-M2-01 | 完成（2026-08-07） |
| **WP-M2-05** Worker execution/adapters | 6 | 單次 active call；Fact cardinality；cleanup-before-Fact；abort/force-abort；deterministic ASR/Vision/LLM/TTS | M2-WRK-001 | WP-M2-01 | 完成（2026-08-07） |
| **WP-M2-06** Perception workers | 6 | Listen/Read/Look；timeout/P5/exception/cancel；read arrival-order/at-most-once | M2-WRK-002 | WP-M2-03、04、05 | 完成（2026-08-07） |
| **WP-M2-07** PromptBuilder/Reasoner | 5 | 固定 prompt 排序；opaque pending metadata；capability 過濾；LLM 正規化與 clean-failure fallback | M2-WRK-003 | WP-M2-02、03、05 | 完成（2026-08-07） |
| **WP-M2-08** Action workers | 4 | Speak 完整播放；Tool 單次 dispatch；Rest no-op Fact；P5/cancel cleanup | M2-WRK-004 | WP-M2-02、04、05 | 完成（2026-08-07） |
| **WP-M2-09** Composition/InputSource | 5 | Button/Wake mock source；M2 RM graph；control late-fill；catalog/capability coherence；default mock composition | M2-FLOW-008（部分） | WP-M2-02、03、04、06、07、08 | 完成（2026-08-07） |
| **WP-M2-10** SM/RM 垂直整合 | 5 | 同步 validator 對齊；next-perception 過濾/去重；P5/exception/self-check；notice barrier；flush/discard 順序 | M2-FLOW-003、M2-FLOW-004、M2-FLOW-005、M2-FLOW-006 | WP-M2-03、06、07、08、09 | 完成（2026-08-07） |
| **WP-M2-11** Flows/Process/Regression | 5 | wake 多 turn；external-message action；SIGINT exit 0；21 Test ID 證據；M1/M2/full regression；Python 3.11 復驗 | M2-FLOW-001、M2-FLOW-002、M2-FLOW-008；M2-REG-001 | WP-M2-01～10 | 完成（2026-08-07） |
| **合計** | **60** | | **21 個 M2 Test ID 全覆蓋** | | |

---

### 工作包最低驗收

#### WP-M2-01：測試骨架（3 SP）

- 建立 tests/milestones/test_m2_mock_pipeline.py，避免 wildcard re-export 重複 collection。
- fixtures 只以 asyncio.Event、Condition predicate、queue barrier 或 completion notice 控時，不用 sleep 猜 race。
- M2 可 collection、fixtures 有真實 assert，且 M1 167 passed 維持不變。

#### WP-M2-02：Payload 與 ToolRegistry（5 SP）

- validator 深度受限、不 mutation、拒絕 NaN/bytes/custom value；Reasoner 與 SM 共用同一同步 instance。
- registry 支援 duplicate/seal、sorted defensive schemas；validate 不呼叫 handler，dispatch exactly once。
- M2-PAY-001、M2-PAY-002 通過，error/log 不含 payload 或 secret sentinel。

#### WP-M2-03：External message（8 SP）

- 依 Ch 7 建立 models、buffer、source、consumer，固定 store-before-publish、UUIDv4 與 arrival order。
- 以單一 ownership lock/condition 線性化 begin/assign/consume/close；覆蓋 notify-before-wait、並行 ingest 與三種 cancel 時點。
- flush 在 lock 外以原 ID 重發；discard/stop 收斂 waiter；M2-MSG-001、M2-MSG-002、M2-MSG-004、M2-MSG-005 通過。

#### WP-M2-04：Mock/null HAL（8 SP）

- 依 Ch 2a 建立 core/audio、display、camera、gpio；factory 只 lazy import 選定 backend，GPIO 不建 NullGPIO。
- 覆蓋 audio frame/獨占 iterator、display buffer、camera RGB/YUV/JPEG、GPIO subscriber/debounce/output。
- M2-HAL-001、M2-HAL-002、M2-HAL-004 通過，lifecycle 收斂無 task，import guard 無 Pi/native dependency。

#### WP-M2-05：Worker execution/adapters（6 SP）

- 以 private helper 實作重入拒絕、normal/P5/exception/cancel 互斥、cleanup-before-publish 與純 asyncio force-abort，不新增 public API。
- 提供可控 timeout/reject/bad-output/exception 的 deterministic adapters。
- M2-WRK-001 覆蓋每種 worker；cancel 無 normal Fact；Fact 不早於 cleanup；無殘留 task。

#### WP-M2-06：Perception workers（6 SP）

- 建立 Listen/Read/Look，正規化 kind/status/text/extra 與 IDs。
- Read 只持有 consumer 窄介面，assigned item 最多消費一次，cancel/timeout 先 cleanup。
- M2-WRK-002 的 success/empty/timeout/error/cancel 全部通過。

#### WP-M2-07：PromptBuilder/Reasoner（5 SP）

- 固定 listen/read/look 排序；pending 只暴露 count/opaque ID；每 turn 無隱藏 history。
- 只選 startup-static capability 可用 kind；timeout/reject/bad JSON 轉 apology 或 rest fallback，raw output 不進 event/log。
- M2-WRK-003 通過，perception 完成順序不改變 canonical prompt order。

#### WP-M2-08：Action workers（4 SP）

- Speak 播放全部 PCM 並釋放 audio 後才發 Fact；Tool 只由 action worker dispatch 一次。
- Rest 只發 no-op Fact，不呼叫 SM/buffer/他人資源；可翻譯失敗為 ActionCompleted(error)。
- M2-WRK-004 通過，handler exactly once，cancel/P5 無殘留 task。

#### WP-M2-09：Composition/InputSource（5 SP）

- 建立 Button/WakeWord mock source與 M2 graph：HAL、buffer、adapters、workers、Reasoner、registry、validator。
- SM 先 READY；RM 完成 catalog seal/capability freeze/control late-fill 後才 arm producer。
- default composition 使用 mock config 進 IDLE，無 Pi/network/model/credential；保留 M1 composition 作 regression fixture。

#### WP-M2-10：SM/RM 垂直整合（5 SP）

- 對齊 Ch 9 同步 validator；unknown next kind 過濾並 WARNING；duplicate 保留首次；rest 忽略 next list。
- worker exception 先 ErrorOccurred 再 ERROR；SM self-check 直接 ERROR；P5 使用 fallback/default perceptions。
- convergence return 後仍等 _TaskCompleted；rest 先 IDLE 再 flush，error/interrupt/shutdown discard。
- M2-FLOW-003、M2-FLOW-004、M2-FLOW-005、M2-FLOW-006 通過，結束時 in-flight/read window/waiter 全空。

#### WP-M2-11：Flows/Process/Regression（5 SP）

- 完成 wake 多 turn 與 external-message action 兩條 deterministic session。
- 完成 subprocess SIGINT/exit 0、sanitized IDLE log、無殘留 task/handle。
- 產出 21 Test ID 到 pytest node ID、race barrier/call-log、聚焦、M1、M2、full suite 證據；交 Tester 前在 Python 3.11 clean env 復驗。
- M2-FLOW-001、M2-FLOW-002、M2-FLOW-008、M2-REG-001 與 test spec 四條正式命令通過，無新 skip/xfail。

---

### 相依與建議順序

1. WP-M2-01 先固定測試命名、barrier 與 regression guard。
2. WP-M2-02/03/04/05 是可獨立交付的第一批元件。
3. WP-M2-06/07/08 各自先以 WRK Test ID 收斂，不等 app 完成才測。
4. WP-M2-09 組裝 graph；WP-M2-10 收斂跨模組狀態；WP-M2-11 只處理 milestone 證據與回歸。

---

### Test Spec 覆蓋對照

| Test ID | 主責包 | 整合/回歸包 |
| :--- | :--- | :--- |
| M2-HAL-001、M2-HAL-002、M2-HAL-004 | WP-M2-04 | WP-M2-06、08、09、11 |
| M2-WRK-001 | WP-M2-05 | WP-M2-06、07、08、10、11 |
| M2-WRK-002 | WP-M2-06 | WP-M2-03、04、10、11 |
| M2-WRK-003 | WP-M2-07 | WP-M2-02、03、09、10、11 |
| M2-WRK-004 | WP-M2-08 | WP-M2-02、04、10、11 |
| M2-PAY-001、M2-PAY-002 | WP-M2-02 | WP-M2-07、08、09、10、11 |
| M2-MSG-001、M2-MSG-002、M2-MSG-004、M2-MSG-005 | WP-M2-03 | WP-M2-06、09、10、11 |
| M2-FLOW-001、M2-FLOW-002 | WP-M2-11 | WP-M2-03、06、07、08、09、10 |
| M2-FLOW-003、M2-FLOW-004、M2-FLOW-005、M2-FLOW-006 | WP-M2-10 | WP-M2-02、03、05、06、07、08、09、11 |
| M2-FLOW-008 | WP-M2-09 | WP-M2-11 |
| M2-REG-001 | WP-M2-01 | WP-M2-11 |

### 開發紀錄

#### 2026-08-07：WP-M2-01 完成

- 建立明確檔案清單式 M2 milestone entrypoint 與 21 個 Test ID 追溯 manifest；未映射 Test ID 會使正式 M2 gate 明確失敗，不會假綠燈。
- 建立 `FX-BARRIER-WORKER`、call-log、`FX-MOCK-HAL`、`FX-MOCK-WORKER`、`FX-MESSAGE`、`FX-MOCK-APP` deterministic fixtures；race 控時只使用 `asyncio.Event`。
- 新增 `M2-REG-001` 部分證據：fixture barrier/call ordering、fixture 有效性與 default package Pi-only import guard，共 3 個真實 assert test。
- 驗證環境：workspace `.venv` Python 3.12；移除 host ROS `PYTHONPATH` 並設定 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，避免外部 `launch_testing` plugin 污染。
- `python -m pytest --collect-only -q tests/milestones/test_m2_mock_pipeline.py`：1 collected，PASS。
- `python -m pytest -q tests/test_m2_reg_001.py`：3 passed。
- `python -m pytest -q tests/milestones/test_m1_foundation.py`：1 passed（entrypoint 內執行既有 M1 suite）。
- 正式 M2 entrypoint 目前預期為 RED：HAL/WRK/PAY/MSG/FLOW 共 20 個 Test ID 尚未映射，`M2-REG-001` 只有部分證據；這是後續 WP-M2-02～11 的開發 gate，不視為 defect 或 M2 PASS。

#### 2026-08-07：WP-M2-02 完成

- 新增同步 `ActionPayloadValidator`：plain JSON value、最大深度 32、finite float、speak/tool/rest exact schema、輸入不 mutation 與 sanitized path/reason error。
- 新增 sealed `ToolRegistry`：registration validation、duplicate/seal、sorted defensive schemas、side-effect-free synchronous validate、unknown-before-handler 與 exactly-once async dispatch。
- 將 M1 StateManager 的 validator port/call seam 對齊 Ch 9 已簽核同步 API；M1 rejecting fake 同步更新，驗收門檻未放寬。
- `python -m pytest -q tests/test_m2_pay_001_002.py tests/test_state_manager.py`：20 passed。
- Test ID 證據：`M2-PAY-001` 2 nodes、`M2-PAY-002` 2 nodes；均已加入 M2 manifest。


#### 2026-08-07：WP-M2-03 完成

- 新增 `ExternalMessageSource`、canonical model、single-lock/Condition buffer、SM control 與 narrow read consumer；store-before-publish、UUIDv4/sequence、arrival order 與 payload-free Signal 均固定。
- ownership/read-window 覆蓋 queued→session/pending→turn→consumed、consume/close/late-assign 線性化、notify-before-wait、timeout/cancel/discard/stop waiter 收斂。
- overflow 在接受後才分配 ID/sequence；drop-oldest 不淘汰 turn-owned，drop-newest/reject 不發 Signal；flush 於 lock 外按原 ID/arrival 重發。
- 將 M1 `ExternalMessageControl` seam 對齊 Ch 7 `begin_read() -> tuple` 與 `discard()` 正式 API。
- `python -m pytest -q tests/test_m2_msg_001_002_004_005.py tests/test_state_manager.py`：24 passed；目前全部 M2 component tests：15 passed；M1 milestone：PASS。
- Test ID 證據：`M2-MSG-001/002/004/005` 共 8 nodes，已加入 M2 manifest。

#### 2026-08-07：WP-M2-04 完成

- 新增 Audio/Display/Camera/GPIO Protocol 與 mock/null backend；四組 factory 僅 lazy import 所選 backend，GPIO 明確不提供 NullGPIO。
- AudioInput 同 process 單一 active iterator、`aclose()`/stop 釋放與 reopen；AudioOutput 完整消費；Display back-buffer/show 與 pixel length validation。
- Camera 產合法 RGB/I420 YUV，並以純 Python baseline encoder 產任意合法尺寸 JPEG；系統 `file` 獨立辨識為 JFIF baseline 13x9。
- MockGPIO 覆蓋一 pin 一 owner、edge/debounce、callback task isolation、冪等 unregister 與 configure-before-set output。
- `python -m pytest -q tests/test_m2_hal_001_002_004.py`：4 passed；M1 milestone：PASS；import guard 未載入 sounddevice/picamera2/gpiod/native display。
- Test ID 證據：`M2-HAL-001/002/004` 共 4 nodes，已加入 M2 manifest。

#### 2026-08-07：WP-M2-05、06、08 完成

- 新增 private single-call worker runtime：reentry rejection、inner operation ownership、cooperative abort、pure-async force-abort 與 outer-task done proof；未取消 outer task冒充完成。
- 新增 deterministic ASR/Vision/LLM/TTS adapters，可控 normal、P5、unexpected exception、block/cancel；adapter 不 publish Event。
- Listen/Read/Look 覆蓋 cleanup-before-Fact、timeout/error、message arrival-order/at-most-once、cancel 無 normal Fact；unexpected exception 恰一 sanitized `ErrorOccurred` 後逸出。
- Speak 完整播放所有 PCM 後發 Fact；Tool 只在 dispatch 執行 handler 一次；Rest 只發 no-op Fact；P5 轉 `ActionCompleted(error)`。
- active abort/force-abort 均等待 outer task done、回空 `ForceAbortReport` 且無殘留 operation task。
- `python -m pytest -q tests/test_m2_wrk_001_002_004.py`：6 passed；目前全部 M2 component tests：25 passed；M1 milestone：PASS。
- Test ID 證據：`M2-WRK-001/002/004` 共 6 nodes，已加入 manifest；`M2-WRK-003` 於 IR Revised 後完成。

#### 2026-08-07：WP-M2-07 完成

- Designer 將 `IR_dev_M2_I` 標為 Revised；Ch 2 新增 Reasoner `action_validator` 參數，Ch 5 明定與 SM 共用同一 instance，依裁定解除阻塞。
- 新增 deterministic PromptBuilder 與 Reasoner normalizer：固定 perception 排序、opaque pending IDs、無 hidden history、capability 過濾、同步 payload 驗證。
- timeout/reject/empty/bad JSON 走 apology speak 或 rest fallback；raw output 不進 Event/log；cancel 與 unexpected exception 分支互斥。
- `python -m pytest -q tests/test_m2_wrk_003.py tests/test_contracts.py tests/test_resource_manager.py`：40 passed；`M2-WRK-003` 共 3 nodes。

#### 2026-08-07：WP-M2-09 完成

- 新增 Button/WakeWord mock InputSource 與 external source late-fill/arm 接線；producer 只在 catalog seal/capability freeze 後可用。
- 新增 default M2 graph：mock HAL、adapters、perception/action workers、Reasoner、registry/validator 與 input producers；保留 explicit M1 composition fixture。
- main 在 SM 前建立 validator，default composition 將同一 instance 注入 Reasoner；M1/custom 路徑以 lazy import 維持 M1 concrete-module boundary。
- default subprocess 無 Pi/network/model/credential 即進 `state=IDLE`，SIGINT/SIGTERM exit 0。

#### 2026-08-07：WP-M2-10 完成

- SM THINK Exit 使用同步 validator，unknown next kind WARNING 過濾、duplicate stable dedupe、rest 忽略 next，missing target/invalid payload 直接 self-check ERROR。
- production/focused flows 覆蓋 perception/LLM/action P5、worker ErrorOccurred→ERROR 與 self-check 無 ErrorOccurred 的分流。
- completion notice 前不離開 ACTION/PERCEPTION；rest 固定 IDLE→flush，error/interrupt/shutdown 固定 discard，結束無 in-flight/read window。
- `python -m pytest -q tests/test_m2_sm_flows.py tests/test_state_manager.py`：20 passed；`M2-FLOW-003/004/005/006` 完成。

#### 2026-08-07：WP-M2-11 與 M2 DoD 完成

- production M2 graph 完成 button 兩 turn speak→rest 與 external read-once→action→rest；另完成 bad-LLM fallback session。
- default `python -m sbd.main` 由 subprocess 證明 IDLE、SIGINT exit 0、無 startup/runtime fatal；process smoke 不取代 session asserts。
- 21 個 Test ID 全部映射到唯一 pytest node；manifest 無 empty/partial、無 skip/xfail。
- `python -m pytest -v tests/milestones/test_m2_mock_pipeline.py`：1 passed（內層 manifest 全綠）。
- `python -m pytest -v tests/milestones/test_m1_foundation.py`：1 passed（內層 166 passed）。
- `python -m pytest -q`：204 passed。
- workspace `.venv` 為 Python 3.12.3，符合 DEV-PY311「Python 3.11 以上」；本機未提供獨立 `python3.11` binary。

#### 2026-08-07：PM Feedback 修正 (OUT-M2-2026-003)

- **根因說明**：重建 history 時，初始 snapshot 係透過 `git add src tests docs` 等手動拉取，未包含 repository root 的 `pyproject.toml`，導致 clean env 無法安裝套件與取得 test metadata。
- **確認方式**：比對 accepted M1 tree 與重建後的 initial commit tree，確認僅遺漏 `pyproject.toml` 等非目錄檔案。
- **防止再發措施**：已重新加入可安裝的 `pyproject.toml`。後續若需重建 history 或 snapshot，將使用 `git archive` 匯出再匯入，確保根目錄設定檔一併包含。
---

### 主要風險與重估點條件

| 風險 | 緩解 | 主責包 |
| :--- | :--- | :--- |
| message lock/notify 錯誤造成遺失、重複或 deadlock | 單一 ownership lock、predicate wait、lock-order/cancel barriers | WP-M2-03、06、10 |
| Fact/task-done race 造成提早轉 state 或殘留 task | 分開 Fact、cleanup、task-done、notice barrier | WP-M2-05、10 |
| 元件綠燈但 graph/session 無法收斂 | coherence test 加兩條 session 與 P5/error/interrupt/shutdown 矩陣 | WP-M2-09、10、11 |
| mock startup 意外載入 Pi/native dependency | lazy import recorder 加 subprocess smoke | WP-M2-04、09、11 |
| host ROS PYTHONPATH 污染 pytest | 隔離 venv、排除 host PYTHONPATH，另以 Python 3.11 clean env 復驗 | WP-M2-01、11 |

以下情況需更新估點，不在 code 內自行改契約：

1. 已定稿 public API 無法在 Python 3.11 或現有 M1 邊界實作，需開 IR_dev_M2。
2. 任一包因新契約或平台要求增加超過 2 SP，或產生未列出的跨包相依。
3. 需要網路、Pi/native dependency、真實模型、MQTT 或 child process；這些均超出 M2 簽核範圍。

### M2 共同 Definition of Done

1. 不私自更改 implement/ public API；無法實作時停止並開 IR_dev_M2。
2. 對應 Test ID 有真實 assert 且測到 src/sbd/，不以 mock-only 取得假綠燈。
3. async race 使用明確 barrier；結束時無 task/handle/waiter。
4. log/exception 不含 credential、prompt、payload、transcript、原始音訊/影像或 raw model output。
5. 聚焦測試、M1 entrypoint 與 current full suite 通過，無新 skip/xfail。
6. 更新狀態、修改檔案、原始命令/結果與 Test ID 到 pytest node ID 證據。
