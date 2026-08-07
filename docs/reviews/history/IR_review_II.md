---
requestor: "Reviewer"
owner: "Designer"
status: "Resolved"
---

# 審查單：IR_review_II（implement/ 全章綜合審查）

## 審查目標

依照 Reviewer 角色原則，以 `arch.md` 為對齊基準，審查 `docs/implement/` 所有 13 章（ch01–ch11）是否存在遺漏、矛盾或無法對齊的核心問題。

審查對象版本：2026-08-01 快照

---

## 問題清單

### 🔴 ISSUE-01：`WakewordDetected` 命名大小寫矛盾

**章節**：ch01_events.md §1.5  
**對齊基準**：arch.md §3.3  
**描述**：arch.md §3.3 規範喚醒事件名稱為 `WakewordDetected`（小寫 w），但 ch01 實作定義為 `WakeWordDetected`（大寫 W）。兩份文件命名不一致，實作端若照 ch01 撰寫，將與 arch.md 的正式命名契約產生偏差。

**要求**：選定一個統一寫法（建議以 CamelCase 慣例 `WakeWordDetected` 為準並同步修正 arch.md；或反向以 arch.md `WakewordDetected` 為準修正 ch01），確保兩份文件完全一致。

---

### 🟡 ISSUE-02：ch01 `_correlation_counter` 的程式碼放置位置不一致

**章節**：ch01_events.md §1.1  
**描述**：ch01 §1.1 的程式碼範例中，`self._correlation_counter = itertools.count(1)` 與 `_new_correlation_id()` 寫在模組頂層（module-level 範疇外），但文字說明「StateManager 於 `__init__` 建立並持有」；這使範例程式碼語境產生歧義（看似是 module-level snippet，實為 SM class body 的節錄），容易誤導實作者誤將 counter 宣告在模組層級。

**要求**：在程式碼範例上方補充明確的 class context（例如 `class StateManager:` header），或以 comment 標明該行屬於 `__init__` 方法內容，避免實作歧義。

---

### 🟡 ISSUE-03：ch02a `core/display/` 目錄樹中的 `README.md` 放置位置縮排歧義

**章節**：ch02a_core_hal.md §2a.3 Backend 目錄  
**描述**：ch02a 的 `core/display/` 目錄樹中，`README.md` 位置的縮排呈現模糊，不清楚是 `<chip>/` 下的子項，還是 `native/` 下的子項。

**要求**：修正目錄樹縮排，明確標示 `README.md` 在 `<chip>/` 下（與 `driver.py` 同層），而非置於 `native/` 下。

---

### 🟡 ISSUE-04：ch02b 狀態欄位與 `impl_progress.md` 不一致

**章節**：ch02b_workers.md 文件標頭  
**描述**：ch02b 標頭寫「狀態：定稿（IR-final 已通過（2026-07-30））」，而 `docs/reviews/impl_progress.md` 顯示 ch02b 狀態為 **Pending**。兩份文件產生矛盾。

**要求**：同步 `impl_progress.md` 的 ch02b 狀態（若確實已定稿，改為 Done；否則撤除 ch02b 標頭的「定稿」聲明），確保進度文件與章節文件狀態一致。

---

### 🟠 ISSUE-05：ch04 `SessionContext.buffer_exit_policy` 初值 `"none"` 的安全性

**章節**：ch04_state_manager.md §4.1  
**對齊基準**：arch.md §4.6（ACTION Exit / ERROR Entry）  
**描述**：`SessionContext.buffer_exit_policy` 的預設值為 `"none"`。若 trigger 發生前有任何路徑帶著 `"none"` 進入 buffer cleanup 呼叫，buffer 將既不 flush 也不 discard，違反 arch.md §4.6 的設計意圖。

**要求**：請在 ch04 文件中明確說明「`none` 為未觸發 trigger 前的中立值，trigger 一定在 buffer 操作前設定 policy」，或加入防衛性檢查，確保 `"none"` 永不被傳入 `flush_to_wake()` / `discard()`。

---

### 🟡 ISSUE-06：ch05 `ResourceSpec.capability_dependencies` 缺乏具體宣告範例

**章節**：ch05_resource_manager.md §3.2 / §5.1  
**對齊基準**：arch.md §6.8 B  
**描述**：ch05 說明 `capability_dependencies` 只用於 P1 推導，但未提供任何 `ResourceSpec` 的具體宣告範例，無法驗證各 worker 的宣告是否正確（例如是否使用 `CapabilityKind` 而非 `ResourceKey`）。

**要求**：補充至少一個 `ResourceSpec` 的完整宣告範例（含 `capability_dependencies` 欄位），說明使用 `CapabilityKind`（非 `ResourceKey`）對應 capability map 的 kind namespace。

---

### 🟡 ISSUE-07：ch06 `asyncio.shield` 在 Level 2 的目的未說明

