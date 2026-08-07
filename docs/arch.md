# Snowboard 架構設計

離線 AI 語音助理，執行於 Raspberry Pi 5 (Pi OS)。本文件描述模組權責、邊界、能力範圍與流程；實作進度與檔案清單見 `implement.md`。

## 1. 目標與邊界

### 1.1 產品定位

Snowboard 為裝置端執行的離線 AI 語音助理。核心承諾：

* 主要對話流程不依賴雲端
* 使用者可透過語音、按鈕、外部訊息任一入口喚醒
* 系統以 OLED 為本機主要表達通道

### 1.2 硬體與軟體堆疊

**硬體**

* I2S 麥克風
* I2S 喇叭
* SPI OLED
* 8MP CSI 相機
* GPIO（按鈕、LED、控制家電）

**軟體能力**

* ASR：離線語音辨識
* TTS：離線語音合成
* LLM：LiteRT-LM 執行 Gemma3:e2b
* Tool calling：本機工具註冊 + 執行
* 外部通訊：MQTT / UART / 其他 IPC
* 喚醒：wake word、GPIO 按鈕、外部訊息

### 1.3 貫穿性原則 P1-P5

以下五條為不可違反的架構原則，貫穿其他章節；違反即需回本節重新裁決。

* **P1 — Core = 契約 + Library Adapter**：`core/*` 把 OS / 社群 library 包成 Protocol 契約，不自寫 driver。同一契約下可並存多種實作，由 config 選擇。
* **P2 — 契約以本 agent 使用情境為依據**：不追求通用性；目前無人使用的能力不進契約。
* **P3 — Adaptor 只承擔對外通道**：每個 adaptor 對應一個明確對外用途；本機 HW 屬 core、不屬 adaptor。
* **P4 — 模組介面應允許未來跨 process**：可能獨立為 daemon 的模組（如 `voice_wake`），介面契約可序列化、不共享物件狀態；IPC schema 寫入 `docs/protocol.md`。
* **P5 — Worker Degradation Principle**：Worker 應盡可能在內部消化部分失敗、產出可用 fact，使 turn 能走完 perception -> think -> action 循環。內部降級可產出可用結果時，對外仍以 `status=ok` 呈現；降級後亦無可用結果時，對外以 `status=error` 呈現。Exception 洩漏（觸發 `ErrorOccurred`）為最後手段。錯誤兩層分界的完整責任見 §6.6。

---

## 2. 系統拓撲與責任歸屬

### 2.1 分層與依賴方向

生命週期分層：目錄結構直接對應對話生命週期。

```text
input_events -> perception -> cognition -> action
（外部觸發）    （感知）       （認知）    （行動）

adaptor      ：全程訂閱狀態，把系統狀態具現化到物理世界
core         ：所有實作能共享的基礎設施與硬體資源
adjustments  ：不進入對話流程的直接控制輸入（音量、亮度等）
```

流程協調 只經 SM 與 Event Bus：SM 用方法呼叫驅動 worker、發 `StateChanged`；worker 透過 Bus 發布事實或發送 Signal。能力取得 只經 core 契約：上層模組向 core 借用資源，不直接碰硬體。工作節點之間 互不相識，只認 SM 與 Bus。StateManager（SM）是唯一狀態擁有者與協調者。

抽象 + 多實作：有多實作需求的層遵循「抽象契約 + 多種實作」—— `base.py` 定義 Protocol，實作以子目錄組織；SM 只認契約不認實作。目前 `input_events` / `perception` / `action` / `adaptor` / 各 `core` HAL 皆採此結構。`cognition` 現況為單一 reasoner，暫不設 `base.py`；若未來加入第二種實作（例：雲端 reasoner），再引入契約——依 P2「契約以本 agent 使用情境為依據」，無多實作需求時不預先造契約。

HW 通道與語意角色分離：同一硬體通道可被多層借用，但語意角色由生命週期決定（例：麥克風是 `core/audio` 的資源；`voice_wake` 借它偵測喚醒詞、`perception/listen` 借它錄使用者語音）。

### 2.2 目錄總覽

```text
src/sbd/
├── main.py                # 進入點：組裝 + 啟動
│
├── core/                  # 基礎設施 + 硬體 HAL
│   ├── config/
│   ├── logger.py
│   ├── event_bus/         # 本機 pub/sub (asyncio direct-call)
│   ├── state_manager/     # 全局狀態機 (SM)
│   ├── audio/             # I2S mic/speaker
│   ├── display/           # SPI OLED
│   ├── camera/            # CSI 相機
│   └── gpio/              # GPIO 存取
│
├── input_events/          # 外部輸入層 -> 送 Signal 給 SM
│   ├── base.py
│   ├── button/
│   ├── external_message/  # MQTT-in 等外部訊息
│   └── voice_wake/        # IPC client：連線獨立的 wake daemon
│
├── adjustments/           # 直接控制輸入，不進 SM（音量、亮度等）
│
├── perception/            # 感知層
│   ├── base.py
│   ├── listen/            # 麥克風 + ASR
│   ├── read/              # 外部訊息 -> 文字
│   └── look/              # 相機 + 視覺
│
├── cognition/             # 認知層
│   ├── reasoner.py
│   ├── llm_engine.py
│   └── prompt_builder.py
│
├── action/                # 行動層
│   ├── base.py
│   ├── speak/             # TTS
│   ├── tool/              # 命令式 fire-and-forget
│   └── rest/              # session 收尾 (見 §2.8)
│
└── adaptor/               # 對外具現化 / 雙向通道
    ├── base.py
    └── mqtt/              # 對外 MQTT 通道
```

`models/`、`scripts/`、`deploy/`、`docs/`、`tests/` 支援目錄見 `implement.md`。

### 2.3 core/ ── 基礎設施 + 硬體 HAL

**職責分類**

* 軟體基礎設施：`config/`（三層設定，見 §7.1）、`logger.py`（統一 logger）、`event_bus/`（direct-call async pub/sub，見 §3.4）、`state_manager/`（SM，見 §3.5）
* 硬體 HAL：`audio/`、`display/`、`camera/`、`gpio/`

**core/audio 邊界**

* 只提供純 PCM 進出（frames stream / play）
* VAD、串流分段屬軟體演算法，留在 `perception/listen` 或 `voice_wake`
* 麥克風獨佔切換原則見 §5.2

**core/display 邊界**

* 低階原語（畫 pixel、寫文字、清畫面）
* 不含多寫入者仲裁：仲裁屬應用層與 HAL 之間的獨立層，見 §5.3
* 不含觸控事件源：目前無 touch 使用情境，依 P2 不進契約（見 §8.1）

**core/gpio 邊界**

* 集中管理 pin 存取，避免多模組爭搶
* 消費者：`input_events/button`、`action/tool`（家電控制）
* 分流常見規 §5.4

### 2.4 input_events/ ── 外部輸入層

職責：把物理世界的事件翻譯為對 SM 的 Signal（意圖類事件），觸發或影響對話流程。

契約：`InputSource` Protocol──能被啟動與停止的常駐輸入源，運作中對 Event Bus 發布 Signal 事件。

事件產出：`ButtonPressed`、`ExternalMessageArrived`、`WakeWordDetected`。事件簽名見 §3.3。未使用的輸入類型（knob / gesture 等）不建立；touch 屬未定案（§8.1）。

voice_wake 的位置：`input_events/voice_wake` 僅是獨立 wake daemon 的 IPC client。Daemon 本身屬 P4 原則的獨立 process 案例，IPC schema 見 `docs/protocol.md`。

外部訊息（`external_message`）的職責分工與 `read` perception 消費路徑見 §5.1。

### 2.5 adjustments/ ── 直接控制輸入

處理不改變對話狀態的操作類輸入（音量鍵、亮度鍵等），直接呼叫目標模組介面，不經過 SM。

* `input_events -> Signal -> SM -> 對話流程`
* `adjustments -> 直接呼叫 core / adaptor -> 不影響 SM`

GPIO 分流常見規 §5.4。

### 2.6 perception/ —— 感知層

職責與契約：把物理訊號翻譯成內部可用資料。每個 module 自知輸入來源。契約 `Perception` 提供 `perceive() -> PerceptionResult`。

