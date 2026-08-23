from __future__ import annotations

import asyncio
import argparse
import tempfile
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc.m3_core_hal import (  # noqa: E402
    HAL_FRAME_BYTES,
    capture_frames,
    iter_pcm_chunks,
    play_stream_pcm,
    read_stream_wav,
    write_stream_wav,
)
from audio_poc.m3_formal_hal import (  # noqa: E402
    _require_outside_repo,
    assert_network_isolated,
    cleanup_delta,
    run_hal_lifecycle,
    validate_case_identity,
)
from audio_poc.m3_asr import _level  # noqa: E402
from audio_poc.m3_candidate_lifecycle import run_candidate_lifecycle  # noqa: E402
from audio_poc.m3_vad_worker import bounded_payload  # noqa: E402
from audio_poc.m3_tts_playback import run_matcha_playback  # noqa: E402


class _InputStream:
    def __init__(self, frames: list[bytes], fail_at: int | None = None) -> None:
        self.frames = frames
        self.index = 0
        self.fail_at = fail_at
        self.closed = 0

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        if self.fail_at == self.index:
            raise OSError("capture failure")
        if self.index >= len(self.frames):
            raise StopAsyncIteration
        frame = self.frames[self.index]
        self.index += 1
        return frame

    async def aclose(self) -> None:
        self.closed += 1


class _Input:
    def __init__(self, stream: _InputStream) -> None:
        self.stream = stream
        self.started = 0
        self.stopped = 0

    async def start(self) -> None:
        self.started += 1

    def frames(self) -> _InputStream:
        return self.stream

    async def stop(self) -> None:
        self.stopped += 1


class _Output:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.started = 0
        self.stopped = 0
        self.chunks: list[bytes] = []

    async def start(self) -> None:
        self.started += 1

    async def play(self, chunks) -> None:
        async for chunk in chunks:
            self.chunks.append(chunk)
            if self.fail:
                raise OSError("playback failure")

    async def stop(self) -> None:
        self.stopped += 1


class _AudioFactories:
    def __init__(self) -> None:
        self.inputs: list[_Input] = []
        self.outputs: list[_Output] = []

    def make_audio_input(self, config):
        source = _Input(_InputStream([bytes(HAL_FRAME_BYTES)]))
        if "invalid_input" in str(config.input.device):
            async def fail_start() -> None:
                raise OSError("invalid input")
            source.start = fail_start
        self.inputs.append(source)
        return source

    def make_audio_output(self, config):
        sink = _Output()
        if "invalid_output" in str(config.output.device):
            async def fail_start() -> None:
                raise OSError("invalid output")
            sink.start = fail_start
        self.outputs.append(sink)
        return sink


