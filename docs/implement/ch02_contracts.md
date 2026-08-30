# Ch 2. 跨層貫穿契約

屬於 implement.md 索引 | 對應 arch.md §2.4 / §2.6 / §2.8 / §2.9 / §6.1 | 狀態：定稿（IR-final 已通過（2026-08-01））

本章定義 arch.md §2.1「有多實作需求的層」的 `base.py` Protocol——`InputSource` / `Perception` / `Action` / `Adaptor` 四類 Protocol，以及共通 `start()` / `stop()` 與 in-flight worker 的 `abort()` / `force_abort()` 語意。

**範圍邊界**
- **本章包含**：四類 Protocol 方法簽名、Lifecycle 與 cancel 方法語意、跨層 `ForceAbortReport`，以及 SM / Resource Manager 的呼叫契約
- **不含**：`core/*` HAL Protocol（見 Ch 2a）、worker 內部 library adapter（見 Ch 2b）
- **`cognition/` 不設 `base.py`**：依 arch.md §2.1，現況為單一 reasoner；`Reasoner` 直接於 `cognition/reasoner.py` 實作相同 in-flight 契約，不另預建 Protocol

---

## 2.1 Lifecycle 與 cancel 統一契約

四類 Protocol 皆採 asyncio 生態。所有模組具有 `start()` / `stop()`；只有會被 SM 放入 in-flight 集合的 `Perception`、`Action`、`Reasoner` 具有 `abort()` / `force_abort()`。

### `start()` —— 完全就緒

```python
async def start(self) -> None: ...
```

- **呼叫者**：Resource Manager（arch.md §6.1 職責 2）
- **時機**：Process 啟動階段，依 arch.md §6.2 順序
- **完成語意**：return 時模組已具備服務能力——長期資源、內部 queue / task，以及 native thread / child process 等 execution container 均已建立並完成 READY handshake；不能只代表硬體 handle 或 Python wrapper 已建好
- **失敗處置**：raise exception；Resource Manager 依模組類別採不同政策（見「§2.1.1 `start()` 失敗降級政策」）
- **冪等性**：不要求；重複呼叫行為未定義

### 2.1.1 `start()` 失敗降級政策

arch.md §6.8 A 明訂 Null Object 對象為 core 資源；worker（Perception / Action / Reasoner）、InputSource、Adaptor 的 `start()` 失敗政策依模組類別分別如下：

| 模組類別 | `start()` 失敗處置 | 下游查詢介面 |
| :--- | :--- | :--- |
| **core HAL**（Ch 2a） | `audio` / `display` / `camera` 的 real 建立或 start 失敗 $\rightarrow$ RM 注入對應 Null Object；純登錄型 `gpio` 不提供 Null Object，register/start 失敗即停用其下游 | `capability_map[<hal_kind>] = False`；RM `capability_of(kind)` |
| **Perception / Action** | **依 config schema（Ch 10）的 `required` 標記**：<br>• `required=true`（例：`perception/listen`）$\rightarrow$ 中止啟動、log fatal、process 結束<br>• `required=false`（例：`perception/look`）$\rightarrow$ 停用該 worker、不建立 in-flight-eligible 實例 | 若 optional 且失敗：`capability_map[<kind>] = False`；RM `capability_of(kind)`（`kind` $\in$ perception $\cup$ action） |
| **Reasoner** | `required=true` 唯一實例（arch.md §2.7「唯一 cognition 消費者」）；start 失敗即中止啟動 | 不入 `capability_map`（唯一實例、無 optional 語意） |
| **InputSource** | **依 config `required` 標記**：`required` 失敗中止啟動；optional 失敗停用該通道 | 不入 `capability_map`；InputSource Protocol 自帶 `is_available() -> bool` 查詢介面（§2.2） |
| **Adaptor** | 一律視為 optional（arch.md §2.9「損壞不影響主流程」）；失敗即停用該對外通道 | 不入 `capability_map`；Adaptor Protocol 自帶 `is_available() -> bool` 查詢介面（§2.5） |

**不為 worker / InputSource / Adaptor 建立 Null Object**。core 內也只有有需要以無害行為維持呼叫鏈的 `audio` / `display` / `camera` 提供 null；`gpio` 的登錄失敗與實體未接線等價，不建立 `NullGPIO`。擴張此範圍違背架構政策變更。

