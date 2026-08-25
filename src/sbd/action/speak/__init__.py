from .speaker import Speak
from sbd.core.config.models import TTSConfig

from .tts import MockTTSAdapter, NullTTSAdapter, TTSAdapter


def make_tts_adapter(cfg: TTSConfig) -> TTSAdapter:
    if cfg.driver == "mock":
        return MockTTSAdapter()
    if cfg.driver == "null":
        return NullTTSAdapter()
    raise ValueError(
        f"TTS driver '{cfg.driver}' is not yet available. "
        "Candidate-specific backend requires M2B provisional selection ACK."
    )


__all__ = ["MockTTSAdapter", "NullTTSAdapter", "Speak", "TTSAdapter", "make_tts_adapter"]
