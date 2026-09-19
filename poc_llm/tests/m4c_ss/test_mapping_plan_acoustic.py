from __future__ import annotations

import struct
import unittest

from poc_llm.m4c_ss.acoustic import AcousticConfig, AcousticError, detect_s16le
from poc_llm.m4c_ss.controller import FragmentChannel
from poc_llm.m4c_ss.mapping import B1, B2, acknowledge_mapping_batch, next_mapping_batch
from poc_llm.m4c_ss.plan import build_plan, case_key


class MappingTests(unittest.IsolatedAsyncioTestCase):
    async def test_b1_keeps_each_fragment_as_one_request(self):
        subject = FragmentChannel("op")
        await subject.feed("op", 0, "甲，")
        await subject.feed("op", 1, "乙。")
        first = await next_mapping_batch(subject, B1)
        self.assertEqual((first.sequences, first.text, first.coalesced), ((0,), "甲，", False))
        await acknowledge_mapping_batch(subject, "op", first)
        second = await next_mapping_batch(subject, B1)
        self.assertEqual(second.sequences, (1,))

    async def test_b2_coalesces_only_already_available_lookahead(self):
        subject = FragmentChannel("op")
        await subject.feed("op", 0, "甲，")
        first = await next_mapping_batch(subject, B2)
        self.assertEqual((first.sequences, first.coalesced), ((0,), False))
        await acknowledge_mapping_batch(subject, "op", first)
        await subject.feed("op", 1, "乙，")
        await subject.feed("op", 2, "丙。")
        second = await next_mapping_batch(subject, B2)
        self.assertEqual((second.sequences, second.text, second.coalesced), ((1, 2), "乙，丙。", True))


class PlanTests(unittest.TestCase):
    def test_fixed_plan_contains_82_unique_records(self):
        plan = build_plan()
        self.assertEqual(len(plan), 82)
        self.assertEqual(len({case_key(item) for item in plan}), 82)
        counts = {name: sum(item.partition == name for item in plan)
                  for name in ("controller", "mapping", "live", "negative")}
        self.assertEqual(counts, {"controller": 15, "mapping": 18, "live": 40, "negative": 9})

    def test_live_order_alternates_and_keeps_both_arms(self):
        rows = [item for item in build_plan() if item.partition == "live" and item.case_id == "L01-IDENTITY"]
        self.assertEqual([(item.repetition, item.arm, item.order) for item in rows[:4]], [
            (1, "A", "A-B"), (1, "B", "A-B"), (2, "B", "B-A"), (2, "A", "B-A"),
        ])
        mapping = [item for item in build_plan()
                   if item.partition == "mapping" and item.case_id == "T01"]
        self.assertEqual([item.candidate for item in mapping], [
            B1, B2, B2, B1, B1, B2,
        ])


class AcousticTests(unittest.TestCase):
    def config(self, **changes):
        values = dict(sample_rate_hz=16000, threshold_abs_s16=1000,
                      minimum_active_samples=3, clock_error_ns=10_000_000,
                      detector_error_ns=5_000_000)
        values.update(changes)
        return AcousticConfig(**values)

    def test_detects_stable_onset_end_and_maps_monotonic_time(self):
        values = [0] * 10 + [1500, -1600, 1700, 1800] + [0] * 4
        pcm = struct.pack(f"<{len(values)}h", *values)
        result = detect_s16le(pcm, capture_start_monotonic_ns=1_000_000_000, config=self.config())
        self.assertEqual((result.onset_sample, result.final_sample), (10, 13))
        self.assertEqual(result.onset_monotonic_ns, 1_000_625_000)
        self.assertEqual(result.uncertainty_ns, 15_000_000)

    def test_rejects_transient_noise_and_excessive_uncertainty(self):
        pcm = struct.pack("<5h", 0, 1500, 0, 1500, 0)
        with self.assertRaisesRegex(AcousticError, "NO_ACOUSTIC_ACTIVITY"):
            detect_s16le(pcm, capture_start_monotonic_ns=0, config=self.config())
        with self.assertRaisesRegex(AcousticError, "EXCESSIVE_UNCERTAINTY"):
            detect_s16le(pcm, capture_start_monotonic_ns=0,
                         config=self.config(clock_error_ns=46_000_000))


if __name__ == "__main__":
    unittest.main()
