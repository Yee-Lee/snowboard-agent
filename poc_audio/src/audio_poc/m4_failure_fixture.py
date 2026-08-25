"""Build a bounded external-only long WAV for actual M4 timeout/cancel probes."""

from __future__ import annotations

import wave
from pathlib import Path


def build_sustained_probe(source: Path, destination: Path, minimum_seconds: int = 30) -> Path:
    if not source.is_file() or destination.exists() or minimum_seconds <= 0:
        raise ValueError("M4 failure sustained probe inputs are invalid")
    with wave.open(str(source), "rb") as input_wav:
        parameters = input_wav.getparams()
        if (parameters.nchannels, parameters.sampwidth, parameters.framerate, parameters.comptype) != (1, 2, 16_000, "NONE"):
            raise ValueError("M4 failure sustained probe source format is invalid")
        frames = input_wav.readframes(input_wav.getnframes())
    if not frames:
        raise ValueError("M4 failure sustained probe source is empty")
    destination.parent.mkdir(parents=True, exist_ok=False)
    repeats = max(1, (minimum_seconds * 16_000 * 2 + len(frames) - 1) // len(frames))
    with wave.open(str(destination), "wb") as output_wav:
        output_wav.setparams(parameters)
        output_wav.writeframes(frames * repeats)
    return destination
