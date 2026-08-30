"""PM-025 hardware diagnostic regressions with injected HAL owners."""

from __future__ import annotations

import asyncio
import math
import struct
from pathlib import Path
from types import SimpleNamespace

from scripts import hw_diag, run_button


def _format(sample_rate: int = 16_000):
    return SimpleNamespace(sample_rate=sample_rate, channels=1, sample_format="s16_le")


def _core_config(*, camera_payload_format: str = "RGB"):
    stream = _format()
    return SimpleNamespace(
        audio=SimpleNamespace(
            driver="alsa",
            input=SimpleNamespace(stream_format=stream, frame_duration_ms=20),
            output=SimpleNamespace(stream_format=stream),
        ),
        display=SimpleNamespace(
            driver="ssd1351", width=128, height=128, frame_buffer_bytes=32768,
        ),
        camera=SimpleNamespace(
            driver="picamera2", format=camera_payload_format, width=4, height=2,
        ),
        gpio=SimpleNamespace(
            driver="gpiod",
            pins={
                "conversation": SimpleNamespace(pin=23, active_low=True, debounce_ms=50),
            },
        ),
    )


def _s16_frames(seconds: float, *, tone_hz: float | None = None) -> list[bytes]:
    frame_count = math.ceil(seconds * 1000 / 20)
    values = []
    for index in range(frame_count * 320):
        values.append(
            0 if tone_hz is None
            else round(4_000 * math.sin(2 * math.pi * tone_hz * index / 16_000))
        )
    payload = struct.pack(f"<{len(values)}h", *values)
    return [payload[index:index + 640] for index in range(0, len(payload), 640)]


class _AudioStream:
    def __init__(self, frames: list[bytes]) -> None:
        self._frames = iter(frames)
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._frames)
        except StopIteration:
            raise StopAsyncIteration

    async def aclose(self) -> None:
        self.closed = True


class _AudioInput:
    def __init__(self, captures: list[list[bytes]]) -> None:
        self.captures = captures
        self.started = False
        self.stopped = False
        self.streams: list[_AudioStream] = []

    async def start(self) -> None:
        self.started = True

    def frames(self):
        stream = _AudioStream(self.captures.pop(0))
        self.streams.append(stream)
        return stream

    async def stop(self) -> None:
        self.stopped = True


class _AudioOutput:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.played_bytes = 0

    async def start(self) -> None:
        self.started = True

    async def play(self, chunks) -> None:
        async for chunk in chunks:
            self.played_bytes += len(chunk)

    async def stop(self) -> None:
        self.stopped = True


def _factories(**overrides):
    defaults = {
        "audio_input": lambda _config: None,
        "audio_output": lambda _config: None,
        "display": lambda _config: None,
        "camera": lambda _config: None,
        "gpio": lambda _config: None,
        "renderer": lambda: None,
    }
    defaults.update(overrides)
    return hw_diag.HardwareFactories(**defaults)


def test_pm_025_audio_requires_measured_acoustic_tone_and_cleans_up(tmp_path: Path) -> None:
    assert hw_diag.DiagnosticOptions().tone_seconds == 0.5
    options = hw_diag.DiagnosticOptions(
        baseline_seconds=0.04,
        tone_seconds=0.04,
        tone_settle_seconds=0.02,
        minimum_tone_amplitude=100,
        minimum_tone_gain_ratio=3,
    )
    input_owner = _AudioInput([
        _s16_frames(options.baseline_seconds),
        _s16_frames(options.tone_seconds + options.tone_settle_seconds * 2, tone_hz=440),
    ])
    output_owner = _AudioOutput()
    factories = _factories(
        audio_input=lambda _config: input_owner,
        audio_output=lambda _config: output_owner,
    )

    result = asyncio.run(hw_diag.check_audio(_core_config(), factories, tmp_path, options))

    assert result.status == "PASS"
    assert result.metrics["tone_seconds"] == options.tone_seconds
    assert result.metrics["tone_gain_ratio"] >= 3
    assert output_owner.played_bytes > 0
    assert input_owner.stopped and output_owner.stopped
    assert all(stream.closed for stream in input_owner.streams)
    assert {path.name for path in tmp_path.iterdir()} == {
        "audio-baseline.wav", "audio-tone-capture.wav",
    }


def test_pm_025_audio_silence_is_fail_not_speaker_pass(tmp_path: Path) -> None:
    options = hw_diag.DiagnosticOptions(
        baseline_seconds=0.02, tone_seconds=0.02, tone_settle_seconds=0.01,
    )
    input_owner = _AudioInput([
        _s16_frames(options.baseline_seconds),
        _s16_frames(options.tone_seconds + options.tone_settle_seconds * 2),
    ])
    output_owner = _AudioOutput()
    result = asyncio.run(hw_diag.check_audio(
        _core_config(),
        _factories(
            audio_input=lambda _config: input_owner,
            audio_output=lambda _config: output_owner,
        ),
        tmp_path, options,
    ))

    assert result.status == "FAIL"
    assert "not distinguishable" in result.detail
    assert input_owner.stopped and output_owner.stopped


