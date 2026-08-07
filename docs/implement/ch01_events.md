# Ch 1. 事件 dataclass 定義

屬於 implement.md 索引 | 對應 arch.md §3.2 / §3.3 | 狀態：定稿（IR-final 已通過（2026-08-01））

本章定義 arch.md §3.3 事件清單的 Python dataclass 具體欄位、型別與生成規則。所有 dataclass 使用 `@dataclass(frozen=True, slots=True)` —— 事件為不可變值物件，publish 後不允許修改。

事件唯讀行為契約：`@dataclass(frozen=True)` 只保護外層欄位；nested container (`PerceptionResult.extra` / `LLMResponse.action_payload` / `ActionCompleted.result` 皆為 `dict[str, Any]`) 依 Python 語意仍可變。本 codebase 明訂以下行為契約：
• Worker publish 事件後，該事件（含 nested payload）即為系統共享的唯讀值
• 任何 subscriber / observer / SM 不得就地修改事件的任何層級——包含 nested dict / list 的 mutation (`event.extra["new_key"] = ...` 屬違反)
• 需要衍生資料時，subscriber 必須產出新的 dict / 新事件；不重用同一物件
• 違反此契約會導致 direct-call bus 下游 subscriber 看到污染資料，且錯誤源難以追蹤

不引入強制機制：不使用 `types.MappingProxyType` / `frozendict` / `deep-copy` —— 這些會增加建構開銷或引入外部依賴。契約由 code review 與慣例維護；此約束等同 arch.md §3.2「事件為過去式事實」的實作面延伸。

## 1.1 共用型別與識別符

```python
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4
import itertools
import time

# 型別別名（僅供閱讀清晰，runtime 為 str / int）
SessionId = str        # UUIDv4 字串
TurnId = int           # session 內遞增，首 turn = 1
CorrelationId = int    # process 內 monotonic counter
MessageId = str        # UUIDv4 字串（由 external_message 產生）

# 識別符生成
def new_session_id() -> SessionId: return str(uuid4())
def new_message_id() -> MessageId: return str(uuid4())

# correlation_id : process 內 counter，但不使用 module-global 狀態。
# StateManager 於 __init__ 建立並持有自己的 counter :
class StateManager:
    def __init__(self) -> None:
        self._correlation_counter = itertools.count(1)

    def _new_correlation_id(self) -> CorrelationId:
        return next(self._correlation_counter)
```

識別符歸屬（arch.md §3.7 追蹤粒度）：

| 識別符 | 型別 | 生成者 | 生成時機 |
| :--- | :--- | :--- | :--- |
| `session_id` | UUIDv4 str | SM | WAKE Entry |
| `turn_id` | int | SM | PERCEPTION Entry ( session 內遞增，首 turn = 1 ) |
| `correlation_id` | int | SM | 每次呼 worker 前 counter 遞增 |
| `message_id` | UUIDv4 str | external_message | 訊息入 buffer 時分配 |

型別選擇理由
• UUIDv4 (`session_id` / `message_id`)：字串 36 字元、8-4-4-4-12 hex，例 `550e8400-e29b-41d4-a716-446655440000`。碰撞率視為零。適用於跨 process / 跨系統流通的識別符——`session_id` 可能寫入 log 供跨機器 debug；`message_id` 可能對接外部 MQTT / UART，UUID 是通用交換格式。
• int counter (`correlation_id`)：process 內 log 追蹤用途為主，counter 更短更好讀（例：`corr=42` vs `corr=550e8400-...`）。目前 (`session_id`, `turn_id`, `kind`) 已能唯一定位 SM→worker 呼叫，`correlation_id` 主要 log 可讀性；未來若同 turn 同 kind 需多次呼叫，counter 仍能區辦。
• int (`turn_id`)：session 內遞增，人眼可讀 `turn=1, 2, 3 ...`。

## 1.2 事件基底

所有事件不繼承共同基類類別——union 型別已足供靜態檢查，繼承會迫使 dataclass frozen 屬性統一而失彈性。事件族群以 `typing.TypeAlias` 宣告的 union 表達；因 union 需在所有事件 dataclass 定義之後才能引用，實際 TypeAlias 定義集中於 §1.6。本節僅列語意分組：

| 族群名 | 成員 | 語意 |
| :--- | :--- | :--- |
| WorkerFact | `PerceptionResult` / `LLMResponse` / `ActionCompleted` / `ErrorOccurred` | SM 用來驅動狀態轉移或收斂的事實類事件；發布者依事件種類而異 |
| StateBroadcast | `StateChanged` | SM 唯一發布的狀態廣播 |
| Signal | `ButtonPressed` / `ExternalMessageArrived` / `WakeWordDetected` / `InterruptRequested` / `ShutdownRequested` | 外部輸入或系統訊號 |
| Event | 上述三族群之聯集 | 通用事件參數型別（bus 介面、subscriber callback 參數） |

## 1.3 Worker Facts