**實作**

| 實作 | 輸入 | 輸出 |
| :--- | :--- | :--- |
| `perception/listen/` | core/audio 麥克風 | 文字 ( ASR ) |
| `perception/read/` | 外部訊息 payload | 文字 |
| `perception/look/` | core/camera | 視覺結果 |

**平行執行**

* 一個 turn 內可平行啟動多個 module
* 每個 module 有獨立 timeout
* Timeout 與部分失敗都不算錯誤，是資訊：`PerceptionResult.status` 為 `{ok, timeout, error}`，一併送入 reasoner。`error` 表示 module 內部依 P5 降級後仍無可用結果、但 module 仍存活；worker crash 屬 exception 層走 `ErrorOccurred` (§6.6)
* SM 等所有 module 完成或 timeout -> 收齊送入 THINK

**組合決策權**

* 第一 turn：SM 依 wake source 決定（反射式起首，映射表見 §4.4）
* 後續 turn：reasoner 決定（決策式延續，見 §2.7 `next_perceptions`）

`read` perception 的輸入路徑：`read` 是外部訊息的被動消費者，運作機制見 §5.1。其他 perception（ `listen` / `look` ）的輸入是時間點觸發的裝置讀取，語意單純，直接向 `core` 借用資源即可，不需分流機制。

### 2.7 cognition/ —— 認知層

**分工**

* SM：反射與時序協調（狀態轉移、事件路由、in-flight worker 協調）
* Reasoner：認知與決策（理解、推論、選擇 action、決定下一 turn 的 perception 組合）

> 比喻備忘：SM 如小腦——不做認知，負責反射與時序；Reasoner 如大腦——負責理解、推論與決策。命名與目錄採認知層術語（ `cognition/` ），生物比喻僅為直覺輔助。

**Reasoner 能力**

* 接收本 turn 所有 perception 結果（含 `status ∈ {ok, timeout, error}` ）
* 接收本 turn 起始時的 pending message metadata（僅 count 或 id 清單，不含 payload；由 SM 於 THINK Entry 傳入，見 §4.6 / §5.1）——供 reasoner 在決定 `next_perceptions` 時判斷是否加入 `read`
* 組 prompt、呼叫 LLM、正規化輸出為 `LLMResponse`
* 決定本 turn action 類型與內容
* 決定下一 turn 的 perception 組合（若 session 繼續）
* 一次 turn 只推論一次、只產出一個 `LLMResponse`
* 依 P5，LLM engine 部分失敗（timeout、解析錯誤、拒答）時應內部降級產出合理 `LLMResponse`（例：apology speak + 繼續 listen），優先讓 session 延續

**Pending message metadata 的邊界**：reasoner 可觀察但不可解讀 pending metadata——metadata 為 payload-free（僅 id 或 count），reasoner 藉此決定 `next_perceptions` 是否含 `read`；實際訊息內容由下一 turn 的 read perception 讀取。具體 metadata 形式（count vs id list、傳入通道）屬 `implement.md` 。

**Capability 查詢邊界**：reasoner 可透過 `capability_of(kind)`（§6.8 B）查詢與其產出契約一致粒度的能力狀態——合法 kind = perception kind（ `listen` / `read` / `look` ）∪ action kind（ `speak` / `tool` ）。reasoner 不查 core 資源（ `audio` / `display` / `camera` / `gpio` ）、adaptor、input source——底層依賴鏈屬 Resource Manager 職責，reasoner 不感知「 `capability_of("listen")=false` 是因為 audio null、還是 listen 自身 start 失敗、還是 config 標 optional 而未載入」（Null Object Pattern 的完整落實，見 §6.8）。

**LLMResponse 契約**

* `action_kind` ∈ { speak, tool, rest }
* `action_payload` ：依 `kind` 決定內容（schema 屬 `implement.md`）
* `next_perceptions` ：下一 turn 的 perception 組合（ rest 時忽略 ）

**`next_perceptions` 的邊界**

* Reasoner 只能從架構已註冊的 perception capability 中選擇（目前為 `listen` / `read` / `look` ）
* 只是 kind 清單，不攜帶輸入脈絡；每個 perception module 自知輸入來源
* SM 於 THINK Exit 的處理順序（見 §4.6）：
    i. 剔除非註冊 kind：含未註冊 kind 者 log warning + 忽略該 kind（不因單一壞 kind 判整個 `Fact` 違約）
    ii. 非空要求：`action_kind ∈ {speak, tool}` 時，剔除後的 `next_perceptions` 必須為非空清單。若 reasoner 判定 session 應結束，應改產 `action_kind=rest` 而非空清單
    iii. 空清單即違約：`action_kind ∈ {speak, tool}` 而剔除後為空（reasoner 原本即給空清單，或給的 kind 全未註冊）-> 視為 reasoner 契約違反，SM 走 §3.2「SM 自檢」ERROR 路徑（非 process 崩）
* 剔除發生於 THINK Exit 驗證通過後、PERCEPTION Entry 平行啟動前；SM 以剔除後清單啟動 worker

### 2.8 action/ —— 行動層

契約：`Action Protocol` 提供 `execute(request) -> result`。所有 action 皆以 `ActionCompleted(kind, status, result)` 回報，`status ∈ {ok, error}`。依 P5，worker 應內部降級優先產出合理 fact；`status=error` 表示 worker 存活但主動作無可用結果（例：TTS 引擎回饋、tool 派發器回失敗代碼）。Worker crash 屬 exception 層走 `ErrorOccurred` (§6.6)。

**種類**

| 種類 | 職責 |
| :--- | :--- |
| `speak/` | TTS 合成 + 播放 |
| `tool/` | 命令式派發（開燈、發指令），fire-and-forget |
| `rest/` | 產生使用者可感知的收尾（例：告別語、關螢幕、滅燈） |

**Fire-and-forget 語意（tool）**：派發完成即 `ActionCompleted`，不等待結果。真正的執行結果由外部通道以獨立事件回到系統，屬下一次 wake 或下一 turn 的 input。

> 註：query（查詢式派發，例：雲端查詢／雲端 LLM）為重要但尚未定義的第四類 action，見 §8。

**Rest 的意義與邊界**：Reasoner 判定 session 該結束時產出 `LLMResponse(action_kind=rest)`。`rest` 是可選的使用者可感知收尾，不擁有 session 或資源生命週期。責任分工：

* SM：session / turn 狀態轉移的唯一擁有者；收到 `ActionCompleted(kind=rest)` 後結束 session、對剩餘 in-flight 收斂、釋放追蹤欄位、回 `IDLE`
* action/rest：純執行 UX 收尾，跑完即回報 `ActionCompleted`；不呼叫 SM、不管其他 worker

**統一性優勢**：所有 turn 一律以 `ActionCompleted` 收尾，消除「`LLMResponse` 無 action -> SM 直接回 `IDLE`」的特例分支。

### 2.9 adaptor/ —— 對外通道

定位：對外通道，本機 HW 不屬此層（P3）。損壞不影響主流程。

範圍：`adaptor/mqtt/` 雙向 MQTT（接收外部觸發、對外廣播狀態）。外部訊息驗證分工見 §5.1。

本機具現化 `Display` 三角色：以 `OLED` 為本機主要表達通道；三角色（Presenter / StatusBar / 全螢幕請求者）皆屬應用層，見 §5.3。

---

## 3. 跨模組互動模型

### 3.1 控制流 vs 事件流分離

* 控制流走方法呼叫：SM 認識 worker 外層契約（Protocol，不知內部實作），直接呼叫 worker 方法啟動工作、持有 task handle（用於強制 cancel）。Worker 之間互不相識，只認 SM
* 事件流承載觀察與意圖：Event Bus 不承載命令

In-flight worker 概念與 handle 生命週期見 §6.3；三級 cancel 見 §6.4。

SM 持有的 task handle 是 worker 外殼 coroutine；若 worker 內部持有 native thread 或 child process，由 worker 自己管理，狀態不進 SM 追蹤、不進 Event Bus。

### 3.2 事件三類與貫穿性契約

