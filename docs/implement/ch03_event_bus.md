# Ch 3. Event Bus 實作

屬於 `implement.md` 索引 | 對應 `arch.md` §3.1–§3.4 / §6.4 / §6.7 | 狀態：定稿（IR-final 已通過（2026-08-01））

上游契約：Ch 1, AR-Impl-6 已解決，且不影響本章 Event Bus 契約。

## 0. 本輪判斷點

| 編號 | 判斷點 | 確認結論 |
| --- | --- | --- |
| ch3-Q1 | 單次 `publish()` 如何派送 | 依註冊順序逐一 `await`；不用 `gather()` |
| ch3-Q2 | 多個 concurrent publisher 是否全域排序 | 否；Bus 不加全域 lock / queue，只保證單次 `publish` 內的順序 |
| ch3-Q3 | 訂閱如何匹配事件型別 | 只做 `type(event) is subscribed_type` 的 exact match；無 wildcard / 繼承展開 |
| ch3-Q4 | `unsubscribe()` 如何避免 bound-method identity 問題 | `subscribe()` 回傳 opaque `subscription` token；以 token 解除訂閱 |
| ch3-Q5 | 派送中訂閱表被修改 | `publish` 起始時獲取 tuple snapshot；修改只影響下一次 `publish` |
| ch3-Q6 | 一般 handler exception 如何處理 | 先完成原事件其餘 handler，再為每個失敗 publish 一個 `ErrorOccurred`，避免 SM inbox 因 subscriber 順序出現因果顛倒 |
| ch3-Q7 | `ErrorOccurred` handler 再失敗如何交給頂層 | 不再 publish error；Bus latch 第一個 `FatalDispatchError` 並從目前 publish re-raise，已監督 `wait_fatal()` 的 `main.py` 必然收到 |
| ch3-Q8 | Handler 可否直接做網路 / 硬體 IO | 否；handler 只可同步 enqueue / 更新輕量 observer state，耗時工作移入模組自己的 task |
| ch3-Q9 | 重複訂閱與解除訂閱語意 | 同一 event type + handler 不得重複；解除未知 / 已解除 token 為 no-op |

## 1. 範圍與非目標

### 1.1 本章包含

- `EventBus.subscribe()`、`unsubscribe()`、`publish()` 與 fatal handoff API。
- 訂閱儲存結構、exact-type matching、派送順序與 snapshot 規則。
- 一般 handler exception 到 `ErrorOccurred` 的轉譯。
- `ErrorOccurred` handler exception 的不遞迴 fatal 收斂。
- Event Bus 自身可重複驗證的單元測試條件。

### 1.2 本章不包含

- 事件 dataclass 與 union：由 Ch 1 定義，落於 `src/sbd/core/events.py`。
- SM inbox 容量、guard 與狀態轉移：留 Ch 4。
- logger backend、輸出格式與 rotation：留 Ch 11。
- process shutdown / systemd 操作：Bus 只交出 fatal；`main.py` 如何結束由 Ch 11 定義。
- 跨 process / 跨機器訊息：留 `docs/protocol.md` 與 adaptor。

Event Bus 只承載內部 Event，不承載命令，也不提供 retry、persistence、priority、backpressure 或 replay。

## 2. 套件落點與公開 API

```
src/sbd/core/
├── events.py
└── event_bus/
    ├── __init__.py
    └── bus.py
```

`events.py` 由 Ch 1 擁有。`event_bus/__init__.py` 只 re-export：

```python
from .bus import EventBus, FatalDispatchError, Subscription

__all__ = ["EventBus", "FatalDispatchError", "Subscription"]
```

### 2.1 型別

```python
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import NoReturn, TypeVar

from sbd.core.events import ErrorOccurred, Event

E = TypeVar("E", bound=Event)
EventHandler = Callable[[E], Awaitable[None]]


@dataclass(frozen=True, slots=True, eq=False)
class Subscription:
    """EventBus 建立的 opaque identity token。"""


class FatalDispatchError(RuntimeError):
    def __init__(
        self,
        *,
        event: ErrorOccurred,
        handler_name: str,
        root_cause: Exception,
    ) -> None:
        self.event = event
        self.event_type = type(event).__name__
        self.handler_name = handler_name
        self.root_cause = root_cause
        super().__init__(
            f"fatal dispatch: event={self.event_type} handler={handler_name}"
        )
```

