from __future__ import annotations

import unittest

from poc_llm.efficiency.plan import ENCODING_ORDER, FULL_ORDER, PlanError, descriptive, paired_deltas, verify_next_case


class PlanTests(unittest.TestCase):
    def test_order_is_fixed_paired_and_no_retry(self):
        self.assertEqual(ENCODING_ORDER[:4], ("A-J1", "A-P1", "A-J2", "A-P2"))
        entries = []
        for case in FULL_ORDER:
            verify_next_case(entries, case)
            entries.append({"case_id": case})
        with self.assertRaises(PlanError):
            verify_next_case([], "A-P1")
        with self.assertRaises(PlanError):
            verify_next_case(entries, FULL_ORDER[-1])

    def test_descriptive_has_no_p95_or_significance(self):
        value = descriptive([1, 2, 3, 4, 100])
        self.assertEqual(value, {"count": 5, "median": 3.0, "minimum": 1.0, "maximum": 100.0})
        self.assertNotIn("p95", value)

    def test_exact_five_pair_deltas(self):
        rows = []
        for pair in range(1, 6):
            rows.extend([
                {"pair": pair, "variant": "J", "metrics": {"ttc": pair * 10}},
                {"pair": pair, "variant": "P", "metrics": {"ttc": pair * 10 - 2}},
            ])
        result = paired_deltas(rows, left="J", right="P", metric="ttc")
        self.assertEqual(result["summary"]["median"], -2.0)
        with self.assertRaises(PlanError):
            paired_deltas(rows[:-1], left="J", right="P", metric="ttc")


if __name__ == "__main__":
    unittest.main()
