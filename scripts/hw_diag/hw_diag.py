#!/usr/bin/env python3
"""Zero-interaction Raspberry Pi hardware diagnostics.

The tool talks directly to Core HAL implementations.  It is a maintenance
diagnostic, not a milestone acceptance runner and never writes formal evidence.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import struct
import sys
import wave
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Literal


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sbd.core.config import load_config  # noqa: E402


Status = Literal["PASS", "FAIL"]
DEFAULT_TONE_HZ = 440.0


class DiagnosticError(RuntimeError):
    """A diagnostic precondition or measurable assertion failed."""


@dataclass(frozen=True, slots=True)
class DiagnosticOptions:
    operation_timeout_seconds: float = 10.0
    cleanup_timeout_seconds: float = 5.0
    baseline_seconds: float = 0.5
    tone_seconds: float = 0.5
    tone_settle_seconds: float = 0.2
    tone_hz: float = DEFAULT_TONE_HZ
    minimum_tone_amplitude: float = 100.0
    minimum_tone_gain_ratio: float = 3.0
    camera_minimum_luma_range: int = 8


@dataclass(frozen=True, slots=True)
class DiagnosticResult:
    component: str
    status: Status
    scope: str
    detail: str
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HardwareFactories:
    audio_input: Callable[[Any], Any]
    audio_output: Callable[[Any], Any]
    display: Callable[[Any], Any]
    camera: Callable[[Any], Any]
    gpio: Callable[[Any], Any]
    renderer: Callable[[], Any]


def production_factories() -> HardwareFactories:
    """Import Pi/native owners only when the command actually runs."""
    from sbd.core.audio.alsa.input import AlsaAudioInput
    from sbd.core.audio.alsa.output import AlsaAudioOutput
    from sbd.core.camera.picamera2.driver import PiCamera
    from sbd.core.display.renderer import Oled128Renderer
    from sbd.core.display.ssd1351.driver import DisplayDriver
    from sbd.core.gpio.gpiod.driver import GpiodGPIO

    return HardwareFactories(
        audio_input=AlsaAudioInput,
        audio_output=AlsaAudioOutput,
        display=DisplayDriver,
        camera=PiCamera,
        gpio=GpiodGPIO,
        renderer=Oled128Renderer,
    )


def _require_timeout(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0 or parsed > 300:
        raise argparse.ArgumentTypeError("timeout must be finite and in (0, 300]")
    return parsed


async def _bounded(awaitable, seconds: float, operation: str):
    try:
        return await asyncio.wait_for(awaitable, timeout=seconds)
    except TimeoutError as exc:
        raise DiagnosticError(f"{operation} timed out") from exc


async def _stop_devices(
    devices: list[tuple[str, Any]], timeout_seconds: float
) -> tuple[str, ...]:
    failures: list[str] = []
    for label, device in reversed(devices):
        try:
            await _bounded(device.stop(), timeout_seconds, f"{label} stop")
        except BaseException as exc:  # cleanup must report cancellation too
            failures.append(f"{label} cleanup failed: {type(exc).__name__}")
    return tuple(failures)


def _decode_s16(payload: bytes) -> tuple[int, ...]:
    if len(payload) % 2:
        raise DiagnosticError("captured S16_LE payload is not frame-aligned")
    if not payload:
        raise DiagnosticError("captured audio payload is empty")
    return struct.unpack(f"<{len(payload) // 2}h", payload)


def _rms(samples: tuple[int, ...]) -> float:
    return math.sqrt(sum(sample * sample for sample in samples) / len(samples))


def _frequency_amplitude(
    samples: tuple[int, ...], sample_rate: int, frequency_hz: float
) -> float:
    """Return the single-bin sinusoid amplitude for a bounded diagnostic clip."""
    if sample_rate <= 0 or not 0 < frequency_hz < sample_rate / 2:
        raise DiagnosticError("tone frequency is outside the capture Nyquist range")
    count = len(samples)
    real = sum(
        sample * math.cos(2 * math.pi * frequency_hz * index / sample_rate)
        for index, sample in enumerate(samples)
    )
    imaginary = sum(
        sample * math.sin(2 * math.pi * frequency_hz * index / sample_rate)
        for index, sample in enumerate(samples)
    )
    return 2.0 * math.hypot(real, imaginary) / count


def _write_wav(path: Path, payload: bytes, audio_format: Any) -> None:
    sample_width = {"s16_le": 2, "s32_le": 4}.get(audio_format.sample_format)
    if sample_width is None:
        raise DiagnosticError("unsupported WAV sample format")
    with path.open("xb") as raw:
        with wave.open(raw, "wb") as output:
            output.setnchannels(audio_format.channels)
            output.setsampwidth(sample_width)
            output.setframerate(audio_format.sample_rate)
            output.writeframes(payload)


async def _capture_audio(
    owner: Any, audio_format: Any, frame_duration_ms: int, seconds: float,
    timeout_seconds: float,
) -> bytes:
    if audio_format.sample_format != "s16_le" or audio_format.channels != 1:
        raise DiagnosticError("acoustic loopback requires mono S16_LE capture")
    expected_bytes = (
        audio_format.sample_rate * audio_format.channels * 2 * frame_duration_ms // 1000
    )
    frame_count = max(1, math.ceil(seconds * 1000 / frame_duration_ms))
    stream = owner.frames()
    frames: list[bytes] = []

    async def collect() -> None:
        for _ in range(frame_count):
            frame = await anext(stream)
            if type(frame) is not bytes or len(frame) != expected_bytes:
                raise DiagnosticError("audio capture produced an invalid frame")
            frames.append(frame)

    try:
        await _bounded(collect(), seconds + timeout_seconds, "audio capture")
    finally:
        close = getattr(stream, "aclose", None)
        if callable(close):
            await _bounded(close(), timeout_seconds, "audio stream close")
    return b"".join(frames)


async def _tone_stream(audio_format: Any, seconds: float, frequency_hz: float):
    rate = audio_format.sample_rate
    channels = audio_format.channels
    sample_format = audio_format.sample_format
    if sample_format not in {"s16_le", "s32_le"} or channels not in {1, 2}:
        raise DiagnosticError("unsupported playback stream format")
    total_frames = max(1, round(rate * seconds))
    chunk_frames = max(1, rate // 50)
    peak = 8_000 if sample_format == "s16_le" else 500_000_000
    code = "h" if sample_format == "s16_le" else "i"
    for start in range(0, total_frames, chunk_frames):
        values: list[int] = []
        for frame_index in range(start, min(start + chunk_frames, total_frames)):
            sample = round(peak * math.sin(2 * math.pi * frequency_hz * frame_index / rate))
            values.extend([sample] * channels)
        yield struct.pack(f"<{len(values)}{code}", *values)


async def check_audio(
    core: Any, factories: HardwareFactories, output_dir: Path, options: DiagnosticOptions
) -> DiagnosticResult:
    scope = "ALSA microphone + speaker acoustic loopback"
    if core.audio.driver != "alsa":
        return DiagnosticResult("Audio", "FAIL", scope, "core.audio.driver must be alsa")
    capture_format = core.audio.input.stream_format
    baseline_path = output_dir / "audio-baseline.wav"
    tone_path = output_dir / "audio-tone-capture.wav"
    started: list[tuple[str, Any]] = []
    input_owner = factories.audio_input(core.audio)
    output_owner = factories.audio_output(core.audio)
    error: BaseException | None = None
    result: DiagnosticResult | None = None
    try:
        await _bounded(input_owner.start(), options.operation_timeout_seconds, "audio input start")
        started.append(("audio input", input_owner))
        await _bounded(output_owner.start(), options.operation_timeout_seconds, "audio output start")
        started.append(("audio output", output_owner))

        baseline = await _capture_audio(
            input_owner, capture_format, core.audio.input.frame_duration_ms,
            options.baseline_seconds, options.operation_timeout_seconds,
        )
        tone_capture_seconds = options.tone_seconds + options.tone_settle_seconds * 2
        capture_task = asyncio.create_task(_capture_audio(
            input_owner, capture_format, core.audio.input.frame_duration_ms,
            tone_capture_seconds, options.operation_timeout_seconds,
        ))
        try:
            await asyncio.sleep(options.tone_settle_seconds)
            await _bounded(
                output_owner.play(_tone_stream(
                    core.audio.output.stream_format, options.tone_seconds, options.tone_hz,
                )),
                options.tone_seconds + options.operation_timeout_seconds,
                "audio tone playback",
            )
            tone_capture = await capture_task
        except BaseException:
            capture_task.cancel()
            await asyncio.gather(capture_task, return_exceptions=True)
            raise

        baseline_samples = _decode_s16(baseline)
        tone_samples = _decode_s16(tone_capture)
        baseline_amplitude = _frequency_amplitude(
            baseline_samples, capture_format.sample_rate, options.tone_hz
        )
        tone_amplitude = _frequency_amplitude(
            tone_samples, capture_format.sample_rate, options.tone_hz
        )
        gain_ratio = tone_amplitude / max(1.0, baseline_amplitude)
        _write_wav(baseline_path, baseline, capture_format)
        _write_wav(tone_path, tone_capture, capture_format)
        metrics = {
            "tone_hz": options.tone_hz,
            "tone_seconds": options.tone_seconds,
            "baseline_rms": round(_rms(baseline_samples), 3),
            "tone_capture_rms": round(_rms(tone_samples), 3),
            "baseline_tone_amplitude": round(baseline_amplitude, 3),
            "tone_amplitude": round(tone_amplitude, 3),
            "tone_gain_ratio": round(gain_ratio, 3),
        }
        passed = (
            tone_amplitude >= options.minimum_tone_amplitude
            and gain_ratio >= options.minimum_tone_gain_ratio
        )
        result = DiagnosticResult(
            "Audio", "PASS" if passed else "FAIL", scope,
            "known tone detected by product microphone" if passed
            else "played tone was not distinguishable from baseline",
            metrics=metrics,
            artifacts=(str(baseline_path), str(tone_path)),
        )
    except BaseException as exc:
        error = exc
    cleanup = await _stop_devices(started, options.cleanup_timeout_seconds)
    if isinstance(error, asyncio.CancelledError):
        raise error
    if cleanup:
        return DiagnosticResult(
            "Audio", "FAIL", scope, "; ".join(cleanup),
            limitations=("cleanup proof failed",),
        )
    if error is not None:
        return DiagnosticResult("Audio", "FAIL", scope, f"{type(error).__name__}: {error}")
    assert result is not None
    return result


async def check_display(
    core: Any, factories: HardwareFactories, options: DiagnosticOptions
) -> DiagnosticResult:
    scope = "SSD1351 artifact authentication, ABI open and SPI present transaction"
    limitation = "SSD1351 has no panel readback; visual pixels remain unverified"
    if core.display.driver != "ssd1351":
        return DiagnosticResult("Display", "FAIL", scope, "core.display.driver must be ssd1351")
    from sbd.core.display.hints import DisplayHint
    from sbd.core.display.renderer import RenderModel

    owner = factories.display(core.display)
    started: list[tuple[str, Any]] = []
    error: BaseException | None = None
    try:
        await _bounded(owner.start(), options.operation_timeout_seconds, "display start")
        started.append(("display", owner))
        renderer = factories.renderer()
        pixels = renderer.render(
            size=(core.display.width, core.display.height),
            model=RenderModel(
                status_slots=(("state", DisplayHint("status.state", {"state": "IDLE"})),),
                main=DisplayHint("main.text", {"text": "HW DIAG"}),
                fullscreen=None,
            ),
        )
        owner.clear()
        owner.write_pixels(pixels)
        owner.show()
        owner.clear()
        owner.show()
    except BaseException as exc:
        error = exc
    cleanup = await _stop_devices(started, options.cleanup_timeout_seconds)
    if isinstance(error, asyncio.CancelledError):
        raise error
    if cleanup:
        return DiagnosticResult("Display", "FAIL", scope, "; ".join(cleanup), limitations=(limitation,))
    if error is not None:
        return DiagnosticResult(
            "Display", "FAIL", scope, f"{type(error).__name__}: {error}", limitations=(limitation,)
        )
    return DiagnosticResult(
        "Display", "PASS", scope, "two complete present transactions succeeded",
        metrics={"frame_buffer_bytes": core.display.frame_buffer_bytes, "present_count": 2},
        limitations=(limitation,),
    )


def _camera_signal(payload: bytes, config: Any) -> tuple[list[int], str]:
    width, height = config.width, config.height
    if config.format == "JPEG":
        from PIL import Image

        try:
            with Image.open(BytesIO(payload)) as image:
                image.load()
                if image.size != (width, height):
                    raise DiagnosticError("JPEG dimensions do not match config")
                values = list(image.convert("L").getdata())
        except DiagnosticError:
            raise
        except Exception as exc:
            raise DiagnosticError("camera JPEG is invalid") from exc
        return values, ".jpg"
    expected = width * height * (3 if config.format == "RGB" else 3 / 2)
    if len(payload) != int(expected):
        raise DiagnosticError("camera raw payload size does not match config")
    if config.format == "RGB":
        return [payload[index] for index in range(0, len(payload), 3)], ".rgb"
    return list(payload[:width * height]), ".yuv"


async def check_camera(
    core: Any, factories: HardwareFactories, output_dir: Path, options: DiagnosticOptions
) -> DiagnosticResult:
    scope = "Picamera2 capture format, dimensions and non-uniform luma signal"
    if core.camera.driver != "picamera2":
        return DiagnosticResult("Camera", "FAIL", scope, "core.camera.driver must be picamera2")
    owner = factories.camera(core.camera)
    started: list[tuple[str, Any]] = []
    error: BaseException | None = None
    result: DiagnosticResult | None = None
    try:
        await _bounded(owner.start(), options.operation_timeout_seconds, "camera start")
        started.append(("camera", owner))
        payload = await _bounded(owner.capture(), options.operation_timeout_seconds, "camera capture")
        values, extension = _camera_signal(payload, core.camera)
        sample_step = max(1, len(values) // 20_000)
        sampled = values[::sample_step]
        luma_range = max(sampled) - min(sampled)
        artifact = output_dir / f"camera-capture{extension}"
        with artifact.open("xb") as target:
            target.write(payload)
        passed = luma_range >= options.camera_minimum_luma_range
        result = DiagnosticResult(
            "Camera", "PASS" if passed else "FAIL", scope,
            "capture has measurable scene variation" if passed else "capture is effectively uniform",
            metrics={
                "format": core.camera.format,
                "payload_bytes": len(payload),
                "sampled_luma_range": luma_range,
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
            artifacts=(str(artifact),),
        )
    except BaseException as exc:
        error = exc
    cleanup = await _stop_devices(started, options.cleanup_timeout_seconds)
    if isinstance(error, asyncio.CancelledError):
        raise error
    if cleanup:
        return DiagnosticResult("Camera", "FAIL", scope, "; ".join(cleanup))
    if error is not None:
        return DiagnosticResult("Camera", "FAIL", scope, f"{type(error).__name__}: {error}")
    assert result is not None
    return result


async def check_gpio(
    core: Any, factories: HardwareFactories, options: DiagnosticOptions,
) -> DiagnosticResult:
    scope = "gpiod chip access and configured conversation input-line transaction"
    limitation = "no electrical stimulus; physical pin voltage and button circuit remain unverified"
    if core.gpio.driver != "gpiod":
        return DiagnosticResult("GPIO", "FAIL", scope, "core.gpio.driver must be gpiod")
    pin_config = core.gpio.pins.get("conversation")
    if pin_config is None:
        return DiagnosticResult(
            "GPIO", "FAIL", scope, "core.gpio.pins.conversation is required",
            limitations=(limitation,),
        )

    owner = factories.gpio(core.gpio)
    started: list[tuple[str, Any]] = []
    registered = False
    error: BaseException | None = None

    async def callback(_event: Any) -> None:
        return None

    try:
        await _bounded(owner.start(), options.operation_timeout_seconds, "GPIO start")
        started.append(("GPIO", owner))
        await _bounded(
            owner.register_input(
                pin_config.pin, "both", callback, debounce_ms=pin_config.debounce_ms
            ),
            options.operation_timeout_seconds, "GPIO input register",
        )
        registered = True
    except BaseException as exc:
        error = exc

    unregister_failures: list[str] = []
    if registered:
        try:
            await _bounded(
                owner.unregister(pin_config.pin),
                options.cleanup_timeout_seconds,
                "GPIO unregister",
            )
        except BaseException as exc:
            unregister_failures.append(f"pin {pin_config.pin}: {type(exc).__name__}")
    cleanup = await _stop_devices(started, options.cleanup_timeout_seconds)
    if isinstance(error, asyncio.CancelledError):
        raise error
    if unregister_failures or cleanup:
        return DiagnosticResult(
            "GPIO", "FAIL", scope,
            "; ".join((*unregister_failures, *cleanup)),
            limitations=(limitation, "cleanup proof failed"),
        )
    if error is not None:
        return DiagnosticResult(
            "GPIO", "FAIL", scope, f"{type(error).__name__}: {error}",
            limitations=(limitation,),
        )
    return DiagnosticResult(
        "GPIO", "PASS", scope, "conversation input line requested and released",
        metrics={"input_bcm": pin_config.pin, "debounce_ms": pin_config.debounce_ms},
        limitations=(limitation,),
    )


def _result_json(result: DiagnosticResult) -> dict[str, Any]:
    value = asdict(result)
    value["artifacts"] = list(result.artifacts)
    value["limitations"] = list(result.limitations)
    return value


async def run_diagnostics(
    config: Any, components: tuple[str, ...], factories: HardwareFactories,
    output_dir: Path, options: DiagnosticOptions,
) -> tuple[DiagnosticResult, ...]:
    results: list[DiagnosticResult] = []
    for component in components:
        if component == "audio":
            result = await check_audio(config.core, factories, output_dir, options)
        elif component == "display":
            result = await check_display(config.core, factories, options)
        elif component == "camera":
            result = await check_camera(config.core, factories, output_dir, options)
        elif component == "gpio":
            result = await check_gpio(config.core, factories, options)
        else:  # parser and direct callers both fail closed
            raise DiagnosticError(f"unknown component: {component}")
        results.append(result)
        print(f"{result.component}: {result.status} — {result.detail}")
    return tuple(results)


def _output_directory(raw: Path | None) -> Path:
    if raw is None:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        raw = Path("/tmp") / f"snowboard-hw-diag-{timestamp}-{os.getpid()}"
    path = raw.expanduser().resolve()
    if path.exists() and any(path.iterdir()):
        raise DiagnosticError("output directory must be absent or empty")
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--component", action="append", choices=("audio", "display", "camera", "gpio"),
        dest="components", help="repeat to select checks; default is all",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--operation-timeout-seconds", type=_require_timeout, default=10.0)
    parser.add_argument("--cleanup-timeout-seconds", type=_require_timeout, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.config.is_file() or args.config.is_symlink():
        print("ERROR: --config must be a readable non-symlink file", file=sys.stderr)
        return 2
    try:
        output_dir = _output_directory(args.output_dir)
        config = load_config(
            local_path=args.config.resolve(), dotenv_path=Path(os.devnull), environ={}
        )
        options = DiagnosticOptions(
            operation_timeout_seconds=args.operation_timeout_seconds,
            cleanup_timeout_seconds=args.cleanup_timeout_seconds,
        )
        components = tuple(args.components or ("audio", "display", "camera", "gpio"))
        if len(components) != len(set(components)):
            raise DiagnosticError("each --component may be selected only once")
        results = asyncio.run(run_diagnostics(
            config, components, production_factories(), output_dir, options,
        ))
        summary = {
            "schema": "snowboard.hw-diag/1",
            "created_at_utc": datetime.now(UTC).isoformat(),
            "status": "PASS" if all(item.status == "PASS" for item in results) else "FAIL",
            "formal_acceptance": False,
            "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
            "results": [_result_json(item) for item in results],
        }
        summary_path = output_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Summary: {summary_path}")
        return 0 if summary["status"] == "PASS" else 1
    except (DiagnosticError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
