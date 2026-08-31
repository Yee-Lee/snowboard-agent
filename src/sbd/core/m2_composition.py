"""Default all-mock M2 ResourceManager composition."""

from __future__ import annotations

from sbd.action.payload_validator import ActionPayloadValidator
from sbd.action.rest import Rest
from sbd.action.speak import Speak, make_tts_adapter
from sbd.action.tool import Tool, ToolRegistry
from sbd.cognition.llm import (
    LLMGeneration,
    LLMGenerationMetrics,
    MockLLMEngineAdapter,
)
from sbd.cognition.factory import make_llm_adapter
from sbd.cognition.prompt_builder import PromptBuilder
from sbd.cognition.reasoner import Reasoner
from sbd.core.audio import make_audio_input, make_audio_output
from sbd.core.audio.null import NullAudioInput, NullAudioOutput
from sbd.core.camera import make_camera
from sbd.core.camera.null import NullCamera
from sbd.core.config.models import AppConfig
from sbd.core.display import make_display
from sbd.core.display.null import NullDisplay
from sbd.core.event_bus import EventBus
from sbd.core.gpio import make_gpio
from sbd.core.resource_manager import ResourceManager, ResourceSpec, StartPhase
from sbd.input_events.external_message import ExternalMessageSource
from sbd.input_events.mock import MockButtonInputSource, MockWakeWordInputSource
from sbd.input_events.button import ButtonInputSource
from sbd.perception.listen import Listen, make_asr_adapter
from sbd.perception.look import Look, MockVisionAdapter
from sbd.perception.read import Read


class _NoopAggregate:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


