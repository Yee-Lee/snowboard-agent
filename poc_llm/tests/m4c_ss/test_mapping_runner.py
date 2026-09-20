from __future__ import annotations

import unittest

from poc_llm.m4c_ss.mapping import B1, B2
from poc_llm.m4c_ss.mapping_runner import run_mapping_trace


class FakeManagedBackend:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.active = False
        self.requests: list[str] = []

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True
        self.started = False
        self.active = False

    async def speak(self, text: str) -> None:
        self.active = True
        self.requests.append(text)
        self.active = False

    async def abort(self) -> None:
        self.active = False

    async def force_abort(self) -> None:
        self.active = False

    def operation_idle(self) -> bool:
        return not self.active


class MappingRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_b1_preserves_three_sequential_requests(self):
        backend = FakeManagedBackend()
        result = await run_mapping_trace(trace_id="T02", candidate=B1, backend=backend)
        self.assertEqual(backend.requests, [
            "因為太陽光穿過大氣，", "藍光被散射，", "所以天空看起來是藍色的。",
        ])
        self.assertEqual((result.fragment_count, result.tts_request_count), (3, 3))
        self.assertTrue(backend.stopped)

    async def test_b2_uses_only_one_available_lookahead(self):
        backend = FakeManagedBackend()
        result = await run_mapping_trace(trace_id="T02", candidate=B2, backend=backend)
        self.assertEqual(backend.requests, [
            "因為太陽光穿過大氣，藍光被散射，", "所以天空看起來是藍色的。",
        ])
        self.assertEqual((result.fragment_count, result.tts_request_count), (3, 2))
        self.assertTrue(backend.stopped)

    async def test_invalid_trace_does_not_start_backend(self):
        backend = FakeManagedBackend()
        with self.assertRaisesRegex(ValueError, "UNKNOWN_MAPPING_TRACE"):
            await run_mapping_trace(trace_id="T99", candidate=B1, backend=backend)
        self.assertFalse(backend.started or backend.stopped)


if __name__ == "__main__":
    unittest.main()
