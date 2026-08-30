

# Ch 2b. worker 契約與 library adapter

|本章定義 ASR / Vision / LLM / TTS adapter 與 worker 行為；精確 engine、model、voice、版本、授權與 Pi benchmark gate 見 ../model_spec.md 。


屬於 implement.md 索引 | 對應 arch.md §2.4 / §2.6 / §2.7 / §2.8 / §6.3–§6.8 | 狀態：定稿（IR-final 已通過（2026-08-01））
上文章：Ch 2a core HAL Protocol | 下文章：Ch 3 Event Bus 實作

上游契約：Ch 1 / Ch 2 / Ch 2a · read buffer / consumer 見 Ch 7 · action payload / tool registry 見 Ch 9（均已定義）。

## 0. 本輪判斷點

| 編號 | 判斷點 | 草案結論 |
| --- | --- | --- |
| ch2b-Q1 | Library adapter 是否共用一個大介面 | 否；ASR、Vision、TTS、LLM 各自定義最小 Protocol |
| ch2b-Q2 | Timeout 由誰執行 | Worker 自我計時；SM 只把 perception timeout 傳給 worker |
| ch2b-Q3 | Fact 如何回傳 | 方法回傳 `None`；正常 / P5 路徑 publish 一個 terminal Fact，不可翻譯路徑 publish `ErrorOccurred`，cancel 路徑不 publish 正常 Fact；SM 另等 task done |
| ch2b-Q4 | LLM conversation 是否跨 turn 保留 | 否；Engine 跨 turn 常駐，每次 `reason()` 建立一次無隱藏歷史的 conversation |
| ch2b-Q5 | Tool 如何註冊並提供給 LLM | Tool 一律註冊於 Snowboard `ToolRegistry`；只把 schema 提供給 LLM，禁止 LiteRT-LM 自動執行 handler |
| ch2b-Q6 | Worker 內部 thread / child process 如何強制收斂 | AR-Impl-6 已裁定：worker 管理 internal container；Level 2 先 `force_abort()`，必要時 RM rebuild 並等待 recovery barrier |
| ch2b-Q7 | Read buffer API 是否在本章定義 | 否；本章只定 read worker 行為，buffer 具體 API 留 Ch 7 |

## 1. 共通 worker 實作規則

### 1.1 Execution container 單單次呼叫狀態

每個 in-flight worker 維護一個私有 `_active` 記錄：

```python
# 定義於 Ch 2 / src/sbd/core/lifecycle.py，worker 與 adapter 共用。
# from sbd.core.lifecycle import ForceAbortReport

@dataclass(slots=True)
class ActiveCall:
    outer_task: asyncio.Task[None]
    cancel_requested: asyncio.Event
    force_abort_done: asyncio.Event
```

- 同一 worker instance 同時只允許一個 active call；重入 raise `RuntimeError`。
- `perceive()` / `execute()` / `reason()` 進入時建立 `_active`，在 `finally` 清除。
- `abort()` / `force_abort()` 只操作目前 `_active`；沒有 active call 時為 no-op。
- `_active` 是 worker 內部狀態，不進事件 schema，不由其他模組讀取。
- SM 只持有 `outer_task`；native thread / child process handle 留在 worker 或 adapter 內部，不放入 SM in-flight record 或 Event Bus。

所有 in-flight worker 都提供：

```python
async def abort(self) -> None: ...
async def force_abort(self) -> ForceAbortReport: ...
```

