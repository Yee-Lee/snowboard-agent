# Ch 10. Config schema

屬於 implement.md 索引 | 對應 arch.md §7.1 | 狀態：定稿（IR-final 已通過（2026-08-01））

上游：Ch 2a、Ch 2b、Ch 4、Ch 5、Ch 6、Ch 7、Ch 9。

0. 已確認判斷

| 編號 | 判斷點 | 已確認結論 |
| --- | --- | --- |
| ch10-Q1 | Dataclass是否允許runtime mutation | 全部 `frozen=True, slots=True` ；mapping轉 `MappingProxyType` |
| ch10-Q2 | YAML merge是否接受未知key | 不接受；recursive strict merge，拼字錯誤在startup失敗 |
| ch10-Q3 | 實際載入哪個YAML | defaults → optional `config.local.yaml` ； `config.example.yaml` 只供複製、不自動載入 |
| ch10-Q4 | `.env` 是否需要新dependency | 不需要；實作最小KEY=VALUE parser，僅支援明列env keys |
| ch10-Q5 | Env能否覆寫所有YAML | 否；只需寫secret與明列operational key（初版僅log level） |
| ch10-Q6 | 開發機default backend | HAL / model使用 `mock` ，讓純軟體啟動可重複；Pi由local YAML選real |
| ch10-Q7 | required預設 | listen/speak/rest/reasoner為required；look/read/tool與所有InputSource / Adaptor預設optional |
| ch10-Q8 | Cancel timeout形式 | default + per-kind overrides；欄位名固定 `abort_timeout_seconds` / `force_abort_timeout_seconds` |
| ch10-Q9 | Resource timeout形式 | startup/stop default + per-resource overrides；recovery另有overall與shutdown-cleanup上限 |
| ch10-Q10 | Secret在Config中的型別 | `SecretValue` ， `repr` / `str`不輸出原值，只能明確 `reveal()` 給adaptor factory |
| ch10-Q11 | Reload | 不支援；config startup載入一次，變更需process restart |

1. 範圍與非目標

1.1 本章包含

- Config dataclass tree、defaults、strict overlay與validation。
- `config.local.yaml` 、process env與 `.env` 載入順序。
- HAL、worker、timeout、buffer、logging與optional channel設定。
- `config.example.yaml` / `.env.example` 應涵蓋的欄位。
- Config錯誤taxonomy與測試條件。

1.2 本章不包含

- Secret storage service、remote config或runtime reload。
- Tool-specific domain設定；由tool factory own schema後掛在明確namespace。
- StatusBar slot、Display template、P5文案；這些是code-declared。
- 跨process wire schema。
- 部署時真正的Pi pin / ALSA card / model path值；example只放placeholder。

2. 套件

```text
src/sbd/core/config/
├── __init__.py         # load_config / AppConfig re-export
├── models.py           # frozen dataclasses
├── defaults.py         # DEFAULT_CONFIG
├── loader.py           # YAML + env overlay
├── env.py              # .env parser / SecretValue
└── validate.py         # field與cross-field validation

config.example.yaml
.env.example
```

唯一第三方依賴為現有 `PyYAML>=6.0` ，使用 `yaml.safe_load()` 。

3. Root schema

```python
@dataclass(frozen=True, slots=True)
class AppConfig:
    wake: WakeConfig
    perception: PerceptionConfig
    cognition: CognitionConfig
    action: ActionConfig
    cancel: CancelConfig
    resource: ResourceConfig
    shutdown: ShutdownConfig
    external_message: ExternalMessageConfig
    core: CoreConfig
    input_sources: InputSourcesConfig
    adaptors: AdaptorsConfig
    log: LogConfig
```

Dataclass constructor不直接接受raw dict；loader先strict merge與type decode，再建立 完整object。沒有「任意extras」bucket。

4. 共用設定型別

```python
@dataclass(frozen=True, slots=True)
class ComponentPolicy:
    enabled: bool
    required: bool

@dataclass(frozen=True, slots=True)
class TimeoutMap:
    default: float
    by_kind: Mapping[str, float] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class BackendConfig:
    driver: str
    options: Mapping[str, JsonValue] = field(default_factory=dict)

class SecretValue:
    __slots__ = ("_value",)
    def reveal(self) -> str: ...
    def __repr__(self) -> str: return "SecretValue(***)"
    def __str__(self) -> str: return "***"
```

`TimeoutMap` lookup未知kind時使用default；但 `by_kind` 中的key必須來自該欄位的 合法registry，config load時驗證。各欄位的合法registry namespace固定為：

