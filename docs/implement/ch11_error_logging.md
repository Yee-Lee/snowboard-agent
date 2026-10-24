# Ch 11. 錯誤處理與 logging 慣例

屬於 `implement.md` 索引 | 對應 `arch.md` §3.4 / §6.4 / §6.6 ~ §6.7 | 狀態：定稿（IR-final 已通過（2026-08-01））

上游：Ch 1、Ch 3、Ch 4、Ch 5、Ch 6、Ch 10。

## 0. 已確認判斷

| 編號 | 判斷點 | 已確認結論 |
| --- | --- | --- |
| ch11-Q1 | Logging library | stdlib `logging`；不新增structlog dependency |
| ch11-Q2 | 結構化格式 | 自有Formatter支援text與JSON lines，共用同一LogRecord欄位 |
| ch11-Q3 | `ErrorOccurred` 是否每個publisher自行寫ERROR | 否；logging observer為canonical ERROR log，publisher只publish一次 |
| ch11-Q4 | P5 fact error的level | WARNING；它是可翻譯結果，不等於Exception層ERROR |
| ch11-Q5 | Fatal traceback由誰寫 | main supervisor只需一次CRITICAL + traceback；下層附context但不重複traceback |
| ch11-Q6 | Runtime fatal後是否嘗試完整RM stop | 不保證；只做有上限的logger flush，讓process/systemd完成Level 3 |
| ch11-Q7 | `where` 動態片段 | 必須sanitize為lower snake/dotted token；原handler repr另放safe field |
| ch11-Q8 | 是否記prompt / payload / transcript | 預設禁止；只記ID、kind、status、length等metadata |
| ch11-Q9 | Logging observer是否optional | 不是；必須在producer前subscribe，start失敗是startup fatal |
| ch11-Q10 | Rotation | `RotatingFileHandler`；file=None時stderr，預設不rotation |
| ch11-Q11 | Exit code | config=2、startup=3、runtime fatal=4、正常shutdown=0 |

## 1. 範圍與非目標

### 1.1 本章包含

- Logger建立、格式、context與rotation。
- `ErrorOccurred.where` namespace與canonical logging owner。
- P5 / exception / fatal三層log level。
- Bus / SM / RM / Converger fatal supervision與top-level exit。
- 敏感資料、traceback與重複log政策。
- 各層可重複驗收條件。

### 1.2 本章不包含

- 遠端log shipping、metrics backend或distributed tracing。
- End-user UI error文案；Display error slot只需sanitized摘要。
- systemd unit細節；只定義process exit與flush契約。
- Audit log、長期conversation transcript或模型prompt保存。

## 2. 套件

```
src/sbd/core/
├── logger.py             # configure_logging / get_logger / formatters
└── error_observer.py     # ErrorOccurred canonical subscriber

src/sbd/
└── main.py               # bootstrap + fatal supervision + exit code
```

`ErrorLoggingObserver` 屬bootstrap logging infrastructure：由 `main.py` 在建立 EventBus後立即建立 / subscribe，不放入Ch 5 optional Observer phase或RM registry。其start failure也是startup fatal；Presenter / StatusBar等一般Observer仍維持optional。

所有project logger都在 `sbd` namespace：

```python
logger = logging.getLogger("sbd.perception.listen")
```

禁止各模組自行呼叫 `basicConfig()`、自行新增handler或改變root logger level。

## 3. Logging runtime

```python
@dataclass(frozen=True, slots=True)
class LoggingRuntime:
    logger: logging.Logger
    handlers: tuple[logging.Handler, ...]

    async def flush(self, timeout_seconds: float) -> None: ...
    def close(self) -> None: ...

def configure_logging(config: LogConfig) -> LoggingRuntime: ...
def get_logger(name: str) -> logging.Logger: ...
```

啟動分兩階段：
1. Config載入前使用bootstrap stderr logger，固定簡短text、INFO。
2. Config成功後 `configure_logging()` 原子替換 `sbd` handlers / level。

重複configure需先flush/close舊handler，主要供test fixture；runtime不reload。

## 4. LogRecord schema

保留stdlib欄位並約定extra：

```
timestamp
level
logger
message
where
state
session_id
turn_id
correlation_id
worker_kind
event_type
trigger
cancel_level
resource_key
exception_type
```

未知extra允許，但key必須lower snake case且value為JSON scalar。不得把dict/list 任意塞進LogRecord；需要多值時使用逗號分隔的sanitized string或count。

### 4.1 Text format

```
2026-07-30T12:00:00.123+08:00 WARNING sbd.cancel level1_timeout \
  trigger=error worker_kind=cognition.reasoner correlation_id=42
```

