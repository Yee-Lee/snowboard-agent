from __future__ import annotations

import unittest

from poc_llm.tools.run_efficiency_prompt_engineering import TIMING_PAIR, _passes


class PromptEngineeringTests(unittest.TestCase):
    def test_timing_pair_reaches_but_does_not_cross_voice_limit(self) -> None:
        self.assertLess(len(TIMING_PAIR[0]), 20)
        self.assertEqual(len(TIMING_PAIR[1]), 20)

    def test_public_semantic_checks_are_bounded(self) -> None:
        self.assertTrue(_passes("identity", {"text": "我是雪板。", "end": False}))
        self.assertTrue(_passes("negative", {"text": "我無法看見你。", "end": False}))
        self.assertTrue(_passes("end", {"text": "", "end": True}))
        self.assertFalse(_passes("end", {"text": "再見", "end": False}))
        self.assertFalse(_passes("answer", {"text": "", "end": True}))


if __name__ == "__main__":
    unittest.main()
