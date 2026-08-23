"""Bounded M3 capture/playback helpers over the packet-pinned Core Audio HAL."""

from __future__ import annotations

import asyncio
import importlib
import os
import subprocess
import sys
import wave
from collections.abc import AsyncIterator, Iterable
from pathlib import Path
from typing import Any

from .m3_packet import CORE_HAL_EXECUTION_SHA


STREAM_RATE = 16_000
STREAM_CHANNELS = 1
STREAM_SAMPLE_WIDTH = 2
STREAM_FRAME_BYTES = STREAM_CHANNELS * STREAM_SAMPLE_WIDTH
HAL_FRAME_SAMPLES = 320
HAL_FRAME_BYTES = HAL_FRAME_SAMPLES * STREAM_FRAME_BYTES


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def verify_core_checkout(core_root: Path) -> dict[str, str]:
    """Fail closed unless this is the clean packet-pinned Core checkout."""

    resolved = core_root.resolve()
    observed = _git(resolved, "rev-parse", "HEAD")
    if observed != CORE_HAL_EXECUTION_SHA:
        raise ValueError(
            f"Core checkout SHA mismatch: expected={CORE_HAL_EXECUTION_SHA} observed={observed}"
        )
    if _git(resolved, "status", "--porcelain"):
        raise ValueError("M3 Core HAL checkout must be clean")
    required = (
        "src/sbd/core/audio/__init__.py",
        "src/sbd/core/audio/alsa/input.py",
        "src/sbd/core/audio/alsa/output.py",
        "src/sbd/core/audio/alsa/adaptation.py",
        "src/sbd/core/config/models.py",
    )
    missing = [relative for relative in required if not (resolved / relative).is_file()]
    if missing:
        raise ValueError(f"Core checkout is missing M3 HAL files: {', '.join(missing)}")
    return {"core_root": str(resolved), "core_execution_sha": observed}


def load_core_audio(core_root: Path) -> tuple[Any, Any]:
    """Import factories/models from the verified external Core checkout."""

    identity = verify_core_checkout(core_root)
    source_root = str(Path(identity["core_root"]) / "src")
    if source_root not in sys.path:
        sys.path.insert(0, source_root)
    audio = importlib.import_module("sbd.core.audio")
    models = importlib.import_module("sbd.core.config.models")
    module_path = Path(audio.__file__).resolve()
    if not module_path.is_relative_to(Path(source_root).resolve()):
        raise RuntimeError("loaded Core Audio HAL does not originate from the pinned checkout")
    return audio, models


def make_alsa_config(
    core_root: Path,
    input_device: str,
    output_device: str,
    input_channel: int,
) -> tuple[Any, Any]:
    if input_channel not in {0, 1}:
        raise ValueError("input_channel must be 0 or 1")
    audio, models = load_core_audio(core_root)
    stream = models.AudioFormatConfig(
        sample_rate=STREAM_RATE,
        channels=STREAM_CHANNELS,
        sample_format="s16_le",
    )
    native = models.AudioFormatConfig(sample_rate=48_000, channels=2, sample_format="s32_le")
    config = models.AudioConfig(
        driver="alsa",
        input=models.AudioInputConfig(
            stream_format=stream,
            frame_duration_ms=20,
            device=input_device,
            native_format=native,
            channel_index=input_channel,
            valid_bits=24,
            valid_bits_alignment="msb",
            resampler="samplerate.sinc_best",
        ),
        output=models.AudioOutputConfig(
            stream_format=stream,
            device=output_device,
            native_format=native,
        ),
    )
    return audio, config


def validate_stream_pcm(payload: bytes) -> None:
    if type(payload) is not bytes or len(payload) % STREAM_FRAME_BYTES:
        raise ValueError("M3 stream PCM must be complete 16kHz mono S16_LE samples")


def write_stream_wav(path: Path, payload: bytes) -> None:
    validate_stream_pcm(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as raw:
        with wave.open(raw, "wb") as destination:
            destination.setnchannels(STREAM_CHANNELS)
            destination.setsampwidth(STREAM_SAMPLE_WIDTH)
            destination.setframerate(STREAM_RATE)
            destination.writeframes(payload)


def read_stream_wav(path: Path) -> bytes:
    with wave.open(str(path), "rb") as source:
        actual = (source.getframerate(), source.getnchannels(), source.getsampwidth())
        expected = (STREAM_RATE, STREAM_CHANNELS, STREAM_SAMPLE_WIDTH)
        if actual != expected or source.getcomptype() != "NONE":
            raise ValueError(f"M3 WAV format mismatch: expected={expected} actual={actual}")
        payload = source.readframes(source.getnframes())
    validate_stream_pcm(payload)
    return payload


def iter_pcm_chunks(payload: bytes, samples_per_chunk: int = HAL_FRAME_SAMPLES) -> Iterable[bytes]:
    validate_stream_pcm(payload)
    if type(samples_per_chunk) is not int or samples_per_chunk <= 0:
        raise ValueError("samples_per_chunk must be a positive integer")
    chunk_bytes = samples_per_chunk * STREAM_FRAME_BYTES
    return (payload[offset:offset + chunk_bytes] for offset in range(0, len(payload), chunk_bytes))


async def capture_frames(audio_input: Any, frame_count: int, timeout_s: float) -> bytes:
    """Capture exact Core 20 ms frames and always release stream/device ownership."""

    if type(frame_count) is not int or frame_count <= 0 or timeout_s <= 0:
        raise ValueError("capture requires positive frame_count and timeout")
    stream: Any | None = None
    frames: list[bytes] = []
    await asyncio.wait_for(audio_input.start(), timeout=timeout_s)
    try:
        stream = audio_input.frames()
        for _ in range(frame_count):
            frame = await asyncio.wait_for(anext(stream), timeout=timeout_s)
            if type(frame) is not bytes or len(frame) != HAL_FRAME_BYTES:
                raise RuntimeError("Core AudioInput returned a malformed 20 ms stream frame")
            frames.append(frame)
    finally:
        if stream is not None:
            await asyncio.wait_for(stream.aclose(), timeout=timeout_s)
        await asyncio.wait_for(audio_input.stop(), timeout=timeout_s)
    return b"".join(frames)


async def _pcm_iterator(chunks: Iterable[bytes]) -> AsyncIterator[bytes]:
    for chunk in chunks:
        validate_stream_pcm(chunk)
        yield chunk


async def play_stream_pcm(
    audio_output: Any,
    payload: bytes,
    timeout_s: float,
    samples_per_chunk: int = HAL_FRAME_SAMPLES,
) -> None:
    """Play native TTS-format PCM through Core and always stop the output."""

    if timeout_s <= 0:
        raise ValueError("playback timeout must be positive")
    chunks = iter_pcm_chunks(payload, samples_per_chunk)
    await asyncio.wait_for(audio_output.start(), timeout=timeout_s)
    try:
        await asyncio.wait_for(audio_output.play(_pcm_iterator(chunks)), timeout=timeout_s)
    finally:
        await asyncio.wait_for(audio_output.stop(), timeout=timeout_s)


def process_resource_snapshot() -> dict[str, int]:
    """Collect stable local counters used for before/after cleanup comparisons."""

    task_dir = Path("/proc/self/task")
    fd_dir = Path("/proc/self/fd")
    return {
        "process_id": os.getpid(),
        "threads": len(list(task_dir.iterdir())) if task_dir.is_dir() else 0,
        "file_descriptors": len(list(fd_dir.iterdir())) if fd_dir.is_dir() else 0,
    }
