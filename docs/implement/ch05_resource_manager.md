# Ch 5. Resource Manager 實作

屬於 `implement.md` 索引 | 對應 `arch.md` §6.1 ~ §6.2 / §6.5 / §6.8 | 狀態：定稿（IR-final 已通過（2026-08-01））

上游：Ch 2、Ch 2a、Ch 2b、Ch 4。

## 0. 已確認判斷

| 編號 | 判斷點 | 已確認結論 |
| --- | --- | --- |
| ch5-Q1 | config / logger / EventBus 是否也塞進 managed registry | 否；由 `main.py` 依序 bootstrap，之後建立 RM；RM registry 從 StateManager 起管 |
| ch5-Q2 | 建置與啟動如何排序 | 使用 code-declared hard dependency DAG + phase barrier；scoped resolver 只提供已宣告且 READY 的 dependency，producers 最後 start |
| ch5-Q3 | SM 先 start 但 worker 尚未建立如何解 circular dependency | 注入可填充 `WorkerCatalog`；RM 啟動期註冊 worker，所有 producer start 前 seal catalog |
| ch5-Q4 | core null 後 required worker 是否必然 fatal | 否；P1=false 與 P2 start failure 分開。null-backed worker 仍可 start，供固定首 turn 降級；`required` 只決定 P2 自身 start failure 是否中止 |
| ch5-Q5 | capability map 何時可查 | startup 末尾一次 freeze；freeze 前查詢 raise，runtime 永不修改 |
| ch5-Q6 | reasoner 取得 RM 全介面或窄函式 | 沿用 Ch 2 定案，注入會限制 kind 範圍的 `reasoner_capability_of` closure，不交 RM instance / raw method |
| ch5-Q7 | `destroyed_backends` key 格式 | 使用 registry 的 stable dotted `ResourceKey`；與 capability kind 分離，unknown key 視為 fatal contract violation |
| ch5-Q8 | recovery barrier API | `begin_recovery()` 回 `RecoveryTicket`；RM clear barrier 並背景 rebuild，SM await ticket 並以 private notice 喚醒 |
| ch5-Q9 | 可否同時有複數 recovery batch | 否；Ch 6 先聚合本次 destroyed keys後只開一個 batch；active 時再 begin 視為 bug / fatal |
| ch5-Q10 | shutdown 遇到進行中的 recovery | `prepare_shutdown()` 停止 rebuild 並清理局部 replacement；失敗 / timeout 直接 Level 3 |

## 1. 範圍與非目標

### 1.1 本章包含

- `main.py` bootstrap 與 RM ownership 邊界。
- managed resource spec / record、phase + DAG 檢查、startup rollback。
- core real → null fallback 與 worker / InputSource / Adaptor start failure policy。
- `WorkerCatalog` 裝配與 seal。
- capability map P1 + P2 推導、freeze、窄查詢 API。
- stable ResourceKey / recovery registry / ticket / barrier。
- reverse stop 與 shutdown 期間 recovery cleanup。

### 1.2 本章不包含

- worker `abort()` / `force_abort()` 演算法：Ch 6。
- backend child IPC schema：`docs/protocol.md`；Audio v1已固定，其他domain依各自gate補章。
- config dataclass 與 timeout 實際值：Ch 10。
- logger backend：Ch 11。
- systemd unit / restart policy：部署文件。

RM 不 publish Event，也不改 StateManager state。所有 recovery completion 透過控制流 Future / ticket；StateChanged 仍只有 SM 可 publish。

## 2. Bootstrap 與 package

```
src/sbd/core/resource_manager/
├── __init__.py        # re-export ResourceManager / public control types
├── manager.py         # startup、stop、capability、recovery
├── models.py          # ResourceSpec / ManagedRecord / RecoveryTicket / reports
└── catalog.py         # WorkerCatalog / ResourceResolver
```

`main.py` 固定 bootstrap：

1. 載入 config。
2. 建 logger。
3. 建 EventBus。
4. 進入 main startup supervision scope，立即監督 `bus.wait_fatal()`。
5. 建空 `WorkerCatalog`。
6. 建 `ResourceManager(config, logger, bus, worker_catalog)` 並 register specs。
7. 在同一supervision scope內先建立`rm.wait_fatal()` task再`await rm.start_all()`；StateManager start後，
   RM必須在進入CORE phase前把`sm.wait_stopped()`交給main supervision。Runtime同時監督
   `bus.wait_fatal()`、`rm.wait_fatal()`與`sm.wait_stopped()`，任一fatal完成皆exit 4。
8. startup 成功後才啟用 OS signal bridge；Bus / SM 監督沿用到 process 結束。

`config` / `logger` / `EventBus` 不放 managed registry：`config` 已在 RM 前完成；`logger` 是 RM 錯誤報告前提；`EventBus` 無 lifecycle。RM 仍保有引用，供 factory dependency injection。

## 3. Resource registry

### 3.1 Stable key

