# Ch 9. LLMResponse action_payload schema

> M4B-MVA revision（2026-09-05）：本章generic／已Accepted行為維持；
> LLM新session/control/semantic/profile契約依[ch_m4b_llm_production.md](ch_m4b_llm_production.md)，
> 尚待AR_impl_M4B_I與design/spec簽核。不得以舊source已實作視為M4B-MVA Ready。


屬於 `implement.md` 索引 | 對應 `arch.md` §2.7 ~ §2.8 / §3.3 / §4.6 | 狀態：定稿（IR-final 已通過（2026-08-01））

上游：Ch 1、Ch 2b、Ch 4。

## 0. 已確認判斷

| 編號 | 判斷點 | 已確認結論 |
| --- | --- | --- |
| ch9-Q1 | 初版 speak除 `text` 外是否加欄位 | 不加；只接受非空 `text`，voice/speed等無使用者先不進契約 |
| ch9-Q2 | Speak未知欄位 | 拒絕；避免模型hallucinated option被默默忽略 |
| ch9-Q3 | Tool payload envelope | 固定 `{"name": str, "arguments": dict}`，arguments內部由registry tool驗證 |
| ch9-Q4 | Tool schema技術 | Registry同時保存JSON-compatible `input_schema` 與同步validator；runtime不硬綁外部jsonschema套件 |
| ch9-Q5 | Rest非空 payload | 初版不支援；只接受 `{}`，有實際UX action再擴充 |
| ch9-Q6 | Payload validator是否正規化 / 修改dict | 不修改；只驗證，事件nested dict維持publish後唯讀 |
| ch9-Q7 | Reasoner與SM是否共用validator | 是；Reasoner用於P5正規化，SM在THINK Exit做獨立防線 |
| ch9-Q8 | Tool registry何時seal | startup完成、Reasoner開始前seal；runtime不可增刪tool |
| ch9-Q9 | JSON-compatible檢查範圍 | 所有payload遞迴檢查string key與JSON scalar/list/dict；拒絕NaN/Infinity |

## 1. 範圍與非目標

### 1.1 本章包含

* `speak` / `tool` / `rest` 三種payload的exact envelope。
* `ActionPayloadValidator` API、錯誤taxonomy與驗證順序。
* Tool registry schema、seal與提供給PromptBuilder的唯讀view。
* Reasoner / SM / Action worker三層驗證責任。
* JSON-compatible與事件唯讀行為。

### 1.2 本章不包含

* Tool handler本身的domain arguments：各registered tool擁有。
* Tool執行與abort / force-abort：Ch 2b / Ch 6。
* LLM wire output format或LiteRT-LM IPC：Ch 2b / `docs/protocol.md`。
* Query action、完整reasoning loop：`arch.md` §8未定案。
* TTS voice / speed設定：若是裝置固定選項，進Ch 10 TTS config，不由每次LLM輸出。

## 2. 共用型別與 JSON 值

```python
from typing import TypeAlias

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

SpeakPayload: TypeAlias = dict[str, JsonValue]
ToolPayload: TypeAlias = dict[str, JsonValue]
RestPayload: TypeAlias = dict[str, JsonValue]
```

事件仍使用 Ch 1 的 `dict[str, Any]`，避免recursive alias污染所有event imports；本章validator在runtime收窄為JsonValue。

`validate_json_value()`：

* dict key必須是str；
* list / dict遞迴深度上限32，超過拒絕，避免惡意 / 錯誤模型輸出耗盡stack；
* float必須 `math.isfinite()`；
* tuple、set、bytes、datetime、callable與custom object全部拒絕；
* bool先於int判定，兩者都合法。

Validator只讀取，不deep copy、不coerce：

* 不把int轉str；
* 不自動strip後寫回text；
* 不把list轉tuple；
* 不刪未知欄位。

## 3. Speak payload

Exact schema：

```json
{
  "text": "要播放的非空文字"
}
```

驗證：

1. payload必須是dict。
2. keys恰好 `{"text"}`。
3. text 必須是str且 `text.strip()` 非空。
4. 不在本章限制語言或字數；TTS adapter可對超出backend能力的輸入走P5 error。

Speak worker使用原 `payload["text"]`，保留原文內容空白；只用strip做空值判斷。

不加入：

* `voice_id`：裝置backend選擇屬Ch 10；
* `speed` / `volume`：目前沒有per-utterance需求；
* `ssml`：現有TTS契約未聲明支援；
* `emotion` / `emphasis`：沒有renderer / TTS consumer。

需要上述能力時新增明確使用者與worker行為，再擴schema；不採「接受但忽略」。

## 4. Tool payload

Envelope：

```json
{
  "name": "light.set",
  "arguments": {
    "room": "desk",
    "on": true
  }
}
```

Envelope驗證：

1. keys恰好 `{"name", "arguments"}`。
2. name是非空str，符合 `^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$`。
3. arguments是 `dict[str, JsonValue]`。
4. registry已seal且 `contains(name)`。
5. `registry.validate(name, arguments)` 成功。

