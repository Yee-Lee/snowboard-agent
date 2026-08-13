"""Stateful Option A conversion primitives for exploratory P4 validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal


Alignment = Literal["left", "right"]


@dataclass(frozen=True, slots=True)
class ValidBitMapping:
    channel_index: int
    channels: int = 2
    valid_bits: int = 24
    alignment: Alignment = "left"

    def validate(self) -> None:
        if self.channels <= 0:
            raise ValueError("channels must be positive")
        if not 0 <= self.channel_index < self.channels:
            raise ValueError("channel_index is outside the container")
        if not 1 <= self.valid_bits <= 32:
            raise ValueError("valid_bits must be between 1 and 32")
        if self.alignment not in {"left", "right"}:
            raise ValueError("alignment must be left or right")


@dataclass(frozen=True, slots=True)
class FlushResult:
    frames: tuple[bytes, ...]
    partial_pcm: bytes


def decode_s32_interleaved(
    payload: bytes,
    mapping: ValidBitMapping,
    numpy_module: Any,
) -> Any:
    """Decode one selected S32_LE channel using an explicit valid-bit policy."""

    mapping.validate()
    frame_bytes = mapping.channels * 4
    if len(payload) % frame_bytes:
        raise ValueError("payload does not contain complete interleaved frames")
    containers = numpy_module.frombuffer(payload, dtype="<i4").reshape(
        -1, mapping.channels
    )[:, mapping.channel_index].astype(numpy_module.int64)
    if mapping.alignment == "left":
        values = containers >> (32 - mapping.valid_bits)
    else:
        mask = (1 << mapping.valid_bits) - 1
        sign = 1 << (mapping.valid_bits - 1)
        unsigned = containers & mask
        values = (unsigned ^ sign) - sign
    scale = float(1 << (mapping.valid_bits - 1))
    return (values / scale).astype(numpy_module.float32)


def float_to_s16le(samples: Any, numpy_module: Any) -> bytes:
    """Convert normalized float samples to saturating S16_LE without wrap."""

    values = numpy_module.asarray(samples, dtype=numpy_module.float64)
    scaled = numpy_module.rint(values * 32768.0)
    saturated = numpy_module.clip(scaled, -32768, 32767).astype("<i2")
    return saturated.tobytes()


class OptionAStreamConverter:
    """Preserve decode/resampler/framing state across arbitrary byte chunks."""

    input_rate_hz = 48_000
    output_rate_hz = 16_000
    ratio = 1.0 / 3.0

    def __init__(
        self,
        mapping: ValidBitMapping,
        *,
        converter_type: str = "sinc_best",
        frame_samples: int = 320,
        numpy_module: Any | None = None,
        resampler_factory: Callable[[], Any] | None = None,
    ) -> None:
        mapping.validate()
        if frame_samples <= 0:
            raise ValueError("frame_samples must be positive")
        if numpy_module is None:
            import numpy as numpy_module
        if resampler_factory is None:
            import samplerate

            resampler_factory = lambda: samplerate.Resampler(
                converter_type, channels=1
            )
        self.mapping = mapping
        self.converter_type = converter_type
        self.frame_samples = frame_samples
        self._np = numpy_module
        self._resampler_factory = resampler_factory
        self.reset()

    def reset(self) -> None:
        self._resampler = self._resampler_factory()
        self._raw_remainder = b""
        self._output = self._np.empty(0, dtype=self._np.float32)
        self._flushed = False
        self.total_input_samples = 0
        self.total_resampled_samples = 0
        self.frames_yielded = 0

    def feed(self, payload: bytes) -> tuple[bytes, ...]:
        if self._flushed:
            raise RuntimeError("converter must be reset after flush")
        combined = self._raw_remainder + payload
        frame_bytes = self.mapping.channels * 4
        complete_bytes = len(combined) - (len(combined) % frame_bytes)
        self._raw_remainder = combined[complete_bytes:]
        if not complete_bytes:
            return ()
        decoded = decode_s32_interleaved(
            combined[:complete_bytes], self.mapping, self._np
        )
        self.total_input_samples += int(decoded.size)
        converted = self._resampler.process(
            decoded,
            self.ratio,
            end_of_input=False,
        )
        return self._accumulate(converted)

    def flush(self) -> FlushResult:
        if self._flushed:
            raise RuntimeError("flush is not idempotent; reset starts a new session")
        if self._raw_remainder:
            raise ValueError("incomplete interleaved container remains at flush")
        tail = self._resampler.process(
            self._np.empty(0, dtype=self._np.float32),
            self.ratio,
            end_of_input=True,
        )
        frames = self._accumulate(tail)
        partial_pcm = float_to_s16le(self._output, self._np)
        self._output = self._np.empty(0, dtype=self._np.float32)
        self._flushed = True
        return FlushResult(frames=frames, partial_pcm=partial_pcm)

    def _accumulate(self, converted: Any) -> tuple[bytes, ...]:
        values = self._np.asarray(converted, dtype=self._np.float32).reshape(-1)
        self.total_resampled_samples += int(values.size)
        if values.size:
            self._output = self._np.concatenate((self._output, values))
        frame_count = int(self._output.size) // self.frame_samples
        frames = []
        for index in range(frame_count):
            start = index * self.frame_samples
            end = start + self.frame_samples
            frames.append(float_to_s16le(self._output[start:end], self._np))
        if frame_count:
            self._output = self._output[frame_count * self.frame_samples :].copy()
            self.frames_yielded += frame_count
        return tuple(frames)