```python
ResourceKey = NewType("ResourceKey", str)
CapabilityKind = Literal[
    "audio", "display", "camera", "gpio",
    "listen", "read", "look", "speak", "tool",
]
```

`ResourceKey` 格式為小寫 dotted path：

```
state_manager
core.audio              # no-op aggregate, owns capability "audio"
core.audio.input
core.audio.output
core.display
core.display.renderer
core.display.arbiter
core.camera
core.gpio
backend.perception.listen.asr
backend.perception.look.vision
backend.cognition.reasoner.llm
backend.action.speak.tts
backend.action.tool.<registered_tool_name>
worker.perception.listen
worker.perception.read
worker.perception.look
worker.cognition.reasoner
worker.action.speak
worker.action.tool
worker.action.rest
input.button
input.external_message
input.voice_wake
adaptor.mqtt
```

- `ResourceKey` 定位可 start / stop / rebuild 的 instance、backend 或 no-op aggregate。
- `CapabilityKind` 是產品層靜態能力；不可把二者當同一 namespace。
- `core.audio.input` / `core.audio.output` 是實體 records；`core.audio` 是依賴兩者的 aggregate owner，避免兩個 specs 重複宣告同一 capability。任一實體使用 null，coarse-grained `capability_of("audio")` 即為 false。
- `ForceAbortReport.destroyed_backends` 每個值必須是已註冊且 `recoverable=True` 的 `ResourceKey`。
- Tool key 最後一段取 registry name，啟動期驗證只能含 `[a-z0-9_]`。

### 3.2 Spec 與 record

```python
class StartPhase(IntEnum):
    STATE_MANAGER = 10
    CORE = 20
    BACKEND = 30
    WORKER = 40
    OBSERVER = 50
    INPUT_PRODUCER = 60

Factory = Callable[["ResourceResolver"], Lifecycle]
RecoveryHook = Callable[[], Awaitable[None]]

@dataclass(frozen=True, slots=True)
class ResourceSpec:
    key: ResourceKey
    phase: StartPhase
    dependencies: tuple[ResourceKey, ...]
    factory: Factory
    required: bool
    capability_kind: CapabilityKind | None = None
    capability_dependencies: tuple[CapabilityKind, ...] = ()
    null_factory: Factory | None = None
    recoverable: bool = False

@dataclass(slots=True)
class ManagedRecord:
    spec: ResourceSpec
    instance: Lifecycle | None = None
    started: bool = False
    using_null: bool = False
    own_start_ok: bool = False
    recovery_hook: RecoveryHook | None = None
```

宣告範例：

```python
worker_listen_spec = ResourceSpec(
    key="worker.perception.listen",
    phase=StartPhase.WORKER,
    dependencies=("backend.perception.listen.asr", "core.audio"),
    capability_kind="listen",
    capability_dependencies=("audio",), # 指向 CapabilityKind，而非 ResourceKey
    required=True,
    factory=listen_worker_factory
)
```

`ResourceSpec` 由 composition root 的 Python registry 建立；config 只選擇 driver / enabled / required 等產品設定，不可任意注入 dependency key。依賴圖因此能 經 code review 與純軟體測試固定，不把架構 wiring 下放給 YAML。

- `dependencies` 是 hard construction / lifecycle edge，決定 construction / start order；consumer 若缺少任一 hard dependency 就不能建立。
- `capability_dependencies` 只用於 P1，不等同 object graph。
- `capability_kind` 只放在唯一 owner spec；多 instance 共用一個 coarse capability 時以 no-op aggregate spec 收斂（例：`core.audio`）。
- `required` 只作 Perception / Action / InputSource 的政策分歧；Reasoner 固定 required。Core 依 real → null / unavailable 政策處理，Backend 由其 consumer 的 required 政策收斂，Observer / Adaptor 固定 optional。
- null factory 只允許 Ch 2a 定義的 audio / display / camera core spec。
- recoverable spec 在 start 成功後必須提供 hook；hook return 代表 replacement 已 READY 且 owner reference 已原子切換。

### 3.3 Scoped ResourceResolver

RM 每次呼叫 factory 都建立綁定目前 `ResourceSpec` 的 scoped resolver；factory 不得取得完整 RM：

```python
class ResourceResolver:
    def require(self, key: ResourceKey) -> Lifecycle:
        if key not in self._owner.dependencies:
            raise UndeclaredDependencyError(self._owner.key, key)
        record = self._records[key]
        if not record.started or record.instance is None:
            raise ResourceNotReadyError(self._owner.key, key)
        return record.instance
```

因此 DAG 不只負責排序，也限制實際 wiring：
- factory 只能 `require()` 自己明列的 dependency；漏宣告會在 startup 立即失敗。
- record 只有 `await instance.start()` 成功 return 後才標 `started=True`；建立過 object 不等於 READY。
- child-process backend 的 `start()` 必須等 IPC / READY handshake 完成才 return；consumer 不會取得半啟動 instance。
- `config` / `logger` / `EventBus` 是 RM 建立前已 READY 的 bootstrap 前置，不是 managed DAG 節點；factory 可接收 RM 注入的這三者。其他 managed instance 不得由 closure 偷渡，必須經 scoped resolver。

