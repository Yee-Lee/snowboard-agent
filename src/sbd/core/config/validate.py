class ConfigError(RuntimeError): ...
class ConfigFileError(ConfigError): ...
class ConfigParseError(ConfigError): ...
class UnknownConfigKey(ConfigError): ...
class ConfigTypeError(ConfigError): ...
class ConfigValueError(ConfigError): ...
class MissingSecretError(ConfigError): ...

def validate_config(config: 'AppConfig'):
    # required=True + enabled=False => ConfigValueError
    def check_policy(p, path):
        if p.required and not p.enabled:
            raise ConfigValueError(f"{path}: required=True but enabled=False is a contradiction")

    def check_engine_config(driver, engine_name, path):
        if driver not in ("mock", "null") and engine_name is None:
            raise ConfigValueError(
                f"{path}.engine_name is required when driver is not 'mock' or 'null'"
            )

    check_policy(config.perception.listen, "perception.listen")
    check_policy(config.perception.read, "perception.read")
    check_policy(config.perception.look, "perception.look")
    check_policy(config.action.speak, "action.speak")
    check_policy(config.action.tool, "action.tool")
    check_policy(config.action.rest, "action.rest")
    check_policy(config.input_sources.button.policy, "input_sources.button.policy")
    check_policy(config.input_sources.voice_wake.policy, "input_sources.voice_wake.policy")
    check_policy(config.input_sources.external_message.policy, "input_sources.external_message.policy")
    check_policy(config.adaptors.mqtt.policy, "adaptors.mqtt.policy")

    # default_perceptions non-empty tuple of valid kinds
    if not config.perception.default_perceptions:
        raise ConfigValueError("perception.default_perceptions cannot be empty")

    seen = set()
    for kind in config.perception.default_perceptions:
        if kind not in {"listen", "read", "look"}:
            raise ConfigValueError(f"Unknown default perception kind: {kind}")
        if kind in seen:
            raise ConfigValueError(f"Duplicate default perception kind: {kind}")
        seen.add(kind)

    # validate timeouts > 0, finite
    import math
    def check_timeout(val, path):
        if type(val) not in (int, float):
            raise ConfigTypeError(f"{path} must be a number, got {type(val)}")
        if math.isnan(val) or math.isinf(val) or val <= 0:
            raise ConfigValueError(f"{path} timeout must be a finite positive number, got {val}")

    check_timeout(config.wake.ack_seconds, "wake.ack_seconds")
    check_timeout(config.perception.timeout_seconds.listen, "perception.timeout_seconds.listen")
    check_timeout(config.perception.timeout_seconds.read, "perception.timeout_seconds.read")
    check_timeout(config.perception.timeout_seconds.look, "perception.timeout_seconds.look")
    check_timeout(config.cognition.reason_timeout_seconds, "cognition.reason_timeout_seconds")
    check_timeout(config.cognition.llm.child_ready_timeout_seconds, "cognition.llm.child_ready_timeout_seconds")
    check_timeout(config.cognition.llm.child_terminate_timeout_seconds, "cognition.llm.child_terminate_timeout_seconds")
    check_timeout(config.cognition.llm.child_kill_wait_timeout_seconds, "cognition.llm.child_kill_wait_timeout_seconds")

    # Cancel timeouts
    check_timeout(config.cancel.abort_timeout_seconds.default, "cancel.abort_timeout_seconds.default")
    for k, v in config.cancel.abort_timeout_seconds.by_kind.items():
        check_timeout(v, f"cancel.abort_timeout_seconds.by_kind.{k}")
    check_timeout(config.cancel.force_abort_timeout_seconds.default, "cancel.force_abort_timeout_seconds.default")
    for k, v in config.cancel.force_abort_timeout_seconds.by_kind.items():
        check_timeout(v, f"cancel.force_abort_timeout_seconds.by_kind.{k}")

    # Resource timeouts
    check_timeout(config.resource.startup_timeout_seconds.default, "resource.startup_timeout_seconds.default")
    for k, v in config.resource.startup_timeout_seconds.by_kind.items():
        check_timeout(v, f"resource.startup_timeout_seconds.by_kind.{k}")
    check_timeout(config.resource.stop_timeout_seconds.default, "resource.stop_timeout_seconds.default")
    for k, v in config.resource.stop_timeout_seconds.by_kind.items():
        check_timeout(v, f"resource.stop_timeout_seconds.by_kind.{k}")
    check_timeout(config.resource.recovery_timeout_seconds, "resource.recovery_timeout_seconds")
    check_timeout(config.resource.recovery_shutdown_cleanup_timeout_seconds, "resource.recovery_shutdown_cleanup_timeout_seconds")

    # Shutdown
    check_timeout(config.shutdown.sm_drain_timeout_seconds, "shutdown.sm_drain_timeout_seconds")
    check_timeout(config.shutdown.logger_flush_timeout_seconds, "shutdown.logger_flush_timeout_seconds")

    # cancel timeouts only accept operation kinds
    allowed_cancel_keys = {
        "perception.listen", "perception.read", "perception.look",
        "cognition.reasoner", "action.speak", "action.tool", "action.rest"
    }
    for k in config.cancel.abort_timeout_seconds.by_kind:
        if k not in allowed_cancel_keys:
            raise ConfigValueError(f"Invalid cancel timeout kind: {k}")
    for k in config.cancel.force_abort_timeout_seconds.by_kind:
        if k not in allowed_cancel_keys:
            raise ConfigValueError(f"Invalid cancel timeout kind: {k}")

    # resource timeouts only accept stable ResourceKeys
    # stable resource key list from spec:
    # "backend.cognition.reasoner.llm"
    # "core.audio.input"
    # Wait, the spec says: `resource.*_timeout_seconds.by_kind` keys must be from stable ResourceKey namespace, e.g. "backend.cognition.reasoner.llm", "core.audio.input", ...
    # We will just check if they are dotted paths and not operation kinds for now, or match a strict registry. Let's list the known ones.
    # Actually, the registry is in Ch 5 §3.1. We can at least reject if it looks like an operation kind or `backend.llm`.
    allowed_resource_keys = {
        "core.audio.input",
        "core.audio.output",
        "core.display",
        "core.camera",
        "core.gpio",
        "backend.perception.listen.asr",
        "backend.perception.look.vision",
        "backend.cognition.reasoner.llm",
        "backend.action.speak.tts",
        "backend.action.tool.executor",
        "input.button",
        "input.voice_wake",
        "input.external_message",
        "adaptor.mqtt"
    }
    for k in config.resource.startup_timeout_seconds.by_kind:
        if k not in allowed_resource_keys:
            raise ConfigValueError(f"Invalid resource timeout key: {k}")
    for k in config.resource.stop_timeout_seconds.by_kind:
        if k not in allowed_resource_keys:
            raise ConfigValueError(f"Invalid resource timeout key: {k}")

    # Audio math
    def check_positive_int(value, path):
        if type(value) is not int or value <= 0:
            raise ConfigValueError(f"{path} must be a positive integer")

    display = config.core.display
    selected_display = {
        "profile": "DSP-PROFILE-OLED-128",
        "width": 128,
        "height": 128,
        "pixel_format": "rgb565",
        "rotation": 0,
        "byte_order": "msb_first",
        "frame_buffer_bytes": 32768,
    }
    for field, expected in selected_display.items():
        if getattr(display, field) != expected:
            raise ConfigValueError(
                f"core.display.{field} must be {expected!r} for DSP-PROFILE-OLED-128"
            )
    check_positive_int(config.core.camera.width, "core.camera.width")
    check_positive_int(config.core.camera.height, "core.camera.height")
    if config.core.camera.format == "YUV" and (
        config.core.camera.width % 2 or config.core.camera.height % 4
    ):
        raise ConfigValueError(
            "core.camera YUV I420 width must be even and height divisible by 4"
        )
    if type(config.core.camera.quality) is not int or not 1 <= config.core.camera.quality <= 100:
        raise ConfigValueError("core.camera.quality must be an integer in 1..100")

    def check_model_path(driver, model_path, path):
        if driver != "mock":
            if model_path is None or not model_path.is_file():
                raise ConfigValueError(f"{path} is required for real driver and must name an existing file")


    ac = config.core.audio
    container_bytes = {"s16_le": 2, "s32_le": 4}
    for path, fmt, duration in (
        ("core.audio.input", ac.input.stream_format, ac.input.frame_duration_ms),
        ("core.audio.output", ac.output.stream_format, 1_000),
    ):
        check_positive_int(fmt.sample_rate, f"{path}.stream_format.sample_rate")
        check_positive_int(fmt.channels, f"{path}.stream_format.channels")
        check_positive_int(duration, f"{path}.frame_duration_ms")
        frame_bytes = (
            fmt.sample_rate * duration / 1000
            * fmt.channels * container_bytes[fmt.sample_format]
        )
        if not frame_bytes.is_integer():
            raise ConfigValueError(f"{path} frame bytes must be an exact integer")

    # Log rotate
    if config.log.rotate_max_bytes > 0 and config.log.rotate_backup_count <= 0:
        raise ConfigValueError("log.rotate_backup_count must be > 0 if rotate_max_bytes > 0")

    # Real drivers require valid paths
    check_model_path(config.perception.look.adapter.driver, config.perception.look.adapter.model_path, "perception.look.adapter.model_path")
    check_model_path(config.cognition.llm.driver, config.cognition.llm.model_path, "cognition.llm.model_path")
    check_engine_config(
        config.perception.listen.adapter.driver,
        config.perception.listen.adapter.engine_name,
        "perception.listen.adapter",
    )
    check_engine_config(
        config.action.tts.driver,
        config.action.tts.engine_name,
        "action.tts",
    )

    audio_real_fields = (
        ac.input.device, ac.input.native_format, ac.input.channel_index,
        ac.input.valid_bits, ac.input.valid_bits_alignment, ac.input.resampler,
        ac.output.device, ac.output.native_format,
    )
    if ac.driver in {"mock", "null"} and any(value is not None for value in audio_real_fields):
        raise ConfigValueError("core.audio mock/null cannot contain real-only fields")
    if ac.driver == "alsa":
        _validate_alsa_option_a(ac)
    if ac.driver not in {"mock", "null", "alsa"}:
        raise ConfigValueError(f"core.audio.driver is unsupported: {ac.driver}")

    display_real_fields = (
        display.native_library_path, display.native_library_sha256,
        display.native_abi_version, display.spi_device, display.spi_speed_hz,
        display.spi_mode, display.spi_chip_select, display.gpio_chip_index,
        display.dc_bcm, display.reset_bcm,
    )
    if display.driver in {"mock", "null"} and any(value is not None for value in display_real_fields):
        raise ConfigValueError("core.display mock/null cannot contain real-only fields")
    if display.driver == "ssd1351":
        _validate_ssd1351(display)
    elif display.driver not in {"mock", "null"}:
        raise ConfigValueError(f"core.display.driver is unsupported: {display.driver}")

    # Audio input / TTS format match
    if config.action.tts.driver not in {"mock", "null"}:
        # Candidate-specific adapters must declare their native PCM format later.
        fmt = ac.output.stream_format
        if fmt.sample_rate != 16000 or fmt.channels != 1 or fmt.sample_format != "s16_le":
            raise ConfigValueError("Audio input format must match TTS output format (16000Hz, 1ch, 16bit)")

    # GPIO pin uniqueness
    pins = set()
    for name, p in config.core.gpio.pins.items():
        if p.pin in pins:
            raise ConfigValueError(f"Duplicate physical GPIO pin: {p.pin}")
        pins.add(p.pin)

    button = config.input_sources.button
    button_pin = config.core.gpio.pins.get(button.conversation_pin)
    if button.short_press_min_ms <= 0:
        raise ConfigValueError("input_sources.button.short_press_min_ms must be positive")
    if button.long_press_min_ms <= button.short_press_min_ms:
        raise ConfigValueError("input_sources.button.long_press_min_ms must exceed short_press_min_ms")
    if button_pin is not None and button.short_press_min_ms < button_pin.debounce_ms:
        raise ConfigValueError("input_sources.button.short_press_min_ms must be >= GPIO debounce_ms")


