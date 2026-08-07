# Ch 7. External message buffer

屬於 implement.md 索引 | 對應 arch.md §3.3 / §4.4 ~ §4.8 / §5.1 | 狀態：定稿（IR-final 已通過（2026-08-01））
上游：Ch 1、Ch 2b、Ch 4。

## 0. 已確認判斷

| 編號 | 判斷點 | 已確認結論 |
| --- | --- | --- |
| ch7-Q1 | Buffer 的 owner 與落點 | `input_events/external_message` 擁有 store、ID 與 Signal；read worker只持窄 consumer |
| ch7-Q2 | Payload 的最小內部形式 | 驗證後正規化為非空 `text: str` + JSON-compatible metadata；raw wire payload 不入 buffer |
| ch7-Q3 | Item / read window 狀態模型 | item 為 `queued` -> `session/pending` -> `turn` -> `consumed`；每個 read window另有 `ACTIVE` -> `CLOSED`，close 後新訊息只能進 pending |
| ch7-Q4 | `begin_read()` 的批次邊界 | 原子開啟 ACTIVE window，並將指定 session 的 session/pending items 指派給 turn；arrival order 不變 |
| ch7-Q5 | Read 何時真正刪除 item | `consume_for_read()` 在同一 lock 內原子「取出 + 刪除 + 關閉 window」；worker publish 前已完成 consume mark |
| ch7-Q6 | Overflow 是否可淘汰 active-turn item | 不可；只淘汰 queued/session/pending，若全是 turn-owned 則退化為 drop-newest |
| ch7-Q7 | `reject` policy 如何回報 | `ingest()` raise `ExternalMessageBufferFull`；不分配 ID、不 publish Signal |
| ch7-Q8 | `flush_to_wake()` 發幾個 Signal | 每個未消費 item各重發一次，依 arrival sequence；publish 在 lock 外執行 |
| ch7-Q9 | Pending metadata 形式 | 固定為 arrival-ordered `tuple[MessageId, ...]`，不用 count |
| ch7-Q10 | 多 coroutine 一致性 | 單 event loop + `asyncio.Lock` / `Condition`；任何 native thread producer先排回 loop |

## 1. 範圍與非目標

### 1.1 本章包含

- 驗證後外部訊息的資料模型、狀態與唯一 `message_id` 生成。
- 有界 buffer、overflow policy 與 arrival-order 保證。
- Ch 4 `ExternalMessageControl` 與 read worker consumer API。
- `flush_to_wake` / `discard` 的原子性與 Event Bus 發布順序。
- payload-free pending metadata 與純軟體驗收。

### 1.2 本章不包含

- MQTT / UART wire schema、認證與 raw payload 驗證：adaptor / `docs/protocol.md`。
- SM 何時選 read、flush 或 discard：Ch 4。
- Read worker如何組合 `PerceptionResult`：Ch 2b。
- `buffer_max` / overflow policy 的設定載入：Ch 10。
- 外部訊息的跨 process durable queue：未納入架構；本 buffer 是 process memory。

## 2. 套件與 ownership

```
src/sbd/input_events/external_message/
├── __init__.py
├── models.py             # ExternalMessage / 狀態
├── buffer.py             # store + ExternalMessageControl
├── source.py             # ingest + InputSource lifecycle + Signal publish
└── consumer.py           # ReadMessageConsumer 窄介面
```

`ExternalMessageSource` 同時扮演：

- `InputSource`：`start()` / `stop()` / `is_available()`；
- 經驗證訊息入口：`ingest()`；
- `buffer owner`：持有 `ExternalMessageBuffer`；
- `Signal publisher`：成功入 buffer 後 publish `ExternalMessageArrived`。

Read worker只取得 `ReadMessageConsumer`，不取得 `ingest()`、`flush` 或 `discard`。StateManager只取得 `ExternalMessageControl`，不取得 payload reader。

## 3. 資料模型

```python
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

MessageState = Literal["queued", "session", "pending", "turn"]
ReadWindowState = Literal["active", "closed"]

@dataclass(frozen=True, slots=True)
class ExternalMessage:
    message_id: str
    channel: str
    arrived_at: float
    sequence: int
    text: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class _BufferedMessage:
    value: ExternalMessage
    state: MessageState = "queued"
    session_id: str | None = None
    turn_id: int | None = None

@dataclass(slots=True)
class _ReadWindow:
    session_id: str
    turn_id: int
    state: ReadWindowState = "active"
```

不保存：

- adaptor 的 socket / MQTT client object；
- bytes raw payload；
- secret、credential 或不可 JSON serialize 的物件；
- reasoner / SM 物件 reference。

