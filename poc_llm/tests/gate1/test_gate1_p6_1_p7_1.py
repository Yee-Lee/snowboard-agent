from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest import mock

from jsonschema import Draft202012Validator

from poc_llm.harness.pi_artifact_auth import streaming_digest
from poc_llm.harness.pi_runtime import PiPacketFailure
from poc_llm.tools import run_gate1_p6_1_p7_1 as runner


ROOT = Path(__file__).resolve().parents[3]
LOCK = ROOT / "poc_llm/harness/gate1-p6-1-p7-1-lock-v1.json"
PACKET = ROOT / "poc_llm/tests/gate1/GATE1-P6.1-P7.1-REDESIGN-001.md"
RUNNER = ROOT / "poc_llm/tools/run_gate1_p6_1_p7_1.py"
ADAPTER = ROOT / "poc_llm/harness/litert_lm_pi_async_child_adapter_v1.py"
SCHEMA = ROOT / "poc_llm/evidence/gate1/gate1-p6-1-p7-1-v1-result.schema.json"


def fake_process() -> mock.Mock:
    process = mock.Mock()
    process.pid = 1234
    process.stdout = mock.Mock()
    return process


def common() -> dict:
    return {
        "config": Path("config.json"),
        "config_sha256": "a" * 64,
        "config_value": {},
        "config_schema": Path("config.schema.json"),
        "protocol_schema": Path("protocol.schema.json"),
        "prompt_schema": Path("prompt.schema.json"),
        "response_schema": Path("response.schema.json"),
        "receipt": Path("receipt.json"),
        "receipt_schema": Path("receipt.schema.json"),
        "install_root": Path("install"),
        "validator": mock.Mock(),
        "abort_fixture": {"input": {}},
        "catalog": {"valid_cases": [{}]},
    }


