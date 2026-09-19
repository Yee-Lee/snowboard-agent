from __future__ import annotations

import asyncio
import json
from pathlib import Path
import subprocess
import sys
import unittest

from poc_llm.m4c_ss.deterministic import run_controller_case
from poc_llm.m4c_ss.plan import CONTROLLER_CASES


ROOT = Path(__file__).resolve().parents[3]


class DeterministicCasesTests(unittest.TestCase):
    def test_all_15_controller_subcases_pass_independently(self):
        for case_id in CONTROLLER_CASES:
            with self.subTest(case_id=case_id):
                result = asyncio.run(run_controller_case(case_id))
                self.assertEqual(result["status"], "PASS", result)
                self.assertTrue(result["observations"]["queue_empty"])
                self.assertTrue(result["observations"]["backend_idle"])

    def test_plan_cli_reports_exact_82_case_keys(self):
        result = subprocess.run(
            [sys.executable, "-m", "poc_llm.tools.run_m4c_ss", "plan"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["expected_case_count"], 82)
        self.assertEqual(len(set(value["case_keys"])), 82)


if __name__ == "__main__":
    unittest.main()
