from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator

from poc_llm.harness.pi_artifact_auth import streaming_digest
from poc_llm.tools.run_gate1_qwen_isolated_completion import isolation_state


ROOT = Path(__file__).resolve().parents[3]
LOCK = ROOT / "poc_llm/harness/gate1-qwen-isolated-completion-lock-v1.json"
CANDIDATES = ROOT / "poc_llm/fixtures/gate1/pi-qwen-isolated-candidate-v1.json"
INNER_SCHEMA = ROOT / "poc_llm/evidence/gate1/gate1-qwen-isolated-v1-inner-result.schema.json"
RESULT_SCHEMA = ROOT / "poc_llm/evidence/gate1/gate1-qwen-isolated-v1-result.schema.json"
PACKET = ROOT / "poc_llm/tests/gate1/GATE1-QWEN-ISOLATED-COMPLETION-ADDENDUM-001.md"


class Gate1QwenIsolatedCompletionTests(unittest.TestCase):
    def test_lock_authenticates_single_qwen_surface(self) -> None:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["packet_id"], "G1-PI-COMPAT-007")
        self.assertEqual(lock["candidate_order"], ["CAND-LRT-Q25-15B-Q8-R1"])
        self.assertEqual(streaming_digest(CANDIDATES), lock["candidate_set_sha256"])
        for item in lock["artifacts"].values():
            path = ROOT / item["path"]
            self.assertEqual(streaming_digest(path), item["sha256"], path)

    def test_candidate_keeps_exact_qwen_512_config(self) -> None:
        candidate = json.loads(CANDIDATES.read_text(encoding="utf-8"))["candidates"][0]
        self.assertEqual(candidate["candidate_id"], "CAND-LRT-Q25-15B-Q8-R1")
        config_path = ROOT / candidate["standard_config"]["path"]
        self.assertEqual(streaming_digest(config_path), candidate["standard_config"]["sha256"])
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(config["engine_max_num_tokens"], 512)
        self.assertEqual(config["ready_timeout_ms"], 10_000)

    def test_isolation_state_requires_recent_boot_and_no_adapter(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            proc = Path(directory)
            (proc / "sys/kernel/random").mkdir(parents=True)
            (proc / "uptime").write_text("123.5 0.0\n", encoding="ascii")
            (proc / "sys/kernel/random/boot_id").write_text("boot-one\n", encoding="ascii")
            state = isolation_state(proc, max_uptime_s=900)
            self.assertEqual(state["prelaunch_uptime_s"], 123.5)
            self.assertEqual(state["preexisting_adapter_processes"], 0)
            self.assertEqual(
                state["boot_id_sha256"], hashlib.sha256(b"boot-one").hexdigest()
            )
            (proc / "uptime").write_text("901 0\n", encoding="ascii")
            with self.assertRaises(RuntimeError):
                isolation_state(proc, max_uptime_s=900)

    def test_inner_schema_accepts_only_one_qwen_candidate(self) -> None:
        validator = Draft202012Validator(json.loads(INNER_SCHEMA.read_text(encoding="utf-8")))
        candidate = {
            "candidate_id": "CAND-LRT-Q25-15B-Q8-R1",
            "p_results": {
                "P1": "PASS", "P6": "Conditional escalation", "P7": "PASS",
                "P10A": "PASS", "P11": "PASS", "P12": "PASS",
            }, "artifact_authentication": {}, "normal_lifecycle": {},
            "stability": {}, "cancel": {}, "recovery": {}, "violations": [],
            "result": "PASS",
        }
        result = {
            "packet_id": "G1-PI-COMPAT-007",
            "run_id": "G1-PI-COMPAT-007-QWEN-ISOLATED-TEST",
            "execution_sha": "a" * 40,
            "execution_surface_sha256": "b" * 64,
            "core_acceptance": "PENDING",
            "gate2_credit_scope": ["P1", "P6", "P7", "P10A", "P11", "P12"],
            "environment": {}, "environment_post": {}, "runtime": {},
            "candidates": [candidate],
            "proposed_finalists": ["CAND-LRT-Q25-15B-Q8-R1"],
            "violations": [], "result": "PASS",
        }
        self.assertTrue(validator.is_valid(result), list(validator.iter_errors(result)))
        result["candidates"][0]["p_results"]["P10A"] = "Blocked"
        self.assertFalse(validator.is_valid(result))
        result["candidates"][0]["p_results"]["P10A"] = "PASS"
        result["candidates"][0]["candidate_id"] = "CAND-LRT-G4E2B-MOBILE-R1"
        self.assertFalse(validator.is_valid(result))

    def test_packet_freezes_isolation_and_no_retuning(self) -> None:
        packet = PACKET.read_text(encoding="utf-8")
        for value in ("512", "10,000 ms", "reboot", "no other candidate workload"):
            self.assertIn(value, packet)
        self.assertIn("No repeated attempts or token retuning", packet)

    def test_outer_schema_rejects_nonisolated_pass(self) -> None:
        validator = Draft202012Validator(json.loads(RESULT_SCHEMA.read_text(encoding="utf-8")))
        result = {
            "packet_id": "G1-QWEN-ISOLATED-COMPLETION-001",
            "base_packet_id": "G1-PI-COMPAT-007",
            "run_id": "G1-PI-COMPAT-007-QWEN-ISOLATED-TEST",
            "execution_sha": "a" * 40,
            "execution_surface_sha256": "b" * 64,
            "isolation": {
                "boot_id_sha256": "c" * 64,
                "prelaunch_uptime_s": 12.0,
                "preexisting_adapter_processes": 0,
                "prior_candidate_workloads_in_run": 0,
                "candidate_id": "CAND-LRT-Q25-15B-Q8-R1",
            },
            "inner_result_sha256": "d" * 64,
            "candidate_run": {}, "violations": [], "result": "PASS",
        }
        self.assertTrue(validator.is_valid(result), list(validator.iter_errors(result)))
        result["isolation"]["prior_candidate_workloads_in_run"] = 1
        self.assertFalse(validator.is_valid(result))


if __name__ == "__main__":
    unittest.main()