**Config `required` 標記**：Ch 10 `ComponentPolicy`已定案各worker/InputSource的
`enabled/required` defaults；Reasoner固定required、不另提供欄位，Adaptor固定optional。Resource Manager
於建立階段讀取已定schema、依上表分歧，不得自行推導另一組default。

**Capability Map 範圍（AR-Impl-5 已定案，2026-07-29）**：`capability_map` 內容為「跨模組決策所需、啟動時決定的靜態能力」，範圍限 **core 資源 + perception kind + action kind**。Adaptor / InputSource 屬 runtime-varying 能力（連線可能斷線、daemon 可能停），不塞進 map，改由各自 Protocol 自帶 `is_available()` 查詢介面。map 只在 startup 計算一次；runtime recovery 成功或失敗都不修改，recovery 失敗 / timeout 直接 Level 3，下一個 process 重新計算。

**Worker capability 推導原則（P1 + P2 並存）**：Perception / Action worker 的 `capability_map[<kind>]` 由 Resource Manager 依兩條路徑推導，任一為 false 即為 false：

| 路徑 | 場景 | 判定者 |
| :--- | :--- | :--- |
| **P1 依賴不可用** | worker 拿到的 core 依賴是 null（core 資源啟動失敗） | RM 依「依賴宣告 + core capability」推導 |
| **P2 自身 start 失敗** | worker 自己起不來（模型缺、引擎初始化失敗），或 config 標 optional 而未載入 | RM 依「start 成功與否 + config `required`」判定 |

Null Object Pattern 只約束 worker 內部行為（拿到 null 依賴不 raise、不寫 `if is_null` 分支），不代表 worker 一定 start 成功；能力鏈的最終結論由 RM 統一收斂。

本節寫政策、Ch 5 寫演算法：本節明訂「哪類模組走哪條路徑、`capability_map` 最終值為何」；RM 遍歷依賴 graph、在 `start()` 前後判定的具體流程屬 Ch 5 Resource Manager 實作章。

### `stop()` —— 完全下架

```python
async def stop(self) -> None: ...
```

- **呼叫者**：Resource Manager（arch.md §6.1 職責 4）
- **時機**：Process 停機階段，依 arch.md §6.2 反向順序
- **完成語意**：return 時所有長期資源已釋放——硬體 handle 關閉、library 實例銷毀、subscription 取消、背景 task 停止；所有 descendant thread / process / subprocess 已確認退出，不得留下 orphan
- **失敗處置**：raise exception；`main.py` log fatal 後繼續下一個模組的 `stop`（stop 期間錯誤不進 ERROR 狀態機）
- **冪等性**：要求。重複呼叫 `stop` 應無害（用於 shutdown 逾時後的最終清理）
- **與 `abort` 關係**：`stop` 不隱含 `abort`；若 worker 尚在 in-flight，Resource Manager 呼叫 `stop` 前 SM 應已完成 arch.md §6.5 收斂（含 `abort`）

### `abort()` —— Level 1 合作式中止（Perception / Action / Reasoner）

```python
async def abort(self) -> None: ...
```

- **呼叫者**：SM（arch.md §6.4 Level 1 cancel）
- **時機**：Session 收斂——`ActionCompleted(kind=rest)` / `InterruptRequested` / `ErrorOccurred` / `ShutdownRequested`（arch.md §6.5）
- **完成語意**：return 時該次呼叫（`perceive()` / `execute()`）佔用的短期硬體資源已釋放，對應 asyncio task 已進入結束流程；長期資源保留、worker 可再次接受呼叫
- **`CancelledError` re-raise**：worker / adapter 內若收到 asyncio cancellation，必須原樣 re-raise；此規則不代表 SM 可把 outer `task.cancel()` 當 Level 2 手段
- **適用範圍**：Perception / Action / Reasoner；InputSource / Adaptor 為常駐模組、不進 in-flight 集合，Protocol 不宣告 cancel 方法

### `force_abort()` —— Level 2 強制收斂

```python
@dataclass(frozen=True, slots=True)
class ForceAbortReport:
    destroyed_backends: tuple[str, ...] = ()

async def force_abort(self) -> ForceAbortReport: ...
```