- `start()` return 前，worker 與所有 internal container 必須完成 READY handshake。
- Level 1 `abort()` 只走合作式停止。若 native operation 尚未真正停止，`abort()` 不得假裝成功 return；讓 SM 的 Level 1 timeout 升級。
- Level 2 `force_abort()` return 前，所有 internal operation 必須停止、descendant process 必須以 `waitpid()` 或等價方式確認退出、短期 HW 資源必須釋放，且 outer call 不得再 publish 終態 Fact。
- 純 asyncio worker 的 `force_abort()` 可重用 `abort()`，report 為空。
- 破壞 backend 的強制終止在 `destroyed_backends` 回報確定 RM key；Ch 6 將 report 交 RM rebuild 並建立 recovery barrier，key namespace 由 Ch 5 定義。
- `abort()` 設定 `cancel_requested` 並等待 outer call 合作式結束；只有 outer call 已停止產出且資源釋放後才 return。
- `force_abort()` 完成強制清理後設定 `force_abort_done`，喚醒等待中的 outer call，並等待 `outer_task` 真正 done 後才回傳 report。若 outer 仍卡住，`force_abort()` 本身保持 pending，讓同一個 Level 2 timeout 直接升級 Level 3；禁止用 outer `task.cancel()` 冒充 internal container 的完成證明。
- `stop()` return 前同樣必須確認沒有 descendant process；不得把 orphan 留給 systemd cleanup。

### 1.2 Worker 自我 timeout 與強制清理

Worker 自我 timeout 只有在 operation 已停止且資源已釋放後，才能 publish `PerceptionResult(status="timeout")` 或 Reasoner P5 fallback：

1. operation 到期後先走 adapter / 資源的合作式 `abort()`。
2. 合作式停止完成：可發布正常 timeout / fallback Fact。
3. 合作式停止無法在 Ch 10 / Ch 6 定義的 Level 1 cleanup 上限內完成：worker publish 一個 `ErrorOccurred` 觸發 SM ERROR 收斂，不發布正常終態 Fact，並保持 outer call in-flight，等待 SM 呼叫 `force_abort()`。
4. `force_abort()` 完成後 outer call 才能結束；其 report 由 SM 交 RM rebuild。

因此「使用者等待逾時」可走 P5；「必須破壞 backend 才能停止」屬 execution container 失效，必須走 ERROR + recovery barrier。這條規則適用 Listen、Look、Reasoner、Speak、Tool，不只 LiteRT-LM。

### 1.3 終態 Fact 與 exception

每次正常呼叫只走以下一條：

1. 成功或可翻譯失敗：publish 對應終態 Fact，然後 return `None`。
2. 收斂取消：不 publish Fact，re-raise `CancelledError` 或由合作式 `abort` 結束。
3. 不可翻譯 exception：publish 一個 `ErrorOccurred`；若無強制清理完成，讓原 exception 逸出；若已進 §1.2 路徑，先保持 in-flight，待 `force_abort()` 完成再逸出。

Worker 必須在資源釋放後才 publish 正常終態 Fact。Publish 後不得再進行可能失敗的 library 或硬體操作。

### 1.4 Library adapter 邊界

Library adapter 只隔離第三方 API，不 publish Event Bus、不生成 session / turn / correlation ID，也不知道 SM。Adapter 可以回傳 typed value 或 raise adapter exception；worker 負責依 P5 翻譯為 Fact。

```python
class AdapterError(RuntimeError): ...
class AdapterTimeout(AdapterError): ...
class AdapterRejected(AdapterError): ...
class AdapterUnavailable(AdapterError): ...
```

- `AdapterTimeout`：可翻譯 timeout。
- `AdapterRejected`：輸入被模型 / library 拒絕，但 adapter 仍可繼續使用。
- `AdapterUnavailable`：本次無法提供能力；是否可重試由 worker 決定。
- 未列入的 exception 視為不可翻譯錯誤。
- `CancelledError` 不包成 `AdapterError`。
- 擁有 native thread / child process 的 adapter 必須實作 `abort()` 與 `force_abort()`；後者回傳 `ForceAbortReport`。
- 無可靠 native cancel 的 blocking backend 必須 child-process isolate。
- Adapter `start()` 必須等 READY ACK；`stop()` / `force_abort()` 必須完成 descendant exit proof。跨 process READY / cancel / result schema進`docs/protocol.md`；Audio Protocol v1已建立，其他domain依各自gate補章。

## 2. Perception workers

### 2.1 Listen + ASR

```python
@dataclass(frozen=True, slots=True)
class ASRResult:
    text: str
    confidence: float | None = None
    language: str | None = None

class ASRAdapter(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...
    async def transcribe(
        self,
        frames: AsyncIterator[bytes],
    ) -> ASRResult: ...
```

