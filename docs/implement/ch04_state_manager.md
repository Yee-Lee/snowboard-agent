# Ch 4. State Manager 實作

關於 implement.md 索引 | 對應 arch.md §3.5～§3.7 / §4 / §5.1～§5.2 / §6.3～§6.5 | 狀態：定稿（IR-final 已通過（2026-08-01））

上游契約：Ch 1、Ch 2、Ch 3。AR-Impl-7 已 Confirmed：THINK Exit 壞 `LLMResponse` / 剔除未註冊 kind 後空清單走 §3.2 SM 自檢 ERROR 路徑（非 process 崩）。IR-IV-01（第 IV 輪）：§6.4 THINK Exit 對 speak/tool 的 `next_perceptions` 做正規化（剔除未註冊 kind + 去重，同屬 arch.md §2.7 授權的 SM 正規化，degrade 不 ERROR）；rest 完全忽略 `next_perceptions`（arch.md §2.7 / §4.6）。

## 0. 已確認判斷

| 編號 | 判斷點 | 已確認結論 |
|---|---|---|
| ch4-Q1 | SM inbox 是否有容量上限 | 使用單一 unbounded `asyncio.Queue`；Event Bus callback 必須 `put_nowait()` 且不可丟事件 |
| ch4-Q2 | task done 如何回到單軌 dispatch loop | done callback 只 enqueue private `_TaskCompleted`；callback 不改 in-flight、不跑狀態轉移 |
| ch4-Q3 | terminal Fact 與 task done 如何 join | 以 `correlation_id` 對應 `InFlightRecord`；Fact 先記錄，task done 才移除 handle，兩者成立才前進 |
| ch4-Q4 | worker task 無 terminal Fact 就結束如何處理 | cancel 中盤合法，非 cancel 且正常 return 視為 fatal contract violation；raise 路徑必須優先使 SM 進 ERROR，否則 fatal |
| ch4-Q5 | Ch 6 cancel 是否在 dispatch loop 外另開狀態機 | 否；dispatch loop await 單次 `converge()`，Ch 6 封裝 Level 1 / 2 / 3，completion notices 仍排回同一 inbox |
| ch4-Q6 | recovery 完成如何喚醒 ERROR Exit | SM 為 Ch 5 `RecoveryTicket` 建 waiter task；done callback enqueue private `_RecoveryCompleted`，不走 Event Bus |
| ch4-Q7 | rest destructive recovery 何時時 flush-to-wake | 保留原 trigger 的 buffer policy；先在 ERROR 等 recovery，回 IDLE 後才 `flush_to_wake()`，避免訊息在 ERROR 被拒絕 |
| ch4-Q8 | voice wake 與 listen 的麥克風切換 | 若 voice-wake 已啟動，late-fill 窄 `WakeListenerControl.suspend()/resume()/ensure_released()`；WAKE Entry suspend，真正回 IDLE 後 resume；未啟動時為 None。suspend 失敗改以 `ensure_released()`（終止 daemon + exit proof）取得麥克風釋放證明才 listen；連釋放都無法證明則阻擋本次 transition 並 fatal（單一 mic owner 為硬性不變量） |
| ch4-Q9 | StateManager 自身異常如何處理 | SM 不 publish `ErrorOccurred`，也不自行進 ERROR；dispatch task exception 交 `main.py`，直接結束 process |

## 1. 範圍與非目標

### 1.1 本章包含

- `StateManager` constructor、`start()` / `stop()` / `wait_stopped()`。
- Event Bus exact-type subscriptions 與 unbounded internal inbox。
- public Event guard、private completion notice dispatch。
- session / turn / correlation state、in-flight record 與雙完成 join。
- IDLE / WAKE / PERCEPTION / THINK / ACTION / ERROR 的可實作 entry / exit 演算法。
- Ch 5 recovery 與 Ch 6 convergence 的窄控制流介面。
- 可重複驗證的單元測試條件。

### 1.2 本章不包含

- Event Bus 派送：Ch 3。
- worker / adapter 內部取消：Ch 2b。
- Level 1 / 2 timeout 與 trigger matrix 的演算法：Ch 6。
- Resource Manager 建置 / recovery 實作：Ch 5。
- external-message buffer 內部資料結構：Ch 7。
- action payload 的完整 schema：Ch 9。
- config 欄位與實際秒數：Ch 10。

SM 對外仍只 publish `StateChanged`；private inbox item 不是 Event、不進 `core/events.py`，不會被 observer 看到。

## 2. 套件與窄依賴

```
src/sbd/core/state_manager/
├── __init__.py      # re-export StateManager / fatal contract errors
├── manager.py       # lifecycle 、 dispatch loop 、 state entry/exit
└── models.py        # private inbox item 、 SessionContext 、 InFlightRecord
```

不為六個狀態各自建 class。狀態數固定且共享大量 session data；以一個 manager 加私有 `_enter_*()` / `_try_progress()` 可讓 ownership 與轉移順序集中可見。

StateManager constructor 只收介面：

```python
class StateManager:
    def __init__(
        self,
        *,
        bus: EventBus,
        workers: WorkerCatalog,
        converger: SessionConverger,       # Ch 6
        recovery: RecoveryControl,         # Ch 5
        action_validator: ActionPayloadValidator,  # Ch 9
        wake_ack_seconds: float,
        perception_timeouts: PerceptionTimeouts,   # Ch 10 §5，per-kind immutable policy
        default_perceptions: tuple[str, ...],
    ) -> None: ...

    # late-fill：由 RM 於對應 producer record started=True 後`arm receiver 前呼叫 ( Ch 5 §3.5 )
    def set_external_message_control(self, control: ExternalMessageControl) -> None: ...
    def set_wake_listener(self, control: WakeListenerControl | None) -> None: ...
