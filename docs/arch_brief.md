# Snowboard 架構設計 ( Brief )

離線 AI 語音助理，於 Raspberry Pi 5 ( Pi OS ) 執行。本檔為 `arch.md` 的極簡摘要，保留主要原則、契約與邏輯（少數演進觸發條件與冗長討論脈絡略去，權威定義以 `arch.md` 為準）。

## 1. 目標與邊界

### 1.1 定位
裝置端離線 AI 語音助理：主要對話不依賴雲端；語音 / 按鈕 / 外部訊息任一口喚醒；OLED 為本機主要表達通道。

### 1.2 硬體 / 軟體堆疊
* **HW** : I2S mic、I2S speaker、SPI OLED、8MP CSI 相機、GPIO ( 按鈕 / LED / 家電 )
* **SW** : ASR ( 離線 )、TTS ( 離線 )、LLM ( LiteRT-LM 執行 Gemma3:e2b )、Tool calling、外部通訊 ( MQTT / UART / IPC )、喚醒 ( wake word / 按鈕 / 外部訊息 )

### 1.3 貫穿性原則 P1–P5 ( 不可違反 )
* **P1 Core = 契約 + Library Adapter** : `core/*` 把 OS / library 包成 Protocol 契約，不自寫 driver；同契約可並存多實作，config 選擇。
* **P2 契約以本 agent 使用情境為依據** : 不追求通用；目前無人使用的能力不進契約。
* **P3 Adaptor 只承擔對外通道** : 每個 adaptor 對應一個明確對外用途；本機 HW 屬 core。
* **P4 模組介面應允許未來跨 process** : 可能獨立為 daemon 者，介面可序列化、不共享物件狀態；IPC schema → `docs/protocol.md`。
* **P5 Worker Degradation** : Worker 應內部消化部分失敗、產出可用 fact 使 turn 走完。降級後有可用結果 → 對外 `status=ok`；無可用結果 → `status=error`。Exception 洩漏 ( `ErrorOccurred` ) 為最後手段。錯誤兩層分界見 §6.6。

---

## 2. 系統拓撲

### 2.1 分層與依賴
生命週期分層（對應目錄）：`input_events` → `perception` → `cognition` → `action` （外部觸發 → 感知 → 認知 → 行動）；`adaptor` 全程訂閱狀態，把系統狀態具現化到物理世界；`core` 所有實作共享的基礎設施與硬體資源；`adjustments` 不進對話流程的直接控制輸入（音量、亮度等）。

* **流程協調**：僅經 SM 與 Event Bus。SM 用方法呼叫驅動 worker、發 `StateChanged`；worker 透過 Bus 發 Fact 或送 Signal。
* **能力取得**：上層向 core 借用資源，不直接碰硬體。
* **工作節點**：互不相識，只認 SM 與 Bus。SM 是唯一狀態擁有者與協調者。
* **抽象 + 多實作**：有多實作需求的層以 `base.py` 定 Protocol、實作以子目錄組織；SM 只認契約。目前 `input_events` / `perception` / `action` / `adaptor` / 各 core HAL 皆採此結構。`cognition/` 現況單一 reasoner，暫不設 `base.py` （P2：無多實作需求不預先造契約）；未來若加入第二種 cognition 實作（例：雲端 reasoner），再引入 Protocol。
* **HW 通道與語意角色分離**：同 HW 可被多層借用，語意由生命週期層決定（例：mic 是 core/audio 資源；voice_wake 偵測喚醒詞、perception/listen 錄語音）。

---

### 2.2 目錄總覽

```text
src/sbd/
├── main.py                     # 進入點：組裝 + 啟動
│
├── core/                       # 基礎設施 + 硬體 HAL
│   ├── config/                 # 三層設定 (§7.1)
│   ├── logger.py               # 統一 logger
│   ├── event_bus/              # 本機 pub/sub (direct-call)
│   ├── state_manager/          # 全局狀態機 (SM)
│   ├── audio/                  # I2S mic/speaker
│   ├── display/                # SPI OLED
│   ├── camera/                 # CSI 相機
│   └── gpio/                   # GPIO 存取
│
├── input_events/               # 外部輸入層 -> 送 Signal 給 SM
│   ├── base.py
│   ├── button/
│   ├── external_message/       # MQTT-in 等外部訊息
│   └── voice_wake/             # IPC client : 連接獨立的 wake daemon
│
├── adjustments/                # 直接控制類輸入，不進 SM (音量、亮度等)
│
├── perception/                 # 感知層
│   ├── base.py
│   ├── listen/                 # 麥克風 + ASR
│   ├── read/                   # 外部訊息 -> 文字
│   └── look/                   # 相機 + 視覺
│
├── cognition/                  # 認知層
│   ├── reasoner.py
│   ├── llm_engine.py
│   └── prompt_builder.py
│
├── action/                     # 行動層
│   ├── base.py
│   ├── speak/                  # TTS
│   ├── tool/                   # 命令式 fire-and-forget
│   └── rest/                   # session 收尾 (見 §2.8)
│
└── adaptor/                    # 對外具現化 / 雙向通道
    ├── base.py
    └── mqtt/                   # 對外 MQTT 通道
```

---

### 2.3 core/ 邊界
* **軟體基礎設施**：`config/`、`logger.py`、`event_bus/`、`state_manager/` ；**HW HAL**：`audio/`、`display/`、`camera/`、`gpio/`
* **core/audio**：只提純 PCM I/O；VAD / 串流分段屬 `perception/listen` 或 `voice_wake` ；mic 獨佔切換見 §5.2
* **core/display**：低階原語（畫 pixel、寫文字、清畫面）；不含多寫入者仲裁（見 §5.3）；不含觸控事件源（依 P2，無 touch 使用情境不進契約，見 §8.1）
* **core/gpio**：集中管理 pin 存取；消費者：`input_events/button`、`action/tool` ；分流見 §5.4

### 2.4 input_events/ ── 外部輸入
* **職責**：把物理事件翻譯為對 SM 的 Signal (意圖類事件)
* **契約 InputSource** : 可 start/stop 的常駐輸入源，運作中對 Bus 發 Signal
* **事件**：`ButtonPressed`、`ExternalMessageArrived`、`WakeWordDetected`（見 §3.3）；未使用類型（knob/gesture 等）不建立；touch 屬未定案（§8.1）
* **voice_wake**：僅獨立 wake daemon 的 IPC client（P4 案例，IPC schema → `docs/protocol.md`）
* **external_message** 與 read 消費路徑 → §5.1

