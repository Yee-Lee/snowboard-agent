"""Stateful stream-to-native conversion for selected ALSA playback."""

from __future__ import annotations

import struct
from collections.abc import Callable
from typing import Any


class StreamFormatAdapter:
    """Convert 16 kHz mono S16_LE chunks to 48 kHz stereo S32_LE chunks.

    The resampler is deliberately created lazily: portable imports of the
    Audio HAL must not require the optional Raspberry Pi audio dependencies.
    ``resampler_factory`` is a private seam for deterministic unit tests.
    """

    def __init__(self, *, resampler_factory: Callable[[], Any] | None = None) -> None:
        self._resampler_factory = resampler_factory or self._make_resampler
        self._resampler: Any | None = None

    def convert(self, chunk: bytes) -> bytes:
        if len(chunk) % 2:
            raise ValueError("stream chunk must contain complete S16_LE mono samples")
        if not chunk:
            return b""
        return self._pack_native(self._process(self._to_float(chunk), end_of_input=False))

    def flush(self) -> bytes:
        if self._resampler is None:
            return b""
        return self._pack_native(self._process([], end_of_input=True))

    def reset(self) -> None:
        """Discard state so the next conversion starts an independent session."""
        self._resampler = None

    def _process(self, samples: list[float], *, end_of_input: bool) -> Any:
        if self._resampler is None:
            self._resampler = self._resampler_factory()
        return self._resampler.process(samples, ratio=3.0, end_of_input=end_of_input)

    @staticmethod
    def _to_float(chunk: bytes) -> list[float]:
        return [sample / 32_768.0 for (sample,) in struct.iter_unpack("<h", chunk)]

    @staticmethod
    def _pack_native(samples: Any) -> bytes:
        values: list[int] = []
        for sample in samples:
            scaled = max(-2_147_483_648, min(2_147_483_647, round(float(sample) * 2_147_483_648)))
            values.extend((scaled, scaled))
        return struct.pack(f"<{len(values)}i", *values) if values else b""

    @staticmethod
    def _make_resampler() -> Any:
        try:
            import numpy as np
            import samplerate
        except ImportError as exc:
            raise RuntimeError("samplerate==0.2.4 and numpy are required for ALSA output adaptation") from exc

        class _Resampler:
            def __init__(self) -> None:
                self._native = samplerate.Resampler(converter_type="sinc_best", channels=1)

            def process(self, samples, *, ratio: float, end_of_input: bool):
                return self._native.process(
                    np.asarray(samples, dtype=np.float32), ratio=ratio, end_of_input=end_of_input
                )

        return _Resampler()