| 欄位 | key namespace | 來源 |
| --- | --- | --- |
| `cancel.abort_timeout_seconds` / `cancel.force_abort_timeout_seconds` | operation kind（ `perception.listen` `cognition.reasoner` `action.tool` ...） | Ch 6 §9 / Ch 11 operation namespace |
| `resource.startup_timeout_seconds` / `resource.stop_timeout_seconds` | stable ResourceKey（ `backend.cognition.reasoner.llm` `core.audio.input` ...） | Ch 5 §3.1 registry |

兩個 namespace 不可混用：resource timeout 不接受 operation kind，cancel timeout 不接受 ResourceKey。未知 key 在 config load 時 `ConfigValueError` ，不等到 runtime 才發現。

`componentPolicy.enabled=False` 表示不建立。 `required=True` 且 `enabled=False` 是矛盾，loader拒絕。

5. 流程與 timeout

> **設計意圖**：將 timeout 統一集中於 `PerceptionConfig.timeout_seconds`（而非散置於各 kind 的 config 中），是為了方便 State Manager / Orchestrator 能統一讀取與傳遞，維持個別 kind config 結構精簡。

```python
@dataclass(frozen=True, slots=True)
class WakeConfig:
    ack_seconds: float = 0.3

@dataclass(frozen=True, slots=True)
class PerceptionTimeouts:
    listen: float = 10.0
    read: float = 0.5
    look: float = 3.0

@dataclass(frozen=True, slots=True)
class ASRConfig:
    driver: Literal["mock", "whisper"] = "mock"
    model_path: Path | None = None
    language: str | None = None

@dataclass(frozen=True, slots=True)
class VisionConfig:
    driver: Literal["mock", "local"] = "mock"
    model_path: Path | None = None

@dataclass(frozen=True, slots=True)
class ListenConfig:
    enabled: bool = True
    required: bool = True
    adapter: ASRConfig = ASRConfig()

@dataclass(frozen=True, slots=True)
class ReadConfig:
    enabled: bool = True
    required: bool = False

@dataclass(frozen=True, slots=True)
class LookConfig:
    enabled: bool = True
    required: bool = False
    adapter: VisionConfig = VisionConfig()

@dataclass(frozen=True, slots=True)
class PerceptionConfig:
    timeout_seconds: PerceptionTimeouts
    default_perceptions: tuple[str, ...] = ("listen",)
    listen: ListenConfig = ListenConfig()
    read: ReadConfig = ReadConfig()
    look: LookConfig = LookConfig()

@dataclass(frozen=True, slots=True)
class CancelConfig:
    abort_timeout_seconds: TimeoutMap
    force_abort_timeout_seconds: TimeoutMap

@dataclass(frozen=True, slots=True)
class ResourceConfig:
    startup_timeout_seconds: TimeoutMap
    stop_timeout_seconds: TimeoutMap
    recovery_timeout_seconds: float = 30.0
    recovery_shutdown_cleanup_timeout_seconds: float = 5.0

@dataclass(frozen=True, slots=True)
class ShutdownConfig:
    sm_drain_timeout_seconds: float = 5.0
    logger_flush_timeout_seconds: float = 2.0
```

Perception dataclass decoder與 `DEFAULT_CONFIG` 只接受同一棵樹，不提供 `listen_adapter` / `look_adapter` 相容alias：

```yaml
perception:
  timeout_seconds:
    listen: 10.0
    read: 0.5
    look: 3.0
  default_perceptions: [listen]
  listen:
    enabled: true
    required: true
    adapter:
      driver: mock
      model_path: null
      language: null
  read:
    enabled: true
    required: false
  look:
    enabled: true
    required: false
    adapter:
      driver: mock
      model_path: null
```

因此 PerceptionConfig.listen / read / look 分別decode為 `ListenConfig` `ReadConfig` `LookConfig` ； adapter factory只讀 `config.perception.listen.adapter` 或 `config.perception.look.adapter` 。

Cancel defaults :

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

Resource defaults :

```yaml
resource:
  startup_timeout_seconds:
    default: 15.0
    by_kind:
      backend.cognition.reasoner.llm: 120.0
  stop_timeout_seconds:
    default: 3.0
    by_kind:
      backend.cognition.reasoner.llm: 10.0
  recovery_timeout_seconds: 30.0
  recovery_shutdown_cleanup_timeout_seconds: 5.0
```

