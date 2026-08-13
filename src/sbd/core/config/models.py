from dataclasses import dataclass, field
from typing import Mapping, Literal, Union, Any, Tuple
from pathlib import Path
import os

JsonValue = Union[str, int, float, bool, None, Mapping[str, Any], list[Any]]

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
    def __init__(self, value: str):
        self._value = value
    def reveal(self) -> str:
        return self._value
    def __repr__(self) -> str:
        return "SecretValue(***)"
    def __str__(self) -> str:
        return "***"
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, SecretValue):
            return NotImplemented
        return self._value == other._value

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
    adapter: ASRConfig = field(default_factory=ASRConfig)

@dataclass(frozen=True, slots=True)
class ReadConfig:
    enabled: bool = True
    required: bool = False

@dataclass(frozen=True, slots=True)
class LookConfig:
    enabled: bool = True
    required: bool = False
    adapter: VisionConfig = field(default_factory=VisionConfig)

@dataclass(frozen=True, slots=True)
class PerceptionConfig:
    timeout_seconds: PerceptionTimeouts
    default_perceptions: tuple[str, ...] = ("listen",)
    listen: ListenConfig = field(default_factory=ListenConfig)
    read: ReadConfig = field(default_factory=ReadConfig)
    look: LookConfig = field(default_factory=LookConfig)

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
    llm: LLMConfig = field(default_factory=LLMConfig)

@dataclass(frozen=True, slots=True)
class TTSConfig:
    driver: Literal["mock", "piper"] = "mock"
    model_path: Path | None = None
    voice_id: str | None = None

@dataclass(frozen=True, slots=True)
class ActionConfig:
    speak: ComponentPolicy = field(default_factory=lambda: ComponentPolicy(True, True))
    tool: ComponentPolicy = field(default_factory=lambda: ComponentPolicy(True, False))
    rest: ComponentPolicy = field(default_factory=lambda: ComponentPolicy(True, True))
    tts: TTSConfig = field(default_factory=TTSConfig)

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

@dataclass(frozen=True, slots=True)
class ExternalMessageConfig:
    buffer_max: int = 32
    overflow_policy: Literal["drop_oldest", "drop_newest", "reject"] = "drop_oldest"
    allowed_channels: tuple[str, ...] = ("fixture",)

@dataclass(frozen=True, slots=True)
class VoiceWakeConfig:
    policy: ComponentPolicy = field(default_factory=lambda: ComponentPolicy(True, False))
    socket_path: Path = field(default_factory=lambda: Path("/run/snowboard/wake.sock"))
    suspend_ack_seconds: float = 1.0
    ensure_released_seconds: float = 2.0

@dataclass(frozen=True, slots=True)
class ButtonInputConfig:
    policy: ComponentPolicy = field(default_factory=lambda: ComponentPolicy(True, False))
    conversation_pin: str = "conversation"
    short_press_min_ms: int = 50
    long_press_min_ms: int = 1500

@dataclass(frozen=True, slots=True)
class ExternalInputConfig:
    policy: ComponentPolicy = field(default_factory=lambda: ComponentPolicy(True, False))

@dataclass(frozen=True, slots=True)
class InputSourcesConfig:
    button: ButtonInputConfig
    voice_wake: VoiceWakeConfig
    external_message: ExternalInputConfig

@dataclass(frozen=True, slots=True)
class MQTTConfig:
    policy: ComponentPolicy = field(default_factory=lambda: ComponentPolicy(False, False))
    host: str = "localhost"
    port: int = 1883
    username: str | None = None
    password: SecretValue | None = None
    topic_prefix: str = "snowboard"

@dataclass(frozen=True, slots=True)
class AdaptorsConfig:
    mqtt: MQTTConfig

@dataclass(frozen=True, slots=True)
class LogConfig:
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: Literal["text", "json"] = "text"
    file: Path | None = None
    rotate_max_bytes: int = 0
    rotate_backup_count: int = 0

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
    native_library_path: Path | None = None
    native_library_sha256: str | None = None
    native_abi_version: int | None = None
    spi_device: str | None = None
    spi_speed_hz: int | None = None
    spi_mode: int | None = None
    spi_chip_select: int | None = None
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