class _Camera:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.stopped = False

    async def start(self) -> None: pass
    async def capture(self) -> bytes: return self.payload
    async def stop(self) -> None: self.stopped = True


def test_pm_025_camera_rejects_uniform_payload_and_stops(tmp_path: Path) -> None:
    camera = _Camera(bytes(4 * 2 * 3))
    result = asyncio.run(hw_diag.check_camera(
        _core_config(), _factories(camera=lambda _config: camera), tmp_path,
        hw_diag.DiagnosticOptions(camera_minimum_luma_range=8),
    ))

    assert result.status == "FAIL"
    assert result.metrics["sampled_luma_range"] == 0
    assert camera.stopped
    assert (tmp_path / "camera-capture.rgb").is_file()


def test_pm_025_camera_cancellation_propagates_after_cleanup(tmp_path: Path) -> None:
    class BlockingCamera(_Camera):
        async def capture(self) -> bytes:
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

    async def run() -> None:
        camera = BlockingCamera(b"")
        task = asyncio.create_task(hw_diag.check_camera(
            _core_config(), _factories(camera=lambda _config: camera), tmp_path,
            hw_diag.DiagnosticOptions(),
        ))
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("cancellation must propagate")
        assert camera.stopped

    asyncio.run(run())


class _GPIO:
    def __init__(self) -> None:
        self.callback = None
        self.registered_inputs: list[tuple[int, str, int]] = []
        self.unregistered: list[int] = []
        self.stopped = False

    async def start(self) -> None: pass

    async def register_input(self, pin, edge, callback, debounce_ms=0) -> None:
        self.callback = callback
        self.registered_inputs.append((pin, edge, debounce_ms))

    async def configure_output(self, _pin, initial=False) -> None:
        assert initial is False

    async def set_output(self, _pin, _value: bool) -> None: pass

    async def unregister(self, pin: int) -> None:
        self.unregistered.append(pin)

    async def stop(self) -> None:
        self.stopped = True


def test_pm_025_gpio_checks_configured_input_line_without_stimulus() -> None:
    core = _core_config()
    missing_core = _core_config()
    missing_core.gpio.pins.clear()
    missing = asyncio.run(hw_diag.check_gpio(
        missing_core, _factories(), hw_diag.DiagnosticOptions(),
    ))
    assert missing.status == "FAIL"
    assert "conversation is required" in missing.detail

    owner = _GPIO()
    passed = asyncio.run(hw_diag.check_gpio(
        core, _factories(gpio=lambda _config: owner), hw_diag.DiagnosticOptions(),
    ))
    assert passed.status == "PASS"
    assert owner.registered_inputs == [(23, "both", 50)]
    assert owner.unregistered == [23]
    assert owner.stopped
    assert any("physical pin voltage" in item for item in passed.limitations)


def test_pm_025_gpio_line_request_failure_is_not_pass_and_stops() -> None:
    class FailingGPIO(_GPIO):
        async def register_input(self, pin, edge, callback, debounce_ms=0) -> None:
            raise OSError("line busy")

    owner = FailingGPIO()
    result = asyncio.run(hw_diag.check_gpio(
        _core_config(), _factories(gpio=lambda _config: owner),
        hw_diag.DiagnosticOptions(),
    ))
    assert result.status == "FAIL"
    assert "line busy" in result.detail
    assert owner.unregistered == []
    assert owner.stopped


class _Display:
    def __init__(self) -> None:
        self.stopped = False

    async def start(self) -> None: pass
    def clear(self) -> None: pass
    def write_pixels(self, _pixels: bytes) -> None: raise RuntimeError("SPI failed")
    def show(self) -> None: pass
    async def stop(self) -> None: self.stopped = True


class _Renderer:
    def render(self, **_kwargs) -> bytes:
        return bytes(32768)


def test_pm_025_display_failure_is_not_pass_and_cleanup_runs() -> None:
    owner = _Display()
    result = asyncio.run(hw_diag.check_display(
        _core_config(),
        _factories(display=lambda _config: owner, renderer=_Renderer),
        hw_diag.DiagnosticOptions(),
    ))
    assert result.status == "FAIL"
    assert owner.stopped
    assert any("visual pixels remain unverified" in item for item in result.limitations)


def test_pm_025_manual_button_is_separate_and_bounded() -> None:
    class ButtonGPIO(_GPIO):
        async def register_input(self, pin, edge, callback, debounce_ms=0) -> None:
            assert (pin, edge, debounce_ms) == (23, "falling", 50)
            await super().register_input(pin, edge, callback, debounce_ms)
            await callback(SimpleNamespace(edge="falling"))

    owner = ButtonGPIO()
    config = SimpleNamespace(core=_core_config())
    asyncio.run(run_button.wait_for_button(
        config, timeout_seconds=0.1, gpio_factory=lambda _config: owner,
    ))
    assert owner.unregistered == [23]
    assert owner.stopped
