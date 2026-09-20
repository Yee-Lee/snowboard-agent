from __future__ import annotations

import struct
import unittest

from poc_llm.m4c_ss.duplex import (
    CAPTURE_PERIOD_FRAMES,
    CaptureBlock,
    DuplexError,
    analyze_capture_blocks,
)


def pcm(value: int) -> bytes:
    return struct.pack(f"<{CAPTURE_PERIOD_FRAMES}h", *([value] * CAPTURE_PERIOD_FRAMES))


class DuplexAnalysisTests(unittest.TestCase):
    def test_stable_pulse_and_clock_mapping_pass_under_50_ms(self):
        period = 10_000_000
        blocks = [
            CaptureBlock((index + 1) * period, pcm(100 if index < 45 else 2_000))
            for index in range(80)
        ]
        result = analyze_capture_blocks(blocks)
        self.assertEqual(result.capture_rate_hz, 48_000)
        self.assertEqual(result.capture_format, "S16_LE")
        self.assertTrue(result.uncertainty_within_limit)
        self.assertEqual(result.uncertainty_ns, 20_000_000)
        self.assertTrue(result.capture_owner_stopped)

    def test_accumulated_read_jitter_is_counted_conservatively(self):
        period = 10_000_000
        blocks = []
        for index in range(80):
            jitter = 35_000_000 if index < 50 else max(0, 35_000_000 - (index - 49) * 5_000_000)
            blocks.append(CaptureBlock((index + 1) * period + jitter, pcm(100 if index < 45 else 2_000)))
        result = analyze_capture_blocks(blocks)
        self.assertFalse(result.uncertainty_within_limit)
        self.assertEqual(result.uncertainty_ns, 55_000_000)

    def test_transient_or_invalid_capture_fails_closed(self):
        period = 10_000_000
        transient = [
            CaptureBlock((index + 1) * period, pcm(2_000 if index == 45 else 100))
            for index in range(80)
        ]
        with self.assertRaisesRegex(DuplexError, "PULSE_NOT_DETECTED"):
            analyze_capture_blocks(transient)
        invalid = list(transient)
        invalid[10] = CaptureBlock(invalid[9].observed_end_ns - 1, pcm(100))
        with self.assertRaisesRegex(DuplexError, "NON_MONOTONIC"):
            analyze_capture_blocks(invalid)


if __name__ == "__main__":
    unittest.main()
