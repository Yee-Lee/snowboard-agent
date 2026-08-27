from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from poc_llm.harness.pi_artifact_auth import streaming_digest


ROOT = Path(__file__).resolve().parents[3]
LOCK = ROOT / "poc_llm/harness/gate1-qwen-p6-p7-isolated-lock-v1.json"
RUNNER = ROOT / "poc_llm/tools/run_gate1_qwen_p6_p7_isolated.py"
PACKET = ROOT / "poc_llm/tests/gate1/GATE1-QWEN-P6-P7-ISOLATED-ADDENDUM-001.md"
SCHEMA = ROOT / "poc_llm/evidence/gate1/gate1-qwen-p6-p7-isolated-v1-result.schema.json"


class Gate1QwenP6P7IsolatedTests(unittest.TestCase):
    def test_lock_binds_every_focused_artifact(self) -> None:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["packet_id"], "G1-PI-COMPAT-007")
        self.assertEqual(lock["candidate_order"], ["CAND-LRT-Q25-15B-Q8-R1"])
        for item in lock["artifacts"].values():
            path = ROOT / item["path"]
            self.assertEqual(streaming_digest(path), item["sha256"], path)

    def test_packet_preserves_every_threshold_and_removes_redundant_start(self) -> None:
        packet = PACKET.read_text(encoding="utf-8")
        for value in ("512-token", "10,000 ms", "500 ms", "does not insert a cooldown"):
            self.assertIn(value, packet)
        self.assertIn("does not rerun P1/P10A", packet)
        self.assertIn("Only the contract-required rebuild", packet)

    def test_runner_has_one_pre_abort_and_one_rebuild_start(self) -> None:
        tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "start_child"
        ]
        self.assertEqual(len(calls), 2)
        source = RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("time.sleep(", source)
        self.assertNotIn("P10A", source)
        self.assertIn("rebuild_timeout_ms", source)

    def test_pass_schema_requires_p7_and_isolation(self) -> None:
        validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
        result = {
            "packet_id": "G1-QWEN-P6P7-ISOLATED-001",
            "base_packet_id": "G1-PI-COMPAT-007",
            "run_id": "G1-QWEN-P6P7-ISOLATED-TEST",
            "execution_sha": "a" * 40,
            "execution_surface_sha256": "b" * 64,
            "core_acceptance": "PENDING",
            "isolation": {
                "boot_id_sha256": "c" * 64, "prelaunch_uptime_s": 30.0,
                "preexisting_adapter_processes": 0,
                "prior_candidate_workloads_in_run": 0,
                "candidate_id": "CAND-LRT-Q25-15B-Q8-R1",
            },
            "environment": {}, "environment_post": {}, "runtime": {},
            "artifact_authentication": {}, "prerequisite_ready_ms": 3500.0,
            "p_results": {"P6": "Conditional escalation", "P7": "PASS"},
            "cancel": {}, "recovery": {}, "violations": [], "result": "PASS",
            "elapsed_ms": 1.0,
        }
        self.assertTrue(validator.is_valid(result), list(validator.iter_errors(result)))
        result["p_results"]["P7"] = "Blocked"
        self.assertFalse(validator.is_valid(result))
        result["p_results"]["P7"] = "PASS"
        result["isolation"]["prior_candidate_workloads_in_run"] = 1
        self.assertFalse(validator.is_valid(result))


if __name__ == "__main__":
    unittest.main()