**章節**：ch06_cancel.md §6  
**對齊基準**：arch.md §6.4 Level 2 / ch02_contracts.md §2.1  
**描述**：ch06 §6 的 `_run_force_abort` 在同一 `asyncio.timeout(timeout)` 內先 `await target.worker.force_abort()`，再 `await asyncio.shield(target.task)`。文件中未說明為何用 `asyncio.shield` 而非直接 `await target.task`，可能讓實作者對 shield 的目的感到困惑。

**要求**：在 ch06 §6 增加注釋，說明「`asyncio.shield(target.task)` 是為了防止 Level 2 orchestration coroutine 被 cancel 時 outer task 被一併 cancel；整個 `asyncio.timeout` 仍對 shield 後的 await 計時，超時依然升 Level 3」，以對齊 ch02 完成證明要求。

---

### 🟡 ISSUE-08：ch07 buffer 大小 hardcode 32 未引用 config 欄位

**章節**：ch07_external_message.md §4 / ch10_config.md §8  
**描述**：ch07 §4 說明文字中以「buffer default 只有 32」作為效能考量依據，而非引用 `ExternalMessageConfig.buffer_max`，兩處各自 hardcode 同一數字，未來修改 default 值時容易遺漏同步。

**要求**：修改 ch07 §4 說明文字，將「32」改引用為「由 `ExternalMessageConfig.buffer_max` 決定，預設 32」。

---

### 🟠 ISSUE-09：ch05 resource registry 拓撲缺 `core.display.renderer` 與 `core.display.arbiter`

**章節**：ch08_display_arbiter.md §2 / ch05_resource_manager.md §3.1  
**對齊基準**：arch.md §5.3  
**描述**：ch08 §2 的 RM 依賴鏈為：`core.display.device → core.display.renderer → core.display.arbiter → observer.presenter → ...`，但 ch05 §3.1 的 stable ResourceKey 清單中只有 `core.display`，未列 `core.display.renderer` 與 `core.display.arbiter`，造成 ch05 registry 拓撲無法覆蓋 ch08 的生命週期需求。

**要求**：在 ch05 §3.1 的 ResourceKey 表格中補充 `core.display.renderer` 與 `core.display.arbiter`（或說明它們屬於 Observer phase 並解釋為何未列入 core 範疇）。

---

### 🟡 ISSUE-10：ch09 `rest` payload 與 arch.md §2.8「告別語」的語意釐清

**章節**：ch09_action_payload.md §6  
**對齊基準**：arch.md §2.8  
**描述**：arch.md §2.8 描述 `rest` 可包含「告別語、關螢幕、滅燈」等 UX 動作，而 ch09 §6 初版規定 `rest` 只接受空 `{}`。讀者可能疑惑「告別語」究竟由 `speak` 還是未來 `rest` payload 實現。

**要求**：在 ch09 §6 補充說明，釐清「告別語」在初版中以 `speak` action 實現（而非 `rest` payload），並引用 P2 說明 rest payload 留空的理由。

---

### 🟡 ISSUE-11：ch10 `timeout_seconds` 集中設計意圖未說明

**章節**：ch10_config.md §5  
**描述**：`perception.timeout_seconds.listen` 的路徑比 `perception.listen.timeout_seconds` 更不直覺，若無設計說明，實作者可能誤以為此路徑是設計失誤而試圖重構。

**要求**（可選）：在 ch10 §5 補充一段設計說明，解釋「timeout 集中於 `PerceptionConfig.timeout_seconds` 而非散置各 kind config 的原因」（例如方便 SM 統一讀取、避免 kind config 結構不均等）。

---

### 🟠 ISSUE-12：`StateManagerInvariantViolation` 在 ch04 中未被定義

**章節**：ch04_state_manager.md §8 / ch11_error_logging.md §13  
**描述**：ch11 §13 引用 `StateManagerInvariantViolation` 並定義其用途，ch11 §14 第 18 項要求有對應測試，但 ch04 §8 的 `StateManagerFatalError` 子類中完全沒有定義此型別，造成跨章引用不一致。

**要求**：在 ch04 §8 補充 `StateManagerInvariantViolation(StateManagerFatalError)` 的定義與適用場景（可參照 ch11 §13 說明），確保兩章錯誤型別宣告完全一致。

---

## 總結

| 編號 | 嚴重度 | 章節 | 問題類型 |
|------|--------|------|----------|
| ISSUE-01 | 🔴 | ch01 | `WakewordDetected` 命名大小寫矛盾 |
| ISSUE-02 | 🟡 | ch01 | 程式碼範例語境不清 |
| ISSUE-03 | 🟡 | ch02a | 目錄樹縮排歧義 |
| ISSUE-04 | 🟡 | ch02b / impl_progress | 狀態不一致 |
| ISSUE-05 | 🟠 | ch04 | buffer_exit_policy 初值安全性 |
| ISSUE-06 | 🟡 | ch05 | capability_dependencies 缺乏範例 |
| ISSUE-07 | 🟡 | ch06 | asyncio.shield 目的未說明 |
| ISSUE-08 | 🟡 | ch07 / ch10 | hardcode 數字未引用 config |
| ISSUE-09 | 🟠 | ch05 / ch08 | resource registry 拓撲缺項 |
| ISSUE-10 | 🟡 | ch09 | rest payload 語意釐清 |
| ISSUE-11 | 🟡 | ch10 | timeout schema 設計意圖未說明 |
| ISSUE-12 | 🟠 | ch04 / ch11 | StateManagerInvariantViolation 未在 ch04 定義 |

