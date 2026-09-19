from __future__ import annotations

import asyncio
import unittest

from poc_llm.m4c_ss.controller import FragmentChannelError
from poc_llm.m4c_ss.mapping import B1
from poc_llm.m4c_ss.operation import StreamingSpeakOperation


class ControlledBackend:
    def __init__(self, *, fail: bool = False, abort_hangs: bool = False) -> None:
        self.fail = fail
        self.abort_hangs = abort_hangs
        self.entered = asyncio.Event()
        self.playing = asyncio.Event()
        self.release = asyncio.Event()
        self.idle = True
        self.force_count = 0

    async def speak(self, text: str) -> None:
        self.idle = False
        self.entered.set()
        await asyncio.sleep(0)
        self.playing.set()
        if self.fail:
            self.idle = True
            raise RuntimeError("stable fake failure")
        await self.release.wait()
        self.idle = True

    async def abort(self) -> None:
        if self.abort_hangs:
            await asyncio.Event().wait()
        self.release.set()
        self.idle = True

    async def force_abort(self) -> None:
        self.force_count += 1
        self.release.set()
        self.idle = True

    def operation_idle(self) -> bool:
        return self.idle


class OperationTests(unittest.IsolatedAsyncioTestCase):
    async def test_normal_completion_waits_for_terminal_and_playback(self):
        backend = ControlledBackend()
        subject = StreamingSpeakOperation("op", candidate=B1, backend=backend)
        run = asyncio.create_task(subject.run())
        await subject.feed(0, "完成。")
        await subject.finish("完成。")
        await backend.playing.wait()
        self.assertFalse(run.done())
        backend.release.set()
        result = await run
        self.assertTrue(result.normal_success)
        self.assertEqual(result.terminal_proof.fragment_count, 1)

    async def test_c07_interrupt_queued_converges_without_backend_start(self):
        backend = ControlledBackend()
        subject = StreamingSpeakOperation("op", candidate=B1, backend=backend)
        await subject.feed(0, "queued")
        result = await subject.interrupt()
        self.assertFalse(result.normal_success)
        self.assertTrue(result.backend_idle)
        self.assertFalse(backend.entered.is_set())

    async def test_c07_interrupt_during_synthesis_or_playback_converges(self):
        for wait_for in ("entered", "playing"):
            with self.subTest(wait_for=wait_for):
                backend = ControlledBackend()
                subject = StreamingSpeakOperation("op-" + wait_for, candidate=B1, backend=backend)
                run = asyncio.create_task(subject.run())
                await subject.feed(0, "active")
                await getattr(backend, wait_for).wait()
                result = await subject.interrupt()
                self.assertFalse(result.normal_success)
                self.assertTrue(result.cleanup_proof.no_inflight_fragment)
                self.assertEqual((await run).status, "CANCELLED")

    async def test_c08_shutdown_uses_same_zero_owner_boundary(self):
        backend = ControlledBackend()
        subject = StreamingSpeakOperation("op", candidate=B1, backend=backend)
        run = asyncio.create_task(subject.run())
        await subject.feed(0, "active")
        await backend.playing.wait()
        result = await subject.shutdown()
        self.assertEqual(result.status, "CANCELLED")
        self.assertTrue(result.backend_idle)
        await run

    async def test_c09_backend_error_never_becomes_success(self):
        backend = ControlledBackend(fail=True)
        subject = StreamingSpeakOperation("op", candidate=B1, backend=backend)
        run = asyncio.create_task(subject.run())
        await subject.feed(0, "failure")
        result = await run
        self.assertEqual(result.status, "FAILED")
        self.assertFalse(result.normal_success)

    async def test_c09_abort_timeout_escalates_to_force_abort(self):
        backend = ControlledBackend(abort_hangs=True)
        subject = StreamingSpeakOperation(
            "op", candidate=B1, backend=backend,
            abort_timeout_s=0.01, force_abort_timeout_s=0.1,
        )
        run = asyncio.create_task(subject.run())
        await subject.feed(0, "active")
        await backend.entered.wait()
        result = await subject.interrupt()
        self.assertTrue(result.force_abort_used)
        self.assertEqual(backend.force_count, 1)
        await run

    async def test_c09_speak_timeout_aborts_without_success(self):
        backend = ControlledBackend()
        subject = StreamingSpeakOperation(
            "op", candidate=B1, backend=backend,
            speak_timeout_s=0.01, abort_timeout_s=0.1,
        )
        run = asyncio.create_task(subject.run())
        await subject.feed(0, "active")
        result = await run
        self.assertEqual(result.status, "FAILED")
        self.assertFalse(result.normal_success)
        self.assertFalse(result.force_abort_used)

    async def test_invalid_terminal_converges_active_backend(self):
        backend = ControlledBackend()
        subject = StreamingSpeakOperation("op", candidate=B1, backend=backend)
        run = asyncio.create_task(subject.run())
        await subject.feed(0, "spoken")
        await backend.playing.wait()
        with self.assertRaisesRegex(FragmentChannelError, "INVALID_TERMINAL"):
            await subject.finish("", semantic_valid=False)
        self.assertFalse((await run).normal_success)


if __name__ == "__main__":
    unittest.main()