- `Subscription` 使用 object identity；呼叫者不得自行解構或建構 token。Bus 內部持有 handler 的 strong reference，直到 token 被解除訂閱。
- `FatalDispatchError` 明確保存 `event`、`event_type`、`handler_name` 與 `root_cause`；message 包含事件型別與 handler name。Bus 建構後以 `raise fatal from root_cause` 保存 `__cause__`，同一 instance 亦放入 fatal latch。

### 2.2 EventBus

```python
class EventBus:
    def subscribe(
        self,
        kind: type[E],
        handler: EventHandler[E],
        *,
        name: str | None = None,
    ) -> Subscription: ...

    def unsubscribe(self, subscription: Subscription) -> None: ...

    async def publish(self, event: Event) -> None: ...

    async def wait_fatal(self) -> NoReturn: ...
```

- `publish()` 是 async direct-call；完成代表本次事件與其必要 error fallback 已完成派送，不代表 subscriber 背後排入的工作已完成。
- `name` 用於 `ErrorOccurred.where="bus.dispatch.<name>"` 與 fatal log。Production 組裝應傳入穩定名稱；省略時由 handler 的 `__module__` / `__qualname__` 推導，主要供測試與簡單 observer 使用。
- `wait_fatal()` 平時永久等待；fatal latch 後 raise 同一個 `FatalDispatchError`。`main.py` 必須從啟動期起監督此 coroutine。
- Bus 沒有 `start()` / `stop()`；它不持有背景 dispatch task。

## 3. 訂閱生命週期

### 3.1 儲存模型

Bus 內部使用：

```python
@dataclass(slots=True)
class _SubscriptionRecord:
    token: Subscription
    kind: type[Event]
    handler: EventHandler[Event]
    name: str


_subscribers: dict[type[Event], list[_SubscriptionRecord]]
_by_token: dict[Subscription, _SubscriptionRecord]
```

`list` 順序就是派送順序。不得使用 `set`，避免順序不穩定。

### 3.2 subscribe()

1. `kind` 必須是 Ch 1 的具體事件 dataclass；`Event` / `WorkerFact` 等 union alias 不是 runtime 訂閱目標。
2. 同一 `kind` 下若已有相同 `handler`，raise `ValueError`；不靜默建立第二份。
3. 同一 `handler` 可分別訂閱多個 event type，每次取得不同 token。
4. 建立 record 後同時寫入 `_subscribers` 與 `_by_token`，回傳 token。

不提供「訂閱所有事件」wildcard。需要觀察多種事件的 adaptor 必須逐一註冊，讓可觀測範圍由 code review 直接判斷。

### 3.3 unsubscribe()

1. 從 `_by_token` pop record。
2. token 不存在時直接 return，滿足 `stop()` 冪等需求。
3. 從該 `kind` 的 list 移除 record；list 變空時刪除 dict key。

token 避免 `self.on_event` 每次取值可能產生不同 bound-method object 的問題，也讓同一個 handler 訂閱多種型別時能精確解除其中一項。

### 3.4 派送期間修改

`publish()` 取得：

```python
snapshot = tuple(self._subscribers.get(type(event), ()))
```

之後才開始呼叫 handlers。因此：
- 派送中新增的訂閱收不到本次事件。
- 派送中解除的訂閱若已存在 snapshot，仍收到本次事件一次。
- 修改於下一次 `publish()` 才生效。

Bus API 僅可在主 asyncio event-loop thread 使用。native thread 若要產生事件，必須以該 loop 的 thread-safe scheduling API 把 publish 排回主 loop，不得直接讀寫訂閱表。

## 4. Direct-call 派送

### 4.1 單次 publish

單次 publish 依 snapshot 順序逐一 await：

