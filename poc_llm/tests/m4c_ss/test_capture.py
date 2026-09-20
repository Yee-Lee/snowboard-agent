from __future__ import annotations

import array
import unittest

from poc_llm.m4c_ss.capture import CaptureError, analyze_acoustic_activity
from poc_llm.m4c_ss.duplex import CAPTURE_PERIOD_FRAMES, CaptureBlock


def block(stamp: int, value: int) -> CaptureBlock:
    samples = array.array("h", [value] * CAPTURE_PERIOD_FRAMES)
    return CaptureBlock(stamp, samples.tobytes())


class CaptureAnalysisTests(unittest.TestCase):
    def test_detects_first_and_last_stable_activity(self):
        period = 10_000_000
        values = [10] * 30 + [20] * 5 + [1200] * 6 + [20] * 4 + [1400] * 3 + [20] * 5
        blocks = [block((index + 1) * period, value) for index, value in enumerate(values)]
        result = analyze_acoustic_activity(blocks)
        self.assertEqual(result.onset_monotonic_ns, 35 * period)
        self.assertEqual(result.final_monotonic_ns, 48 * period)
        self.assertEqual(result.threshold_rms, 300.0)
        self.assertEqual(result.uncertainty_ns, 20_000_000)

    def test_rejects_noise_without_stable_activity(self):
        period = 10_000_000
        values = [10] * 30 + [1200, 10, 1200, 10, 1200]
        blocks = [block((index + 1) * period, value) for index, value in enumerate(values)]
        with self.assertRaisesRegex(CaptureError, "ACTIVITY_NOT_DETECTED"):
            analyze_acoustic_activity(blocks)

    def test_ignores_stable_click_before_onset_lower_bound(self):
        period = 10_000_000
        values = [10] * 30 + [1200] * 3 + [10] * 4 + [1400] * 4 + [10] * 3
        blocks = [block((index + 1) * period, value) for index, value in enumerate(values)]

        unrestricted = analyze_acoustic_activity(blocks)
        bounded = analyze_acoustic_activity(blocks, not_before_ns=35 * period)

        self.assertEqual(unrestricted.onset_monotonic_ns, 30 * period)
        self.assertEqual(bounded.onset_monotonic_ns, 37 * period)
        self.assertGreaterEqual(bounded.onset_monotonic_ns, 35 * period)


if __name__ == "__main__":
    unittest.main()
