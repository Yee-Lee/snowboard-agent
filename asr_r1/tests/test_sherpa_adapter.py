import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from asr_r1.protocol import ErrorCode, EventKind, PCMChunk, ProtocolError, SessionState
from asr_r1.sherpa_adapter import (
    SherpaOnnxTransducerBackend,
    SherpaOnnxWenetCtcBackend,
    SherpaStreamingRuntime,
)


class FakeBackend:
    model_id = "fake-sherpa"

    def __init__(self) -> None:
        self.loaded = False
        self.closed = False
        self.fail_accept = False
        self.always_ready = False
        self.closed_stream_ids = []
        self._next_stream = 0

    def load_model(self) -> None:
        self.loaded = True

    def create_stream(self) -> dict:
        self._next_stream += 1
        return {"id": self._next_stream, "chunks": 0, "decoded": 0, "finished": False}

    def accept_waveform(self, stream: dict, samples) -> None:
        if self.fail_accept:
            raise RuntimeError("private backend detail")
        self.last_samples = samples
        stream["chunks"] += 1

    def is_ready(self, stream: dict) -> bool:
        return self.always_ready or stream["decoded"] < stream["chunks"]

    def decode_stream(self, stream: dict) -> None:
        stream["decoded"] += 1

    def get_text(self, stream: dict) -> str:
        return f"partial {stream['chunks']}" if stream["chunks"] else ""

    def input_finished(self, stream: dict) -> None:
        stream["finished"] = True

    def close_stream(self, stream: dict) -> None:
        self.closed_stream_ids.append(stream["id"])

    def close(self) -> None:
        self.closed = True


def chunk(session_id: str, sequence: int, timestamp_ms: int) -> PCMChunk:
    return PCMChunk(session_id, sequence, timestamp_ms, b"\x00\x40" * 320)


class SherpaAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = FakeBackend()
        self.runtime = SherpaStreamingRuntime(self.backend)
        self.assertEqual("fake-sherpa", self.runtime.load_model())

    def test_partial_final_and_top_one_fallback(self) -> None:
        session = self.runtime.create_session()
        partial = self.runtime.accept_chunk(chunk(session, 0, 0))
        self.assertIsNotNone(partial)
        self.assertEqual(EventKind.PARTIAL, partial.kind)
        self.assertAlmostEqual(0.5, self.backend.last_samples[0])
        final = self.runtime.finish_input(session, 20)
        self.assertEqual(EventKind.FINAL, final.kind)
        self.assertEqual(final.text, final.alternatives[0].text)
        self.assertIsNone(final.alternatives[0].confidence)
        self.assertEqual([1], self.backend.closed_stream_ids)
        selected = self.runtime._sessions[session]
        self.assertTrue(selected.stream_closed)
        self.assertIsNone(selected.stream)

    def test_model_residency_reset_and_session_isolation(self) -> None:
        first = self.runtime.create_session()
        second = self.runtime.create_session()
        self.runtime.accept_chunk(chunk(first, 0, 0))
        self.assertEqual(SessionState.STREAMING, self.runtime.state(first))
        self.assertEqual(SessionState.OPEN, self.runtime.state(second))
        self.runtime.reset_session(first)
        self.assertEqual(SessionState.OPEN, self.runtime.state(first))
        self.assertTrue(self.runtime.model_loaded)
        self.assertIn(1, self.backend.closed_stream_ids)

    def test_cancel_is_typed_and_terminal(self) -> None:
        session = self.runtime.create_session()
        event = self.runtime.cancel_session(session, 1)
        self.assertEqual(ErrorCode.CANCELLED, event.error_code)
        self.assertEqual([1], self.backend.closed_stream_ids)
        with self.assertRaises(ProtocolError):
            self.runtime.accept_chunk(chunk(session, 0, 2))

    def test_backend_error_is_sanitized_and_reset_recovers(self) -> None:
        session = self.runtime.create_session()
        self.backend.fail_accept = True
        with self.assertRaisesRegex(ProtocolError, "backend failure: RuntimeError") as raised:
            self.runtime.accept_chunk(chunk(session, 0, 0))
        self.assertNotIn("private backend detail", str(raised.exception))
        self.assertEqual(SessionState.ERROR, self.runtime.state(session))
        self.backend.fail_accept = False
        self.runtime.reset_session(session)
        self.assertIsNotNone(self.runtime.accept_chunk(chunk(session, 0, 1)))

    def test_decode_timeout_sets_error_state(self) -> None:
        session = self.runtime.create_session()
        self.backend.always_ready = True
        with self.assertRaisesRegex(ProtocolError, "decode timeout"):
            self.runtime.accept_chunk(chunk(session, 0, 0), decode_timeout_ms=1)
        self.assertEqual(SessionState.ERROR, self.runtime.state(session))

    def test_bounded_shutdown_releases_sessions(self) -> None:
        self.runtime.create_session()
        self.assertLessEqual(self.runtime.shutdown(100), 100)
        self.assertTrue(self.backend.closed)
        self.assertEqual(0, self.runtime.session_count)
        self.assertEqual([1], self.backend.closed_stream_ids)
        with self.assertRaises(ProtocolError) as raised:
            self.runtime.create_session()
        self.assertEqual(ErrorCode.SHUTDOWN, raised.exception.code)


class SherpaBackendConfigTest(unittest.TestCase):
    def test_transducer_uses_current_release_filenames(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            model_dir = Path(temporary)
            for name in (
                "encoder.int8.onnx",
                "decoder.onnx",
                "joiner.int8.onnx",
                "tokens.txt",
            ):
                (model_dir / name).touch()
            factory = Mock(return_value=object())
            module = SimpleNamespace(
                OnlineRecognizer=SimpleNamespace(from_transducer=factory)
            )
            backend = SherpaOnnxTransducerBackend("zipformer-test", model_dir, 3)
            with patch.dict("sys.modules", {"sherpa_onnx": module}):
                backend.load_model()
            kwargs = factory.call_args.kwargs
            self.assertTrue(kwargs["encoder"].endswith("encoder.int8.onnx"))
            self.assertTrue(kwargs["decoder"].endswith("decoder.onnx"))
            self.assertEqual(3, kwargs["num_threads"])
            self.assertEqual("cpu", kwargs["provider"])

    def test_wenet_uses_streaming_ctc_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            model_dir = Path(temporary)
            (model_dir / "model-streaming.int8.onnx").touch()
            (model_dir / "tokens.txt").touch()
            factory = Mock(return_value=object())
            module = SimpleNamespace(
                OnlineRecognizer=SimpleNamespace(from_wenet_ctc=factory)
            )
            backend = SherpaOnnxWenetCtcBackend("wenet-test", model_dir, 2)
            with patch.dict("sys.modules", {"sherpa_onnx": module}):
                backend.load_model()
            kwargs = factory.call_args.kwargs
            self.assertTrue(kwargs["model"].endswith("model-streaming.int8.onnx"))
            self.assertEqual(16, kwargs["chunk_size"])
            self.assertEqual(4, kwargs["num_left_chunks"])
            self.assertEqual("greedy_search", kwargs["decoding_method"])


if __name__ == "__main__":
    unittest.main()