| 類別 | 命名 | 事件 | 發布者 | 訂閱者 |
| :--- | :--- | :--- | :--- | :--- |
| **Worker Facts** | 過去式 | `PerceptionResult` / `LLMResponse` / `ActionCompleted` / `ErrorOccurred` | worker / HAL / bus 兜底（皆 non-SM） | SM + observer |
| **State Broadcast** | 過去式 | `StateChanged` | SM 唯一 | observer（SM 不訂閱自己） |
| **Signals** | 意圖語意 | `ButtonPressed` / `ExternalMessageArrived` / `WakeWordDetected` /<br>`InterruptRequested` / `ShutdownRequested` | `input_events` / 系統模組 | SM 唯一 |

observer = adaptor / log / metrics

**貫穿性契約**

* SM publish 集合 = `{StateChanged}` —— SM 對外只廣播狀態
* SM 訂閱集合 = Worker Facts ∪ Signals
* SM 從不 publish `ErrorOccurred` —— SM 遇 unrecoverable exception 時讓 process 崩、由 systemd 接手
* ERROR 進入的兩條因果鏈（SM 皆不 publish `ErrorOccurred` ）：
    * 外因：`ErrorOccurred` (non-SM) -> SM 讀到 -> `StateChanged(->ERROR)` ；observer 依時序推得原因
    * SM 自檢 Worker Fact 契約違反：SM 於 guard / 狀態 Exit 判定送達的 Worker Fact 內容違約（不合 schema 的 `LLMResponse` 、剔除非註冊 kind 後仍為空的 `next_perceptions` ）-> SM 直接 transition 到 ERROR，不先 publish `ErrorOccurred` 。此路徑無前導事件， `StateChanged(->ERROR)` 即為權威信號。兩條路徑於 ERROR Entry 皆走 §6.5 error 收斂，且皆不升級為 process 崩（Level 3 僅保留給 §6.4 收斂失敗與 §3.4 bus 兜底失敗）

### 3.3 事件清單

**Worker Facts**

* `PerceptionResult(kind, status, text, extra)` —— `status ∈ {ok, timeout, error}`
* `LLMResponse(action_kind, action_payload, next_perceptions)` —— `action_kind ∈ {speak, tool, rest}`
* `ActionCompleted(kind, status, result)` —— `status ∈ {ok, error}`
* `ErrorOccurred(where, error)` —— 無 severity 欄位；SM 對所有 `ErrorOccurred` 統一反應（進 ERROR）

**State Broadcast**

* `StateChanged(old, new)`

**Signals**

* `ButtonPressed(button_id, duration_ms)`
* `ExternalMessageArrived(channel, arrived_at, message_id)` — 僅 metadata, payload 由 external_message 持有 ; `message_id` 為 opaque 識別符, 由 external_message 產生、與 buffer 內單則訊息 1:1 對應 ; SM 只轉發不解讀 ; 雙重角色見 §5.1
* `WakeWordDetected(phrase, confidence)`
* `InterruptRequested()`
* `ShutdownRequested()`

**Schema 與版本化原則**

* 事件 dataclass 具體欄位型別、驗證規則屬 implement.md ; 本文件僅列欄位名與語意約束
* 內部事件無版本化需求：單 process、direct-call、一起 build 一起部署, 加欄位即改 code
* 跨 process / 跨機器 wire format 才需要版本化：屬 docs/protocol.md ( 例：wake daemon IPC、對外 MQTT topic schema )
* `LLMResponse.action_payload` schema 由 implement.md 依 `action_kind` 分別定義 ; SM 於 THINK Exit 驗證 ( §4.6 ) ; 此文件不列舉具體欄位以避免綁死 tool 種類擴展性。三種 kind 的驗證邊界：
  * `speak` : payload 至少含可播放的文本欄位 ( 具體欄位名屬 implement.md )
  * `tool` : Registry-driven — SM 驗證「tool 名稱存在於 tool registry」即可 ( open schema ) ; 每個 registered tool 自帶 payload schema 由 tool 執行時自驗, SM 不列舉支援 tool 的欄位。依 P2「契約以本 agent 使用情境為依據」, 避免寫死 schema 綁架 tool 種類擴展
  * `rest` : payload 允許 empty ( 表意「session 結束、無使用者可感知動作」, 符合 §2.8「rest 為可選的 UX 收尾」)
* 外部訊息驗證位置：adaptor 內驗證協定格式、驗證失敗於 adaptor 丟棄並 log warning ; 通過驗證後由 input_events/external_message 產出符合 read perception 契約的 payload

### 3.4 Event Bus 執行模型

* Direct-call : `publish()` 同步呼叫所有 subscribers ; 無 Queue、無背景 dispatch loop
* Handler 異常隔離 : bus 用 try/except 隔離每個 handler ; 抓到 exception 一律 publish `ErrorOccurred(where="bus.dispatch.<handler>", ...)` 兜底, 不偵測是否重複 ( 無法可靠偵測、也沒必要 )。若 handler 已自報 ErrorOccurred, SM 在 ERROR 狀態對後續 ErrorOccurred 自然吸收 ( 狀態機一般規則 ), 重複無害
* 兜底規則不迴避、fatal 交回頂層 : bus 派送 `ErrorOccurred` 時, 若某 handler 拋 exception, 不再為此 exception 二次 publish `ErrorOccurred` — log fatal 後將 exception 交回頂層 ( re-raise 至 event loop 的 unhandled exception handler, 或呼叫明確的 fatal shutdown hook ) ; main.py 收到即結束 process, 交由 systemd 重啟 ( §6.4 Level 3 )。理由：`ErrorOccurred` 已是系統最後兜底信號 ; 再失敗代表 observer 層自身崩潰, direct-call 模型下 `continue` 遞迴 publish 會無限展開 ; 僅 log 不足以構成收斂行為
* 無 subscriber -> log warning ( 不區分「未知型別」與「無訂閱」)
* 外部 raw 協定訊息由 adaptor 過濾、不進 bus ; 內部事件 ( 含 `ExternalMessageArrived` Signal ) 走 bus

### 3.5 SM 執行模型（Inbox）

* SM 的 subscriber 是薄殼：只將事件放進 SM 內部 inbox ( 同步 enqueue ) 後立即返回
* SM 有常駐 dispatch loop, 唯一負責從 inbox 取事件、跑狀態轉移、呼叫 worker

**保證性質**

* SM 狀態轉移永遠單執行、無交錯
* 巢狀 publish 深度固定為 1 ( worker 回報事件走 inbox , 不重入 SM handler )

### 3.6 併發限制與 guard 判定順序

**併發性質**

* 單 event loop : handler 內 `await` 會讓出控制權，其他事件可穿插
* 多 producer 並行 publish 時不保證全域順序
* 非法時序 -> log warning + 忽略，不拋錯

Guard 三步判定：SM dispatch loop 從 inbox 取出事件後，依序執行以下三步；任一步失敗即 log warning + drop，不進狀態轉移。

| Step | 檢查 | 適用範圍 | 失敗處置 |
| :--- | :--- | :--- | :--- |
| 1. Kind 白名單 | 事件 `kind` ∈ ( 跨狀態三事件 U 當前狀態額外接受事件 )，見 §4.5 | 所有事件 | `log warning + drop` |
| 2. ID 過期驗證 | 事件 `session_id` / `turn_id` 匹配 SM 當前追蹤 | 僅 `Worker Facts` ; `Signals` 與 `ErrorOccurred` 天生無 ID，跳過 | `log warning + drop` |
| 3. 交狀態卡處理 | 依 §4.5 / §4.6 執行狀態轉移、`Entry` / `Exit`、或調度指令 ( 如 §5.1 `external_message pending` ) | 通過前兩步者 | — |

**設計要點**

* `ErrorOccurred` 不參與 ID 驗證：事件無 `session_id` 欄位，且過期 `error` 仍是 `error`，`drop` 反而可能漏收斂機會 ; 只要 `kind` 檢查通過就進 `ERROR`
* `Signals` 無 ID 天生跳過 `Step 2` ; `ExternalMessageArrived` 於非 `IDLE` 通過 `Step 1` 後由 `Step 3` 依 §5.1 發調度指令
* 收斂中 `worker` race 送出的 `Facts` : 由「被 `cancel` 者不 publish `Facts`」規範源頭 ( §6.3 ) ; `guard` 則由 `Step 2` ID 驗證兜底 ( 新 `session` 的 ID 已重置，過期 `Facts` 自然被 `drop` )
* `In-flight` 集合成員身份不納入 `guard` : 屬 `implement.md` 層雙保險

