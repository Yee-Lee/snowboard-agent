# Snowboard M5.tool 測試規格 ( test_spec_M5_tool.md )

- **Owner**: Tester
- **Status**: Current（M5.tool Test Spec 已完成，作為 Developer 實作與 Pi Verify 驗收基準）
- **Working baseline**: 原 ALPHA `8b4af53f433c4bcdb5b858973e10767318986554`（見 [M5 §2.2](../milestones/M5.md#22-entry)）
- **權威上游**: [M5 §2](../milestones/M5.md#2-m5tool--工具能力開發與驗證)、[M5.tool 設計](../implement/ch_m5_tool.md)、[protocol.md §7 (`snowboard.llm/4`)](../protocol.md#7-m5tool-llm-protocol-v4)

---

## 1. 範圍、價值檢查與測試精簡原則

### 1.1 驗證目標

本規格將 `core-m5-tool-001` 的三條產品路徑——**answering**（`speak | end`）、**dispatching**（`tool` → `mock.send` → 固定回饋 → `listen`）與 **observing**（`look` → 固定準備語「我看一下。」→ 下一輪 `look` perception → 原 Conversation 回答）——映射為可執行 Test ID、輸入 fixture 與判定條件。

核心風險分界：
1. **真實模型能力選擇與有據回答**：在 Raspberry Pi 5 上使用真實 Gemma 4 E2B（LiteRT-LM 0.16.0）驗證能否依語意選對 `speak | end | tool | look`、保留 `mock.send` 訊息內容，並在下一輪根據不同 mock 觀察（含空偵測）回答原問題，不捏造未提供屬性、不把前次觀察帶入下次對話。只 mock handler（`mock.send`）與 Camera／Vision 輸入，**不得以注入語意或 mock LLM 代替真實模型能力選擇 PASS**。
2. **首輪 `runtime_prefill_tokens <= 128` 與效能觀測**：新 Conversation（`conversation_revision == 0`）首次合法推論必須維持 `runtime_prefill_tokens <= 128`；記錄首輪與同 Conversation 後續 turn（`conversation_revision >= 1`）的 prefill、首段安全文字等待與語意 terminal 等待。
3. **Core 驗證、固定回饋與錯誤／中斷收斂**：未知工具、非法參數或 `look` 輪再次選 `look`/`tool` 均在 handler 執行前拒絕；`mock.send` 單次合法意圖只執行一次；`tool_feedback` 由 SM 以固定語音（「已送出。」／「未能確認送出，請稍後再試。」）誠實回報且不再次呼叫 LLM；Look 錯誤／timeout 與 Conversation replacement 邊界不重播舊問題或注入孤立觀察。

### 1.2 測試精簡與證據邊界（依 `AGENTS.md` 與 M5 §2.3）

- **不計算／不驗證 SHA／digest**：Startup、child `READY`（v4）、`MEASURE`/`GENERATE`/`DISCARD_TICKET` 與所有測項均**不自動計算或驗證** source、patch、config、model、artifact、prompt、schema、evidence 或 input text 的 SHA-256／digest。Private runtime 直接比較實值。
- **不設行政簽核／freeze gate**：不建立 candidate freeze JSON、authorization 文件、owner 互簽或通用 close-proof matrix。
- **Lifecycle 斷言最小化**：僅在明確測試取消、中斷、replacement 與停止的測項（`M5T-WRK-001`、`M5T-SM-002`、`M5T-CAN-001`）驗證對應的取消／process group 收斂，不在一般功能測項重複堆疊 lifecycle 斷言。
- **公開證據最小化**：Public log 與驗收證據只記錄必要的 boolean、count、stable code（`intent`、`dispatch_status`、token counts、monotonic latency ms、sanitized error code）；prompt、使用者原話、`arguments.message`、Look `facts` 與 private session/request ID 只供 private runtime 驗證與現場人工判讀，不得寫入公開證據。

---

## 2. 驗收問題與 Test ID 對照矩陣

| M5 §2.3 驗收問題 | 保護的產品失敗風險 | 對應 Test ID | 執行層級 |
| :--- | :--- | :--- | :--- |
| **首輪效能與 v4 協定** | 完整能力 prompt 超過首輪 `128` prefill、後續輪被誤套 `128` 限制、ticket 未綁定實際 `text` 或混用 v3/v4 | `M5T-CFG-001`, `M5T-WRK-001`, `M5T-FLOW-001` | Portable + `RPI-NATIVE` |
| **原對話回歸與 Streaming** | 為支援工具而破壞 `speak`/`end` streaming、JSON key 順序變動導致誤播音、或後續欄位違反互斥時未取消播音並阻擋工具 | `M5T-WRK-002`, `M5T-FLOW-002` | Portable + `RPI-NATIVE` + `EV-MANUAL` |
| **派發驗證與輸入投影** | 未知工具／非法參數進入 handler、`look` 輪重複觸發 `look`/`tool`、`last_dispatch_status` 佔用使用者 20 字／32-token 配額、或 Look 觀察被誤套 32-token 限制 | `M5T-PAY-001`, `M5T-PAY-002` | Portable |
| **派發回饋與狀態誠實** | 派發失敗卻播報成功、回饋觸發第二次 LLM 推論、單次意圖重複派發、或下一輪 `listen` 模型不知前輪派發結果 | `M5T-SM-001`, `M5T-FLOW-002` | Portable + `RPI-NATIVE` + `EV-MANUAL` |
| **Look 接續、有據回答與錯誤處理** | Look 輪誤等新語音、模型忽略觀察或捏造細節、空偵測被當成錯誤、Look 失敗未回 `listen`、或 Conversation 遺失時把舊觀察灌入新對話 | `M5T-SM-002`, `M5T-FLOW-003` | Portable + `RPI-NATIVE` + `EV-MANUAL` |
| **中斷、停止與可觀察性** | `mock.send`、`tool_feedback` 或 `look` 等待時中斷造成遲到播音／跨 Session 污染，或 Display／log 洩漏 `arguments.message` | `M5T-CAN-001`, `M5T-LOG-001`, `M5T-FLOW-003` | Portable + `RPI-NATIVE` + `EV-MANUAL` |

---

## 3. M5.tool 專屬 Fixture 定義

除沿用 [`test_spec.md` §2.2](../test_spec.md#22-共用-fixture) 的共用 fixture 外，M5.tool 新增以下受控 fixture：

| Fixture ID | 用途與契約 |
| :--- | :--- |
| **FX-M5T-SEND** | `mock.send` handler 控制器與呼叫記錄器：無網路／外部 IO，記錄每次呼叫的 normalized `message` 與次數；可注入三種模式：`ok`（立即成功）、`error`（回報已知派發失敗）、`wait(event)`（可取消等待，供驗證 interrupt／timeout）。這些控制參數只由測試 harness 注入，不暴露給 LLM schema。 |
| **FX-M5T-VISION** | Mock Camera + `VisionAdapter` fixture：Camera 回傳固定非空 image bytes；`VisionAdapter.describe(image)` 透過 Look worker 正常管線回傳受控結果：<br>1. `OBS_BOOK`：`VisionResult(text="偵測到一本書。", extra={})`<br>2. `OBS_CUP`：`VisionResult(text="偵測到一個馬克杯。", extra={})`<br>3. `OBS_EMPTY`：`VisionResult(text="本次沒有辨識到支援的物件", extra={})`（`status="ok"` 正常空偵測）<br>4. `OBS_ERROR`：拋出可翻譯 adapter error<br>5. `OBS_TIMEOUT`：等待直到 Look worker timeout 或 cooperative cancel |
| **FX-M5T-V4-CHILD** | 遵循 `snowboard.llm/4` 的 deterministic child / adapter harness：可控制 `READY` 欄位、`MEASURED` token counts（含 `128`/`129` 邊界）、chunked JSON / `SAFE_TEXT` 順序、`RESULT(semantic=...)` 與 `REQUEST_FAILED(code="INVALID_SEMANTIC")`。 |

---

## 4. Portable 自動化測項規格（`PORTABLE-PY311/312/313`）

### `M5T-CFG-001`：`core-m5-tool-001` Profile Composition 與 M4 Baseline 隔離

- **來源契約**：[ch_m5_tool.md §1, §2.2, §6](../implement/ch_m5_tool.md#6-composition-與可觀察性)、[protocol.md §7.1](../protocol.md#7-m5tool-llm-protocol-v4)
- **平台／證據**：`DEV-PY311`（收斂）、`PORTABLE-PY311/312/313`；`EV-AUTO`
- **刺激與步驟**：
  1. 以 `core-m5-tool-001` 初始化 composition factory，檢查啟用的 capabilities、ToolRegistry、Perception adapters、LLM protocol 版本與 SDK 設定。
  2. 以既有 `core-m4b-cognition-001` 初始化 composition factory，檢查其 LLM protocol 版本與 capabilities。
  3. 注入真實 provider 初始化失敗或 profile 不相容組合（例如在 M4 profile 啟用 `tool`/`look`、或在 `core-m5-tool-001` 啟用 `read`/`wake`）。
- **判定條件（Pass Criteria）**：
  - `core-m5-tool-001` 固定啟用 real LLM/Audio/TTS 配置、mock Camera/Vision、`ToolRegistry` 僅註冊 `mock.send`、`look` 與 `tool` 啟用、`external-message`/`read` 與 `voice wake` 停用、`automatic_tool_calling=false`、schema 指向 `requirements/m5tool/semantic-output-v1.schema.json`，且選用 `snowboard.llm/4`。
  - `core-m4b-cognition-001` 維持 `snowboard.llm/3` 與 listen-only，不受新 profile 影響。
  - 真實 provider 失敗時直接依啟動失敗處理，**絕不靜默 fallback 為 mock**；非法 capability 組合在 composition 階段即拒絕。
  - 啟動過程不執行檔案或文字 SHA-256 計算。

---

### `M5T-WRK-001`：`snowboard.llm/4` READY、雙軌 Token 計數、首輪 `<=128` 邊界與實值 Ticket 綁定

- **來源契約**：[protocol.md §7.1, §7.2](../protocol.md#7-m5tool-llm-protocol-v4)、[ch_m5_tool.md §3, §4.2](../implement/ch_m5_tool.md#42-model-facing-input)
- **平台／證據**：`DEV-PY311`、`PORTABLE-PY311/312/313`；`EV-AUTO`
- **刺激與步驟**（使用 `FX-M5T-V4-CHILD` 與 child protocol handler）：
  1. **READY 實值核對**：驗證 v4 `READY`（`protocol=4`、`protocol_name="snowboard.llm/4"`、`profile_id="core-m5-tool-001"`、`response_schema_locator="requirements/m5tool/semantic-output-v1.schema.json"`，無 6 個 `*_sha256` 欄位）；測試夾帶 v3 版本號、缺少必要欄位或夾帶舊 `*_sha256` 欄位時的拒絕行為。
  2. **帶 `last_dispatch_status` 的 `listen` MEASURE**：在 `conversation_revision == 1` 送出含 `user_text="剛才送出了嗎"` 與完整 `text='{"source":"listen","last_dispatch_status":"ok","text":"剛才送出了嗎"}'` 的 v4 `MEASURE`（不含 `input_sha256`）；再測試 `text` 不是合法 listen wrapper 或 wrapper 內 `"text"` 與 `user_text` 不一致的情況。
  3. **Look MEASURE 免除 32-token 限制**：在 `conversation_revision == 1` 送出不含 `user_text` 的 Look wrapper（`user_tokens=80`，但 `current_kv_tokens + rendered_incremental_tokens + 128 <= 1024`）。
  4. **首輪 `runtime_prefill_tokens` 128／129 邊界 vs 後續輪豁免**：
     - Case A：`conversation_revision == 0`，`runtime_prefill_tokens = 128` → 進入 `GENERATE`。
     - Case B：`conversation_revision == 0`，`runtime_prefill_tokens = 129` → Parent 在 `GENERATE` 前判定失敗。
     - Case C：`conversation_revision == 1`，`runtime_prefill_tokens = 180`（且總 context `<= 1024`）→ 正常進入 `GENERATE`。
  5. **實值 Ticket 綁定與 `DISCARD_TICKET`**：`MEASURE` 取得 ticket 後，分別以相同 `text`、修改單一字元的 `text` 呼叫 `GENERATE`，以及在 R1 拒絕時呼叫無 `input_sha256` 的 `DISCARD_TICKET`。
- **判定條件（Pass Criteria）**：
  - `READY` 缺欄、多欄（含舊 `*_sha256`）或版本不符均觸發 E1 並終止回收 child PGID。
  - 帶狀態 `listen` 的 `user_tokens` 由 `user_text` 計算並套用 `<= 32` 限制，完整 wrapper 用於 `rendered_incremental_tokens`／`runtime_prefill_tokens`；若 `wrapper["text"] != user_text` 立即走 E1。
  - Look `MEASURE` 不套用 `user_tokens <= 32`，只要完整 context equation `<= 1024` 即通過。
  - `conversation_revision == 0` 時 `runtime_prefill_tokens == 128` 通過、`129` 在 `GENERATE` 前走 **E1**（不偽裝成 R1 輸入過長或 R2 context replacement）；`conversation_revision >= 1` 不套用 `128` 限制。
  - `GENERATE` 的 `text` 與 `MEASURE` 實值不符時立即走 E1；`DISCARD_TICKET` 完成 native scratch scrub 並回傳 `TICKET_DISCARDED`（三個 proof boolean 為 `true`），Conversation 保持 `ready`。

---

### `M5T-WRK-002`：v4 Streaming `SAFE_TEXT` 鎖定規則、互斥衝突取消與 `RESULT` 驗證

- **來源契約**：[ch_m5_tool.md §2.2, §5](../implement/ch_m5_tool.md#5-streaming-sdk-與-child-protocol)、[protocol.md §7.3, §7.4](../protocol.md#7-m5tool-llm-protocol-v4)
- **平台／證據**：`DEV-PY311`、`PORTABLE-PY311/312/313`；`EV-AUTO`
- **刺激與步驟**：
  1. **正常 `speak`／有文字 `end` streaming**：模擬 JSON stream 先後輸出 `intent="speak"`（或 `"end"`）與 `text="今天天氣很好。"`，以及 `"text"` 欄位先於 `"intent"` 到達的亂序 JSON stream。
  2. **`tool` 與 `look` 無 `SAFE_TEXT`**：模擬 `intent="tool"`（`tool_name="mock.send"`, `arguments={"message":"測試"}`）與 `intent="look"` 的完整 stream。
  3. **Streaming 後續欄位違反語意互斥**：模擬 stream 先輸出 `{"intent":"speak","text":"好，幫你送出"`（已觸發 `SAFE_TEXT`），隨後在同一個 JSON 出現 `"tool_name":"mock.send"` 或非空 `arguments.message`。
  4. **非法 JSON 結構**：模擬重複 key（如兩個 `"intent"`）、額外 key、缺少必填 key 或 prefix 與 terminal `semantic.text` 不一致。
- **判定條件（Pass Criteria）**：
  - 僅在鎖定 `intent="speak"` 或 `"end"`（非空文字）且已出現欄位無非空工具矛盾時才發出 `SAFE_TEXT`；若 `"text"` 先於 `"intent"` 到達，parser 先緩存，待鎖定 `"speak"`/`"end"` 後才依序（`sequence=0, 1...`）發出，不依賴 key 順序，也不等待尚未到達的空工具欄位。
  - `tool` 與 `look` 全程 `SAFE_TEXT` 次數為 `0`。
  - 後續欄位違反互斥或含重複／額外 key 時，child 不發 `RESULT`，改發 `REQUEST_FAILED(code="INVALID_SEMANTIC", request_terminal_proven=true, engine_usable=true)`；Parent 立即取消已啟動的播音並走 R2 replacement，**工具派發次數為 `0`**。

---

### `M5T-PAY-001`：四種語意 Envelope 驗證、Reasoner 路由映射與 Handler 前拒絕

- **來源契約**：[ch_m5_tool.md §2.1, §2.2, §4.2, §4.4](../implement/ch_m5_tool.md#21-m5tool-的能力)
- **平台／證據**：`DEV-PY311`、`PORTABLE-PY311/312/313`；`EV-AUTO`
- **刺激與步驟**（Table-driven）：
  1. 餵入四種合法 `ToolSemantic`：
     - `speak`：`text="你好呀！"`、`tool_name=""`、`arguments={"message":""}`
     - `end`（有文字與空文字兩種）：`text="再見。"` 或 `""`、`tool_name=""`、`arguments={"message":""}`
     - `tool`：`text=""`、`tool_name="mock.send"`、`arguments={"message":"請幫我拿水"}`
     - `look`（於 `source="listen"` 輪）：`text=""`、`tool_name=""`、`arguments={"message":""}`
  2. 餵入非法語意與邊界違規組合：
     - 未註冊工具名稱（如 `tool_name="mqtt.send"` 或 `"look"`）或 capability 未啟用
     - `intent="tool"` 但 `arguments.message` 為空／空白、或 normalize 後 `> 40` code points、或 `tool_name > 64` code points、或 `text` 非空
     - `intent="speak"` 但 `text` 為空、或 spoken characters `> 30`、或 raw `> 4096` code points、或夾帶非空 `tool_name`／`arguments.message`
     - `intent="look"` 但夾帶非空 `text`／`tool_name`／`arguments.message`
     - **Look 輪禁止再次 `look`／`tool`**：當本輪輸入為 `source="look"` 時，模型回傳合法格式的 `intent="look"` 或 `intent="tool"`。
- **判定條件（Pass Criteria）**：
  - 合法語意精確映射為：
    - `speak` → `speak + KEEP_NEXT + listen`
    - `end`（有文字）→ `speak + END_SESSION`；`end`（空文字）→ `rest + END_SESSION`
    - `tool` → `tool(mock.send) + KEEP_NEXT + listen`
    - `look` → `speak("我看一下。") + KEEP_NEXT + look`（Look 不進入 `ToolRegistry`）
  - 所有非法組合與 `source="look"` 輪出現的 `look`/`tool` 均在 Reasoner／validator 階段以 `INVALID_SEMANTIC` 拒絕並走 R2 replacement；`FX-M5T-SEND` 記錄到的 handler 呼叫次數恆為 `0`。

---

### `M5T-PAY-002`：Perception Projector（`listen` 狀態包裝與 `look` 長度邊界）

- **來源契約**：[ch_m5_tool.md §3, §4.2, §4.3, §4.4](../implement/ch_m5_tool.md#42-model-facing-input)
- **平台／證據**：`DEV-PY311`、`PORTABLE-PY311/312/313`；`EV-AUTO`
- **刺激與步驟**：
  1. 無前輪派發狀態的 `listen`（`<= 20` normalized code points）與 `> 20` code points 的 `listen`。
  2. 有前輪 `last_dispatch_status="ok"` 或 `"error"` 的 `listen`，其中使用者原話剛好 `20` normalized code points（包裝成 JSON 後總長 `> 20` code points）。
  3. `look` 正常觀察（含長度 `21..512` normalized code points 的 `facts`，以及空偵測字串 `"本次沒有辨識到支援的物件"`）。
  4. `look` 空字串 `facts=""` 或超長 `facts`（`513` normalized code points）。
  5. 未知 perception source（如 `"read"`）、同輪混合 `listen + look`、或 session/turn 不一致。
- **判定條件（Pass Criteria）**：
  - 無前輪狀態時，`listen` 投影為 normalized 原話；有前輪狀態時，投影為 `{"source":"listen","last_dispatch_status":"ok|error","text":"<normalized utterance>"}`，且 `20` 字限制只檢查 `<normalized utterance>`，不因 wrapper 拒絕合法 20 字原話。
  - `look`（`1..512` 字，含空偵測文字）投影為 `{"source":"look","status":"ok","facts":"...","instruction":"依本次觀察回答先前問題；未提供的資訊請說明無法判斷。"}`，不套用 20 字限制。
  - `look` 空 `facts` 或 `> 512` 字在推論前直接拒絕（不截斷半份資料），回傳 application-owned retry speech + `KEEP_NEXT + listen`，不呼叫 LLM `MEASURE`/`GENERATE`，Conversation revision 不變。
  - 未知 source、混合 perception 或 session/turn 不符視為 wiring error（走 E1）。

---

### `M5T-SM-001`：`dispatching` 完整狀態機、`tool_feedback` 固定語音與 `last_dispatch_status` 生命週期

- **來源契約**：[ch_m5_tool.md §3](../implement/ch_m5_tool.md#3-工具派發與固定回饋)
- **平台／證據**：`DEV-PY311`、`PORTABLE-PY311/312/313`；`EV-AUTO`、`EV-RACE`
- **刺激與步驟**：
  1. **派發成功路徑（`FX-M5T-SEND` = `ok`）**：`listen` 推論回傳 `tool(mock.send, message="買牛奶")`。觀察 Tool worker 執行、primary Tool Fact + task done join、`tool_feedback` phase 啟動、TTS 播放內容、Feedback Fact + task done join 與下一輪狀態。
  2. **下一輪 `last_dispatch_status` 傳遞與消費**：在步驟 1 後進入下一輪 `listen`（「送出了嗎？」），檢查傳給 Reasoner 的 cognition context 與 child `MEASURE` 輸入；成功推論後再進第三輪 `listen`，檢查 `last_dispatch_status` 是否已清除。
  3. **派發失敗路徑（`FX-M5T-SEND` = `error`）**：`listen` 推論回傳 `tool(mock.send, message="買牛奶")`，handler 回報 `ActionCompleted(tool, error)`。觀察回饋語音、handler 呼叫次數與下一輪 `listen` 的 `last_dispatch_status`。
  4. **Session 結束／Replacement 清除**：在產生 `last_dispatch_status` 後觸發 Session 結束或 Conversation replacement，檢查新 Session／新 generation 的首輪 `listen` 是否殘留舊 status。
- **判定條件（Pass Criteria）**：
  - 單次 `tool` 意圖只呼叫 `FX-M5T-SEND` **恰 1 次**。
  - Tool Fact + task done join 後，SM 移除 primary record，留在 `ACTION`（`action_phase="tool_feedback"`、in-flight `action_tool_feedback`），建立具**不同 correlation ID** 的唯一 Speak feedback record，**不產生 `ACTION → ACTION` 轉移，且不再呼叫 Reasoner／LLM**：
    - `ok` 固定播報 `"已送出。"`
    - `error` 固定播報 `"未能確認送出，請稍後再試。"`（絕不播報已送出，也不自動重送）
  - Feedback Fact + task done 兩者都完成 join 後，SM 才轉入下一輪 `listen`。
  - `last_dispatch_status`（`"ok"` 或 `"error"`）只保留給同一 Session／generation 的下一次成功 generation 消費一次，之後自動清除；Session 結束或 Conversation replacement 時立即清除，絕不跨 Session 或跨 generation 殘留。

---

### `M5T-SM-002`：`observing`（`look`）接續路徑、Look 錯誤／Timeout 與 Conversation Replacement 邊界

- **來源契約**：[ch_m5_tool.md §4.1–§4.4](../implement/ch_m5_tool.md#4-look-投影與原問題接續)
- **平台／證據**：`DEV-PY311`、`PORTABLE-PY311/312/313`；`EV-AUTO`、`EV-RACE`
- **刺激與步驟**：
  1. **正常 `observing` 接續**：Turn 1（`listen`）使用者詢問「前面是什麼？」，模型回 `intent="look"`。驗證 SM 播放固定準備語 `"我看一下。"`、記錄當時 Conversation `generation`，完成後直接進入 Turn 2 `PERCEIVE(look)`（不等待 `listen` 或按鈕）。`FX-M5T-VISION` 回傳 `OBS_BOOK`（或 `OBS_EMPTY`），驗證 Reasoner 在**同一個 Conversation `generation`**（`conversation_revision` 由 `1` 增為 `2`）送出 `source="look"` 推論並播報回答，最後回到 `listen`。
  2. **Look error／cooperative timeout**：Turn 1 選 `look` 並播完 `"我看一下。"` 後，Turn 2 `FX-M5T-VISION` 分別設定為 `OBS_ERROR` 與 `OBS_TIMEOUT`。
  3. **Look 輪發生 Conversation replacement／遺失**：Turn 1 選 `look`（記錄 `generation=1`），在 Turn 2 Look 推論前或 admission 時觸發 context replacement（或 Conversation generation 已變動）。
- **判定條件（Pass Criteria）**：
  - 正常路徑中，Turn 2 只啟動 Look worker，不等語音輸入，且與 Turn 1 共用同一 Conversation `generation`，不重送 history 文字。
  - `OBS_ERROR` 與 `OBS_TIMEOUT` 時，SM **不呼叫 LLM、不自動重試 Look**，直接播放 application-owned `"這次無法取得影像，請再試一次。"` + `KEEP_NEXT + listen`，原 Conversation 保持可用。
  - 若在 Look 結果產生前或 admission 時必須 replacement（或 generation 已不符），SM **放棄本次 Look 結果與原問題接續**，播放 `"這次無法接續原問題，請再說一次。"`，透過既有 replacement barrier 關閉舊 Conversation、開啟新 Conversation 後回 `listen`，**絕不把舊 Look `facts` 送進空白 Conversation，也不自動 replay 舊問題**。

---

### `M5T-CAN-001`：`dispatching`／`observing` 中斷取消與正常 `stop()` 收斂

- **來源契約**：[M5 §2.3](../milestones/M5.md#23-驗收問題)、[ch_m5_tool.md §3, §4.4](../implement/ch_m5_tool.md#3-工具派發與固定回饋)、[arch.md §6.4–§6.5](../arch.md#64-cancel-分級三級收斂)、[protocol.md §4.6](../protocol.md#46-cancel-and-shutdown)
- **平台／證據**：`DEV-PY311`、`PORTABLE-PY311/312/313`；`EV-AUTO`、`EV-RACE`
- **刺激與步驟**：
  1. 在 `FX-M5T-SEND` 處於 `wait(event)` 等待中時觸發 Interrupt（按鈕中斷）。
  2. 在 `tool_feedback` TTS 播音進行中時觸發 Interrupt。
  3. 在 Look worker（`FX-M5T-VISION` `OBS_TIMEOUT`）等待中或 Look 輪 LLM `GENERATING` 時觸發 Interrupt，隨後開啟新 Session。
  4. 完成一輪 `dispatching` 與 `observing` 後呼叫 application `stop()`。
- **判定條件（Pass Criteria）**：
  - 步驟 1–3 中斷後，當前 active phase 依 arch §6.4 完成 Level 1 合作式停止，或於 Level 1 逾時後完成 Level 2 `force_abort` 的終止／資源釋放證明；外層 task 完成、handle 移除後才轉移狀態。`FX-M5T-SEND wait(event)` 與 `FX-M5T-VISION OBS_TIMEOUT` 等受控可取消等待，在未注入故障時應走 Level 1。Look 輪 LLM `GENERATING` 可先收到 `CANCEL_DEFERRED`；若 Level 1 逾時，須由 Parent 終止／回收 child PGID，不得偽造 `CANCELLED`、`RESULT` 或 `CLOSED`。若 Level 2 成功但破壞 backend，須進 `ERROR` 並完成 recovery barrier 後才可開啟新 Session；若 Level 2 失敗，依架構進 Level 3 fatal process exit，不能以同一 process 的「中斷後新 Session 正常」判 PASS。所有已取消路徑均不得產生遲到播音、被取消操作的正常 Fact，或讓舊 `last_dispatch_status`／Look generation 污染後續 Session。
  - 步驟 4 正常 `stop()` 先完成 `CLOSE(reason="shutdown")` → `CLOSED` 再完成 `SHUTDOWN` → `SHUTDOWN_ACK`，無殘留 asyncio task 或 child process。

---

### `M5T-LOG-001`：公開日誌／證據紅線與 Display 投影

- **來源契約**：[ch_m5_tool.md §6](../implement/ch_m5_tool.md#6-composition-與可觀察性)、[protocol.md §1, §7](../protocol.md#7-m5tool-llm-protocol-v4)
- **平台／證據**：`DEV-PY311`、`PORTABLE-PY311/312/313`；`EV-LOG`
- **刺激與步驟**：
  1. 以包含敏感 sentinel 的輸入執行 `answering`、`dispatching`（`arguments={"message":"SECRET_MSG_99"}`）與 `observing`（`facts="SECRET_VISION_FACT_88"`）。
  2. 檢查所有 public logger 輸出、child stderr 與 Display adapter 收到的投影事件。
- **判定條件（Pass Criteria）**：
  - Public log 只出現 sanitized `intent`、`dispatch_status`、次數、token counts、stable code 與 timing；**不得出現** system prompt、使用者原話、`SECRET_MSG_99`、`SECRET_VISION_FACT_88` 或 private session/request ID。
  - Display 在 `tool` 執行時收到 `SCN-ACTION-TOOL`（不含 raw `arguments.message`），在 `tool_feedback` 時收到既有 `SCN-ACTION-SPEAK`，在 `look` 時收到 `SCN-PERCEPTION`。

---

## 5. Raspberry Pi 5 真實模型與實機驗收規格（`RPI-NATIVE` + `EV-MANUAL`）

所有開發內容必須在 Raspberry Pi 5 上對待提交的相同 bytes 完成下列驗證；Pi 驗證未通過前不得準備 commit。

### `M5T-FLOW-001`：Pi 真實 Gemma Schema 相容性與首輪 `runtime_prefill_tokens <= 128` 閘門

- **來源契約**：[M5 §2.3](../milestones/M5.md#23-驗收問題)、[ch_m5_tool.md §4.2, §7](../implement/ch_m5_tool.md#7-實作路徑與交-test-spec)、[protocol.md §7](../protocol.md#7-m5tool-llm-protocol-v4)
- **平台／證據**：`RPI-NATIVE`；`EV-RPI`（自動化 subprocess／integration harness，連接真實 LiteRT-LM 0.16.0 + Gemma 4 E2B）
- **刺激與步驟**：
  1. 啟動 `core-m5-tool-001` 的真實 v4 LLM child，驗證 `READY` 實值欄位。
  2. 開啟新 Conversation（`conversation_revision == 0`），送入代表性的首輪合法 `listen` 短句（涵蓋一般問候、明確送訊要求、明確看圖要求三類新 Session 首輪情境），執行 v4 `MEASURE` → `GENERATE`。
  3. 在同一 Conversation（`conversation_revision >= 1`）接續送入：
     - 帶 `last_dispatch_status="ok"` 與 `"error"` 的 `listen` 輸入
     - `OBS_BOOK`、`OBS_CUP` 與 `OBS_EMPTY` 的 `source="look"` 輸入
  4. 收集並記錄首輪（`revision == 0`）與後續輪（`revision >= 1`）的 `prompt_tokens`、`runtime_prefill_tokens`、`rendered_incremental_tokens`、`decode_tokens`、首個安全文字等待時間（`first_safe_text_latency_ms`，適用 `speak`/`end`）與語意 terminal 等待時間（`terminal_latency_ms`）。
- **判定條件（Pass Criteria）**：
  - 真實 LiteRT-LM 0.16.0 + Gemma 4 E2B 支援 `requirements/m5tool/semantic-output-v1.schema.json`，且在 `M5T-FLOW-002`／`M5T-FLOW-003` 指定情境中產出符合 schema 的 `speak`、`end`、`tool`（`tool_name="mock.send"`）與 `look` 四種合法語意，並通過各場景判準（不額外設定重複次數或統計門檻）。
  - **首輪硬門檻**：所有新 Conversation（`conversation_revision == 0`）首次合法 `listen` 的 `runtime_prefill_tokens <= 128`。
    - **阻擋回報規則**：若完整能力 prompt 導致首次合法 `listen` 的 `runtime_prefill_tokens > 128`，或縮減至 `<= 128` 後真實模型無法選對能力，必須判定 **Blocked／Fail 並回報 Designer 修正設計**；不得以隱藏 prewarm、額外隱藏推論、或未核准的第二 turn 啟用方式宣稱通過。
  - 後續輪（`conversation_revision >= 1`，含 `look` facts 與 `last_dispatch_status` wrapper）通過完整 context admission（`<= 1024`）並正常產生 `RESULT`。
  - Public evidence 完整記錄首輪與後續輪在 `answering`、`dispatching`、`observing` 三路徑的 token counts 與首段／terminal 等待時間（ms）。

---

### `M5T-FLOW-002`：Pi 真實模型 `answering` 回歸與 `dispatching`（`mock.send`）端到端驗收

- **來源契約**：[M5 §2.1, §2.3](../milestones/M5.md#23-驗收問題)、[ch_m5_tool.md §2, §3](../implement/ch_m5_tool.md#3-工具派發與固定回饋)
- **平台／證據**：`RPI-NATIVE` + 真實 Audio/ASR/TTS、Button、selected Display；`EV-RPI` + `EV-MANUAL`
- **刺激與步驟**：
  1. **場景 A — 原對話回歸（`answering`：`speak` → 同 Conversation 接續 → `end`）**：
     - 按鍵啟動 Session，對麥克風說一般聊天句（如「你好，簡單介紹一下你自己」）。
     - 聽取回答後，在同一 Session 第二輪追問需依賴前文的問題（如「那你可以幫我做什麼？」）。
     - 第三輪明確表達結束（如「好，先這樣，再見」）。
  2. **場景 B — 明確送訊成功（`dispatching`：`FX-M5T-SEND` = `ok`）**：
     - 開啟新 Session，說出明確送訊指令（如「幫我送訊息說我們已經到雪場了」）。
     - 觀察 Display、聽取固定回饋語音，並在自動回到 `listen` 後追問「剛才訊息有送出去嗎？」。
  3. **場景 C — 派發失敗誠實回報（`dispatching`：`FX-M5T-SEND` = `error`）**：
     - 將 `FX-M5T-SEND` 設為 `error`，開啟新 Session，說出相同送訊指令。
     - 聽取固定回饋語音，並在下一輪 `listen` 追問「剛才訊息有送出嗎？」。
- **判定條件（Pass Criteria）**：
  - **場景 A**：首輪 `runtime_prefill_tokens <= 128`；一般問答選 `intent="speak"`（有 `SAFE_TEXT` streaming、語音自然且 `<= 30` 字、`mock.send` 呼叫次數 `0`、不誤觸 `look`）；第二輪在同一 Conversation（`revision=1`）合理接續前文；第三輪選 `intent="end"` 並正常結束 Session 回 `IDLE`。
  - **場景 B**：真實模型選 `intent="tool"`、`tool_name="mock.send"`，且 private 驗證確認 `arguments.message` 保留使用者指定的核心訊息內容（如「我們已經到雪場了」）；`FX-M5T-SEND` 呼叫次數恰為 `1`；無 `SAFE_TEXT`；裝置清楚播報固定語音「已送出。」（不額外呼叫 LLM）並回到 `listen`；追問時模型依 `last_dispatch_status="ok"` 回答已送出／已派發，且不捏造外部對方已回覆。
  - **場景 C**：`FX-M5T-SEND` 呼叫次數恰為 `1`；裝置播報固定語音「未能確認送出，請稍後再試。」（**絕不說已送出**）；追問時模型依 `last_dispatch_status="error"` 誠實說明未能確認送出。

---

### `M5T-FLOW-003`：Pi 真實模型 `observing`（`look`）接續、雙觀察對照、空偵測與錯誤／中斷驗收

- **來源契約**：[M5 §2.1, §2.3](../milestones/M5.md#23-驗收問題)、[ch_m5_tool.md §4](../implement/ch_m5_tool.md#4-look-投影與原問題接續)
- **平台／證據**：`RPI-NATIVE` + 真實 Audio/ASR/TTS、Button、selected Display；`EV-RPI` + `EV-MANUAL`
- **刺激與步驟**：
  1. **場景 A — 觀察 Fixture 1（`OBS_BOOK`：「偵測到一本書。」）**：
     - 設定 `FX-M5T-VISION` 為 `OBS_BOOK`。按鍵啟動 Session，提問需看畫面才能回答的問題（如「幫我看一下前面有什麼東西？」）。
     - 觀察裝置是否先說「我看一下。」、是否不需再次按鍵／說話即自動執行 `look` 並回答問題；接著在同一對話追問未提供的細節（如「那本書是什麼顏色的？」）。
  2. **場景 B — 同一問題配觀察 Fixture 2（`OBS_CUP`：「偵測到一個馬克杯。」）**：
     - 設定 `FX-M5T-VISION` 為 `OBS_CUP`。開啟新 Session，對麥克風說與場景 A **完全相同的問題**（「幫我看一下前面有什麼東西？」）。
  3. **場景 C — 正常空偵測（`OBS_EMPTY`：「本次沒有辨識到支援的物件」）**：
     - 設定 `FX-M5T-VISION` 為 `OBS_EMPTY`。開啟新 Session，詢問「幫我看一下前面有什麼東西？」。
  4. **場景 D — Look 失敗回復與中斷停止**：
     - 設定 `FX-M5T-VISION` 為 `OBS_ERROR`（或 `OBS_TIMEOUT`），詢問看圖問題，觀察錯誤回饋後是否回到 `listen` 並可繼續一般對話。
     - 在 `observing` 等待期間再次按鍵中斷，確認立即停止；最後執行正常程式停止。
- **判定條件（Pass Criteria）**：
  - **場景 A & B（回答有依據且不跨輪殘留）**：
    - 兩場景首輪均選 `intent="look"`（`runtime_prefill_tokens <= 128`），先播報「我看一下。」，下一輪只執行 `look`（不等新語音），並在原 Conversation（`revision=1`）以 `intent="speak"` 回答（不再次選 `look` 或 `tool`）。
    - 場景 A 回答明確指出「書」；追問顏色時誠實說明觀察資料未提供／無法判斷，不捏造顏色。
    - 場景 B 對同一問題改回答「馬克杯／杯子」，**絕不殘留場景 A 的「書」**。
  - **場景 C（空偵測不等於錯誤或捏造）**：`OBS_EMPTY` 以 `status="ok"` 送入原 Conversation，模型自然回答沒有辨識到支援的物件／看不出有什麼，不當作系統錯誤，也不憑空捏造物件。
  - **場景 D（錯誤回復與中斷）**：`OBS_ERROR`／`OBS_TIMEOUT` 時播報「這次無法取得影像，請再試一次。」後進入 `listen`（不額外呼叫 LLM），接著說一般問候仍能正常回答；中斷後無遲到播音或新 Session 污染，正常停止 exit 0。

---

## 6. Developer 交付與 Verify 清單

Developer 完成實作與 Pi 自驗後，更新 `docs/status/development.md` 並交回 Verify 時須具備：

1. **Test ID 對照與執行結果**：`M5T-CFG-001`、`M5T-WRK-001`、`M5T-WRK-002`、`M5T-PAY-001`、`M5T-PAY-002`、`M5T-SM-001`、`M5T-SM-002`、`M5T-CAN-001`、`M5T-LOG-001`（Portable）與 `M5T-FLOW-001`、`M5T-FLOW-002`、`M5T-FLOW-003`（Pi 5 實機）對應的 pytest node ID／執行命令與全數 PASS 結果，以及直接受影響的 M1/M2/M4 回歸測試結果。
2. **固定產品資產與經驗整理（依 [M5 §2.4](../milestones/M5.md#24-排除與交付)）**：
   - `core-m5-tool-001` profile 與 `requirements/m5tool/semantic-output-v1.schema.json`
   - 若為通過真實模型能力選擇或首輪 `<= 128` prefill 而微調了 prompt 文字，須已同步回 [`docs/implement/ch_m5_tool.md` §2.3](../implement/ch_m5_tool.md#23-模型-prompt)
   - 已在 Pi 驗證可啟動 `dispatching`／`observing` 的示例說法與已知限制，以及首輪 vs 後續輪的 `runtime_prefill_tokens`、首段安全文字等待與語意 terminal 等待實測數據（整理於既有設計／狀態文件，不新增平行報告）。
3. **待提交內容一致性**：Pi 上驗證的內容與工作站待提交 bytes 完全一致（不內建自動 SHA/digest startup guard 或測項）。