class Gate1P61P71Tests(unittest.TestCase):
    def test_lock_binds_entire_new_surface(self) -> None:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["packet_id"], runner.PACKET_ID)
        self.assertEqual(lock["base_packet_id"], runner.BASE_PACKET_ID)
        self.assertEqual(lock["candidate_order"], list(runner.CANDIDATES))
        self.assertEqual(
            lock["thresholds"],
            {"cancel_ms": 500, "rebuild_ready_ms": 10000,
             "rebuild_diagnostic_ms": 30000},
        )
        for item in lock["artifacts"].values():
            path = ROOT / item["path"]
            self.assertEqual(streaming_digest(path), item["sha256"], path)

    def test_packet_freezes_independent_reboots_and_diagnostic_only_window(self) -> None:
        packet = PACKET.read_text(encoding="utf-8")
        for phrase in (
            "separate run after a Pi reboot",
            "No P6.1 run may feed P7.1",
            "may continue a separately labelled, non-scoring observation",
            "extended observation cannot convert FAIL to PASS",
            "User authorized direct Pi execution",
        ):
            self.assertIn(phrase, packet)

    def test_async_adapter_uses_documented_path_and_discards_conversations(self) -> None:
        source = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("conversation.send_message_async(prompt)", source)
        self.assertNotIn("conversation.send_message(prompt)", source)
        self.assertIn("conversation.cancel_process()", source)
        self.assertIn("conversation.close()", source)

    def test_p7_runner_has_no_cancel_and_one_rebuild(self) -> None:
        tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
        function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "run_p7_1"
        )
        names = {
            node.func.id for node in ast.walk(function)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertNotIn("cancel", names)
        self.assertNotIn("run_p6_1", names)
        self.assertEqual(
            sum(
                1 for node in ast.walk(function)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "observed_rebuild"
            ),
            1,
        )

    def test_suite_rejects_same_boot_and_duplicate_candidate_test(self) -> None:
        prior = {
            "packet_id": runner.PACKET_ID,
            "execution_sha": "a" * 40,
            "execution_surface_sha256": "b" * 64,
            "candidate_id": "CAND-LRT-G4E2B-MOBILE-R1",
            "test_id": "P6.1",
            "isolation": {"boot_id_sha256": "c" * 64},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            receipt_dir = root / "prior"
            receipt_dir.mkdir()
            (receipt_dir / "p6-1-p7-1-sanitized.json").write_text(
                json.dumps(prior), encoding="utf-8"
            )
            kwargs = {
                "candidate_id": "CAND-LRT-Q25-15B-Q8-R1", "test_id": "P7.1",
                "execution_sha": "a" * 40, "execution_surface_sha256": "b" * 64,
            }
            with self.assertRaisesRegex(PiPacketFailure, "boot ID"):
                runner.enforce_suite_isolation(
                    root, {"boot_id_sha256": "c" * 64}, **kwargs
                )
            kwargs.update(
                candidate_id="CAND-LRT-G4E2B-MOBILE-R1", test_id="P6.1"
            )
            with self.assertRaisesRegex(PiPacketFailure, "already has a receipt"):
                runner.enforce_suite_isolation(
                    root, {"boot_id_sha256": "d" * 64}, **kwargs
                )
            kwargs.update(
                candidate_id="CAND-LRT-Q25-15B-Q8-R1", test_id="P7.1"
            )
            self.assertEqual(
                runner.enforce_suite_isolation(
                    root, {"boot_id_sha256": "d" * 64}, **kwargs
                ),
                1,
            )
    def test_p6_1_pass_requires_async_cancel_once_and_same_engine_health(self) -> None:
        process = fake_process()
        result = {"p_result": "INCONCLUSIVE", "final_cleanup": {}}
        cleanup = {
            "exit_code": 0, "waited": True, "term_sent": False,
            "kill_sent": False, "process_group_absent": True,
        }
        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(runner, "start_async_child", return_value=(process, 3200.0)), \
             mock.patch.object(runner, "send"), \
             mock.patch.object(runner, "read_frame", side_effect=[
                 {"type": "PONG"},
                 {"type": "CANCELLED", "request_id": "p6-1-cancel"},
             ]), \
             mock.patch.object(runner, "wait_marker", return_value=True), \
             mock.patch.object(runner, "marker_elapsed_ms", side_effect=[1.0, 2.0]), \
             mock.patch.object(runner, "marker_count", side_effect=[1, 2]), \
             mock.patch.object(runner, "generate", return_value=({"type": "RESULT"}, 50.0)), \
             mock.patch.object(runner, "close_child", return_value=cleanup), \
             mock.patch.object(runner, "catalog_input", return_value={}):
            runner.run_p6_1(
                common=common(), result=result,
                stderr_path=Path(temp_dir) / "p6.stderr",
            )
        self.assertEqual(result["p_result"], "PASS")
        self.assertEqual(result["cancel"]["native_cancel_count"], 1)
        self.assertEqual(result["cancel"]["native_cancel_invoked_ms"], 1.0)
        self.assertEqual(result["cancel"]["native_stream_terminal_ms"], 2.0)
        self.assertEqual(result["cancel"]["conversation_discard_count"], 2)
        self.assertEqual(result["cancel"]["same_engine_health_terminal"], "RESULT")

    def _run_p7(self, rebuild_ready_ms: float) -> tuple[dict, mock.Mock]:
        fault_process = fake_process()
        rebuilt_process = fake_process()
        result = {"p_result": "INCONCLUSIVE", "final_cleanup": {}}
        force_cleanup = {
            "exit_code": -15, "waited": True, "term_sent": True,
            "kill_sent": False, "process_group_absent": True,
        }
        clean_cleanup = {
            "exit_code": 0, "waited": True, "term_sent": False,
            "kill_sent": False, "process_group_absent": True,
        }
        send_mock = mock.Mock()
        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(runner, "start_child", return_value=(fault_process, 3500.0)), \
             mock.patch.object(runner, "group_resource_sample", return_value={"threads": 4}), \
             mock.patch.object(runner, "observe_generation_threads", return_value=5), \
             mock.patch.object(runner, "send", send_mock), \
             mock.patch.object(runner, "stop", return_value=force_cleanup), \
             mock.patch.object(runner, "observed_rebuild", return_value=(rebuilt_process, rebuild_ready_ms)), \
             mock.patch.object(runner, "read_frame", return_value={"type": "PONG"}), \
             mock.patch.object(runner, "generate", return_value=({"type": "RESULT"}, 60.0)), \
             mock.patch.object(runner, "close_child", return_value=clean_cleanup), \
             mock.patch.object(runner, "catalog_input", return_value={}), \
             mock.patch.object(runner.subprocess, "run", return_value=types.SimpleNamespace(returncode=4)):
            kwargs = {
                "common": common(), "result": result,
                "fault_stderr_path": Path(temp_dir) / "fault.stderr",
                "rebuild_stderr_path": Path(temp_dir) / "rebuild.stderr",
            }
            if rebuild_ready_ms <= 10000:
                runner.run_p7_1(**kwargs)
            else:
                with self.assertRaisesRegex(PiPacketFailure, "product recovery SLA"):
                    runner.run_p7_1(**kwargs)
        return result, send_mock

    def test_p7_1_under_ten_seconds_passes_without_cancel_frame(self) -> None:
        result, send_mock = self._run_p7(3490.0)
        self.assertEqual(result["p_result"], "PASS")
        self.assertEqual(result["recovery"]["diagnostic_disposition"], "WITHIN_SLA")
        self.assertFalse(result["recovery"]["native_cancel_invoked"])
        self.assertNotIn(
            "CANCEL", [call.args[1].get("type") for call in send_mock.call_args_list]
        )

    def test_p7_1_ready_after_ten_seconds_is_irreversible_fail(self) -> None:
        result, _send_mock = self._run_p7(10000.001)
        self.assertEqual(result["p_result"], "FAIL")
        self.assertEqual(result["recovery"]["diagnostic_disposition"], "SLOW_RECOVERY")
        self.assertEqual(result["recovery"]["diagnostic_timeout_ms"], 30000)

    def test_pass_schema_rejects_p7_over_ten_seconds(self) -> None:
        validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
        base = {
            "packet_id": runner.PACKET_ID, "base_packet_id": runner.BASE_PACKET_ID,
            "run_id": "G1-P7.1-TEST", "test_id": "P7.1",
            "candidate_id": "CAND-LRT-Q25-15B-Q8-R1", "execution_sha": "a" * 40,
            "execution_surface_sha256": "b" * 64, "core_acceptance": "PENDING",
            "isolation": {
                "boot_id_sha256": "c" * 64, "prelaunch_uptime_s": 30.0,
                "preexisting_adapter_processes": 0, "prior_candidate_workloads_in_run": 0,
                "candidate_id": "CAND-LRT-Q25-15B-Q8-R1", "test_id": "P7.1",
                "prior_receipts_checked": 1,
            },
            "environment": {}, "environment_post": {}, "runtime": {},
            "artifact_authentication": {}, "prerequisite_ready_ms": 3490.0,
            "cancel": {},
            "recovery": {
                "native_cancel_invoked": False, "abort_to_absence_ms": 20.0,
                "rebuild_ready_ms": 3490.0, "ready_sla_ms": 10000,
                "diagnostic_timeout_ms": 30000, "diagnostic_disposition": "WITHIN_SLA",
                "health_terminal": "RESULT", "health_ms": 60.0,
                "fatal_outcome_exit_code": 4,
            },
            "final_cleanup": {}, "p_result": "PASS", "violations": [],
            "result": "PASS", "elapsed_ms": 7000.0,
        }
        self.assertTrue(validator.is_valid(base), list(validator.iter_errors(base)))
        base["recovery"]["rebuild_ready_ms"] = 10000.001
        self.assertFalse(validator.is_valid(base))


if __name__ == "__main__":
    unittest.main()
