# M4b Local LLM production design

狀態：**Design review approved；Tester coverage、implementation與Core Gate 3 pending**。

Architecture change：**No**。Persistent child、LiteRT-LM runtime、Reasoner、Resource Manager與三級
收斂邊界不變。USER已於2026-08-29澄清`arch.md`的`Gemma3:e2b`是文字typo；E2B指Gemma 4 E2B，
因此Gate 2A選型不構成model-generation architecture change。Designer不在本輪修改Architect-owned
`arch.md`，但後續引用一律使用Gemma 4 E2B正名。

本章把 `docs/milestones/M4.md` 的 M4b 範圍轉成 Core product 可實作的
persistent-child、runtime identity、failure convergence、POC inheritance 與 Gate 3
驗收設計。架構仍以 `docs/arch.md` 為權威；LLM winner lifecycle與wire schema見
`docs/protocol.md` §4，測試要求見§6；final engine / model / quantization / artifact identity已由
`docs/model_spec.md` §6固定。

Gate 2A已在execution SHA `e2b59fac609e0d768ff3554754363900cbed70a9`、surface SHA-256
`eccbcdc1a099c40a80cc86de8f711711b9ed351400197a505d4f4f466b37b2e1`完成。User選定
`CAND-LRT-G4E2B-MOBILE-R1`（Gemma 4 E2B mobile）為sole model finalist並排除Qwen；Core decision見
`DELIVERY-LLM-POC-M4B-GATE2A-PROVISIONAL-ACK-001`。Gemma R1 P2/P8仍FAIL的歷史不可改寫；後續
`DELIVERY-LLM-POC-M4B-GATE2B-FINAL-WINNER-ACK-001`已接受R3 winner baseline，但該POC waiver
不等於Core product Gate 3 PASS。

本章原先在Gate 2A後形成的Phase A schema與work-package內容只保留為歷史脈絡。若與後續winner
`docs/protocol.md` §4或`docs/model_spec.md` §6衝突，後兩者為implementation authority；current seam
已收斂到`protocol_version="snowboard.llm/1"`，並已由單輪`IR_review_M4B_I`完整審查通過。

## 0. Post-Gate-2B authority and design disposition

### 0.1 Immutable design inputs

| Input | Authoritative value / consequence |
| :--- | :--- |
| Final winner ACK | `DELIVERY-LLM-POC-M4B-GATE2B-FINAL-WINNER-ACK-001`；R3是唯一POC product input |
| Runtime / model | LiteRT-LM API `0.16.0` + Gemma 4 E2B mobile；exact artifact/config identity見`model_spec.md` §6 |
| Wire contract | `protocol_version="snowboard.llm/1"`；exact lifecycle/schema見`protocol.md` §4 |
| Readiness | 每次child start都須完成authenticate → Engine load → fixed disposable pre-warm → `INFERENCE_READY` |
| Machine risk | Attempt 006 P9/P10B維持`FAIL`；POC waiver不得轉成Core product PASS |
| Core exit | single `IR_review_M4B_I` → Tester完整`TR_spec_M4B_I` → WP-01～06 → exact-SHA Gate 3 |

Architecture disposition：**No architecture change / no `AR_impl`**。Persistent child、Reasoner、
process-group Level 2 termination與RM recovery barrier都已存在；本輪只收斂Designer-owned API、
state、config、product lock、maintenance recycle與Gate 3 mapping。`arch.md`中的`Gemma3:e2b`仍按
USER既有澄清解讀為Gemma 4 E2B typo，不據此改寫Architect-owned文件。
Ch 5新增`rm.wait_fatal()`只讓main觀察架構既定的「recovery failure → Level 3」，不新增owner、
fallback或recovery policy。
Ch 5既有`prepare_shutdown()`同時固定shutdown期間取消recovery orchestration、清理未READY replacement
及cleanup失敗升Level 3的語意；它與`rm.wait_fatal()`共同構成本輪所引用的RM surface，不新增LLM owner。

### 0.2 Design approval and remaining Development Ready blocker

Designer已完成§3.1 structured seam、startup/pre-warm、single-flight generation、typed terminal、
planned recycle state machine、real config、tracked lock responsibility、offline package/preflight、
license/notices與known resident-retention defect的可驗證產品處置。

Reviewer已於2026-08-30完成本章、`protocol.md` §4/§6、`model_spec.md` §6、Ch 2b/5/6/9/10與
M4 gate的單輪審查；`IR_review_M4B_I`以Blocking 0標記`Resolved`並歸檔。設計審查已通過，剩餘
Development Ready blocker只有Tester新增§10完整M4B Test IDs，再由Designer以`TR_spec_M4B_I`
確認100% coverage；在該單Resolved前不交Developer，也不宣告Gate 3 PASS或Accepted。

### 0.3 Bounded recycle policy

每個child在pre-warm完成後建立resource baseline。任一條件在operation terminal、Conversation close、
output/reference discard與owner sample完成後成立，即設定`RECYCLE_PENDING`：

- `inference_attempts >= 8`；每次真正建立production Conversation並進入inference即計數，成功、
  timeout、cancel或generation error都不扣回；
- `owner_pss_mib - prewarm_owner_pss_mib >= 48`；
- `MemAvailable < 768 MiB`；或
- owner sample／Conversation cleanup無法證明完成，此項升級為destructive recovery，不當planned success。

Production sampler在child啟動前先read-only驗`/proc/meminfo`與`/proc/<pid>/smaps_rollup`可用；owner PSS
是child process-group leader及其全部live descendants的unique PID PSS總和，不能只看parent controller、
單一thread或sum RSS。每次比較使用原始bytes：`48 * 1024**2`與`768 * 1024**2`，不得先四捨五入
MiB。Baseline在pre-warm cleanup、READY identity與完整owner sample皆成功後只建立一次；replacement
建立自己的新baseline與attempt counter。取樣期間PID消失、任一owner不可讀或欄位非finite/nonnegative
或`type(value) is not int`均視為sample failure，不沿用前一筆值。

8次上限使Attempt 006觀察到的LLM PSS斜率`5.484794 MiB/session`在單一child內預期累積約
`43.878 MiB`，低於48 MiB early trigger與64 MiB frozen late-delta gate。數值是Core產品防線，
不是對POC machine FAIL的重標。Target缺少`MemAvailable`／owner PSS讀取能力時preflight fail closed；
portable tests使用injected sampler，不以macOS缺`/proc`作Skip。