`Listen.perceive()`：

1. 取得 `audio_input.frames()` iterator。
2. 以 `asyncio.timeout(timeout_seconds)` 包住 `asr.transcribe(frames)`。
3. 成功且 `text.strip()` 非空：publish `PerceptionResult(kind="listen", status="ok", text=...)`。
4. 到期：先 `await frames.aclose()`、再走 `asr.abort()`；只有合作式停止完成才 publish `status="timeout"`。
5. `asr.abort()` 無法在 Level 1 cleanup 上限內完成：依 §1.2 publish `ErrorOccurred` 並等待 SM 呼叫 `Listen.force_abort()`；不得先 publish timeout。
6. `Listen.force_abort()` 強制關閉 frame source、呼叫 `asr.force_abort()`、確認 audio 資源釋放，並彙整 destroyed backend report。
7. `AdapterError` 且無可用文字：publish `status="error"`。
8. `finally` 保證關閉 frame iterator。

`extra` 僅存在的欄位：

```json
{"confidence": 0.91, "language": "zh-TW"}
```

空白 transcript 不算成功；若是純靜音 / VAD 無語音，使用 `status="timeout"`，不另增事件 kind。

### 2.2 Read

Read worker 是 external-message buffer 的被動消費者，不訂閱 `ExternalMessageArrived`。

本章只規定：

- 依 SM 傳入的 session context 取出已歸屬該 session、尚未消費的訊息。
- 按 buffer arrival order 組成單一文字結果。
- 至少一則可用訊息：publish `status="ok"`。
- 指定訊息已被 flush / discard、或 payload 全部無效：publish `status="error"`。
- 到達 `timeout_seconds` 仍無可消費資料：publish `status="timeout"`。
- 成功 publish 前完成 consume mark，避免同一訊息被下一 turn 重複讀取。

Buffer 的 `Message` 型別、claim / consume / flush / discard API 與 overflow 行為留 Ch 7 定義。

### 2.3 Look + Vision

```python
@dataclass(frozen=True, slots=True)
class VisionResult:
    text: str
    extra: dict[str, Any] = field(default_factory=dict)

class VisionAdapter(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...
    async def describe(self, image: bytes) -> VisionResult: ...
```

`Look.perceive()`：

1. 在同一 `asyncio.timeout(timeout_seconds)` 內執行 `camera.capture()` 與 `vision.describe(image)`。
2. 非空描述：publish `kind="look", status="ok"`。
3. 到期：先走 `vision.abort()`；只有 capture / describe 都已停止才 publish `status="timeout"`。
4. 合作式停止無法在 Level 1 cleanup 上限內完成：依 §1.2 publish `ErrorOccurred` 並等待 SM 呼叫 `Look.force_abort()`；不得先 publish timeout。
5. `Look.force_abort()` 終止 Vision internal container、停止 capture、確認 Camera 資源釋放，並彙整 destroyed backend report。
6. Camera / Vision 可翻譯失敗且無描述：publish `status="error"`。

Vision adapter 不直接取得 Camera；拍攝與分析的資源順序由 Look worker 擁有。

## 3. Cognition

### 3.1 PromptBuilder

```python
@dataclass(frozen=True, slots=True)
class ReasoningPerception:
    kind: Literal["listen", "read", "look"]
    status: Literal["ok", "timeout", "error"]
    text: str

@dataclass(frozen=True, slots=True)
class ReasoningInput:
    perceptions: tuple[ReasoningPerception, ...]
    pending_message_count: int
    available_perceptions: tuple[str, ...]
    available_actions: tuple[str, ...]
    tool_schemas: tuple[dict[str, Any], ...]

class ReasoningInputError(ValueError): ...
class ReasoningInputContractError(ReasoningInputError): ...
class ReasoningInputTooLarge(ReasoningInputError): ...

class PromptBuilder:
    def build(
        self,
        *,
        perceptions: tuple[PerceptionResult, ...],
        pending_message_count: int,
        available_perceptions: tuple[str, ...],
        available_actions: tuple[str, ...],
        tool_schemas: tuple[dict[str, Any], ...],
    ) -> ReasoningInput: ...
```

