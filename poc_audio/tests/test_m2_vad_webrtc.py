from __future__ import annotations

import unittest

from audio_poc.m2_vad_webrtc import (
    FRAME_BYTES,
    detect_events,
    match_boundaries,
    padded_and_merged_events,
    score_records,
)


class WebRtcVadScorecardTests(unittest.TestCase):
    def test_detector_masks_startup_debounces_and_closes_after_500_ms(self) -> None:
        frames = [b"0" * FRAME_BYTES for _ in range(50)]
        speech = set(range(15))
        calls = iter(range(len(frames)))
        events, positives = detect_events(frames, lambda _: next(calls) in speech)
        self.assertEqual(events, [(160, 460)])
        self.assertEqual(positives, 15)

    def test_detector_rejects_short_impact_burst(self) -> None:
        frames = [b"0" * FRAME_BYTES for _ in range(40)]
        speech = set(range(4, 11))
        calls = iter(range(len(frames)))
        events, positives = detect_events(frames, lambda _: next(calls) in speech)
        self.assertEqual(events, [])
        self.assertEqual(positives, 7)

    def test_capture_padding_merges_touching_pause_events(self) -> None:
        self.assertEqual(
            padded_and_merged_events([(1400, 2540), (3520, 5180)], 8000),
            [[900, 5780]],
        )

    def test_boundary_matching_is_one_to_one(self) -> None:
        matched, errors, extras = match_boundaries([100, 500], [90, 510, 520], -100, 300)
        self.assertEqual(matched, 2)
        self.assertEqual(errors, [-10, 10])
        self.assertEqual(extras, [520])

    def test_score_applies_separate_recall_boundary_and_false_start_gates(self) -> None:
        records = [
            {
                "fixture_id": "clear",
                "class": "clear_speech",
                "duration_seconds": 6.0,
                "reference_intervals_ms": [[500, 1500]],
                "candidate_events_ms": [[520, 1540]],
                "capture_intervals_ms": [[20, 2140]],
            },
            {
                "fixture_id": "pause",
                "class": "pause",
                "duration_seconds": 8.0,
                "reference_intervals_ms": [[500, 1500], [2200, 3000]],
                "candidate_events_ms": [[520, 1540], [2220, 3040]],
                "capture_intervals_ms": [[20, 3640]],
            },
            {
                "fixture_id": "silence",
                "class": "silence",
                "duration_seconds": 300.0,
                "reference_intervals_ms": [],
                "candidate_events_ms": [],
                "capture_intervals_ms": [],
            },
            {
                "fixture_id": "noise",
                "class": "noise",
                "duration_seconds": 300.0,
                "reference_intervals_ms": [],
                "candidate_events_ms": [],
                "capture_intervals_ms": [],
            },
        ]
        result = score_records(records)
        self.assertTrue(result["quality_pass"])
        self.assertEqual(result["overall"]["speech_start_recall_percent"], 100)
        self.assertEqual(result["overall"]["reference_starts"], 2)
        self.assertEqual(result["overall"]["complete_utterance_percent"], 100)
        self.assertEqual(result["overall"]["false_starts_per_10_min"], 0)


if __name__ == "__main__":
    unittest.main()
