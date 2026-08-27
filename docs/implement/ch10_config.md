# Ch 10. Config schema

屬於 implement.md 索引 | 對應 arch.md §7.1 | 狀態：基礎契約定稿（IR-final 2026-08-01）；M4a production extension待Reviewer審查（2026-08-26）

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
    driver: Literal["mock", "null", "whispercpp"] = "mock"
    engine_name: str | None = None
    model_path: Path | None = None
    worker_path: Path | None = None
    runtime_python: Path | None = None
    vad_model_path: Path | None = None
    artifact_lock_path: Path | None = None
    language: str | None = None
    dsp_profile: str | None = None
    decoder_profile: str | None = None
    child_ready_timeout_seconds: float = 30.0
    child_terminate_timeout_seconds: float = 5.0
    child_kill_wait_timeout_seconds: float = 2.0

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
    driver: Literal["mock", "null", "sherpa_matcha"] = "mock"
    engine_name: str | None = None
    model_path: Path | None = None
    vocoder_path: Path | None = None
    runtime_python: Path | None = None
    artifact_lock_path: Path | None = None
    voice_id: str | None = None
    native_sample_rate: int | None = None
    native_channels: int | None = None
    native_sample_format: str | None = None
    child_ready_timeout_seconds: float = 30.0
    child_terminate_timeout_seconds: float = 5.0
    child_kill_wait_timeout_seconds: float = 2.0

@dataclass(frozen=True, slots=True)
class ActionConfig:
    speak: ComponentPolicy = ComponentPolicy(True, True)
    tool: ComponentPolicy = ComponentPolicy(True, False)
    rest: ComponentPolicy = ComponentPolicy(True, True)
    tts: TTSConfig = TTSConfig()
```

Reasoner固定required，不提供 `required` 欄位； `cognition.llm.driver=litert_lm` 時 `model_path` 必須且必須是file。Mock不要求path。

M4a real Audio adapter另套用`model_spec.md`與`ch_m4a_audio_production.md`：

- `whispercpp`要求engine=`whisper.cpp-1.9.2`、language=`zh-TW`、DSP=`silero-6.2.1-endpoint-v1`、decoder=`p0-greedy-best-of-1`，以及model / worker / VAD runtime / VAD model / artifact lock五個絕對路徑；
- `sherpa_matcha`要求engine=`sherpa-onnx-1.13.5-matcha`、voice=`matcha-zh-en-default-sid-0`、native format=`16000/1/s16_le`，以及model dir / Vocos / runtime / artifact lock四個絕對路徑；
- 兩個real Audio adapter各自的READY、TERM wait與KILL wait timeout皆必須為strict config中的有限正數；不得使用無界child wait；
- YAML只能選tracked lock，不得覆寫checksum；path存在與artifact identity由product preflight在child / Audio HAL前fail closed；
- `mock` / `null`不得因real-only path為空而失敗，也不得importreal module。

`action.tool.enabled=true` 但sealed ToolRegistry為空時，依Ch 9視為tool worker未載入； `required=false` 得到P2=false， `required=true` 則startup fatal。

ASR / Vision config已在§5成為 `ListenConfig.adapter` 與 `LookConfig.adapter` 的實際 欄位。不存在root-level perception adapter欄位；所有factory、validation、example 與文件都使用 `perception.listen.adapter` / `perception.look.adapter` 。

7. Core HAL

```python
@dataclass(frozen=True, slots=True)
class AudioFormatConfig:
    sample_rate: int = 16_000
    channels: int = 1
    sample_format: Literal["s16_le", "s32_le"] = "s16_le"

@dataclass(frozen=True, slots=True)
class AudioInputConfig:
    stream_format: AudioFormatConfig = field(default_factory=AudioFormatConfig)
    frame_duration_ms: int = 20
    device: str | None = None
    native_format: AudioFormatConfig | None = None
    channel_index: Literal[0, 1] | None = None
    valid_bits: int | None = None
    valid_bits_alignment: str | None = None
    resampler: str | None = None

@dataclass(frozen=True, slots=True)
class AudioOutputConfig:
    stream_format: AudioFormatConfig = field(default_factory=AudioFormatConfig)
    device: str | None = None
    native_format: AudioFormatConfig | None = None

@dataclass(frozen=True, slots=True)
class AudioConfig:
    driver: str = "mock"
    input: AudioInputConfig = field(default_factory=AudioInputConfig)
    output: AudioOutputConfig = field(default_factory=AudioOutputConfig)

