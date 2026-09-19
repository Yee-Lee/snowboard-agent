"""Async backpressure bridge over the frozen LiteRT raw-stream seam."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
import threading

from poc_llm.efficiency.raw_stream import RawStreamChunk
from poc_llm.m4c_ss.s2 import S2Terminal, consume_raw_s2


class RawS2Source:
    """Adapt a blocking native iterator without buffering model fragments.

    ``chunk_factory`` is invoked exactly once.  Its callback blocks the native
    producer until the bounded async channel admits the fragment, so queue
    pressure reaches the LiteRT read loop instead of creating another list or
    task.  Target wiring supplies the existing native cancel and process-group
    force-abort hooks.
    """

    def __init__(
        self,
        *,
        chunk_factory: Callable[[], Iterable[RawStreamChunk]],
        cancel_hook: Callable[[], None],
        force_abort_hook: Callable[[], None],
    ) -> None:
        self._chunk_factory = chunk_factory
        self._cancel_hook = cancel_hook
        self._force_abort_hook = force_abort_hook
        self._lock = threading.Lock()
        self._active = False
        self._used = False

    async def generate(
        self, on_safe_text: Callable[[str], Awaitable[None]],
    ) -> S2Terminal:
        with self._lock:
            if self._used or self._active:
                raise RuntimeError("SOURCE_NOT_REUSABLE")
            self._used = True
            self._active = True
        loop = asyncio.get_running_loop()

        def consume() -> S2Terminal:
            def emit(text: str) -> None:
                if not text:
                    return
                future = asyncio.run_coroutine_threadsafe(on_safe_text(text), loop)
                future.result()

            return consume_raw_s2(self._chunk_factory(), on_safe_text=emit)

        try:
            return await asyncio.to_thread(consume)
        finally:
            with self._lock:
                self._active = False

    async def cancel(self) -> None:
        await asyncio.to_thread(self._cancel_hook)

    async def force_abort(self) -> None:
        await asyncio.to_thread(self._force_abort_hook)

    def operation_idle(self) -> bool:
        with self._lock:
            return not self._active