PromptBuilder 是 Snowboard 自有的純 Python 元件，不是第三方 adapter：

- 不做 IO、不管 Resource Manager、不 publish 事件。
- 固定排序 perception：`listen`、`read`、`look`；同kind重複、超過16筆或未知kind直接拒絕，
  不依完成順序改語意輸入。
- 每筆只投影`kind/status/text`；不把`extra`、session/turn/correlation ID傳給child。Ch 1的
  `text=None` canonical映射為`text=""`，但原`status`保持`timeout/error`，不得改成`ok`。
- pending metadata 只輸出 count，不含 ID、payload 或可反查內容。
- perception依`listen/read/look`、action依`speak/tool/rest` canonical order去重；unknown kind拒絕。
  `speak/tool`只有在至少一個perception可作合法`next_perceptions`時才進effective actions；`tool`
  另要求sealed tool schema非空；`rest`必須存在，否則startup composition fatal。
- 將Snowboard `ToolRegistry.schemas()`的defensive copy依tool name排序後提供給模型；每筆只含
  `name/description/input_schema`，不傳validator、execution control或handler。
- 只做 Snowboard 語意資料的排序、正規化與不可變複製；chat-template rendering、tokenization 與 constrained-output 均由 child 擁有。
- 不建立 raw prompt 字串；`ReasoningInput` 依 `docs/protocol.md` 的 `snowboard.llm/1` 傳入 child。
- 要求模型只輸出一個 Ch 9 定義的 action object；tool 選擇正規化為 `LLMResponse(action_kind="tool")`，不允許 LiteRT-LM 自動執行 handler。

Unknown/duplicate kind、negative pending count、invalid tool schema或缺少required `rest`屬
`ReasoningInputContractError`，表示composition/fact違約；Reasoner發布sanitized `ErrorOccurred`並進ERROR，
不得P5掩蓋。單筆text超過4096 code point，或well-formed projection因本turn private content超過16 KiB，
屬`ReasoningInputTooLarge`，child side effect=0並可走P5。若空content+完整static tool projection已超過
16 KiB，則在startup preflight即composition fatal，不等到user turn。

### 3.2 LLMEngineAdapter

```python
@dataclass(frozen=True, slots=True)
class LLMGenerationMetrics:
    init_ms: float
    ttft_ms: float
    prefill_tokens: int
    prefill_tokens_per_second: float
    decode_tokens: int
    decode_tokens_per_second: float
    kv_tokens: int

@dataclass(frozen=True, slots=True)
class LLMGeneration:
    response: Mapping[str, object]
    metrics: LLMGenerationMetrics

class LLMEngineAdapter(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...
    async def generate(self, value: ReasoningInput) -> LLMGeneration: ...
```

LiteRT-LM 實作落點：

```text
src/sbd/cognition/litert_lm/
├── __init__.py
├── adapter.py   # parent-side adapter、watchdogs、recycle policy + IPC client
└── worker.py    # child entrypoint，持有 LiteRT-LM Engine
```

實作約束：

- LiteRT-LM Python 未公開可靠推論 cancellation API，故 Engine 必須放在專用 child process，不得在 Snowboard 主 process 的 thread 內直接推論。
- `start()` spawn child；child驗artifact/config後載入並持有`litert_lm.Engine`，此時只到`ENGINE_LOADED`。每次child start/rebuild都須以相同chat template、model tokenizer、rendered-token檢查與constrained-output path執行固定非敏感pre-warm，close/discard disposable Conversation、output與KV/history後才回`READY`（唯一語意為`INFERENCE_READY`），adapter才return。Pre-warm算startup availability，不藏入第一個user request latency。模型跨IDLE、wake與session常駐，不因每turn重載。
- 每次`generate()`以`snowboard.llm/1`傳送結構化`ReasoningInput`，並建立無隱藏歷史的新
  `Conversation`。Child control loop保持在main thread收CANCEL；每request只建立一個background thread，
  該thread呼叫winner已驗證的同步`send_message(prompt, response_format=ResponseFormat.json(schema))`。
  Worker outcome回control loop後須先join thread，再由control loop送唯一terminal；不對parent暴露文字chunk。