def _validate_ssd1351(display) -> None:
    import hashlib
    import re

    required = {
        "native_library_path": display.native_library_path,
        "native_library_sha256": display.native_library_sha256,
        "native_abi_version": display.native_abi_version,
        "spi_device": display.spi_device,
        "spi_speed_hz": display.spi_speed_hz,
        "spi_mode": display.spi_mode,
        "spi_chip_select": display.spi_chip_select,
        "gpio_chip_index": display.gpio_chip_index,
        "dc_bcm": display.dc_bcm,
        "reset_bcm": display.reset_bcm,
    }
    for field, value in required.items():
        if value is None:
            raise ConfigValueError(f"core.display.{field} is required for ssd1351")
    library = display.native_library_path
    if not library.is_file():
        raise ConfigValueError("core.display.native_library_path must name a regular file")
    digest = display.native_library_sha256
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ConfigValueError("core.display.native_library_sha256 must be 64 lowercase hex characters")
    if hashlib.sha256(library.read_bytes()).hexdigest() != digest:
        raise ConfigValueError("core.display.native_library_sha256 does not match artifact")
    exact = {
        "native_abi_version": 1,
        "spi_device": "/dev/spidev0.0",
        "spi_speed_hz": 4_000_000,
        "spi_mode": 0,
        "spi_chip_select": 0,
        "dc_bcm": 24,
        "reset_bcm": 25,
    }
    for field, expected in exact.items():
        if getattr(display, field) != expected:
            raise ConfigValueError(f"core.display.{field} must be {expected!r}")
    if (
        type(display.gpio_chip_index) is not int
        or not 0 <= display.gpio_chip_index <= 2_147_483_647
    ):
        raise ConfigValueError(
            "core.display.gpio_chip_index must be an integer in 0..2147483647"
        )
    if display.dc_bcm == display.reset_bcm or {display.dc_bcm, display.reset_bcm} & {8, 10, 11}:
        raise ConfigValueError("core.display DC/reset pins conflict with selected SPI fixture")