```

external_messages 與 wake_listener 不進 constructor：它們來自晚於 SM 的 producer（ExternalMessageSource / voice_wake InputSource），若放 constructor 會違反 Ch 5 §3.3 scoped resolver「只取已 READY managed instance」。兩者改由上列 one-shot setter late-fill：

- one-shot：每個 setter 只允許成功呼叫一次。`set_external_message_control()` 重複呼叫、或傳入 None -> raise `StateManagerWiringError` ( composition bug，fatal )；`set_wake_listener()` 允許以 None 表示「voice-wake 未啟用」，但同樣只可呼叫一次，重複呼叫 raise。
- producer arm 前 guard：兩個 producer 都在 arm receiver（開始 publish Signal）前由 RM 完成 late-fill（Ch 5 §3.5 B / §4.2 step 7）。SM 進入任何會觸發 external / wake Signal 的路徑前，`_external_messages` 必為 非 None；若 dispatch loop 收到 external / wake Signal 時對應 control 仍為 None，代表 RM arm 順序錯誤，raise `StateManagerWiringError` ( fatal )。`_wake_listener` 為 None 是合法「未啟用」狀態，§2.2 gate 據此略過 suspend / resume。
- 過晚呼叫：setter 在 `_dispatch_ready` 之後、producer arm 之前呼叫皆合法（此窗口內尚無對應 Signal 進 inbox）；`stop()` / shutdown 後呼叫 raise。

`perception_timeouts` 是 Ch 10 §5 的 immutable `PerceptionTimeouts(listen, read, look)`；SM 在 PERCEPTION Entry 建立每個 worker task 時，依該 worker 的 kind 取得對應值傳給 worker 方法（Ch 2 / 2b 規定每個 perception 收自己的 timeout_seconds）。SM 以固定 kind->field 對映（listen / read / look）查值；kind 集合與 Ch 10 schema 一致，unknown kind 在 §6.3 選擇 perception 階段即因未註冊被拒（不會默默退回錯誤 timeout）。SM 不再持有單一 scalar perception_timeout_seconds。

- `WorkerCatalog` 是 RM 組裝填入的 catalog；SM 不 import backend class。
- `RecoveryControl` 不暴露完整 RM factory / registry。
- Reasoner 的 capability 查詢由 RM 直接注入 reasoner，不經 SM 轉送。
- `ExternalMessageControl` 的最終 Protocol 落腳點 Ch 7 承接；`WakeListenerControl` 的 Protocol 與語意由本章 §2.1 正式定義（SM 是唯一 consumer）。兩者皆由 RM late-fill setter 注入（見上方 setter 說明與 Ch 5 §3.5 B），不進 constructor。voice-wake 未 start 時 `set_wake_listener(None)`，不建立 Null InputSource。

### 2.1 WakeListenerControl 契約

`WakeListenerControl` 是主 process 對獨立 wake daemon ( arch.md P4 / §2.4 / §5.2 ) 的窄控制介面。它不共享 daemon 的 Python 物件，只暴露可序列化的控制動詞；wire schema 見 `docs/protocol.md` ( 延後產出 )。

```python
class WakeListenerControl(Protocol):
    async def suspend(self) -> None: ...
    async def resume(self) -> None: ...
    async def ensure_released(self) -> None: ...
```

- Owner / 落腳：實作層 `input_events/voice_wake` 的 IPC client ( arch.md §2.4 )；由 Resource Manager 於 INPUT_PRODUCER phase 建立 `voice_wake` InputSource 後，把 control late-fill 給 SM ( `set_wake_listener()` )。SM constructor 不接收 daemon 連線細節。RM 對 SM 的注入採用 `WorkerCatalog` 相同的「late fill」模式（見 Ch 5 §3.5），因此 SM early-start 不需要在 constructor 持有 daemon instance。
- `suspend()` 完成語意：return 代表 daemon 已停止錄音並釋放 ALSA 裝置，listen 可安全獨佔麥克風。此為可等待、可失敗的動詞：IPC round-trip ACK 成立才 return。
- `ensure_released()` 完成語意 ( release proof )：return 代表 daemon 確定不再持有麥克風——以「已收到 stop ACK」或「daemon process 已經 exit proof ( `waitpid()` 等價 )」之一為準。此為 suspend 失敗後的強制釋放動詞：即使 cooperative `suspend()` timeout / 斷線，`ensure_released()` 仍須透過終止 daemon 取得單一 owner 保證。它可 raise `WakeListenerControlError` ( 連終止都無法證明釋放 )。
- `resume()` 完成語意：return 代表 daemon 已重新開始偵測喚醒詞。readiness 以 ACK 表示；SM 只在真正回 IDLE 後呼叫。
- 冪等：重複 `suspend()` / `ensure_released()` ( 已釋放 ) 或重複 `resume()` ( 已 active ) 為 no-op ACK，不 raise；涵蓋 recovery / shutdown 期間可能的重入。
- Timeout：control 內部對每次 IPC 套用 daemon-control timeout ( 值見 Ch 10 `input_sources.voice_wake` )；逾時 raise `WakeListenerControlError`。
- 失敗政策：`voice_wake` 為 optional InputSource ( Ch 10 §58 )，故 daemon 控制的功能性失敗 ( `resume()` 失敗、或 daemon 永久斷線 ) 本身以 degrade-not-crash 處置，不進 ERROR / fatal。但「listen 開始前 daemon 是否已釋放麥克風」是單一 mic owner 的硬性不變量 ( arch.md §5.2 )：§2.2 gate 在放行 listen 前必須先取得 release proof ( 見下 )；只有在證明釋放後才可降級成 listen 獨佔。不得在無釋放證明時放行 listen。
- Shutdown：SM shutdown 不特別 resume；daemon 由 RM reverse stop 一併停止。

### 2.2 Suspend / resume gate

SM 對 `wake_listener` 的呼叫集中於 helper，統一以「先取得麥克風釋放證明、才放行 listen」為不可退讓條件（IR-III-01 完成條件 3）：

suspend gate ( WAKE Entry, listen 取得 `frames()` 之前 )

```
若 _wake_listener is None -> 直接 return ( 未啟用 voice-wake，主 process 獨佔麥克風 )
若 _wake_control_released 為 True -> 直接 return ( 已證明釋放 )
嘗試 cooperative : await suspend()
成功 -> _wake_control_released = True ` return ( release proof 成立 )
raise WakeListenerControlError / IPC 例外 ( timeout / 斷線 ) :
    log WARNING ( cooperative suspend 失敗，升級強制釋放 )
    嘗試強制 : await ensure_released()
    成功 -> _wake_control_released = True ` log WARNING ( daemon 已終止/釋放 ) ` return
    raise -> 連釋放都無法證明 : **不放行 listen**
            設 _wake_control_failed = True，阻擋本次 WAKE->PERCEPTION listen 路徑，
            raise 交 §8 fatal ( 無法保證單一 mic owner，屬硬性不變量違反 )。
```