class M3CoreHalTests(unittest.IsolatedAsyncioTestCase):
    async def test_capture_exact_frames_and_cleanup(self) -> None:
        stream = _InputStream([bytes([index]) * HAL_FRAME_BYTES for index in range(3)])
        source = _Input(stream)
        payload = await capture_frames(source, 3, 1.0)
        self.assertEqual(len(payload), 3 * HAL_FRAME_BYTES)
        self.assertEqual((source.started, source.stopped, stream.closed), (1, 1, 1))

    async def test_capture_failure_still_closes_and_stops(self) -> None:
        stream = _InputStream([bytes(HAL_FRAME_BYTES)], fail_at=1)
        source = _Input(stream)
        with self.assertRaisesRegex(OSError, "capture failure"):
            await capture_frames(source, 2, 1.0)
        self.assertEqual((source.stopped, stream.closed), (1, 1))

    async def test_playback_uses_legal_chunks_and_stops_on_error(self) -> None:
        sink = _Output(fail=True)
        with self.assertRaisesRegex(OSError, "playback failure"):
            await play_stream_pcm(sink, bytes(HAL_FRAME_BYTES * 2), 1.0)
        self.assertEqual((sink.started, sink.stopped), (1, 1))
        self.assertEqual(len(sink.chunks[0]), HAL_FRAME_BYTES)

    async def test_playback_preserves_complete_payload(self) -> None:
        payload = bytes(range(256)) * 7
        sink = _Output()
        await play_stream_pcm(sink, payload, 1.0, samples_per_chunk=7)
        self.assertEqual(b"".join(sink.chunks), payload)
        self.assertTrue(all(len(chunk) % 2 == 0 for chunk in sink.chunks))

    async def test_wav_boundary_is_exact_and_non_overwriting(self) -> None:
        payload = bytes(HAL_FRAME_BYTES * 2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.wav"
            write_stream_wav(path, payload)
            self.assertEqual(read_stream_wav(path), payload)
            with self.assertRaises(FileExistsError):
                write_stream_wav(path, payload)

    async def test_chunk_size_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive integer"):
            list(iter_pcm_chunks(bytes(2), 0))

    async def test_cleanup_delta_reports_only_residue(self) -> None:
        before = {
            "children": {10}, "threads": 3, "tasks": 1,
            "file_descriptors": 5, "device_owners": 0,
        }
        after = {
            "children": {10, 11}, "threads": 4, "tasks": 1,
            "file_descriptors": 7, "device_owners": 1,
        }
        self.assertEqual(cleanup_delta(before, after), {
            "child_processes": 1,
            "threads": 1,
            "tasks": 0,
            "iterators": 0,
            "streams": 0,
            "file_descriptors": 2,
            "device_owners": 1,
        })

    async def test_hal_lifecycle_reopen_and_invalid_devices(self) -> None:
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class Direction:
            device: str

        @dataclass(frozen=True)
        class Config:
            input: Direction
            output: Direction

        config = Config(Direction("hw:0,0"), Direction("hw:0,0"))
        factories = _AudioFactories()
        reopen = await run_hal_lifecycle(factories, config, "reopen-5", 1.0)
        self.assertEqual((reopen["input_cycles"], reopen["output_cycles"]), (5, 5))
        invalid_input = await run_hal_lifecycle(factories, config, "invalid-input", 1.0)
        invalid_output = await run_hal_lifecycle(factories, config, "invalid-output", 1.0)
        self.assertEqual(invalid_input["valid_output_recheck"], "PASS")
        self.assertEqual(invalid_output["valid_input_recheck"], "PASS")

    async def test_matcha_protocol_pcm_is_played_without_resampling(self) -> None:
        factories = _AudioFactories()
        prompts = [
            {"fixture_id": "tts-001", "category": "general", "text": "test one"},
            {"fixture_id": "tts-005", "category": "number", "text": "test two"},
        ]
        records = await run_matcha_playback(
            Path(sys.executable),
            Path("unused-model"),
            Path("unused-vocos"),
            prompts,
            factories,
            SimpleNamespace(
                input=SimpleNamespace(device="hw:0,0"),
                output=SimpleNamespace(device="hw:0,0"),
            ),
            2.0,
            REPO_ROOT / "poc_audio/tests",
            worker_module="m3_tts_protocol_fake",
        )
        self.assertEqual([item["fixture_id"] for item in records], ["tts-001", "tts-005"])
        self.assertTrue(all(item["playback_complete"] for item in records))
        self.assertEqual(len(factories.outputs), 2)
        self.assertEqual([b"".join(sink.chunks) for sink in factories.outputs], [
            bytes.fromhex("00000100ff7f0080"),
            bytes.fromhex("00000100ff7f0080"),
        ])

    async def test_asr_fixture_level_is_sanitized_numeric_metadata(self) -> None:
        import struct

        level = _level(struct.pack("<4h", -32768, -100, 0, 32767))
        self.assertEqual(level["peak_abs_s16"], 32768)
        self.assertEqual(level["clipped_samples"], 2)
        self.assertGreater(level["rms_s16"], 0)

    async def test_vad_bounded_payload_uses_one_exact_interval(self) -> None:
        payload = bytes(range(256)) * 250
        bounded = bounded_payload(payload, [[500, 1500]])
        self.assertEqual(bounded, payload[16_000:48_000])
        with self.assertRaisesRegex(ValueError, "one merged"):
            bounded_payload(payload, [[0, 10], [20, 30]])

    async def test_controlled_paths_must_stay_outside_repo(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside the POC repository"):
            _require_outside_repo(REPO_ROOT / "private.wav", REPO_ROOT, "private WAV")
        with tempfile.TemporaryDirectory() as directory:
            _require_outside_repo(Path(directory) / "private.wav", REPO_ROOT, "private WAV")

    @mock.patch("audio_poc.m3_formal_hal.shutil.which", return_value="/usr/sbin/ip")
    @mock.patch("audio_poc.m3_formal_hal.subprocess.run")
    async def test_network_isolation_requires_only_loopback_down(self, run, _which) -> None:
        run.return_value = SimpleNamespace(
            stdout='[{"ifname":"lo","operstate":"DOWN","flags":["LOOPBACK"]}]'
        )
        self.assertTrue(assert_network_isolated()["network_disabled"])
        run.return_value = SimpleNamespace(
            stdout='[{"ifname":"lo","operstate":"UNKNOWN","flags":["LOOPBACK"]},'
            '{"ifname":"eth0","operstate":"UP","flags":["UP"]}]'
        )
        with self.assertRaisesRegex(RuntimeError, "disabled network namespace"):
            assert_network_isolated()

    @mock.patch("audio_poc.m3_candidate_lifecycle.run_scenario")
    @mock.patch("audio_poc.m3_candidate_lifecycle._asr_cancel")
    @mock.patch("audio_poc.m3_candidate_lifecycle.safe_extract")
    @mock.patch("audio_poc.m3_candidate_lifecycle.verify_candidate_inputs")
    async def test_candidate_cancel_requires_both_real_paths_clean(
        self, _verify, extract, asr_cancel, run_scenario,
    ) -> None:
        asr_cancel.return_value = {
            "active_at_cancel": True,
            "terminal_status": "CANCELLED",
            "duration_ms": 100,
            "cleanup": {"clean": True},
        }
        run_scenario.return_value = {
            "terminal_status": "CANCELLED",
            "duration_ms": 100,
            "cleanup": {"clean": True},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            extract.return_value = root / "model"
            result = run_candidate_lifecycle(
                REPO_ROOT,
                root / "artifacts",
                Path(sys.executable),
                root / "worker",
                root / "asr-model",
                root / "fixtures",
                root / "new-work",
                "cancel",
                10,
            )
        self.assertEqual(result["scenario"], "cancel")

    async def test_formal_case_identity_rejects_lifecycle_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "scenario/test ID mismatch"):
            validate_case_identity(argparse.Namespace(
                mode="candidate-lifecycle",
                test_id="M3-LIFE-06",
                candidate_scenario="cancel",
                lifecycle_scenario=None,
            ))
        validate_case_identity(argparse.Namespace(
            mode="hal-lifecycle",
            test_id="M3-LIFE-03",
            candidate_scenario=None,
            lifecycle_scenario="invalid-input",
        ))


if __name__ == "__main__":
    unittest.main()
