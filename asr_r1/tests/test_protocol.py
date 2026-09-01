import unittest

from asr_r1.fake_runtime import FakeStreamingRuntime
from asr_r1.protocol import (
    ErrorCode,
    EventKind,
    LifecycleCommand,
    LifecycleOperation,
    PCMChunk,
    ProtocolError,
    SessionState,
    TranscriptEvent,
    final_text_for_downstream,
)


def chunk(session_id: str, sequence: int, timestamp_ms: int) -> PCMChunk:
    return PCMChunk(
        session_id=session_id,
        sequence=sequence,
        timestamp_ms=timestamp_ms,
        samples_s16le=b"\x00\x00" * 320,
    )


class ProtocolTest(unittest.TestCase):
    def test_event_round_trip_and_downstream_final_only(self) -> None:
        runtime = FakeStreamingRuntime()
        runtime.load_model()
        session_id = runtime.create_session()
        partial = runtime.accept_chunk(chunk(session_id, 0, 0))
        final = runtime.finish_input(session_id, 20)

        self.assertIsNone(final_text_for_downstream(partial))
        self.assertEqual(final.text, final_text_for_downstream(final))
        self.assertEqual(final, TranscriptEvent.from_dict(final.to_dict()))

    def test_lifecycle_command_requires_session_and_positive_timeout(self) -> None:
        with self.assertRaises(ValueError):
            LifecycleCommand(LifecycleOperation.CANCEL, "request-1")
        with self.assertRaises(ValueError):
            LifecycleCommand(LifecycleOperation.SHUTDOWN, "request-2")
        with self.assertRaises(ValueError):
            LifecycleCommand(LifecycleOperation.SHUTDOWN, "request-3", timeout_ms=0)

    def test_pcm_contract_rejects_invalid_shape(self) -> None:
        with self.assertRaises(ValueError):
            PCMChunk("session", 0, 0, b"\x00", sample_rate_hz=16_000)
        with self.assertRaises(ValueError):
            PCMChunk("session", 0, 0, b"\x00\x00", sample_rate_hz=8_000)

    def test_pcm_chunk_round_trip(self) -> None:
        original = chunk("session", 3, 60)
        self.assertEqual(original, PCMChunk.from_dict(original.to_dict()))


class FakeRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = FakeStreamingRuntime()
        self.assertEqual("fake-asr-ar1m0-v1", self.runtime.load_model())

    def test_model_residency_and_session_isolation(self) -> None:
        first = self.runtime.create_session()
        second = self.runtime.create_session()
        self.runtime.accept_chunk(chunk(first, 0, 0))

        self.assertEqual(SessionState.STREAMING, self.runtime.state(first))
        self.assertEqual(SessionState.OPEN, self.runtime.state(second))
        self.runtime.reset_session(first)
        self.assertEqual(SessionState.OPEN, self.runtime.state(first))
        self.assertTrue(self.runtime.model_loaded)
        self.assertEqual(2, self.runtime.session_count)

    def test_out_of_order_chunks_fail_with_typed_error(self) -> None:
        session_id = self.runtime.create_session()
        with self.assertRaises(ProtocolError) as raised:
            self.runtime.accept_chunk(chunk(session_id, 1, 0))
        self.assertEqual(ErrorCode.OUT_OF_ORDER, raised.exception.code)

    def test_cancel_emits_typed_terminal_event(self) -> None:
        session_id = self.runtime.create_session()
        event = self.runtime.cancel_session(session_id, 10)
        self.assertEqual(EventKind.ERROR, event.kind)
        self.assertEqual(ErrorCode.CANCELLED, event.error_code)
        self.assertEqual(SessionState.CANCELLED, self.runtime.state(session_id))

    def test_input_finished_and_bounded_shutdown(self) -> None:
        session_id = self.runtime.create_session()
        self.runtime.accept_chunk(chunk(session_id, 0, 0))
        final = self.runtime.finish_input(session_id, 20)
        self.assertEqual(EventKind.FINAL, final.kind)
        self.assertEqual(SessionState.FINAL, self.runtime.state(session_id))
        self.assertLessEqual(self.runtime.shutdown(timeout_ms=100), 100)
        self.assertFalse(self.runtime.model_loaded)
        with self.assertRaises(ProtocolError) as raised:
            self.runtime.create_session()
        self.assertEqual(ErrorCode.SHUTDOWN, raised.exception.code)


if __name__ == "__main__":
    unittest.main()
