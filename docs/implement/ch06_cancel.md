# Ch 6. Cancel 三級收斂實作

> M4B-MVA revision（2026-09-05）：本章generic／已Accepted行為維持；
> LLM新session/control/semantic/profile契約依[ch_m4b_llm_production.md](ch_m4b_llm_production.md)，
> 尚待AR_impl_M4B_I與design/spec簽核。不得以舊source已實作視為M4B-MVA Ready。


屬於 `implement.md` 索引 | 對應 `arch.md` §6.3 ~ §6.5 | 狀態：定稿（IR-final 已通過（2026-08-01））

上游：Ch 2、Ch 2b、Ch 4、Ch 5。

## 0. 已確認判斷

| 編號 | 判斷點 | 已確認結論 |
| --- | --- | --- |
| ch6-Q1 | 多個 in-flight worker 依序或平行收斂 | 同一 Level 內平行；避免一個慢 worker 消耗其他 worker 的停止時間 |
| ch6-Q2 | Level 1 timeout 粒度 | 每個 target 各自計時；timeout 由 kind policy 決定，不共用整批倒數 |
| ch6-Q3 | abort() raise 如何處理 | 記錄 Level 1 failure 並升級該 target 至 Level 2；不由 Converger 發 ErrorOccurred |
| ch6-Q4 | Level 2 是否可呼叫 outer task.cancel() | 不可；唯一動詞是 force_abort()，逾時 / raise 直接 Level 3 |
| ch6-Q5 | ForceAbortReport 如何聚合 | 依 stable ResourceKey 去重、排序後回 ConvergenceResult.destroyed_backends |
| ch6-Q6 | force_abort() return 但 outer task 尚未 done | 視為 worker 契約違反；Level 2 timeout 覆蓋 termination proof 與 outer task done |
| ch6-Q7 | 四種 trigger 是否使用不同 cancel 演算法 | 否；演算法相同，差異只由 Ch 4 決定 recovery 與 buffer policy |
| ch6-Q8 | Level 3 如何交給 main | raise `ConvergenceFatalError`，保留 target / stage / root cause；不呼叫 `os._exit()` |
| ch6-Q9 | 第二次 convergence 如何處理 | 同一 SessionConverger 不允許重入；raise fatal contract violation |

## 1. 範圍與非目標

### 1.1 本章包含

- `SessionConverger` 的資料模型與三級收斂演算法。
- Level 1 `abort()` 與 Level 2 `force_abort()` 的 timeout、平行調度與結果聚合。
- `ForceAbortReport.destroyed_backends` 到 Ch 5 recovery key 的交接。
- Level 3 fatal exception 與 `main.py` supervision 的控制流。
- 四種 trigger 共用演算法的可重複測試條件。

### 1.2 本章不包含

- Worker / adapter 內部如何停止 native thread 或 child process：Ch 2b。
- In-flight record、task done notice 與狀態轉移：Ch 4。
- Recovery rebuild、ticket 與 barrier：Ch 5。
- External-message buffer policy 的執行順序：Ch 4 / Ch 7。
- Timeout 數值與 YAML schema：Ch 10。
- Fatal log 格式與 process exit code：Ch 11。

本章不 publish Event、不修改 SM state、不直接呼叫 Resource Manager。它只收斂 Ch 4 傳入的 operation，回報被破壞的 backend keys，或以 fatal exception 宣告 已無法證明 process 內資源乾淨。

## 2. 套件與資料模型

```
src/sbd/core/
├── lifecycle.py          # ForceAbortReport / AbortableWorker
└── state_manager/
    └── convergence.py    # SessionConverger 實作
```

Ch 2 的共用值維持：

```python
@dataclass(frozen=True, slots=True)
class ForceAbortReport:
    destroyed_backends: tuple[str, ...] = ()
```

Ch 6 新增：

```python
from dataclasses import dataclass
from typing import Literal, Protocol

ConvergenceTrigger = Literal["rest", "interrupt", "error", "shutdown"]

@dataclass(frozen=True, slots=True)
class ConvergenceResult:
    destroyed_backends: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class CancelTimeoutPolicy:
    abort_default_seconds: float
    force_abort_default_seconds: float
    abort_by_kind: Mapping[str, float]
    force_abort_by_kind: Mapping[str, float]

    def abort_for(self, kind: str) -> float: ...
    def force_abort_for(self, kind: str) -> float: ...
```