### 3.7 追蹤粒度

* 每個 `session` 分配 `session_id`
* 每個 `turn` 分配 `turn_id` ( `session` 內遞增 )
* SM 下發呼叫與 `worker` 回報事件皆帶 `(kind, session_id, turn_id, correlation_id)`
* SM 拒絕不屬於當前 `session/turn` 的事件 ( `log` + 忽略 )
* `Wake` 類事件、`Shutdown`、`Interrupt` 是 `session` 外事件，不需 ID

---

## 4. 對話狀態機

### 4.1 Session / Turn 雙層

* `Session` : 從一次 `wake` 到回 `IDLE` 的完整服務會話
* `Turn` : `Session` 內一次「`perception -> think -> action`」循環
* 一個 `session` 可包含多個 `turn`

### 4.2 狀態集合

| 狀態 | 意義 |
| :--- | :--- |
| `IDLE` | 等待外部觸發 |
| `WAKE` | 已被喚醒，發出反饋、準備啟動 `perception` |
| `PERCEPTION` | 一或多個 `perception module` 平行執行中 |
| `THINK` | `Reasoner` 推論中 |
| `ACTION` | 執行 `action` ( `speak / tool / rest` ) |
| `ERROR` | 錯誤處理中，短暫停留後回 `IDLE` |

### 4.3 醒來反饋時序

`IDLE` -> `WAKE` -> 等 `wake_ack_seconds` ( config ) -> `PERCEPTION`。

進 `WAKE` 時 SM 發 `StateChanged`，`StatusBar` 狀態 `slot` 更新顯示 ( 見 §5.3 ) ; 反饋亦可含 `earcon` 等其他通道。`wake_ack_seconds` 是刻意的 `UX buffer`，讓使用者感知系統已醒來、開始收音才穩定。

### 4.4 Wake source -> 首 turn perception 映射

SM 內建的 wake source -> perception 組合對應關係：

| Wake source | Perception 組合 | 理由 |
| :--- | :--- | :--- |
| `ButtonPressed` | `[listen]` | 使用者在裝置前按鈕，預期後續語音對話 |
| `WakeWordDetected` | `[listen]` | 使用者剛講話喚醒，接續錄音承接語句 |
| `ExternalMessageArrived` | `[read]` | 訊息 `payload` 已於外部通道到達，由 `read` 消費 ( §5.1 ) |

性質：SM 內建、不進 `config` 寫死 ( 此映射屬架構層反射行為，形式與內容一同確立；`default_perceptions` 之於錯誤路徑才是產品層調校項，見 §4.8 )。若未來出現產品層調校需求 ( 例：某產品情境希望 `button` 起首同時開 `look` )，再考慮升級為 `config-driven`。

同時到達：不支援複合觸發。多個 `wake` Signal 若近乎同時到達 SM `inbox`，先到者觸發 `IDLE` -> `WAKE` 並確定 `wake source`；後到者依 §4.5「`wake` 類 Signal 雙態行為」處理。

### 4.5 狀態轉移表

**共通前置**：所有 `Entry` 隱含 SM publish `StateChanged(old, new)`。

**跨狀態接受的三個事件**：`ShutdownRequested` / `ErrorOccurred` / `InterruptRequested` 在所有狀態 ( 終止流程除外 ) 皆合法接受，反應見 §4.7。非白名單事件一律 `log warning` + 忽略。

**wake 類 Signal 的雙態行為**

* `ButtonPressed` / `WakeWordDetected` : 僅 `IDLE` 接受並觸發狀態轉移；其餘狀態拒絕 ( 過期 `wake` Signal )
* `ExternalMessageArrived` : `IDLE` 接受並觸發狀態轉移；其餘狀態亦接受但不觸發狀態轉移，SM 依 §5.1 對 `external_message` 發調度指令

**主流流程狀態轉移**

| 當前狀態 | 觸發事件 / 條件 | 目的狀態 | 備註 |
| :--- | :--- | :--- | :--- |
| IDLE | `ButtonPressed` / `WakeWordDetected` / `ExternalMessageArrived` | WAKE | 記錄 wake source |
| WAKE | `wake_ack_seconds` timer 到期 | PERCEPTION | — |
| PERCEPTION | 所有 perception 完成或 timeout | THINK | — |
| THINK | `LLMResponse` 產出且通過契約驗證 | ACTION | 驗證項見 §4.6 THINK Exit |
| THINK | `LLMResponse` 產出但驗證不通過（schema 不合、payload 不合，或剔除未註冊 kind 後 `next_perceptions` 空） | ERROR | 視為 reasoner bug（P5 降級亦失敗）；走 §3.2「SM 自檢」ERROR 路徑，SM 不 publish `ErrorOccurred`、不升級為 process 崩 |
| ACTION | `ActionCompleted(kind∈{speak,tool}, status=ok)` | PERCEPTION | 依 reasoner `next_perceptions` |
| ACTION | `ActionCompleted(kind∈{speak,tool}, status=error)` | PERCEPTION | 依 SM `default_perceptions` (§4.8) |
| ACTION | `ActionCompleted(kind=rest, status=any)` | IDLE ( 正常 ) / ERROR ( 有 recovery 需要 ) / (process 崩) ( Level 2 失敗 ) | 見 §4.6 ACTION Exit；Level 1 正常完成 → IDLE；Level 2 破壞 backend → 進 ERROR 等 recovery barrier；Level 2 失敗 → Level 3 (§6.5) |
| ERROR | in-flight 集合空 且 RM recovery barrier 已清除 | IDLE | 見 §6.5 ERROR Exit 條件 |

### 4.6 影響資源與資料 ownership 的 entry/exit 動作

僅列會影響資源分配、資料 ownership 或跨模組契約的動作；純 defensive check（如「Entry 時斷言 in-flight 集合為空」）不列。所有 Exit 均隱含「確認相關 in-flight handle 已釋放」——此為 defensive check，正確性仰賴 worker 契約（見 §6.3「終態 Fact 發布時序」）。

**WAKE Entry**

* 分配新 `session_id`
* 記錄本 session 的 wake source（供 §4.4 首 turn 映射）
* 啟動 `wake_ack_seconds` timer
* 若 wake source 為 `ExternalMessageArrived` → 通知 `external_message` ：訊息屬本 session（§5.1）

**WAKE Exit**

* 停止 `wake_ack_seconds` timer（正常路徑 timer 觸發即進 PERCEPTION；若因 Interrupt / Shutdown / Error 提前離開，需顯式停 timer 避免延遲觸發污染下一 session）

**PERCEPTION Entry**

* 分配新 `turn_id`（session 內遞增，首 turn = 1）
* 決定本 turn perception 組合：
    * 首 turn：依記錄的 wake source 反射式選擇（§4.4）
    * 後續 turn：依前一 `LLMResponse.next_perceptions` ；若前一 turn 為 `ActionCompleted(kind∈{speak,tool}, status=error)` ，改用 `default_perceptions`（§4.8）
* 對每個選定的 perception kind 呼叫 worker、加入 in-flight 集合
* 若組合含 `read` → 通知 `external_message` 啟動 `read` 消費（§5.1）

**THINK Entry**

* 呼叫 reasoner，加入 in-flight 集合
* 傳入 reasoner 本 turn 的 pending message metadata（僅 id 清單或 count，不含 payload；來源見 §5.1）——供 reasoner 決定 `next_perceptions` 是否含 `read`

**THINK Exit**

* 驗證 `LLMResponse` 是否合契約，依序：
    i. `action_kind` ∈ {speak, tool, rest} ；否則違約 → ERROR
    ii. `action_payload` 符合對應 kind 的 schema（§3.3）；否則違約 → ERROR
    iii. 剔除 `next_perceptions` 中未註冊 kind（log warning + 忽略，見 §2.7）
    iv. `action_kind` ∈ {speak, tool} 時，剔除後 `next_perceptions` 須非空；為空 → 違約 → ERROR