### 2.5 adjustments/ ── 直接控制輸入
不改變對話狀態的操作（音量、亮度等），直呼 core / adaptor，不經 SM。GPIO 分流見 §5.4。

### 2.6 perception/ ── 感知層
* **契約 Perception** : `perceive() -> PerceptionResult`
* **實作**：`listen` ( mic + ASR ) / `read` ( 外部訊息 payload → 文字 ) / `look` ( camera + 視覺 )
* **平行執行**：一 turn 可平行多 module；每 module 獨立 timeout
* **Timeout / 部分失敗 = 資訊，非錯誤**：
  * `PerceptionResult.status` ∈ `{ok, timeout, error}`，一併送入 reasoner
  * `error` = module 內部依 P5 降級後仍無可用結果，但 module 仍存活
  * worker crash 屬 exception 層，走 `ErrorOccurred` (§6.6)
* **組合決策權**：第一 turn 由 SM 依 wake source 反射決定 (§4.4)；後續 turn 由 reasoner `next_perceptions` 決定
* **read 的輸入路徑**：被動消費者，向 `external_message` 索取 (§5.1)；其他 perception 為時間點觸發，直接向 core 借用資源即可

### 2.7 cognition/ ── 認知層
* **分工**：SM 反射與時序協調；Reasoner 認知與決策（理解 / 推論 / 選 action / 決定 `next_perceptions`）
* **Reasoner 能力**：接收本 turn 所有 `PerceptionResult`（含 status）；接收 THINK Entry 傳入的 pending message metadata（payload-free：id 清單或 count；來源 §5.1）──供決定 `next_perceptions` 是否含 read；組 prompt → 呼 LLM → 正規化為 `LLMResponse` ；一 turn 一 `LLMResponse` ；依 P5：LLM 部分失敗時內部降級（例：apology speak + 繼續 listen）
* **Pending metadata 邊界**：reasoner 可觀察但不可解讀（僅 metadata）；實際內容由下一 turn 的 read perception 讀取
* **Capability 查詢邊界**：reasoner 可查 `capability_of(kind)` (§6.8 B)，合法 kind = perception kind ∪ action kind（與其產出契約同粒度）；不查 core 資源、adaptor、input source（Null Object Pattern 完整落實──reasoner 不感知 false 的原因來自依賴 null / 自身 fail / config optional）
* **LLMResponse 契約**：`action_kind` ∈ `{speak, tool, rest}` ；`action_payload` 依 kind ( schema 屬 implement.md ) ；`next_perceptions` 為下一 turn perception 組合 ( rest 時忽略 )
* **next_perceptions 邊界**：只能從架構已註冊 capability 中選（目前 `listen` / `read` / `look`）；只是 kind 清單，不攜輸入脈絡（每 perception 自知輸入來源）；SM 於 THINK Exit 的驗證與剔除處理見 §4.6

### 2.8 action/ ── 行動層
* **契約 Action** ： `execute(request) -> result` ；全數以 `ActionCompleted(kind, status, result)` 回報（status ∈ `{ok, error}`）。依 P5：worker 內部降級優先產 fact；`status=error` = worker 存活但主動作無可用結果；crash 走 `ErrorOccurred`
* **種類**：
  * `speak/` ( TTS 合成 + 播放 )
  * `tool/` ( 命令式派發，fire-and-forget──派發完成即 ActionCompleted，不等結果；真正執行結果由外部通道以獨立事件回到系統，屬下一 wake 或下一 turn 的 input )
  * `rest/` ( 產生使用者可感知的收尾：告別語、關螢幕、滅燈 )
* **Query** ( 第四類 action ) 尚未定案 → §8
* **rest 意義與邊界**：Reasoner 判 session 該結束 → `LLMResponse(action_kind=rest)` ；rest 為可選 UX 收尾，不擁有 session / 資源生命週期；`action/rest` 純執行 UX 收尾，跑完即回報，不呼 SM、不管其他 worker ；SM 收 `ActionCompleted(kind=rest)` 後的收尾流程見 §4.6 ACTION Exit。
* **統一性**：所有 turn 一律以 `ActionCompleted` 收束，消除「無 action → SM 直接回 IDLE」特例分支

### 2.9 adaptor/ ── 對外通道
對外通道 ( P3 )，本機 HW 不屬此層；損壞不影響主流程。範圍：`adaptor/mqtt/` 雙向 MQTT。本機具現化 Display 三角色皆屬應用層（見 §5.3）。

---

## 3. 跨模組互動

### 3.1 控制流 vs 事件流分離
* **控制流走方法呼叫**：SM 認 worker 外層契約（Protocol，不知內部實作），直呼方法啟動、持 task handle（用於強制 cancel）；worker 之間互不相識，只認 SM
* **事件流承載觀察與意圖**：Event Bus 不承載命令
* **SM 持有的 task handle** 是 worker 外殼 coroutine ；若 worker 內部持有 native thread 或 child process，由 worker 自己管理，不進 SM 追蹤、不進 Event Bus
* **生命週期**：In-flight worker 與 handle 生命週期 → §6.3 ；三級 cancel → §6.4

### 3.2 事件三類與貫穿性契約

| 類別 | 命名 | 事件 | 發布者 | 訂閱者 |
| :--- | :--- | :--- | :--- | :--- |
| **Worker Facts** | 過去式 | `PerceptionResult` / `LLMResponse` / `ActionCompleted` / `ErrorOccurred` | worker / HAL / bus 兜底（皆 non-SM） | SM + observer |
| **State Broadcast** | 過去式 | `StateChanged` | SM 唯一 | observer（SM 不訂閱自己） |
| **Signals** | 意圖 | `ButtonPressed` / `ExternalMessageArrived` / `WakeWordDetected` / `InterruptRequested` / `ShutdownRequested` | input_events / 系統模組 | SM 唯一 |

`observer = adaptor / log / metrics`

* **貫穿性契約**：SM publish 集合 = `{StateChanged}` （只廣播狀態）；SM 訂閱集合 = Worker Facts ∪ Signals ；SM 從不 publish `ErrorOccurred` （遇 unrecoverable exception 讓 process 崩、由 systemd 接手）；ERROR 進入的兩條因果鏈（SM 皆不 publish `ErrorOccurred`）：
  * **外因**：`ErrorOccurred(non-SM)` → SM 讀到 → `StateChanged(→ERROR)` （observer 依時序推得原因）
  * **SM 自檢**：SM 判定送達的 Fact 內容違約（不合 schema 的 LLMResponse、剔除未註冊 kind 後仍為空的 next_perceptions） → SM 直接 transition ERROR、不先 publish `ErrorOccurred` ， `StateChanged(→ERROR)` 即權威信號
