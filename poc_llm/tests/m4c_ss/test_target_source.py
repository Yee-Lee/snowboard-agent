from __future__ import annotations

import asyncio
import threading
import unittest

from poc_llm.efficiency.raw_stream import RawStreamChunk, RawStreamError
from poc_llm.m4c_ss.target_source import RawS2Source


class TargetSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_callback_waits_for_async_admission(self):
        callback_entered = threading.Event()
        callback_released = threading.Event()

        def chunks():
            yield RawStreamChunk('{"text":"回答。","end":false}', False)
            callback_released.set()
            yield RawStreamChunk("", True)

        source = RawS2Source(
            chunk_factory=chunks,
            cancel_hook=lambda: None,
            force_abort_hook=lambda: None,
        )
        admit = asyncio.Event()

        async def emit(text: str) -> None:
            self.assertEqual(text, "回答。")
            callback_entered.set()
            await admit.wait()

        running = asyncio.create_task(source.generate(emit))
        await asyncio.to_thread(callback_entered.wait, 1)
        self.assertFalse(callback_released.is_set())
        admit.set()
        result = await running
        self.assertEqual(result.text, "回答。")
        self.assertTrue(callback_released.is_set())
        self.assertTrue(source.operation_idle())

    async def test_cancel_hook_unblocks_native_source(self):
        cancelled = threading.Event()

        def chunks():
            cancelled.wait(1)
            raise RawStreamError("CANCELLED")
            yield  # pragma: no cover

        source = RawS2Source(
            chunk_factory=chunks,
            cancel_hook=cancelled.set,
            force_abort_hook=cancelled.set,
        )
        running = asyncio.create_task(source.generate(lambda _text: asyncio.sleep(0)))
        await asyncio.sleep(0)
        await source.cancel()
        with self.assertRaisesRegex(Exception, "CANCELLED"):
            await running
        self.assertTrue(source.operation_idle())

    async def test_source_is_single_use(self):
        source = RawS2Source(
            chunk_factory=lambda: iter([
                RawStreamChunk('{"text":"回答。","end":false}', False),
                RawStreamChunk("", True),
            ]),
            cancel_hook=lambda: None,
            force_abort_hook=lambda: None,
        )
        await source.generate(lambda _text: asyncio.sleep(0))
        with self.assertRaisesRegex(RuntimeError, "NOT_REUSABLE"):
            await source.generate(lambda _text: asyncio.sleep(0))


if __name__ == "__main__":
    unittest.main()