`resource.*_timeout_seconds.by_kind` 的 key 是 Ch 5 §3.1 的 stable dotted ResourceKey （例： `backend.cognition.reasoner.llm` `core.audio.input` ），不是簡寫 `backend.llm` 。 startup 與 stop lookup 都以同一 ResourceKey namespace 對 ResourceManager 的 production registry 查值； `TimeoutMap.by_kind` 的每個 key 必須存在於該 registry，否則 config load 時 `ConfigValueError` (見 §11 / §15 )。這確保 repository 預設設定與 `config.example.yaml` 都能通過 strict validation，且 LLM override 實際套用至該 `backend.cognition.reasoner.llm` 這筆 record。

`sm_drain_timeout_seconds` 是main等待SM shutdown flow的外層guard；Ch 6每個worker 仍使用自己的cancel timeout。Main timeout到期不呼叫task.cancel假裝乾淨，而是 Level 3 fatal exit。

6. Cognition 與 action

```python
@dataclass(frozen=True, slots=True)
class LLMConfig:
    driver: Literal["mock", "litert_lm"] = "mock"
    model_path: Path | None = None
    max_output_tokens: int = 512
    temperature: float = 0.2
    top_p: float = 0.9
    child_ready_timeout_seconds: float = 120.0
    child_terminate_timeout_seconds: float = 3.0
    child_kill_wait_timeout_seconds: float = 2.0

@dataclass(frozen=True, slots=True)
class CognitionConfig:
    reason_timeout_seconds: float = 30.0
    llm: LLMConfig = LLMConfig()

@dataclass(frozen=True, slots=True)
class TTSConfig:
    driver: Literal["mock", "piper"] = "mock"
    model_path: Path | None = None
    voice_id: str | None = None

@dataclass(frozen=True, slots=True)
class ActionConfig:
    speak: ComponentPolicy = ComponentPolicy(True, True)
    tool: ComponentPolicy = ComponentPolicy(True, False)
    rest: ComponentPolicy = ComponentPolicy(True, True)
    tts: TTSConfig = TTSConfig()
```

Reasoner固定required，不提供 `required` 欄位； `cognition.llm.driver=litert_lm` 時 `model_path` 必須且必須是file。Mock不要求path。

`action.tool.enabled=true` 但sealed ToolRegistry為空時，依Ch 9視為tool worker未載入； `required=false` 得到P2=false， `required=true` 則startup fatal。

ASR / Vision config已在§5成為 `ListenConfig.adapter` 與 `LookConfig.adapter` 的實際 欄位。不存在root-level perception adapter欄位；所有factory、validation、example 與文件都使用 `perception.listen.adapter` / `perception.look.adapter` 。

7. Core HAL

```python
@dataclass(frozen=True, slots=True)
class AudioConfig:
    driver: str = "mock"
    sample_rate: int = 16_000
    channels: int = 1
    bit_depth: Literal[16] = 16
    frame_duration_ms: int = 20
    input_device: str | None = None
    output_device: str | None = None

@dataclass(frozen=True, slots=True)
class DisplayConfig:
    driver: str = "mock"
    width: int = 128
    height: int = 64
    pixel_format: Literal["mono1", "rgb565", "rgb888"] = "mono1"
    spi_device: str | None = None

@dataclass(frozen=True, slots=True)
class CameraConfig:
    driver: str = "mock"
    format: Literal["JPEG", "RGB", "YUV"] = "RGB"
    width: int = 640
    height: int = 480
    quality: int = 85

@dataclass(frozen=True, slots=True)
class GPIOPinConfig:
    pin: int
    active_low: bool = False
    debounce_ms: int = 30

@dataclass(frozen=True, slots=True)
class GPIOConfig:
    driver: str = "mock"
    chip: str = "/dev/gpiochip0"
    pins: Mapping[str, GPIOPinConfig] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class CoreConfig:
    audio: AudioConfig
    display: DisplayConfig
    camera: CameraConfig
    gpio: GPIOConfig
```

Driver name由composition root的factory registry驗證；config不能import arbitrary class path。

Cross validation :

- `frame bytes = sample_rate * frame_duration_ms / 1000 * channels * bit_depth/8` 必須是整數；
- AudioInput / TTS output format必須一致，不做runtime resample；
- width / height正整數，camera quality 1..100；
- mono1 width需可被8整除；
- GPIO logical name與pin都不可重複，一pin一訂閱者；
- real driver需要的device/path欄位不可為 `None` 。

8. InputSource、Adaptor 與 external buffer