* **收斂**：兩條於 ERROR Entry 皆走 §6.5 error 收斂，皆不升級為 process 崩（Level 3 僅留給 §6.4 收斂失敗與 §3.4 bus 兜底失敗）

### 3.3 事件清單
* **Worker Facts**：
  * `PerceptionResult(kind, status, text, extra)` （status ∈ `{ok, timeout, error}`）
  * `LLMResponse(action_kind, action_payload, next_perceptions)` （action_kind ∈ `{speak, tool, rest}`）
  * `ActionCompleted(kind, status, result)` （status ∈ `{ok, error}`）
  * `ErrorOccurred(where, error)` ── 無 severity 欄位，SM 對所有 `ErrorOccurred` 統一反應（進 ERROR）
* **State Broadcast**：
  * `StateChanged(old, new)`
* **Signals**：
  * `ButtonPressed(button_id, duration_ms)`
  * `ExternalMessageArrived(channel, arrived_at, message_id)` ── 僅 metadata，payload 由 external_message 持有，message_id opaque、由 external_message 產生、與 buffer 內單則訊息 1:1，SM 只轉發不解讀（雙重角色見 §5.1）
  * `WakeWordDetected(phrase, confidence)`
  * `InterruptRequested()`
  * `ShutdownRequested()`
* **Schema 與版本化**：事件 dataclass 具體欄位型別 / 驗證 → `implement.md` （本文件只列欄位名與語意約束）；內部事件無版本化需求（單 process、direct-call、一起 build 一起部署）；跨 process / 跨機器 wire format 才需版本化 → `docs/protocol.md` ；`LLMResponse.action_payload` schema 由 `implement.md` 依 `action_kind` 定義，SM 於 THINK Exit 驗證──speak 至少含可播放的文本欄位；tool registry-driven （SM 只驗 tool 名稱存在於 tool registry，open schema，避免綁架擴展）；rest 允許 empty payload （符合 §2.8 rest 為可選 UX 收尾）；外部訊息驗證位置：adaptor 內驗證協定格式，失敗於 adaptor 丟棄 + log warning，通過後由 `input_events/external_message` 產出符合 read 契約的 payload

### 3.4 Event Bus 執行模型
* **Direct-call**：`publish()` 同步呼叫所有 subscribers ；無 Queue、無背景 dispatch loop
* **Handler 異常隔離**：bus 用 try/except 隔離每個 handler ；抓到 exception 一律 publish `ErrorOccurred(where="bus.dispatch.<handler>", ...)` 兜底，不偵測是否重複（無法可靠偵測、也沒必要──若 handler 已自報，SM 在 ERROR 對後續 `ErrorOccurred` 自然吸收）
* **兜底規則不遞迴、fatal 交回頂層**：派送 `ErrorOccurred` 時 handler 拋 exception → 不再二次 publish ；log fatal 後把 exception 交回頂層 ；`main.py` 收到即結束 process，交由 systemd 重啟 ( §6.4 Level 3 ) ── `ErrorOccurred` 已是最後兜底信號，再失敗則 direct-call 下遞迴 publish 會無限展開
* **無 subscriber**：log warning ( 不區分「未知型別」與「無訂閱」 )
* **過濾**：外部 raw 協定訊息由 adaptor 過濾、不進 bus ；內部事件（含 `ExternalMessageArrived` Signal）走 bus

### 3.5 SM 執行模型 ( Inbox )
* **SM subscriber 是薄殼**：將事件放進 SM 內部 inbox ( 同步 enqueue ) 後立即返回
* **SM 有常駐 dispatch loop**：唯一負責從 inbox 取事件、跑狀態轉移、呼叫 worker
* **保證**：SM 狀態轉移永遠單執行、無交錯；巢狀 publish 深度固定為 1 ( worker 回報走 inbox，不重入 SM handler )

### 3.6 併發與 Guard 三步判定
* **單 event loop**：handler 內 `await` 會讓出控制權，其他事件可穿插
* **順序**：多 producer 並行 publish 時不保證全域順序
* **非法時序**：→ log warning + 忽略，不拋錯

**Guard 三步**（SM dispatch loop 從 inbox 取出後依序執行，任一失敗即 log warning + drop）：
1. **Kind 白名單**：事件 kind ∈ ( 跨狀態三事件 ∪ 當前狀態額外接受事件 )，見 §4.5；適用所有事件
2. **ID 過期驗證**：事件 `session_id` / `turn_id` 匹配 SM 當前追蹤；僅 Worker Facts ；Signals 與 `ErrorOccurred` 無 ID，跳過
3. **交狀態卡處理**：依 §4.5 / §4.6 執行轉移、Entry / Exit、或調度指令（例 §5.1 pending）

**設計要點**：`ErrorOccurred` 不參與 ID 驗證（無 `session_id`，且過期 error 仍是 error，drop 反漏收斂機會）；Signals 無 ID 天生跳過 Step 2，`ExternalMessageArrived` 於非 IDLE 通過 Step 1 後由 Step 3 依 §5.1 發調度指令；收斂中 worker race 送出的 Facts 由「被 cancel 者不 publish Facts」規範源頭（§6.3），guard 層由 Step 2 兜底；In-flight 集合成員身份不納入 guard（屬 `implement.md` 層雙保險）

### 3.7 追蹤粒度
* 每 session 分 `session_id` ；每 turn 分 `turn_id` ( session 內遞增 )
* SM 下發呼叫與 worker 回報皆帶 `(kind, session_id, turn_id, correlation_id)`
* SM 拒絕不屬當前 session/turn 的事件（log + 忽略）
* Wake / Shutdown / Interrupt 屬 session 外事件，不需 ID

---

## 4. 對話狀態機

### 4.1 Session / Turn 雙層
Session 從一次 wake 回到 IDLE ；Turn Session 內一次「perception → think → action」；一 session 可含多 turn。

### 4.2 狀態集合