### 3.4 WorkerCatalog

`StateManager` 是例外的大 early subscriber：它先取得同一個可填充 `WorkerCatalog`。RM 在 worker start 成功後註冊 instance：

```python
class WorkerCatalog:
    def register_perception(self, kind: str, worker: Perception) -> None: ...
    def register_action(self, kind: str, worker: Action) -> None: ...
    def set_reasoner(self, reasoner: Reasoner) -> None: ...
    def seal(self) -> None: ...
    def perception(self, kind: str) -> Perception: ...
    def action(self, kind: str) -> Action: ...
    def reasoner(self) -> Reasoner: ...
```

- seal 前只允許 RM register；runtime lookup 尚未開放。
- seal 的必要 kind 由實際啟用的 sources / defaults 一致推導，不無條件要求所有 optional kind（見下方「必要 kind 推導」與 §4.5 startup coherence gate）。
- 所有 InputSource / Adaptor producer start 前先 seal + freeze capability map。
- seal 後 registry immutable；runtime recovery 只替換 catalog 內 worker 所持的 backend，不替換 worker identity。

必要 kind 推導（解 optional worker 與固定首 turn / seal 的政策衝突）

seal 驗證的必要 instance 集合，由下列三者聯集推導，而非硬編 `listen` / `read`：
1. `reasoner` 與 `rest`（此兩者固定需要）。
2. startup coherence gate（§4.5）執行後仍為 enabled 的 InputSources，其 first-turn workers。
3. `config.perception.default_perceptions` 中列出的 kinds。

不在此聯集內的 optional worker（例如 read disabled 且非 default_perceptions），其缺席不會導致 seal 失敗。

對應實作（`ResourceManager._required_catalog_kinds()`）：

```python
def _required_catalog_kinds(self) -> set[str]:
    # 1. 固定需要 reasoner / rest；加入 default_perceptions
    required = {"reasoner", "rest", *self._config.perception.default_perceptions}
    # 2. 三個 wake source 與其 first-turn worker kind 的對應表
    sources = (
        ("input.button",           self._config.input_sources.button.policy,           "listen"),
        ("input.voice_wake",       self._config.input_sources.voice_wake.policy,       "listen"),
        ("input.external_message", self._config.input_sources.external_message.policy, "read"),
    )
    # 3. policy.enabled 且未被 gate 停用（key 不在 _disabled_sources）才納入
    required.update(
        worker_kind
        for key, policy, worker_kind in sources
        if policy.enabled and key not in self._disabled_sources
    )
    return required
```

- `_disabled_sources` 是 §4.5 startup coherence gate 的輸出：gate 停用某 optional source 後，其 key 加入此集合；`_required_catalog_kinds()` 在 gate 之後被呼叫，故推導結果已反映 gate 決策。
- seal 呼叫在 freeze capability map 之後、任何 producer start 之前（見 §4.2 step 6），確保推導使用 gate 後的最終 `enabled` 狀態。
- `policy.enabled=False`（config 層面明確關閉）與「gate 停用」（optional source 的 first-turn worker 缺席）都會使對應 worker kind 從必要集合中排除，兩者語意不同但路徑皆安全：前者不 arm receiver 也不計入 required；後者由 gate 先排除 source 再由此函式排除 kind。

### 3.5 StateManager early-start 依賴與 late-fill

StateManager 於 STATE_MANAGER phase（最早）start。其 Ch 4 §2 constructor 只收四個 early 依賴：`workerCatalog`、`SessionConverger`、`RecoveryControl`、`ActionPayloadValidator`。晚於 SM 的 producer control——`ExternalMessageControl` 與 `WakeListenerControl | None`——不進 constructor，改由 Ch 4 §2 的 one-shot setter `set_external_message_control()` / `set_wake_listener()` late-fill（見下方 B 類）。SM 對這兩者的內部初值為 `None`。這樣拆分後，所有依賴的來源分兩類，兩類都不違反 §3.3 scoped resolver「只取已 READY managed instance」規則：

A. 早於 SM 即可建立、且不 publish 事件的 control / registry（constructor 直接注入）

這些物件無 lifecycle 或其 lifecycle 早於 SM，`main.py` 在建立 SM 前先以純建構方式備妥，不進 managed DAG，因此不需要 scoped resolver：

| SM 依賴 | 建立者 / 時機 | phase / READY 條件 |
| --- | --- | --- |
| `RecoveryControl` | 即 `ResourceManager` 自身（實作 `RecoveryControl` Protocol） | RM 建構完成即 ready；startup 末尾才 set barrier |
| `SessionConverger` | `main.py` 以 `CancelTimeoutPolicy`（來自 config）建構 `DefaultSessionConverger` | 無 lifecycle；建構即 ready |
| `ActionPayloadValidator` | `main.py` 以 `ToolRegistry` 建構（Ch 9 §7）；registry 於 BACKEND / WORKER phase register、Reasoner start 前 seal | validator instance 建構即 ready；其驗證正確性取決於 registry 已 seal，seal 在 Reasoner start 前完成，早於任何 THINK |
| `WorkerCatalog`（空殼） | `main.py` bootstrap step 5 建立空 catalog | 建構即 ready；內容於 WORKER phase late-fill、producer start 前 seal |