Tool name使用至少兩段dotted namespace，避免全域短名碰撞。例：

```text
light.set
gpio.set_output
message.publish
```

Unknown tool或arguments不合，在Reasoner正規化階段走條Ch 2b P5 fallback；若仍進入 SM THINK Exit，SM以內部 ReasonerContractViolation 記錄判定原因並直接transition ERROR，不讓exception逸出至main，也不造成process fatal。Tool worker保留defensive validation，處理registry被錯誤替換等不可能狀態時publish `ActionCompleted(status="error")`。

## 5. Tool registry

沿用Ch 2b並補齊seal / schema view：

```python
@dataclass(frozen=True, slots=True)
class RegisteredTool:
    name: str
    description: str
    input_schema: dict[str, JsonValue]
    validate: Callable[[dict[str, JsonValue]], None]
    handler: ToolHandler
    execution_control: ToolExecutionControl | None = None


class ToolRegistry:
    def register(self, tool: RegisteredTool) -> None: ...
    def seal(self) -> None: ...
    def contains(self, name: str) -> bool: ...
    def validate(self, name: str, arguments: dict[str, JsonValue]) -> None: ...
    def schemas(self) -> tuple[dict[str, JsonValue], ...]: ...
    async def dispatch(
        self,
        name: str,
        arguments: dict[str, JsonValue],
    ) -> dict[str, JsonValue]: ...
```

### 5.1 Register / seal

* `name`、`description`、`input_schema`與validator在register時驗證。
* duplicate name raise `DuplicateToolName`。
* `input_schema` 必須JSON-compatible，並至少包含：

```json
{
  "type": "object",
  "properties": {},
  "additionalProperties": false
}
```

* Schema是給LLM / 文件的描述；`validate` callable是本process執行時的權威驗證。兩者不一致是tool owner bug，需由該tool測試覆蓋。
* seal後register raise `ToolRegistrySealed`。
* `schemas()` 依tool name排序，return defensive copy且只含 `{"name", "description", "input_schema"}`，絕不暴露handler。
* seal時registry為空：`action.tool.required=false` 則不把Tool worker註冊進WorkerCatalog，`capability_of("tool")=False`；`required=true`則startup fatal。空registry不可對Reasoner宣稱tool capability可用。

### 5.2 Validation

`registry.validate()` 同步且不得：

* 執行IO；
* 呼叫handler；
* publish Event；
* mutation arguments；
* 查詢runtime硬體狀態。

Capability只回答整個 `tool` action是否可用；單一tool是否註冊由sealed registry 決定，不另進capability map。

## 6. Rest payload

初版exact schema：

```json
{}
```

任何key都拒絕。Rest worker因此採Ch 2b最小no-op實作，立即publish `ActionCompleted(kind="rest", status="ok")`。

> **註**：`arch.md` §2.8 提及的「告別語」等語音互動，在初版設計中係由前置之 `speak` action 承載。`rest` 的 payload 刻意留空 `{}`，純粹作為「不包含實質 IO」的休眠觸發，貫徹 P2 最小化設計原則。日後若需要告別畫面或 earcon，應在本章新增明確 key 與 consumer，不把任意 hint 塞入 open dict。

## 7. ActionPayloadValidator

```python
class ActionPayloadValidationError(ValueError):
    def __init__(
        self,
        *,
        action_kind: str,
        path: str,
        reason: str,
    ) -> None: ...


class ActionPayloadValidator:
    def __init__(self, *, tools: ToolRegistry) -> None: ...

    def validate(
        self,
        action_kind: str,
        payload: dict[str, Any],
    ) -> None: ...
```

驗證順序：

1. action kind在 `{"speak", "tool", "rest"}`。
2. payload是plain dict且JSON-compatible。
3. dispatch到per-kind validator。
4. Tool再查sealed registry與arguments validator。

錯誤只含path與reason，不含備份payload；例如：

```text
action_kind=tool path=$.arguments.pin reason=expected integer
```

Validator可供Reasoner與SM共用同一instance，因它無mutable call state。Tool registry在runtime sealed，驗證結果不受註冊race影響。

## 8. 三層責任

| 層 | 責任 | 不合時處置 |
| --- | --- | --- |
| Reasoner normalizer | M4B-MVA驗semantic text/end、依product policy組canonical mapping，再呼叫validator | 未改context的P5或dirty-session rest |
| StateManager THINK Exit | 獨立驗證kind、payload、next_perceptions與catalog target | 內部 ReasonerContractViolation 診斷 + 直接transition ERROR；非fatal |
| Action worker | Defensive讀取與dispatch | 可翻譯錯誤 -> ActionCompleted(error) |

SM THINK Exit固定依序：

