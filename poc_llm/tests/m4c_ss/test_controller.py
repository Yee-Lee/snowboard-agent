from __future__ import annotations

import asyncio
import hashlib
import unittest

from poc_llm.m4c_ss.controller import FragmentChannel, FragmentChannelError


OPERATION = "session-1:turn-1:correlation-1"


class FragmentChannelTests(unittest.IsolatedAsyncioTestCase):
    async def test_c01_one_fragment_matching_terminal_completes_once(self):
        subject = FragmentChannel(OPERATION)
        await subject.feed(OPERATION, 0, "我是雪板。")
        await subject.finish(OPERATION, "我是雪板。")
        fragment = await subject.receive()
        self.assertEqual((fragment.sequence, fragment.text), (0, "我是雪板。"))
        await subject.acknowledge(OPERATION, 0)
        self.assertIsNone(await subject.receive())
        proof = await subject.complete(OPERATION)
        self.assertEqual(proof.fragment_count, 1)
        self.assertEqual(
            proof.normalized_text_sha256,
            hashlib.sha256("我是雪板。".encode()).hexdigest(),
        )
        with self.assertRaisesRegex(FragmentChannelError, "TERMINAL_NOT_VALID"):
            await subject.complete(OPERATION)

    async def test_c02_multiple_fragments_preserve_order(self):
        subject = FragmentChannel(OPERATION)
        parts = ["我是雪板，", "很高興為您服務！"]
        for sequence, text in enumerate(parts):
            await subject.feed(OPERATION, sequence, text)
        await subject.finish(OPERATION, "".join(parts))
        for sequence, text in enumerate(parts):
            fragment = await subject.receive()
            self.assertEqual((fragment.sequence, fragment.text), (sequence, text))
            await subject.acknowledge(OPERATION, sequence)
        self.assertEqual((await subject.complete(OPERATION)).fragment_count, 2)

    async def test_c03_third_fragment_backpressures_without_drop(self):
        subject = FragmentChannel(OPERATION)
        await subject.feed(OPERATION, 0, "一")
        await subject.feed(OPERATION, 1, "二")
        third = asyncio.create_task(subject.feed(OPERATION, 2, "三"))
        await asyncio.sleep(0)
        self.assertFalse(third.done())
        self.assertEqual(subject.pending_count, 2)
        first = await subject.receive()
        await asyncio.wait_for(third, 0.1)
        self.assertEqual(subject.pending_count, 2)
        await subject.acknowledge(OPERATION, first.sequence)
        await subject.finish(OPERATION, "一二三")
        for expected in ("二", "三"):
            fragment = await subject.receive()
            self.assertEqual(fragment.text, expected)
            await subject.acknowledge(OPERATION, fragment.sequence)
        self.assertEqual((await subject.complete(OPERATION)).normalized_utf8_bytes, 9)

    async def test_c04_invalid_terminal_closes_and_discards_pending(self):
        subject = FragmentChannel(OPERATION)
        await subject.feed(OPERATION, 0, "已播放")
        active = await subject.receive()
        with self.assertRaisesRegex(FragmentChannelError, "INVALID_TERMINAL"):
            await subject.finish(OPERATION, "", semantic_valid=False)
        self.assertEqual(subject.state, "FAILED")
        self.assertEqual(subject.pending_count, 0)
        with self.assertRaisesRegex(FragmentChannelError, "OPERATION_CLOSED"):
            await subject.acknowledge(OPERATION, active.sequence)
        with self.assertRaisesRegex(FragmentChannelError, "CLEANUP_NOT_CONVERGED"):
            await subject.cleanup_proof(OPERATION)
        await subject.abort_inflight(OPERATION, active.sequence)
        self.assertEqual((await subject.cleanup_proof(OPERATION)).terminal_state, "FAILED")

    async def test_c05_terminal_prefix_mismatch_fails_closed(self):
        subject = FragmentChannel(OPERATION)
        await subject.feed(OPERATION, 0, "已播放")
        with self.assertRaisesRegex(FragmentChannelError, "TERMINAL_PREFIX_MISMATCH"):
            await subject.finish(OPERATION, "不同文字")
        self.assertEqual(subject.state, "FAILED")

    async def test_c06_post_terminal_fragment_is_rejected(self):
        subject = FragmentChannel(OPERATION)
        await subject.feed(OPERATION, 0, "完成")
        await subject.finish(OPERATION, "完成")
        with self.assertRaisesRegex(FragmentChannelError, "ADMISSION_CLOSED"):
            await subject.feed(OPERATION, 1, "太晚")

    async def test_cancel_clears_queue_and_prevents_success(self):
        subject = FragmentChannel(OPERATION)
        await subject.feed(OPERATION, 0, "active")
        active = await subject.receive()
        await subject.feed(OPERATION, 1, "queued")
        await subject.cancel(OPERATION)
        self.assertEqual(subject.state, "CANCELLED")
        self.assertEqual((subject.pending_count, subject.pending_utf8_bytes), (0, 0))
        with self.assertRaisesRegex(FragmentChannelError, "OPERATION_CLOSED"):
            await subject.acknowledge(OPERATION, active.sequence)
        with self.assertRaisesRegex(FragmentChannelError, "CLEANUP_NOT_CONVERGED"):
            await subject.cleanup_proof(OPERATION)
        await subject.abort_inflight(OPERATION, active.sequence)
        cleanup = await subject.cleanup_proof(OPERATION)
        self.assertTrue(cleanup.queue_empty and cleanup.no_inflight_fragment)
        with self.assertRaisesRegex(FragmentChannelError, "TERMINAL_NOT_VALID"):
            await subject.complete(OPERATION)

    async def test_cancel_releases_backpressured_producer_without_admission(self):
        subject = FragmentChannel(OPERATION)
        await subject.feed(OPERATION, 0, "一")
        await subject.feed(OPERATION, 1, "二")
        blocked = asyncio.create_task(subject.feed(OPERATION, 2, "三"))
        await asyncio.sleep(0)
        await subject.cancel(OPERATION)
        with self.assertRaisesRegex(FragmentChannelError, "ADMISSION_CLOSED"):
            await blocked
        self.assertEqual(subject.pending_count, 0)

    async def test_duplicate_out_of_order_empty_and_oversize_are_rejected(self):
        subject = FragmentChannel(OPERATION)
        with self.assertRaisesRegex(FragmentChannelError, "INVALID_FRAGMENT"):
            await subject.feed(OPERATION, 0, "")
        with self.assertRaisesRegex(FragmentChannelError, "FRAGMENT_SEQUENCE"):
            await subject.feed(OPERATION, 1, "out of order")
        await subject.feed(OPERATION, 0, "first")
        with self.assertRaisesRegex(FragmentChannelError, "FRAGMENT_SEQUENCE"):
            await subject.feed(OPERATION, 0, "duplicate")
        other = FragmentChannel("large")
        with self.assertRaisesRegex(FragmentChannelError, "FRAGMENT_TOO_LARGE"):
            await other.feed("large", 0, "界" * 86)

    async def test_c10_stale_callback_cannot_enter_new_operation(self):
        old = FragmentChannel("old")
        await old.cancel("old")
        new = FragmentChannel("new")
        with self.assertRaisesRegex(FragmentChannelError, "STALE_OPERATION"):
            await new.feed("old", 0, "late")
        await new.feed("new", 0, "clean")
        await new.finish("new", "clean")
        fragment = await new.receive()
        await new.acknowledge("new", fragment.sequence)
        self.assertEqual((await new.complete("new")).fragment_count, 1)


if __name__ == "__main__":
    unittest.main()
