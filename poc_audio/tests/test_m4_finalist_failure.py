from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc.m4_finalist_failure import FinalistFailureAdapter  # noqa: E402
from audio_poc.m4_formal import _prepare_failure_executor  # noqa: E402


class Domain:
    def __init__(self, complete_early: bool = False) -> None:
        self.complete_early = complete_early
        self.active = False
        self.abort = False

    async def start(self) -> None:
        self.active = True

    async def run(self, session: dict[str, object]) -> dict[str, object]:
        if self.complete_early:
            return {"terminal": "SUCCESS"}
        while not self.abort:
            await __import__("asyncio").sleep(0.005)
        raise RuntimeError("aborted")

    async def stop(self) -> None:
        self.active = False

    async def inject_error(self) -> None:
        if not self.active:
            raise RuntimeError("not active")

    async def abort_active(self) -> None:
        self.abort = True


class FinalistFailureAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_failure_executor_exists_before_case_cleanup_baseline(self) -> None:
        replacement = mock.AsyncMock(return_value=0)
        with mock.patch("audio_poc.m4_formal.asyncio.to_thread", replacement):
            await _prepare_failure_executor()
        self.assertEqual(replacement.await_count, 2)

    async def test_actual_error_timeout_cancel_and_controlled_abort(self) -> None:
        # Process startup is not the behavior under test and can exceed 200 ms
        # when the complete regression suite is contending for the workstation.
        adapter = FinalistFailureAdapter("vad", Domain, 0.01, 1.0)
        error = await adapter.inject("error", {})
        self.assertEqual(error["terminal_status"], "ERROR")
        for scenario, terminal in (("timeout", "TIMEOUT"), ("cancel", "CANCELLED")):
            result = await adapter.inject(scenario, {})
            self.assertEqual(result["terminal_status"], terminal)
            self.assertEqual(result["injection_source"], "ACTUAL_FINALIST")
        aborted = await adapter.inject("force_abort", {})
        self.assertTrue(aborted["force_abort_used"])
        self.assertEqual(aborted["injection_source"], "CONTROLLED_FORCE_ABORT_DOUBLE")

    async def test_early_completion_cannot_be_claimed_as_cancel(self) -> None:
        adapter = FinalistFailureAdapter("asr", lambda: Domain(complete_early=True), 0.01, 0.2)
        with self.assertRaisesRegex(RuntimeError, "completed before cancel"):
            await adapter.inject("cancel", {})


if __name__ == "__main__":
    unittest.main()
