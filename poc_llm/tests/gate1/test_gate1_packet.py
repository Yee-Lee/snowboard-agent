#!/usr/bin/env python3
"""Gate 1 packet protocol and false-PASS regression tests; never candidate evidence."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import platform
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "poc_llm/tools/run_gate1_prescreen.py"
SELECTOR = ROOT / "poc_llm/tools/select_gate1_finalists.py"
LOCK = ROOT / "poc_llm/harness/gate1-lock.json"
POSITIVE_MANIFEST = ROOT / "poc_llm/tests/gate1/CAND-PROTOCOL-SELFTEST.json"
NEGATIVE_MANIFEST = ROOT / "poc_llm/tests/gate1/CAND-NO-LLM-REPRO.json"
HOST_PLATFORM = {"x86_64": "ubuntu-x86_64", "aarch64": "ubuntu-aarch64"}.get(platform.machine())
OTHER_PLATFORM = "ubuntu-aarch64" if HOST_PLATFORM == "ubuntu-x86_64" else "ubuntu-x86_64"


class Gate1PacketTest(unittest.TestCase):
    @unittest.skipUnless(HOST_PLATFORM, "Gate 1 packet supports x86_64 and aarch64 only")
    def test_protocol_flow_and_expected_json_printer_regression(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gate1-packet-") as temporary:
            temp = Path(temporary)
            positive = subprocess.run(
                ["python3", str(RUNNER), "--platform", HOST_PLATFORM, "--run-id", "G1-RUN-PROTOCOL-TEST",
                 "--candidate-manifest", str(POSITIVE_MANIFEST), "--lock", str(LOCK),
                 "--raw-dir", str(temp / "positive-raw")],
                cwd=ROOT, check=False, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(positive.returncode, 0, positive.stdout + positive.stderr)
            positive_result = json.loads(positive.stdout)
            self.assertEqual(positive_result["result"], "PASS")
            self.assertEqual(set(positive_result["gates"].values()), {"PASS"})
            self.assertEqual(len(positive_result["cases"]), 60)
            self.assertEqual(positive_result["cleanup"], {
                "exit_code": 0, "process_group_absent": True, "waited": True,
            })

            negative = subprocess.run(
                ["python3", str(RUNNER), "--platform", HOST_PLATFORM, "--run-id", "G1-RUN-NO-LLM-TEST",
                 "--candidate-manifest", str(NEGATIVE_MANIFEST), "--lock", str(LOCK),
                 "--raw-dir", str(temp / "negative-raw")],
                cwd=ROOT, check=False, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(negative.returncode, 1, negative.stdout + negative.stderr)
            negative_result = json.loads(negative.stdout)
            self.assertEqual(negative_result["result"], "FAIL")
            self.assertNotEqual(negative_result["gates"]["P1"], "PASS")
            self.assertTrue(negative_result["cleanup"]["process_group_absent"])

            result_paths = []
            for name, result in (("positive", positive_result), ("negative", negative_result)):
                for result_platform in (HOST_PLATFORM, OTHER_PLATFORM):
                    value = copy.deepcopy(result)
                    value["platform"] = result_platform
                    path = temp / f"{name}-{result_platform}.json"
                    path.write_text(json.dumps(value), encoding="utf-8")
                    result_paths.append(path)
            selection = subprocess.run(
                ["python3", str(SELECTOR), "--lock", str(LOCK), "--results", *map(str, result_paths)],
                cwd=ROOT, check=False, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(selection.returncode, 0, selection.stdout + selection.stderr)
            decision = json.loads(selection.stdout)
            self.assertEqual([item["candidate_id"] for item in decision["proposed_finalists"]],
                             ["CAND-PROTOCOL-SELFTEST"])
            self.assertNotIn("CAND-NO-LLM-REPRO",
                             [item["candidate_id"] for item in decision["proposed_finalists"]])

    @unittest.skipUnless(HOST_PLATFORM, "Gate 1 packet supports x86_64 and aarch64 only")
    def test_selector_is_deterministic_and_caps_finalists_at_two(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gate1-selector-") as temporary:
            temp = Path(temporary)
            run = subprocess.run(
                ["python3", str(RUNNER), "--platform", HOST_PLATFORM, "--run-id", "G1-RUN-RANK-TEST",
                 "--candidate-manifest", str(POSITIVE_MANIFEST), "--lock", str(LOCK),
                 "--raw-dir", str(temp / "raw")],
                cwd=ROOT, check=False, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            baseline = json.loads(run.stdout)
            paths = []
            for index in range(3):
                for result_platform in (HOST_PLATFORM, OTHER_PLATFORM):
                    value = copy.deepcopy(baseline)
                    value["candidate_id"] = f"CAND-RANK-{index}"
                    value["pairing_revision"] = "selector-test-r1"
                    value["platform"] = result_platform
                    value["metrics"]["peak_rss_bytes"] += index
                    path = temp / f"rank-{index}-{result_platform}.json"
                    path.write_text(json.dumps(value), encoding="utf-8")
                    paths.append(path)
            selection = subprocess.run(
                ["python3", str(SELECTOR), "--lock", str(LOCK), "--results", *map(str, paths)],
                cwd=ROOT, check=False, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(selection.returncode, 0, selection.stdout + selection.stderr)
            decision = json.loads(selection.stdout)
            self.assertTrue(decision["max_two_enforced"])
            self.assertEqual([item["candidate_id"] for item in decision["proposed_finalists"]],
                             ["CAND-RANK-0", "CAND-RANK-1"])


if __name__ == "__main__":
    unittest.main()