Recycle不得在active request中執行。Parent先讓目前result/terminal完成，再原子清READY並以窄化的
`schedule_recovery(("backend.cognition.reasoner.llm",))` callback進既有RM barrier。下一個generate
只可等待同一`RecoveryTicket`；成功後使用新child generation，failure/timeout傳遞
`RecoveryFatalError`到Level 3，不fallback到舊child、mock、另一model或network。Recovery hook對舊
child執行SHUTDOWN → bounded TERM → bounded KILL → waitpid，之後以相同product lock重走
authenticate/load/pre-warm；只有新`INFERENCE_READY`才原子切換owner reference並解除barrier。
Adapter保存ticket供下一個`generate()`呼叫窄化`wait_recovery(ticket)`；同時Ch 5的
`rm.wait_fatal()`由main常駐監督，所以即使沒有下一request或SM waiter，background recovery failure也
立即Level 3，而不是unobserved task。Planned success可與後續Action執行重疊，但舊LLM child已先退出，
且任何新LLM inference仍被ticket阻擋。

健康terminal取得完整sample而命中8/48/768時是planned path：schedule成功後可把本次validated result交
Reasoner。Cleanup或sample proof失敗則不是planned path：adapter標FATAL並raise sanitized non-P5
failure、不交付本次result；Reasoner發布一個`ErrorOccurred`。其後`abort()`不得假裝cooperative success，
由Ch 6 Level 2呼叫idempotent `force_abort()`取得destroyed key，再由SM既有ticket waiter進ERROR／RM
recovery。這條路徑不由adapter預先開第二個recovery batch。Termination或planned schedule本身失敗
直接Level 3。

## 1. Planning boundary

### 1.1 Designer-fixed scope

- Core controller 與其直接擁有的 LLM child 之 process / IPC ownership；
- READY、structured GENERATE、single RESULT、CANCEL、SHUTDOWN 與 protocol-failure 語意；
- 一次只允許一個 active generation、每 turn 無 hidden history、engine 跨 turn 常駐；
- Reasoner P5 fallback、privacy、timeout、Level 2 termination proof 與 RM recovery barrier；
- selected runtime 必須具備的 product lock、offline install、preflight、inheritance 與
  exact-SHA evidence 欄位；
- Gate 3 工作包與 test-spec coverage skeleton。

### 1.2 Post-design role gates

- Core Tester PASS、M4b Accepted、M4c entry或整體M4 acceptance。
- machine-readable Core lock、offline installation closure與redistribution notice inventory；
- bounded recycle、pre-warm、cancellation與4 GB combined resource defect的實作及產品驗證；
- `snowboard.llm/1`實作、single design/test review及完整Gate 3 evidence。

Gate 2B final ACK已固定LiteRT-LM / Gemma 4 E2B POC winner reference。任何runtime或locked identity
偏離仍須另開change request／必要時`AR_impl`；不得只靠config或adapter名稱私下改變runtime架構。

### 1.3 Gate 2A product implication（immutable history）

以下條件已由後續R3 winner與final ACK滿足，只保留作inheritance lineage，不是current design blocker：

- Gemma R1：P2 `FAIL (3/30)`、P3/P4/P5 `PASS`、P8
  `FAIL / DEPENDENCY_LIMITED_BY_P2`；沒有observed history pollution。
- Qwen：P2 `FAIL (0/30)`、P3/P5 `PASS`、P4需Core threshold decision、P8
  `FAIL / DEPENDENCY_LIMITED_BY_P2`，且carry P7.1 `FAIL / SLOW_RECOVERY`；不進formal Gate 2B。
- New Gemma revision只可調整versioned integration surface，使用bounded adaptation budget與分離的
  development/scored cases；不得覆寫或重標R1 receipt。
- 受影響P2/P8當時須在new frozen revision完成後才能進Gate 2B；實際machine history與User disposition
  以R3 manifest分欄保存。Input未變的P1/P3/P4/P5/P6.1/P7.1/P10A/P11/P12依lock carry；Core仍對
  product delta重驗對應Test ID。

### 1.4 DELIVERY-019 bounded integration adaptation plan（executed history）

本節記錄R1→R3當時可用的POC revision budget；R3/final ACK後不再授權新的POC調參，也不是Core
Developer待執行工作。§3.2的Core general renderer源自原始M1 product contract，並以M4B-OUT/INH列為
POC narrow harness的產品delta，不回頭改寫或延伸本budget。

R1失敗證明目前model/chat-template/PromptBuilder/prompt/config pairing不可交付，不證明Gemma 4 E2B
artifact本身不可用。New revision以「先prompt integration、後必要config」的最小變更順序收斂：

| Stage | 允許動作 | Freeze / exit |
| :--- | :--- | :--- |
| A — failure taxonomy | 只在新的development catalog分析sanitized disposition count：JSON framing、required key、action/payload、current-marker、token truncation；不得讀取或複用R1 scored case的private output來調prompt | 先commit development catalog checksum、diagnostic分類與adaptation budget；不產生P credit |
| B — prompt-only revision | 調整system instruction、Core schema描述、Gemma官方chat-template套用方式、section ordering及最多一個完全synthetic generic example；temperature/top-p/model/runtime/token envelope不變 | 建立一個versioned development candidate；development cases 100%後才能freeze scored candidate |
| C — bounded config revision | 只有B仍可重現明確truncation或template-capacity問題時，才可調整product input/output envelope或generation profile；一次只改一組predeclared變因 | 任何shared identity drift依下表重算affected P；不得以重試、majority vote或post-hoc repair取代single result |
| D — frozen qualification | 在freeze前commit新catalog schema/checksum與expected dispositions；scored catalog須與R1及development cases分離，或由獨立Reviewer持有至freeze後 | P2 30/30與P8全部PASS才可提交Gate 2B entry；valid FAIL保留且該revision停止 |

Adaptation budget固定為最多兩個new development revisions：一個prompt-only revision，加上一個只有在
documented capacity/template root cause時才允許的config revision。超過兩個revision、需要改model
artifact/runtime、需要fine-tune weights或仍無法達成P2/P8時，停止調參並回Core/USER作re-estimation / no-go，
不得無限增加prompt特例。

明確禁止：

- 把R1 scored catalog case、expected literal、nonce/trap或model output抄入system prompt / few-shot；
- 讓normalizer補寫缺少的model fields、把壞JSONrepair成P2 PASS或以P5 fallback計入normal answer；
- 同request自動重試、挑最佳結果、majority vote、提高repetition後平均失敗；
- 放寬P2 exact schema、P8 current-marker / prior-leak規則或重標R1 FAIL；
- 以Qwen、另一Gemma artifact、雲端service或runtime downloader作隱式fallback。

Affected-evidence規則：

