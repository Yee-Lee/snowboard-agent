"""Private M4C B2 streaming-speak operation."""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
import hashlib
import inspect
from collections.abc import Awaitable
from typing import Callable

from sbd.action.speak.tts import TTSAdapter
from sbd.adaptor.errors import AdapterError
from sbd.core.audio.base import AudioOutput
from sbd.core.event_bus import EventBus
from sbd.core.events import ActionCompleted
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.faults import BackendDisposition, ComponentSystemFault

MAX_PENDING_FRAGMENTS = 2
MAX_PENDING_UTF8_BYTES = 256


class StreamingSpeakError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class StreamingSpeakProof:
    fragment_count: int
    normalized_utf8_bytes: int
    normalized_text_sha256: str
    queue_high_water: int
    admission_closed: bool = True
    queue_empty: bool = True
    owner_idle: bool = True


@dataclass(frozen=True, slots=True)
class _Fragment:
    sequence: int
    text: str

    @property
    def size(self) -> int:
        return len(self.text.encode("utf-8"))


class StreamingSpeakControl:
    """One operation, one bounded queue, and one eventual public completion."""

    def __init__(self, *, session_id: str, turn_id: int, operation_id: str,
                 tts: TTSAdapter, audio_output: AudioOutput, bus: EventBus,
                 observe: Callable[[str], None] | None = None,
                 before_start: Callable[[], Awaitable[None] | None] | None = None) -> None:
        if (type(session_id) is not str or not session_id
                or type(turn_id) is not int or turn_id < 0
                or type(operation_id) is not str or not operation_id):
            raise StreamingSpeakError("INVALID_OPERATION_ID")
        self.session_id, self.turn_id, self.operation_id = session_id, turn_id, operation_id
        self._tts, self._audio_output, self._bus = tts, audio_output, bus
        self._observe = observe
        self._before_start = before_start
        self._condition = asyncio.Condition()
        self._pending: deque[_Fragment] = deque()
        self._pending_bytes = 0
        self._inflight: tuple[_Fragment, ...] = ()
        self._admitted: list[str] = []
        self._acknowledged: list[str] = []
        self._next_sequence = 0
        self._terminal_text: str | None = None
        self._state = "OPEN"
        self._queue_high_water = 0
        self._pcm = None
        self._task: asyncio.Task[StreamingSpeakProof] | None = None
        self._adopted_correlation: int | None = None
        self._adopted = asyncio.Event()

    @property
    def state(self) -> str: return self._state
    @property
    def queue_depth(self) -> int: return len(self._pending)
    @property
    def pending_utf8_bytes(self) -> int: return self._pending_bytes
    @property
    def queue_high_water(self) -> int: return self._queue_high_water
    @property
    def admitted_count(self) -> int: return len(self._admitted)
    @property
    def task(self) -> asyncio.Task[StreamingSpeakProof] | None: return self._task

    def start(self) -> asyncio.Task[StreamingSpeakProof]:
        if self._task is not None:
            raise StreamingSpeakError("OPERATION_STARTED")
        self._task = asyncio.create_task(self._run(), name="m4c-streaming-speak")
        return self._task

    def _check_identity(self, session_id: str, turn_id: int) -> None:
        if (session_id, turn_id) != (self.session_id, self.turn_id):
            raise StreamingSpeakError("STALE_OPERATION")

    async def feed(self, session_id: str, turn_id: int, sequence: int, text: str) -> None:
        self._check_identity(session_id, turn_id)
        if type(sequence) is not int or sequence < 0:
            raise StreamingSpeakError("FRAGMENT_SEQUENCE")
        if type(text) is not str or not text or "\x00" in text:
            raise StreamingSpeakError("INVALID_FRAGMENT")
        fragment = _Fragment(sequence, text)
        if fragment.size > MAX_PENDING_UTF8_BYTES:
            raise StreamingSpeakError("FRAGMENT_TOO_LARGE")
        async with self._condition:
            while (self._state == "OPEN" and
                   (len(self._pending) >= MAX_PENDING_FRAGMENTS
                    or self._pending_bytes + fragment.size > MAX_PENDING_UTF8_BYTES)):
                await self._condition.wait()
            if self._state != "OPEN":
                raise StreamingSpeakError("ADMISSION_CLOSED")
            if sequence != self._next_sequence:
                raise StreamingSpeakError("FRAGMENT_SEQUENCE")
            self._pending.append(fragment)
            self._pending_bytes += fragment.size
            self._admitted.append(text)
            self._next_sequence += 1
            self._queue_high_water = max(self._queue_high_water, len(self._pending))
            self._condition.notify_all()

    async def finish(self, session_id: str, turn_id: int, terminal_text: str) -> None:
        self._check_identity(session_id, turn_id)
        if type(terminal_text) is not str:
            await self.fail()
            raise StreamingSpeakError("INVALID_TERMINAL")
        admitted = "".join(self._admitted)
        if not terminal_text.startswith(admitted):
            await self.fail()
            raise StreamingSpeakError("TERMINAL_PREFIX_MISMATCH")
        remainder = terminal_text[len(admitted):]
        if remainder:
            await self.feed(session_id, turn_id, self._next_sequence, remainder)
        async with self._condition:
            if self._state != "OPEN":
                raise StreamingSpeakError("ADMISSION_CLOSED")
            self._terminal_text = terminal_text
            self._state = "TERMINAL_VALID"
            self._condition.notify_all()

    async def adopt(self, session_id: str, turn_id: int, correlation_id: int,
                    terminal_text: str) -> None:
        self._check_identity(session_id, turn_id)
        if (type(correlation_id) is not int or correlation_id <= 0
                or terminal_text != self._terminal_text
                or self._adopted_correlation is not None):
            raise StreamingSpeakError("ADOPTION_MISMATCH")
        self._adopted_correlation = correlation_id
        self._adopted.set()

    async def wait(self) -> StreamingSpeakProof:
        if self._task is None:
            raise StreamingSpeakError("OPERATION_NOT_STARTED")
        return await asyncio.shield(self._task)

    async def cancel(self) -> None:
        async with self._condition:
            if self._state in {"COMPLETED", "CANCELLED", "FAILED"}:
                return
            self._state = "CANCELLED"
            self._pending.clear()
            self._pending_bytes = 0
            self._condition.notify_all()
        task = self._task
        if task is not None and not task.done():
            task.cancel()
        await self._tts.abort()
        if task is not None:
            await asyncio.gather(task, return_exceptions=True)
        await self._close_pcm()
        self._inflight = ()

    async def close_unused(self) -> None:
        async with self._condition:
            if self._admitted or self._inflight or self._pending:
                raise StreamingSpeakError("CONTROL_NOT_UNUSED")
            if self._state != "OPEN":
                raise StreamingSpeakError("ADMISSION_CLOSED")
            self._state = "CANCELLED"
            self._condition.notify_all()
        task = self._task
        if task is not None:
            await asyncio.gather(task, return_exceptions=True)

    async def fail(self) -> None:
        async with self._condition:
            if self._state in {"COMPLETED", "CANCELLED", "FAILED"}:
                return
            self._state = "FAILED"
            self._pending.clear()
            self._pending_bytes = 0
            self._condition.notify_all()
        task = self._task
        if task is not None and not task.done():
            task.cancel()
        await self._tts.abort()
        if task is not None:
            await asyncio.gather(task, return_exceptions=True)
        await self._close_pcm()
        self._inflight = ()

    async def force_abort(self) -> ForceAbortReport:
        await self.cancel()
        return await self._tts.force_abort()

    async def _dequeue(self) -> tuple[_Fragment, ...] | None:
        async with self._condition:
            while True:
                if self._state in {"CANCELLED", "FAILED"}:
                    raise asyncio.CancelledError
                if self._pending:
                    values = [self._pending.popleft()]
                    if self._pending:
                        values.append(self._pending.popleft())
                    for value in values:
                        self._pending_bytes -= value.size
                    self._inflight = tuple(values)
                    self._condition.notify_all()
                    return self._inflight
                if self._state == "TERMINAL_VALID":
                    return None
                await self._condition.wait()

    async def _run(self) -> StreamingSpeakProof:
        try:
            first_batch = True
            while True:
                batch = await self._dequeue()
                if batch is None:
                    break
                if first_batch and self._before_start is not None:
                    started = self._before_start()
                    if inspect.isawaitable(started):
                        await started
                first_batch = False
                text = "".join(fragment.text for fragment in batch)
                self._pcm = self._tts.synthesize(text)
                playback = self._observed_pcm(self._pcm)
                try:
                    await self._audio_output.play(playback)
                finally:
                    await playback.aclose()
                    await self._close_pcm()
                self._acknowledged.extend(fragment.text for fragment in batch)
                self._inflight = ()
            terminal = self._terminal_text
            if terminal is None or "".join(self._acknowledged) != terminal:
                raise StreamingSpeakError("SPOKEN_TEXT_MISMATCH")
            await self._adopted.wait()
            correlation_id = self._adopted_correlation
            assert correlation_id is not None
            await self._bus.publish(ActionCompleted(
                "speak", "ok", {}, self.session_id, self.turn_id, correlation_id))
            self._state = "COMPLETED"
            encoded = terminal.encode("utf-8")
            return StreamingSpeakProof(
                len(self._admitted), len(encoded), hashlib.sha256(encoded).hexdigest(),
                self._queue_high_water)
        except asyncio.CancelledError:
            raise
        except ComponentSystemFault as error:
            if await self._finish_worker_failure():
                await self._bus.publish(error.to_event())
            raise
        except AdapterError as error:
            if await self._finish_worker_failure():
                fault = ComponentSystemFault.create(
                    where="action.speak.tts", code="TTS_GENERATION_FAILED",
                    backend=BackendDisposition.REBUILD_REQUIRED,
                    recovery_keys=("backend.action.speak.tts",))
                await self._bus.publish(fault.to_event())
            raise
        except BaseException as error:
            if await self._finish_worker_failure():
                fault = ComponentSystemFault.create(
                    where="action.speak.audio", code="AUDIO_PLAYBACK_FAILED",
                    backend=BackendDisposition.UNPROVEN,
                    recovery_keys=("core.audio.output",))
                await self._bus.publish(fault.to_event())
            raise
        finally:
            await self._close_pcm()

    async def _finish_worker_failure(self) -> bool:
        """Drop all operation-owned work before exposing a worker fault."""
        async with self._condition:
            publish = self._state not in {"CANCELLED", "FAILED"}
            if publish:
                self._state = "FAILED"
            self._pending.clear()
            self._pending_bytes = 0
            self._inflight = ()
            self._condition.notify_all()
        await self._close_pcm()
        return publish

    async def _observed_pcm(self, source):
        first = True
        async for chunk in source:
            if first and type(chunk) is bytes and chunk:
                first = False
                if self._observe is not None:
                    self._observe("tts_pcm_ready")
            yield chunk

    async def _close_pcm(self) -> None:
        pcm, self._pcm = self._pcm, None
        if pcm is not None:
            await pcm.aclose()


__all__ = ["MAX_PENDING_FRAGMENTS", "MAX_PENDING_UTF8_BYTES",
           "StreamingSpeakControl", "StreamingSpeakError", "StreamingSpeakProof"]
