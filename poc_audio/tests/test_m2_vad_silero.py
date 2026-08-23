from __future__ import annotations

import unittest

from audio_poc.m2_vad_silero import detect_probability_windows


class SileroVadScorecardTests(unittest.TestCase):
    def test_probability_onset_debounce_and_hangover_are_fixed(self) -> None:
        probabilities = [0.9] * 9 + [0.1] + [0.1] * 16
        events, positives = detect_probability_windows(probabilities, 1200)
        self.assertEqual(events, [(160, 448)])
        self.assertEqual(positives, 9)

    def test_short_probability_burst_does_not_trigger(self) -> None:
        events, positives = detect_probability_windows([0.9] * 8 + [0.1] * 20, 1200)
        self.assertEqual(events, [])
        self.assertEqual(positives, 8)


if __name__ == "__main__":
    unittest.main()
