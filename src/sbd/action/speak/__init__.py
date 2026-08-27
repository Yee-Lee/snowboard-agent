from .speaker import Speak
from sbd.core.config.models import TTSConfig

from .tts import MockTTSAdapter, NullTTSAdapter, TTSAdapter


def make_tts_adapter(cfg: TTSConfig) -> TTSAdapter:
    if cfg.driver == "mock":
        return MockTTSAdapter()
    if cfg.driver == "null":
        return NullTTSAdapter()
    if cfg.driver == "sherpa_matcha":
        from sbd.adaptor.audio_lock import AudioArtifactLock

        assert cfg.artifact_lock_path is not None
        lock = AudioArtifactLock.load(cfg.artifact_lock_path)
        lock.verify_tts_config(cfg)
        from .matcha.adapter import MatchaTTSAdapter

        return MatchaTTSAdapter(cfg, lock=lock)
    raise ValueError(
        f"TTS driver '{cfg.driver}' is unsupported"
    )


__all__ = ["MockTTSAdapter", "NullTTSAdapter", "Speak", "TTSAdapter", "make_tts_adapter"]