* 上述任一違約走 §3.2「SM 自檢」ERROR 路徑：SM 直接 transition 到 ERROR、不 publish `ErrorOccurred`、不升級為 process 崩；ERROR Entry 執行 §6.5 error 收斂。通過驗證者以剔除後的 `next_perceptions` 進 ACTION

**ACTION Entry**

* 依 `LLMResponse.action_kind` 啟動對應 action worker，加入 in-flight 集合

**ACTION Exit（`kind=rest`）**

* 對本 session 剩餘 in-flight 執行 §6.5 error 收斂機制
* 清 SM 內部 session 追蹤欄位（`session_id`、`turn_id`、`wake source` 記錄、上一輪 `next_perceptions` 記錄等）
* 通知 `external_message` `flush-to-wake`（§5.1）——buffer 內未消化訊息重新發 `ExternalMessageArrived` ，於 IDLE 自然開新 session

**ERROR Entry**

* 對 in-flight 集合執行 §6.5 error 收斂機制

**ERROR Exit**

* 清 SM 內部 session 追蹤欄位
* 通知 `external_message` `discard` buffer（§5.1）

### 4.7 跨狀態收斂觸發

以下三個事件在任意狀態（終止流程除外）皆合法接受；收斂上限、Level 2 失敗後行為、external message buffer 處置統一見 §6.5。

| 事件 | SM 反應 | 目的狀態 |
| --- | --- | --- |
| `InterruptRequested` | 觸發收斂（§6.5）；收斂正常完成後清 session 追蹤欄位、隱性收斂不進顯性中間狀態 → IDLE；Level 2 破壞 backend → 進 ERROR 等 recovery barrier；Level 2 失敗 → Level 3 | IDLE ( 正常 ) / ERROR ( 有 recovery 需要 ) / (process 崩) ( Level 2 失敗 ) |
| `ErrorOccurred` | 進 ERROR（收斂動作於 ERROR Entry 執行） | ERROR |
| `ShutdownRequested` / `SIGTERM` / `SIGINT` | SM 進 shutdown 模式（拒新 wake 類 Signal）→ 收斂（§6.5）→ in-flight 集合空後停 dispatch loop → `main.py` 依 Resource Manager 反向呼叫各模組 `stop()`（§6.2） | (終止) |

**若已在 ERROR 狀態**

* `ErrorOccurred` 疊加：自然吸收（§3.4 handler 異常隔離規則）
* `InterruptRequested` ：忽略（已在收斂中）
* `ShutdownRequested` ：升級為 shutdown 收斂

ERROR 狀態特殊性： `ExternalMessageArrived` 於 ERROR 狀態亦拒絕 ( 無額外接受事件 ) —— ERROR 為短暫收斂狀態，且 Exit 時將對 `external_message` 發 `discard` 指令，此期間新訊息無留存意義。

### 4.8 `next_perceptions` 與 `default_perceptions`

* `next_perceptions` ： reasoner 於 `LLMResponse` 產出 ( 見 §2.7 ) ， SM 用於 PERCEPTION Entry 決定下一 turn 的 perception 組合
* `default_perceptions` ： SM 內建、 `config-driven` 的預設 perception 組合 ( 預設值 `[listen]` ) 。僅在 `ActionCompleted(kind∈{speak,tool}, status=error)` 時使用，用以取代 reasoner 的 `next_perceptions` ，避免下一 turn 卡在等永遠不到的訊息 ( 例： tool 派發失敗但 reasoner 假定會收到 ACK ) 。此為 SM 唯一依 fact `status` 分歧的決策點

---

## 5. 特殊流程與資源仲裁

本章收錄需要跨層協調的資源與資料流。

### 5.1 外部訊息 buffer 與 read perception

外部 MQTT / UART 等訊息進入系統的正式路徑：

1. **adaptor/mqtt ( 或其他對外通道 )**：處理外部協定、驗證訊息格式、翻譯為內部可用 payload； `adaptor/mqtt` 只做協定翻譯、不進 Bus；驗證失敗於 adaptor 丟棄並 log warning
2. **input_events/external_message**：
    * 接收 adaptor 交付的訊息、產出符合 read perception 契約的 payload
    * 持有訊息 buffer ——訊息從到達至被消化 / 丟棄的全生命週期擁有者
    * `message_id` 唯一發生源——每則訊息入 buffer 時分配 opaque `message_id` ，作為對外指涉單則訊息的識別符
    * 對 SM 發 `ExternalMessageArrived` Signal ( 僅 metadata 、含 `message_id` )
    * 接收 SM 的調度指令控制 buffer 生命週期
    * 對 read perception 提供消費介面
3. **SM**：純調度——依 Signal 與當下狀態發指令，不接觸訊息 payload 、不持有訊息 buffer
4. **read perception**：被動消費者，執行時向 external_message 索取當前該處理的訊息；不 subscribe `ExternalMessageArrived` 、不持有訊息狀態；read 收到的訊息集合由 external_message 依 SM 指令決定，read 對此無感

**SM 依狀態的調度指令（ `ExternalMessageArrived` 既是 wake source 也是 perception input）：**

* **IDLE 收到訊息**：SM 開新 session、通知 `external_message` 訊息屬本 session
* **Session 中、當前 turn 有 read**：SM 啟動 `read` ； `read` 執行時直接向 `external_message` 消費
* **Session 中、其他情況**：SM 通知 `external_message` 進 `pending` 模式 ( 訊息續存於 buffer )
* **Session 結束走 rest（正常收斂）**：SM 通知 `external_message` `flush-to-wake` ——buffer 內未消化訊息重新發 `ExternalMessageArrived` Signal，SM 於 IDLE 收到後依第一條規則自然開新 session
* **Session 走 ERROR / Interrupt / Shutdown（異常收斂）**：SM 通知 `external_message` `discard` 、buffer 清空

**設計原則**

* 每則訊息只走一條路徑 ( `ExternalMessageArrived` Signal → SM 決策 ) ；pending 升級為 wake 是同機制，非特殊路徑
* SM 不接觸 payload、不持有 buffer；訊息生命週期由 external_message 完全擁有
* 調度指令以 `message_id` 指涉單則訊息 ( 來自 Signal 攜帶的 opaque id ) ；批次指令 ( 如 flush / discard ) 以「當前 buffer 全體」或指定 id 集合為對象。SM 只轉發 id、不解讀
* **Pending metadata 對 reasoner 可見 ( payload-free )**：SM 於 THINK Entry 將當前 buffer 內 pending 訊息 of id 清單或 count 傳入 reasoner ( 見 §2.7 / §4.6 ) ——僅 metadata、不含 payload，維持 SM / reasoner 皆不接觸 payload 的邊界。Reasoner 依此判斷是否於下一 turn 加入 `read` ；實際訊息內容由該 read perception 讀取

具體指令 API、buffer 資料結構、read 消費介面屬實作細節，見 `implement.md` 。

### 5.2 麥克風獨佔切換

`voice_wake` 與 `perception/listen` 不同時錄音；由 SM 協調誰在使用 ( 見 §4.3 醒來反饋時序 ) 。使用情境為「先喚醒、給反饋、才對話」，不做同時錄音。

### 5.3 Display 三角角色與仲裁層

Snowboard 以 OLED 為本機主要表達通道。三角角色皆屬應用層 ( 非 core、非 adaptor ) ，與 HAL ( `core/display` ) 之間存在仲裁層。

**Display 三角角色**

| 角色 | 職責 | 顯示位置 | 觸發來源 | 生命週期 |
| --- | --- | --- | --- | --- |
| `Presenter` | Worker 主動借用、顯示 domain hint ( 音量、信心度、部分結果、字幕等 ) | main area | Worker push hint | 綁 worker |
| `StatusBar` | 系統常駐資訊區、內部多 slot 聚合 ( 時間 / 對話狀態 / 音量 / 連線 / 能力異動 / 錯誤提示 ... ) | 頂部固定區 | 各 slot 自訂 | 常駐 |
| 全螢幕請求者 | 特殊時機的全螢幕顯示 ( 開機 / 結束 / 高光時刻 ... ) | 蓋掉整個螢幕 ( 含 `StatusBar` ) | 任何模組主動呼叫 | 呼叫者掌控 |

