"""Frozen T01-T03 mapping traces over a managed speech backend."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
from typing import Protocol

from poc_llm.m4c_ss.mapping import CANDIDATES
from poc_llm.m4c_ss.operation import OperationResult, SpeechBackend, StreamingSpeakOperation


MAPPING_TRACE_FRAGMENTS = {
    "T01": ("我是雪板，", "很高興為您服務！"),
    "T02": ("因為太陽光穿過大氣，", "藍光被散射，", "所以天空看起來是藍色的。"),
    "T03": ("多聽多說，", "找對話練習，", "會很有幫助喔！"),
}


class ManagedSpeechBackend(SpeechBackend, Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...


@dataclass(frozen=True, slots=True)
class MappingRunResult:
    trace_id: str
    candidate: str
    status: str
    fragment_count: int
    tts_request_count: int
    terminal_text_sha256: str
    terminal_codepoints: int
    request_text_sha256: tuple[str, ...]
    request_codepoints: tuple[int, ...]
    backend_idle: bool


class _CountingBackend:
    def __init__(self, backend: ManagedSpeechBackend) -> None:
        self.backend = backend
        self.request_text_sha256: list[str] = []
        self.request_codepoints: list[int] = []

    async def speak(self, text: str) -> None:
        encoded = text.encode("utf-8")
        self.request_text_sha256.append(hashlib.sha256(encoded).hexdigest())
        self.request_codepoints.append(len(text))
        await self.backend.speak(text)

    async def abort(self) -> None:
        await self.backend.abort()

    async def force_abort(self) -> None:
        await self.backend.force_abort()

    def operation_idle(self) -> bool:
        return self.backend.operation_idle()


async def run_mapping_trace(
    *,
    trace_id: str,
    candidate: str,
    backend: ManagedSpeechBackend,
    speak_timeout_s: float = 1800.0,
) -> MappingRunResult:
    """Run one fresh mapping sample and always stop its backend owner.

    The first two fragments are admitted before the consumer starts. This
    gives B2 exactly one already-available look-ahead while preserving the
    same frozen trace for B1. A third fragment is admitted only after the
    consumer frees bounded queue capacity.
    """

    if trace_id not in MAPPING_TRACE_FRAGMENTS:
        raise ValueError("UNKNOWN_MAPPING_TRACE")
    if candidate not in CANDIDATES:
        raise ValueError("UNKNOWN_MAPPING_CANDIDATE")
    fragments = MAPPING_TRACE_FRAGMENTS[trace_id]
    terminal_text = "".join(fragments)
    operation_id = f"mapping:{trace_id}:{candidate}"
    counting = _CountingBackend(backend)
    operation = StreamingSpeakOperation(
        operation_id,
        candidate=candidate,
        backend=counting,
        speak_timeout_s=speak_timeout_s,
    )
    started = False
    running: asyncio.Task[OperationResult] | None = None
    try:
        await backend.start()
        started = True
        for sequence, text in enumerate(fragments[:2]):
            await operation.feed(sequence, text)
        running = asyncio.create_task(operation.run())
        for sequence, text in enumerate(fragments[2:], start=2):
            await operation.feed(sequence, text)
        await operation.finish(terminal_text)
        result = await running
        if not result.normal_success or result.terminal_proof is None:
            raise RuntimeError("MAPPING_OPERATION_FAILED")
        if result.terminal_proof.fragment_count != len(fragments):
            raise RuntimeError("MAPPING_FRAGMENT_ACCOUNTING_FAILED")
        if not counting.operation_idle():
            raise RuntimeError("MAPPING_BACKEND_NOT_IDLE")
        encoded = terminal_text.encode("utf-8")
        return MappingRunResult(
            trace_id=trace_id,
            candidate=candidate,
            status="PASS",
            fragment_count=len(fragments),
            tts_request_count=len(counting.request_text_sha256),
            terminal_text_sha256=hashlib.sha256(encoded).hexdigest(),
            terminal_codepoints=len(terminal_text),
            request_text_sha256=tuple(counting.request_text_sha256),
            request_codepoints=tuple(counting.request_codepoints),
            backend_idle=True,
        )
    finally:
        if running is not None and not running.done():
            running.cancel()
            await asyncio.gather(running, return_exceptions=True)
        if started:
            await backend.stop()
