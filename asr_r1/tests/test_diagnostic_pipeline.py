import unittest

from asr_r1.diagnostic_pipeline import (
    FakeSecondPassScorer,
    FakeVadEndpoint,
    VadEventKind,
    inspect_final_with_fake_scorer,
)
from asr_r1.protocol import EventKind, TranscriptAlternative, TranscriptEvent


class DiagnosticPipelineTest(unittest.TestCase):
    def test_fake_vad_endpoint_reset_and_cancel(self) -> None:
        endpoint = FakeVadEndpoint()
        self.assertIsNone(endpoint.observe(0, False))
        self.assertEqual(VadEventKind.SPEECH_START, endpoint.observe(10, True).kind)
        self.assertIsNone(endpoint.observe(20, True))
        self.assertEqual(VadEventKind.SPEECH_END, endpoint.observe(30, False).kind)
        endpoint.cancel()
        with self.assertRaisesRegex(RuntimeError, "cancelled"):
            endpoint.observe(40, True)
        endpoint.reset()
        self.assertEqual(VadEventKind.SPEECH_START, endpoint.observe(0, True).kind)

    def test_fake_scorer_inspects_nbest_without_changing_final(self) -> None:
        event = TranscriptEvent(
            kind=EventKind.FINAL,
            session_id="session-1",
            sequence=3,
            emitted_at_ms=1000,
            text="first",
            alternatives=(
                TranscriptAlternative("first", rank=1, confidence=0.4),
                TranscriptAlternative("second", rank=2, confidence=0.3),
            ),
        )
        before = event.to_dict()
        result = inspect_final_with_fake_scorer(
            event, FakeSecondPassScorer({"first": 1.0, "second": 2.0})
        )
        self.assertEqual(2, result.recommended_input_rank)
        self.assertFalse(result.top_one_fallback)
        self.assertTrue(result.confidence_available)
        self.assertTrue(result.final_unchanged)
        self.assertEqual(before, event.to_dict())
        self.assertNotIn("first", str(result.to_dict()))
        self.assertNotIn("second", str(result.to_dict()))

    def test_fake_scorer_proves_top_one_fallback(self) -> None:
        event = TranscriptEvent(
            kind=EventKind.FINAL,
            session_id="session-1",
            sequence=1,
            emitted_at_ms=1000,
            text="only",
        )
        result = inspect_final_with_fake_scorer(event, FakeSecondPassScorer({}))
        self.assertTrue(result.top_one_fallback)
        self.assertFalse(result.confidence_available)
        self.assertEqual(1, result.recommended_input_rank)

    def test_fake_scorer_rejects_partial(self) -> None:
        partial = TranscriptEvent(
            kind=EventKind.PARTIAL,
            session_id="session-1",
            sequence=0,
            emitted_at_ms=0,
            text="partial",
        )
        with self.assertRaisesRegex(ValueError, "final events only"):
            inspect_final_with_fake_scorer(partial, FakeSecondPassScorer({}))


if __name__ == "__main__":
    unittest.main()
