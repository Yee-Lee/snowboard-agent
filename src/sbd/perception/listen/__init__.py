from sbd.core.config.models import ASRConfig

from .asr import ASRAdapter, ASRResult, MockASRAdapter, NullASRAdapter
from .listener import Listen


def make_asr_adapter(cfg: ASRConfig) -> ASRAdapter:
    if cfg.driver == "mock":
        return MockASRAdapter()
    if cfg.driver == "null":
        return NullASRAdapter()
    if cfg.driver == "whispercpp":
        from sbd.adaptor.audio_lock import AudioArtifactLock

        assert cfg.artifact_lock_path is not None
        lock = AudioArtifactLock.load(cfg.artifact_lock_path)
        lock.verify_asr_config(cfg)
        from .whispercpp.adapter import WhisperCppASRAdapter

        return WhisperCppASRAdapter(cfg, lock=lock)
    raise ValueError(
        f"ASR driver '{cfg.driver}' is unsupported"
    )


__all__ = [
    "ASRAdapter", "ASRResult", "Listen", "MockASRAdapter", "NullASRAdapter",
    "make_asr_adapter",
]