`StatusBar` 內部 `slot`：`StatusBar` 是聚合器，內部管理多個 `slot`。`Slot` 種類、`owner`、資料來源屬 UX 設計，`slot` 列表屬 `implement.md`。原 `StateIndicator` ( 訂閱 `stateChanged` 顯示對話狀態 ) 在此架構下降格為 `StatusBar` 的狀態 `slot`，不再是獨立模組。

意圖 vs 執行分離：三角色皆為意圖產生者，不直接寫 `core/display`。

* `HAL` 層 ( `core/display` )：只提供低階原語，不知有幾個 client、不管誰蓋誰
* 仲裁層：管區域分配 ( `status_bar / main / fullscreen` ) 與獨佔狀態
* 應用層 ( 三角色 )：只送意圖，互不知情

仲裁層對外四動作

| 動作 | 呼叫者 | 效果 |
| --- | --- | --- |
| `write_status_slot(slot_id, hint)` | `StatusBar` 內部 `slot` owner | 更新指定 `slot` 內容 |
| `write_main(hint)` | `Presenter` | 更新 `main area` 內容 |
| `request_fullscreen(hint)` | 任何模組 | 無人佔用 -> 給、返回 `true`；已被佔用 -> 拒絕、返回 `false` |
| `release_fullscreen()` | 佔用者 | 釋放全螢幕、回到 `status_bar + main` 常規模式 |

仲裁規則

* `Status_bar` 與 `main area` 無競爭：各自專屬區域
* `Status_bar` 常駐不隱藏：無「請隱藏」動作；除非全螢幕蓋掉，否則永遠顯示
* `Fullscreen` 為互斥獨佔：一次一個佔用者；呼叫者必須 `release` 後其他人才能取得
* 無先到先得排隊：拒絕即拒絕；呼叫者自決是否重試或降級
* 系統時序保證獨佔不易撞：對話流程單線程使實際競爭罕見

仲裁層的建立與注入：仲裁層 instance 由 Resource Manager 於啟動階段建立、注入給三角色（同 §6.1 依賴注入責任）。模組落點：掛於 `core/display/` 之下，作 HAL 上層薄殼；`core/display/` 底層 HAL 仍為只提供低階原語的驅動封裝，仲裁層獨立於底層 HAL、位於同一目錄。若未來 LED 或其他表達通道亦納入表達架構，且與 Display 需共用同一種仲裁機制，再考慮搬移至獨立模組（見 §8.1 LED 顯示機制）。

Protocol 方法簽名細節屬 `implement.md`。`Adjuster / Overlay` 短暫覆蓋、LED 顯示機制尚未納入，見 §8。

### 5.4 GPIO 分流

`core/gpio` 依 `pin` 註冊映射把事件送到唯一訂閱者，一 `pin` 一訂閱者——不同物理按鈕依用途註冊給 `input_events` 或 `adjustments`。單一訂閱者內部可依按法（短按 / 長按 / 雙擊）產出不同輸出：

* 例：對話按鈕 `pin` 註冊給 `input_events/button`，短按 -> `ButtonPressed` Signal、長按 -> `InterruptRequested` Signal
* 例：音量鍵 `pin` 註冊給 `adjustments/volume`，短按 / 長按皆直控 `core/audio`

— `pin` 多訂閱者屬進階分流場景，尚未定案（見 §8）。

---

## 6. 生命週期、失敗與收斂

### 6.1 Resource Manager 角色

系統定義 **Resource Manager** 角色，承擔以下職責：

1. **建立**：依 `config` 建立所需 `core` / `worker` instance、注入依賴
2. **啟動**：按依賴順序呼叫 `start()`
3. **啟動失敗處理**：中止啟動並清理已啟動者，或依 §6.8 A 注入 Null Object 續行；並依 §6.8 B 更新 `capability_map`
4. **Shutdown 收斂**：依序呼叫 `stop()`；in-flight worker 收斂由 SM 執行（§6.5）
5. **依賴一致性**：保證使用者取得的資源已就緒
6. **能力查詢**：提供 `capability_of(kind)` 供其他模組主動查詢（見 §6.8 B）
7. **Recovery rebuild** ：Level 2 `force_abort()` 破壞 `backend`（終止 child process）後，RM 在背景重建並 `re-start`；維護 recovery barrier，barrier 清除前 SM 維持 ERROR（見 §6.4 / §6.5）

Lifecycle 契約：所有 `core` 與 `worker` 模組實作統一介面（`start()` / `stop()` 或等價），供 Resource Manager 呼叫。契約細節屬實作，見 `implement.md`。

### 6.2 啟動與停機順序

啟動順序：`config` → `logger` → `event_bus` → `state_manager` → 硬體 `core` → `workers / adaptor`。

Shutdown 順序：由 `ShutdownRequested` Signal 或 `SIGTERM / SIGINT` 觸發。

1. SM 進 `shutdown` 模式（拒絕 `wake` 類 Signal，見 §4.7）
2. SM 對 `in-flight` 執行 §6.5 shutdown 收斂
3. `In-flight` 集合空後停 SM dispatch loop
4. `main.py` 依 Resource Manager 反向呼叫各模組 `stop()`

各步驟具備獨立 `timeout`（config-driven，值屬 `implement.md`）。Level 3（`process` 崩、`systemd` 重啟）為終極兜底路徑，見 §6.4。

### 6.3 In-flight worker 與 handle 生命週期

**In-flight worker**：SM 呼叫 `worker` 方法啟動後、直到 `task handle` 對應的 `asyncio task` 真正結束（`return / cancelled / raised`），該 `worker` 稱為 `in-flight`。SM 為每個 `session` 追蹤其 `in-flight worker` 集合。

Worker execution container 契約：

* `start() return` => `worker` 及其所有 `internal container`（native thread、child process）均已 `READY`
* `force_abort() return` => 所有 `internal operation` 終止、`descendant process` 確認退出（`waitpid` 或等價）、`HW` 資源釋放
* 無可靠 `native cancel` 的 `blocking backend`（如 `LiteRT-LM Engine`）：必須隔離於 `child process`；`force_abort()` 以「終止並 `waitpid child process`」作為完成證明。若不隔離，Level 2 無法成證明，唯一合法兜底為 Level 3

**In-flight 集合的性質**

* 多元素：`PERCEPTION` 平行啟動多個 `perception worker` 時，`in-flight` 集合含多個 `handle`；「所有 `perception` 完成或 `timeout`」轉移條件 = 該集合中所有 `perception kind handle` 均已釋放
* Empty check 時機：SM dispatch loop 每處理完一個事件後，依當前狀態的觸發條件檢查 `in-flight` 集合。此為原則層規範；具體實作屬 `implement.md`
* 狀態間清空要求：狀態卡的 Exit 隱含「確認相關 `handle` 已從 `in-flight` 集合移除」（§4.6）——這是 defensive check；正常路徑上 `worker` 完成即釋放 `handle`

`Handle` 釋放：`worker task` 真正結束後（無論 `return / cancel / raise`），SM 從 `in-flight` 集合移除該 `handle`。「真正結束」等價於 `asyncio runtime` 對該 `task` 標記完成——SM 藉 `task done callback`（或等價機制）得知，不以 `abort() / force_abort() return` 為準；具體排程機制屬 Ch 4。

終態 Fact 發布時序：`worker` 必須在資源釋放完畢、`task` 即將 `return` 前 `publish` 終態 Fact（ `PerceptionResult / LLMResponse / ActionCompleted` ）。Fact 到達與 `task done` 為兩個排程事件：Fact enqueue 進 `SM inbox` 後，`worker task` 尚未 `return`（外殼 `coroutine` 仍需執行 `publish` 之後、`return` 之前的收尾）。狀態轉移的完成條件為：

> 對應終態 Fact 已收到 AND 對應 `worker task` 已 `done`、`handle` 已從 `in-flight` 集合移除