class M2Composition:
    """One-use composition object that exposes mock sources to flow fixtures."""

    def __init__(
        self,
        *,
        tools: ToolRegistry | None = None,
        action_validator: ActionPayloadValidator | None = None,
        llm_outcomes: tuple[LLMGeneration | Exception, ...] | None = None,
    ) -> None:
        self.tools = tools or ToolRegistry()
        self.action_validator = action_validator or ActionPayloadValidator(
            tools=self.tools
        )
        self.llm_outcomes = llm_outcomes or (
            LLMGeneration(
                {
                    "action_kind": "rest",
                    "action_payload": {},
                    "next_perceptions": [],
                },
                LLMGenerationMetrics(0.0, 1.0, 1, 1.0, 1, 1.0, 1),
            ),
        )
        self.button: MockButtonInputSource | None = None
        self.wake_word: MockWakeWordInputSource | None = None
        self.external_message: ExternalMessageSource | None = None
        self._registered = False

    def __call__(
        self,
        rm: ResourceManager,
        bus: EventBus,
        config: AppConfig,
    ) -> None:
        if self._registered:
            raise RuntimeError("M2 composition may only be registered once")
        self._registered = True
        self.tools.seal()

        audio_input = make_audio_input(config.core.audio)
        audio_output = make_audio_output(config.core.audio)
        display = make_display(config.core.display)
        camera = make_camera(config.core.camera)
        gpio = make_gpio(config.core.gpio)
        asr = make_asr_adapter(config.perception.listen.adapter)
        vision = MockVisionAdapter()
        if config.cognition.llm.driver == "mock":
            llm = MockLLMEngineAdapter(self.llm_outcomes)
        else:
            from sbd.cognition.litert_lm.resource import ProcLLMResourceSampler

            llm = make_llm_adapter(
                config.cognition.llm,
                schedule_recovery=rm.begin_recovery,
                wait_recovery=rm.wait_recovery,
                resource_sampler=ProcLLMResourceSampler(),
            )
        tts = make_tts_adapter(config.action.tts)
        external = ExternalMessageSource(
            bus=bus,
            max_items=config.external_message.buffer_max,
            overflow_policy=config.external_message.overflow_policy,
            allowed_channels=frozenset(config.external_message.allowed_channels),
        )
        self.external_message = external
        if config.core.gpio.driver == "gpiod":
            pin_config = config.core.gpio.pins.get(
                config.input_sources.button.conversation_pin
            )
            if pin_config is None:
                raise ValueError("conversation button pin is missing from core.gpio.pins")
            self.button = ButtonInputSource(
                gpio=gpio, bus=bus, config=config.input_sources.button,
                pin_config=pin_config,
            )
        else:
            self.button = MockButtonInputSource(bus=bus)
        self.wake_word = MockWakeWordInputSource(bus=bus)

        rm.register(ResourceSpec(
            key="core.audio.input", phase=StartPhase.CORE,
            factory=lambda resolver: audio_input,
            null_factory=lambda resolver: NullAudioInput(config.core.audio),
        ))
        rm.register(ResourceSpec(
            key="core.audio.output", phase=StartPhase.CORE,
            factory=lambda resolver: audio_output,
            null_factory=lambda resolver: NullAudioOutput(),
        ))
        rm.register(ResourceSpec(
            key="core.audio", phase=StartPhase.CORE,
            dependencies=("core.audio.input", "core.audio.output"),
            factory=lambda resolver: _NoopAggregate(), capability_kind="audio",
        ))
        rm.register(ResourceSpec(
            key="core.display", phase=StartPhase.CORE,
            factory=lambda resolver: display, capability_kind="display",
            null_factory=lambda resolver: NullDisplay(),
        ))
        rm.register(ResourceSpec(
            key="core.camera", phase=StartPhase.CORE,
            factory=lambda resolver: camera, capability_kind="camera",
            null_factory=lambda resolver: NullCamera(config.core.camera),
        ))
        rm.register(ResourceSpec(
            key="core.gpio", phase=StartPhase.CORE,
            factory=lambda resolver: gpio, capability_kind="gpio",
            required=False,
        ))
        rm.register(ResourceSpec(
            key="backend.perception.listen.asr", phase=StartPhase.BACKEND,
            factory=lambda resolver: asr,
            recoverable=config.perception.listen.adapter.driver == "whispercpp",
            recovery_hook=(
                asr
                if config.perception.listen.adapter.driver == "whispercpp"
                else None
            ),
        ))
        rm.register(ResourceSpec(
            key="backend.perception.look.vision", phase=StartPhase.BACKEND,
            factory=lambda resolver: vision,
        ))
        rm.register(ResourceSpec(
            key="backend.cognition.reasoner.llm", phase=StartPhase.BACKEND,
            factory=lambda resolver: llm,
            recoverable=config.cognition.llm.driver == "litert_lm",
            recovery_hook=(llm if config.cognition.llm.driver == "litert_lm" else None),
        ))
        rm.register(ResourceSpec(
            key="backend.action.speak.tts", phase=StartPhase.BACKEND,
            factory=lambda resolver: tts,
            recoverable=config.action.tts.driver == "sherpa_matcha",
            recovery_hook=(
                tts if config.action.tts.driver == "sherpa_matcha" else None
            ),
        ))

        if config.perception.listen.enabled:
            rm.register(ResourceSpec(
                key="worker.perception.listen", phase=StartPhase.WORKER,
                dependencies=(
                    "core.audio.input",
                    "backend.perception.listen.asr",
                ),
                factory=lambda resolver: Listen(
                    audio_input=resolver.require("core.audio.input"),
                    asr=resolver.require("backend.perception.listen.asr"),
                    bus=bus,
                ),
                required=config.perception.listen.required,
                capability_kind="listen", capability_dependencies=("audio",),
            ))
        if config.perception.read.enabled:
            rm.register(ResourceSpec(
                key="worker.perception.read", phase=StartPhase.WORKER,
                factory=lambda resolver: Read(
                    consumer=external.consumer,
                    bus=bus,
                ),
                required=config.perception.read.required,
                capability_kind="read",
            ))
        if config.perception.look.enabled:
            rm.register(ResourceSpec(
                key="worker.perception.look", phase=StartPhase.WORKER,
                dependencies=(
                    "core.camera",
                    "backend.perception.look.vision",
                ),
                factory=lambda resolver: Look(
                    camera=resolver.require("core.camera"),
                    vision=resolver.require("backend.perception.look.vision"),
                    bus=bus,
                ),
                required=config.perception.look.required,
                capability_kind="look", capability_dependencies=("camera",),
            ))
        rm.register(ResourceSpec(
            key="worker.cognition.reasoner", phase=StartPhase.WORKER,
            dependencies=("backend.cognition.reasoner.llm",),
            factory=lambda resolver: Reasoner(
                resolver.require("backend.cognition.reasoner.llm"),
                PromptBuilder(self.tools.schemas()),
                bus,
                rm.reasoner_capability_of,
                self.action_validator,
                config.cognition.reason_timeout_seconds,
            ),
            required=True,
        ))
        if config.action.speak.enabled:
            rm.register(ResourceSpec(
                key="worker.action.speak", phase=StartPhase.WORKER,
                dependencies=(
                    "core.audio.output",
                    "backend.action.speak.tts",
                ),
                factory=lambda resolver: Speak(
                    tts=resolver.require("backend.action.speak.tts"),
                    audio_output=resolver.require("core.audio.output"),
                    bus=bus,
                ),
                required=config.action.speak.required,
                capability_kind="speak", capability_dependencies=("audio",),
            ))
        if config.action.tool.enabled and self.tools.schemas():
            rm.register(ResourceSpec(
                key="worker.action.tool", phase=StartPhase.WORKER,
                factory=lambda resolver: Tool(registry=self.tools, bus=bus),
                required=config.action.tool.required,
                capability_kind="tool",
            ))
        rm.register(ResourceSpec(
            key="worker.action.rest", phase=StartPhase.WORKER,
            factory=lambda resolver: Rest(bus=bus), required=True,
        ))

        if config.input_sources.button.policy.enabled:
            rm.register(ResourceSpec(
                key="input.button", phase=StartPhase.INPUT_PRODUCER,
                dependencies=("core.gpio",),
                factory=lambda resolver: self.button,
                required=config.input_sources.button.policy.required,
            ))
        if config.input_sources.external_message.policy.enabled:
            rm.register(ResourceSpec(
                key="input.external_message", phase=StartPhase.INPUT_PRODUCER,
                factory=lambda resolver: external,
                required=config.input_sources.external_message.policy.required,
            ))
        if config.input_sources.voice_wake.policy.enabled:
            rm.register(ResourceSpec(
                key="input.voice_wake", phase=StartPhase.INPUT_PRODUCER,
                factory=lambda resolver: self.wake_word,
                required=config.input_sources.voice_wake.policy.required,
            ))


__all__ = ["M2Composition"]
