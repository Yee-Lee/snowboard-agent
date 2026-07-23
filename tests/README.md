# tests/ 測試說明

M1 階段的純邏輯單元測試。所有測試不需硬體、不需 AI 模型，只驗證 event bus 與 state manager 的行為。

---

## 生命週期

**這些測試會保留並持續累積**：

- `test_event_bus.py` 與 `test_state_manager.py` 測的是 milestone.md 定義的**常駐骨架**（M1–M4 不重構）——後續階段只加事件與轉移規則，舊測試持續通過
- M2 之後會新增測試（mock pipeline、tool registry、prompt builder 等），**不會取代**現有測試
- 除非契約本身刻意變動（例如拆事件型別），否則測試應永遠可跑
- 若哪次改動讓舊測試失敗，代表**backbone 契約被意外破壞**——這正是它們的價值

---

## 執行方式

需要 Python 3.11+ 與 `pytest`、`pytest-asyncio`。

```bash
cd snowboard-agent

# 全部跑一次
python3.11 -m pytest -v

# 只跑某檔
python3.11 -m pytest tests/test_event_bus.py -v
python3.11 -m pytest tests/test_state_manager.py -v

# 只跑名字含關鍵字的測試
python3.11 -m pytest -v -k wake
python3.11 -m pytest -v -k guard

# 顯示 print / log 訊息
python3.11 -m pytest -v -s

# 失敗時看完整 traceback
python3.11 -m pytest -v --tb=long

# 只跑單一測試
python3.11 -m pytest tests/test_state_manager.py::test_idle_wake_transitions_to_perception -v
```

> Windows 開發機把 `python3.11` 換成 `py -3.11`。

**預期結果**：19 passed

---

## 檔案總覽

| 檔案 | 測試數 | 職責 |
|---|---|---|
| `conftest.py` | — | 共用 fixture：`bus`、`sm_settings`、`sm` |
| `test_event_bus.py` | 5 | 驗證 `core/event_bus/bus.py` 的 pub/sub 行為 |
| `test_state_manager.py` | 14 | 驗證 `core/state_manager/manager.py` 的六狀態機（覆蓋 `docs/arch.md` §11.2） |

---

## `conftest.py` 的 fixture

- **`bus`**：全新的 `EventBus` 實例
- **`sm_settings`**：`StateManagerSettings(error_recovery_seconds=0.0, perception_timeout_seconds=1.0)`——測試用零延遲
- **`sm`**：已綁定 `bus` 的 `StateManager` 實例

每個測試會自動拿到全新的 bus + sm，不會互相干擾。

---

## `test_event_bus.py` — Event Bus 行為（5 tests）

| 測試 | 驗證什麼 |
|---|---|
| `test_publish_delivers_to_all_subscribers` | 同一事件型別的多個 handler 都會被呼叫 |
| `test_subscribers_are_keyed_by_type` | 訂閱依事件型別分派，不同型別彼此隔離 |
| `test_handler_error_does_not_block_other_handlers` | 某個 handler 拋錯不影響同一事件的其他 handler；錯誤會被 log |
| `test_unsubscribed_event_type_warns` | 沒有 subscriber 的事件被 publish 時，log 出 warning（不 crash） |
| `test_unsubscribe_removes_handler` | `unsubscribe` 後該 handler 不再收到事件 |

**共同技法**：測試自建 `Foo` / `Bar` 兩個 dataclass 事件型別（不用真的內部事件），聚焦 bus 機制本身。

---

## `test_state_manager.py` — StateManager 六狀態機（14 tests）

依 `docs/arch.md` §11.2 狀態轉移表逐條測試。輔助類 `Recorder` 訂閱所有 SM 會 publish 的事件（`StartPerception`、`StateChanged`、`SpeakRequested`...），供各測試檢查。

### IDLE 起點（3 tests）

| 測試 | 場景 | 期望 |
|---|---|---|
| `test_idle_wake_transitions_to_perception` | 收到 `WakeDetected(source="button")` | 狀態 IDLE→WAKE→PERCEPTION；publish `StartPerception(kind="listen")` |
| `test_wake_with_text_payload_uses_read_perception` | `WakeDetected(source="event", payload={"text": ...})` | SM 選 `read` perception 而非 `listen` |
| `test_idle_ignores_unrelated_events` | IDLE 狀態下收到 `SpeechFinished` | 狀態不變，log warning |