`RecoveryControl` / `SessionConverger` / `ActionPayloadValidator` / `WorkerCatalog` 均由 `main.py` 在 `ResourceManager` 建構參數或 SM 建構參數中直接傳入；它們不是 managed records，故 SM 早注入它們不構成「consumer 依賴較晚 phase managed instance」。同一個 `ActionPayloadValidator` instance 在組裝時亦直接傳入 Reasoner constructor（Ch 2 §2.8 `action_validator` 參數），確保 Reasoner normalizer 與 SM THINK Exit 呼叫同一 instance 以符合 ch9-Q7 契約；此 instance 無 mutable call state，不構成 ownership 問題（解決 IR_dev_M2_I）。RM 對其中屬 managed 節點的 backend（例：ToolRegistry 內各 tool 的 handler / execution control）仍走正常 phase / DAG start。


B. 會 publish 事件、lifecycle 晚於 SM 的 producer control（late-fill setter 注入）

`WakeListenerControl`（來自 `voice_wake` InputSource，INPUT_PRODUCER phase）與 `ExternalMessageControl`（來自 `ExternalMessageSource`）都晚於 SM 建立，且其 producer 會 publish wake Signal。為避免「先注入 control、後啟動 producer」缺乏建置邊界，RM 對這兩者採用與 `WorkerCatalog` 相同的 late-fill 模式，並明確拆分 control 與 producer lifecycle：

```python
class StateManager:
    def set_external_message_control(self, control: ExternalMessageControl) -> None: ...
    def set_wake_listener(self, control: WakeListenerControl | None) -> None: ...
```

- store / control 先建立：`ExternalMessageSource` 的 buffer store 與 `ExternalMessageControl` 面在其 `start()`（標 available、拒 ingest 前的建構階段）即可取得；RM 在該 record `start()` 成功後、producer 開始接收外部訊息之前，呼叫 `sm.set_external_message_control(...)`。`voice_wake` 同理：daemon IPC client 建立並 `start()` 成功後填入 `set_wake_listener(...)`；未啟用時填 `None`。
- producer lifecycle 明確晚一步：INPUT_PRODUCER phase 內，RM 對每個 source 固定「`start()`（建立 store / control、備妥 receiver 但尚未 publish）→ late-fill setter → arm receiver（開始 publish Signal）」。因此 SM 一定在收到第一個 wake / external Signal 前已持有對應 control。
- 不倫不類 READY instance：setter 只在對應 record `started=True` 後呼叫；SM 收到的 control 已 READY。SM 這兩個欄位（`_external_messages` / `_wake_listener`，非 constructor 參數）的內部初值為 `None`，在 late-fill 前不會被使用（producer 尚未 arm，不會有事件進 inbox）；setter 的 one-shot / 過晚呼叫 guard 由 Ch 4 §2 定義（`StateManagerWiringError`）。
- SM `start()` 的 `_dispatch_ready` 只保證 loop 就緒可收 private notice 與訂閱；真正 處理 wake Signal 必然發生在 producer arm 之後，此時 control 已 late-fill 完成。

`ExternalMessageSource` 的 store / control ownership 與 producer receiver 拆分細節見 Ch 7 §9 lifecycle；本節只固定 RM 的 late-fill 順序。

## 4. Preflight 與 startup

### 4.1 Registry preflight

硬體前一次驗證：
1. key unique、格式合法。
2. 同一 spec 的 dependency 不重複、不指向自己。
3. dependency key 全存在。
4. dependency phase 不可晚於 consumer phase。
5. 建立 dependency → consumer edges，以 Kahn topological sort 驗證；若最後仍有 未取出的節點即有 cycle。
6. null factory 只出現在允許的 core。
7. capability kind 不重複宣告 owner；合法 kind 集合完整。
8. recoverable spec 有可建立 recovery hook 的方式。

Preflight 成功後 lock spec registry，startup / runtime 不允許新增或改寫 dependency。任一驗證失敗直接 raise `ResourceGraphError`，不呼叫任何 factory / start。

### 4.2 啟動順序

RM 依 phase 由小到大建立 barrier；每個 phase 內對尚未滿足的同 phase edges 做 stable topological sort，同時要求跨 phase dependencies 已是 READY。多個 ready 節點以 registration order 作 tie-breaker，不平行 start，使錯誤與 rollback 順序可重現。整體排序成本為 `O(V + E)`。

單一一般 resource 的啟動骨架：

```python
resolver = ResourceResolver(owner=spec, records=records)
instance = spec.factory(resolver)
record.instance = instance
await instance.start()          # return 必須代表 READY
record.started = True
record.own_start_ok = True
_started_order.append(spec.key)
```