Converger直接接收Ch 4 InflightRecord tuple，與已確認的Ch 4 protocol一致。Ch 4在呼叫前先把每個record的 `cancel_requested=True`。Converger只需 `correlation_id` / `phase` / `kind` / `worker` / `task`，不得新增、移除或替換SM的 `_in_flight` dict成員。

## 3. Public 契約

```python
class SessionConverger(Protocol):
    async def converge(
        self,
        records: tuple[InFlightRecord, ...],
        trigger: ConvergenceTrigger,
    ) -> ConvergenceResult: ...
```

實作 constructor：

```python
class DefaultSessionConverger:
    def __init__(
        self,
        *,
        timeouts: CancelTimeoutPolicy,
        logger: logging.Logger,
    ) -> None: ...
```

契約：

- `records` 的 `correlation_id` 必須唯一；重複是 caller bug。
- 已 done 的 target 仍可傳入；Converger 收割狀態後視為已收斂，不重呼 worker。
- 空 tuple 立即回空 `ConvergenceResult`。
- 同一 instance 同時只允許一個 `converge()`；重入 raise `ConvergenceContractViolation`。
- `trigger` 只進 log context；不得改變 Level 1 / 2 的完成證明。
- return 表示每個 target 已完成合作式或強制式 termination proof；outer task 皆已 done。SM handle removal 仍由 Ch 4 已排入 inbox 的 `_TaskCompleted` notice 執行。

## 4. Preflight

`converge()` 在呼叫 worker 前：

1. 驗證 trigger。
2. 驗證 correlation 唯一、timeout 皆為有限正數。
3. 設 `_active=True`，在 `finally` 清除。
4. 依輸入順序建立 target map；輸出排序固定依 correlation id。
5. 對已 done task 呼叫 `task.exception()` 收割：
   - cancelled / normal done：視為已收斂；
   - exception：保存 log context，但不重新發布 `ErrorOccurred`；Ch 4 會依既有 public event / task completion 順序判斷是否 fatal。

Preflight 不檢查 session / turn；Ch 4 在建立 snapshot 前已完成 ownership guard。

## 5. Level 1：合作式 abort()

所有尚未 done 的 target 同時啟動一個私有 `_run_abort(target)` task：

```python
async def _run_abort(target: InFlightRecord) -> _Level1Outcome:
    timeout = policy.abort_for(target.kind)
    try:
        async with asyncio.timeout(timeout):
            await target.worker.abort()
            await asyncio.shield(target.task)
    except TimeoutError:
        return _Level1Outcome(target, escalate=True, reason="timeout")
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        return _Level1Outcome(
            target,
            escalate=True,
            reason="abort_error",
            error=exc,
        )
    return _Level1Outcome(target, escalate=False)
```

規則：

- `abort()` return 後仍等 outer task done；兩者共用同一 target timeout。
- 使用 `asyncio.shield(outer_task)`，避免等待者（主控編排協程）timeout 或被外層取消時把 outer task 一併 cancel。Outer task cancel 不是合法 escalation；整個 `asyncio.timeout` 仍會對 shield 在內的等待計時，超時依然升 Level 3。
- target 自己已 cancelled 且 done 視為 Level 1 success；取消 Ch 6 orchestration task 則 re-raise，交 shutdown/fatal supervision，不吞掉。
- 一個 target timeout 不取消其他 target 的 `_run_abort()`。
- `abort()` exception 是 Level 1 失敗資訊；Converger log warning 後升級該 target。若 worker 依契約另外發布了 `ErrorOccurred`，該事件已排在 Ch 4 inbox，Converger 不去重也不補發。

實作使用 `asyncio.gather(..., return_exceptions=False)`；不得用 `TaskGroup` 的 fail-fast 取消語意，否則單一 target raise 可能取消其他 target 的合作式清理。

## 6. Level 2：強制 force_abort()

