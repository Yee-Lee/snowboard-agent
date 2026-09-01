import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from asr_r1.m1_lifecycle import run_lifecycle


class LifecycleBackend:
    model_id = "lifecycle-candidate"

    def __init__(self) -> None:
        self.loaded = 0
        self.closed = False
        self.next_stream = 1

    def load_model(self) -> None:
        self.loaded += 1

    def create_stream(self) -> dict:
        stream = {"id": self.next_stream, "chunks": 0, "closed": False}
        self.next_stream += 1
        return stream

    def accept_waveform(self, stream: dict, samples) -> None:
        stream["chunks"] += 1

    def is_ready(self, stream: dict) -> bool:
        return False

    def decode_stream(self, stream: dict) -> None:
        raise AssertionError("fake stream is never ready")

    def get_text(self, stream: dict) -> str:
        return "stable final" if stream["chunks"] else ""

    def input_finished(self, stream: dict) -> None:
        pass

    def close_stream(self, stream: dict) -> None:
        stream["closed"] = True

    def close(self) -> None:
        self.closed = True


class M1LifecycleTest(unittest.TestCase):
    def test_real_backend_contract_is_sanitized_and_complete(self) -> None:
        backend = LifecycleBackend()
        with TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "fixture.wav"
            fixture.touch()
            identity = type(
                "Identity",
                (),
                {
                    "path": fixture,
                    "fixture_id": "asr-clear-002-p0",
                    "duration_seconds": 2.66,
                },
            )()
            chunks = [(0, b"\x00\x00" * 10), (160, b"\x00\x00" * 10)]
            with (
                patch(
                    "asr_r1.m1_lifecycle.verify_controlled_smoke_fixture",
                    return_value=identity,
                ),
                patch("asr_r1.m1_lifecycle._pcm_chunks", return_value=chunks),
            ):
                result = run_lifecycle("lifecycle-candidate", backend, fixture)
        self.assertTrue(result["lifecycle_completed"])
        self.assertTrue(result["checks"]["partial_events_observed"])
        self.assertTrue(result["checks"]["session_isolation_stable"])
        self.assertTrue(result["checks"]["cancel_recovery"])
        self.assertTrue(result["checks"]["typed_error_recovery"])
        self.assertNotIn("stable final", str(result))
        self.assertEqual(1, backend.loaded)
        self.assertTrue(backend.closed)


if __name__ == "__main__":
    unittest.main()