- **呼叫者**：SM；只有 Level 1 `abort()` 逾時後呼叫
- **完成證明**：return 前所有 internal operation 已終止、descendant process 已 waitpid（或等價確認）退出、短期硬體資源已釋放；無可靠 native cancel 的 blocking backend 必須 child-process isolate
- **結果**：`destroyed_backends` 使用 Ch 5 定義的穩定 RM key；非破壞性或純 asyncio worker 回空 tuple
- **outer task**：`force_abort()` return 不是 handle removal 訊號。SM 仍只在 outer task done callback / 等價 completion notice 後移除 handle；worker 實作可等待 outer task 結束再 return，使 outer 卡住也計入同一個 Level 2 timeout
- **失敗**：`force_abort()` 未在上限內完成即直接 Level 3；禁止再對 outer task 呼叫 `task.cancel()` 冒充 internal container 的完成證明
- **recovery**：破壞 backend 時，由 SM 將 report 交 RM rebuild；Rest / Interrupt / Error 路徑在 recovery barrier 清除前保持 ERROR・Shutdown 不 rebuild

`ForceAbortReport` 是 SM、worker 與 RM 共用的控制流值，落於 `src/sbd/core/lifecycle.py`；不進 Event Bus，不是 Event。

**Shutdown 時的兩階段**：`ShutdownRequested` 觸發時，SM 對 in-flight worker 執行 arch.md §6.5 收斂（`abort()`，必要時 `force_abort()`），完成後 `main.py` 才對所有模組（含 InputSource / Adaptor / core）反向呼叫 `stop()`。Level 2 破壞 backend 時不 rebuild；完成 termination proof 後直接停機。

---

## 2.2 InputSource Protocol

```python
# src/sbd/input_events/base.py
from typing import Protocol

class InputSource(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def is_available(self) -> bool: ...
```

**職責（arch.md §2.4）**：常駐輸入源；運作中對 Event Bus 發布 Signal 事件（`ButtonPressed` / `ExternalMessageArrived` / `WakeWordDetected`）。

**事件產出對照**

| 實作 | 發布事件 | 事件產出時機 |
| :--- | :--- | :--- |
| `input_events/button/` | `ButtonPressed(button_id, duration_ms)`（短按）/ `ShutdownRequested()`（長按） | GPIO 訂閱者依按法和 config 門檻判定（arch.md §5.4）；短按 ≥ `short_press_min_ms` 且 < `long_press_min_ms`；長按 ≥ `long_press_min_ms` |
| `input_events/external_message/` | `ExternalMessageArrived(channel, arrived_at, message_id)` | 訊息入 buffer 時（arch.md §5.1） |
| `input_events/voice_wake/` | `WakeWordDetected(phrase, confidence)` | Wake daemon 透過 IPC 通知 |

**`is_available()` 契約（AR-Impl-5）**
- **語意**：InputSource 當前是否具備發布 Signal 的能力
- **同步方法**：查詢應即時 return，不觸發 IO；具體實作依 InputSource 類型：
  - `input_events/button/`：`start()` 成功後即 return True 直到 `stop()`（GPIO 註冊成功後常駐）
  - `input_events/external_message/`：常駐 buffer，`start()` 成功後恆為 True
  - `input_events/voice_wake/`：反映 IPC client 到 wake daemon 的連線狀態（daemon 若停 / socket 斷 $\rightarrow$ False）
- **呼叫者**：Resource Manager 於下游模組建立時可查；SM 不查（wake source 由 Signal 到達與否決定，非查詢決定）
- **不入 `capability_map`**：InputSource 屬 runtime-varying 能力（voice_wake daemon 可能斷線）；改由 Protocol 自帶查詢介面（§2.1.1 已定案）

**不宣告 `abort`**：InputSource 不進 SM in-flight 集合。

**Bus 存取**：InputSource 透過 constructor 直接取得 `EventBus` 實例（Q3 依賴注入方式）。

---

## 2.3 Perception Protocol

```python
# src/sbd/perception/base.py
from typing import Protocol

class Perception(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...

    async def perceive(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        timeout_seconds: float,
    ) -> None: ...
```

**職責（arch.md §2.6）**：把物理訊號翻譯成內部可用資料；透過注入的 Event Bus publish `PerceptionResult`。