def _validate_alsa_option_a(audio) -> None:
    """Validate the P4-selected M3 Option A mapping before any ALSA import."""
    input_config, output_config = audio.input, audio.output
    required = {
        "input.device": input_config.device,
        "input.native_format": input_config.native_format,
        "input.channel_index": input_config.channel_index,
        "input.valid_bits": input_config.valid_bits,
        "input.valid_bits_alignment": input_config.valid_bits_alignment,
        "input.resampler": input_config.resampler,
        "output.device": output_config.device,
        "output.native_format": output_config.native_format,
    }
    for field, value in required.items():
        if value is None:
            raise ConfigValueError(f"core.audio.{field} is required for alsa")
    for path, device in (("input", input_config.device), ("output", output_config.device)):
        if not device.startswith("hw:") or device.startswith("plughw:"):
            raise ConfigValueError(f"core.audio.{path}.device must be a direct hw: device")

    native = (48_000, 2, "s32_le")
    stream = (16_000, 1, "s16_le")

    def fields(fmt):
        return (fmt.sample_rate, fmt.channels, fmt.sample_format)

    if fields(input_config.native_format) != native:
        raise ConfigValueError("core.audio.input.native_format must be 48000/2/s32_le")
    if fields(input_config.stream_format) != stream:
        raise ConfigValueError("core.audio.input.stream_format must be 16000/1/s16_le")
    if input_config.frame_duration_ms != 20:
        raise ConfigValueError("core.audio.input.frame_duration_ms must be 20")
    if input_config.channel_index not in {0, 1}:
        raise ConfigValueError("core.audio.input.channel_index must be 0 or 1")
    if input_config.valid_bits != 24:
        raise ConfigValueError("core.audio.input.valid_bits must be 24")
    if input_config.valid_bits_alignment != "msb":
        raise ConfigValueError("core.audio.input.valid_bits_alignment must be msb")
    if input_config.resampler != "samplerate.sinc_best":
        raise ConfigValueError("core.audio.input.resampler must be samplerate.sinc_best")
    if fields(output_config.native_format) != native:
        raise ConfigValueError(
            "core.audio.output.native_format must be 48000/2/s32_le"
        )
    if fields(output_config.stream_format) not in {native, stream}:
        raise ConfigValueError(
            "core.audio.output.stream_format must be 48000/2/s32_le or 16000/1/s16_le"
        )
