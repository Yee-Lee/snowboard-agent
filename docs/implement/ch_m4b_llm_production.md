# M4b Local LLM production integration planning

狀態：**Gate 2A integrated — Gemma sole model finalist；architecture / integration revision / Gate 2B pending**。

Architecture change：**No**。Persistent child、LiteRT-LM runtime、Reasoner、Resource Manager與三級
收斂邊界不變。USER已於2026-08-29澄清`arch.md`的`Gemma3:e2b`是文字typo；E2B指Gemma 4 E2B，
因此Gate 2A選型不構成model-generation architecture change。Designer不在本輪修改Architect-owned
`arch.md`，但後續引用一律使用Gemma 4 E2B正名。

本章把 `docs/milestones/M4.md` 的 M4b 範圍轉成 Core product 可實作的
persistent-child、runtime identity、failure convergence、POC inheritance 與 Gate 3
驗收設計。架構仍以 `docs/arch.md` 為權威；LLM wire schema 草案見
`docs/protocol.md` §6；最終 engine / model / quantization / artifact identity 必須等
Gate 2B final winner ACK 後才寫入 `docs/model_spec.md`。

Gate 2A已在execution SHA `e2b59fac609e0d768ff3554754363900cbed70a9`、surface SHA-256
`eccbcdc1a099c40a80cc86de8f711711b9ed351400197a505d4f4f466b37b2e1`完成。User選定
`CAND-LRT-G4E2B-MOBILE-R1`（Gemma 4 E2B mobile）為sole model finalist並排除Qwen；Core decision見
`DELIVERY-LLM-POC-M4B-GATE2A-PROVISIONAL-ACK-001`。Gemma R1 P2/P8仍FAIL，故這是model-selection
input，不是Core production baseline。

## 1. Planning boundary

### 1.1 現在可定義

- Core controller 與其直接擁有的 LLM child 之 process / IPC ownership；
- READY、GENERATE、CHUNK、RESULT、CANCEL、SHUTDOWN 與 protocol-failure 語意；
- 一次只允許一個 active generation、每 turn 無 hidden history、engine 跨 turn 常駐；
- Reasoner P5 fallback、privacy、timeout、Level 2 termination proof 與 RM recovery barrier；
- selected runtime 必須具備的 product lock、offline install、preflight、inheritance 與
  exact-SHA evidence 欄位；
- Gate 3 工作包與 test-spec coverage skeleton。

### 1.2 尚不可固定

- final winner、production pairing、quantization/profile checksum、artifact lock與完整notice結論；
- Gemma integration-qualified revision的PromptBuilder / chat template / product prompt / config identity；
- Gate 2B P9 / P10B combined結果與final winner；
- product dependency、model lock與shipping READY exact identity；
- Core Tester PASS、M4b Accepted、M4c entry或整體M4 acceptance。

Gate 2A已確認LiteRT-LM / Gemma 4 E2B方向，但Gate 2B final ACK前仍不得把reference identity寫成
production baseline。任何runtime偏離LiteRT-LM仍須另開`AR_impl`；不得只靠config或adapter名稱私下
改變runtime架構。

### 1.3 Gate 2A product implication

- Gemma R1：P2 `FAIL (3/30)`、P3/P4/P5 `PASS`、P8
  `FAIL / DEPENDENCY_LIMITED_BY_P2`；沒有observed history pollution。
- Qwen：P2 `FAIL (0/30)`、P3/P5 `PASS`、P4需Core threshold decision、P8
  `FAIL / DEPENDENCY_LIMITED_BY_P2`，且carry P7.1 `FAIL / SLOW_RECOVERY`；不進formal Gate 2B。
- New Gemma revision只可調整versioned integration surface，使用bounded adaptation budget與分離的
  development/scored cases；不得覆寫或重標R1 receipt。
- 受影響P2/P8須在new frozen revision PASS後才能進Gate 2B。Input未變的P1/P3/P4/P5/P6.1/P7.1/
  P10A/P11/P12可依lock carry；identity drift只重驗affected rows。

### 1.4 DELIVERY-019 bounded integration adaptation plan

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