### 4.2 JSON lines

每單一行UTF-8 object：

```json
{"timestamp":"2026-07-30T12:00:00.123+08:00","level":"ERROR",
 "logger":"sbd.error_observer","message":"worker_error",
 "where":"perception.listen","exception_type":"AdapterError"}
```

JSON formatter：
- timestamp使用timezone-aware ISO 8601 wall clock；
- event排序仍依 `stateChanged.at` / IDs，不依wall clock保證；
- exception只在CRITICAL root log加入formatted traceback；
- invalid extra value轉安全repr並截斷，不讓formatter exception回到Event Bus。

## 5. Context API

使用stdlib `LoggerAdapter`：

```python
def with_context(
    logger: logging.Logger,
    *,
    state: str | None = None,
    session_id: str | None = None,
    turn_id: int | None = None,
    correlation_id: int | None = None,
    worker_kind: str | None = None,
) -> logging.LoggerAdapter: ...
```

規則：
- constructor / operation entry建立adapter，不以module global保存session context。
- `None` 欄位不輸出。
- child function可新增context但不可覆寫不同session / correlation；debug build可 assert。
- Event handler名稱使用Ch 3 subscription explicit `name`，不從callable repr推導stable identity。

## 6. `ErrorOccurred.where` namespace

格式：

`<layer>.<component>[.<subcomponent>...]`

token regex：

`^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$`

Canonical表：

| where | publisher邊界 |
| --- | --- |
| `perception.listen` | Listen worker不可翻譯exception |
| `perception.read` | Read worker / buffer invariant failure |
| `perception.look` | Look worker不可翻譯exception |
| `cognition.reasoner` | Reasoner不可翻譯exception |
| `action.speak` | Speak worker不可翻譯exception |
| `action.tool` | Tool worker不可翻譯exception |
| `action.rest` | Rest worker不可翻譯exception |
| `core.audio` | HAL boundary無worker可翻譯的錯誤 |
| `core.camera` | HAL boundary無worker可翻譯的錯誤 |
| `core.gpio.callback` | GPIO callback exception |
| `bus.dispatch.<name>` | Ch 3 subscriber fallback |

Ch 3 `<name>` 在subscribe時先sanitize：
- lower case；非 `[a-z0-9_]` 轉underscore；連續underscore合併；空結果用 `anonymous`，但production registration禁止anonymous。

Pin、message ID、tool name等dynamic identity不放where token，另放 `resource_key` / safe field。

## 7. Canonical `ErrorOccurred` observer

```python
class ErrorLoggingObserver:
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def __call__(self, event: ErrorOccurred) -> None: ...
```

`start()`：
- exact-type subscribe `ErrorOccurred`，name=`error_logger`；
- 保存Subscription token；
- 必須在任何producer start前完成。

Handler：
1. 驗證 / sanitize `where`；非法值改 `invalid_where` safe field，不raise。
2. 對 `event.error` 做redaction / truncate。
3. 寫一筆ERROR，不帶 `exc_info`，因event只保存string與exception type。
4. return；handler自身不得publish Event。

`stop()` 精確unsubscribe，idempotent。

### 7.1 單一ERROR owner

Publisher責任：
- 建構並publish一個 `ErrorOccurred`；
- 不先寫同內容ERROR traceback；
- 可在publish前寫DEBUG operation context。

Observer責任：
- 為每個實際收到的 `ErrorOccurred` 寫一筆ERROR；
- 不跨來源去重。Worker與Bus fallback是不同error時可各寫一筆。

Bus派送 `ErrorOccurred` 時observer自身失敗屬Ch 3 fatal fallback不遮蔽；因此handler 設計必須極小、formatter必須fail-safe。

## 8. Level policy

| level | 使用情境 |
| --- | --- |
| DEBUG | inbox enqueue、stale notice、cancel start/success、display fullscreen拒絕 |
| INFO | startup成功、state transition、resource READY、normal shutdown |
| WARNING | P5 status=error/timeout、optional start失敗、null fallback、Level 1升Level 2、buffer drop |
| ERROR | canonical `ErrorOccurred`、SM reasoner-response自檢違約、display operational disable、shutdown單一stop failure |
| CRITICAL | config/startup fatal、Level 3、Bus fatal fallback、SM internal invariant / worker contract violation、recovery fatal |

`PerceptionResult(status="error")` / `ActionCompleted(status="error")` 是Fact層，記WARNING而不是ERROR。ERROR保留給Exception層、SM自檢診斷或已失去主要observer能力的operational degradation。