若 factory / start 失敗，record 不標 started、不加入 `_started_order`；core 轉入 §4.3 fallback，其他類別依 §4.4 處理。之後才依序進入：

1. StateManager：subscribe + dispatch ready。
2. Core：audio / display / camera / gpio。
3. Backend：ASR / Vision / LLM / TTS / Tool execution controls。
4. Worker：Perception / Reasoner / Action，成功後填 WorkerCatalog。
5. Observer：Presenter / StatusBar / Adaptor observer subscriptions。
6. freeze capability map → §4.5 startup coherence gate → seal WorkerCatalog（seal 的必要 kind 依 gate 後 `enabled_after_gate` 推導，見 §3.4）。
7. Input producers：button / external_message / voice_wake；會產生 wake Signal 的 adaptor receiver 也放此 phase 最後。每個 source 固定「build + start()（備妥 store / control，尚未 publish）→ RM late-fill SM control (§3.5) → arm receiver」。被 §4.5 gate 停用的 source 不 arm。

如此 SM / logger observers 一定先於 producer ready，又不要求 SM constructor 直接持有尚未建立的 worker instance。

### 4.3 Core real → null

對有 null factory 的 core：
1. 建 real；factory raise 視同 real start failure。
2. `await real.start()`。
3. 失敗時 best-effort `real.stop()`，保留原 exception 作 warning context。
4. 建 null 並 start；record `using_null=True`、`core capability=false`。
5. null factory / start 失敗 → fatal startup rollback。

顯式 `config driver=null` 亦標 `capability=false`，但不是 warning fallback。

GPIO 無 null：factory / start / register setup 失敗 → `capability gpio=false`，依賴其 實體機能 的 InputSource / tool registration 跳過。GPIO instance 若根本未 ready，不注入假 object。

### 4.4 非 core start failure

| 類別 | failure policy |
| --- | --- |
| StateManager | startup fatal、reverse rollback |
| Backend | 記 unavailable 並略過；由依賴它的 worker 自身 required 政策收斂 |
| required worker / Reasoner | startup fatal、reverse rollback |
| optional worker | 記 P2=false、略過 catalog registration |
| Observer | log warning、略過；不影響主流程 |
| required InputSource | startup fatal |
| optional InputSource | log warning、略過 |
| Adaptor | log warning、略過；不影響主流程 |

P1 與 P2 必須分開：
- core dependency 已被 null 替代時，worker 仍可 start 並註冊，讓固定 first-turn mapping 得到契約內 P5 結果；其 capability 因 P1=false。
- `required=true` 只使 worker「自身 factory / start 失敗」（P2=false）成為 fatal，不把 P1=false 自動升級 fatal。
- Backend factory / start 失敗本身先記為 unavailable；依賴它的 worker 無法完成 factory / start 時，才由該 worker 的 required 值決定 fatal 或 P2=false。
- 無 null 且 dependency object 不存在時，scoped resolver 在呼叫 consumer factory 前拒絕取得；required consumer fatal，optional consumer 略過。
- `dependencies` 一律是 hard edge。若某功能不存在時 consumer 仍可完整運作，就不宣告為 dependency；目前沒有需要新增 `optional_dependencies` 的案例。
- optional worker 缺席（P2=false）與「固定 wake mapping 指向它的 source」的一致性，不由 `dependencies` 硬邊處理（source 對 first-turn worker 並非建構期 hard edge），而由 §4.5

### 4.5 Startup coherence gate

固定 wake mapping（Ch 4 §6.3）要求某些 InputSource 一旦啟用，其第一 turn 必然啟動特定 perception worker，且無 runtime fallback：`external_message` source → 首 turn `read`；`button` / `wake_word` → 首 turn `listen`。若該 worker 因 optional start failure 缺席，直接啟用 source 會讓 runtime 第一個訊息找不到 worker。

seal WorkerCatalog 前、freeze capability map 後、任何 producer start 前，RM 執行一次 coherence gate：

```python
對每個 enabled InputSource src (含會產生 wake Signal 的 adaptor receiver)：
    w = first_turn_worker(src)         # external_message->read; button/wake_word->listen
    若 w 不在 sealed-candidate catalog：  # optional worker start failed / disabled
        若 src.required 為 True -> startup fatal ( required source 指向缺席 worker 是 composition 錯 )
        否則 -> 停用 src ( 不 arm receiver、log WARNING )，並從 §3.4 required_kinds 的
               enabled_after_gate 移除
```

- 結果：沒有任何 enabled wake source 指向不存在的 first-turn worker（IR-III-04 完成條件 3）。
- `read` optional start failure ⇒ `external_message` source（若 optional）被 gate 停用：不 arm ingest / receiver、`is_available()` 回 false；已在此前建立的 buffer store 立即 `stop()`（discard、拒新 ingest）。因此不會有「external source enabled 但 read 缺席」的 runtime 狀態（IR-III-04 完成條件 1）。
- gate 在 seal 前跑，故 §3.4 的 `required_kinds` 依 gate 後的 `enabled_after_gate` 推導，seal 不會再要求被降級 source 的 first-turn worker，seal 成功。
- gate 只依 startup 靜態資訊（enabled 集合、catalog candidate、capability map）判定，不涉 runtime 狀態；與「capability map 為 startup static」一致。