既有公開Protocol保持不變：

```python
class LLMEngineAdapter(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...
    async def generate(self, prompt: str) -> LLMGeneration: ...
```

LiteRT-LM是既有architecture runtime，Gate 2A ACK後可使用`litert_lm`作real adapter scaffold module；
production identity與shipping branch仍只在Gate 2B final winner ACK後固定：

```text
src/sbd/cognition/
├── llm.py                         # existing Protocol + mock
├── reasoner.py                    # existing normalizer / P5 owner
├── prompt_builder.py              # existing stateless prompt owner
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
但LLM state machine、chunk aggregation、output hash與request code只能留在LLM module。

### 3.1 Phase A exact implementation seam

Gate 2A前只允許protocol / fake scaffold，因此首個Developer package不得建立parent-side real
adapter、selected runtime worker、real factory branch、recoverable RM record或artifact lock。Phase A
核准後的精確落點為：

```text
src/sbd/cognition/
└── llm_child_protocol.py          # pure codec / schema / state validation only
tests/fakes/
└── m4b_llm_child.py               # deterministic subprocess；無runtime/model/network import
tests/
└── test_m4b_ipc_001.py            # Phase A portable protocol/fake coverage
```

`llm_child_protocol.py`固定下列public seam：

```python
class LLMProtocolError(AdapterError): ...

@dataclass(frozen=True, slots=True)
class LLMReady:
    pid: int
    pgid: int
    runtime_lock_sha256: str
    runtime_artifact_sha256: str
    model_sha256: str
    profile_sha256: str

@dataclass(frozen=True, slots=True)
class LLMChunk:
    request_id: int
    sequence: int
    text: str

@dataclass(frozen=True, slots=True)
class LLMResult:
    request_id: int
    finish_reason: Literal["stop", "max_tokens", "refused"]
    chunk_count: int
    output_utf8_bytes: int
    output_sha256: str

@dataclass(frozen=True, slots=True)
class LLMRequestError:
    request_id: int
    code: Literal["INVALID_PROMPT", "GENERATION_REJECTED", "OUTPUT_LIMIT"]

@dataclass(frozen=True, slots=True)
class LLMCancelled:
    request_id: int

@dataclass(frozen=True, slots=True)
class LLMCancelDeferred:
    request_id: int

@dataclass(frozen=True, slots=True)
class LLMBusy:
    request_id: int
    active_request_id: int