`ReasonerContractViolation` 是壞 LLMResponse 的資料層自檢結果。SM記恰好一筆 不帶traceback、不含raw payload的ERROR診斷後直接transition ERROR；此路徑不publish `ErrorOccurred`，所以不由canonical observer代寫，也不進main fatal supervisor。 `StateChanged(->ERROR)` 仍是狀態權威信號。

State transition記INFO只含old/new/session/turn；高頻 production可日後調DEBUG，初版保留INFO便於bring-up。

## 9. 敏感資料與 redaction

永不記錄：
- `.env` value、MQTT password、API key；
- audio PCM、image bytes；完整external-message text / metadata；
- ASR transcript；
- LLM prompt、raw output；完整action payload / tool arguments；
- Python object repr若可能包含上述內容。

允許metadata：

```
message_id, channel, payload_bytes, text_length,
model_name, token_count, action_kind, tool_name,
session_id, turn_id, correlation_id
```

Redactor處理常見pattern：

```
password=...
token=...
api_key=...
authorization=...
```

但redaction不是允許任意payload進log的理由；caller首先就不應傳入。

所有user/library字串預設截斷至512 Unicode code points，換行轉義。Exception class name可保留； `repr(exc)` 經同一redactor。

## 10. Fatal supervision

### 10.1 必須監督的 awaitable

- `bus.wait_fatal()`：Ch 3 latch的 `FatalDispatchError`。
- `state_manager.wait_stopped()`：正常shutdown return或dispatch fatal raise。
- process signal bridge：SIGTERM / SIGINT只publish `ShutdownRequested` 一次。

Fatal supervision必須在啟動任何InputSource / worker / adaptor producer前武裝。這是Ch 5 startup phase barrier的一部分。

### 10.2 Main runtime loop

概念流程：

```python
bus_fatal = asyncio.create_task(bus.wait_fatal())
sm_stopped = asyncio.create_task(sm.wait_stopped())
signal_waiter = install_signal_bridge(bus)

done, pending = await asyncio.wait(
    {bus_fatal, sm_stopped, signal_waiter},
    return_when=asyncio.FIRST_COMPLETED,
)
```

判定：
- signal waiter完成：publish ShutdownRequested後繼續等待SM stopped。
- SM正常stopped：呼叫RM reverse `stop_all()`、flush logger、exit 0。
- SM raise真正fatal subtype / bus fatal：進runtime fatal path，exit 4。
- `RecoveryFatalError` / `ConvergenceFatalError` / `WorkerContractViolation` / `StateManagerInvariantViolation` 皆由SM wait task帶到runtime fatal path。
- `ReasonerContractViolation` 不離開SM dispatch；SM記ERROR診斷並完成ERROR state convergence，main持續監督process，不產生exit 4。

### 10.3 Runtime fatal path

1. Latch第一個root exception；後續fatal只附summary。
2. 寫一筆CRITICAL， `exc_info=(type, value, traceback)`。
3. 設process exiting，拒絕新producer啟動。
4. 不呼叫SM ERROR、不publish `ErrorOccurred`。
5. 不宣稱執行乾淨的RM reverse stop；Level 3本身表示termination proof失敗。
6. 在 `logger_flush_timeout_seconds` 內flush。
7. 讓root exception逸出top-level，轉exit code 4；systemd依部署政策重啟。

`asyncio.run()` 結束時可能cancel剩餘Python tasks，這是Level 3 process teardown，不是Ch 6 Level 2完成證明。Child process最終清理由systemd cgroup政策負責。

## 11. Startup / shutdown logging

### 11.1 Config fatal

- bootstrap stderr CRITICAL；不建立Event Bus；
- exit 2。

### 11.2 Resource startup fatal

- `StartupError` 由main寫一次CRITICAL traceback；
- RM完成已started resources的reverse rollback；
- rollback failure逐一ERROR，但不取代原root cause；
- logger flush，exit 3。

### 11.3 Normal shutdown

- SM已停止、in-flight empty後呼叫 `stop_all()`。
- `ShutdownReport.failures` 每項寫ERROR並繼續。
- logger最後flush / close。
- 即使optional stop有failure，若主shutdown流程完成仍exit 0；deployment可從ERROR log觀察。

## 12. Rotation 與輸出

依Ch 10：
- `file=None`：單一 `StreamHandler(sys.stderr)`。
- file非None、rotation disabled： `FileHandler(encoding="utf-8")`。
- rotation enabled： `RotatingFileHandler(maxBytes, backupCount, encoding="utf-8")`。

