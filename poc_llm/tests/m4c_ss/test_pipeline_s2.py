from __future__ import annotations

import asyncio
import hashlib
import unittest

from poc_llm.efficiency.raw_stream import RawStreamChunk
from poc_llm.m4c_ss.mapping import B1
from poc_llm.m4c_ss.operation import StreamingSpeakOperation
from poc_llm.m4c_ss.pipeline import StreamingSpeakPipeline
from poc_llm.m4c_ss.s2 import S2Error, S2Terminal, consume_raw_s2


class ImmediateBackend:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.idle = True

    async def speak(self, text: str) -> None:
        self.idle = False
        self.spoken.append(text)
        await asyncio.sleep(0)
        self.idle = True

    async def abort(self) -> None:
        self.idle = True

    async def force_abort(self) -> None:
        self.idle = True

    def operation_idle(self) -> bool:
        return self.idle


def terminal(text: str, *, end: bool = False) -> S2Terminal:
    return S2Terminal(text, end, hashlib.sha256(text.encode()).hexdigest(), len(text))


class FakeSource:
    def __init__(self, parts: list[str], final: S2Terminal, *, wait: bool = False, cancel_hangs: bool = False) -> None:
        self.parts = parts
        self.final = final
        self.wait = wait
        self.cancel_hangs = cancel_hangs
        self.release = asyncio.Event()
        self.started = asyncio.Event()
        self.idle = True
        self.force_count = 0

    async def generate(self, emit):
        self.idle = False
        self.started.set()
        try:
            for part in self.parts:
                await emit(part)
            if self.wait:
                await self.release.wait()
                raise asyncio.CancelledError
            return self.final
        finally:
            self.idle = True

    async def cancel(self) -> None:
        if self.cancel_hangs:
            await asyncio.Event().wait()
        self.release.set()

    async def force_abort(self) -> None:
        self.force_count += 1
        self.release.set()

    def operation_idle(self) -> bool:
        return self.idle


class S2Tests(unittest.TestCase):
    def test_release_is_normalized_and_precedes_native_final_marker(self):
        events: list[str] = []

        def chunks():
            yield RawStreamChunk('{"text":"Ａ  答。","end":false}', False)
            events.append("native-final")
            yield RawStreamChunk("", True)

        result = consume_raw_s2(chunks(), on_safe_text=lambda text: events.append("safe:" + text))
        self.assertEqual(result.text, "A 答。")
        self.assertEqual(events, ["safe:A 答。", "native-final"])

    def test_trailing_output_cancels_an_already_released_fragment(self):
        events: list[str] = []
        with self.assertRaisesRegex(S2Error, "INVALID_SEMANTIC"):
            consume_raw_s2([
                RawStreamChunk('{"text":"回答。","end":false}', False),
                RawStreamChunk("x", False),
                RawStreamChunk("", True),
            ], on_safe_text=events.append)
        self.assertEqual(events, ["回答。", ""])

    def test_missing_native_terminal_is_rejected(self):
        with self.assertRaisesRegex(S2Error, "MISSING_TERMINAL"):
            consume_raw_s2([
                RawStreamChunk('{"text":"回答。","end":false}', False),
            ], on_safe_text=lambda _text: None)


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_b_streams_safe_text_into_one_operation(self):
        backend = ImmediateBackend()
        source = FakeSource(["前段，", "後段。"], terminal("前段，後段。"))
        operation = StreamingSpeakOperation("op", candidate=B1, backend=backend)
        result = await StreamingSpeakPipeline(source=source, operation=operation).execute()
        self.assertTrue(result.operation.normal_success)
        self.assertEqual(backend.spoken, ["前段，", "後段。"])
        self.assertTrue(result.source_idle)

    async def test_a_withholds_safe_text_until_terminal(self):
        backend = ImmediateBackend()
        source = FakeSource(["前段，", "後段。"], terminal("前段，後段。"))
        operation = StreamingSpeakOperation("op", candidate=B1, backend=backend)
        result = await StreamingSpeakPipeline(
            source=source, operation=operation, mode="A",
        ).execute()
        self.assertTrue(result.operation.normal_success)
        self.assertEqual(backend.spoken, ["前段，後段。"])

    async def test_generation_failure_converges_speech_without_success(self):
        class FailedSource(FakeSource):
            async def generate(self, emit):
                self.idle = False
                try:
                    await emit("已送出。")
                    raise RuntimeError("stable fake failure")
                finally:
                    self.idle = True

        backend = ImmediateBackend()
        source = FailedSource([], terminal(""))
        operation = StreamingSpeakOperation("op", candidate=B1, backend=backend)
        result = await StreamingSpeakPipeline(source=source, operation=operation).execute()
        self.assertEqual(result.operation.status, "FAILED")
        self.assertFalse(result.operation.normal_success)

    async def test_interrupt_cancels_generation_and_rejects_success(self):
        backend = ImmediateBackend()
        source = FakeSource(["前段，"], terminal("前段，"), wait=True)
        operation = StreamingSpeakOperation("op", candidate=B1, backend=backend)
        pipeline = StreamingSpeakPipeline(source=source, operation=operation)
        running = asyncio.create_task(pipeline.execute())
        await source.started.wait()
        result = await pipeline.interrupt()
        self.assertEqual(result.operation.status, "CANCELLED")
        self.assertFalse(result.operation.normal_success)
        await running

    async def test_cancel_timeout_uses_bounded_source_force_abort(self):
        backend = ImmediateBackend()
        source = FakeSource([], terminal(""), wait=True, cancel_hangs=True)
        operation = StreamingSpeakOperation("op", candidate=B1, backend=backend)
        pipeline = StreamingSpeakPipeline(
            source=source,
            operation=operation,
            cancel_timeout_s=0.01,
            force_abort_timeout_s=0.1,
        )
        running = asyncio.create_task(pipeline.execute())
        await source.started.wait()
        result = await pipeline.interrupt()
        self.assertTrue(result.source_force_abort_used)
        self.assertEqual(source.force_count, 1)
        await running


if __name__ == "__main__":
    unittest.main()