def build_generate(request_id: int, prompt: str) -> tuple[dict[str, object], bytes]: ...
def parse_ready(
    value: Mapping[str, object],
    *,
    expected_pid: int,
    expected_identity: Mapping[str, str],
) -> LLMReady: ...
def parse_event(value: Mapping[str, object], *, active_request_id: int) -> LLMEvent: ...
def validate_result(result: LLMResult, chunks: Sequence[LLMChunk]) -> LLMGeneration: ...
```

`LLMEvent`是`LLMChunk | LLMResult | LLMRequestError | LLMCancelled |
LLMCancelDeferred | LLMBusy`的closed union。所有parser要求exact keys、`type(value) is int`
（拒絕bool）、lowercase SHA-256、positive request ID與`docs/protocol.md` §6 bounds。錯誤訊息只含
stage / field / reason，不含prompt、chunk、output、payload或私人path。

Phase A可呼叫現有`encode_control`、`read_control`、`require_schema`、`require_sha256`，但不得為了
消除既有`AudioProtocolError`名稱而重構`FramedProcess`或改動M4a adapter。LLM codec在boundary把
共用transport的`AdapterError`正規化為sanitized `LLMProtocolError`；M4a behavior與其既有tests
保持逐項不變。Audio專用`read_exact_payload()`含even-length / 64 MiB PCM規則，LLM prompt不得
重用；Phase A fake child依§6獨立做positive 256 KiB UTF-8 payload length/hash read。
`FramedProcess`的workdir prefix、READY owner與real lifecycle extension留到Gate 2A provisional
ACK後的M4B-WP-02。

`tests/fakes/m4b_llm_child.py`以caller明確傳入的scenario執行`ready_result`、`refused`、
`cancelled`、`cancel_deferred`、`busy`、`bad_identity`、`bad_chunk`、`late_terminal`、`hang`與
`shutdown`。它只使用stdlib、固定fake hashes與synthetic text；不得import LiteRT-LM / llama.cpp、
讀真實model/config、連網或被production config選取。

## 4. Parent adapter lifecycle

Parent維護`STOPPED → STARTING → READY ↔ BUSY → DESTROYED`：

1. `start()`先驗tracked lock、isolated runtime、artifact/config identity與private work root，再spawn
   child；只有收到`docs/protocol.md` §6 exact READY且全部identity吻合才return。
2. 同一已驗證child上的重複`start()`為idempotent；`stop()`在`STOPPED`為no-op。
3. READY identity missing/mismatch、invalid first frame、EOF或startup timeout時，parent先完成
   TERM → bounded wait → 必要時KILL → waitpid、關streams、刪workdir，才raise
   `AdapterUnavailable`；不得留下半啟動child。
4. `generate()`只在READY合法。Parent配置單調遞增且不重用的request ID，傳一個bounded prompt，
   收集有序CHUNK並驗terminal RESULT的count、UTF-8 byte count及SHA-256後，才建立
   `LLMGeneration`。任何partial output在terminal前都不可交給Reasoner。
5. RESULT / request ERROR / CANCELLED完成後同一child回READY；protocol、identity、EOF、
   late-terminal或cleanup failure使owner進DESTROYED，不得轉成空模型輸出。
6. `stop()`只在READY送SHUTDOWN；BUSY時先依worker收斂路徑處置。收到ACK後仍須waitpid。

## 5. Cancel, timeout and recovery

### 5.1 Cooperative path

- Reasoner的使用者等待上限取自`AppConfig.cognition.reason_timeout_seconds`；不得沿用目前
  module-level hard-coded 30秒常數。
- timeout後Reasoner依Ch 2b §1.2呼叫`llm.abort()`。Adapter送CANCEL並只在matching CANCELLED
  證明operation停止、request-local state清除且child回READY後return；此時Reasoner可發布P5
  fallback。Reasoner不得無界等待abort：使用
  `cancel.abort_timeout_seconds.by_kind["cognition.reasoner"]`作cleanup上限。
- 若runtime不提供可靠native cancel，child送nonterminal CANCEL_DEFERRED，adapter的`abort()`
  保持pending。cleanup上限到期時Reasoner發布一個sanitized `ErrorOccurred`、不發布fallback並保持
  outer call in-flight，等待SM依Ch 6呼叫`force_abort()`；不得自行kill後假裝一般timeout。

### 5.2 Force-abort and rebuild

- `force_abort()`對完整PGID送SIGTERM、bounded wait；仍存活才SIGKILL並再次waitpid，然後關IPC、
  清workdir、確認orphan/descendant為零。
- 成功後state=`DESTROYED`，回
  `ForceAbortReport(("backend.cognition.reasoner.llm",))`。任一exit/cleanup proof失敗則raise，
  由Ch 6進Level 3 exit 4。
- RM recovery hook只在DESTROYED建立全新child並重驗同一product lock READY。Recovery barrier在
  replacement READY前保持closed；不得回傳replacement adapter instance、更新capability map或
  讓Reasoner自行restart。
- Rebuild failure / timeout維持既有Level 3規則；不得fallback到mock、另一model或network service。

## 6. Result normalization and history isolation

Parent只回`LLMGeneration(text, finish_reason)`；Core product validator仍由Reasoner與
`ActionPayloadValidator`擁有：

1. child output必須是單一UTF-8 JSON object；不得由child執行tool、修補payload或發布Fact。
2. Reasoner只接受exact keys `action_kind`、`action_payload`、`next_perceptions`，再依Ch 9驗
   `speak/tool/rest`及capability；unknown/empty/refused/bad JSON走既有P5 apology-speak或rest。
3. `finish_reason="refused"`或空白output直接走P5。`max_tokens`只有在完整output仍通過product
   validator時才可使用；截斷/壞JSON仍走P5。
4. 每次GENERATE建立fresh conversation。Gate 3至少以五個有意污染前一turn的固定case證明
   後一turnoutput只取決於本次prompt；同時assert child PID與engine load count不變。
5. PromptBuilder只接收已定義的perception結果、payload-free pending IDs、capability與sealed tool
   schemas。產品test不得把hidden context、credential或raw tool arguments加入prompt/evidence。

## 7. Config and strict identity

現有`LLMConfig`只是placeholder。Gate 2B winner後的最小形狀預定為：

```python
@dataclass(frozen=True, slots=True)
class LLMConfig:
    driver: Literal["mock", "<selected_driver>"] = "mock"
    engine_name: str | None = None
    runtime_python: Path | None = None
    model_path: Path | None = None
    artifact_lock_path: Path | None = None
    profile_id: str | None = None
    max_output_tokens: int = 512
    temperature: float = 0.2
    top_p: float = 0.9
    child_ready_timeout_seconds: float = 120.0
    child_terminate_timeout_seconds: float = 3.0
    child_kill_wait_timeout_seconds: float = 2.0
