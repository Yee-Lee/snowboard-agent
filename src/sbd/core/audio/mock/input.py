"""Deterministic finite mock audio input."""

from sbd.core.audio.null.input import NullAudioInput
from sbd.core.config.models import AudioConfig


class MockAudioInput(NullAudioInput):
    def __init__(
        self,
        config: AudioConfig | None = None,
        *,
        frames: tuple[bytes, ...] | None = None,
    ) -> None:
        cfg = config or AudioConfig(driver="mock")
        samples = cfg.sample_rate * cfg.frame_duration_ms // 1000
        silence = bytes(samples * cfg.channels * cfg.bit_depth // 8)
        super().__init__(cfg, finite_frames=frames or (silence,))