```python
failures: list[_HandlerFailure] = []

for record in snapshot:
    try:
        await record.handler(event)
    except Exception as exc:
        failures.append(_HandlerFailure(record, exc))
```

不用 `asyncio.gather()`，理由：
- 註冊順序可重複驗證。
- 避免多個 handler 同時修改各自 observer state 時產生不必要競態。
- fatal 與一般 exception 的因果順序更清楚。
- SM inbox handler 本來就必須快速 enqueue，不需要並行化。

### 4.2 Handler 快速返回契約

Handler 只能做 bounded、非阻塞工作：
- SM：`inbox.put_nowait(event)` 後 return。
- adaptor / metrics：寫入自己的 queue 或更新記憶體統計數後 return。
- logger observer：建立 log record；不得在 handler 內等待網路 sink。

Handler 不得：
- 等待網路、磁碟、模型或硬體 IO。
- 呼叫長時間 lock。
- 在 handler 內再次 `publish()` 一般業務事件。

需要耗時工作的 subscriber 自行擁有 queue 與 consumer task。Event Bus 不替 subscriber 建 task，否則會退化為隱藏的 background dispatch 模型。

### 4.3 Concurrent publisher

Bus 不加全域 dispatch lock。兩個 task 同時呼叫 `publish()` 時：
- 各自仍依自己的 snapshot 與註冊順序派送。
- 若 handler 內真的發生 suspension，兩次 publish 可能交錯。
- Bus 不提供跨 publish 的 total order。

SM 的 handler 以 `put_nowait()` 立即 enqueue；其 inbox 看到的順序就是 asyncio 實際呼叫 handler 的順序。任何模組不得依賴兩個 concurrent publisher 之間未被契約保證的先後。

### 4.4 Cancellation

Bus 只 catch `Exception`，不 catch `BaseException`：
- `asyncio.CancelledError` 原樣傳出，不轉成 `ErrorOccurred`。
- `KeyboardInterrupt` / `SystemExit` 原樣傳出。
- publisher 被 cancel 時，Bus 不保證尚未呼叫的 handler 會收到事件。

Worker 契約已要求進入 cancel 後不得 publish Fact；handler 快速返回契約則縮短 publish 中途被 cancel 的窗口。Bus 不使用 `asyncio.shield()`，避免 canceled publisher 留下脫離生命週期管理的派送 task。

## 5. Handler exception 與 fatal handoff

### 5.1 一般事件

一般事件的 handler exception 不阻止原事件其餘 subscribers：

1. 捕捉 exception 並記錄 `_HandlerFailure`。
2. 完成本次原事件 snapshot 的其餘 handlers。
3. 依 failure 發生順序，各 publish 一個：

```python
ErrorOccurred(
    where=f"bus.dispatch.{record.name}",
    error=repr(exc),
    exception_type=type(exc).__name__,
)
```

先完成原事件 fan-out，再發布 fallback，可確保 subscriber 註冊順序不會造成 SM 在尚未收到原事件前就先收到該事件的 dispatch error。

若 handler 自己自行 publish `ErrorOccurred` 後又 raise，Bus 仍為 raise 再產生一個 `ErrorOccurred`；不做去重。

**SM subscriber 與 inbox 順序**

SM 的 Event Bus callback 是薄殼，只負責 enqueue：

```python
async def on_event(event: Event) -> None:
    inbox.put_nowait(event)
```

callback 不執行 guard、不改變 SM state，也不呼叫下一個 worker。實際流程由獨立的 SM dispatch loop 從 inbox 取出事件後執行。對 terminal Fact，dispatch loop 只先記錄結果；必須收到 Ch 4 的 task completion notice、確認 handle 已移除，而且期間未進 ERROR，才可離開目前 operation：

```
SM inbox 取出 LLMResponse
 -> guard，記錄 terminal Fact
 -> reasoner handle 尚在 in-flight：暫緩 THINK Exit
 -> inbox 取出 reasoner completion notice
 -> 確認 Fact 已收到 AND task done/handle removed
 -> StateChanged(THINK -> ACTION)
 -> 呼叫對應 Action worker
```