@dataclass(frozen=True, slots=True)
class DisplayConfig:
    driver: str = "mock"
    profile: Literal["DSP-PROFILE-OLED-128"] = "DSP-PROFILE-OLED-128"
    width: int = 128
    height: int = 128
    pixel_format: Literal["rgb565"] = "rgb565"
    rotation: Literal[0] = 0
    byte_order: Literal["msb_first"] = "msb_first"
    frame_buffer_bytes: Literal[32768] = 32768
    show_session_content: bool = True

    # SSD1351 real-backend deployment fields. Generic mock/null defaults must
    # not contain a native artifact location or Pi fixture wiring.
    native_library_path: Path | None = None
    native_library_sha256: str | None = None
    native_abi_version: int | None = None
    spi_device: str | None = None
    spi_speed_hz: int | None = None
    spi_mode: int | None = None
    spi_chip_select: int | None = None
    gpio_chip_index: int | None = None
    dc_bcm: int | None = None
    reset_bcm: int | None = None

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

- `sample_format` 的 container bytes 為 `s16_le=2`、`s32_le=4`；`frame bytes = sample_rate * frame_duration_ms / 1000 * channels * container_bytes` 必須是整數；
- AudioInput stream format與AudioOutput stream format獨立。Listen / ASR必須匹配 `audio.input.stream_format`；TTS / Speak必須匹配 `audio.output.stream_format`。Listen、ASR、TTS與Speak不得隱式resample；只有本節明列的M3 real AudioInput adaptation可在HAL內轉換native→stream；
- width / height正整數，camera quality 1..100；selected `DSP-PROFILE-OLED-128` 對所有 driver 都固定 `128×128`、`rgb565`、rotation `0`、RGB565 MSB-first 與 `128 * 128 * 2 = 32768` bytes 完整 frame。任何矛盾值都在 factory / native code 之前以 `ConfigValueError` 拒絕；未來 profile 必須另定 profile-specific validation；
- `show_session_content` 實作 `DSP-REQ-004`，只控制 `display_spec.md` 的 Perception / Tool / Speak 內容；State、Error、Blank 與 lifecycle 不受影響，且此設定為 startup-static、不支援 runtime reload；
- GPIO logical name與pin都不可重複，一pin一訂閱者；
- real driver需要的device/path欄位不可為 `None` 。

`driver="alsa"` 的M3 Option A語意依`DELIVERY-AUDIO-POC-M3-ACK-002`固定；下列mapping除resampler implementation identifier外可先實作strict validation。Audio real factory與production dependency lock須等`DELIVERY-AUDIO-POC-M3-VALIDATION-001`通過後才放行：

| 欄位 | 合法值 / 規則 | 原因 |
| :--- | :--- | :--- |
| `input.device` | 必填 direct `hw:` identifier；不得為 `plughw:`；POC P2 baseline為 `hw:0,0` | 禁止 ALSA 隱式 format conversion；實際值由 Pi local config提供 |
| `input.native_format` | 48000 Hz / 2 channels / `s32_le` | POC direct native capability matrix |
| `input.stream_format` | 16000 Hz / 1 channel / `s16_le` | 對 Listen / VAD / ASR 的既有產品契約 |
| `input.frame_duration_ms` | `20` | 320 samples / 640 bytes exact frame |
| `input.channel_index` | 必填 `0` 或 `1` | 由 INMP441 L/R 接線與 operator attestation決定，不猜測 |
| `input.valid_bits` / `valid_bits_alignment` | POC驗證後固定；目前候選為`24` / `msb` | I2S資料語意與ALSA S32 container表示必須由target fixture交叉驗證，不以datasheet推論取代實測 |
| `input.resampler` | POC通過後必填Core核准的implementation identifier | stateful streaming anti-alias converter，ratio 1/3；候選名稱不得先成為production allowlist |
| `output.device` | 必填 direct `hw:` identifier；不得為 `plughw:`；POC P2 baseline為 `hw:0,0` | M3 direct playback evidence |
| `output.native_format` | 48000 Hz / 2 channels / `s32_le` | POC direct native capability matrix |
| `output.stream_format` | M3 必須等於 `output.native_format` | P3 TTS winner前不核准output adaptation |

Loader必須在Audio factory / Pi-only import前拒絕unknown key、缺real欄位、非selected native / stream format、非法channel、未宣告mismatch、`plughw:`或非Core核准resampler。POC gate未通過時不存在核准resampler，`driver="alsa"`不得成為可發布的production config。`input.native_format != input.stream_format`只在完整Option A mapping成立時合法；其他mismatch一律`ConfigValueError`。`mock` / `null`只使用input / output stream format，若攜帶`device`、`native_format`、channel / valid-bits / resampler任一real-only值即拒絕。

Startup必須再以backend實際開啟結果核對direct device與native format；config parse成功不等於硬體capability PASS。Runtime不允許format renegotiation。Config的repr / log可列sanitized `hw:` identifier與format，但不得記raw PCM、endpoint、account或private path。

