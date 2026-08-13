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
        input_config = cfg.input
        stream_format = input_config.stream_format
        samples = stream_format.sample_rate * input_config.frame_duration_ms // 1000
        container_bytes = {"s16_le": 2, "s32_le": 4}[stream_format.sample_format]
        silence = bytes(samples * stream_format.channels * container_bytes)
        super().__init__(cfg, finite_frames=frames or (silence,))