| 狀態 | 意義 |
| :--- | :--- |
| `IDLE` | 等待外部觸發 |
| `WAKE` | 已喚醒，發反饋、準備啟動 perception |
| `PERCEPTION` | 一或多 perception module 平行執行中 |
| `THINK` | Reasoner 推論中 |
| `ACTION` | 執行 action ( speak / tool / rest ) |
| `ERROR` | 錯誤處理中，短暫停留後回 IDLE |

### 4.3 醒來反饋時序
`IDLE` → `WAKE` → 等 `wake_ack_seconds` ( config ) → `PERCEPTION`。進 WAKE 時 SM 發 `StateChanged`，StatusBar 狀態 slot 更新 (§5.3)；反饋可含 earcon 等其他通道。`wake_ack_seconds` 是刻意 UX buffer，讓使用者感知已醒來、收音才穩定。

### 4.4 Wake source → 首 turn perception 映射

| Wake source | Perception 組合 | 理由 |
| :--- | :--- | :--- |
| `ButtonPressed` | `[listen]` | 使用者按鈕 → 預期後續語音 |
| `WakeWordDetected` | `[listen]` | 剛講話喚醒 → 接續錄音 |
| `ExternalMessageArrived` | `[read]` | 訊息 payload 已於外部通道到達，由 read 消費（§5.1） |

**性質**：SM 內建、不進 config 覆寫（屬架構層反射行為，形式與內容一同確立；`default_perceptions` 之於錯誤路徑才是產品層調校項，見 §4.8）。未來出現產品層調校需求，再升級為 config-driven。同時到達：不支援複合觸發。多 wake Signal 近乎同時到達，先到者觸發 IDLE→WAKE 並確定 wake source；後到者依 §4.5「wake 類 Signal 雙態行為」處理。

### 4.5 狀態轉移表
* **共通前置**：所有 Entry 隱含 SM publish `StateChanged(old, new)`。
* **跨狀態接受的三個事件**：`ShutdownRequested` / `ErrorOccurred` / `InterruptRequested` 在所有狀態（終止流程除外）皆合法接受，反應見 §4.7。非白名單一律 log warning + 忽略。
* **wake 類 Signal 雙態行為**：`ButtonPressed` / `WakeWordDetected` 僅 IDLE 接受並觸發轉移，其餘狀態拒絕；`ExternalMessageArrived` IDLE 接受並觸發轉移，其餘狀態亦接受但不觸發轉移，SM 依 §5.1 對 `external_message` 發調度指令。

**主流程轉移**：

| 當前 | 觸發 | 目的 | 備註 |
| :--- | :--- | :--- | :--- |
| `IDLE` | `ButtonPressed` / `WakeWordDetected` / `ExternalMessageArrived` | `WAKE` | 記錄 wake source |
| `WAKE` | `wake_ack_seconds` 到期 | `PERCEPTION` | ── |
| `PERCEPTION` | 所有 perception 完成或 timeout | `THINK` | ── |
| `THINK` | `LLMResponse` 驗證通過 | `ACTION` | 驗證見 §4.6 THINK Exit |
| `THINK` | `LLMResponse` 驗證不通過（schema / payload 不合，或剔除未註冊 kind 後 `next_perceptions` 空） | `ERROR` | reasoner bug（P5 降級亦失敗）；走 §3.2「SM 自檢」ERROR 路徑（見 §4.6 THINK Exit） |
| `ACTION` | `ActionCompleted(kind∈{speak,tool}, status=ok)` | `PERCEPTION` | 依 reasoner `next_perceptions` |
| `ACTION` | `ActionCompleted(kind∈{speak,tool}, status=error)` | `PERCEPTION` | 依 SM `default_perceptions` (§4.8) |
| `ACTION` | `ActionCompleted(kind=rest, status=any)` | `IDLE` / `ERROR` / (process 崩) | 見 §4.6 ACTION Exit 與 §6.5 |
| `ERROR` | in-flight 集合空且 RM recovery barrier 已清除 | `IDLE` | 見 §6.5 ERROR Exit 條件 |

### 4.6 Entry / Exit（僅列影響資源、ownership、契約者）
純 defensive check 不列。所有 Exit 均隱含「確認相關 in-flight handle 已釋放」──defensive check，正確性仰賴 worker 契約（§6.3「終態 Fact 發布時序」）。

* **WAKE Entry**：分配 `session_id` ；記錄 wake source (供 §4.4) ；啟動 `wake_ack_seconds` timer ；若 wake source 為 `ExternalMessageArrived` → 通知 `external_message` ：訊息屬本 session (§5.1)。
* **WAKE Exit**：停 `wake_ack_seconds` timer（正常路徑 timer 觸發即進 PERCEPTION；若提前離開需顯式停避免延遲觸發污染下一 session）。
* **PERCEPTION Entry**：分配 `turn_id`（session 內遞增，首 turn = 1）；決定本 turn perception 組合──首 turn 依 wake source 反射 (§4.4)，後續依前一 `next_perceptions` ；若前一 turn 為 `ActionCompleted(kind∈{speak,tool}, status=error)` → 改用 `default_perceptions` (§4.8)；對每 kind 呼 worker、加入 in-flight 集合；若含 read → 通知 `external_message` 啟動 read 消費 (§5.1)。
* **THINK Entry**：呼 reasoner，加入 in-flight 集合；傳入本 turn `pending message metadata`（僅 id 清單或 count，不含 payload；來源 §5.1）。
* **THINK Exit**：依序驗證 `LLMResponse` ── (1) `action_kind` ∈ `{speak, tool, rest}` ；(2) `action_payload` 符合對應 kind schema ；(3) 剔除 `next_perceptions` 未註冊 kind（log warning + 忽略）；(4) `action_kind` ∈ `{speak, tool}` 時剔除後須非空。任一違約走 §3.2「SM 自檢」ERROR 路徑，通過者以剔除後 `next_perceptions` 進 ACTION。
* **ACTION Entry**：依 `action_kind` 啟動對應 action worker，加入 in-flight 集合。
* **ACTION Exit ( kind=rest )**：執行 §6.5 rest 收斂；清 SM session 追蹤欄位（`session_id`、`turn_id`、`wake source`、`next_perceptions` 等）；通知 `external_message` flush-to-wake (§5.1)。Level 1 正常完成 → IDLE；Level 2 破壞 backend → ERROR 等 recovery barrier；Level 2 失敗 → Level 3。
* **ERROR Entry**：對 in-flight 執行 §6.5 error 收斂。
* **ERROR Exit**：清 SM session 追蹤欄位；通知 `external_message` discard buffer。