| Changed surface | Required requalification before Gate 2B |
| :--- | :--- |
| PromptBuilder / system prompt / product config only | P2、P8；P3若reference normalizer與privacy scanner完全不變可carry |
| Shared chat-template rendering or tokenizer boundary | P2、P4、P5、P8 |
| Token envelope / engine capacity / timeout profile | P2、P4、P5、P8與4GB preflight；Gate 2B P9/P10B照常新跑 |
| Runtime/model artifact or native library | Gate 1/2A affected evidence全部失效；須另提Core change request，不屬本adaptation budget |

每個revision manifest須列changed field、before/after checksum、root-cause hypothesis、development catalog
identity、freeze SHA、scored catalog custody與affected-P decision。這些欄位讓Reviewer一次判斷是否有
overfit、偷改gate或漏跑直接影響面。

## 2. Product topology and ownership

```text
Core controller (no selected-runtime native import)
  └─ LLMEngineAdapter owner
      └─ dedicated LLM process group
          └─ selected runtime + one persistent engine
              └─ one fresh conversation per GENERATE
```

- Parent adapter是child process group、IPC streams、request counter、active operation、
  stderr sanitized tail與temporary work directory的唯一owner。
- Child以`start_new_session=True`啟動，PID=PGID；selected runtime不得再建立逃離該PGID的
  descendant。若runtime不可避免地建立descendant，product delta必須證明parent的單一
  TERM/KILL操作仍能涵蓋並wait所有descendant，否則baseline不可採用。
- Child不得listen socket、執行tool handler、開Audio/Display HAL或接受任意artifact path。
  Tool schema只作prompt input；tool intent回parent後仍由既有Reasoner / SM路徑處理。
- Engine在READY前載入一次並跨IDLE、wake、session與turn常駐。每個GENERATE建立全新、
  無hidden KV/history的conversation；不得以重載engine來偽裝history isolation。
- Prompt與model output可存在於private pipe及process memory，但不得寫入log、result、
  evidence、exception message或stderr。

## 3. Core interfaces and file ownership

M4b把既有text seam收斂成structured input/result；Reasoner仍擁有產品validator與P5，child只負責
frozen render/inference與wire-level exact schema：

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

@dataclass(frozen=True, slots=True)
class LLMResourceSample:
    owner_pss_bytes: int
    mem_available_bytes: int

class LLMResourceSampler(Protocol):
    def sample(self, *, child_pid: int, child_pgid: int) -> LLMResourceSample: ...

class ScheduleRecovery(Protocol):
    def __call__(self, keys: tuple[str, ...]) -> RecoveryTicket: ...

class WaitRecovery(Protocol):
    async def __call__(self, ticket: RecoveryTicket) -> None: ...
```

LiteRT-LM與winner identity已固定；controller-side module不得import native runtime。只有child entry
在strict lock與isolated runtime驗證後lazy import：

```text
src/sbd/cognition/
├── llm.py                         # existing Protocol + mock
├── reasoner.py                    # existing normalizer / P5 owner
├── prompt_builder.py              # bounded ReasoningInput projection；不render model prompt
└── litert_lm/
    ├── __init__.py
    ├── adapter.py                 # parent-side LLMEngineAdapter / recovery owner
    └── worker.py                  # child entry; selected runtime imported lazily here only
requirements/m4b/
├── llm-artifacts.json             # Accepted POC + product identity lock
├── llm-runtime-rpi-cp313.json     # exact offline runtime closure
└── THIRD_PARTY_NOTICES.md
scripts/
└── m4b_llm_product.py             # install / preflight; no model payload in Git
```

`src/sbd/adaptor/framed_child.py`可重用bounded line reader與process-group termination primitive，
但LLM state machine、request/terminal mapping、output validation與request code只能留在LLM module；
LLM wire沒有parent-visible chunk aggregation。

### 3.1 Current exact implementation seam

落點固定為：

```text
src/sbd/cognition/
├── llm.py                         # public structured Protocol + mock
├── reasoner.py                    # product validator / P5 owner
├── prompt_builder.py              # ReasoningInput semantic owner；不render model chat template
├── llm_child_protocol.py          # snowboard.llm/1 pure codec / exact schema
└── litert_lm/
    ├── __init__.py
    ├── adapter.py                 # parent owner / admission / recovery-ticket wait
    └── worker.py                  # isolated child；only native runtime import
tests/fakes/
└── m4b_llm_child.py               # deterministic structured-wire child
tests/
└── test_m4b_ipc_001.py
```

`llm_child_protocol.py`不保留Gate 2A numeric protocol、CHUNK aggregate或raw prompt payload。Current
public seam為：

```python
class LLMProtocolError(AdapterError): ...

@dataclass(frozen=True, slots=True)
class LLMReadyIdentity:
    candidate_id: str
    pairing_revision: str
    platform: str
    runtime_sha256: str
    model_sha256: str
    config_sha256: str

@dataclass(frozen=True, slots=True)
class LLMReady:
    identity: LLMReadyIdentity

@dataclass(frozen=True, slots=True)
class LLMWireResult:
    request_id: str
    response: Mapping[str, object]
    metrics: LLMGenerationMetrics

@dataclass(frozen=True, slots=True)
class LLMWireError:
    request_id: str
    code: Literal[
        "BUSY",
        "INVALID_REQUEST",
        "TIMEOUT",
        "GENERATION_FAILED",
        "CANCEL_FAILED",
        "PROTOCOL_ERROR",
    ]
    state: Literal["READY", "GENERATING", "FATAL"]

@dataclass(frozen=True, slots=True)
class LLMWireCancelled:
    request_id: str