resume gate ( 回 IDLE 、 in-flight 空後 )

```
若 _wake_listener is None 或 _wake_control_failed -> 直接 return
否則 await resume() ; 捕捉 WakeListenerControlError / IPC 例外時
設 _wake_control_failed = True ` log WARNING ` return ( 不 raise ` 不進 ERROR )
```

- 因此在 daemon 正常時「suspend ACK 先於 listen」成立；suspend 失敗改由 `ensure_released()` 取得釋放證明後才 listen；連釋放都證明不了時阻擋 listen 並 fatal，絕不讓兩個 process 同時持有 ALSA 裝置。
- `resume()` 是回復 daemon 偵測的功能性動作，失敗只降級 ( wake 詞偵測退化，主對話不受影響 )，不涉 mic 獨佔安全，故沿用 degrade-not-crash。
- `_wake_control_released` 每次真正回 IDLE 、成功 `resume()` 後重設為 False ( daemon 重新持有麥克風 )，下一次 WAKE 再走一次 suspend gate。

## 3. Inbox 與 lifecycle

### 3.1 Inbox item

```python
@dataclass(frozen=True, slots=True)
class _TaskCompleted:
    correlation_id: int
    task: asyncio.Task[None]

@dataclass(frozen=True, slots=True)
class _WakeAckElapsed:
    session_id: str

@dataclass(frozen=True, slots=True)
class _RecoveryCompleted:
    generation: int
    waiter: asyncio.Task[None]

InboxItem: TypeAlias = Event | _TaskCompleted | _WakeAckElapsed | _RecoveryCompleted
```

使用 `asyncio.Queue[InboxItem](maxsize=0)` :

- Bus callback 必須能同步 enqueue 後立即 return ； bounded queue 的 `QueueFull` 需要 drop / backpressure 政策，架構沒有允許任何一種。
- Queue 僅供同 process 、單 event loop 使用；native thread 必須先排回主 loop。
- private item 帶 generation / correlation，過期 notice 可確定地 drop。

### 3.2 Event subscriptions

`start()` 對以下九個 concrete dataclass 逐一 subscribe :

```
PerceptionResult, LLMResponse, ActionCompleted, ErrorOccurred,
ButtonPressed, ExternalMessageArrived, WakeWordDetected,
InterruptRequested, ShutdownRequested
```

所有 subscription 使用同一個簡單 callback :

```python
async def _on_event(self, event: Event) -> None:
    self._inbox.put_nowait(event)
```

保存九個 `Subscription` token，`stop()` 逐一 unsubscribe。不得訂閱 `Event` / `WorkerFact` union alias。

### 3.3 start() / stop()

`start()` :

1. 驗證 config : `perception_timeouts` 三個 kind 值皆 > 0 ` `wake_ack_seconds` > 0 ` `default_perceptions` 非空且 kind 不重複。
2. 建立 subscriptions。
3. 建立 `_dispatch_task` ，等 `_dispatch_ready` event 後 return。
4. 初始 state 為 IDLE ；不發布虛構的 None -> IDLE。

`stop()` 是 shutdown 的最後清理，不代替 `ShutdownRequested` :

- 解除 subscriptions、取消 / await SM 自有 wake timer 與 recovery waiter。
- 重複呼叫為 no-op；若首次呼叫時仍有 active session，raise `RuntimeError` 暴露 main/RM 關閉順序錯誤，不暗中 cancel worker。
- `wait_stopped()` 供 `main.py` await ； dispatch loop 的 fatal exception 原樣傳出。

## 4. Session 與 in-flight 資料模型

### 4.1 SessionContext

```python
@dataclass(slots=True)
class SessionContext:
    session_id: str
    wake_source: Literal["button", "wake_word", "external_message"]
    turn_id: int = 0
    selected_perceptions: tuple[str, ...] = ()
    perception_results: list[PerceptionResult] = field(default_factory=list)
    llm_response: LLMResponse | None = None
    action_completed: ActionCompleted | None = None
    next_perceptions: tuple[str, ...] = ()
    buffer_exit_policy: Literal["none", "flush_to_wake", "discard"] = "none"
```

StateManager instance 持有 :

```python
_state: State = "IDLE"
_session: SessionContext | None = None
_correlation_counter = itertools.count(1)
_in_flight: dict[int, InFlightRecord] = {}
_shutting_down: bool = False
_recovery_generation: int | None = None
_pending_convergence: _PendingConvergence | None = None
_external_messages: ExternalMessageControl | None = None   # §2 late-fill
_wake_listener: WakeListenerControl | None = None        # §2 late-fill ( None=未啟用 )
_wake_control_released: bool = False  # 本次 WAKE 是否已取得 daemon 麥克風釋放證明
wake_control_failed: bool = False     # resume 功能性失敗後降級標籤
```

`_pending_convergence` 保存已 `converge()` return 、但尚未通過 §7.5 in-flight empty gate 的收斂結果 :

```python
@dataclass(frozen=True, slots=True)
class _PendingConvergence:
    trigger: Literal["rest", "interrupt", "error", "shutdown"]
    buffer_exit_policy: Literal["none", "flush_to_wake", "discard"]
    recovery_generation: int | None  # 有 destroyed backend 時為 active recovery generation，否則 None