### 4.6 Startup rollback

任一 fatal：
1. 停止後續 start。
2. 依 `_started_order` reverse 呼叫 `stop()`，每項使用 shutdown timeout。
3. 單一 stop 失敗只記錄，不阻止其他 cleanup。
4. raise `StartupError(root_cause, rollback_failures)` 給 main；不啟動 system runtime。

## 5. Capability map

### 5.1 推導

啟動期 mutable builder：

```python
_capability_builder: dict[CapabilityKind, bool]
_capability_map: Mapping[CapabilityKind, bool] | None = None
```

Core capability owner：
- owner 及其所有實體 contributors 皆以 real / mock start 成功 → true。
- 任一 contributor 使用 explicit null / fallback null，或無 null 而 unavailable → false。
- `audio` 由 `core.audio` aggregate 收斂 input + output；display / camera / gpio 由各自單一 owner 直接決定。

Perception / Action worker：

```python
capability(kind) = all(capability(dep) for dep in capability_dependencies)
                   AND own_start_ok
                   AND product_specific_availability
```

一般 worker 的 product-specific availability=true；Tool action 另要求至少一個 已啟用且 handler ready 的 registered tool。`rest` 不進 map，永遠作為 session 收尾 fallback。

### 5.2 Freeze 與查詢

所有 worker 完成後：
1. 驗證九個合法 kind 都有 bool。
2. 以 `MappingProxyType(dict(builder))` freeze。
3. 清除 builder 的外部引用。

```python
def capability_of(self, kind: str) -> bool:
    if self._capability_map is None:
        raise RuntimeError("capability map not ready")
    try:
        return self._capability_map[kind]
    except KeyError:
        raise KeyError(f"unknown capability kind: {kind}") from None
```

Reasoner constructor 不取得 RM instance，也不直接取得 unrestricted raw method；RM 組裝時建立 closure：

```python
def reasoner_capability_of(kind: str) -> bool:
    if kind not in {"listen", "read", "look", "speak", "tool"}:
        raise KeyError(f"reasoner cannot query capability kind: {kind}")
    return rm.capability_of(kind)
```

Runtime recovery success / failure、adaptor 斷線、voice-wake daemon 斷線均不修改 map。

## 6. Recovery registry 與 barrier

### 6.1 Public control API

```python
@dataclass(frozen=True, slots=True)
class RecoveryTicket:
    generation: int
    keys: tuple[ResourceKey, ...]

class RecoveryControl(Protocol):
    def begin_recovery(self, keys: tuple[ResourceKey, ...]) -> RecoveryTicket: ...
    async def wait_recovery(self, ticket: RecoveryTicket) -> None: ...
    def recovery_ready(self) -> bool: ...
    async def prepare_shutdown(self) -> None: ...

class ScheduleRecovery(Protocol):
    def __call__(self, keys: tuple[ResourceKey, ...]) -> RecoveryTicket: ...

class WaitRecovery(Protocol):
    async def __call__(self, ticket: RecoveryTicket) -> None: ...

class ResourceFatalMonitor(Protocol):
    async def wait_fatal(self) -> NoReturn: ...
```

RM 內部：

```python
_recovery_ready = asyncio.Event()   # startup 後 set
_recovery_generation = 0
_active_recovery: _RecoveryBatch | None = None
_fatal_ready = asyncio.Event()
_fatal_error: RecoveryFatalError | None = None
```

`recovery_ready()` 只讀 Event 狀態，無 await、無 IO。
`wait_fatal()`由main在RM建構後、任何resource start前建立supervised task；正常runtime永不return。
第一個recovery fatal被latched後set event並raise同一`RecoveryFatalError`，後續錯誤不得覆寫。這使M4b
planned recycle即使尚無下一個`generate()`／SM ticket waiter，failure仍立即進Level 3，不形成unobserved
background-task exception。

### 6.2 begin_recovery()

1. 僅 startup complete、非 shutdown 時合法。
2. 去重 keys 並依 recovery dependency DAG 排序。
3. unknown / 不可 recover key → raise `RecoveryContractViolation`（fatal）。
4. active batch 已存在 → raise；Ch 6 應先聚合本次所有 reports。
5. `generation += 1`、clear ready Event。
6. 建 background `_run_recovery(batch)` task，回 ticket；不等待 rebuild。

空 key 不應呼叫；若發生，回一個 already-complete ticket 但不改 barrier，並記 debug。

`begin_recovery()`另允許M4b LLM planned recycle共用同一barrier，但只限composition root注入
adapter的窄化`ScheduleRecovery` closure，且keys必須exact等於
`("backend.cognition.reasoner.llm",)`。呼叫前adapter須已完成目前wire terminal與Conversation
cleanup、確認無active native inference並原子設定`RECYCLE_PENDING`；不得由Reasoner直接取得RM、
不得在active request中排程，也不得用此路徑recycle其他resource。下一個LLM admission須等待同一
ticket，不能在舊child繼續工作。