只對 Level 1 `escalate=True` 的 target 平行執行：

```python
async def _run_force_abort(
    target: InFlightRecord,
) -> tuple[InFlightRecord, ForceAbortReport]:
    timeout = policy.force_abort_for(target.kind)
    try:
        async with asyncio.timeout(timeout):
            report = await target.worker.force_abort()
            await asyncio.shield(target.task)  # 防止主控編排協程被取消時連帶取消 worker task
    except TimeoutError as exc:
        raise ConvergenceFatalError.from_target(
            target, stage="force_abort_timeout", cause=exc
        ) from exc
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        raise ConvergenceFatalError.from_target(
            target, stage="force_abort_error", cause=exc
        ) from exc
    return target, report
```

不可加入以下 fallback：

- `outer_task.cancel()`；
- 再呼叫一次 `abort()`；
- 把 worker 從 in-flight dict 移除；
- 將 backend 標 unavailable 或注入 null；
- 吞掉 exception 後繼續回 IDLE。

`force_abort()` return 與 outer task done 都必須在同一 Level 2 timeout 內成立。如果 worker 已完成 internal termination proof 但 outer coroutine 仍卡住，系統仍無法證明 operation 已收斂，故直接 Level 3。

## 7. Report 聚合與 trigger 交接

所有 Level 2 target 成功後：

1. 展開各 `ForceAbortReport.destroyed_backends`。
2. 驗證每個 key 是非空 `str`；空值是 `ConvergenceContractViolation`。
3. 以 set 去重，再依字典序轉 tuple，確保測試與 log 穩定。
4. return `ConvergenceResult`。

Ch 4 接到 result 後依 trigger 處置。關鍵時序：`converge()` return 只證明 outer tasks done，對應的 `_TaskCompleted` notice 仍在 SM inbox 未消費、handle 未移除。因此以下每一列的「回 IDLE / flush / resume / 接受新 wake」都不是在 `converge()` return 當下發生，一律先通過 Ch 4 §7.5 統一的「in-flight empty progress gate」（所有相應 `_TaskCompleted` 已消費、`_in_flight` 真正清空）後才由 Ch 4 執行；有 destroyed backend 時再加等 recovery barrier。下表描述的是 gate 成立後的最終處置，時序權威在 Ch 4 §7.5：

| trigger | destroyed 空（§7.5 gate 後） | destroyed 非空（§7.5 gate + recovery barrier 後） |
| --- | --- | --- |
| rest | in-flight 空 → IDLE → flush-to-wake | begin_recovery() → ERROR → barrier clear + in-flight 空 → IDLE → flush |
| interrupt | in-flight 空 → IDLE (discard) | discard → recovery → ERROR → barrier + in-flight 空 → IDLE |
| error | 留 ERROR，等 in-flight empty → IDLE | 留 ERROR，等 recovery barrier + in-flight empty |
| shutdown | 等 handles 移除後停 dispatch，再 reverse stop | 不 rebuild；等 handles 移除後 reverse stop |

- 所有列的 IDLE / flush / discard-完成 均以 Ch 4 §7.5 gate 為前提；Converger / event handler 不得直接 pop record 或在 `converge()` return 當下清 session、resume wake 或接受新 wake。
- Ch 6 不直接呼叫 `begin_recovery()`，避免把 trigger policy 與 RM dependency 注入收斂 演算法；recovery 與 in-flight-empty gate 的協調由 Ch 4 §7.3 / §7.5 執行。

## 8. Level 3 與錯誤型別

```python
class ConvergenceError(RuntimeError):
    pass

class ConvergenceContractViolation(ConvergenceError):
    pass

class ConvergenceFatalError(ConvergenceError):
    def __init__(
        self,
        *,
        correlation_id: int,
        kind: str,
        phase: str,
        stage: str,
        cause: BaseException,
    ) -> None: ...
```

Level 3 觸發：

- 任一 `force_abort()` timeout；
- 任一 `force_abort()` raise；
- Level 2 return 後 outer task 仍未 done直到 timeout；
- report 含非法 backend key；
- Converger reentry 或 target identity 不一致。