```

每次 WAKE 建新 session ； counter 是 process 級、SM instance-owned，不隨 session 歸零。

> **註**：`SessionContext.buffer_exit_policy` 預設值 `"none"` 僅表示「尚未觸發收斂」，在進入 buffer 清理動作（如 flush 或 discard）前，StateManager **必須**確保已被 trigger 覆寫為有效策略；若以 `"none"` 傳入清理邏輯，應拋出 `StateManagerInvariantViolation`。

### 4.2 InFlightRecord

```python
@dataclass(slots=True)
class InFlightRecord:
    correlation_id: int
    session_id: str
    turn_id: int
    phase: Literal["perception", "think", "action"]
    kind: str
    worker: AbortableWorker
    task: asyncio.Task[None]
    terminal_fact: PerceptionResult | LLMResponse | ActionCompleted | None = None
    cancel_requested: bool = False
```

啟動 operation :

1. 取新 correlation id。
2. `asyncio.create_task(worker_method(...))`。
3. 先寫 `_in_flight[correlation_id]`。
4. `task.add_done_callback(partial(_enqueue_task_completed, correlation_id))`。

Done callback 只 `put_nowait(_TaskCompleted(...))`。禁止 callback 直接 :

- pop in-flight record ;
- 呼叫下一個 worker ;
- publish Event ;
- 執行 state transition。

### 4.3 Fact 與 completion join

收到 terminal Fact :

1. Guard Step 2 驗證 session / turn。
2. 以 correlation id 取 record，再驗證 phase / kind。
3. 若 record 已有 terminal fact，log warning 並 drop duplicate ( first Fact wins )。
4. 保存 Fact ；不移除 handle、不成立轉移狀態。

收到 `_TaskCompleted` :

1. correlation 不存在 -> stale notice，log debug 後 drop。
2. 確認 notice task object 與 record 相同。
3. 呼叫 `task.exception()` 收割 exception ( cancelled task 先以 `task.cancelled()` 分支處理 )。
4. 此時才從 `_in_flight` 移除。
5. 執行 §6 的 `_try_progress()`。

合法完成矩陣 :

| task 結果 | terminal Fact | `cancel_requested` | 處置 |
|---|---|---|---|
| return | 有 | false | 正常 join |
| return / cancelled | 無 | true | 合法收斂，不前進 normal flow |
| raise | 無 | 任意 | 若 SM 已因先到的 `ErrorOccurred` 進 ERROR，記錄後由 ERROR 收斂；否則 fatal contract violation |
| raise | 有 | 任意 | `FatalDispatchError` 原樣交 main；其他 exception 視為 publish Fact 後仍失敗的 fatal contract violation |
| return | 無 | false | fatal contract violation ( worker 違反 terminal Fact 契約 ) |
| 任意 | 有 | true | Fact 應已在 cancel 前 enqueue；若 state 已進收斂，不再用它推進 normal flow |

Fatal contract violation 由 dispatch task raise `WorkerContractViolation` ； SM 不自行 publish `ErrorOccurred`。

## 5. Dispatch loop 與 guard

```python
async def _dispatch_loop(self) -> None:
    self._dispatch_ready.set()
    while not self._loop_should_stop:
        item = await self._inbox.get()
        try:
            if isinstance(item, EventConcreteTypes):
                await self._handle_public_event(item)
            else:
                await self._handle_internal_notice(item)
            await self._try_progress()
        finally:
            self._inbox.task_done()
```

`Event` 是 union，不能直接用於 runtime `isinstance` ；實作使用 concrete tuple 或 `match`。

### 5.1 Public Event guard

Guard 固定三步 :

1. 依 state 白名單判斷 kind。
2. terminal Fact 驗證 current session / turn，再驗證 correlation record。
3. 交 state handler。

白名單 :

| State | 額外 public Event | 共通 Event |
|---|---|---|
| IDLE | `ButtonPressed` ` `WakeWordDetected` ` `ExternalMessageArrived` | Shutdown / Error / Interrupt |
| WAKE | `ExternalMessageArrived` | Shutdown / Error / Interrupt |
| PERCEPTION | `PerceptionResult` ` `ExternalMessageArrived` | Shutdown / Error / Interrupt |
| THINK | `LLMResponse` ` `ExternalMessageArrived` | Shutdown / Error / Interrupt |
| ACTION | `ActionCompleted` ` `ExternalMessageArrived` | Shutdown / Error / Interrupt |
| ERROR | `ButtonPressed` | Shutdown / Error / Interrupt |

- ERROR 中追加 `ErrorOccurred` : 記錄後吸收；若原 buffer policy 是 rest 的 flush，升級為 discard ( discard 優先於 flush )。
- ERROR 中 `InterruptRequested` : warning/debug 後忽略。
- ERROR 中 `ButtonPressed`（recovery **進行中**）: warning 後忽略。
- ERROR 中 `ButtonPressed`（recovery **已完成**或無 recovery）: 清 session 追蹤欄位 → 直接進 WAKE（使用者主動重試）。
- 非 IDLE 且非 ERROR 的 `ButtonPressed` : 觸發 `InterruptRequested` 行為，SM 直接執行收斂，語意等同直接收到 `InterruptRequested`。
- 非 IDLE 的 wake-word : 過期 Signal，warning 後 drop。
- ERROR 中 external message : 拒絕；buffer 由既定 exit policy 收斂。

### 5.2 Private notice guard

- `_WakeAckElapsed.session_id` 必須等於 current session 且 state=WAKE。
- `_TaskCompleted` 以 correlation + task identity 驗證。
- `_RecoveryCompleted.generation` 必須等於 active recovery generation 且 state=ERROR；過期 waiter 不可清除新 barrier。

Private notice 不走 public kind 白名單，也不 publish warning Event。

## 6. State 演算法

### 6.1 Transition primitive

```python
async def _transition(self, new: State) -> None:
    old = self._state
    if old == new:
        return
    await self._exit_state(old, new)
    self._state = new
    await self._bus.publish(StateChanged(old=old, new=new))
    await self._enter_state(new, old)
```

