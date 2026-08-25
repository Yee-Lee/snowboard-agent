from sbd.core.config.models import ASRConfig

from .asr import ASRAdapter, ASRResult, MockASRAdapter, NullASRAdapter
from .listener import Listen


def make_asr_adapter(cfg: ASRConfig) -> ASRAdapter:
    if cfg.driver == "mock":
        return MockASRAdapter()
    if cfg.driver == "null":
        return NullASRAdapter()
    raise ValueError(
        f"ASR driver '{cfg.driver}' is not yet available. "
        "Candidate-specific backend requires M2B provisional selection ACK."
    )


__all__ = [
    "ASRAdapter", "ASRResult", "Listen", "MockASRAdapter", "NullASRAdapter",
    "make_asr_adapter",
]
