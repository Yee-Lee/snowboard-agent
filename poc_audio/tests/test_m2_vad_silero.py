from __future__ import annotations

import unittest

from audio_poc.m2_vad_silero import detect_probability_windows


class SileroVadScorecardTests(unittest.TestCase):
    def test_probability_hysteresis_and_hangover_are_fixed(self) -> None:
        probabilities = [0.9] * 9 + [0.4] * 3 + [0.1] * 17
        events, positives = detect_probability_windows(probabilities, 1300)
        self.assertEqual(events, [(160, 544)])
        self.assertEqual(positives, 9)

    def test_minimum_speech_rejects_short_probability_burst(self) -> None:
        events, positives = detect_probability_windows([0.9] * 7 + [0.1] * 20, 1200)
        self.assertEqual(events, [])
        self.assertEqual(positives, 7)

    def test_probability_return_above_threshold_cancels_pending_end(self) -> None:
        probabilities = [0.9] * 9 + [0.1] * 8 + [0.9] * 3 + [0.1] * 17
        events, _ = detect_probability_windows(probabilities, 1500)
        self.assertEqual(events, [(160, 800)])


if __name__ == "__main__":
    unittest.main()