### 4.7 跨狀態收斂觸發
以下三事件在任意狀態（終止流程除外）皆合法接受；收斂上限、Level 2 失敗後行為、external message buffer 處置 → §6.5。

| 事件 | SM 反應 | 目的 |
| :--- | :--- | :--- |
| `InterruptRequested` | 觸發收斂 (§6.5)；Level 分支見 §6.5 表格 | IDLE / ERROR / (process 崩) |
| `ErrorOccurred` | 進 ERROR ( 收斂於 ERROR Entry 執行 ) | ERROR |
| `ShutdownRequested` / `SIGTERM` / `SIGINT` | SM 進 shutdown 模式（拒新 wake 類 Signal） → 收斂 (§6.5) → in-flight 空後停 dispatch loop → `main.py` 依 Resource Manager 反向呼各模組 `stop()` (§6.2) | (終止) |

若已在 ERROR：
* `ErrorOccurred` 疊加自然吸收 (§3.4)
* `InterruptRequested` 忽略（已在收斂中）
* `ShutdownRequested` 升級為 shutdown 收斂
* **ERROR 特殊性**：`ExternalMessageArrived` 於 ERROR 亦拒絕（無額外接受事件）── ERROR 為短暫收斂狀態、Exit 將對 `external_message` 發 discard，此期間新訊息無留存意義。

### 4.8 next_perceptions 與 default_perceptions
* `next_perceptions`：reasoner 於 `LLMResponse` 產出 (§2.7)；SM 用於 `PERCEPTION Entry` 決定下一 turn 組合
* `default_perceptions`：SM 內建、config-driven 預設組合（預設 `[listen]`）。僅在 `ActionCompleted(kind∈{speak,tool}, status=error)` 時取代 `next_perceptions`，避免下一 turn 卡在等永遠不到的訊息（例：tool 派發失敗但 reasoner 假定會收到 ACK）。此為 SM 唯一依 fact status 分歧的決策點



---

## 5. 特殊設計

### 5.1 external_message 與 read 消費路徑
SM 依狀態的調度指令（ExternalMessageArrived 既是 wake source 也是 perception input）：
* **IDLE 收到**：SM 開新 session、通知 `external_message` 訊息屬本 session
* **Session 中、當前 turn 有 read**：SM 啟動 read；read 執行時直接向 `external_message` 消費
* **Session 中、其他情況**：SM 通知 `external_message` 進 pending 模式（訊息續存於 buffer）
* **Session 結束走 rest（正常收斂）**：SM 通知 `external_message` `flush-to-wake` ── buffer 內未消化訊息重發 `ExternalMessageArrived`，SM 於 IDLE 收到後依第一條規則自然開新 session
* **Session 走 ERROR / Interrupt / Shutdown（異常收斂）**：SM 通知 `external_message` `discard`、buffer 清空

**設計原則**：每則訊息只走一條路徑（`ExternalMessageArrived` Signal → SM 決策），pending 升級為 wake 是同機制、非特殊路徑；SM 不接觸 payload、不持有 buffer，訊息生命週期由 `external_message` 完全擁有；調度指令以 `message_id` 指涉單則訊息（來自 Signal 攜帶的 opaque id），批次指令（flush / discard）以「當前 buffer 全體」或指定 id 集合為對象，SM 只轉發 id、不解讀；Pending metadata 對 reasoner 可見（payload-free）── SM 於 THINK Entry 將當前 buffer 內 pending 訊息的 id 清單或 count 傳入 reasoner（§2.7 / §4.6），僅 metadata、不含 payload，維持 SM / reasoner 皆不接觸 payload 的邊界；Reasoner 依此判斷下一 turn 是否加入 `read`。具體指令 API、buffer 資料結構、read 消費介面 → `implement.md`。

### 5.2 麥克風獨佔切換
`voice_wake` 與 `perception/listen` 不同時錄音；由 SM 協調誰在使用（見 §4.3）。使用情境「先喚醒、給反饋、才對話」，不做同時錄音。

### 5.3 Display 三角色與仲裁層
Snowboard 以 OLED 為本機主要表達通道。三角色皆屬應用層（非 core、非 adaptor），與 HAL（`core/display`）之間存在仲裁層。

**三角色**：

| 角色 | 職責 | 位置 | 觸發來源 | 生命週期 |
| :--- | :--- | :--- | :--- | :--- |
| **Presenter** | Worker 主動借用、顯示 domain hint（音量、信心度、部分結果、字幕等） | main area | Worker push hint | 綁 worker |
| **StatusBar** | 系統常駐資訊區、內部多 slot 聚合（時間 / 對話狀態 / 音量 / 連線 / 能力異動 / 錯誤提示 ...） | 頂部固定區 | 各 slot 自訂 | 常駐 |
| **全螢幕請求者** | 特殊時機的全螢幕（開機 / 結束 / 高光時刻 ...） | 蓋掉整個螢幕（含 StatusBar） | 任何模組主動呼叫 | 呼叫者掌控 |

`StatusBar` 內部 slot：StatusBar 是聚合器，內部管理多 slot ；slot 種類、owner、資料來源屬 UX 設計，列表屬 `implement.md`。原 StateIndicator（訂閱 `StateChanged` 顯示對話狀態）在此架構下降格為 StatusBar 的狀態 slot，不再是獨立模組。

**意圖 vs 執行分離**：三角色皆為意圖產生者，不直接寫 `core/display`。HAL 層（`core/display`）只提供低階原語，不知有幾 client、管誰蓋誰；仲裁層管區域分配（status_bar / main / fullscreen）與獨佔狀態；應用層（三角色）只送意圖，互不知情。

**仲裁層對外四動作**：

| 動作 | 呼叫者 | 效果 |
| :--- | :--- | :--- |
| `write_status_slot(slot_id, hint)` | StatusBar 內部 slot owner | 更新指定 slot |
| `write_main(hint)` | Presenter | 更新 main area |
| `request_fullscreen(hint)` | 任何模組 | 無人佔用 → 給、回 true；已佔用 → 拒、回 false |
| `release_fullscreen()` | 佔用者 | 釋放，回到 status_bar + main 常規模式 |

**仲裁規則**：`status_bar` 與 `main` 無競爭（各專屬區域）；`status_bar` 常駐不隱藏（除非 fullscreen 蓋掉）；fullscreen 互斥獨佔（一次一佔用者，呼叫者必須 `release` 後他人才能取得）；無先到先得排隊（拒絕即拒絕，呼叫者自決重試或降級）；系統時序保證獨佔不易撞（對話流程單線程使實際競爭罕見）。