Audio POC須回交候選binding / resampler比較、exact版本與source hash、transitive dependency、license / notice、system package、target build命令及runtime library identity。Core核准後才把選定值寫入schema allowlist與deployment lock；binding由target Pi build / install，產生的wheel / shared object不進Git。Pi evidence記錄實際package與native library版本。

`driver="ssd1351"` 是 M3 唯一 selected real backend，另套用下列 strict cross-field validation：

| 欄位 | 合法值 / 規則 | 原因 |
| :--- | :--- | :--- |
| `native_library_path` | 必填、存在的 regular file | artifact 位置由 Pi local deployment config 提供；不得放入 generic defaults |
| `native_library_sha256` | 必填、64 個小寫 hex，且與檔案 SHA-256 相同 | 只載入已核准的 exact artifact |
| `native_abi_version` | `1` | 對應 accepted Display ABI v1；adapter 在 `dlopen` 後、`display_open` 前再驗 exported ABI / struct size |
| `spi_device` | `/dev/spidev0.0` | SPI0 CE0；CE0 由 kernel 管理，不得另由 GPIO library claim |
| `spi_speed_hz` | `4000000` | accepted M3 baseline；不得把未驗證的 requested speed 當 effective throughput |
| `spi_mode` | `0` | selected SSD1351 fixture |
| `spi_chip_select` | `0` | CE0，對應 BCM8 / physical pin 24；native config 的 software-CS 必須保持 disabled (`cs=-1`) |
| `gpio_chip_index` | 必填 `0..2147483647` 整數；target baseline 由 operator 將實際 gpiochip resolve 為 index，M3 fixture 為 `0` | 對齊 ABI v1 `int32_t`；唯一 authoritative strict loader 驗證後，adapter 原樣映射至 `_CDisplayConfig.gpio_chip.chip_index`，不得由環境、global probe 或 `GPIOConfig.chip` 推測 |
| `dc_bcm` | `24` | co-I2S fixture；physical pin 18 |
| `reset_bcm` | `25` | co-I2S fixture；physical pin 22 |

`dc_bcm`、`reset_bcm` 必須互異，且不得等於 kernel-owned CE0 BCM8、SPI0 MOSI BCM10 或 SCLK BCM11。上述 native / SPI / GPIO 欄位只允許在 `driver="ssd1351"` 時出現；`mock` / `null` 若攜帶任一 real-only 值即為矛盾 config，必須以 `ConfigValueError` 拒絕。Loader 先完成 unknown-key、型別、path / checksum 與所有 cross-field validation，composition root 才可呼叫 Display factory；因此 invalid config 不得觸及 GPIO、SPI 或 native library。

Factory 只在 `driver="ssd1351"` 分支 lazy import `sbd.core.display.ssd1351.driver`，並把已驗證的 `DisplayConfig` 原樣交給 adapter。Adapter 必須直接把 `DisplayConfig.gpio_chip_index` 寫入 ABI v1 `_CDisplayConfig.gpio_chip.chip_index`；不得讀取 `GPIOConfig.chip`、環境變數、hidden global、硬編碼 target index，或另行解析設定。`null` / `mock` 分支不得攜帶 `gpio_chip_index`，亦不得 import、`dlopen`、hash 或 probe native artifact。SSD1351 adapter 必須在建立硬體 handle 前驗證 ABI v1 / struct size，將 artifact / ABI 不符視為 startup failure；RM 依 Ch 2a 的 real→null 規則降級。共用 Renderer、Arbiter 與 Resource Manager 不得 import SSD1351 module 或判斷其 pin / SPI 欄位。

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
      engine_name: null
      model_path: null
      worker_path: null
      runtime_python: null
      vad_model_path: null
      artifact_lock_path: null
      language: null
      dsp_profile: null
      decoder_profile: null
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
    engine_name: null
    model_path: null
    vocoder_path: null
    runtime_python: null
    artifact_lock_path: null
    voice_id: null
    native_sample_rate: null
    native_channels: null
    native_sample_format: null

core:
  audio: {driver: mock}
  display:
    driver: mock
    width: 128
    height: 128
    pixel_format: rgb565
    show_session_content: true
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
20. `whispercpp`與`sherpa_matcha`的required field / exact profile table-driven驗證；每個missing/mismatch以含完整path的`ConfigValueError`在factory前拒絕。
21. `mock` / `null`保留無artifact default；real-only module保持未import，factory unknown driver fail closed。
22. YAML嘗試提供checksum override或舊`whisper` / `piper` driver視為unknown/invalid，不得fallback到real或mock。

16. 對後續章節的輸入

- Ch 11：固定stdlib logging所需 `LogConfig` 、logger flush timeout與secret redaction。
- milestone：Developer實作config時一併產出example files與schema tests。