def encode_generate(request_id: str, value: ReasoningInput) -> dict[str, object]: ...
def encode_cancel(request_id: str) -> dict[str, object]: ...
def parse_ready(
    value: Mapping[str, object],
    *,
    expected_identity: LLMReadyIdentity,
) -> LLMReady: ...
def parse_terminal(
    value: Mapping[str, object],
    *,
    active_request_id: str,
) -> LLMWireResult | LLMWireError | LLMWireCancelled: ...
```

Exact rules：

- parent request ID由adapter配置為`llm.<child_generation>.<monotonic_counter>`；counter在同一child
  lifetime嚴格遞增、不重用，且不嵌入session ID、prompt或其他private metadata；
- GENERATE直接傳`ReasoningInput`的bounded structured fields；perceptions最多16筆，
  `pending_message_count >= 0`，capability/tool schema由parent封閉，不傳handler；
- child套用winner chat template與model tokenizer，在inference前拒絕rendered input >128 tokens；
- RESULT response仍由Reasoner以Ch 9 validator再次驗證；child constrained schema不是繞過
  product validator的權威；
- production RESULT必須含完整metrics；缺失、NaN/Infinity、token boundary違約、wrong/duplicate
  terminal、late frame或wrong request ID都是protocol failure；
- `TIMEOUT`只可在15秒generation deadline後產生；2秒grace只收matching terminal，不接受late
  RESULT；`CANCEL_FAILED`／`PROTOCOL_ERROR`使child FATAL並走Level 2；
- codec錯誤只含stage/field/reason，不含perception text、response、tool arguments、credential或path。

Factory seam固定為：

```python
def make_llm_adapter(
    cfg: LLMConfig,
    *,
    schedule_recovery: ScheduleRecovery | None = None,
    wait_recovery: WaitRecovery | None = None,
    resource_sampler: LLMResourceSampler | None = None,
) -> LLMEngineAdapter: ...
```

Real branch要求三個窄介面皆非None，先以pure-Python parser讀tracked lock並驗config paths/identity，
之後才lazy import`litert_lm.adapter`；mock要求三者皆為None、不讀lock、不建立workdir、不import native
runtime。Portable recycle測試直接建real parent adapter並注入fake child、deterministic sampler與ticket
scheduler，不藉mock driver放寬production validation。

### 3.2 Winner renderer, constrained schema and pre-warm

Gate 2B winner evidence與Core product renderer必須分欄，不可誤稱相同：execution SHA
`0c75536e6ee99b502c59438989ca852194648946`的
`poc_llm/harness/litert_lm_gate2b_child_adapter_v2.py`為combined Gate 2B marker harness，只接受
`listen -> speak -> listen`。它證明winner runtime、token/cancel/pre-warm與resource行為，但不是Core
一般`speak/tool/rest` renderer。Core general contract authority來自同一SHA的：

| Input | SHA-256 | Core disposition |
| :--- | :--- | :--- |
| `contracts/m1/prompt-input.schema.json` | `aca834bb448f88dfb403c74c427b5462922ccf23f4f26c1944c47d5731522de6` | §3.1 projection與protocol exact schema |
| `contracts/m1/response.schema.json` | `4be45ee60f603d7349ff5fb29b667d6e59970dd0be3ce9176c03e923e0a6fca2` | Ch 9 general speak/tool/rest base schema |
| `contracts/m1/protocol-frame-pi.schema.json` | `e1af3bc5f83f1456d393d30acd9bcf9b9a8a7f91cbdcbe7aa0136a17c275301e` | selected Pi `snowboard.llm/1` wire、metrics、PING/PONG |
| `contracts/m1/strict-config-pi-gate2b-product-v2.schema.json` | `ce8fa478a1b167042714cb579bb950cf87f7bdb0f80af73fe3a023e16ad77c34` | POC runtime product-config schema |
| Gate 2B product config v2 | `c4557b018733ce8a2f4aa46b375cc7dafb31fbd8c363271deb1156c651e5171e` | runtime/token/sampling/deadline/offline reference；POC absolute paths不得用於Core I/O |

Child `_render_prompt(value)`固定為POC generic M1 renderer，不自行加入scored examples、history或重試：

```python
payload = json.dumps(
    encode_reasoning_input(value),
    ensure_ascii=True,
    sort_keys=True,
    separators=(",", ":"),
)
prompt = (
    "Return exactly one JSON object with action_kind, action_payload, and "
    "next_perceptions. Do not add markdown or commentary. Input: " + payload
)
```

`_build_response_schema(value)`每request由Ch 9 exact schema建立deterministic constrained schema：

1. top-level exact keys固定`action_kind/action_payload/next_perceptions`；branch依canonical
   `speak`、tool name排序、`rest`排列；
2. speak branch固定nonblank text，`next_perceptions`為1筆以上、unique且只可取input available
   perceptions；沒有available perception時PromptBuilder已移除speak branch；
3. 每個tool各有一個branch：name為該registered dotted name的`const`，arguments只constrain為JSON
   object，next-perception規則同speak；tool的closed `input_schema`只放semantic prompt供模型參考，
   實際arguments由Reasoner的sealed registry validator判定並在不合時走P5。這避免把任意tool schema
   誤當LiteRT constraint-provider支援面；不得把handler/validator傳入child；
4. rest branch只接受empty payload與empty next perceptions；
5. input effective actions不存在的branch不得生成。若沒有合法branch、schema無法由LiteRT constraint
   provider接受或renderer/parser違約，startup/pre-request fail closed，不退回unconstrained decode；
6. child取得complete model output後以strict JSON parser建立mapping，再依同一dynamic schema驗證；
   raw text不得越過child。Reasoner仍以Ch 9 validator/capability/tool registry作獨立產品防線。

Inference execution固定沿用winner可行surface：child main control loop收frame，每request啟動一個且僅一個
background thread呼叫同步
`Conversation.send_message(prompt, response_format=ResponseFormat.json(dynamic_schema))`。CANCEL／deadline
由control loop對同一Conversation最多呼叫一次`cancel_process()`；worker只把typed outcome交回control
loop，control loop先join worker、確認Conversation close/reference discard，才emit terminal。不得換成
async iterator、讓worker thread自行寫wire，或以thread不再alive取代outcome/join assertion。

固定public pre-warm輸入為：

```json
{"perceptions":[{"kind":"listen","status":"ok","text":"Say ready."}],"pending_message_count":0,"capabilities":{"perceptions":["listen"],"actions":["speak"],"tools":[]}}
```

它走同一renderer、exact model chat template/tokenizer、dynamic speak schema與Conversation cleanup；
application prompt SHA-256固定為
`4f3bc3e09b3b1693812c749765cfce5899dc11933de06623dbfc82a61a50472d`。Model output只要求通過
dynamic schema且decode token >0，隨後完整丟棄。Gate 2B current/forbidden/prior marker是Gate 3 fixed
catalog的獨立品質assertion，不是每個production request都注入的hidden欄位。

## 4. Parent adapter lifecycle

Parent state固定為：

```text
STOPPED
  -> AUTHENTICATING
  -> STARTING
  -> ENGINE_LOADED
  -> PREWARMING
  -> READY
  -> GENERATING -> READY
  -> RECYCLE_PENDING -> RECOVERING -> AUTHENTICATING
  -> DESTROYED