規則：
- parent目錄不存在時config/startup fatal；logger不默默建立任意目錄。
- 同process只裝一個application handler，避免duplicate log。
- handler flush同步操作很短； `LoggingRuntime.flush()` 用有上限的thread offload 或逐handler flush，實作不得無限等待。
- child process不直接寫同一rotation file；透過IPC把必要status帶回parent log，避免多process rotation race。

## 13. Error taxonomy 對照

SM fatal hierarchy需明確區分資料違約與程式不分量破壞：

```python
class StateManagerFatalError(RuntimeError): ...
class WorkerContractViolation(StateManagerFatalError): ...
class StateManagerInvariantViolation(StateManagerFatalError): ...

class ReasonerContractViolation(Exception):
    """壞 LLMResponse 的內部自檢診斷；進 ERROR state，不是 fatal exception。"""
```

`StateManagerInvariantViolation` 只用於SM本身不可能狀態、dispatch bookkeeping破壞 或其他無法用既定ERROR convergence證明終止的bug；不得拿來包裝payload。

| exception | owner | 層級 / 處置 |
| --- | --- | --- |
| `ConfigError` | config loader | CRITICAL、exit 2 |
| `StartupError` | RM | CRITICAL、rollback、exit 3 |
| `FatalDispatchError` | Event Bus | CRITICAL、exit 4 |
| `WorkerContractViolation` | SM | CRITICAL、exit 4 |
| `StateManagerInvariantViolation` | SM | CRITICAL、exit 4 |
| `ReasonerContractViolation` | SM | 一筆非fatal ERROR診斷、直接transition ERROR、process繼續 |
| `ConvergenceFatalError` | Ch 6 | CRITICAL、exit 4 |
| `RecoveryFatalError` | RM/SM waiter | CRITICAL、exit 4 |
| `ActionPayloadValidationError` | Reasoner/SM | Reasoner走P5；SM包成內部 `ReasonerContractViolation` 後走自檢ERROR，不fatal |
| `ExternalMessageNotFound` | Ch 7 caller | DEBUG/WARNING、drop stale |
| `DisplayHintError` | display caller | WARNING、主流程繼續 |

Root exception chain使用 `raise ... from exc` 保留；只有main root log輸出真正fatal的 完整chain。 `ReasonerContractViolation` 不帶出SM，因此不產生CRITICAL traceback。

## 14. 驗收與測試

最低軟體測試：
1. `configure` 只在 `sbd` 裝一個handler，重複configure不duplicate。
2. text / JSON formatter包含共同context且每筆JSON單行可parse。
3. JSON formatter遇不可serialize extra仍不raise。
4. Error observer exact-type subscribe且在producer前READY。
5. 每個 `ErrorOccurred` 恰寫一筆ERROR，不含traceback duplication。
6. P5 error / timeout記WARNING，不記ERROR。
7. `where` 合法表與dynamic handler sanitize。
8. secret、payload、transcript、prompt測試字串不出現在captured log。
9. user/library字串截斷且newline escape。
10. Bus fatal / SM真正fatal競速時只選第一個root CRITICAL traceback。
11. runtime fatal不publish新 `ErrorOccurred`、不嘗試SM ERROR recovery。
12. config / startup / runtime / normal exit codes分別2 / 3 / 4 / 0。
13. startup rollback failure不遮蔽原StartupError。
14. normal shutdown report逐項ERROR且仍完成logger close。
15. rotation設定選對handler；child logger不直接開同一file。
16. logger flush timeout不阻止runtime fatal process exit。
17. invalid action kind / payload或剔除後空 `next_perceptions` 只產一筆無payload、無 traceback的SM ERROR診斷與 `StateChanged(->ERROR)`；不publish `ErrorOccurred`、SM wait task不raise、main不寫CRITICAL且process不exit 4。
18. 人工觸發真正SM bookkeeping invariant破壞時raise `StateManagerInvariantViolation`，main只寫一次CRITICAL traceback並exit 4；此 測試與第17項使用不同exception與不同supervision結果。

測試使用in-memory handler與fake supervisor futures，不真正送OS signal；signal bridge 另做platform-specific小型integration test。

## 15. 對 IR-final 與 milestone 的輸入

- Ch 3： `FatalDispatchError` 與 `wait_fatal()` 正式章需保持一致。
- Ch 5：logging observer與fatal supervision是producer startup前的required gate。
- Ch 6：Level 3 root由main寫一次CRITICAL。
- Ch 10：stdlib logging、format、rotation與flush timeout欄位已固定。
- Ch 4 / Ch 9： `ReasonerContractViolation` 固定為SM自檢ERROR收斂；真正internal fatal固定使用 `StateManagerInvariantViolation` / `WorkerContractViolation`。
- milestone M1驗收應包含config/startup/runtime三種non-zero exit與log capture。
