"""Deterministic PCM onset/end detection and clock-bound validation."""

from __future__ import annotations

from dataclasses import dataclass
import struct


class AcousticError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AcousticConfig:
    sample_rate_hz: int
    threshold_abs_s16: int
    minimum_active_samples: int
    clock_error_ns: int
    detector_error_ns: int

    def validate(self) -> None:
        if self.sample_rate_hz <= 0:
            raise AcousticError("INVALID_SAMPLE_RATE")
        if not 0 < self.threshold_abs_s16 <= 32767:
            raise AcousticError("INVALID_THRESHOLD")
        if self.minimum_active_samples <= 0:
            raise AcousticError("INVALID_ACTIVE_WINDOW")
        if self.clock_error_ns < 0 or self.detector_error_ns < 0:
            raise AcousticError("INVALID_ERROR_BOUND")
        if self.clock_error_ns + self.detector_error_ns > 50_000_000:
            raise AcousticError("EXCESSIVE_UNCERTAINTY")


@dataclass(frozen=True, slots=True)
class AcousticObservation:
    onset_sample: int
    final_sample: int
    onset_monotonic_ns: int
    final_monotonic_ns: int
    uncertainty_ns: int


def detect_s16le(
    pcm: bytes,
    *,
    capture_start_monotonic_ns: int,
    config: AcousticConfig,
) -> AcousticObservation:
    """Locate stable audible activity in timestamped mono S16_LE capture."""

    config.validate()
    if type(pcm) is not bytes or not pcm or len(pcm) % 2:
        raise AcousticError("INVALID_PCM")
    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    active = [abs(value) >= config.threshold_abs_s16 for value in samples]
    width = config.minimum_active_samples
    onset = next(
        (index for index in range(len(active) - width + 1) if all(active[index:index + width])),
        None,
    )
    final = next(
        (index + width - 1 for index in range(len(active) - width, -1, -1)
         if all(active[index:index + width])),
        None,
    )
    if onset is None or final is None or final < onset:
        raise AcousticError("NO_ACOUSTIC_ACTIVITY")

    def timestamp(index: int) -> int:
        return capture_start_monotonic_ns + index * 1_000_000_000 // config.sample_rate_hz

    return AcousticObservation(
        onset_sample=onset,
        final_sample=final,
        onset_monotonic_ns=timestamp(onset),
        final_monotonic_ns=timestamp(final),
        uncertainty_ns=config.clock_error_ns + config.detector_error_ns,
    )