`ConvergenceFatalError` 由 Ch 4 dispatch task 原樣逸出，Ch 11 的 main supervisor 記 CRITICAL 後讓 process 結束。Converger 不呼叫 `sys.exit()` / `os._exit()`，以便 main 執行有上限的 logger flush；也不進 ERROR，因 Level 3 已表示同 process 內無法安全恢復。

## 9. Timeout policy

Ch 10 提供：

```yaml
cancel:
  abort_timeout_seconds:
    default: 2.0
    by_kind: {}
  force_abort_timeout_seconds:
    default: 1.0
    by_kind:
      cognition.reasoner: 3.0
```

kind key 使用 Ch 11 的 operation namespace：

```
perception.listen
perception.read
perception.look
cognition.reasoner
action.speak
action.tool
action.rest
```

查不到 override 就用 default。未知 override key 在 config load 時拒絕，不等到 收斂時才發現拼字錯誤。

## 10. Logging

每次 convergence 使用共同 context：

```
trigger, correlation_id, phase, worker_kind, cancel_level, timeout_seconds
```

- Level 1 開始 / 成功：DEBUG。
- Level 1 timeout / raise、升級 Level 2：WARNING。
- Level 2 成功且 destroyed backend 非空：WARNING。
- Level 3：CRITICAL，由 main supervisor 寫一次 root log；Converger 可附 exception context，但不得再寫第二份 traceback。
- 不記錄 payload、prompt、音訊或訊息內容。

## 11. 驗收與測試

最低純軟體測試：

1. 空 target 立即回空 result。
2. duplicate correlation 在呼叫任何 worker 前失敗。
3. 多 target 的 `abort()` 同時開始，不因輸入順序串行。
4. 每個 target 使用自己的 kind timeout。
5. `abort()` return 但 outer task 未 done，不算 Level 1 success。
6. Level 1 timeout 不 cancel outer task，且只升級該 target。
7. Level 1 raise 只升級該 target，其他 target 繼續完成。
8. Level 2 只呼叫 `force_abort()`，任何路徑都不呼叫 outer `task.cancel()`。
9. `force_abort()` return 但 outer 未 done直到 timeout，raise fatal。
10. 任一 Level 2 timeout / raise 都使整批 fatal，不回部分成功 result。
11. 多 report 的 destroyed keys 去重並字典排序。
12. 四種 trigger 在相同 target 行為下得到相同 convergence result。
13. Converger reentry fatal；前一回合 `finally` 後可再使用。
14. orchestration task 被 cancel 時正確 re-raise `CancelledError`。
15. Level 1 worker 已自行發布 `ErrorOccurred` 時，Converger 不補發第二個事件。

Fake worker 以 `asyncio.Event` 控制 abort、force-abort 與 outer task done；測試需 明確斷言 outer task 的 `cancelled()` 保持 false。

## 12. 對後續章節的輸入

- Ch 7：buffer policy 仍由 Ch 4 執行，Ch 6 不直接依賴 buffer。
- Ch 10：固定 `cancel.abort_timeout_seconds` 與 `cancel.force_abort_timeout_seconds` 的 default + per-kind schema。
- Ch 11：固定 `ConvergenceFatalError` 為 Level 3 root cause；main 記一次 CRITICAL 並結束 process。
- `docs/protocol.md`：Audio child cooperative/deferred cancel wire已固定；其他domain仍待gate。本章只依賴`force_abort()`return的termination proof。

## 13. M4B-MVA control-operation convergence

M4B-MVA session open/close pending與generate同樣受SM收斂追蹤，不以非THINK為由漏掉cleanup。
Cancel不論發生於open、generate、close，都須typed terminal、joined worker與
Conversation清理證據；外部cancel不publish正常Fact。無法證明時沿Level2 PGID
termination/waitpid，回報同一backend key供RM recovery；shutdown不rebuild。
Dirty request已清Conversation時結束產品session，不能P5 apology後silent reset續聊；
pre-inference rejection且context未變仍可P5。詳M4B-MVA §4/§9。
0.5秒等既有操作值只作舊profile參考；新watchdog與10秒產品recovery目標分欄，
由凍結profile決定，不以3秒user target直接代替native cleanup deadline。