**`perceive()` 契約**
- **呼叫者**：SM，於 PERCEPTION Entry 為每個選定 kind 呼叫（arch.md §4.6）
- **識別符**：SM 傳入 `(session_id, turn_id, correlation_id)`；worker publish 時原樣填回 `PerceptionResult` 對應欄位（Ch 1 §1.8）
- **Timeout 傳遞**：SM 傳入 `timeout_seconds`，worker 自我計時。到期後必須先合作式停止 operation 並釋放資源；成功才 publish `PerceptionResult(status="timeout", text=None, ...)`。若 cleanup 無法在 Level 1 上限內完成，改 publish 一個 `ErrorOccurred`、不發布 timeout Fact，並保持 in-flight 等待 SM 的 `force_abort()`
- **Fact 分支（Ch 1 §1.8）**：成功、timeout 或可翻譯失敗只 publish 一個 `PerceptionResult`；不可翻譯失敗由 worker 主動 publish 一個 `ErrorOccurred`，task completion 不重複補發；進入收斂後不 publish 正常終態 Fact
- **status 三值**：`{ok, timeout, error}` 皆為正常 publish 路徑（timeout / error 是資訊、不是 exception，見 arch.md §2.6 / §6.6）
- **P5 降級**：worker 內部部分失敗應優先降級產出可用 fact；`status=error` 表示已降級但仍無可用結果（arch.md P5）
- **Exception 處理**：不可翻譯錯誤由 worker publish `ErrorOccurred` 後讓 exception 逸出；`CancelledError` re-raise 不 publish（Ch 1 §1.8）
- **完成條件**：SM 記錄對應 terminal Fact 後仍須等待 `perceive()` task done、handle 移除；任一條件未成立都不得完成 PERCEPTION

**Kind 對照**

| 實作 | 輸入來源 | `PerceptionResult.text` 內容 |
| :--- | :--- | :--- |
| `perception/listen/` | `core/audio` 麥克風 | ASR 文字結果 |
| `perception/read/` | `input_events/external_message` buffer | 訊息文字（arch.md §5.1 消費機制） |
| `perception/look/` | `core/camera` | 視覺描述文字（詳細結果進 `extra`） |

**依賴注入**：worker constructor 直接接收所需 core 契約物件、library adapter 與 Event Bus instance（Ch 1 §1.8 Fact 傳遞模型的實作前提）。例：`Listen(audio: AudioHAL, asr: ASRAdapter, bus: EventBus)`。不注入 Resource Manager；由 Resource Manager 於建立階段完成裝配（arch.md §6.1 職責 1 / 5）。

---

## 2.4 Action Protocol

```python
# src/sbd/action/base.py
from typing import Any, Protocol

class Action(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...

    async def execute(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        payload: dict[str, Any],
    ) -> None: ...
```

**職責（arch.md §2.8）**：執行 action；透過注入的 Event Bus publish `ActionCompleted(kind, status, result)`。

**`execute()` 契約**
- **呼叫者**：SM，於 ACTION Entry 依 `LLMResponse.action_kind` 呼叫對應 worker（arch.md §4.6）
- **`payload`**：來自 `LLMResponse.action_payload`；schema 依 kind 分別定義（見 Ch 9）；SM 已於 THINK Exit 驗證通過
- **識別符**：SM 傳入 `(session_id, turn_id, correlation_id)`；worker publish 時原樣填回 `ActionCompleted`
- **無 timeout 參數**：與 `perceive()` 對照，`execute()` 不由 SM 傳入 timeout。理由：
  - `speak` 完成時間依合成文本長度自然決定
  - `tool` 為 fire-and-forget（arch.md §2.8），派發完成即回
  - `rest` 為使用者可感知收尾，完成時間由 UX 決定
  - 若需硬性中止（例：使用者觸發 `InterruptRequested`），走 arch.md §6.5 收斂機制（`abort`），非 timeout