`PerceptionResult` ( arch.md §3.3 / §2.6 )

```python
@dataclass(frozen=True, slots=True)
class PerceptionResult:
    kind: Literal["listen", "read", "look"]
    status: Literal["ok", "timeout", "error"]
    text: str | None                  # ok 時必為非 None；timeout / error 時可 None
    extra: dict[str, Any] = field(default_factory=dict)
    session_id: SessionId = ""
    turn_id: TurnId = 0
    correlation_id: CorrelationId = 0
```
• `text`：主結果——listen / read 為 ASR / 文字結果；look 為視覺描述文字（詳細結果進 `extra`）
• `extra`：kind-specific 額外資料（如 look 的 bounding boxes、listen 的 confidence）
• SM 於 Guard Step 2 驗證 (`session_id`, `turn_id`) 匹配當前追蹤

`LLMResponse` ( arch.md §3.3 / §2.7 )

```python
@dataclass(frozen=True, slots=True)
class LLMResponse:
    action_kind: Literal["speak", "tool", "rest"]
    action_payload: dict[str, Any]            # schema 依 action_kind，見 Ch 9
    next_perceptions: tuple[str, ...]         # `action_kind` ∈ {"speak", "tool"} 時必須非空
    session_id: SessionId = ""
    turn_id: TurnId = 0
    correlation_id: CorrelationId = 0
```
• `next_perceptions` 為 `tuple` 而非 `list` —— frozen dataclass 內部不可含 mutable
• SM 於 THINK Exit 驗證 ( arch.md §4.6 )：`action_kind` 合法、`next_perceptions` 非空條件、`action_payload` schema

`ActionCompleted` ( arch.md §3.3 / §2.8 )

```python
@dataclass(frozen=True, slots=True)
class ActionCompleted:
    kind: Literal["speak", "tool", "rest"]
    status: Literal["ok", "error"]
    result: dict[str, Any] = field(default_factory=dict)
    session_id: SessionId = ""
    turn_id: TurnId = 0
    correlation_id: CorrelationId = 0
```
• `result`：worker 產出的補充資訊（例：speak 的實際播放秒數、tool 的派發回執）
• `status=error` 為 P5 降級結果，SM 依 arch.md §4.8 改用 `default_perceptions`

`ErrorOccurred` ( arch.md §3.3 / §6.6 )

```python
@dataclass(frozen=True, slots=True)
class ErrorOccurred:
    where: str               # e.g. "perception.listen", "bus.dispatch.<handler>"
    error: str               # exception repr 或明確錯誤訊息
    exception_type: str | None = None   # exception class name，供 log filtering
```
• 無 `severity` 欄位 ( arch.md §3.2 )
• 無 `session_id` / `turn_id` —— `ErrorOccurred` 不參與 Guard Step 2 ID 驗證 ( arch.md §3.6 )
• `where` 命名慣例：`<layer>.<module>[.<sub]`，例如：`perception.listen`、`action.speak`、`bus.dispatch.state_manager_inbox`

## 1.4 State Broadcast

`StateChanged` ( arch.md §3.3 / §4.5 )

```python
State = Literal["IDLE", "WAKE", "PERCEPTION", "THINK", "ACTION", "ERROR"]

@dataclass(frozen=True, slots=True)
class StateChanged:
    old: State
    new: State
    at: float = field(default_factory=time.monotonic)
```
• SM 為唯一 publisher ( arch.md §3.2 )
• `at`：monotonic 時間戳，供 observer 排序 / metrics

## 1.5 Signals

`ButtonPressed` ( arch.md §3.3 )

```python
@dataclass(frozen=True, slots=True)
class ButtonPressed:
    button_id: str
    duration_ms: int
```
• `button_id`：對應 config 中定義的邏輯按鈕名稱（例："conversation"、"volume_up"）
• `duration_ms`：短按 / 長按由訂閱者內部依此判定 ( arch.md §5.4 )

`ExternalMessageArrived` ( arch.md §3.3 / §5.1 )

```python
@dataclass(frozen=True, slots=True)
class ExternalMessageArrived:
    channel: str             # e.g. "mqtt", "uart"
    arrived_at: float        # monotonic 時間戳
    message_id: MessageId
```
• 僅 metadata —— payload 由 external_message 持有
• `message_id` 由 external_message 產生，SM 只轉發不解讀

`WakeWordDetected` ( arch.md §3.3 )

```python
@dataclass(frozen=True, slots=True)
class WakeWordDetected:
    phrase: str
    confidence: float        # 0.0 - 1.0
```

`InterruptRequested` / `ShutdownRequested` ( arch.md §3.3 / §4.7 )

```python
@dataclass(frozen=True, slots=True)
class InterruptRequested:
    pass

@dataclass(frozen=True, slots=True)
class ShutdownRequested:
    pass
```
• 無資料欄位——語意由 kind 本身承載
• Frozen dataclass 允許 empty class

## 1.6 事件族群 TypeAlias