**仲裁層建立與注入**：由 Resource Manager 於啟動階段建立、注入給三角色（同 §6.1 依賴注入責任）。模組落點：掛於 `core/display/` 作 HAL 上層薄殼；底層 HAL 仍為只提供低階原語的驅動封裝，仲裁層獨立於底層 HAL、位於同一目錄。若未來 LED 亦納入表達且需共用仲裁機制，再考慮搬離（見 §8.1）。Protocol 方法簽名細節 → `implement.md`。Adjuster / Overlay 短暫覆蓋、LED 顯示機制尚未納入 → §8。

### 5.4 GPIO 分流
`core/gpio` 依 pin 註冊映射把事件送到唯一訂閱者，一 pin 一訂閱者──不同物理按鈕依用途註冊給 `input_events` 或 `adjustments`。單一訂閱者內部可依按法（短按 / 長按 / 雙擊）產出不同輸出：例對話按鈕 pin → `input_events/button`，短按 → `ButtonPressed`、長按 → `InterruptRequested` ；例音量鍵 pin → `adjustments/volume`，短按 / 長按皆直控 `core/audio`。一 pin 多訂閱者屬進階分流，尚未定案（§8）。

---

## 6. 生命週期、失敗與收斂

### 6.1 Resource Manager
系統定義 Resource Manager 角色，職責：
1. 建立依 config 建立所需 core / worker instance、注入依賴
2. 啟動按依賴順序 `start()`
3. 啟動失敗處理中止並清理已啟動者，或依 §6.8 A 注入 Null Object 續行，並依 §6.8 B 更新 `capability_map`
4. Shutdown 收斂依順序 `stop()`，in-flight worker 收斂由 SM 執行（§6.5）
5. 依賴一致性保證使用者取得的資源已就緒
6. 能力查詢提供 `capability_of(kind)` 供其他模組主動查詢（§6.8 B）
7. Recovery rebuild：Level 2 `force_abort()` 破壞 backend（終止 child process）後，RM 在背景重建並 re-start、維護 recovery barrier，barrier 清除前 SM 維持 ERROR（§6.4 / §6.5）

**Lifecycle 契約**：所有 core 與 worker 實作統一介面（`start()` / `stop()` 或等價），供 Resource Manager 呼叫。細節 → `implement.md`。

### 6.2 啟動與停機順序
* **啟動**：`config` → `logger` → `event_bus` → `state_manager` → 硬體 `core` → `workers` / `adaptor`
* **Shutdown**（由 `ShutdownRequested` Signal 或 `SIGTERM` / `SIGINT` 觸發）：
  1. SM 進 shutdown 模式（拒新 wake 類 Signal，§4.7）
  2. SM 對 in-flight 執行 §6.5 shutdown 收斂
  3. In-flight 空後停 SM dispatch loop
  4. `main.py` 依 Resource Manager 反向呼各模組 `stop()`。各步驟具備獨立 timeout（config-driven，值屬 `implement.md`）
* **Level 3**（process 崩、systemd 重啟）為終極兜底 → §6.4。

### 6.3 In-flight worker 與 handle 生命週期
* **In-flight worker**：SM 呼 worker 方法啟動後，直到 task handle 對應的 asyncio task 真正結束（return / cancelled / raised），該 worker 稱為 in-flight。SM 為每 session 追蹤 in-flight worker 集合。
* **集合性質**：
  * **多元素**：PERCEPTION 平行時集合內含多 handle，「所有 perception 完成或 timeout」轉移條件 = 集合中所有 perception kind handle 均釋放
  * **Empty check 時機**：SM dispatch loop 每處理完一個事件後，依當前狀態的觸發條件檢查 in-flight 集合（原則層規範；實作 → `implement.md`）
  * **狀態間清空要求**：狀態卡 Exit 隱含「確認相關 handle 已從集合移除」（defensive check；正常路徑上 worker完成即釋放）
* **Handle 釋放**：worker task 真正結束後（無論 return / cancel / raise），SM 從 in-flight 集合移除該 handle。「真正結束」等價於 asyncio runtime 對該 task 標記完成──SM 藉 task done callback（或等價機制）得知，不以 `abort()` / `force_abort()` return 為準；具體排程機制屬 Ch 4。
* **Worker execution container 合約**：
  * `start()` return $\Rightarrow$ worker 及其所有 internal container（native thread、child process）均已 READY
  * `force_abort()` return $\Rightarrow$ 所有 internal operation 終止、descendant process 確認退出（waitpid 或等價）、HW 資源釋放
  * 無可靠 native cancel 的 blocking backend（如 LiteRT-LM Engine）：必須隔離於 child process；`force_abort()` 以「終止並 waitpid child process」作為完成證明；不隔離者 Level 2 無完成證明，唯一兜底為 Level 3。
* **終態 Fact 發布時序**：worker 必須在資源釋放完畢、task 即將 return 前 publish 終態 Fact ( `PerceptionResult` / `LLMResponse` / `ActionCompleted` )。Fact 到達與 task done 為兩個排程事件：狀態轉移的完成條件為「對應終態 Fact 已收到 AND 對應 worker task 已 done、handle 已從 in-flight 集合移除」；Fact 早於 task done 時，狀態轉移暫緩，待 task done callback 將 completion notice enqueue 至 inbox 後再重新做 empty check。架構用意如此；具體資料結構屬 Ch 4。
* **被 cancel 者不 publish Facts**：進入收斂後 worker 不再對 bus publish Worker Facts。唯一例外：cancel 過程本身出錯 → `ErrorOccurred`。此規則避免收斂中 worker 送出過期或半熟結果污染 SM。

### 6.4 Cancel 分級（三級收斂）
SM 對 worker 的 cancel 分三級（走控制流方法呼叫，不走事件流）：
* **Level 1 合作式**：SM 呼 worker `abort()` 並 `await` 完成。`abort()` return 代表 worker 已完成合作式停止義務（停內部工作、釋放硬體資源、外殼 coroutine 進入結束流程）；SM 隨後依 §6.3 等外殼 task done、才移除 handle。Level 1 對 native operation 不強制終止，worker 盡力即可
* **Level 2 強制**：Level 1 逾時 → SM 呼叫 `worker.force_abort()` 並 `await`：(1) 在 timeout 內 return → §6.3 完成證明成立，SM 隨後等 task done、移除 handle；(2) `force_abort()` 超時 → 直接進 Level 3。外殼 `task.cancel()` 不作為 Level 2 兜底──外殼 cancel 成功僅證明 Python coroutine 結束，不能證明 native thread / child process 已停止，與 §6.3完成證明義務衝突。純 asyncio worker 允許 `force_abort()` 實作等價 `abort()`
* **Level 3 放棄**：Level 2 逾時（`force_abort()` 未能提供完成證明） → 記錄 fatal → 讓 process 崩，systemd 重啟