- **Fact 分支（Ch 1 §1.8）**：成功或可翻譯失敗只 publish 一個 `ActionCompleted`；不可翻譯失敗由 worker 主動 publish 一個 `ErrorOccurred`，task completion 不重複補發；進入收斂後不 publish 正常終態 Fact
- **`status` 二值**：`{ok, error}`；`status=error` 觸發 SM 改用 `default_perceptions`（arch.md §4.8）
- **Exception 處理**：同 §2.3——不可翻譯錯誤 publish `ErrorOccurred` 後讓 exception 逸出；`CancelledError` re-raise 不 publish
- **完成條件**：SM 記錄 `ActionCompleted` 後仍須等待 `execute()` task done、handle 移除，才可離開 ACTION

**Kind 對照**

| 實作 | 職責 | Fire-and-forget |
| :--- | :--- | :--- |
| `action/speak/` | TTS 合成 + 播放 | 否（等播放完成才 return） |
| `action/tool/` | 命令式派發（開燈、發指令） | 是（派發完成即 return，實際結果由外部通道回傳） |
| `action/rest/` | 使用者可感知收尾（告別語、關螢幕、減燈） | 否 |

**依賴注入**：同 §2.3，constructor 接收所需 core 契約物件、library adapter 與 Event Bus（例：`Speak(audio: AudioHAL, tts: TTSAdapter, presenter: Presenter, bus: EventBus)`）。

---

## 2.5 Adaptor Protocol

```python
# src/sbd/adaptor/base.py
from typing import Protocol

class Adaptor(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def is_available(self) -> bool: ...
```

**職責（arch.md §2.9）**：對外通道；訂閱系統事件，把系統狀態對外具體化；並可能雙向承接外部觸發（`adaptor/mqtt` 接收後轉交 `input_events/external_message`）。

**訂閱範圍**：Adaptor 可訂閱 `StateChanged` 與 Worker Facts（`PerceptionResult` / `LLMResponse` / `ActionCompleted` / `ErrorOccurred`）——依 arch.md §3.2 表計，`adaptor` / `log` / `metrics` 皆為 observer；observer 對事件三類皆可訂閱。實際訂閱哪些事件由 adaptor 自定，不強制。

**`is_available()` 契約（AR-Impl-5）**
- **語意**：Adaptor 當前是否具備對外通訊的能力
- **同步方法**：查詢應即時 return，不觸發 IO；具體實作依 Adaptor 類型：
  - `adaptor/mqtt/`：反映 MQTT broker 連線狀態（連線中 $\rightarrow$ True；斷線 / 重連中 $\rightarrow$ False）
  - `adaptor/uart/`（未來）：反映串列埠開啟狀態
  - `adaptor/log/` / `adaptor/metrics/`（本地 observer）：`start()` 成功後恆為 True
- **呼叫者**：其他 adaptor 或應用層決定是否透過此通道對外時可查；SM 不查（SM 不感知對外通道）
- **不入 `capability_map`**：Adaptor 屬 runtime-varying 能力（連線可能斷線 / 重連）；改由 Protocol 自帶查詢介面（§2.1.1 已定案）

**不宣告 `abort`**：Adaptor 為常駐 observer / 對外通道，不進 SM in-flight 集合。

**Bus 存取**：透過 constructor 注入 `EventBus`；`start` 期間 subscribe，`stop` 期間 unsubscribe（滿足冪等）。

**外部訊息驗證位置**：依 arch.md §3.3 / §5.1，adaptor 內驗證格式、失敗於 adaptor 丟棄並 log warning；通過驗證後交給 `input_events/external_message`（`input_events` 分工歸屬非 adaptor）。

---

## 2.6 檔案落點總覽

```
src/sbd/
├── core/lifecycle.py       # ForceAbortReport 控制流值
├── input_events/base.py    # InputSource Protocol
├── perception/base.py      # Perception Protocol
├── action/base.py          # Action Protocol
└── adaptor/base.py         # Adaptor Protocol
```

`Protocol` 皆為 `typing.Protocol` 純介面宣告；不含具體實作、不含 mixin 或抽象基底類別。具體實作為子目錄下的 module（例：`perception/listen/listener.py`），由 Resource Manager 於建立階段裝配。

---

## 2.7 契約總覽表

