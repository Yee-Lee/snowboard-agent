"""One bounded mapping trace with simultaneous private USB capture."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from typing import Callable, Protocol

from poc_llm.m4c_ss.capture import (
    AcousticActivity, AlsaTimestampCaptureSession, CaptureRecording, analyze_acoustic_activity,
)
from poc_llm.m4c_ss.mapping_runner import (
    ManagedSpeechBackend, MappingRunResult, run_mapping_trace,
)


class CapturePort(Protocol):
    def start(self, *, minimum_baseline_blocks: int = 30, timeout_s: float = 2.0) -> None: ...
    def stop(self) -> CaptureRecording: ...


@dataclass(frozen=True, slots=True)
class AcousticMappingResult:
    status: str
    mapping: MappingRunResult
    acoustic: AcousticActivity
    private_pcm_bytes: int
    private_pcm_sha256: str
    capture_owner_stopped: bool


def _write_private_pcm(path: Path, pcm: bytes) -> tuple[int, str]:
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise ValueError("PRIVATE_PCM_PATH_INVALID")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(pcm)
        output.flush()
    return len(pcm), hashlib.sha256(pcm).hexdigest()


async def run_acoustic_mapping_trace(
    *,
    trace_id: str,
    candidate: str,
    backend: ManagedSpeechBackend,
    capture: CapturePort,
    private_pcm_path: Path,
    tail_seconds: float = 0.5,
    onset_not_before: Callable[[], int | None] | None = None,
) -> AcousticMappingResult:
    if tail_seconds < 0 or tail_seconds > 2.0:
        raise ValueError("INVALID_CAPTURE_TAIL")
    await asyncio.to_thread(capture.start)
    mapping: MappingRunResult | None = None
    mapping_error: BaseException | None = None
    recording: CaptureRecording | None = None
    try:
        mapping = await run_mapping_trace(
            trace_id=trace_id,
            candidate=candidate,
            backend=backend,
        )
        await asyncio.sleep(tail_seconds)
    except BaseException as error:
        mapping_error = error
    finally:
        recording = await asyncio.to_thread(capture.stop)
    size, digest = await asyncio.to_thread(
        _write_private_pcm, private_pcm_path, recording.pcm_s16le,
    )
    if mapping_error is not None:
        raise mapping_error
    if mapping is None:
        raise RuntimeError("MAPPING_RESULT_MISSING")
    not_before_ns = onset_not_before() if onset_not_before is not None else None
    if onset_not_before is not None and not_before_ns is None:
        raise RuntimeError("AUDIO_FIRST_WRITE_MISSING")
    acoustic = analyze_acoustic_activity(
        recording.blocks,
        not_before_ns=not_before_ns,
    )
    status = "PASS" if acoustic.uncertainty_ns <= 50_000_000 else "INCONCLUSIVE"
    return AcousticMappingResult(
        status=status,
        mapping=mapping,
        acoustic=acoustic,
        private_pcm_bytes=size,
        private_pcm_sha256=digest,
        capture_owner_stopped=recording.owner_stopped,
    )


def make_usb_capture(device: str) -> AlsaTimestampCaptureSession:
    return AlsaTimestampCaptureSession(device)
