from .models import (
    AppConfig, WakeConfig, PerceptionConfig, CognitionConfig, ActionConfig,
    CancelConfig, ResourceConfig, ShutdownConfig, ExternalMessageConfig,
    CoreConfig, InputSourcesConfig, AdaptorsConfig, LogConfig,
    PerceptionTimeouts, ListenConfig, ReadConfig, LookConfig, ASRConfig, VisionConfig,
    LLMConfig, TTSConfig, ComponentPolicy, TimeoutMap,
    AudioConfig, DisplayConfig, CameraConfig, GPIOConfig,
    ButtonInputConfig, VoiceWakeConfig, ExternalInputConfig, MQTTConfig
)
from types import MappingProxyType
from pathlib import Path

DEFAULT_CONFIG = AppConfig(
    wake=WakeConfig(),
    perception=PerceptionConfig(
        timeout_seconds=PerceptionTimeouts(),
        default_perceptions=("listen",),
        listen=ListenConfig(),
        read=ReadConfig(),
        look=LookConfig()
    ),
    cognition=CognitionConfig(
        reason_timeout_seconds=30.0,
        llm=LLMConfig()
    ),
    action=ActionConfig(
        speak=ComponentPolicy(True, True),
        tool=ComponentPolicy(True, False),
        rest=ComponentPolicy(True, True),
        tts=TTSConfig()
    ),
    cancel=CancelConfig(
        abort_timeout_seconds=TimeoutMap(
            default=2.0,
            by_kind=MappingProxyType({})
        ),
        force_abort_timeout_seconds=TimeoutMap(
            default=1.0,
            by_kind=MappingProxyType({
                "cognition.reasoner": 3.0
            })
        )
    ),
    resource=ResourceConfig(
        startup_timeout_seconds=TimeoutMap(
            default=15.0,
            by_kind=MappingProxyType({
                "backend.cognition.reasoner.llm": 120.0,
                "backend.perception.listen.asr": 30.0,
                "backend.action.speak.tts": 30.0,
            })
        ),
        stop_timeout_seconds=TimeoutMap(
            default=3.0,
            by_kind=MappingProxyType({
                "backend.cognition.reasoner.llm": 10.0,
                "backend.perception.listen.asr": 5.0,
                "backend.action.speak.tts": 5.0,
            })
        ),
        recovery_timeout_seconds=30.0,
        recovery_shutdown_cleanup_timeout_seconds=5.0
    ),
    shutdown=ShutdownConfig(
        sm_drain_timeout_seconds=5.0,
        logger_flush_timeout_seconds=2.0
    ),
    external_message=ExternalMessageConfig(),
    core=CoreConfig(
        audio=AudioConfig(),
        display=DisplayConfig(),
        camera=CameraConfig(),
        gpio=GPIOConfig(pins=MappingProxyType({}))
    ),
    input_sources=InputSourcesConfig(
        button=ButtonInputConfig(),
        voice_wake=VoiceWakeConfig(),
        external_message=ExternalInputConfig()
    ),
    adaptors=AdaptorsConfig(
        mqtt=MQTTConfig()
    ),
    log=LogConfig()
)