同一 dispatch item 內的 exit -> state assignment -> `StateChanged` -> entry 視為一個序列化 transition。Observer failure 產出的 `ErrorOccurred` 會排入 inbox，於本次 transition 結束後處理。

### 6.2 IDLE -> WAKE

收到第一個 wake Signal :

1. 建立 session id，記 wake source；external message 另把 message id 交 `external_messages.assign_to_session()`。
2. 若 `_wake_listener` is not None，經 §2.2 suspend gate await `_suspend_wake()` 取得 daemon 麥克風釋放證明 ( cooperative `suspend()` ，失敗則 `ensure_released()` )；證明成立才續行。連釋放都證明不了時阻擋本次 listen 路徑並依 §8 fatal ( 單一 mic owner 硬性不變量 )。
3. transition 到 WAKE。
4. 建 wake timer；timer 到期只 enqueue `_WakeAckElapsed(session_id)`。

同一 session 後續 `ExternalMessageArrived` :

- current turn 已選 read -> `assign_to_turn(message_id, session_id, turn_id)` ;
- 其他情況 -> `mark_pending(message_id, session_id)`。

SM 只傳 opaque id，不讀 payload。

### 6.3 PERCEPTION

WAKE timer 到期或 ACTION 續 turn :

1. transition 到 PERCEPTION；turn id += 1。
2. 首 turn 依 wake source 選 `("listen",)` 或 `("read",)`；後續使用保存的 `next_perceptions`，action error 則改 `default_perceptions`。
3. 若選擇包含 read，先 await `external_messages.begin_read(session_id, turn_id)` 建立 ACTIVE window ( 見 §6.3a )，再建立任何 perception task。
4. 清本 turn results，依選擇順序平行啟動 perception workers；每個 worker task 依其 kind 從 `perception_timeouts` 取得應 `timeout_seconds` ( listen->.listen ` read->.read ` look->.look ) 傳入。

### 6.3a read window 與 task 的原子啟動順序

當本 turn 選擇包含 read，PERCEPTION Entry 固定演算法 ( 消除 §6.3 步驟 3 / 4 先後的順序歧義 ) :

```
1. transition PERCEPTION ` turn += 1 ` 選定 selected_perceptions。
2. 若 "read" ∈ selected :
    await external_messages.begin_read(session_id, turn_id)  # 建立 ACTIVE window + item assignment
    ( 此 await 成立後 window 已 ACTIVE；失敗見下 )
3. 對 selected 內每個 kind，create_task(worker_method(..., timeout=perception_timeouts[kind]))
   並寫入 _in_flight。
```

因此 read worker 的 `consume_for_read()` 即使在 task 建立後第一個排程點立即執行，也必定看到已 ACTIVE 的 window ( Ch 7 §6.2 )。`begin_read()` 與 read task creation 之間無其他 await，read task 早於 window 建立的競態不可能發生。

`begin_read()` 失敗處理 :

- `begin_read()` 在 read task 建立之前 await，失敗時尚無已啟動的 read worker 需清理。
- 失敗 ( 例：同 session 已有 ACTIVE window 的 `ExternalMessageOwnershipError` ) 屬 SM 內部順序錯誤，視為 §3.2 SM 自檢問題：log context 後 transition ERROR ( 非 fatal )，不建立本 turn perception task ( arch.md §5.2 )。
- SM 在 phase 結束 / 取消時對 read 呼叫一次 `close_read(session_id, turn_id)` ( Ch 7 §6.3 idempotent )，覆蓋「`begin_read()` 完成但 consumer 尚未進入」的窗口。

`PerceptionResult` 依 inbox 到達順序 append。前進 THINK 的必要且充分條件 :

```
每個 selected perception 都已有一個 matching terminal Fact
AND 本 phase 的所有 outer task 都 done ` handle 已移除
AND state 仍為 PERCEPTION
```

### 6.4 THINK

PERCEPTION join 成立後 :

1. transition 到 THINK。
2. 讀取 `external_messages.pending_ids(session_id)` ；只取 opaque id tuple。
3. 啟動唯一 reasoner，傳 perception result tuple 與 pending ids。

`LLMResponse` join 成立後驗證 :

- `action_kind` 是 speak / tool / rest。
- `action_validator.validate(kind, payload)` 通過。
- `next_perceptions` 的處理只適用於 `action_kind ∈ {speak, tool}`：正規化 ( 剔除未註冊 kind + 去重 ) 後須非空、每個 kind 在 sealed `WorkerCatalog` 找得到。SM 不查 capability map；capability 決策只有 reasoner 執行。
- `action_kind=rest` 完全忽略 `next_perceptions` ( arch.md §2.7 / §4.6 ) ：不做正規化與非空、catalog 檢查，帶任意 `next_perceptions` ( 含未註冊 kind、空、重複 ) 皆合法。

duplicate 是正規化、不是違約：每個 perception kind 是單一通道（listen=麥克風、read=訊息、look=相機），同 kind 啟動兩次會違反單一資源擁有者或使 §6.3 join 永遠等不到第二個 Fact，故 duplicate 為零資訊噪音。SM 於 THINK Exit 靜默去重（保留首次出現順序），與「剔除未註冊 kind」同屬 arch.md §2.7 授權 SM 對 reasoner 輸出的正規化——degrade、不升級為 ERROR。去重只移除重複項、必留至少一個，故永不使非空清單變空、不引入失敗模式。

驗證失敗 ( AR-Impl-7, arch.md §4.5 / §4.6 / §2.7 ) 依序處理，皆為資料層問題，走 §3.2「SM 自檢」ERROR 路徑 ( 非 process 崩 ) :

1. `action_kind ∉ {speak, tool, rest}` -> 違約。
2. `action_validator.validate(kind, payload)` 不通過 -> 違約。
3. `action_kind=rest` : 跳過以下 step 4 全部 `next_perceptions` 處理，直接進 ACTION ( arch.md §2.7 )。
4. `action_kind ∈ {speak, tool}` : 正規化 `next_perceptions` —— (a) 剔除未註冊 kind ( log warning 。忽略，不因單一壞 kind 判整個 Fact 違約，見 §2.7 ) ； (b) 去重 ( 保留首次出現順序，log debug )。正規化後須非空且每個 kind 在 catalog 內，為空 -> 違約。SM 以正規化後 ( unique ) 清單推進 ACTION。

SM 對上述違約以內部 `ReasonerContractViolation` 標示判定原因，但後果是直接 transition 到 ERROR ( 不 publish `ErrorOccurred` 、不 fatal 交 main ) ： `stateChanged(->ERROR)` 即為權威信號，ERROR Entry 走 §6.5 error 收斂。進 ERROR 前依 §8 log 違約 context。

驗證成功後保存 response / 剔除後的 next perceptions，transition 到 ACTION。

### 6.5 ACTION

ACTION Entry 依 response kind 啟動一個 action worker。Fact + task done join 後 :

- `speak/tool` + status=ok : 保存 reasoner next perceptions，進下一 PERCEPTION。
- `speak/tool` + status=error : 改存 config `default_perceptions`，進下一 PERCEPTION。
- rest : 執行 `converge(trigger="rest")` ；依 §7 收斂後回 IDLE 或進 ERROR recovery。

## 7. Convergence 、 recovery 與 shutdown

### 7.1 Ch 6 介面

```python
@dataclass(frozen=True, slots=True)
class ConvergenceResult:
    destroyed_backends: tuple[str, ...] = ()