`message_id = str(uuid4())`，由成功入 buffer 的那一刻生成。`sequence` 是 source instance-owned monotonic integer，只供 process 內穩定排序；不進 Event schema。

`text.strip()` 必須非空；`channel` 必須是 composition root 已註冊的非空名稱。`metadata` 只允許 JSON-compatible value，建立時做 recursive canonical copy以脫離caller原物件，之後依事件 nested payload 同樣視為唯讀。

## 4. Store 與索引

```python
class ExternalMessageBuffer:
    def __init__(
        self,
        *,
        max_items: int,
        overflow_policy: Literal["drop_oldest", "drop_newest", "reject"],
        logger: logging.Logger,
    ) -> None: ...
```

內部使用：

```python
_items: dict[str, _BufferedMessage]
_order: deque[str]
_read_windows: dict[str, _ReadWindow]  # 每個 session 最多保留目前 / 最近的 window
_lock: asyncio.Lock
_changed: asyncio.Condition           # 必須為 asyncio.Condition(self._lock)
_sequence_counter: itertools.count
```

- `_order` 僅保存依然存在的 ID，依 arrival sequence 排列。
- `dict` 提供按 ID 的 O(1) 調度；`deque` 提供 overflow / batch 的穩定順序。
- 所有多步驟 mutation 在同一 `lock` 內完成。
- `_changed` 必須以 `asyncio.Condition(self._lock)` 建立，與 store mutation 共用同一把 `_lock`。`asyncio.Condition.notify()` 要求呼叫者持有該 Condition 的 lock；共用 lock 才能使「mutation + notify」在同一 critical section 內原子成立，且 consumer 檢查 predicate 與 `wait()` 之間不會遺失喚醒。禁止 Condition 另建獨立 lock。
- 所有 `_changed.wait()` 必須置於 predicate loop：`while not <predicate>: await _changed.wait()`，predicate 檢查在持有 `_lock` 時求值（matching item 出現 / window CLOSED）。單次 `wait()` return 不視為條件成立。
- Event Bus publish、logger handler 與 worker Fact publish 都不得在 lock 內 await。
- 刪除 item 同時從 dict 移除；deque 可在同一 critical section 重建，buffer 最大容量由 `ExternalMessageConfig.buffer_max` 決定（預設 32），不需引入複雜 linked index。

## 5. Ingest 與 overflow

```python
class ExternalMessageSource:
    async def ingest(
        self,
        *,
        channel: str,
        text: str,
        metadata: Mapping[str, Any] | None = None,
        arrived_at: float | None = None,
    ) -> str: ...
```

流程：

1. source 未 started / 正在 stop -> raise `ExternalMessageUnavailable`。
2. 驗證並正規化資料，但尚不分配 ID。
3. 取得 buffer lock；若已滿，套用 overflow policy。
4. 若接受，分配 ID / sequence並 append。
5. 釋放 lock。
6. publish `ExternalMessageArrived(channel, arrived_at, message_id)`。
7. return ID。

Signal publish failure遵循 Ch 3 Event Bus fallback。Item 已在 buffer 中，不 rollback；如果 process 因 fatal bus failure 結束，in-memory item跟 process一同消失，不做「從 buffer 拿掉但外界以為已接受」的第二種不一致。

### 5.1 Overflow policy

| policy | 行為 |
| --- | --- |
| `drop_oldest` | 淘汰 arrival 最早且 state 不為 `turn` 的 item，再接受最新 item |
| `drop_newest` | 拒絕本次最新 item，產生dropped outcome並記 warning |
| `reject` | raise `ExternalMessageBufferFull` |

Public `ingest()` 對 `drop_newest` 也 raise `ExternalMessageDropped(policy="drop_newest")`，因此 caller 不會拿到不存在的 message ID。兩個 drop policy 與 reject 的差異是：

- drop policy 是預期容量政策，WARNING、不視為 source failure；
- reject 是 caller 可明確映射為協定層 busy / NACK 的控制流錯誤。

`drop_oldest` 不淘汰 state=`turn` 的 item；若所有 item 都已指派給 active read turn，退化成 drop-newest。淘汰 item後不發內部 Event；log 僅含 ID、channel、age，不含 text。

## 6. StateManager 控制介面

```python
class ExternalMessageControl(Protocol):
    async def assign_to_session(
        self,
        message_id: str,
        session_id: str,
    ) -> None: ...

    async def assign_to_turn(
        self,
        message_id: str,
        session_id: str,
        turn_id: int,
    ) -> None: ...

    async def mark_pending(
        self,
        message_id: str,
        session_id: str,
    ) -> None: ...

    async def begin_read(
        self,
        session_id: str,
        turn_id: int,
    ) -> tuple[str, ...]: ...

    async def close_read(
        self,
        session_id: str,
        turn_id: int,
    ) -> None: ...

    async def pending_ids(self, session_id: str) -> tuple[str, ...]: ...

    async def flush_to_wake(self) -> None: ...
    async def discard(self) -> None: ...
```