- Chat-template rendered input以exact model tokenizer在inference前強制`<=128` tokens，runtime `prefill_tokens`亦須`<=128`；output ceiling 128、Engine capacity 1024分別驗證。Constrained JSON與runtime capability/tool allowlist各自fail closed；current/forbidden/prior marker只屬固定Gate 3 catalog assertion，不注入一般production request。
- Generation deadline固定15秒；parent另有最多2秒terminal-observation-only grace，只能接收child-owned `TIMEOUT`/`ERROR`，不得接受逾時result。Engine-load/pre-warm、first-token、generation與terminal observation使用不同watchdog/telemetry。
- `abort()`送cooperative CANCEL；child control loop對active Conversation最多呼叫一次`cancel_process()`。
  只有typed worker outcome、thread join、Conversation close與READY terminal全成立時才return；native cancel
  無法收斂時保持pending，交Ch 6 Level 1→2處理。
- Cancellation exception處理須先match專用Cancelled型別，再match其`RuntimeError`等父類；thread/process測試必須capture terminal outcome並assert join，任何`PytestUnhandledThreadExceptionWarning`均為test failure，不得只靠thread已結束形成false pass。
- `force_abort()` 依序 terminate child、在上限內 waitpid，必要時 kill 後再次 waitpid；確認 IPC 關閉且無 descendant 後，回報 LLM backend destroyed。
- `stop()` 優先送 graceful shutdown；逾時同樣 terminate / kill + waitpid，return 前不得留下 child。
- 每個 child 最多接受 8 次 inference attempt；或 post-prewarm owner PSS 增量達 48 MiB；或 target `MemAvailable` 低於 768 MiB 時，adapter 在 terminal cleanup 完成且無 active request 後標記 `RECYCLE_PENDING`。缺少 target sampler 資料須 preflight fail closed；portable 測試使用注入 sampler。
- Planned recycle 只可透過窄化的 `schedule_recovery(("backend.cognition.reasoner.llm",))`／
  `wait_recovery(ticket)`交由RM建立並等待`RecoveryTicket`；舊generation關閉後，rebuild必須重跑
  artifact/config驗證與pre-warm，ticket barrier清除前下一個request不得進入。任何recycle recovery
  失敗均由main-supervised`rm.wait_fatal()`立即Level 3，即使沒有下一個request；不得fallback到其他
  模型或profile。
- Tool handler 只註冊於 Snowboard `ToolRegistry`，絕不傳入 child。
- Core不使用LiteRT-LM automatic/manual function execution surface；child一律由`ReasoningInput.tool_schemas`
  建capability-bound JSON response schema並交`ResponseFormat.json(...)` constrained decode。Tool結果只回
  intent，parent正規化為`LLMResponse(action_kind="tool")`；實際handler僅由
  `SM -> action/tool -> ToolRegistry`執行。
- child 被 `force_abort()` 破壞後不得由 Reasoner 自行重啟；SM 把 report 交 RM，RM rebuild / start 新 backend，recovery barrier 清除前 SM 保持 ERROR。
- 模型路徑、backend、sampling、最大輸出 token、reason timeout、terminate / waitpid timeout 進 Ch 10。
- READY、structured generate、single result、cooperative cancel、shutdown 的 wire schema 已固定於 `docs/protocol.md` §4；不得增加 `CHUNK` 或 raw prompt payload。

Selected winner surface使用同步`send_message(..., response_format=...)`與`cancel_process()`；Core不切換到
未由Gate 2B winner驗證的async decode路徑。Native cancel仍不是Level 2完成證明，因此child-process
isolation與`force_abort()`已由AR-Impl-6定案，不再是待決項目。