因此 Q6 保護的是「進入 SM inbox 的事件順序」。假設 `LLMResponse` 的 subscribers 依序為 MQTT、SM、metrics，且 MQTT handler 失敗；若 Bus 立即在 MQTT failure 處 publish fallback，順序會變成：

```
publish LLMResponse
 -> MQTT handler exception
 -> 立即 publish ErrorOccurred
    -> SM enqueue ErrorOccurred
 -> 回到原事件 fan-out
    -> SM enqueue LLMResponse
```

SM inbox 會先有 `ErrorOccurred`、後有 `LLMResponse`，使衍生錯誤跑到原因之前。確認採用的延後 fallback 順序則是：

```
publish LLMResponse
 -> MQTT handler exception，暫存 failure
 -> SM enqueue LLMResponse
 -> metrics handler
 -> 原事件 fan-out 完成
 -> publish ErrorOccurred
    -> SM enqueue ErrorOccurred
```

SM dispatch loop 因而先記錄原 `LLMResponse`，再處理其派送錯誤。由於 worker 必須等整個 `bus.publish()`（含延後 fallback）完成後才能 return，task completion notice 不會早於該 fallback enqueue；SM 會先進 ERROR，不會過早啟動下一階段 Action。這同時維持原事件先於衍生錯誤的因果順序。

若失敗者正是 SM callback，且 `LLMResponse` 尚未 enqueue，Bus 仍先完成其他 subscribers，再 publish `ErrorOccurred`。SM 若能 enqueue 此 error，進入一般 ERROR recovery；若連 `ErrorOccurred` 都無法 enqueue，改走 Q7 fatal。

### 5.2 派送 ErrorOccurred

當目前 event 本身是 `ErrorOccurred`，且 Bus 呼叫其 subscriber callback 時再次發生 exception，不再建立第二個 fallback：

1. 建立 `FatalDispatchError`，以原 exception 為 cause。
2. 以 CRITICAL / FATAL 語意記錄 event type、handler name 與 traceback。
3. 若尚未 latch fatal，保存此 error 並設定 `_fatal_ready`；first failure wins。
4. 從目前 `publish()` raise 同一個 fatal，停止剩餘 `ErrorOccurred` subscribers。

Bus 不在此刻「呼叫 `wait_fatal()`」。`wait_fatal()` 是 `main.py` 從系統啟動期就開始監督的另一條通道；Bus 設定 fatal latch 後，已在等待的 `main.py` 才會被喚醒。

這條路徑不進 SM ERROR recovery；它直接接 `arch.md` §6.4 Level 3，由 `main.py` 結束 process。

### 5.3 Fatal latch

Bus 內部只需：

```python
_fatal_error: FatalDispatchError | None
_fatal_ready: asyncio.Event
```

- `wait_fatal()` await `_fatal_ready` 後 raise `_fatal_error`。
- latch 後若還有人呼叫 `publish()`，不再派送，立即 raise 已保存的 fatal。
- 多個 fatal 競爭時只保存第一個；後續 exception 可追加 critical log，不可覆蓋 root cause。
- `main.py` 不得只依賴 publisher task 的 exception；publisher 可能是 SM 未直接 await 的 worker task。fatal latch 是保證頂層必然可觀察的獨立通道。

完整時序：

```
一般 event handler exception
 -> Bus 完成原事件 fan-out
 -> Bus publish ErrorOccurred
    -> ErrorOccurred handler exception
    -> 不再 publish 第二個 ErrorOccurred
    -> 建立並 latch FatalDispatchError
    ├── 目前 publish() raise
    └── main.py 的 wait_fatal() 被喚醒並 raise
        -> main.py 結束 process
        -> systemd 重啟
```

兩條 fatal 傳遞路徑不可互相取代：
- 目前 `publish()` re-raise：立即停止已損壞的派送路徑。
- fatal latch / `wait_fatal()`：即使 publisher 是頂層未直接 await 的 worker task，也保證 `main.py` 得知系統必須退出。