### 6.1 單則調度

- `assign_to_session`：只允許 `queued` -> `session`。用於 external-message wake 的第一則訊息。
- `mark_pending`：允許 `queued/session` -> `pending`；設定 session，清 turn。
- `assign_to_turn`：只有 target read window 為 ACTIVE 時才做 `queued/session/pending` -> `turn`。若相同 session / turn window 已 CLOSED，原子改存 `pending`、保留 session 並清除 turn；因此 consumer return 後、turn 尚未結束前到達的訊息不會滯留為無 consumer 的 turn-owned item。
- 已是相同 target 的重複指令為 idempotent no-op。
- 不同 session / turn 的重新指派是 `ExternalMessageOwnershipError`。
- 不存在的 ID 通常表示已被 overflow / discard；raise `ExternalMessageNotFound`。Ch 4 將此視為 stale input warning，不進 ERROR。

### 6.2 begin_read

在單一 lock 內：

1. 建立該 session / turn 的 ACTIVE read window；同一 session 已有另一個 ACTIVE window 是 `ExternalMessageOwnershipError`。
2. 找出指定 session 的 `session` / `pending` items。
3. 全部改成 `turn` 並填入 turn id。
4. 保留已經相同 session / turn 的 item。
5. return 本 turn 全部 ID，依 arrival order。
6. notify condition，喚醒 read consumer。

`begin_read` 不刪除 payload、不 publish Signal。空 batch 合法，read worker會依自己的 timeout產 `status=timeout`。

同一 session 的前一個 CLOSED window可由下一次 `begin_read` 取代；ACTIVE window 不可被取代。`flush_to_wake()` / `discard()` 會清除所有 window metadata。

### 6.3 close_read

`close_read(session_id, turn_id)` 是 StateManager取消 / phase cleanup用的窄控制：

1. 在 buffer lock內將matching ACTIVE window改為CLOSED。
2. 將尚未消費的matching `turn` items依arrival order改為 `pending`，保留session、清除turn。
3. notify waiter後return。

相同target已CLOSED是idempotent no-op；target不存在或不相符是 `ExternalMessageOwnershipError`。SM即使已取消read worker仍呼叫一次，覆蓋 begin_read() 完成但consumer尚未進入的窗口。

### 6.4 Pending metadata

`pending_ids(session_id)` 只回 state=`pending` 的 ID tuple，依 arrival order。不含 session-owned wake item、active turn item或任何 payload。方法是 snapshot，return 後新訊息可繼續到達；Reasoner只把它當作下一 turn是否選 read的提示。

## 7. Read consumer

```python
class ReadMessageConsumer(Protocol):
    async def consume_for_read(
        self,
        *,
        session_id: str,
        turn_id: int,
        timeout_seconds: float,
    ) -> tuple[ExternalMessage, ...]: ...
```

語意：

1. 在 `_lock` 下以 predicate loop 等待：`while` 無 matching turn item 且 window 未 CLOSED: `await _changed.wait()`，加上 `asyncio.timeout(timeout_seconds)` 包住整個等待。predicate 在持鎖時求值，故 `begin_read()` / `assign_to_turn()` 的 notify 不會在檢查與 wait 間遺失。
2. 成功路徑在同一 buffer lock內依 arrival order取出所有matching items，從 dict / deque刪除，並把matching read window改為CLOSED。
3. timeout路徑在同一 lock內先CLOSED，再把任何殘留matching turn item還原為 pending，最後return empty tuple。
4. coroutine收到cancel時必須在重新raise `CancelledError` 前，以不可被第二次 cancellation打斷的短critical section完成同一close / 還原；SM仍以§6.3 `close_read()` 作idempotent cleanup。
5. return immutable tuple；刪除不可rollback。

`consume_for_read()` 的「取出matching items」與「關閉window」是同一原子步驟，所以consumer return與新arrival的競態只有兩種合法線性化結果：

- `assign_to_turn()` 先取得lock：訊息成為turn-owned，由本次consumer取出。
- consume / timeout / cancel close先取得lock：後續 `assign_to_turn()` 看到CLOSED，將訊息存成pending，留給後續read。

不存在consumer已return但item仍被指派到舊turn的第三種狀態。

Read worker取得 tuple後：

- 將 text 依 arrival order以 `"\n"` 組合；
- `extra` 可放 `message_ids` / `channels`，但不得放完整 metadata中的 secret；
- 至少一則有效文字 -> publish `PerceptionResult(status="ok")`；
- timeout -> publish `status="timeout"`；
- ownership error / 資料全無效 -> publish `status="error"`。

