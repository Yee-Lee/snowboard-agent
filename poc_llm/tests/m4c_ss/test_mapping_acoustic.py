from __future__ import annotations

import array
from pathlib import Path
import stat
import tempfile
import unittest

from poc_llm.m4c_ss.capture import CaptureRecording
from poc_llm.m4c_ss.duplex import CAPTURE_PERIOD_FRAMES, CaptureBlock
from poc_llm.m4c_ss.mapping import B1
from poc_llm.m4c_ss.mapping_acoustic import run_acoustic_mapping_trace


class FakeBackend:
    def __init__(self) -> None:
        self.active = False
        self.requests = []

    async def start(self):
        pass

    async def stop(self):
        self.active = False

    async def speak(self, text):
        self.active = True
        self.requests.append(text)
        self.active = False

    async def abort(self):
        self.active = False

    async def force_abort(self):
        self.active = False

    def operation_idle(self):
        return not self.active


class FakeCapture:
    def __init__(self) -> None:
        self.started = False
        values = [10] * 30 + [1200] * 5 + [10] * 5
        self.blocks = tuple(
            CaptureBlock(
                (index + 1) * 10_000_000,
                array.array("h", [value] * CAPTURE_PERIOD_FRAMES).tobytes(),
            )
            for index, value in enumerate(values)
        )

    def start(self, *, minimum_baseline_blocks=30, timeout_s=2.0):
        self.started = True

    def stop(self):
        return CaptureRecording(
            blocks=self.blocks,
            pcm_s16le=b"".join(block.pcm_s16le for block in self.blocks),
            owner_stopped=True,
        )


class ClickThenSpeechCapture(FakeCapture):
    def __init__(self) -> None:
        self.started = False
        values = [10] * 30 + [1200] * 3 + [10] * 3 + [1400] * 4 + [10] * 3
        self.blocks = tuple(
            CaptureBlock(
                (index + 1) * 10_000_000,
                array.array("h", [value] * CAPTURE_PERIOD_FRAMES).tobytes(),
            )
            for index, value in enumerate(values)
        )


class AcousticMappingTests(unittest.IsolatedAsyncioTestCase):
    async def test_runs_mapping_and_writes_private_pcm_once(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "private" / "sample.pcm"
            backend = FakeBackend()
            result = await run_acoustic_mapping_trace(
                trace_id="T01", candidate=B1, backend=backend,
                capture=FakeCapture(), private_pcm_path=output, tail_seconds=0,
            )
            self.assertEqual(result.status, "PASS")
            self.assertEqual(result.mapping.tts_request_count, 2)
            self.assertTrue(output.is_file())
            self.assertEqual(output.stat().st_size, result.private_pcm_bytes)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            with self.assertRaisesRegex(ValueError, "PATH_INVALID"):
                await run_acoustic_mapping_trace(
                    trace_id="T01", candidate=B1, backend=FakeBackend(),
                    capture=FakeCapture(), private_pcm_path=output, tail_seconds=0,
                )

    async def test_onset_is_bounded_by_audio_first_write(self):
        with tempfile.TemporaryDirectory() as directory:
            result = await run_acoustic_mapping_trace(
                trace_id="T01", candidate=B1, backend=FakeBackend(),
                capture=ClickThenSpeechCapture(),
                private_pcm_path=Path(directory) / "sample.pcm",
                tail_seconds=0,
                onset_not_before=lambda: 350_000_000,
            )
            self.assertEqual(result.acoustic.onset_monotonic_ns, 360_000_000)

    async def test_required_audio_first_write_must_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "AUDIO_FIRST_WRITE_MISSING"):
                await run_acoustic_mapping_trace(
                    trace_id="T01", candidate=B1, backend=FakeBackend(),
                    capture=FakeCapture(),
                    private_pcm_path=Path(directory) / "sample.pcm",
                    tail_seconds=0,
                    onset_not_before=lambda: None,
                )


if __name__ == "__main__":
    unittest.main()