```python
@dataclass(frozen=True, slots=True)
class VoiceWakeConfig:
    policy: ComponentPolicy = ComponentPolicy(True, False)
    socket_path: Path = Path("/run/snowboard/wake.sock")
    # daemon-control timeouts (Ch 4 §2.1 WakeListenerControl)
    suspend_ack_seconds: float = 1.0  # cooperative suspend()/resume() IPC ACK 上限
    ensure_released_seconds: float = 2.0  # 強制釋放：terminate daemon + exit proof(waitpid) 上限

@dataclass(frozen=True, slots=True)
class ButtonInputConfig:
    policy: ComponentPolicy = ComponentPolicy(True, False)
    conversation_pin: str = "conversation"
    short_press_min_ms: int = 50    # 短按最小持續時間 (ms)；必須 ≥ debounce_ms
    long_press_min_ms: int = 1500   # 長按門檻 (ms)；必須 > short_press_min_ms

@dataclass(frozen=True, slots=True)
class ExternalInputConfig:
    policy: ComponentPolicy = ComponentPolicy(True, False)

@dataclass(frozen=True, slots=True)
class InputSourcesConfig:
    button: ButtonInputConfig
    voice_wake: VoiceWakeConfig
    external_message: ExternalInputConfig

@dataclass(frozen=True, slots=True)
class ExternalMessageConfig:
    buffer_max: int = 32
    overflow_policy: Literal["drop_oldest", "drop_newest", "reject"] = "drop_oldest"

@dataclass(frozen=True, slots=True)
class MQTTConfig:
    policy: ComponentPolicy = ComponentPolicy(False, False)
    host: str = "localhost"
    port: int = 1883
    username: str | None = None
    password: SecretValue | None = None
    topic_prefix: str = "snowboard"

@dataclass(frozen=True, slots=True)
class AdaptorsConfig:
    mqtt: MQTTConfig
```

InputSource / Adaptor預設optional。若產品部署要求某通道，local YAML明確設 `required: true` 。不增加「至少一個InputSource必須ready」的全域規則；某些 測試 / 管理模式允許系統啟動後由程式注入Signal。

9. Logging config

```python
@dataclass(frozen=True, slots=True)
class LogConfig:
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: Literal["text", "json"] = "text"
    file: Path | None = None
    rotate_max_bytes: int = 0
    rotate_backup_count: int = 0
```

- `file=None` → stderr。
- `rotate_max_bytes=0` → 不輪替；file非None時使用普通FileHandler。
- max bytes > 0 時backup count也必須 > 0，使用RotatingFileHandler。
- 不提供每module level，避免config膨脹；需要debug時調整root SBD logger。

10. 載入順序

```python
def load_config(
    *,
    local_path: Path = Path("config.local.yaml"),
    dotenv_path: Path = Path(".env"),
    environ: Mapping[str, str] = os.environ,
) -> AppConfig: ...
```

固定順序：

1. 建立code defaults tree。
2. local YAML存在則 `safe_load()` ；不存在合法。
3. strict recursive merge YAML。
4. 讀 `.env` ；同key process environment優先於 `.env` 。
5. 套用明列env mapping。
6. decode dataclasses / Path / SecretValue。
7. field validation。
8. cross-field validation。
9. freeze mappings，return AppConfig。

`config.example.yaml` 從不自動載入；它是local YAML模板。

11. Strict YAML overlay

規則：

- root必須mapping；空檔視為空mapping。
- allowed path由完整defaults tree與對應dataclass欄位一對一決定； `perception.listen.adapter.*` 與 `perception.look.adapter.*` 合法，舊 `perception.listen_adapter` / `perception.look_adapter` 一律是未知key。
- 未知key立即 `UnknownConfigKey(path)` 。
- scalar不能覆寫為mapping，反之亦然。
- bool不接受字串 `"true"` ；number不接受字串 `"1.0"` 。
- YAML null 只允許schema明確Optional欄位。
- list替換整個default list，不做append merge。
- `default_perceptions` decode成tuple，必須非空、無duplicate且只含 listen/read/look。
- 相對Path以config檔所在目錄resolve；default path以process cwd resolve。

Loader錯誤訊息帶dotted path與來源行line（PyYAML可取得），不輸出secret value。

12. .env 與 process environment

支援：

```text
KEY=value
KEY="quoted value"
# comment
```

不支援shell expansion、 export 、 command substitution或multiline。Malformed line 使startup失敗，不猜測。

明列mapping：