SM 收到 Fact 而 `task` 尚未 `done` 時，狀態轉移暫緩；待 `task done callback` 將 `completion notice` enqueue 至 `inbox` 後再重做 `empty check`。此為架構語意；具體資料結構（例：`task done callback`、內部 `completion notice` 事件）屬 Ch 4。

### 6.4 Cancel 分級（三級收斂）

SM 對 `worker` 的 `cancel` 分三級（走控制流方法呼叫，不走事件流）：

* **Level 1 合作式**：SM 呼叫 `worker.abort()` 並 `await` 其完成。`abort() return` 代表 `worker` 已完成合作式停止義務（停止內部工作、釋放硬體資源、外殼 `coroutine` 進入結束流程）。SM 隨後依 §6.3「Handle 釋放」規則等待外殼 `task done`、才移除 `handle`。Level 1 對 `native operation` 不強制終止，`worker` 盡力即可
* **Level 2 強制**：Level 1 逾時 -> SM 呼叫 `worker.force_abort()` 並 `await` :
    * **i.** `force_abort()` 在 `timeout` 內 return -> §6.3「Worker execution container 契約」的完成證明成立（所有 `internal operation` 已終止、`descendant process` 已 `waitpid` 退出、`HW` 資源已釋放）；SM 隨後等 `task done`、移除 `handle`
    * **ii.** `force_abort()` 超時 -> 直接進 Level 3。外殼 `task.cancel()` 不作為 Level 2 兜底——外殼 `cancel` 成功僅證明 Python `coroutine` 結束，不能證明 `native thread / child process` 已停止，與 §6.3 完成證明義務衝突

    純 `asyncio worker`（無 `internal thread / child process`）：`force_abort()` 允許實作為等價 `abort()`；完成證明由 `asyncio task` 結束天然提供

* **Level 3 放棄**：Level 2 逾時（ `force_abort()` 未能提供完成證明 ）-> 記錄 `fatal` -> 讓 `process` 崩掉，`systemd` 重啟

Level 2 失敗後一律進 Level 3（四條觸發路徑無一例外）；Level 2 成功但破壞 `backend` 的後續處置與 `external-message buffer` 政策才依觸發者而定，見 §6.5。

Process 重啟為設計上的終極兜底：Level 3 不是意外，而是「合作式與強制手段皆失效」時的正常出口。涵蓋兩條進入路徑：

* Cancel 逾時：Level 2 `force_abort()` 逾時，如上
* Bus 兜底失敗：Event Bus 派送 `ErrorOccurred` 時 `handler` 再度失敗（§3.4）——fatal exception交回頂層、`main.py` 結束 `process`

兩條路徑最終皆由 `systemd` 重啟。系統韌性依賴 Level 1 / 2 處理絕大多數情況，`systemd` 處理其餘。

**Worker 契約**：

* 必須實作合作式 `abort()` 方法；`abort() return` 前應停止內部工作並釋放硬體資源；必須正確 `re-raise` `CancelledError`
* 必須實作 `force_abort()` 方法；`force_abort() return` 前須完成 §6.3「Worker execution container 契約」中的完成證明義務。無可靠 `native cancel` 的 `blocking backend` 必須隔離於 `child process`，否則無法提供完成證明
* 各級 `timeout` 值與 `per-worker-kind` 差異尚未定案（含 `child terminate + waitpid` 預期時間，見 §8）

### 6.5 Session 收斂機制（統一）

以下四種情境皆執行 §6.4 三級 `cancel`。Level 2 failure 一律進 Level 3（四條觸發路徑無一例外）；Level 2 成功但破壞 `backend` 的後續處置，以及 `external-message buffer` 政策，才依 `trigger` 而定：

| 觸發 | 收斂上限 | Level 2 失敗後 | Level 2 成功且破壞 backend | External message buffer |
| --- | --- | --- | --- | --- |
| `ActionCompleted(kind=rest)` | Level 2 | 進 Level 3（`process` 崩） | 降級走 Error 路徑（進 `ERROR`，等 recovery barrier） | `flush-to-wake` (§5.1) |
| `InterruptRequested` | Level 2 | 進 Level 3（`process` 崩） | 降級走 Error 路徑（進 `ERROR`，等 recovery barrier） | `discard` |
| `ErrorOccurred` | Level 2 | 進 Level 3（`error` 已是異常路徑，不再降級） | 維持 `ERROR`，等 recovery barrier | `discard` |
| `ShutdownRequested` | Level 2 | 進 Level 3 | 不 `rebuild`；完成 `termination proof` 後直接進 reverse `stop()`（§6.2） | `discard` |

四條觸發路徑的 Level 2 失敗處置一致（皆進 Level 3）——實務上 Level 1 `abort()` 已能處理絕大多數情況；Level 2 失敗代表系統已無法用合作式或強制手段收斂該 worker，此時 `process` 重啟是唯一乾淨的兜底，無論觸發者是使用者中止還是異常事件。

回 `IDLE` 前的 readiness gate：`Rest / Interrupt / Error` 三條「回 `IDLE`」路徑，只要 Level 2 成功但破壞 `backend`，一律先進 `ERROR`、等 RM recovery barrier 清除後才回 `IDLE`——避免 `backend` 尚未 `READY` 時接受新 `session`。Shutdown 屬終止路徑、不 `rebuild`。

`ERROR` `Exit` 條件：`in-flight` 集合空 且 RM recovery barrier 已清除（若無 recovery 需要，barrier 於進 `ERROR` 時即為清除狀態；若 Level 2 有破壞 `backend`，須等 RM完成 `rebuild`）。recovery 失敗或 timeout 由 RM 觸發 Level 3（§6.8 B：recovery 失敗不改 `capability_map`，直接讓 `process` 崩、`systemd` 重啟）。

### 6.6 錯誤兩層分界

依 P5，錯誤區分為兩層：

| 層 | 觸發 | 事件 | 系統狀態 | SM 反應 |
| --- | --- | --- | --- | --- |
| Fact 層 | Worker 存活、能翻譯的部分失敗 | `PerceptionResult / ActionCompleted` 帶 `status=error` | 一致 | 續 `turn`（`ActionCompleted(status=error)` 改用 `default_perceptions` ；其他不分歧） |
| Exception 層 | 崩潰 / 強制中斷 / unhandled | `ErrorOccurred`（non-SM 發） | 潛在不一致 | 進 `ERROR` 狀態，對在載集合執行 §6.5 收斂；待集合空、RM recovery barrier 清除後回到 `IDLE` |

### 6.7 分層責任

| 層 | 責任 |
| --- | --- |
| HAL ( core ) | 消化 transient error、標記 degraded、拋明確錯誤型別 |
| Worker ( perception / cognition / action ) | 依 P5 內部降級產出可用 fact；無法產出 fact 才 raise；`CancelledError` 正確 re-raise |
| Event Bus | 隔離 handler 異常；抓到即兜底 publish `ErrorOccurred`；派送 `ErrorOccurred` 不遞迴、fatal exception 交回頂層 ( §3.4 ) |
| SM | 進 `ERROR` 時執行 §6.5 收斂；in-flight 集合空且 RM recovery barrier 清除後回 `IDLE`。recovery timer 由 RM 擁有，SM 不自管；recovery 失敗或 timeout 由 RM 觸發 Level 3 |
| `main.py` | 常規 asyncio cleanup；接收 bus 交回的 fatal exception 並結束 process ( §6.4 Level 3 兜底路徑之一 ) |

### 6.8 能力降級：Null Object + Capability Map

兩個機制並用：

#### A. Null Object Pattern

* 適用範圍：需要以契約內無害行為維持下游呼叫鏈的 core 資源（例：`core/audio` / `core/display` / `core/camera` ——下游 worker 直接呼叫其工作方法，null 讓呼叫不 raise、經 P5 降級產出可用 fact）在其目錄下提供 null 實作，與其他實作為平行兄弟
* 例外：純登錄型 HAL（例：`core/gpio` 的 `register_input(pin, callback)`）不需 null 實作——「註冊後永不觸發」等同物理上沒接線的行為，不需獨立類別；register 失敗直接由 RM 記 `capability_of=false`、下游依此不啟動。判定原則見 [implement/ch02a §2a.1 Null Object 適用性表]()
* 啟動時 Resource Manager 嘗試建立 real 實作；start 失敗 → 有 null 者改用 null 實作注入；無 null 者將該 kind capability 設為 false、下游不啟動
* 上層 worker 拿到 core 契約物件，不區分 real 或 null——這是 Null Object Pattern 的核心
* Core 本身不做替換判斷，仍依 §6.7「拋明確錯誤型別」；real → null 的替換決策集中於 Resource Manager