```

1. `start()`先以tracked lock驗isolated runtime、wheel/native/model/config identity與private work root，
   再spawn child。Model full hash在spawn前完成，不計入READY timing，也不得在child READY路徑重做。
2. Child建Engine後進`ENGINE_LOADED`，此時拒絕GENERATE。它以同一winner renderer/tokenizer/
   constrained-output path跑固定public pre-warm，close disposable Conversation並丟棄output/KV/reference。
3. 只有收到§3.1 exact READY、state/identity全吻合且parent resource baseline完成，`start()`才return。
   重複`start()`只在READY為idempotent；其他nonterminal state拒絕reentry。
4. `generate(value)` single-flight；READY才配置request ID並送structured input。RESULT只有在response、
   metrics、state與request ID驗完後建立`LLMGeneration`；wire沒有CHUNK或partial product output。
5. Terminal後parent要求child已close Conversation、清request-local reference並回READY，再取owner sample、
   更新attempt count及§0.3 trigger。健康trigger先設定`RECYCLE_PENDING`並建立RecoveryTicket，才把
   目前result交回Reasoner；cleanup/sample failure依§0.3 destructive path不交result。因此下一個request
   不能落到舊child。
6. `generate()`遇`RECYCLE_PENDING/RECOVERING`只await該ticket；success後重新admit，fatal則原樣
   傳遞。不得以BUSY、空output或P5掩蓋recovery failure。
7. READY identity mismatch、pre-warm failure、invalid first frame、EOF或startup timeout都先完成
   TERM → KILL → waitpid、關streams、刪workdir，再raise；不留下半啟動child。
8. `stop()`在READY送SHUTDOWN；GENERATING先走既有cancel convergence。若全域shutdown撞上
   RECOVERING，由main先呼叫RM-owned`prepare_shutdown()`取消／等待recovery，再依reverse order呼叫
   adapter `stop()`；adapter不取得該control。所有return路徑都需process/IPC/workdir cleanup proof。

## 5. Cancel, timeout and recovery

### 5.1 Cooperative request path

- Reasoner外層等待使用`AppConfig.cognition.reason_timeout_seconds`；child generation固定15秒，
  parent terminal-only grace固定2秒，三者不可混成單一timeout。
- Reasoner timeout後呼叫`llm.abort()`；adapter只送一次matching CANCEL。只有typed CANCELLED、
  worker joined、Conversation/output/reference discarded且child回READY後才return，Reasoner才可P5。
- LiteRT-LM `Cancelled`分支必須先於`RuntimeError`父類捕捉；測試capture實際worker outcome，
  禁止`PytestUnhandledThreadExceptionWarning` false-pass。
- 若native cancel沒有在500 ms完成，`abort()`保持pending；Ch 6 Level 1上限到期後Reasoner發布一個
  sanitized `ErrorOccurred`、不發布fallback，outer call留在in-flight等待Level 2。
- CANCEL、TIMEOUT或GENERATION_FAILED只要child成功清request-local state並回READY，也計入§0.3
  inference attempt；cleanup無法證明時一律走Level 2，不當可恢復request error。

### 5.2 Destructive recovery and planned recycle

- `force_abort()`對完整PGID送SIGTERM，2秒後仍存活才SIGKILL並再等1秒，最後waitpid、關IPC、
  清workdir並驗orphan/descendant為零。成功後state=`DESTROYED`，回
  `ForceAbortReport(("backend.cognition.reasoner.llm",))`。
- Ch 6 destructive path與§0.3 planned recycle共用同一RM key、RecoveryTicket、hook與barrier；
  差別只在舊child entry state。Planned path從`RECYCLE_PENDING`先嘗試SHUTDOWN，destructive path
  從`DESTROYED`直接建replacement。
- Hook只在新child完成same-lock authenticate/load/pre-warm/READY後原子切換reference。Capability map
  不變，Reasoner不自行restart，舊child永不重新admit。
- 任一TERM/KILL/waitpid、local-ready/ticket identity、replacement start或pre-warm failure都讓RM
  barrier保持closed並raise`RecoveryFatalError`；不重試、不換null/mock/model、不降級成P5。

## 6. Result validation and history isolation

Parent回`LLMGeneration(response, metrics)`；Reasoner與`ActionPayloadValidator`仍是產品權威：

1. Parent先驗RESULT exact keys、finite metrics與token bounds；Reasoner再驗response exact keys
   `action_kind`、`action_payload`、`next_perceptions`及Ch 9 capability/tool schema。
2. `ReasoningInputTooLarge`、active request的`INVALID_REQUEST/READY`與
   `GENERATION_FAILED/READY`可由Reasoner依P5轉fallback；`TIMEOUT`只有合作式cleanup證明後可P5。
   `ReasoningInputContractError`走sanitized ErrorOccurred/ERROR；BUSY/desync、FATAL、identity、protocol
   或recovery failure不得翻譯。
3. Constrained decoder或child聲稱schema-valid不取代Reasoner validator。Unknown/empty/bad mapping、
   unavailable action/tool或剔除後空next perceptions仍走既有P5/SM contract。
4. 每次GENERATE建立fresh single-turn Conversation並在finally close。Gate 3至少以五組污染前一turn
   的case驗後一turn只依目前`ReasoningInput`；未觸發recycle時child PID與Engine load count不變，
   觸發時則只允許預期generation切換且重新pre-warm。
5. PromptBuilder只建立bounded semantic `ReasoningInput`，不render selected chat template。Child
   renderer只接收已定義perception、payload-free pending count、capability與sealed tool schema。
6. Prompt、perception text、model response、tool arguments、credential與private path不得進stdout、
   stderr、exception、telemetry、runner command或evidence；只保存public digest、timing、token count、
   child generation、trigger reason與resource sample。

## 7. Config and strict identity

`LLMConfig` current product shape固定為：

```python
@dataclass(frozen=True, slots=True)
class LLMConfig:
    driver: Literal["mock", "litert_lm"] = "mock"
    runtime_python: Path | None = None
    model_path: Path | None = None
    product_config_path: Path | None = None
    artifact_lock_path: Path | None = None
    profile_id: str | None = None
    child_ready_timeout_seconds: float = 45.0
    generation_timeout_seconds: float = 15.0
    terminal_grace_seconds: float = 2.0
    child_terminate_timeout_seconds: float = 2.0
    child_kill_wait_timeout_seconds: float = 1.0
    rebuild_ready_timeout_seconds: float = 10.0
    recycle_max_inference_attempts: int = 8
    recycle_owner_pss_delta_mib: int = 48
    recycle_min_mem_available_mib: int = 768