## 6. Logging 邊界

Ch3 只固定 log 語意，不選 logger backend：

| 情境 | 語意 level | Bus 行為 |
| --- | --- | --- |
| 事件無 subscriber | WARNING | 記 event type 後 return |
| 一般 handler exception | ERROR 由產生的 `ErrorOccurred` observer 統一記錄 | Bus 不額外重複 traceback log |
| `ErrorOccurred` handler exception | CRITICAL / FATAL | Bus 自行記錄 traceback、latch fatal、raise |
| duplicate subscription | 不記 log | `subscribe()` raise `ValueError` |
| unknown unsubscribe token | 不記 log | no-op |

若一般 handler exception 產生的 `ErrorOccurred` 也沒有 subscriber，Bus 依一般規則記 WARNING。SM / logging observer 必須在任何 producer 啟動前完成訂閱；該啟動順序由 Ch 5 定義。

## 7. 實作骨架

```
EventBus.publish(event)
├── fatal 已 latch? ── yes ➔ raise saved FatalDispatchError
├── snapshot 為空? ── yes ➔ warning + return
├── event is ErrorOccurred
│   └── sequential dispatch
│       └── handler exception ➔ latch + raise fatal (不遞迴)
└── other Event
    ├── sequential dispatch, 收集 Exception
    └── 原事件 fan-out 完成後
        └── 依序 publish ErrorOccurred
```

內部 helper 建議：

```python
async def _dispatch_regular(
    self,
    event: Event,
    snapshot: tuple[_SubscriptionRecord, ...],
) -> None: ...


async def _dispatch_error(
    self,
    event: ErrorOccurred,
    snapshot: tuple[_SubscriptionRecord, ...],
) -> None: ...


def _trip_fatal(
    self,
    event: ErrorOccurred,
    record: _SubscriptionRecord,
    cause: Exception,
) -> FatalDispatchError: ...
```

分開 regular / error 路徑，避免用可失效的 recursion-depth flag 判斷是否應遞迴。

## 8. 驗收與測試

最低單元測試：

1. 同 event type 的 handlers 依註冊順序各收到同一 event object 一次。
2. 不同 event type 不互相收到；subclass 不觸發 base / 其他型別訂閱。
3. 無 subscriber 記 WARNING 且不 raise。
4. `subscribe()` 回 token；`unsubscribe()` 後不再收到，重複解除不 raise。
5. 同 kind + handler 重複訂閱 raise `ValueError`。
6. handler 在派送中 subscribe：新 handler 從下一次 publish 才收到。
7. handler 在派送中 unsubscribe：snapshot 中 handler 本次仍收到，下一次不收。
8. 一般 handler raise 不阻止其餘原事件 handler。
9. 一般 handler raise 後，產生欄位正確的 `ErrorOccurred`。
10. 多個一般 handler raise 時，fallback 依失敗發生順序發布。
11. `CancelledError` 原樣傳出，不產生 `ErrorOccurred`。
12. `ErrorOccurred` handler raise 時不遞迴；剩餘 error handlers 不執行。
13. fatal 同時從目前 `publish()` 與既已等待的 `wait_fatal()` raise。
14. `FatalDispatchError` 保存 event / event_type / handler_name / root_cause，且 `__cause__` 指向同一 root cause。
15. fatal 發生前、發生後才開始 `wait_fatal()` 都能取得同一 root cause。
16. fatal latch 後再次 publish 立即 raise，不再呼叫 handler。

測試不以 wall-clock sleep 判斷順序；使用 list、`asyncio.Event` 或明確 barrier。

## 9. 跨章同步與待確認

### 9.1 後續章節輸入

- Ch 4：SM subscriber 必須是 `put_nowait()` 薄殼，並保存 Subscription tokens。
- Ch 5：SM 與 logging observer 訂閱完成後，才啟動會 publish 的 producers。
- Ch 11：固定 production handler names、logger facade 與 `main.py` 監督 `wait_fatal()` 的方式。
