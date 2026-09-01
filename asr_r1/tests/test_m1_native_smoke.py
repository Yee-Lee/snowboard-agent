import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from asr_r1.m1_native_smoke import run_native_smoke


class NativeBackend:
    model_id = "native-candidate"

    def __init__(self) -> None:
        self.loaded = 0
        self.closed = False
        self.decoded = False

    def load_model(self) -> None:
        self.loaded += 1

    def create_stream(self) -> dict:
        return {"chunks": 0, "ready": False, "closed": False}

    def accept_waveform(self, stream: dict, samples) -> None:
        stream["chunks"] += 1
        stream["ready"] = True

    def is_ready(self, stream: dict) -> bool:
        return stream["ready"]

    def decode_stream(self, stream: dict) -> None:
        stream["ready"] = False
        self.decoded = True

    def get_text(self, stream: dict) -> str:
        return f"native-{stream['chunks']}" if self.decoded else ""

    def input_finished(self, stream: dict) -> None:
        stream["ready"] = True

    def close_stream(self, stream: dict) -> None:
        stream["closed"] = True

    def close(self) -> None:
        self.closed = True


class FailingNativeBackend(NativeBackend):
    def accept_waveform(self, stream: dict, samples) -> None:
        raise RuntimeError("decode failed")


class M1NativeSmokeTest(unittest.TestCase):
    def test_native_failure_closes_stream_and_backend(self) -> None:
        backend = FailingNativeBackend()
        with TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "fixture.wav"
            fixture.touch()
            identity = type(
                "Identity",
                (),
                {
                    "path": fixture,
                    "fixture_id": "asr-clear-002-p0",
                    "duration_seconds": 0.02,
                },
            )()
            with (
                patch(
                    "asr_r1.m1_native_smoke.verify_controlled_smoke_fixture",
                    return_value=identity,
                ),
                patch(
                    "asr_r1.m1_native_smoke._pcm_chunks",
                    return_value=[(0, b"\x00\x00" * 10)],
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "decode failed"):
                    run_native_smoke("native-candidate", backend, fixture)
        self.assertTrue(backend.closed)

    def test_native_backend_smoke_is_sanitized(self) -> None:
        backend = NativeBackend()
        with TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "fixture.wav"
            fixture.touch()
            identity = type(
                "Identity",
                (),
                {
                    "path": fixture,
                    "fixture_id": "asr-clear-002-p0",
                    "duration_seconds": 0.02,
                },
            )()
            chunks = [(0, b"\x00\x00" * 10), (10, b"\x00\x00" * 10)]
            with (
                patch(
                    "asr_r1.m1_native_smoke.verify_controlled_smoke_fixture",
                    return_value=identity,
                ),
                patch(
                    "asr_r1.m1_native_smoke._pcm_chunks",
                    return_value=chunks,
                ),
            ):
                result = run_native_smoke("native-candidate", backend, fixture)
        self.assertTrue(result["native_smoke_completed"])
        self.assertGreaterEqual(result["full_utterance_rtf"], 0)
        self.assertGreaterEqual(result["full_utterance_decode_wall_seconds"], 0)
        self.assertNotIn("rtf", result)
        self.assertGreaterEqual(result["partial_event_count"], 1)
        self.assertNotIn("native-1", str(result))
        self.assertNotIn("native-2", str(result))
        self.assertEqual(1, backend.loaded)
        self.assertTrue(backend.closed)


if __name__ == "__main__":
    unittest.main()
