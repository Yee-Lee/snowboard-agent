"""One-model-call coordination for the private M4C streaming-speak path."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from poc_llm.m4c_ss.operation import OperationResult, StreamingSpeakOperation
from poc_llm.m4c_ss.s2 import S2Terminal


class SafeTextSource(Protocol):
    async def generate(
        self, on_safe_text: Callable[[str], Awaitable[None]],
    ) -> S2Terminal: ...
    async def cancel(self) -> None: ...
    async def force_abort(self) -> None: ...
    def operation_idle(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class PipelineResult:
    operation: OperationResult
    terminal: S2Terminal | None
    source_force_abort_used: bool
    source_idle: bool


class StreamingSpeakPipeline:
    """Bind one generation to one speech operation with shared cancellation."""

    def __init__(
        self,
        *,
        source: SafeTextSource,
        operation: StreamingSpeakOperation,
        mode: str = "B",
        cancel_timeout_s: float = 2.0,
        force_abort_timeout_s: float = 3.0,
    ) -> None:
        if mode not in {"A", "B"}:
            raise ValueError("mode must be A or B")
        if cancel_timeout_s <= 0 or force_abort_timeout_s <= 0:
            raise ValueError("timeouts must be positive")
        self.source = source
        self.operation = operation
        self.mode = mode
        self.cancel_timeout_s = cancel_timeout_s
        self.force_abort_timeout_s = force_abort_timeout_s
        self._sequence = 0
        self._generation: asyncio.Task[S2Terminal] | None = None
        self._speech: asyncio.Task[OperationResult] | None = None
        self._source_force_abort_used = False
        self._closed = False
        self._source_stop_lock = asyncio.Lock()

    async def _emit(self, text: str) -> None:
        if self._closed or type(text) is not str or not text:
            raise RuntimeError("INVALID_SAFE_TEXT")
        if self.mode == "A":
            return
        sequence = self._sequence
        await self.operation.feed(sequence, text)
        self._sequence += 1

    async def execute(self) -> PipelineResult:
        if self._generation is not None or self._speech is not None:
            raise RuntimeError("PIPELINE_ALREADY_STARTED")
        self._speech = asyncio.create_task(self.operation.run())
        self._generation = asyncio.create_task(self.source.generate(self._emit))
        done, _ = await asyncio.wait(
            {self._generation, self._speech}, return_when=asyncio.FIRST_COMPLETED,
        )
        if self._speech in done and self._generation not in done:
            operation_result = self._speech.result()
            await self._stop_source()
            return self._result(operation_result, None)
        try:
            terminal = self._generation.result()
        except asyncio.CancelledError:
            operation_result = await self.operation.interrupt()
            return self._result(operation_result, None)
        except Exception:
            operation_result = await self.operation.fail()
            return self._result(operation_result, None)
        if self.mode == "A" and terminal.text:
            await self.operation.feed(0, terminal.text)
            self._sequence = 1
        try:
            await self.operation.finish(terminal.text, semantic_valid=True)
        except Exception:
            return self._result(await self._speech, terminal)
        return self._result(await self._speech, terminal)

    async def interrupt(self) -> PipelineResult:
        self._closed = True
        operation_result = await self.operation.interrupt()
        await self._stop_source()
        if self._speech is not None:
            await self._speech
        return self._result(operation_result, None)

    async def shutdown(self) -> PipelineResult:
        self._closed = True
        operation_result = await self.operation.shutdown()
        await self._stop_source()
        if self._speech is not None:
            await self._speech
        return self._result(operation_result, None)

    async def _stop_source(self) -> None:
        async with self._source_stop_lock:
            generation = self._generation
            if generation is None or generation.done():
                return
            try:
                await asyncio.wait_for(self.source.cancel(), self.cancel_timeout_s)
            except TimeoutError:
                await self._force_source(generation)
                return
            try:
                await asyncio.wait_for(asyncio.shield(generation), self.cancel_timeout_s)
            except TimeoutError:
                await self._force_source(generation)
            except asyncio.CancelledError:
                return
            except Exception:
                return

    async def _force_source(self, generation: asyncio.Task[S2Terminal]) -> None:
        if generation.done():
            return
        self._source_force_abort_used = True
        await asyncio.wait_for(
            self.source.force_abort(), self.force_abort_timeout_s,
        )
        try:
            await asyncio.wait_for(
                asyncio.shield(generation), self.force_abort_timeout_s,
            )
        except asyncio.CancelledError:
            return
        except Exception:
            return

    def _result(
        self, operation: OperationResult, terminal: S2Terminal | None,
    ) -> PipelineResult:
        idle = self.source.operation_idle()
        if not idle:
            raise RuntimeError("CONTROL_FAILURE")
        return PipelineResult(
            operation=operation,
            terminal=terminal,
            source_force_abort_used=self._source_force_abort_used,
            source_idle=idle,
        )