Consume 在 terminal Fact 前完成，確保 Fact publish後同一訊息不會被下一 turn再次 請取。若 worker在 consume 後、Fact publish前 crash，訊息會遺失；這是 process-memory、at-most-once consumption 的明確語意，不做 rollback造成重複執行。

## 8. Flush 與 discard

### 8.1 flush_to_wake()

Ch 4 只在回到 IDLE 後呼叫。

1. lock 內選取所有未 consumed item。
2. 清除 session / turn ownership，state改 `queued`，並清除read window metadata。
3. 建立 (channel, arrived_at, message_id) snapshot。
4. 釋放 lock。
5. 依 arrival order逐一 publish `ExternalMessageArrived`。

`turn` item正常情況不應留到 rest；若存在，仍納入 flush，因 Ch 4 已確認原 operation完成或收斂。重發使用原 ID與原 arrived_at，不建立 duplicate item。

第一個重發 Signal使 SM由 IDLE進 WAKE；同批後續 Signal排入 inbox後會依 Ch 4 在 session 中標 pending。這正是 flush-to-wake 的既定機制。

### 8.2 discard()

在 lock 內先關閉所有ACTIVE window，再清空dict / deque與window metadata並notify waiter。Active read waiter醒來後得到空結果，再依cancel flag或timeout結束。Discard idempotent，不 publish Event。

Ch 4 的嚴重度規則維持：

```
discard > flush_to_wake > none
```

一旦 rest recovery期間升級為 error / interrupt / shutdown，最後只呼叫 discard。

## 9. Lifecycle

`start()`：

- 驗證 max items > 0；
- 初始化 lock / condition；
- 建立 buffer store 與 `ExternalMessageControl` 面，使其可被 RM 於 late-fill 注入 SM（見 Ch 5 §5.3）；
- 將 source標 available；
- 尚未 arm receiver / ingest 入口：`start()` return 只代表 store / control 就緒，adaptor receiver（外部訊息真正進 `ingest()` 的路徑）由 RM 在 late-fill SM control 之後才 arm。因此 SM 一定先持有 `ExternalMessageControl` 才可能收到第一個 `ExternalMessageArrived`。
- 不建立背景 dispatch task。

store / control 與 receiver 的兩段式啟動使 Ch 5 §5.3「先注入 control、後啟動 producer」有明確建置邊界；若 source 被 Ch 5 §4.5 coherence gate 降級停用，RM 不 arm receiver 並立即 `stop()` 此 store。

`stop()`：

- 標 unavailable，拒新 ingest；
- 呼叫 discard；
- 喚醒所有 waiter；
- idempotent。

`is_available()` 反映 source lifecycle / adaptor入口是否可用，不進 capability map。Adaptor runtime連線狀態仍由 adaptor自己的 `is_connected()` 表示。

## 10. 錯誤型別與 logging

```python
class ExternalMessageError(RuntimeError): ...
class ExternalMessageUnavailable(ExternalMessageError): ...
class ExternalMessageBufferFull(ExternalMessageError): ...
class ExternalMessageDropped(ExternalMessageError): ...
class ExternalMessageNotFound(ExternalMessageError): ...
class ExternalMessageOwnershipError(ExternalMessageError): ...
class ExternalMessageValidationError(ValueError): ...
```

- 驗證 / overflow / stale ID：WARNING 或 DEBUG，不 publish `ErrorOccurred`。
- Store invariant破壞、lock內不可能狀態：讓 exception逸出 source / read worker，由該 worker責任邊界翻譯。
- Log只記 metadata：`message_id`、`channel`、`state`、`session_id`、`turn_id`、`age`。
- 不記 text、raw payload、credential。

## 11. 驗收與測試

最低純軟體測試：

1. 成功 ingest 先存 item再 publish Signal，ID為 UUIDv4。
2. 空 text / 非 JSON metadata 在存入前拒絕。
3. 多訊息 arrival order跨 assign / pending / turn仍保持。
4. `begin_read` 原子移動指定 session items，不碰其他 session。
5. `pending_ids` 只回 pending metadata，不暴露 payload。
6. `consume_for_read` 在同一lock原子刪除matching item並關閉window；同一item 最多消費一次。
7. consume timeout關閉window、把殘留matching turn items還原pending，且不改 其他session / turn的item state。
8. drop-oldest不淘汰 turn-owned item；全為 turn-owned時退化 drop-newest。
9. drop-newest / reject都不分配 ID、不 publish Signal。
10. stale ID與跨 session重新指派可區分。
11. flush重設 ownership並按 arrival order逐一重發原 ID。