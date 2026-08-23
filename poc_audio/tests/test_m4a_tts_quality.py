from __future__ import annotations

import array
import sys
import unittest

from audio_poc.m4a_tts_quality import QUALITY_IDS, float_samples_to_s16le


class MatchaQualityTests(unittest.TestCase):
    def test_quality_ids_are_exact_and_risk_focused(self) -> None:
        self.assertEqual(len(QUALITY_IDS), 10)
        self.assertEqual(len(set(QUALITY_IDS)), 10)
        self.assertEqual(QUALITY_IDS[0], "tts-005")
        self.assertEqual(QUALITY_IDS[-1], "tts-018")

    def test_float_conversion_clips_and_preserves_zero(self) -> None:
        payload = float_samples_to_s16le([-2.0, -1.0, 0.0, 1.0, 2.0])
        values = array.array("h")
        values.frombytes(payload)
        if sys.byteorder != "little":
            values.byteswap()
        self.assertEqual(values.tolist(), [-32768, -32768, 0, 32767, 32767])


if __name__ == "__main__":
    unittest.main()
