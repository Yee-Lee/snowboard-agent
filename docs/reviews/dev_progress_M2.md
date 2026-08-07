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
| **WP-M2-01** 測試骨架 | 3 | M2 entrypoint；mock HAL/worker/message/app fixtures；barrier/call-log；Pi-only import guard；Test ID 追溯骨架 | M2-REG-001（部分） | M1 PASS | 待開工 |
| **WP-M2-02** Payload 與 ToolRegistry | 5 | JSON-compatible validator；三種 exact schema；sealed registry；defensive schemas；side-effect-free validate 與 exactly-once dispatch | M2-PAY-001、M2-PAY-002 | WP-M2-01 | 待開工 |
| **WP-M2-03** External message | 8 | source/store/control/consumer；overflow；ownership；begin/consume/close race；flush/discard/stop | M2-MSG-001、M2-MSG-002、M2-MSG-004、M2-MSG-005 | WP-M2-01 | 待開工 |
| **WP-M2-04** Mock/null HAL | 8 | Audio/Display/Camera/GPIO Protocol；null/mock backend；lazy factory；格式、iterator、debounce 契約 | M2-HAL-001、M2-HAL-002、M2-HAL-004 | WP-M2-01 | 待開工 |
| **WP-M2-05** Worker execution/adapters | 6 | 單次 active call；Fact cardinality；cleanup-before-Fact；abort/force-abort；deterministic ASR/Vision/LLM/TTS | M2-WRK-001 | WP-M2-01 | 待開工 |
| **WP-M2-06** Perception workers | 6 | Listen/Read/Look；timeout/P5/exception/cancel；read arrival-order/at-most-once | M2-WRK-002 | WP-M2-03、04、05 | 待開工 |
| **WP-M2-07** PromptBuilder/Reasoner | 5 | 固定 prompt 排序；opaque pending metadata；capability 過濾；LLM 正規化與 clean-failure fallback | M2-WRK-003 | WP-M2-02、03、05 | 待開工 |
| **WP-M2-08** Action workers | 4 | Speak 完整播放；Tool 單次 dispatch；Rest no-op Fact；P5/cancel cleanup | M2-WRK-004 | WP-M2-02、04、05 | 待開工 |
| **WP-M2-09** Composition/InputSource | 5 | Button/Wake mock source；M2 RM graph；control late-fill；catalog/capability coherence；default mock composition | M2-FLOW-008（部分） | WP-M2-02、03、04、06、07、08 | 待開工 |
| **WP-M2-10** SM/RM 垂直整合 | 5 | 同步 validator 對齊；next-perception 過濾/去重；P5/exception/self-check；notice barrier；flush/discard 順序 | M2-FLOW-003、M2-FLOW-004、M2-FLOW-005、M2-FLOW-006 | WP-M2-03、06、07、08、09 | 待開工 |
| **WP-M2-11** Flows/Process/Regression | 5 | wake 多 turn；external-message action；SIGINT exit 0；21 Test ID 證據；M1/M2/full regression；Python 3.11 復驗 | M2-FLOW-001、M2-FLOW-002、M2-FLOW-008；M2-REG-001 | WP-M2-01～10 | 待開工 |
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