class SessionConverger(Protocol):
    async def converge(
        self,
        *,
        records: tuple[InFlightRecord, ...],
        trigger: Literal["rest", "interrupt", "error", "shutdown"],
    ) -> ConvergenceResult: ...
```

SM 呼叫前先把傳入 records 標 `cancel_requested=True`。Ch 6 必須等 Level 1 或 Level 2 完成證明 outer tasks done；但 handle 仍由已排入 inbox 的 `_TaskCompleted` 移除。

### 7.2 Trigger 結果

`converge()` return 時，Ch 6 已證明 outer tasks done，但對應的 `_TaskCompleted` notice 仍在 inbox 中未被消費，handle 尚未移除 ( §4.3、Ch 6 §3 )。因此任何 trigger 都不得在 `converge()` return 當下就清 session / 回 IDLE ；否則 `_in_flight` 仍含舊 session record 時即可能接受新 wake，違反 arch.md §6.3 handle 生命週期與狀態清空要求。

收斂結果一律先記為 pending，交由 §7.5 的 progress gate 在 in-flight 真正清空後才完成 :

| Trigger | buffer exit policy | 無 destroyed backend | 有 destroyed backend |
|---|---|---|---|
| rest | flush-to-wake | pending : in-flight 空 -> IDLE -> flush | 進 ERROR，recovery + in-flight 空 -> IDLE -> flush |
| interrupt | discard | pending : in-flight 空 -> IDLE | 進 ERROR，recovery + in-flight 空 -> IDLE |
| error | discard | 留 ERROR，等 in-flight 空 -> IDLE | 留 ERROR 等 recovery + in-flight 空 |
| shutdown | discard | 等 handles 移除後停 loop | 不 rebuild ；等 handles 移除後停 loop |

- 「in-flight 空」統一指 §7.5 gate：所有相應 `_TaskCompleted` 已由 dispatch loop 消費、handle 已移除。Converger / event handler 不得直接 pop record 繞過既定 owner。
- ERROR trigger ( 含有 destroyed backend 的路徑 ) 沿用既有 ERROR Exit gate ( §7.3 )，該 gate 本就含 in-flight empty 條件；本次修訂使 rest / interrupt 的 normal ( 無 destroyed backend ) 路徑也一致地等 in-flight 空，而非在 `converge()` return 即回 IDLE。

Buffer policy 採取重度合併 : `discard` > `flush_to_wake` > `none`。因此 rest recovery 期間若收到 `ErrorOccurred` / Interrupt / Shutdown，policy 升級為 discard，不能在恢復後重新喚醒一個已經歷異常收斂的訊息。

Level 2 failure 不會回傳 result ； Ch 6 raise fatal，dispatch task 結束，main 退出。

### 7.3 Recovery waiter

有 destroyed backends 且 trigger 不是 shutdown :

1. `ticket = recovery.begin_recovery(keys)` ； Ch 5 必須在同步 return 前 clear barrier。下一步必須早於本路徑的 ERROR transition / ERROR Exit gate。
2. 若當前而非 ERROR，transition 到 ERROR；若原 trigger 就是 error，維持 ERROR。
3. 建立 task `recovery.wait_recovery(ticket)`。
4. done callback enqueue `_RecoveryCompleted(ticket.generation, task)`。
5. notice handler 呼叫 `task.result()` ：成功後 barrier 應為 clear-ready；失敗直接 propagate `RecoveryFatalError` 至 main。

ERROR Exit gate 是 §7.5 統一 progress gate 在 `recovery_generation is not None` 時的具體形式 :

```
state == ERROR
AND in_flight 為空
AND recovery.recovery_ready()
```

回 IDLE 的順序與收尾動作由 §7.5 gate 成立後統一執行 ( 清 session -> IDLE -> §2.2 `_resume_wake()` -> buffer exit policy ) ； resume / flush 一定發生在所有 handle 移除之後。

### 7.4 Shutdown

收到 Shutdown :

1. `_shutting_down=True` ，拒絕新 wake。
2. 取消 / await SM 自有 wake timer。
3. 若 RM 正在 recovery，先 `recovery.prepare_shutdown()` 停止 rebuild 並完成其局部資源 cleanup。
4. external-message discard。
5. `converge(trigger="shutdown")` ；不啟動 recovery。
6. 持續處理 inbox 中 `_TaskCompleted` ，直到 in-flight 空。
7. 設 `_loop_should_stop=True` ，`wait_stopped()` 完成；main 再呼叫 RM reverse stop。

### 7.5 收斂後 progress gate ( 統一 in-flight empty gate )

所有 trigger 的 `converge()` 都在單一 dispatch item 內同步 return ； SM 不在該處清 session 或回 IDLE，而是 :

1. 依 §7.2 / §7.3 決定是否 `begin_recovery()` 、是否 transition ERROR，並把結果記入 `_pending_convergence` ( 含 trigger、合併後 buffer policy、recovery generation 或 None )。
2. 回到 dispatch loop 繼續消費 inbox。每個相應 `_TaskCompleted` 依 §4.3 收割 exception、移除 handle，然後呼叫 `_try_progress()`。

`_try_progress()` 對 pending convergence 的完成 gate ( 唯一收斂完成點 ) :

```
_pending_convergence is not None
AND in_flight 為空
AND ( recovery_generation is None OR recovery.recovery_ready() )
```

gate 未成立前，SM 不清 session、不 resume voice wake、不接受新 wake ( IDLE 的 wake 白名單只有在 gate 完成、回到 IDLE 後才開放 )。

gate 成立後，依 trigger 收尾 :

- rest / interrupt / error : 清 session -> transition IDLE -> §2.2 `_resume_wake()` -> 套用 buffer exit policy ( rest 的 `flush_to_wake()` 必在 IDLE 後 ; discard 可在收斂開始時先做 )。清 `_pending_convergence`。
- shutdown : 不回 IDLE ； in-flight 空即 §7.4 步驟 7 停 loop。

因此 Interrupt 發生於 PERCEPTION / THINK / ACTION 時，即使 converge() 已 return，只要相應 _TaskCompleted 尚在 inbox、_in_flight 未空，SM 就停在 pending 狀態 ( 非 IDLE )，不接受新 wake ；全部 notice 處理完畢後才回 IDLE。ERROR trigger 的 §7.3 ERROR Exit gate 是本 gate 在 recovery_generation is not None 且 state==ERROR 時的同一條件。

## 8. 錯誤與 logging 語意

```python
class StateManagerFatalError(RuntimeError): ...
class WorkerContractViolation(StateManagerFatalError): ...
class StateManagerWiringError(StateManagerFatalError):
    """late-fill setter 重複/過晚呼叫，或 producer arm 後 control 仍為 None；composition bug，fatal。"""