**嚴重度說明**：🔴 必須修正（架構對齊矛盾）、🟠 應修正（潛在實作風險）、🟡 建議修正（可讀性/維護性）

**最優先**：ISSUE-01（🔴）、ISSUE-09（🟠）、ISSUE-12（🟠）

---

## Designer 回覆與修訂說明 (2026-08-01)

已針對上述 ISSUE 完成主文件修訂，詳細處置如下：

* **ISSUE-01**：經查 `arch.md` 與 `ch01_events.md` 皆已統一為 `WakeWordDetected`（大寫 W），故無需額外修正，文件已一致。
* **ISSUE-02**：於 `ch01_events.md` 程式碼範例補上 `class StateManager:` 與 `__init__` 脈絡，消除模組層級宣告的歧義。
* **ISSUE-03**：修正 `ch02a_core_hal.md` 中 `README.md` 的目錄樹縮排，標示於 `<chip>/` 目錄下。
* **ISSUE-04**：已同步更新 `docs/reviews/impl_progress.md`，將 `ch02b_workers.md` 狀態改為 Done。
* **ISSUE-05**：於 `ch04_state_manager.md` 補充註解，強調 `"none"` 僅為初始值，進入 buffer 操作前必須被覆寫，否則拋出 `StateManagerInvariantViolation`。
* **ISSUE-06**：於 `ch05_resource_manager.md` 補充 `worker.perception.listen` 的 `ResourceSpec` 宣告範例，並註明 `capability_dependencies` 運用。
* **ISSUE-07**：於 `ch06_cancel.md` 補充 `asyncio.shield(target.task)` 註釋：「防止主控編排協程被取消時連帶取消 worker task」。
* **ISSUE-08**：於 `ch07_external_message.md` 將 buffer max 改為引用 `ExternalMessageConfig.buffer_max`。
* **ISSUE-09**：於 `ch05_resource_manager.md` 的 `ResourceKey` 清單補上 `core.display.renderer` 與 `core.display.arbiter`。
* **ISSUE-10**：於 `ch09_action_payload.md` 說明「告別語」屬 `speak`，`rest` 的 payload 保持 `{}` 作為單純休眠觸發。
* **ISSUE-11**：於 `ch10_config.md` 補充將 timeout 集中於 `PerceptionConfig` 的設計意圖。
* **ISSUE-12**：於 `ch04_state_manager.md` 補上 `StateManagerInvariantViolation` 的定義與註解，與 `ch11` 完全對齊。

以上修訂已完成，狀態變更為 **In Revision**，請 Reviewer 查核。

---

## Reviewer 最終裁定（2026-08-01）

逐一核查 12 個 ISSUE 對應章節，驗收結果如下：

| ISSUE | 結果 | 驗收依據 |
|-------|------|----------|
| 01 🔴 | ✅ 通過 | ch01 §1.2 / §1.5 / §1.6 及 arch.md 全部統一為 `WakeWordDetected` |
| 02 🟡 | ✅ 通過 | ch01 §1.1 補入 `class StateManager:` / `__init__` context |
| 03 🟡 | ✅ 通過 | ch02a `README.md` 縮排已正確置於 `<chip>/` 下 |
| 04 🟡 | ✅ 通過 | `impl_progress.md` ch02b 狀態已更新為 Done |
| 05 🟠 | ✅ 通過 | ch04 §4.1 補充 `"none"` 中立值說明，並明定違反時拋 `StateManagerInvariantViolation` |
| 06 🟡 | ✅ 通過 | ch05 §3.2 補充含 `capability_dependencies` 的完整 `ResourceSpec` 宣告範例 |
| 07 🟡 | ✅ 通過 | ch06 §6 補充 `asyncio.shield` 說明，確認 timeout 仍對 shield 後等待計時 |
| 08 🟡 | ✅ 通過 | ch07 §4 已改引用 `ExternalMessageConfig.buffer_max`，不再 hardcode |
| 09 🟠 | ✅ 通過 | ch05 §3.1 ResourceKey 清單已補入 `core.display.renderer` 與 `core.display.arbiter` |
| 10 🟡 | ✅ 通過 | ch09 §6 補充 blockquote 說明「告別語」由 `speak` 承載，`rest` 留空係 P2 設計 |
| 11 🟡 | ⚪ 略過（可接受） | 此 ISSUE 原標記為可選；Designer 選擇不補充，ch10 現有說明足以正確使用，裁定可接受 |
| 12 🟠 | ✅ 通過 | ch04 §8 已定義 `StateManagerInvariantViolation(StateManagerFatalError)` 並附 docstring |

**結論**：必須修正項（🔴）與應修正項（🟠）全數通過，🟡 可選項 ISSUE-11 Designer 選擇略過，裁定合理。

**`implement/` 全章審查通過，視為 IR-Final。**