依 §1.2 分組，於所有 dataclass 定義後宣告實際 union 型別：

```python
from typing import TypeAlias

WorkerFact: TypeAlias = PerceptionResult | LLMResponse | ActionCompleted | ErrorOccurred
StateBroadcast: TypeAlias = StateChanged
Signal: TypeAlias = (
    ButtonPressed
    | ExternalMessageArrived
    | WakeWordDetected
    | InterruptRequested
    | ShutdownRequested
)
Event: TypeAlias = WorkerFact | StateBroadcast | Signal
```

使用場景
• Bus 介面：`publish(event: Event) -> None`、`subscribe(kind: type[Event], handler: Callable[[Event], Awaitable[None]])`
• SM 內部：subscriber callback 參數型別、guard 過濾函式
• 靜態檢查：mypy / pyright 對 `isinstance(event, WorkerFact)` 需要 union 型別；字串 forward ref 不可行

注意：Signal 的成員 `InterruptRequested` / `ShutdownRequested` 是無資料 dataclass；union 中允許 empty class（見 §1.5）。

## 1.7 事件內部無版本化

arch.md §3.3 明定：內部事件無版本化需求（單 process、direct-call、一起 build 一起部署）。因此本章 dataclass 不含 `version` / `schema_version` 欄位。加欄位即改 code。

跨 process wire format（wake daemon IPC、對外 MQTT topic）需版本化，屬 `docs/protocol.md`。

## 1.8 事件建構慣例

正常終態 Fact 的單一來源：`PerceptionResult`、`LLMResponse`、`ActionCompleted` 只由執行該 operation 的對應 worker，透過注入的 Event Bus publish；成功、timeout 或 P5 可翻譯失敗路徑恰好一個，cancel 路徑不發布。SM 只從 inbox 消費，不接受工作方法回傳的 Fact；工作方法 (`perceive()` / `execute()` / `reason()`) 回傳 `None`。

`ErrorOccurred` 的發布者：`ErrorOccurred` 不是「只由 worker 發布」的正常終態 Fact；worker、HAL 與 Event Bus 均可依 arch.md §3.4 / §6.7 在各自責任邊界發布。已由 worker 翻譯並成功發布的同一個錯誤，不得再由同一路徑重複補發；Event Bus 對 subscriber exception 的 fallback 是另一個明確錯誤來源，不做跨來源去重。

Fact 與 task completion 是兩個條件：正常 worker operation 完成時，對應終態 Fact 已收到與 outer task 真正 done / handle 已移除可能分開到達。StateManager 在兩者皆成立前只記錄結果，不得離開目前 operation 或啟動下一個 worker。Fact 先到時，由 Ch 4 定義的 task done callback / internal completion notice 觸發重新檢查。worker 必須 `await bus.publish(...)`；因此該次 publish 衍生的 `ErrorOccurred` fallback 有機會在 publisher task done 前進入 SM inbox。

Exception 翻譯位置：worker 內以 try/except 處理內部錯誤——
• 可翻譯（P5 降級後仍無可用結果）→ 產出 `PerceptionResult(status="error")` / `ActionCompleted(status="error")` publish；正常 return
• 不可翻譯（worker 邏輯異常、library crash、`CancelledError` 除外）→ 由 worker 於 except 分支 publish 一個 `ErrorOccurred(where="<layer>.<module>", error=repr(exc), exception_type=type(exc).__name__)`，然後讓 exception 逸出至 asyncio task；Ch 4 的 task completion 處理只記錄 / 收割該 exception，不再重複發布同一個 `ErrorOccurred`
• `CancelledError` 必須 re-raise、不 publish 任何 Fact ( arch.md §6.3 / §6.7 )

識別符來源：SM 於呼叫 worker 時傳入 (`session_id`, `turn_id`, `correlation_id`)；worker 於產出 Fact 時原樣填回。Worker 自身不生成識別符。

```python
# SM 內建構 StateChanged
event = StateChanged(old="IDLE", new="WAKE")
# `at` 自動填入 time.monotonic()
await self.bus.publish(event)

# worker 內 publish Fact——只此一次，方法本身 return Fact
result = PerceptionResult(
    kind="listen",
    status="ok",
    text="開燈",
    session_id=self.session_id,     # constructor / call args 傳入
    turn_id=self.turn_id,
    correlation_id=self.correlation_id,
)
await self.bus.publish(result)
# 隨後方法 return None；SM 仍須等 task done completion notice 才能轉狀態
```

識別符欄位預設為 `""` / `0`：允許測試中構造事件不必逐一填識別符（字串型別預設 `""`、int 型別預設 `0`），SM 收到後於 Guard Step 2 依實際值判定。

## 1.9 事件位置

Python 檔案落點：

`src/sbd/core/events.py`    # 本章所有 dataclass 集中於此

理由：事件為跨模組共享的貫穿性契約，集中一檔便於 review 與 import；不散置於各生命週期層目錄。