官方參考：
- [LiteRT-LM Python API](https://ai.google.dev/edge/litert)
- [LiteRT-LM repository](https://github.com/google-ai-edge/litert-lm)

### 3.3 Reasoner 正規化

Reasoner 依 Ch 2 §2.8 接收本 turn facts：

1. 查詢合法 perception / action capability。
2. 以本turn facts、pending count、capability與sealed tool schemas呼叫`PromptBuilder.build()`，取得
   immutable `ReasoningInput`。
3. 在 config 的 `cognition.reason_timeout_seconds` 內呼叫 `llm.generate(value)`。
4. 驗證回傳 mapping 與 Ch 9 schema；不得在 Reasoner 重新解析 raw JSON 文字。
5. 建構、publish 一個帶原識別符的 `LLMResponse`。

以下情境走 P5 fallback，不 publish `ErrorOccurred`：

| 情境 | Fallback |
| --- | --- |
| LLM clean timeout / 拒答 / 空輸出 | 若 `speak` 可用：apology `speak` + `default_perceptions` |
| `ReasoningInputTooLarge` / rendered input >128 tokens | 同上；write/inference前拒絕且不截斷private content |
| child 回傳 schema 不合 / action 不合法 | 同上，並 log warning，不把 raw output 放 Event |
| `speak`不可用或default perceptions過濾後為空 | 不擅自改派`tool`；產`rest` empty payload |

Fallback 的 `next_perceptions` 只保留 capability 為 true 的 `default_perceptions`；若結果為空，改為 `action_kind="rest"`。

「Clean timeout」表示 operation 已自然結束或合作式 abort 已完成；若 timeout 只能靠 `force_abort()` 破壞 child 才能停止，依 §1.2 改發 `ErrorOccurred`，本 session 進 ERROR，不能同時發布 apology `LLMResponse`。

## 4. Action workers

### 4.1 Speak + TTS

```python
class TTSAdapter(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...
    def synthesize(self, text: str) -> AsyncIterator[bytes]: ...
```

`Speak.execute()`：

1. 依 Ch 9 取出已驗證的非空 `text`。
2. 取得 TTS PCM iterator，交 `AudioOutput.play()` 消費。
3. 播放完成後 publish `ActionCompleted(kind="speak", status="ok")`。
4. TTS / Audio 可翻譯失敗：關閉 iterator、publish `status="error"`。
5. `abort()` 合作式要求 TTS 停止生成並關閉 PCM iterator；被取消時不 publish。
6. `force_abort()` 呼叫 `tts.force_abort()`、強制停止 AudioOutput、關閉 iterator，並在所有資源釋放後回傳 destroyed backend report。

TTS 輸出 PCM 格式必須與 `AudioOutput` config 一致；不在 Speak worker 內隱式 resample。格式不合視為啟動設定錯誤。

### 4.2 Tool Registry + Tool action

```python
class ToolHandler(Protocol):
    async def __call__(self, arguments: dict[str, Any]) -> dict[str, Any]: ...

class ToolExecutionControl(Protocol):
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...

@dataclass(frozen=True, slots=True)
class RegisteredTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    validate: Callable[[dict[str, Any]], None]
    handler: ToolHandler
    execution_control: ToolExecutionControl | None = None

class ToolRegistry:
    def register(self, tool: RegisteredTool) -> None: ...
    def contains(self, name: str) -> bool: ...
    def validate(self, name: str, arguments: dict[str, Any]) -> None: ...
    async def dispatch(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]: ...
```

- Duplicate name 在啟動期 raise `ValueError`。
- `description` 與 `input_schema` 是提供給 LLM 的唯讀定義；不得包含 handler callable 或其他不可序列化物件。
- `validate()` 是同步純驗證；不執行 handler。
- `dispatch()` return 代表命令已成功派發，不等待物理世界完成。
- Handler 的 payload schema 由 Ch 9 定義並註冊。
- Tool action 不直接操作未知 GPIO；每個 handler 由 RM 注入明確依賴。
- 純 asyncio handler 可不提供 `execution_control`；Tool worker 自身的 `force_abort()` 可等價合作式停止。
- 使用 native thread / child process 的 handler 必須提供 `execution_control`；無可靠 native cancel 時同樣必須 process-isolate，不能以 Tool 是 fire-and-forget 為由略過完成證明。
- Tool worker 在 dispatch 期間保存目前 `RegisteredTool`，讓 `abort()` / `force_abort()` 能精確轉送至 active execution control 並彙整 report。

`Tool.execute()` 驗證並 dispatch，成功後 publish `status="ok"`；未知 tool、payload 不合或派發失敗 publish `status="error"`。若 handler 在派發完成後的外部動作失敗，由外部訊息另行回報，不回寫本次 `ActionCompleted`。若 dispatch 本身只能靠 destructive `force_abort()` 才能停止，依 §1.2 走 `ErrorOccurred` + recovery，不得 publish `ActionCompleted(status="error")` 偽裝為一般派發失敗。

### 4.3 Rest

Rest 不擁有 session lifecycle。其最小合法實作是 no-op：

1. payload 為 empty：立即 publish `ActionCompleted(kind="rest", status="ok")`。
2. payload 含 Ch 9 支援的 UX hint：盡力執行；可翻譯失敗 publish `status="error"`。
3. Rest 不呼叫 SM、不 flush buffer、不釋放其他 worker。

Session 結束、in-flight 收斂與 buffer flush-to-wake 仍由 SM 負責。Rest 無 internal container，`abort()` / `force_abort()` 均為尋常 no-op，report 為空。

## 5. P5 降級矩陣

| Worker | 可翻譯結果 | 終態 Fact |
| --- | --- | --- |
| listen | 無語音 / 逾時 | `PerceptionResult(timeout)` |
| listen | ASR 可預期失敗 | `PerceptionResult(error)` |
| read | 無有效 / 可消費訊息 | `PerceptionResult(error/timeout)` |
| look | capture / vision 可預期失敗 | `PerceptionResult(error)` |
| reasoner | clean timeout / 拒答 / 解析失敗 | fallback `LLMResponse` |
| speak | TTS / 播放可預期失敗 | `ActionCompleted(error)` |
| tool | 驗證 / 派發失敗 | `ActionCompleted(error)` |
| rest | UX 收尾失敗 | `ActionCompleted(error)` |

只有 worker 自身不再可信、無法產生契約內 Fact 時才 publish `ErrorOccurred`。若原因是合作式停止失敗，outer call 依 §1.2 保持 in-flight，待 SM `force_abort()` 完成後才逸出；destructive cleanup 不得先發布一般 `status="error"` / `status="timeout"` Fact。

## 6. 檔案落點

```text
src/sbd/
├── perception/
│   ├── listen/{listener.py, asr.py}
│   ├── read/reader.py
│   └── look/{looker.py, vision.py}
├── cognition/
│   ├── reasoner.py
│   ├── prompt_builder.py
│   └── litert_lm/{__init__.py, adapter.py, worker.py}
└── action/
    ├── speak/{speaker.py, tts.py}
    ├── tool/{action.py, registry.py}
    └── rest/action.py
```

`asr.py` / `vision.py` / `tts.py` 放 Protocol 與 adapter exception；具體 backend 以同層子目錄或 backend-named module 實作。若同類 adapter 增加到兩個以上，再拆成 `base.py` + `<backend>/`，不預先擴張目錄。

## 7. 對後續章節的輸入

- Ch 4：SM in-flight record 只追蹤 outer task；ERROR Exit 同時等待 RM recovery barrier。
- Ch 5：定義 `destroyed_backends` key、rebuild registry、READY restart 與 recovery barrier API；capability map 為 startup 靜態值，recovery 成功 / 失敗都不更新，失敗或 timeout 直接 Level 3。
- Ch 6：Level 1 `abort()` -> Level 2 `force_abort()` -> Level 3 的 timeout 與 report 轉交流程；Level 2 不得加入 outer `task.cancel()` fallback。
- Ch 7：Read worker 所需 buffer API。
- Ch 9：speak / tool / rest payload schema，以及 tool registry 驗證入口。
- Ch 10：模型、backend、sampling、reason timeout，以及 per-kind abort / force-abort / waitpid timeout。
- Ch 11：adapter exception 對 log level / `ErrorOccurred.where` 的映射。
- `docs/protocol.md`：worker child 的 READY、request、result、cancel、shutdown wire schema；Audio v1 與 LLM v1 已固定，wake 待其 gate。