Level 2 失敗後的分支與 external-message buffer 政策依觸發者而定 → §6.5。

**Process 重啟為設計上的終極兜底**：Level 3 不是意外，而是「合作式與強制手段皆失效」時的正常出口。涵蓋兩條進入路徑：Cancel 逾時（Level 2 `force_abort()` 逾時）；Bus 兜底失敗（Event Bus 派送 `ErrorOccurred` 時 handler 再度失敗，§3.4；fatal exception 交回頂層、`main.py` 結束 process）。兩條路徑最終皆由 systemd 重啟。系統韌性依賴 Level 1 / 2 處理絕大多數情況、systemd 處理其餘。

**Worker 合約**：必須實作合作式 `abort()` 方法；`abort()` return 前應停內部工作並釋放硬體資源；必須正確 re-raise `CancelledError` ；必須實作 `force_abort()` 並完成 §6.3「Worker execution container 合約」的完成證明義務。無可靠 native cancel 的 blocking backend 必須隔離於 child process，否則無法提供完成證明。各級 timeout 值與 per-worker-kind 差異尚未定案（含 child terminate + waitpid 預期時間，§8）。

### 6.5 Session 收斂機制 ( 統一 )
以下四情境皆執行 §6.4 三級 cancel ；Level 2 成功但破壞 backend 的後續處置與 external-message buffer 政策依 trigger 而定：

| 觸發 | 收斂上限 | Level 2 失敗後 | Level 2 成功且破壞 backend | External message buffer |
| :--- | :--- | :--- | :--- | :--- |
| `ActionCompleted(kind=rest)` | Level 2 | 進 Level 3 ( process 崩 ) | 降級走 Error 路徑 ( 進 ERROR，等 recovery barrier ) | flush-to-wake ( §5.1 ) |
| `InterruptRequested` | Level 2 | 進 Level 3 ( process 崩 ) | 降級走 Error 路徑 ( 進 ERROR，等 recovery barrier ) | discard |
| `ErrorOccurred` | Level 2 | 進 Level 3 ( error 已異常，不再降級 ) | 維持 ERROR，等 recovery barrier | discard |
| `ShutdownRequested` | Level 2 | 進 Level 3 | 不 rebuild ；完成 termination proof 後直接進 reverse stop() ( §6.2 ) | discard |

* **回 IDLE 前的 readiness gate**：Rest / Interrupt / Error 三條「回 IDLE」路徑，只要 Level 2 成功但破壞 backend，一律先進 ERROR、等 RM recovery barrier 清除後才回 IDLE ── 避免 backend 尚未 READY 時接受新 session。Shutdown 屬終止路徑、不 rebuild。
* **ERROR Exit 條件**：in-flight 集合空且 RM recovery barrier 已清除（若無 recovery 需要，barrier 於進 ERROR 時即為清除狀態；若 Level 2 有破壞 backend，須等 RM 完成 rebuild）。recovery 失敗或 timeout 由 RM 觸發 Level 3（§6.8 B：recovery 失敗不改 capability_map，直接讓 process 崩、systemd 重啟）。

### 6.6 錯誤兩層分界
依 P5，錯誤分兩層：

| 層 | 觸發 | 事件 | 系統狀態 | SM 反應 |
| :--- | :--- | :--- | :--- | :--- |
| **Fact 層** | Worker 存活、能翻譯的部分失敗 | `PerceptionResult` / `ActionCompleted` 帶 `status=error` | 一致 | 續 turn ( `ActionCompleted(status=error)` 改用 `default_perceptions` ；其他不分歧 ) |
| **Exception 層** | Worker crash / 翻譯不了的 exception 洩漏 | `ErrorOccurred` | 不確定 | 進 ERROR → 收斂 in-flight → 回 IDLE ( session 中斷 ) |

Worker 對「raise 還是回 `status=error`」的選擇即 P5 的實質內容：盡可能不 raise、優先產 fact 讓 session 延續。

### 6.7 分層責任

| 層 | 責任 |
| :--- | :--- |
| **HAL ( core )** | 消化 transient error、標記 degraded、拋明確錯誤型別 |
| **Worker** | 依 P5 內部降級產可用 fact；無法產出 fact 才 raise ；`CancelledError` 正確 re-raise |
| **Event Bus** | 隔離 handler 異常；抓到即兜底 publish `ErrorOccurred` ；派送 `ErrorOccurred` 不遞迴、fatal 交回頂層 (§3.4) |
| **SM** | 進 ERROR 時執行 §6.5 收斂；in-flight 空且 RM recovery barrier 清除後回 IDLE。recovery timer 由 RM 擁有，SM 不自管；recovery 失敗或 timeout 由 RM 觸發 Level 3 |
| **main.py** | 常規 asyncio cleanup ；接收 bus 交回的 fatal exception 並結束 process ( §6.4 Level 3 兜底路徑之一 ) |

### 6.8 能力降級：Null Object + Capability Map
兩機制並用。