| Protocol / 模組 | `start` | `stop` | `abort` | `force_abort` | 主要方法（皆 $\rightarrow$ None；Fact 透過 Bus publish） | 查詢介面 | in-flight |
| :--- | :---: | :---: | :---: | :---: | :--- | :--- | :--- |
| **InputSource** | $\checkmark$ | $\checkmark$ | $\times$ | $\times$ | ——（常駐 publish Signal） | `is_available()` | 否（常駐） |
| **Perception** | $\checkmark$ | $\checkmark$ | $\checkmark$ | $\checkmark$ | `perceive(session_id, turn_id, correlation_id, timeout_seconds)` | RM `capability_of(kind)` | 是 |
| **Action** | $\checkmark$ | $\checkmark$ | $\checkmark$ | $\checkmark$ | `execute(session_id, turn_id, correlation_id, payload)` | RM `capability_of(kind)` | 是 |
| **Reasoner**（具體 class） | $\checkmark$ | $\checkmark$ | $\checkmark$ | $\checkmark$ | `reason(session_id, turn_id, correlation_id, ...)` | 注入的 `capability_of(kind)` | 是 |
| **Adaptor** | $\checkmark$ | $\checkmark$ | $\times$ | $\times$ | ——（常駐訂閱 + 對外發布） | `is_available()` | 否（常駐） |

**查詢介面分類原則（AR-Impl-5）**：入 `capability_map`（RM `capability_of` 查詢）者為「啟動時決定的靜態能力」；InputSource / Adaptor 屬 runtime-varying，改由 Protocol 自帶 `is_available()`。詳見 §2.1.1「Capability Map 範圍」段。

---

## 2.8 Cognition Reasoner 呼叫契約

Cognition 現況為單一 reasoner，依 arch.md §2.1 不建立 `base.py` Protocol。但 SM 於 THINK Entry 需要一個明確的呼叫入口；本節定義 `cognition/reasoner.py` 對外 module-level 契約——不是 Protocol、不是 class 契約，而是具體 module 需要 export 的方法與其簽名。若未來加入第二種 cognition 實作（例：雲端 reasoner），再依 arch.md §2.1 引入 Protocol。

### Module 對外方法

`cognition/reasoner.py` module 提供一個 `Reasoner` class 實例，由 Resource Manager 建立與注入依賴（見 arch.md §6.1 職責 1）。實例 export 以下方法：

```python
# src/sbd/cognition/reasoner.py

class Reasoner:
    def __init__(
        self,
        llm: LLMEngineAdapter,               # Ch 2b LiteRT-LM adapter
        prompt_builder: PromptBuilder,
        bus: EventBus,
        capability_of: Callable[[str], bool],
        action_validator: ActionPayloadValidator,  # Ch 9 §7；與 SM 共用同一 instance
    ) -> None: ...

    async def start(self) -> None:
        """LLM engine warmup、prompt template 載入。"""
        ...

    async def stop(self) -> None:
        """釋放 LLM engine 資源；靜等。"""
        ...

    async def abort(self) -> None:
        """合作式中止當前 in-flight reason() 呼叫。"""
        ...

    async def force_abort(self) -> ForceAbortReport:
        """強制終止 internal container，必要時回報被破壞的 backend。"""
        ...

    async def reason(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        perception_results: tuple[PerceptionResult, ...],
        pending_message_count: int,
    ) -> None: ...
```

### `reason()` 契約

- **呼叫者**：SM，於 THINK Entry 呼叫（arch.md §4.6）
- **識別符**：SM 傳入 `(session_id, turn_id, correlation_id)`；reasoner publish `LLMResponse` 時原樣填回
- **`perception_results`**：本 turn 所有 perception worker 的 `PerceptionResult`（含 `status` $\in$ `{ok, timeout, error}`），順序由 SM 收集完成順序決定；reasoner 不假設順序有意義
- **`pending_message_count`**：本 turn 起始時 external_message buffer 內 pending 訊息數（來源見 arch.md §5.1 / §2.7）——只供 reasoner 決定 `next_perceptions` 是否含 `read`；不得傳入 `message_id`、payload或可反查內容
- **Fact 分支（Ch 1 §1.8）**：成功或可翻譯的 LLM 失敗只 publish 一個 `LLMResponse`；不可翻譯失敗由 reasoner 主動 publish 一個 `ErrorOccurred`，task completion 不重複補發；進入收斂後不 publish 正常終態 Fact
- **P5 降級**：LLM engine timeout / 解析失敗 / 拒答時，reasoner 應內部降級產出合理 `LLMResponse`（例：`action_kind="speak"` + apology text + `next_perceptions=("listen",)`）；不 raise
- **Exception 處理**：不可翻譯錯誤 publish `ErrorOccurred` 後讓 exception 逸出；`CancelledError` re-raise 不 publish（同 §2.3 / §2.4）
- **完成條件**：SM 記錄 `LLMResponse` 後仍須等待 `reason()` task done、handle 移除，才可離開 THINK

