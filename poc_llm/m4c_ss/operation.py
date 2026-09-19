"""One logical POC streaming-speak operation with bounded convergence."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

from poc_llm.m4c_ss.controller import CleanupProof, FragmentChannel, FragmentChannelError, TerminalProof
from poc_llm.m4c_ss.mapping import (
    MappingBatch,
    abort_mapping_batch,
    acknowledge_mapping_batch,
    next_mapping_batch,
)


class SpeechBackend(Protocol):
    async def speak(self, text: str) -> None: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> None: ...
    def operation_idle(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class OperationResult:
    status: str
    normal_success: bool
    force_abort_used: bool
    backend_idle: bool
    terminal_proof: TerminalProof | None
    cleanup_proof: CleanupProof | None


class StreamingSpeakOperation:
    """Coordinate fragments and a private backend without publishing Core Facts."""

    def __init__(
        self,
        operation_id: str,
        *,
        candidate: str,
        backend: SpeechBackend,
        speak_timeout_s: float = 30.0,
        abort_timeout_s: float = 2.0,
        force_abort_timeout_s: float = 1.0,
    ) -> None:
        if speak_timeout_s <= 0 or abort_timeout_s <= 0 or force_abort_timeout_s <= 0:
            raise ValueError("timeouts must be positive")
        self.operation_id = operation_id
        self.channel = FragmentChannel(operation_id)
        self.candidate = candidate
        self.backend = backend
        self.speak_timeout_s = speak_timeout_s
        self.abort_timeout_s = abort_timeout_s
        self.force_abort_timeout_s = force_abort_timeout_s
        self._active: MappingBatch | None = None
        self._converge_lock = asyncio.Lock()
        self._result: OperationResult | None = None
        self._force_abort_used = False

    async def feed(self, sequence: int, text: str) -> None:
        await self.channel.feed(self.operation_id, sequence, text)

    async def finish(self, terminal_text: str, *, semantic_valid: bool = True) -> None:
        try:
            await self.channel.finish(
                self.operation_id, terminal_text, semantic_valid=semantic_valid,
            )
        except FragmentChannelError:
            await self._converge("FAILED")
            raise

    async def interrupt(self) -> OperationResult:
        return await self._converge("CANCELLED")

    async def shutdown(self) -> OperationResult:
        return await self._converge("CANCELLED")

    async def fail(self) -> OperationResult:
        """Converge a generation/protocol failure without reporting cancellation."""

        return await self._converge("FAILED")

    async def run(self) -> OperationResult:
        if self._result is not None:
            return self._result
        try:
            while True:
                batch = await next_mapping_batch(self.channel, self.candidate)
                if batch is None:
                    proof = await self.channel.complete(self.operation_id)
                    self._result = OperationResult(
                        status="OK", normal_success=True, force_abort_used=False,
                        backend_idle=self.backend.operation_idle(), terminal_proof=proof,
                        cleanup_proof=None,
                    )
                    return self._result
                self._active = batch
                try:
                    await asyncio.wait_for(
                        self.backend.speak(batch.text), self.speak_timeout_s,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    return await self._converge("FAILED")
                if self.channel.state in {"FAILED", "CANCELLED"}:
                    return await self._converge(self.channel.state)
                await acknowledge_mapping_batch(self.channel, self.operation_id, batch)
                self._active = None
        except FragmentChannelError:
            if self.channel.state in {"FAILED", "CANCELLED"}:
                return await self._converge(self.channel.state)
            raise

    async def _converge(self, status: str) -> OperationResult:
        async with self._converge_lock:
            if self._result is not None:
                return self._result
            if self.channel.state not in {"FAILED", "CANCELLED"}:
                await self.channel.cancel(self.operation_id)
            active = self._active
            if active is not None:
                try:
                    await asyncio.wait_for(self.backend.abort(), self.abort_timeout_s)
                except Exception:
                    self._force_abort_used = True
                    try:
                        await asyncio.wait_for(
                            self.backend.force_abort(), self.force_abort_timeout_s,
                        )
                    except Exception as error:
                        raise FragmentChannelError("CONTROL_FAILURE") from error
                if self.channel.inflight_sequence == active.sequences[0]:
                    await abort_mapping_batch(self.channel, self.operation_id, active)
                self._active = None
            cleanup = await self.channel.cleanup_proof(self.operation_id)
            if not self.backend.operation_idle():
                raise FragmentChannelError("CONTROL_FAILURE")
            self._result = OperationResult(
                status=status, normal_success=False,
                force_abort_used=self._force_abort_used,
                backend_idle=True, terminal_proof=None, cleanup_proof=cleanup,
            )
            return self._result