#### B. Capability Map

* Resource Manager 內部維護 `capability_map: dict[kind, bool]`
* 合法 kind 範圍：core 資源（`audio` / `display` / `camera` / `gpio`）U perception kind（`listen` / `read` / `look`）U action kind（`speak` / `tool`）——涵蓋「跨模組決策所需、啟動時決定的靜態能力」
* 啟動時：real 建立成功 → `map[kind]=True`；start 失敗、注入 null → `map[kind]=False` + log warning
* 需要認知狀態的模組主動查詢 `resource_manager.capability_of(kind)`；Resource Manager 不主動通知、不 publish 事件
    * o core 資源 kind：例 Presenter 決定顯示樣式、adaptor 對外廣播能力
    * o perception / action kind：僅 reasoner 查（§2.7 Capability 查詢邊界）；用於決定 `next_perceptions` / `action_kind`

**能力鏈推導原則（worker capability）**

* Worker（perception / action）自身不感知依賴的 real/null 狀態——Null Object Pattern 保證介面契約成立，worker 不寫 `if is_null` 分支
* `capability_of("<worker_kind>")` 由 Resource Manager 依兩條並存路徑推導（任一為 false 即為 false）：
    * o P1 依賴不可用：worker 宣告依賴的 core 資源 `capability_of=false` → 該 worker capability = false
    * o P2 自身 start 失敗：worker 自己 start 失敗，或 config 標 optional 而未載入 → 該 worker capability = false
* 兩條路徑都通過才是 true。此推導集中於 Resource Manager，worker 自身無感

**非 map 模組的查詢慣例**

* Adaptor 連線狀態、InputSource（voice_wake daemon 存活、button 硬體就緒等）屬可能 runtime 變化的能力，不入 `capability_map`（不強塞進「啟動時決定的靜態值」模型）
* 需要時由該模組自帶查詢介面（例：adaptor 的 `is_connected()`、`voice_wake` IPC client 自知 daemon 連線狀態）
* 呼叫者（例：`StatusBar`的連線 slot）直接呼叫該模組介面，不透過 `capability_map`

Capability Map 為嚴格靜態值： `capability_map` 在啟動階段一次決定後，runtime 不再更新。Level 2 後的 recovery rebuild 屬 runtime operational state，rebuild 成功不改 map（能力本質未改）；rebuild 失敗或 timeout 亦不改 map，而是直接進 Level 3——由新啟動的 process 於啟動階段重算 `capability_map`。此設計配合 §6.5「recovery 失敗直接 Level 3」政策，避免「runtime 更新 map 但無可觀察存續期」的矛盾。

適用性：Snowboard 啟動後固定、不熱插拔， `capability_map` 中的能力狀態為啟動時決定的靜態值；不引入 runtime detect 機制

---

## 7. 設定與部署假設

### 7.1 三層設定

| 層 | 檔案 | 進 git | 內容 |
| --- | --- | :---: | --- |
| Schema / 預設 | `src/sbd/core/config/` | ✅ | dataclass 定義、預設值、載入邏輯 |
| 本機覆寫 | `config.local.yaml` | ❌ | pin 腳、ALSA card、模型路徑 |
| 秘密 | `.env` | ❌ | MQTT 密碼、API key |
| 範本 | `config.example.yaml` `.env.example` | ✅ | 使用者複製後改名 |

載入順序：預設 → local yaml → env 格式：YAML for config、 `KEY=VALUE` for env

### 7.2 平台與 static capability 假設

* 執行平台：Raspberry Pi 5 (Pi OS)；主流程執行於此
* 開發平台：可於一般 Linux / macOS / Windows 開發（純 Python 邏輯與 mock 測試）；每個 driver / 實作子目錄配 mock 版本以支援開發機執行
* 測試範圍： `tests/` 只測純軟體，不測硬體
* Static capability 假設：HW 啟動後固定、不熱插拔——此為部署層平台假設，其架構意涵（capability 為啟動時決定的靜態值、不引入 runtime detect）見 §6.8 B。此假設若被打破（例：加入 USB 設備動態接入），需回本節重新裁決

---

## 8. 未定案事項

本章收錄已有討論、但尚未正式納入設計的方向。所有本文件出現「尚未定案」字樣的引用皆指向此章。落地時再從此移入對應章節；不落地者可長期留存於此。本章敘述格式較寬鬆，允許保留討論脈絡與設計構想。

### 8.1 錯誤與資源

* LED 顯示機制：現行以 OLED 為主要本機表達通道 (§5.3)；LED 未納入表達架構， `core/leds/` 亦不在目錄結構中。若未來啟用 LED 表達（狀態指示 / 呼吸燈 / 音量條），需一併定義 HAL 契約（ `core/leds/` 目錄與 Protocol）、角色分工、仲裁機制、系統關鍵狀態搶佔規則、與 §5.3 Display 顯示的一致性；若需與 Display 共用同一種仲裁機制，則同時審視 §5.3 仲裁層是否搬離 `core/display/` 。觸發條件：出現實際 LED 表達需求且能與 OLED 表達職責邊界清楚劃分
* Adjuster / Overlay 短暫覆蓋：按鈕觸發的 OSD 顯示（例：音量鍵彈出音量條）屬短暫覆蓋，不屬 `status_bar` / `main` / `fullscreen` 任一模式。需定義新顯示模式、觸發來源（GPIO 直觸發、非對話流程）、與 §2.5 `adjustments` 的對接、自動消失時序。觸發條件：出現實際 OSD 需求
* GPIO 進階分流：一 pin 多訂閱者（同一 pin 事件同時餵給 `input_events` 與 `adjustments`，各自依技法判定）需定義訂閱者間按法解讀重疊時的仲裁、共享 pin 註冊 API、除錯策略。觸發條件：一 pin 一訂閱者無法滿足全新使用情境
* Cancel timeout 分級：各級 timeout 值與 per-worker-kind 差異。觸發條件：實際觀測到 kind 之間收斂時間差異顯著
* Touch 事件源：現行 §1.2 硬體堆疊不含觸控面板； `core/display` 只管顯示，不含觸控事件源； `input_events` 不建立 touch 類型。若未來加入含觸控的面板，需一併裁定：事件 ownership （獨立 `InputSource` vs `core/display` 附屬）、 `DisplayDevice` Protocol 與觸控源的分界、對話流程角色（Signal / `adjustments` / 兩者皆有）。觸發條件：出現實際 touch 使用情境

### 8.2 資料與協定

* `docs/protocol.md` ： wake daemon IPC schema 等對外 / 跨 process wire format；已於 P4、§2.4 引用其存在，內容俟未來分案產出。觸發條件：實作 wake daemon、引入其他跨 process 契約、或實作 worker child process IPC（cooperative cancel 訊號、 `READY ACK`、`result` 回傳等 schema）

### 8.3 尚未納入設計的能力

以下項目屬設計層構想，未確立原則前不進入其他章節。

* Query action：作為第四類 action（查詢式派發，例：雲端查詢 / 雲端 LLM）。無狀態脈絡構想——query payload 附「`brief_context`」摘要、外部服務原樣回傳、reasoner 依 `brief_context` + `answer` 恢復狀態。待決策：回覆入口（ `ExternalMessageArrived` / 專屬 Signal / read perception ）、correlation 機制、上下文 schema
* 完整 reasoning loop：Tool 結果回饋後再次推論。待決策：correlation id、新狀態（如 `TOOL`）
* 多輪對話記憶：跨 turn / 跨 session 的上下文儲存。待決策：儲存範圍、清理策略、與 reasoner 的接面
* `core/network` ：多 adaptor 共用 transport（TCP / UART / 藍牙）的落點。觸發條件：出現第二個需要共用底層 transport 的 adaptor