### Reasoner 可查 capability 範圍（AR-Impl-5）

Reasoner 於決定 `next_perceptions` 與 `action_kind` 時，可透過注入的 Resource Manager 查詢能力：

- **合法查詢 kind**：`perception kind`（`listen` / `read` / `look`）$\cup$ `action kind`（`speak` / `tool`）——與 reasoner 產出契約一致的 kind 粒度
- **不可查**：core 資源（`audio` / `display` / `camera` / `gpio`）、adaptor（`mqtt` / `uart` / ...）、input source（`voice_wake` / `button` / `external_message`）
- **設計意圖**：底層依賴鏈屬 RM 職責；reasoner 不感知「`capability_of("listen")=false` 是因為 audio null、還是 listen 自身 start 失敗、還是 config 標 optional 而未載入」——Null Object Pattern 的完整落實
- **查詢注入**：constructor 只注入 `capability_of: Callable[[str], bool]`，不注入完整 Resource Manager；RM 在組裝時傳入自己的查詢方法，讓 reasoner 只能存取架構允許的窄介面

### `abort()` / `force_abort()` 契約

- **`abort()`**：SM 的 Level 1 合作式停止；向 LLM adapter 發 cancel request，等 adapter 證明目前 operation 已停止並釋放短期資源
- **`force_abort()`**：Level 1 逾時後的 Level 2；LiTeRT-LM child 必須 terminate / kill 並 waitpid，回傳含 LLM backend key 的 `ForceAbortReport`
- **兩者都不可直接移除 SM handle**；outer `reason()` task done callback 才能移除
- **進入 cancel 後不 publish `LLMResponse`**；cancel 本身出錯才 publish `ErrorOccurred`
- **`force_abort()` 超時直接 Level 3**，不得改用 outer `task.cancel()`；破壞 LLM backend 時由 RM rebuild，recovery barrier 清除前保持 ERROR

### Lifecycle 與 in-flight 語意

- **In-flight 集合成員**：SM 呼叫 `reason()` 後、直到對應 asyncio task 真正 done 且 completion notice 使 handle 移除，reasoner 屬於 SM 的 in-flight 集合
- **單一實例**：reasoner 為 process 內單一 instance；同時只會有一個 in-flight `reason()`（THINK 狀態是 SM 序列狀態，不可能重入）
- **`start()` 必須等 LLM child完成Engine load、mandatory disposable pre-warm與cleanup後的`INFERENCE_READY`（wire可仍名`READY`）**；`ENGINE_LOADED`不可使start return或解除recovery barrier；`stop()` / `force_abort()` return前必須確認child與descendant已退出

### 依賴注入

- **`llm: LLMEngineAdapter`**：LiTeRT-LM adapter 抽象；具體介面於 Ch 2b 定義
- **`prompt_builder: PromptBuilder`**：本 turn 上下文組 prompt；於 Ch 2b 定義
- **`bus: EventBus`**：Fact publish 通道
- **`capability_of`**：RM 提供的窄查詢函式，只允許 perception / action kind
- **`action_validator: ActionPayloadValidator`**：Ch 9 §7 定義的 payload 驗證器；由 `main.py` 以同一個 `ToolRegistry` 建立後同時注入 SM（A 類依賴）與 Reasoner；validator 無 mutable call state，同一 instance 在兩處使用結果一致。此參數解決 Reasoner normalizer（P5 路徑）與 SM THINK Exit 共用驗證器的組裝缺口（IR_dev_M2_I）。

與 IR-I-01 對齊：reasoner 採用 Perception / Action 相同的分支模型——正常 / P5 路徑一個 terminal Fact，不可翻譯路徑一個 `ErrorOccurred`，cancel 路徑不發布正常 Fact；方法本身回傳 `None`。

---
