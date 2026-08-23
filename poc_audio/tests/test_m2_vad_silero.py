from __future__ import annotations

import unittest

from audio_poc.m2_vad_silero import detect_probability_windows


class SileroVadScorecardTests(unittest.TestCase):
    def test_probability_threshold_and_hangover_are_fixed(self) -> None:
        probabilities = [0.1] * 3 + [0.5, 0.9] + [0.1] * 16
        events, positives = detect_probability_windows(probabilities, 21 * 32)
        self.assertEqual(events, [(96, 160)])
        self.assertEqual(positives, 2)

    def test_end_is_bounded_by_fixture_duration(self) -> None:
        events, positives = detect_probability_windows([0.9], 20)
        self.assertEqual(events, [(0, 20)])
        self.assertEqual(positives, 1)


if __name__ == "__main__":
    unittest.main()