* **A. Null Object Pattern**：適用範圍──需要以契約內無害行為維持下游呼叫鏈的 core 資源（ `core/audio` / `core/display` / `core/camera` ）在目錄下提供 null 實作。例外──純登錄型 HAL（ `core/gpio` 的 `register_input(pin, callback)` ）不需 null：「註冊後永不觸發」等同物理上沒接線，不需獨立類別；register 失敗直接由 RM 記 `capability_of=false` 、下游不啟動（判定原則見 `implement/ch02a` §2a.1）。啟動時 RM 嘗試建 real，start 失敗 → 有 null 者改用 null 注入、無 null 者將該 kind capability 設為 false ；上層 worker 拿到 core 契約物件，不區分 real / null （Null Object Pattern 核心）；Core 本身不做替換判斷，仍依 §6.7「拋明確錯誤型別」，real → null 替換決策集中於 RM。
* **B. Capability Map**：Resource Manager 內部維護 `capability_map: dict[kind, bool]`。合法 kind 範圍：core 資源（ `audio` / `display` / `camera` / `gpio` ） ∪ perception kind（ `listen` / `read` / `look` ） ∪ action kind（ `speak` / `tool` ）──涵蓋「跨模組決策所需、啟動時決定的靜態能力」。啟動時 real 成功 → `map[kind]=True`，start 失敗、注入 null → `map[kind]=False` + log warning。需能力狀態的模組主動查詢 `resource_manager.capability_of(kind)` ，Resource Manager 不主動通知、不 publish 事件：core 資源 kind → Presenter / adaptor 廣播；perception / action kind → 僅 reasoner 查（§2.7）。
* **能力鏈推導原則（worker capability）**：Worker 自身不感知依賴 real/null（Null Object 保證介面契約成立、不寫 if is_null 分支）。`capability_of("<worker_kind>")` 由 RM 依兩條並存路徑推導（任一為 false 即為 false）：P1 依賴不可用（worker 宣告依賴的 core 資源 `capability_of=false` ）；P2 自身 start 失敗（worker 自己 start 失敗，或 config 標 optional 而未載入）。兩條都通過才是 true。推導集中於 RM，worker 自身無感。
* **非 map 模組的查詢慣例**：adaptor 連線狀態、InputSource（voice_wake daemon 存活、button 硬體就緒等）屬可能 runtime 變化的能力，不入 `capability_map`。由該模組自帶查詢介面（例：adaptor `is_connected()` 、voice_wake IPC client 自知連線狀態）；呼叫者（例：StatusBar 連線 slot）直接呼該模組介面。
* **Capability Map 為嚴格靜態值**：`capability_map` 在啟動階段一次決定後，runtime 不再更新。Level 2 後 recovery rebuild 成功不改 map ；rebuild 失敗或 timeout 亦不改 map，直接進 Level 3 ──由新啟動的 process 於啟動階段重算 `capability_map`。此設計配合 §6.5「recovery 失敗直接 Level 3」政策，避免「runtime 更新 map 但無可觀察存續期」的矛盾。（平台假設根據見 §7.2）

---

## 7. 設定與部署假設

### 7.1 三層設定

| 層 | 檔案 | 進 git | 內容 |
| :--- | :--- | :--- | :--- |
| **Schema / 預設** | `src/sbd/core/config/` | ✅ | dataclass、預設值、載入邏輯 |
| **本機覆寫** | `config.local.yaml` | ❌ | pin 腳、ALSA card、模型路徑 |
| **秘密** | `.env` | ❌ | MQTT 密碼、API key |
| **範本** | `config.example.yaml` 、 `.env.example` | ✅ | 使用者複製後改名 |

`載入順序：預設 → local yaml → env。格式：YAML for config、KEY=VALUE for env。`

### 7.2 平台與 static capability 假設
* **執行**：Raspberry Pi 5 ( Pi OS )；主流程執行於此
* **開發**：一般 Linux / macOS / Windows（純 Python 邏輯與 mock 測試）；每 driver / 實作子目錄配 mock 版本以支援開發機執行
* **測試**：`tests/` 只測純軟體，不測硬體
* **Static capability 假設**：HW 啟動後固定、不熱插拔；架構意涵見 §6.8 B。此假設若被打破（例：加入 USB 設備動態接入），需回本節重新裁決

---

## 8. 未定案事項
已有討論、尚未正式納入；本文件「尚未定案」引用皆指向此章。落地時再移入對應章節；不落地者可長期留存。

### 8.1 錯誤與資源
* **LED 顯示機制**：現行以 OLED 為主要本機表達通道（§5.3）；LED 未納入，`core/leds/` 亦不在目錄結構中。若未來啟用 LED 表達，需一併定義 HAL 契約（`core/leds/` 目錄與 Protocol）、角色分工、仲裁機制、系統關鍵狀態搶佔規則、與 §5.3 一致性；若需與 Display 共用同一個仲裁機制，則同時審視 §5.3 仲裁層是否搬離 `core/display/` 。觸發：出現實際 LED 表達需求且能與 OLED 職責邊界劃分
* **Adjuster / Overlay 短暫覆蓋**：按鈕觸發 OSD（例：音量鍵彈出音量條）屬短暫覆蓋，不屬 status_bar / main / fullscreen 任一模式。需定義新顯示模式、觸發來源（GPIO 直觸發、非對話流程）、與 §2.5 對接、自動消失時序。觸發：出現實際 OSD 需求
* **GPIO 進階分流**：一 pin 多訂閱者（同 pin 事件同時餵給 `input_events` 與 `adjustments` ，各依按法判定）。需定義訂閱者間按法解讀重疊的仲裁、共享 pin 註冊 API、除錯策略。觸發：一 pin 一訂閱者無法滿足全新使用情境
* **Cancel timeout 分級**：各級 timeout 值與 per-worker-kind 差異。觸發：實際觀測到 kind 之間收斂時間差異顯著
* **Touch 事件源**：§1.2 硬體堆疊不含觸控面板；`core/display` 只管顯示、不含觸控源；`input_events` 不建立 touch。若未來加入含觸控面板，需一併裁定事件 ownership、`DisplayDevice` Protocol 與觸控源的分界、對話流程角色（Signal / adjustments / 兩者）。觸發：出現實際 touch 使用情境

### 8.2 資料與協定
* **`docs/protocol.md`** ：wake daemon IPC schema 等對外 / 跨 process wire format ；已於 P4、§2.4 引用。觸發：實作 wake daemon、引入其他跨 process 契約、或實作 worker child process IPC（cooperative cancel 訊號、READY ACK、result 回傳等 schema）

### 8.3 尚未納入設計的能力
* **Query action**（第四類 action，查詢式派發，例：雲端查詢 / 雲端 LLM）。無狀態脈絡構想──query payload 附 `brief_context` 摘要、外部服務原樣回傳、reasoner 依 `brief_context` + answer 恢復狀態。待決：回覆入口（ExternalMessageArrived / 專屬 Signal / read）、correlation 機制、上下文 schema
* **完整 reasoning loop**：Tool 結果回饋後再次推論。待決：correlation id、新狀態（如 `TOOL`）
* **多輪對話記憶**：跨 turn / 跨 session 上下文儲存。待決：儲存範圍、清理策略、與 reasoner 接面
* **core/network**：多 adaptor 共用 transport（TCP / UART / 藍牙）的落點。觸發：出現第二個需共用底層 transport 的 adaptor