class WakeMicReleaseUnprovable(StateManagerFatalError):
    """suspend 與 ensure_released 皆無法證明 daemon 已釋放麥克風；為維持單一 mic owner，fatal。"""
class StateManagerInvariantViolation(StateManagerFatalError):
    """只用於 SM 本身不可能狀態、dispatch bookkeeping 破壞等 bug；不得用於包裝 payload 錯誤，fatal。"""

class ReasonerContractViolation(Exception):
    """SM 自檢 LLMResponse 違約的內部判定；後果為進 ERROR，非 fatal。"""

class WakeListenerControlError(RuntimeError):
    """wake daemon 控制 ( suspend/resume/ensure_released ) 失敗或 timeout。resume 功能性失敗
    以 §2.2 降級處置 ( 非 fatal ) ； suspend 失敗會升級 ensure_released，仍失敗則轉
    WakeMicReleaseUnprovable ( fatal )。"""
```

`WorkerContractViolation` 屬 `StateManagerFatalError` ， dispatch task 原樣交 main supervision、結束 process。 `ReasonerContractViolation` 不是 fatal：它只是 SM 自檢 `LLMResponse` 內容違約的內部判定用途，後果是 §6.4 走 §3.2「SM 自檢」ERROR 路徑 ( AR-Impl-7 )。兩者皆不轉成 `ErrorOccurred`。

| 情境 | 行為 |
|---|---|
| public event 非白名單 / stale id / stale notice | warning ( 高頻 stale notice 可 debug ) + drop |
| duplicate terminal Fact | warning + first wins |
| `LLMResponse` schema / payload 不合、speak/tool 剔除後 `next_perceptions` 空 | 判 `ReasonerContractViolation` -> 進 ERROR ( §3.2 自檢路徑，非 fatal ) ，不 publish `ErrorOccurred` |
| speak/tool `next_perceptions` 含未註冊 kind | log warning + 剔除該 kind ( §2.7 ) ；正規化後非空即通過 |
| speak/tool `next_perceptions` 含 duplicate kind | log debug + 去重 ( 保留首次出現順序，§6.4 正規化 ) ；不違約 |
| `action_kind=rest` 帶任意 `next_perceptions` ( 未註冊 kind / 空 / 重複 ) | 忽略該欄位 ( arch.md §2.7 / §4.6 ) ，不正規化、不違約，直接進 ACTION |
| task return 但無 Fact 且非 cancel | raise `WorkerContractViolation` ( fatal 交 main ) |
| task raise 且目前未進 ERROR | raise `WorkerContractViolation` ，不由 SM 補發 Error |
| convergence / recovery fatal | exception 原樣交 main，process 結束 |
| ERROR 中追加 `ErrorOccurred` | 記錄後吸收 |
| `WakeListenerControl` `suspend()` 失敗 / timeout | §2.2 suspend gate : 升級 `ensure_released()` 取得釋放證明；成功則放行 listen ( WARNING ) |
| `suspend()` 與 `ensure_released()` 皆失敗 ( 無釋放證明 ) | 阻擋本次 listen，raise `WakeMicReleaseUnprovable` ( fatal 交 main ) ；不放行 listen 以免雙 mic owner |
| `WakeListenerControl` `resume()` 失敗 / 斷線 | §2.2 resume gate : 設 `_wake_control_failed` ` WARNING ` 降級 ( wake 偵測退化 ) ；不進 ERROR、不 fatal |
| late-fill setter 重複 / 過晚呼叫，或 arm 後 control 仍 None | raise `StateManagerWiringError` ( fatal 交 main ) |

Log context 至少含 state、session_id、turn_id、correlation_id、worker kind ；詳細 logger facade 留 Ch 11。

## 9. 驗收與測試

最低純軟體測試 :

1. `start()` 訂閱九個 concrete event types ； `stop()` 精確解除。
2. Bus callback 只 enqueue，不同步改 state。
3. 多 producer 並行時 dispatch transition 不交錯。
4. Fact 先到而 task 未 done，不啟動下一 phase。
5. task done notice 後才移除 handle 並前進。
6. terminal Fact 的 Bus fallback `ErrorOccurred` 排在 completion notice 前時，SM 進 ERROR 且未啟動下一 action。
7. 兩個 perception 以不同順序完成，必須兩個 Fact + 兩個 done 才進 THINK。
8. stale session / turn / correlation、duplicate Fact 均不改變狀態。
9. worker 正常 return 無 Fact 且非 cancel，dispatch task fatal。
10. invalid LLM schema / payload、或 speak/tool 正規化 ( 剔除未註冊 kind + 去重 ) 後 `next_perceptions` 空 : SM 直接 transition ERROR ( 不 publish `ErrorOccurred`、不 fatal ) ，走 §6.5 error 收斂；speak/tool `next_perceptions` 含未註冊 kind 但正規化後非空則正常進 ACTION。10a. speak/tool `next_perceptions` 去重：輸入含 duplicate registered kind ( 例 `["listen", "listen"]` ) 時，SM 去重為 `("listen",)` ( 保留首次順序 )、不進 ERROR，且斷言只為 listen 起一個 in-flight perception task ( 不因重複起兩個、不違反單一 mic owner )。10b. `action_kind=rest` 忽略 `next_perceptions` ( arch.md §2.7 / §4.6 ) ： rest 帶未註冊 kind / 空清單 / 重複 kind 皆不觸發 ERROR、不正規化，直接進 ACTION 執行 rest 收斂。以三種 payload 斷言 SM 不進 ERROR。
11. WAKE timer 在 Interrupt / Error / Shutdown 時取消；舊 timer notice 不污染新 session。
12. first-turn wake mapping 三種來源正確。
13. action error 使用 `default_perceptions` ；其他 Fact status 不分歧。
14. rest normal : 先回 IDLE 再 flush-to-wake。
15. rest destructive : 先 clear recovery barrier 再進 ERROR，回 IDLE 後才 flush-to-wake。
16. interrupt / error / shutdown discard policy 正確。
17. ERROR Exit 同時等待 in-flight empty 與 recovery ready。17a. Interrupt in-flight gate ( §7.5 ) : 多 worker Interrupt 下，`converge()` 已 return 但相應 `_TaskCompleted` 仍在 inbox、`_in_flight` 未空時，SM 停在 pending 狀態、不回 IDLE、不接受新 wake、不 resume wake ；所有 notice 處理完 ( in-flight 空 ) 後才清 session、回 IDLE 並套用 discard。以 fake worker 讓 outer task done 與 notice 消費分開時斷言。17b. rest normal ( 無 destroyed backend ) 同樣經 in-flight empty gate 才回 IDLE，再 flush-to-wake ；非在 `converge()` return 當下回 IDLE。
18. recovery waiter failure 與 Ch 6 Level 3 failure 皆傳至 main。
19. Shutdown 等 completion notices 清空後停止 loop，沒有 worker handle 遺留。
20. `WakeListenerControl` ( §2.1 ) : WAKE Entry 的 `suspend()` ACK ( release proof ) 必然先於 listen `frames()` ； `resume()` 只在回 IDLE、in-flight 空後呼叫。以 fake control 斷言呼叫順序。
21. suspend 失敗升級釋放證明：`suspend()` raise `WakeListenerControlError` ( 模擬 daemon timeout / 斷線 ) 時，SM 不直接放行 listen，而是 await `ensure_released()` ； `ensure_released()` 成功 ( daemon 已終止 / 釋放 ) 後才啟動 listen，WAKE transition 完成並 log WARNING。以 fake control 斷言 `ensure_released()` 在 listen `frames()` 之前被呼叫。21a. 釋放無法證明即 fatal：`suspend()` 與 `ensure_released()` 皆 raise 時，SM 阻擋 listen、raise `WakeMicReleaseUnprovable` ( fatal 交 main ) ，且斷言 listen `frames()` 從未被呼叫 ( 不出現雙 mic owner ) 。21b. resume 功能性失敗降級：回 IDLE 後 `resume()` raise 時，SM 設 `_wake_control_failed` 、不進 ERROR、不 fatal，後續 suspend / resume gate 為 no-op ( wake 偵測退化，主對話續行 ) 。
22. 重複 `suspend()` / `ensure_released()` / `resume()` 對 fake control 為 idempotent no-op ACK，不 raise。22a. late-fill setter ( §2 ) : `set_external_message_control()` / `set_wake_listener()` 於 producer arm 前各呼叫一次成功；重複呼叫、傳 None 給 external control、或 `stop()` 後呼叫皆 raise `StateManagerWiringError` 。 `set_wake_listener(None)` 合法表示未啟用；此時 §2.2 suspend gate 直接 return、不呼叫任何 daemon 動詞。22b. producer arm 後 external / wake Signal 進 inbox 時對應 control 仍為 None ( 模擬 RM arm 順序錯誤 ) -> raise `StateManagerWiringError` ( fatal ) 。

測試以 fake workers 、 asyncio.Event / barrier 控制順序，不以 wall-clock sleep 猜競態。

## 10. 對後續章節的輸入

- Ch 5 : 固定 `RecoveryControl` / ticket / barrier 與 `prepare_shutdown()` 語意。
- Ch 6 : 固定 `SessionConverger.converge()` 與聚合 `destroyed_backends`。
- Ch 7 : 固定 assign-to-session / turn 、 pending ids 、 begin-read 、 flush / discard 動詞。
- Ch 9 : 提供 `ActionPayloadValidator` ，且驗證不執行 tool handler。
- Ch 10 : 提供 wake ack 、 perception 、 cancel / recovery timeout 與 default perceptions。
- Ch 11 : main 監督 dispatch task / bus fatal / RM recovery fatal 的方式。