```

- `<selected_driver>`、engine/profile與sampling exact值只從final ACK及`model_spec.md`產生。
- Real driver的四個identity path必須absolute；config loader只做shape / finite-bound validation，
  product preflight在spawn前驗hash、runtime inventory、platform、architecture與Accepted identity。
- YAML不得覆寫checksum、license或artifact source。`mock`不得讀lock、要求real path或importreal module。
- `make_llm_adapter(cfg)`保持單一公開factory；real branch先用pure-Python parser驗lock，再lazy import
  selected adapter。Invalid config/lock在child、hardware與temporary artifact前fail closed。
- `ResourceSpec.instance`與`recovery_hook`必須指向同一owner；real backend才`recoverable=True`。

## 8. Product lock, packaging and offline closure

Gate 2B final ACK後，`requirements/m4b/`逐項保存：POC delivery/full SHA、candidate/pairing ID、
engine/runtime/model/quantization/profile、source/artifact SHA-256、filename/size、target OS/arch/Python、
license與notice locator、Gate 2 evidence locator/checksum。Model、wheel、native binary、raw prompt/output與
POC evidence payload保持Git-external。

`m4b_llm_product.py`只提供：

- `install`：接受caller-supplied、checksum-matching offline inputs；在new same-filesystem staging建立
  isolated runtime，使用no-index/no-deps或selected runtime等價的locked安裝方式；驗完才atomic
  rename，拒絕existing output；
- `preflight`：read-only驗install inventory、model/runtime/config/notice identity、Pi 5 / Debian 13 /
  CPython 3.13、Core candidate SHA與protected paths clean；在child啟動前fail closed。

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

### 10.1 Portable protocol coverage

Reviewer核准完整M4b design後，Tester在`docs/test_spec/test_spec_M4.md`新增
`M4B-IPC-001`的portable部分，至少綁定：

1. GENERATE header + exact prompt payload的fragment/coalesce、length/hash/UTF-8/NUL與256 KiB邊界；
2. READY exact identity、request ID monotonicity、CHUNK sequence、RESULT aggregate count/bytes/hash；
3. empty output、refused、max-token valid/invalid JSON只是codec輸出，不由fake child冒充Reasoner PASS；
4. CANCELLED、CANCEL_DEFERRED後不得再出CHUNK/RESULT、BUSY discard後frame alignment不漂移；
5. EOF、extra/missing key、wrong ID/hash、late terminal及hang皆fail closed並bounded cleanup；
6. stdout/stderr/caplog/result不得含prompt、chunk、output、credential或private path；
7. `tests/test_m4a_ipc_001.py`與所有M4A protocol/lifecycle regressions保持通過，證明Phase A沒有
   改寫Accepted Audio contract。

Tester尚未產出完整M4b章節前，Designer不建立`TR_spec_M4B_I`的Resolved結論；Developer也不得自行以
本章coverage skeleton取代Tester-owned test spec。依USER的single-review方向，本portable scope與
Gate 2B後selected baseline scope合併在同一輪`IR_review_M4B_I` / `TR_spec_M4B_I`，不另開early round。

### 10.2 Full Gate 3 coverage after final winner

下列是Designer交Tester的coverage skeleton，不是Tester PASS，也不直接修改Tester-owned test spec：

| Test ID | Platform | Required risk |
| :--- | :--- | :--- |
| `M4B-CFG-001` | portable | strict selected-driver config、mock isolation、lazy factory、config-driven timeout |
| `M4B-LOCK-001` | portable + Pi preflight | Accepted identity、runtime/model/profile/checksum fail closed |
| `M4B-IPC-001` | portable | LLM Protocol v1 keys/bounds/state/chunk/hash/request/EOF/late terminal/privacy |
| `M4B-GEN-001` | portable double + Pi | READY後generate、single result、persistent engine、fixed product schema |
| `M4B-OUT-001` | portable + Pi | fixed catalog的speak/tool/rest、capability/tool allowlist與normal schema 100%通過 |
| `M4B-P5-001` | portable + Pi | empty/refusal/bad JSON/unknown action/tool fallback與no-log |
| `M4B-CAN-001` | portable + Pi | cancel/deferred cancel/TERM/KILL/waitpid/rebuild/Level 3 outcome |
| `M4B-HIST-001` | portable + Pi | five-turn history isolation且engine不重載 |
| `M4B-PRIV-001` | portable + Pi | prompt/output/payload/credential/private path不進log/evidence |
| `M4B-OFF-001` | Pi | real inference zero network attempt、無downloader/fallback |
| `M4B-RES-001` | Pi | real M4a+M4b 4GB resource/thermal/cleanup與fixed 20-session composition；同SHA |
| `M4B-PKG-001` | portable review + Pi install | clean offline install、exact inventory、license/notices |
| `M4B-INH-001` | evidence review | P1～P12 inheritance/delta identity與single product SHA |

Pi entry不得由portable double宣告Pass。所有formal命令使用外部指定candidate SHA、bounded timeout、
fresh run ID/output；debug result不得合併成formal PASS。M4b只有Tester對Core product exact SHA完成
portable matrix與target acceptance，且Designer final review無Blocking，才可標子gateAccepted。

## 11. Planned work packages and authorization

| WP | Earliest entry | Scope / exit |
| :--- | :--- | :--- |
| M4B-WP-01 | Design + protocol Reviewer approved、test-spec coverage signed | common LLM protocol parser/state machine與deterministic child double；不含selected runtime |
| M4B-WP-02 | Gate 2A provisional finalist ACK + design/test gates | parent owner、chunk aggregation、cancel/termination/recovery scaffold；不鎖dependency/model |
| M4B-WP-03 | Gate 2A provisional finalist ACK + design/test gates | Reasoner timeout/config seam、normalizer/catalog/privacy/history regressions；不宣告baseline |
| M4B-WP-04 | Gate 2B final winner ACK + architecture alignment | selected runtime/model lock、offline install/preflight/notices |
| M4B-WP-05 | WP-04 identity stable | selected child/adapter、factory、composition與RM recovery wiring |
| M4B-WP-06 | WP-05 affected tests green | Gate 3 target entry、combined M4a+M4b resource/session、inheritance generator |

### 11.1 M4B-WP-01 Phase A task split

| Task | Files / output | Done when |
| :--- | :--- | :--- |
| WP-01.1 codec / closed event union | `src/sbd/cognition/llm_child_protocol.py` | §3.1 signatures與§6 exact schema/bounds均可由pure unit test驗證；無selected runtime import |
| WP-01.2 deterministic fake child | `tests/fakes/m4b_llm_child.py` | 所有scenario bounded、offline、synthetic且不可被production config選取 |
| WP-01.3 named portable regression | `tests/test_m4b_ipc_001.py` | Tester核准的Phase A `M4B-IPC-001`逐項有real assertion；無skip/xfail |
| WP-01.4 regression closure | Developer progress記錄 | M4B focused、M4A IPC/lifecycle與repository `not rpi`在主要minor全綠；不建立Pi/PASS evidence |

Developer須先在`docs/reviews/dev_progress_M4.md`估點與拆包。現在只建立Designer規劃輸入；
在Reviewer核准設計、Tester coverage sign-off及各WP external entry滿足前，不開始production implementation。

## 12. Review and completion gates

1. **Phase A Designer complete**：本章、`protocol.md` §6、M4 milestone切點、exact symbol seam、
   Reviewer / Tester handoff與`m4b_gate2a_intake.md`一致。
2. **POC Gate 2A intake complete**：Core ACK保留immutable machine results，接受Gemma sole model
   finalist並排除Qwen；不宣告R1 pairing PASS。
3. **Integration revision**：依§1.4的bounded adaptation plan建立new frozen Gemma revision，並以
   held-out/precommitted cases使affected P2/P8 PASS。
4. **POC Gate 2B / final winner**：replacement packet / lock經review與Pi authorization後，使用Accepted
   Audio package完成P9/P10B；Core書面final ACK。
5. **Single full design review**：依USER減少多輪的決策，Gate 2B final ACK後，
   Reviewer以一張`IR_review_M4B_I`同時審engine-agnostic protocol、selected driver/config/lock/
   packaging、model spec與WP-01～06；不另開generic-only round。
6. **Single full test coverage review**：Tester一次補完整M4B Test ID；Designer以`TR_spec_M4B_I`確認
   100%覆蓋後才交Developer實作。
7. **Development / candidate gate**：Developer fast loop → USER-approved provisional commit → 三minor
   portable matrix → Designer candidate review/freeze → Pi preflight/acceptance → final reconciliation。

M4b Accepted只關閉M4b子gate。M4c仍須在M4a與M4b均通過後接線，整體M4另要求三個子gate在
同一產品delivery exact SHA收斂。M4a Accepted狀態本身不回退，但後續final M4 candidate必須對
未變更M4a scope建立可驗證inheritance，並在該final SHA重跑受M4b composition影響的Audio、
resource、offline、privacy與session regression；不得拼接M4a歷史candidate與另一個M4b-only SHA
宣告M4完成。

## 13. Combined Reviewer handoff（queued after Gate 2B）

Reviewer單輪完整審查輸入固定為：

- 本章§1～§6、§10.1、§11.1、§12及本節；
- `docs/protocol.md` §1與§6；
- `docs/milestones/M4.md` §6.2.2；
- `docs/implement/m4b_gate2a_intake.md`；
- `docs/model_spec.md` M4b final baseline、replacement Gate 2B lock與Core final winner ACK；
- Ch 2b LLMEngineAdapter / Reasoner、Ch 5 stable key、Ch 6 cancellation、Ch 9 validator、Ch 10
  placeholder config，以及現有`framed_child.py` / `llm.py` / `reasoner.py` source seam。

Reviewer至少一次核對：

1. protocol/fake與real adapter/worker/lock的ownership清楚，production identity只來自Gate 2B final ACK；
2. protocol exact keys、bounds、state、terminal、cancel-deferred與BUSY alignment可實作；
3. codec可重用common helpers但不要求改寫Accepted M4A transport；
4. prompt/output privacy在success與每個failure cleanup路徑都封閉；
5. P5 normalizer仍由Reasoner擁有，fake child不宣告product schema/quality PASS；
6. current hard-coded reason timeout由selected implementation改成config-driven且failure convergence不漂移；
7. Gate 2A intake保留Gemma P2/P8 FAIL、Qwen exclusion與R1 receipt，new revision沒有anti-overfitting違約；
8. Gemma 4 E2B typo clarification有記錄；任何非LiteRT-LM runtime仍另開`AR_impl`；
9. Tester handoff能直接形成完整可執行M4B Test ID；
10. M4A accepted behavior與final M4 same-SHA inheritance邊界沒有矛盾。

`IR_review_M4B_I`只在Gate 2B final winner與architecture disposition完整後發起；其通過代表M4b完整
design approved，但仍不等於Developer實作完成、Core Tester PASS或M4b Accepted。