Composition root的schedule closure先檢查exact tuple，再委派同一RM instance的`begin_recovery()`；
另注入只委派`wait_recovery(ticket)`的wait closure。兩者都不暴露`recovery_ready`、
`prepare_shutdown`或registry方法。LLM factory只保存這兩個窄介面與回傳ticket，不以polling猜barrier
狀態。Planned path可在目前LLM result交付後由下一個generate等待；無論是否出現下一個generate，
main-owned`wait_fatal()`都監督該batch failure。

### 6.3 Recovery hook 完成語意

每個 hook 必須：
1. 建 replacement或重新啟動被破壞的child/backend；LLM `RECYCLE_PENDING`則先對舊child執行
   SHUTDOWN → bounded TERM/KILL → waitpid，destructive `DESTROYED` path不得假裝再做cooperative success。
2. 完成 READY handshake。
3. 只在 READY 後把 owner reference 原子切到 replacement。
4. 清理舊 IPC handle / process object。
5. return。

Hook 不 publish Event、不修改 capability map。若 replacement factory/start 失敗，cleanup 其局部資源後 raise。
LLM READY只代表`INFERENCE_READY`，所以hook須重做same-lock authenticate、Engine load、mandatory
pre-warm、Conversation/output/KV discard與resource baseline；Engine construction本身不滿足步驟2。

`_run_recovery` 以 RM 擁有的 overall `recovery_timeout_seconds` 包住整批；成功才：
1. set ready Event；
2. resolve batch future。

failure / timeout：
- ready Event 保持 clear；
- batch future set `RecoveryFatalError`；
- 先以同一exception latch `_fatal_error`並set `_fatal_ready`，使main supervision必然被喚醒；
- 不重試、不降 capability、不換 null；
- Ch 4 waiter 將 exception 交 main，Level 3 結束 process。

Ch 4 destructive waiter與main fatal monitor可能同時觀察同一failure；兩者引用同一latched root cause，
main只需形成一次Level 3 disposition。Success不觸發fatal monitor。

### 6.4 wait_recovery()

- ticket generation / keys 必須匹配 active 或剛完成 batch。
- await batch future；成功 return，失敗 raise 同一 root cause 包裝的 `RecoveryFatalError`。
- 多個 waiter 可等待同一 ticket；不允許不同 generation 誤清 barrier。

### 6.5 Shutdown during recovery

`prepare_shutdown()`：
1. 設定 `_shutting_down=True`，拒新 recovery。
2. 若無 active batch 立即 return。
3. 對 recovery orchestration task 發 asyncio cancellation；這只取消 RM 自有控制 task，不被當作 worker Level 2 fallback。
4. recovery hook 必須在 `CancelledError` 分支清理未 READY replacement 並 re-raise。
5. 在 config timeout 內 await cleanup；失敗 / timeout raise `RecoveryFatalError`，直接 Level 3。

完成後 barrier 不必 set；process 進 shutdown，不會再回 IDLE。

## 7. Reverse stop

```python
@dataclass(frozen=True, slots=True)
class StopFailure:
    key: ResourceKey
    error: BaseException

@dataclass(frozen=True, slots=True)
class ShutdownReport:
    failures: tuple[StopFailure, ...]
```

`stop_all()` 前置：SM dispatch 已停止、in-flight 空、recovery 已 prepare shutdown。

1. reverse `_started_order`。
2. 每個 `stop()` 使用獨立 timeout。
3. failure / timeout 記錄後繼續下一個。
4. record 標 stopped，重複 `stop_all()` 不重呼。
5. 回 `ShutdownReport`；main 對 failure 逐一 fatal log，但仍完成剩餘 process cleanup。

EventBus / logger 由 main 在 RM resources 後收尾；EventBus 無 stop，logger 最後 flush。

## 8. Error taxonomy

```python
class ResourceManagerError(RuntimeError): ...
class ResourceGraphError(ResourceManagerError): ...
class ResourceDependencyError(ResourceManagerError): ...
class UndeclaredDependencyError(ResourceDependencyError): ...
class ResourceNotReadyError(ResourceDependencyError): ...
class StartupError(ResourceManagerError): ...
class RecoveryContractViolation(ResourceManagerError): ...
class RecoveryFatalError(ResourceManagerError): ...
```

- startup error 尚未進 runtime，不發布 `ErrorOccurred`。
- recovery fatal 已是 Level 3，不要求 RM publish `ErrorOccurred`。
- optional resource failure 只 log warning。
- core fallback warning 需同時記 real key、backend、root exception、fallback=null。

## 9. 驗收與測試

最低純軟體測試：

