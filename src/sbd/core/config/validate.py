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

    check_positive_int(config.core.display.width, "core.display.width")
    check_positive_int(config.core.display.height, "core.display.height")
    if config.core.display.pixel_format == "mono1" and config.core.display.width % 8:
        raise ConfigValueError("core.display.width must be divisible by 8 for mono1")
    check_positive_int(config.core.camera.width, "core.camera.width")
    check_positive_int(config.core.camera.height, "core.camera.height")
    if type(config.core.camera.quality) is not int or not 1 <= config.core.camera.quality <= 100:
        raise ConfigValueError("core.camera.quality must be an integer in 1..100")

    def check_model_path(driver, model_path, path):
        if driver != "mock":
            if model_path is None or not model_path.is_file():
                raise ConfigValueError(f"{path} is required for real driver and must name an existing file")


    ac = config.core.audio
    bytes_per_frame = ac.sample_rate * ac.frame_duration_ms / 1000 * ac.channels * (ac.bit_depth / 8)
    if not bytes_per_frame.is_integer():
        raise ConfigValueError(f"Audio frame bytes must be an exact integer, got {bytes_per_frame}")

    # Log rotate
    if config.log.rotate_max_bytes > 0 and config.log.rotate_backup_count <= 0:
        raise ConfigValueError("log.rotate_backup_count must be > 0 if rotate_max_bytes > 0")

    # Real drivers require valid paths
    check_model_path(config.perception.listen.adapter.driver, config.perception.listen.adapter.model_path, "perception.listen.adapter.model_path")
    check_model_path(config.perception.look.adapter.driver, config.perception.look.adapter.model_path, "perception.look.adapter.model_path")
    check_model_path(config.cognition.llm.driver, config.cognition.llm.model_path, "cognition.llm.model_path")
    check_model_path(config.action.tts.driver, config.action.tts.model_path, "action.tts.model_path")

    if config.core.audio.driver != "mock":
        if not config.core.audio.input_device:
            raise ConfigValueError("core.audio.input_device required for real driver")
        if not config.core.audio.output_device:
            raise ConfigValueError("core.audio.output_device required for real driver")

    if config.core.display.driver != "mock" and not config.core.display.spi_device:
        raise ConfigValueError("core.display.spi_device required for real driver")

    # Audio input / TTS format match
    if config.action.tts.driver != "mock":
        # for piper mock maybe we don't care, but for real we check if TTS rate matches Audio out rate
        if ac.sample_rate != 16000 or ac.channels != 1 or ac.bit_depth != 16:
            raise ConfigValueError("Audio input format must match TTS output format (16000Hz, 1ch, 16bit)")

    # GPIO pin uniqueness
    pins = set()
    for name, p in config.core.gpio.pins.items():
        if p.pin in pins:
            raise ConfigValueError(f"Duplicate physical GPIO pin: {p.pin}")
        pins.add(p.pin)