```

Real driver規則：

- `runtime_python`、`model_path`、`product_config_path`、`artifact_lock_path`皆為absolute file；
  `profile_id` exact等於`litert-lm-v0.16.0-pi-g2b-r5`；
- 上述numeric值須與本節完全相等；YAML不得放寬token/sampling/deadline/recycle，selected product
  profile的input/output/capacity/temperature/top-p/threads由checksum-matching product config載入；
- `cancel.abort_timeout_seconds.by_kind["cognition.reasoner"]`固定0.5秒；
  `resource.recovery_timeout_seconds`須大於10秒rebuild READY加舊child cleanup上限，repository
  product default維持30秒；
- tracked lock保存expected identity/digest，YAML只提供path與driver/profile selector，不可覆寫
  candidate、runtime/model/config checksum、license、source或fallback；
- `product_config_path`內容須exact hash為`c4557b...`。其中POC `runtime_path/model_path`與
  `test_profile`只作immutable provenance：Core不得開啟其`/tmp/llm-poc-*`路徑。Core實際isolated
  interpreter/model位置只取本`LLMConfig`，再以product config的runtime/model digest及artifact lock
  驗證；其所有numeric/offline欄仍須逐欄cross-check，不得只驗整檔hash；
- factory在child、native import、workdir、sampler與RM registration前完成shape、path及lock parsing。
  Missing/extra/mismatch一律fail closed且side-effect count為零；
- spawn使用allowlisted environment：`PYTHONNOUSERSITE=1`、bytecode write disabled、移除`PYTHONPATH`／
  `PYTHONHOME`／`LD_PRELOAD`，額外`LD_LIBRARY_PATH`只指向verified runtime closure（platform system ABI
  libraries仍由Debian loader提供）。Child在Engine construction前
  才lazy import runtime，並由loaded module/distribution實際路徑驗證其位於closure內；實際loaded native
  library須open-no-follow、regular-file且SHA-256=`9b3a...`。Import path、loader path或digest漂移即startup
  failure，不以READY自報欄位取代；
- mock driver的四個path/profile皆須為None，不讀lock、不啟用target resource sampler；test可由constructor
  注入deterministic sampler與recovery callback，不靠YAML放寬production values；
- real `ResourceSpec` key固定`backend.cognition.reasoner.llm`、`recoverable=True`，instance與
  hook指向同一adapter owner；hook不得建立第二個獨立owner。

## 8. Product lock, packaging and offline closure

Gate 2B final ACK已到位。`requirements/m4b/llm-artifacts.json`為strict exact-key tracked lock，至少
包含下列top-level object；所有SHA為lowercase 64-hex、所有Git SHA為40-hex，unknown/extra/missing key
均在side effect前拒絕：

| Object | Required fields / fixed consequence |
| :--- | :--- |
| `lock` | `schema_version=1`、`protocol_version="snowboard.llm/1"`、lock自身不含absolute deployment path |
| `poc_reference` | final ACK ID、execution/closure/publication full SHA、R3 manifest ID、formal evidence ID與sanitized digest |
| `candidate` | `CAND-LRT-G4E2B-MOBILE-R1`、`litert-lm-v0.16.0-pi-g2b-r5`、`pi-debian13-aarch64` |
| `runtime` | API `0.16.0`、source commit`924e79...`、exact wheel filename/digest、native library digest`9b3a...`、Apache-2.0 |
| `model` | exact source repo/revision、filename、size`2588147712`、digest`181938...`、embedded mobile quantization、Apache-2.0 |
| `product_profile` | POC config locator/digest`c4557b...`、config-schema digest`ce8fa...`、prompt/response/Pi-protocol schema locators與digests`aca834...`/`4be45e...`/`e1af3b...`、pre-warm prompt digest`4f3bc3...`、128/128/1024、0.0/1.0/4與all deadlines/offline flags |
| `runtime_closure` | `llm-runtime-rpi-cp313.json` relative locator及其implementation-time computed digest；manifest列出isolated interpreter、installed distribution與native files的relative path/size/digest，不接受placeholder |
| `licenses` | runtime/model各自source metadata locator、SPDX`Apache-2.0`、repository-relative license/notice locator |

Known shortened digests above are prose labels only；JSON須保存`model_spec.md` §6與§3.2列出的完整值。
Lock parser逐欄比較，不以lock內自稱identity取代expected constants。Model、wheel、native binary、raw
prompt/output與POC evidence payload保持Git-external；tracked lock、runtime manifest、license text與notices
不得包含它們或使用者absolute path。

`m4b_llm_product.py`只提供：

- `install`：接受caller-supplied、checksum-matching offline inputs；在new same-filesystem staging建立
  isolated runtime，使用no-index/no-deps或selected runtime等價的locked安裝方式；驗完才atomic
  rename，拒絕existing output；
- `preflight`：read-only驗install inventory、model/runtime/config/notice identity、Pi 5 / Debian 13 /
  CPython 3.13、Core candidate SHA與protected paths clean；runtime manifest每筆file以open-no-follow／
  regular-file檢查及streaming SHA驗證，拒絕symlink、extra/missing file與system-site import；在child啟動前
  fail closed。

兩個subcommand都不得下載、解析branch HEAD、fallback、輸出private path或覆寫既有install。
正式target acceptance另在network-disabled environment執行並證明zero network attempt；單純DNS失敗
或未配置credential不算offline證據。Selected runtime/native package不得加入Core controller的
`[project.dependencies]`，也不得被controller-side module import；只存在於Git-external isolated
runtime closure。

## 9. POC inheritance and Core delta

POC PASS不等於Core PASS。Gate 2B final ACK後，Designer建立逐項mapping：

| POC area | Core Gate 3 disposition |
| :--- | :--- |
| P1 / P6 / P7 lifecycle | 以Core parent、Ch 6、RM barrier重跑；POC只繼承candidate行為與已知限制 |
| P2 / P3 result quality | 繼承fixed catalog比較；用Core PromptBuilder / validator重跑bounded product catalog |
| P4 performance | 繼承candidate selection數據；在Core product topology量測delta，不自行改門檻 |
| P5 timeout | 以config-driven Reasoner timeout與Core child cleanup重跑 |
| P8 history | 以persistent engine + fresh conversation在Core exact SHA重跑 |
| P9 / P10B combined | 以Accepted M4a product input重跑Core-ownedcomposition/resource/session；不得用surrogate |
| P11 provenance | 驗product lock、offline install與完整notice inventory |
| P12 offline | 在Core exact SHA下重跑network-disabled product session |

正式inheritance row至少含POC delivery ID/full SHA、manifest/evidence locator及checksum、candidate/pairing
identity、classification、inheritance reason、Core product SHA、delta Test ID/result、result locator與
acceptance run ID。只有「沿用POC」或缺locator/checksum時fail closed。

## 10. Test coverage handoff

Reviewer核准完整M4b design後，Tester在`docs/test_spec/test_spec_M4.md`新增完整M4B章節。Designer
不直接修改Tester-owned spec；`TR_spec_M4B_I`須證明下列風險100%有可觀察assertion後才可Resolved。

### 10.1 Portable protocol minimum

`M4B-IPC-001`至少覆蓋：

1. 16 KiB control boundary、fragment/coalesce、valid UTF-8 JSON與extra/missing/unknown key fail closed；
2. READY只能在pre-warm完成後出現，exact winner identity任一欄mismatch都terminate/waitpid/cleanup；
3. string request ID regex、child-generation/counter monotonicity、wrong/duplicate/late terminal；
4. structured GENERATE的canonical order、duplicate/16-perception/4096-char/16-KiB boundary、
   `None -> ""`+status preservation、pending count、capability/tool exact schema，以及ID/extra/handler排除；
5. generic renderer bytes、capability-bound dynamic speak/tool/rest branches、strict raw JSON parse、RESULT
   exact action mapping、finite metrics與prefill/decode/KV 1..128/1..128/1..1024 boundaries；
6. 15秒generation與2秒terminal-only grace分離；grace內late RESULT仍不可成功；
7. CANCELLED typed outcome、single native cancel、joined worker、Conversation discard、healthy next request及
   zero unhandled-thread warning；
8. BUSY/INVALID_REQUEST/TIMEOUT/GENERATION_FAILED/CANCEL_FAILED/PROTOCOL_ERROR state與P5/FATAL分界；
9. stdout/stderr/caplog/result不含perception、response、tool args、credential或private path；
10. M4A protocol/lifecycle regressions保持通過，證明未改寫Accepted Audio contract。

### 10.2 Full Gate 3 Test IDs

| Test ID | Platform | Required risk |
| :--- | :--- | :--- |
| `M4B-CFG-001` | portable | exact real config、mock isolation、factory三個窄介面、0.5/45/15/2/2/1/10 timeout與8/48/768 recycle values |
| `M4B-LOCK-001` | portable + Pi preflight | strict lock keys、R3/runtime/native/model/config/schema/source/license identity、POC path僅provenance；mismatch zero side effect |
| `M4B-IPC-001` | portable | `snowboard.llm/1` exact keys/state/request/terminal/metrics/privacy |
| `M4B-RDY-001` | portable double + Pi | ENGINE_LOADED不admit、fixed input/prompt digest、mandatory same-renderer pre-warm、discard、READY/rebuild READY |
| `M4B-GEN-001` | portable double + Pi | structured input、single result、persistent Engine、fresh Conversation、token/metric bounds |
| `M4B-OUT-001` | portable + Pi | speak/tool/rest exact schema、current marker、forbidden/prior marker、allowlist |
| `M4B-P5-001` | portable + Pi | invalid/refusal/recoverable error/clean timeout fallback；fatal/recovery failure不被掩蓋 |
| `M4B-CAN-001` | portable + Pi | typed cancel、TERM/KILL/waitpid、single cancel、worker join、next success、Level 3 |
| `M4B-REC-001` | portable + Pi | unique-owner PSS/raw-byte 8/48/768 triggers、missing sample、terminal-only schedule/wait、ticket identity、no old-child admit、same-lock/pre-warm replacement、no-next-request failure仍由RM fatal monitor exit 4 |
| `M4B-HIST-001` | portable + Pi | five-turn isolation；normal child PID stable，planned generation switch only at expected boundary |
| `M4B-PRIV-001` | portable + Pi | input/output/tool/credential/path不進product log/evidence；public digest/metrics allowed |
| `M4B-OFF-001` | Pi | network-disabled real inference、no downloader/fallback/system-site import |
| `M4B-RES-001` | Pi | same-SHA M4a+M4b 4 GB 20-session；三generation、r14 4/64 gates、swap/OOM/thermal/cleanup |
| `M4B-PKG-001` | portable review + Pi install | clean offline atomic install、no-follow exact runtime inventory、Apache-2.0 license/notices |
| `M4B-INH-001` | evidence review | P1～P12 machine result/waiver分欄、Gate2B narrow harness→Core general renderer delta、locator/checksum、single product SHA |

`M4B-RES-001`不讀或要求Memory PSI；仍逐sample驗`system_used <= 3584 MiB`、`swap=0`、
zero OOM/throttle、temperature <80°C、owner PSS/RSS/CPU/thread、20 accepted sessions與zero residue。
沿用Gate 2B r14 frozen verifier公式，完整20-session combined PSS與system-used各自仍須
leak slope`<=4 MiB/session`且late-minus-early median delta`<=64 MiB`；每個child generation的
post-prewarm owner-PSS baseline-to-clean-terminal delta亦不得超過64 MiB。48 MiB是early recycle trigger，
不是放寬64 MiB gate；單次jump越界即FAIL，即使之後recycle成功也不洗掉。Planned recycle不得刪除
pre-trigger sample、分generation重算整體斜率或重設result；evidence須保存child generation、trigger
reason、pre/post baseline、ticket與每次pre-warm timing。8-attempt上限在20個accepted sessions必然於
第8與第16個attempt cleanup後各排程一次，故至少須觀察兩個完成replacement及三個child generation。

Pi entry不得由portable double宣告Pass。所有formal命令使用外部指定candidate SHA、bounded timeout、
fresh run ID/output；debug result不得合併成formal PASS。M4b只有Tester對同一Core product SHA完成
portable matrix與target acceptance，且Designer final review無Blocking，才可標子gate Accepted。

## 11. Planned work packages and authorization

所有WP共同entry是`IR_review_M4B_I=Resolved`與`TR_spec_M4B_I=Resolved`；在此之前只允許
Designer文件工作，不開始Developer implementation。

| WP | Scope | Exit |
| :--- | :--- | :--- |
| M4B-WP-01 | `llm.py` structured types、`llm_child_protocol.py` codec/state、deterministic child double | M4B-IPC/RDY portable assertions全綠；無real runtime import |
| M4B-WP-02 | Ch 10 strict config、tracked R3 lock parser、factory、offline install/preflight/notices | CFG/LOCK/PKG portable negative matrix全綠，invalid input side effect=0 |
| M4B-WP-03 | parent adapter、startup/pre-warm、admission、cancel/terminal、resource sampler與RecoveryTicket wait | RDY/CAN/REC deterministic lifecycle全綠；M4A regressions不變 |
| M4B-WP-04 | isolated LiteRT-LM worker、winner renderer/tokenizer/constrained output、fresh Conversation | Pi preflight identity通過；GEN/OUT/HIST focused target smoke全綠 |
| M4B-WP-05 | Reasoner structured seam、config-driven timeout、factory/composition、RM hook/barrier與main `rm.wait_fatal()` supervision | P5/fatal分界、planned failure即時exit 4、same-owner recovery、next-success與privacy regressions全綠 |
| M4B-WP-06 | candidate runner suite、20-session M4a+M4b composition、inheritance generator/template | Developer fast loop全綠；正式evidence仍只由Tester對candidate SHA產生 |

Developer先在`docs/reviews/dev_progress_M4.md`為每個WP列files/symbols、dependency、估點、affected tests
與exit evidence。WP可依dependency前進，但不得把mock/portable或POC waiver標成Core target PASS。

## 12. Review and completion gates

1. **External input complete**：Gate 2A history、DELIVERY-019 adaptation、022 pre-warm、023 PSI removal、
   Attempt 006 machine FAIL/waiver與R3 final winner ACK皆保持append-only。
2. **Designer delivery complete**：本章、Ch 2b/5/9/10、M4 gate與progress tracker使用同一structured seam、
   exact winner identity、recycle policy與WP/Test ID mapping。
3. **Single full design review — complete**：Reviewer已以一張`IR_review_M4B_I`審完整selected scope；
   2026-08-30以Blocking 0標記`Resolved`，歸檔於`docs/reviews/history/IR_review_M4B_I.md`。
4. **Single full test coverage review**：Tester一次補§10全部M4B Test IDs；Designer以
   `TR_spec_M4B_I`確認100% coverage、portable/target/candidate/evidence contract後才Development Ready。
5. **Development / candidate gate**：WP-01～06 fast loop → USER-approved provisional commit → 三minor
   portable matrix → Designer candidate review/freeze → Pi preflight/acceptance → Tester reconciliation。
6. **Designer final confirmation**：只核對frozen candidate後無protected-input drift、Tester evidence同SHA、
   design Blocking皆關閉；通過才標M4b Accepted。

M4b Accepted只關閉M4b子gate。M4c仍須在M4a與M4b均通過後接線，整體M4另要求三個子gate在
同一產品delivery exact SHA收斂。M4a Accepted狀態本身不回退，但final M4 candidate必須對未變更
M4a scope建立inheritance，並在該SHA重跑受M4b composition影響的Audio/resource/offline/privacy/
session regressions；不得拼接M4a歷史candidate與另一個M4b-only SHA宣告M4完成。

## 13. Combined Reviewer delivery

Reviewer單輪完整審查輸入固定為：

- 本章§0～§14完整內容；
- `docs/protocol.md` §1、§4與§6；
- `docs/milestones/M4.md` §6.2.2；
- `docs/implement/m4b_gate2a_intake.md`；
- `docs/model_spec.md` §6、R3 manifest與Core final winner ACK；
- Ch 2/2b Reasoner/LLMEngineAdapter、Ch 5 stable key、Ch 6 cancellation、Ch 9 validator、Ch 10
  current config，以及現有`main.py`、`resource_manager/manager.py`、`framed_child.py`、`llm.py`、
  `reasoner.py` source seam。

Reviewer至少一次核對：

1. protocol/fake與real adapter/worker/lock的ownership清楚，production identity只來自Gate 2B final ACK；
2. structured protocol exact keys、canonical projection、POC-path exclusion、token/metric bounds、state與
   typed terminal可實作；
3. codec可重用common helpers但不要求改寫Accepted M4A transport；
4. prompt/output privacy在success與每個failure cleanup路徑都封閉；
5. P5 normalizer仍由Reasoner擁有，fake child不宣告product schema/quality PASS；
6. hard-coded reason timeout改成config-driven且15秒generation／2秒grace／0.5秒cancel分層不漂移；
7. unique-owner sampler、raw-byte 8/48/768 trigger、terminal-only schedule/wait、RecoveryTicket、
   main-owned RM fatal monitor與new READY形成single-owner閉環；
8. Gate 2B narrow listen/speak marker harness與Core generic speak/tool/rest renderer明確列為product delta；
   Gate 2A／P9／P10B machine FAIL、User waiver與Core product result分欄，沒有evidence mutation；
9. Gemma 4 E2B typo clarification有記錄；任何非LiteRT-LM runtime仍另開`AR_impl`；
10. Tester handoff能直接形成§10的15個Test ID，r14 4/64 gates不被recycle重設，且M4A accepted
    behavior／same-SHA boundary無矛盾。

Reviewer已依本節清單完成`IR_review_M4B_I`並以Blocking 0核准M4b完整design。此結論仍不等於
Tester coverage sign-off、Developer實作完成、Core Tester PASS或M4b Accepted；下一個owner是Tester。

## 14. Designer completion audit and delivery manifest

### 14.1 Requirement closure

| Requirement | Authoritative closure | Reviewer evidence |
| :--- | :--- | :--- |
| Architecture fit | §0、Ch 2b/5/6；persistent child、Reasoner、Level 2與RM barrier不變 | `No architecture change / no AR_impl` |
| Public API/data | §3、Ch 2/2b；structured immutable input/result、sampler與recovery narrow ports | exact signatures、no raw prompt/ID/payload |
| Wire/renderer | `protocol.md` §4、§3.1/§3.2 | exact schemas/digests、canonical projection、dynamic constrained branches、fixed pre-warm |
| Identity/config | `model_spec.md` §6、Ch 10、§7/§8 | exact R3 values、POC paths provenance-only、strict lock/runtime manifest |
| Lifecycle/failure | §4/§5、Ch 5/6 | deadlines、typed terminal、cleanup proof、P5/fatal table、same-owner rebuild |
| Defect mitigation | §0.3、§10.2、M4 §6.4 | unique-owner sampling、8/48/768 trigger、r14 4/64 gates、two replacements |
| Privacy/offline/package | §6/§8 | no private log/evidence、no download/fallback/system-site、atomic/no-follow install |
| POC inheritance | §1.3/§9、R3/final ACK | machine FAIL與waiver分欄、narrow harness→general renderer delta、single Core SHA |
| Development slicing | §11 | WP-01～06各有scope、dependency與exit evidence |
| Test handoff | §10 | 15 Test IDs覆蓋portable/Pi/evidence；Tester-owned spec未被Designer預寫 |

### 14.2 Review package and ownership boundary

Reviewer已依§13清單完成Reviewer-owned `IR_review_M4B_I`，Blocking 0且無需Designer修訂主設計；
審查單依workflow歸檔。其Advisory所指的`prepare_shutdown()`已由Ch 5 §6.5完整定義，本章§0.1亦補上
surface交叉引用，不改變已核准契約。

下一個owner是Tester：新增`docs/test_spec/test_spec_M4.md`的M4B coverage並提交`TR_spec_M4B_I`。
Designer不代寫Tester-owned spec，亦不修改Developer-owned`dev_progress_M4.md`或建立runtime lock／
production source；在`TR_spec_M4B_I=Resolved`前不得標Development Ready或開始WP-01～06。

### 14.3 Self-check evidence

2026-08-30的mechanical consistency、authority-object digest、15 Test ID／6 WP計數、stale-seam scan與
PM handoff audit記錄於`docs/reviews/impl_progress.md`的「Post-Gate-2B Reviewer delivery self-check」。
這些證明delivery完整且輸入可定位；它們不是source implementation或Gate 3 execution evidence。