1. duplicate key / dependency、self dependency、missing dependency、later-phase dependency、cycle 均在 preflight 失敗，且沒有 factory 被呼叫。
2. Preflight 後 spec registry immutable；startup / runtime 不能改 dependency。
3. Scoped resolver 對 undeclared dependency raise `UndeclaredDependencyError`。
4. Dependency object 已建立但 `start()` / READY 未完成時，consumer factory 不能取得。
5. phase + DAG start order 穩定；Bus / SM fatal supervision 武裝後才允許 producer start。
6. real core factory/start 失敗時 stop real、start null、capability=false。
7. null start 失敗會 rollback 所有已 start resource。
8. GPIO failure 不建立 NullGPIO，依賴 InputSource 按 required 政策處理。
9. Backend failure 由 dependent worker 的 required 政策收斂。
10. Null-backed worker 可 start / 進 catalog，但 P1 使 worker capability=false。
11. required worker 自身 start 失敗 fatal；optional worker 失敗略過且 P2=false。
12. Observer / Adaptor failure 不影響主流程。
13. catalog seal 前 runtime lookup 失敗；seal 後不可 register。
14. capability map freeze 前查詢失敗、unknown kind `KeyError`、freeze 後不可變。
15. reasoner 只取得限制 perception / action kind 的 closure，無 RM 其他方法。
16. destroyed key 去重並依 dependency order recovery。
17. recovery 成功只在所有 hook READY 後 set barrier，capability map 不變。
18. recovery failure / timeout 保持 barrier clear 並 raise `RecoveryFatalError`。
19. unknown destroyed key 或第二個 active batch 為 fatal contract violation。
20. shutdown 取消 active recovery 時局部 replacement 完成 cleanup；失敗走 fatal。
21. startup rollback 與 normal stop 都使用 reverse started order，單一 stop failure 不阻止後續 stop。
22. `stop_all()` 冪等並回完整 failure report。
23. StateManager early-start 依賴（§3.5）：以完整 production-like spec graph preflight + startup 通過，StateManager 於最早 phase start 且其所有依賴皆理解——A 類（四個 constructor 依賴：RecoveryControl / Converger / ActionPayloadValidator / 空 WorkerCatalog）於 SM 建構前備妥；B 類（ExternalMessageControl / WakeListenerControl，非 constructor 參數，Ch 4 §2 one-shot setter）於對應 record `started=True` 後、arm receiver 前 late-fill。斷言 SM constructor 不含這兩個 producer control、無 closure 偷渡未 READY managed instance，且 scoped resolver 規則未被繞過。
24. late-fill 順序：external_message / voice_wake 的 setter 呼叫嚴格早於 receiver arm；SM 在第一個 wake / external Signal 前已持有對應 control。
25. startup coherence gate（§4.5）：read disabled、read optional start failure、external source enabled/disabled、default-perception worker 不可用等組合下——enabled 且 required 的 source 指向缺席 first-turn worker 為 fatal；optional source 指向缺席 worker 被降級且其 buffer store 被 stop；gate 後 seal 的 `required_kinds` 不再要求被降級 source 的 first-turn worker，seal 成功。
26. seal 必要 kind 推導：僅 `{reasoner, rest} U enabled-after-gate first-turn workers U default_perceptions`；optional 且不在此集合的 kind（如 read disabled）缺席不使 seal 失敗。
27. LLM planned recycle只接受exact recoverable key、terminal-clean owner state與single active ticket；active inference、wrong key、Reasoner raw RM access皆拒絕。
28. Planned recycle hook先清舊child再重做authenticate/load/pre-warm；Engine-loaded不set barrier，只有new `INFERENCE_READY`原子切換後成功。
29. 下一個LLM admission等待同一ticket；replacement/pre-warm/cleanup failure保持barrier clear並傳遞`RecoveryFatalError`，不在舊child繼續。
30. Planned recovery在沒有SM waiter與後續LLM request時失敗，`wait_fatal()`仍立即raise同一latched
    `RecoveryFatalError`；main supervision進exit 4，沒有unretrieved task warning或第二份不同root cause。

Fake factory / Lifecycle 以 call log 與 `asyncio.Event` 控制，不碰實體硬體。

## 10. 對後續章節的輸入

- Ch 4：`RecoveryControl`、single active ticket、prepare-shutdown 已固定。
- Ch 6：一次 convergence 聚合全部 `destroyed_backends`，只呼叫一次 `begin_recovery()`；unknown key 直接 fatal。
- Main：與`bus.wait_fatal()`、`sm.wait_stopped()`同時監督`rm.wait_fatal()`；正常shutdown取消該waiter，
  recovery failure以同一root cause走exit 4。
- Ch 10：需要 startup per-resource timeout、stop timeout、`recovery_timeout_seconds`、recovery shutdown cleanup timeout。
- Ch 11：`StartupError` / `RecoveryFatalError` / `ShutdownReport` log 格式，以及 startup 前 Bus / SM fatal supervision 的工具 API。
- `docs/protocol.md`：Audio v1與LLM `snowboard.llm/1` wire已固定；LLM hook return的READY必須是完成pre-warm的`INFERENCE_READY`。
