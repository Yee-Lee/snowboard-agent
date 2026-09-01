import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from asr_r1.m1_streaming_probe import _ttft_ms, run_paced_probe


class PacedBackend:
    model_id = "paced-candidate"

    def __init__(self) -> None:
        self.loaded = 0
        self.closed = False

    def load_model(self) -> None:
        self.loaded += 1

    def create_stream(self) -> dict:
        return {"chunks": 0, "closed": False}

    def accept_waveform(self, stream: dict, samples) -> None:
        stream["chunks"] += 1

    def is_ready(self, stream: dict) -> bool:
        return False

    def decode_stream(self, stream: dict) -> None:
        raise AssertionError("fake stream is never ready")

    def get_text(self, stream: dict) -> str:
        return f"partial-{stream['chunks']}" if stream["chunks"] else ""

    def input_finished(self, stream: dict) -> None:
        pass

    def close_stream(self, stream: dict) -> None:
        stream["closed"] = True

    def close(self) -> None:
        self.closed = True


class M1StreamingProbeTest(unittest.TestCase):
    def test_ttft_uses_stream_speech_start_not_model_load(self) -> None:
        self.assertAlmostEqual(700.0, _ttft_ms(100.0, 200, 100.9))
        with self.assertRaisesRegex(ValueError, "precedes frozen speech start"):
            _ttft_ms(100.0, 200, 100.1)

    def test_paced_probe_reports_sanitized_latency_and_revisions(self) -> None:
        backend = PacedBackend()
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
                    "speech_start_offset_ms": 0,
                    "speech_end_offset_ms": 20,
                },
            )()
            chunks = [(0, b"\x00\x00" * 10), (10, b"\x00\x00" * 10)]
            with (
                patch(
                    "asr_r1.m1_streaming_probe.verify_controlled_smoke_fixture",
                    return_value=identity,
                ),
                patch(
                    "asr_r1.m1_streaming_probe._pcm_chunks",
                    return_value=chunks,
                ),
            ):
                result = run_paced_probe(
                    "paced-candidate", backend, fixture, chunk_duration_ms=10
                )
        self.assertTrue(result["probe_completed"])
        self.assertEqual(2, result["partial_event_count"])
        self.assertEqual(1, result["partial_revision_count"])
        self.assertEqual(0, result["first_partial_audio_timestamp_ms"])
        self.assertGreaterEqual(result["ttft_ms"], 0)
        self.assertEqual(
            "ADAPTER_OBSERVED_FIRST_NONEMPTY_CHANGED_PARTIAL",
            result["ttft_scope"],
        )
        self.assertNotIn("first_partial_from_stream_start_ms", result)
        self.assertNotIn("partial-", str(result))
        self.assertEqual(1, backend.loaded)
        self.assertTrue(backend.closed)


if __name__ == "__main__":
    unittest.main()