| env key | config path | secret |
| --- | --- | --- |
| `SBD_LOG_LEVEL` | `log.level` | 否 |
| `SBD_MQTT_USERNAME` | `adaptors.mqtt.username` | 否 |
| `SBD_MQTT_PASSWORD` | `adaptors.mqtt.password` | 是 |

未知 `SBD_` prefix key視為錯誤，抓出部署拼字問題。其他process env忽略。

`.env` 不進git； `.env.example` 只列key與空值：

```text
SBD_LOG_LEVEL=INFO
SBD_MQTT_USERNAME=
SBD_MQTT_PASSWORD=
```

13. Example YAML 最小骨架

```yaml
wake:
  ack_seconds: 0.3

perception:
  timeout_seconds:
    listen: 10.0
    read: 0.5
    look: 3.0
  default_perceptions: [listen]
  listen:
    enabled: true
    required: true
    adapter:
      driver: mock
      model_path: null
      language: null
  read:
    enabled: true
    required: false
  look:
    enabled: true
    required: false
    adapter:
      driver: mock
      model_path: null

cognition:
  reason_timeout_seconds: 30.0
  llm:
    driver: mock
    model_path: null

action:
  speak: {enabled: true, required: true}
  tool: {enabled: true, required: false}
  rest: {enabled: true, required: true}
  tts:
    driver: mock
    model_path: null

core:
  audio: {driver: mock}
  display: {driver: mock}
  camera: {driver: mock}
  gpio: {driver: mock, pins: {}}
```

Repository的完整 `config.example.yaml` 應列出所有schema欄位與註解，但不得包含 真實credential、使用者絕對路徑或Pi部署特定pin。它不是另外建的寬鬆範例schema； CI必須把該檔直接交給 §10同一個 `load_config()` strict path，任何unknown key、型別 或 cross-field錯誤都使測試失敗。

14. Error taxonomy

```python
class ConfigError(RuntimeError): ...
class ConfigFileError(ConfigError): ...
class ConfigParseError(ConfigError): ...
class UnknownConfigKey(ConfigError): ...
class ConfigTypeError(ConfigError): ...
class ConfigValueError(ConfigError): ...
class MissingSecretError(ConfigError): ...
```

Config load發生在Event Bus / SM之前：

- 不publish `errorOccurred` ；
- main以bootstrap logger / stderr記CRITICAL；
- exit non-zero；
- 不啟動任何resource。

15. 驗收與測試

最低純軟體測試：

1. 無local YAML / env得到完整defaults。
2. local YAML只需覆寫指定leaf，其餘defaults保留。
3. process env覆寫 `.env` ，兩者都覆寫YAML/default。
4. `config.example.yaml` 不會被loader自動讀取。
5. unknown key、mapping/scalar mismatch、錯type與非法null皆帶path失敗。
6. `required=true + enabled=false` 失敗。
7. `default_perceptions` 空、duplicate、未知kind失敗。
8. 所有timeout拒絕<=0、NaN與Infinity。
9. cancel / resource override未知kind失敗； `resource.*_timeout_seconds.by_kind` 只接受Ch 5 stable ResourceKey（ `backend.cognition.reasoner.llm` 通過、簡寫 `backend.llm` 失敗）， `cancel.*_timeout_seconds.by_kind` 只接受operation kind；兩namespace互斥。 9a. LLM startup / stop override以 `backend.cognition.reasoner.llm` 實際套用至該record；完整 defaults與 `config.example.yaml` 的resource段通過strict validation。
10. real backend缺device / model path失敗；mock不要求。
11. Audio frame size與TTS format cross validation。
12. duplicate GPIO logical / physical pin失敗。
13. SecretValue repr / str / dataclass repr不洩漏原值。
14. `.env` 不執行shell expansion，malformed line失敗。
15. unknown `SBD_` env key失敗，無關env忽略。
16. mapping freeze後mutation raise TypeError。
17. loader重複呼叫無global state、結果相同。
18. defaults tree、dataclass decoder與strict overlay對perception使用完全相同的 nested paths；舊 `listen_adapter` / `look_adapter` 以 `UnknownConfigKey` 拒絕。
19. repository完整 `config.example.yaml` 由 `load_config(local_path=example_path)` 走與production相同的strict merge、decode、field與cross-field validation並成功；assert adapter值落在 `config.perception.listen.adapter` 與 `config.perception.look.adapter` 。

16. 對後續章節的輸入

- Ch 11：固定stdlib logging所需 `LogConfig` 、logger flush timeout與secret redaction。
- milestone：Developer實作config時一併產出example files與schema tests。