### PERCEPTION（1 test）

| 測試 | 場景 | 期望 |
|---|---|---|
| `test_perception_result_transitions_to_think` | 走到 PERCEPTION 後收到 `PerceptionResult` | 轉 THINK；publish `StartReasoning(input=result)` |

### THINK（4 tests）

| 測試 | 場景 | 期望 |
|---|---|---|
| `test_llm_response_with_tool_calls_stays_in_think` | `LLMResponse(tool_calls=[...])` | 留在 THINK；publish `ExecuteTool` |
| `test_tool_executed_keeps_state_in_think` | 收到 `ToolExecuted` | 留在 THINK 等下一次 LLMResponse |
| `test_llm_response_with_text_transitions_to_action` | `LLMResponse(text="answer")` 無 tool_calls | 轉 ACTION；publish `SpeakRequested` |
| `test_empty_llm_response_returns_to_idle` | `LLMResponse(text="", tool_calls=[])` | 直接回 IDLE |

### ACTION（2 tests）

| 測試 | 場景 | 期望 |
|---|---|---|
| `test_speech_finished_returns_to_idle_and_publishes_turn_completed` | `SpeechFinished` | 回 IDLE；publish `TurnCompleted` |
| `test_interrupt_during_action_stops_speaking_and_idles` | `InterruptRequested` | publish `StopSpeaking`；回 IDLE |

### Guard（2 tests）

驗證非法時序不會 crash，只 log warning 並忽略。

| 測試 | 場景 | 期望 |
|---|---|---|
| `test_wake_ignored_when_not_idle` | 已在 PERCEPTION 又收到 `WakeDetected` | 忽略；log `WakeDetected ignored` |
| `test_interrupt_ignored_when_idle` | IDLE 下收到 `InterruptRequested` | 忽略；狀態不變 |

### 錯誤與收尾（2 tests）

| 測試 | 場景 | 期望 |
|---|---|---|
| `test_error_transitions_through_error_state_back_to_idle` | 任意狀態收到 `ErrorOccurred` | 進 ERROR 狀態；`error_recovery_seconds` 後回 IDLE |
| `test_shutdown_sets_shutdown_flag` | 收到 `ShutdownRequested` | `sm.wait_until_shutdown()` 立即返回 |

---

## 手動驗收（超出 pytest 範圍）

除了自動化測試，還可以手動觀察 backbone 啟動：

```bash
python3.11 -m sbd.main
```

預期輸出：
```
2026-07-23 ... INFO sbd.main: Snowboard M1 backbone ready; state=IDLE
```
然後停在 IDLE（沒有 wake 實作）。按 **Ctrl+C** 結束。

想手動推事件觀察狀態機，用 REPL：

```python
import asyncio
from sbd.core.event_bus import EventBus, events as ev
from sbd.core.state_manager import StateManager
from sbd.core.config import StateManagerSettings
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')

async def demo():
    bus = EventBus()
    sm = StateManager(bus, StateManagerSettings(error_recovery_seconds=0.5))
    await bus.publish(ev.WakeDetected(source="test"))
    await bus.publish(ev.PerceptionResult(kind="listen", text="hi"))
    await bus.publish(ev.LLMResponse(text="hello"))
    await bus.publish(ev.SpeechFinished())
    print("final state:", sm.state)

asyncio.run(demo())
```

會看到六狀態依序流轉的 log。

> Windows Git-Bash 下若 REPL import 失敗，先執行 `export PYTHONPATH=src` 或改用 `py -3.11 -m pytest` 觀察相同流程。

---

## 加測試的原則

新測試進來時遵守：

1. **一個測試只驗一件事**——命名要能一眼看出意圖
2. **用 fixture 拿共用資源**（`bus`、`sm`），不自己 new
3. **驗證正面與反面**：guard 測試同樣重要
4. **caplog 檢查 log 訊息**時只斷言關鍵字，不比對完整字串（避免格式變動就掛）
5. **測純邏輯，不測硬體**：任何需要 mic、OLED、GPIO、模型的東西，靠 mock 或人工驗證

M2 之後會加更多測試（mock pipeline、reasoner、tool registry 等），本檔案會同步擴充。