1. 驗證 `action_kind` $\in$ `{"speak", "tool", "rest"}`。
2. 呼叫 `ActionPayloadValidator.validate(kind, payload)`；失敗是資料層違約。
3. 依原順序剔除 `next_perceptions` 中未註冊於sealed WorkerCatalog的kind；每個被 剔除的kind記一筆WARNING，不因單一未知kind拒絕整個response。
4. `action_kind` $\in$ `{"speak", "tool"}` 時，對剔除後清單去重（保留首次出現順序並記 DEBUG）；正規化後清單必須非空，且action target存在於catalog。只有正規化後 空清單或missing target屬SM自檢違約；duplicate本身不違約。 `rest` 完全忽略 `next_perceptions`，Reasoner仍應產空tuple作canonical output。

第1、2、4步失敗時，SM以內部 ReasonerContractViolation 保存不含原payload的 kind / path / reason診斷，直接publish權威 StateChanged(->ERROR) 並走Ch 4 ERROR Entry收斂。此路徑不publish ErrorOccurred、不讓exception逸出至main，也不造成 process exit。第3步剔除後仍有合法kind則保存過濾後tuple並正常進ACTION。

Validator不查capability map；Reasoner在產出前已查，SM只驗證catalog存在。這與 Ch 4 / arch.md及Confirmed的AR-Impl-7責任分界一致。

## 9. Canonical examples

合法：

```json
{"text": "好的，已經完成。"}
{"name": "light.set", "arguments": {"on": True}}
{}
```

非法：

```python
{"text": ""}                    # empty speak
{"text": "hi", "speed": 1.2}    # unsupported key
{"tool": "light.set", "args": {}} # wrong envelope
{"name": "light.set", "arguments": []} # arguments not object
{"farewell": True}             # rest v1 only accepts empty
```

## 10. 錯誤型別與 logging

```python
class ToolRegistryError(RuntimeError): ...
class DuplicateToolName(ToolRegistryError): ...
class ToolRegistrySealed(ToolRegistryError): ...
class UnknownTool(ToolRegistryError): ...
class ToolArgumentsInvalid(ToolRegistryError): ...
```

* Reasoner normalizer遇LLM schema不合：WARNING，記action kind/path/reason，不記 structured response內容或child raw model output。
* SM獨立驗證仍遇schema / payload不合：記一筆不含payload的ERROR自檢診斷後進 ERROR state；不publish `ErrorOccurred`，也不進main fatal path。
* Duplicate / invalid registration：startup fatal，由Ch 5 rollback。
* Runtime unknown tool若在SM驗證階段發現，走上述非fatal自檢ERROR；若只在Tool worker defensive路徑發現，記ERROR並產 `ActionCompleted(error)`。
* Handler exception由Tool worker依Ch 2b P5 / exception層處理。

## 11. 驗收與測試

最低純軟體測試：

1. speak只接受唯一非空text欄位。
2. speak未知欄位 / 非str / 空白拒絕且不mutation input。
3. tool envelope exact keys、dotted name與arguments object。
4. unknown tool在handler執行前拒絕。
5. tool validator同步執行且dispatch不在validate階段發生。
6. rest只接受empty dict。
7. JSON validator拒絕bytes、tuple、custom object、NaN、Infinity與過深nesting。
8. duplicate tool與seal後register失敗。
9. schemas按name穩定排序且不暴露handler / control。
10. schemas defensive copy被caller修改不污染registry。
11. Reasoner與SM使用同一payload得到相同validation結果。
12. validation error message不包含完整payload或可能的secret。
13. SM收到invalid action kind或payload時記錄內部 ReasonerContractViolation 診斷、publish `StateChanged(->ERROR)` 並走ERROR Entry；不publish `ErrorOccurred`、不讓 exception逸出main、process不以exit 4結束。
14. `next_perceptions` 含未知kind但剔除後非空時記WARNING並正常進ACTION；剔除後 為空且action是speak / tool時走相同SM自檢ERROR。
15. 過濾後duplicate由SM保留首次順序去重，不進ERROR，且同kind只啟動一個 perception worker；missing action target仍走nonfatal SM自檢ERROR。

每個registered tool需自帶正反例table-driven tests，證明 `input_schema` 範例與 `validate` callable一致。

## 12. 對後續章節的輸入

* Ch 10：TTS固定voice / speed屬backend config，不進per-action payload。
* Ch 11：Reasoner validation warning與SM自檢ERROR只記kind/path/reason，禁止raw prompt / payload；後者不等於runtime fatal。

## 13. M4B-MVA model output versus canonical action

Model僅text/end，schema见M4B-MVA §2；本章speak/tool/rest仍是Core canonical action契約，
不得把移除model full-envelope誤解為刪除SM/ActionPayloadValidator防線。
next_perceptions由Reasoner產生；M4普通speak為(listen,)，end為rest/{} /()。
End結果不承載farewell text，故不新增speak後自动rest或empty-next speak捷徑。
Tool generic validator維持供M5，M4 real-model quality不要求tool。
