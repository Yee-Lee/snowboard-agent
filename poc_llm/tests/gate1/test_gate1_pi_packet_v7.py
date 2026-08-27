from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from jsonschema import Draft202012Validator

from poc_llm.harness.litert_lm_pi_child_adapter_v2 import load_pi_config_v2
from poc_llm.harness.pi_artifact_auth import (
    ArtifactAuthenticationError,
    authenticate_model,
    streaming_digest,
    verify_model_receipt,
)
from poc_llm.tools.run_gate1_pi_compat_v7 import (
    evaluate_p10a,
    ols_slope,
    p12_disposition,
    percentile,
    session_metrics_valid,
)
from poc_llm.tools.run_gate1_pi_compat_v7 import catalog_input


ROOT = Path(__file__).resolve().parents[3]
LOCK = ROOT / "poc_llm/harness/gate1-pi-compat-lock-v7.json"
CANDIDATES = ROOT / "poc_llm/fixtures/gate1/pi-compat-candidates-v7.json"
CONFIG_SCHEMA = ROOT / "poc_llm/contracts/m1/strict-config-pi-v2.schema.json"
RECEIPT_SCHEMA = ROOT / "poc_llm/evidence/m4b/pi-artifact-auth-receipt-v2.schema.json"
RESULT_SCHEMA = ROOT / "poc_llm/evidence/gate1/gate1-pi-compat-v7-result.schema.json"
RUNNER = ROOT / "poc_llm/tools/run_gate1_pi_compat_v7.py"
ADAPTER = ROOT / "poc_llm/harness/litert_lm_pi_child_adapter_v2.py"
INSTALLER = ROOT / "poc_llm/tools/install_gate1_arm64_wheel_v2.py"


class Gate1PiPacketV7Tests(unittest.TestCase):
    def test_lock_authenticates_every_repository_artifact(self) -> None:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["packet_id"], "G1-PI-COMPAT-007")
        self.assertEqual(
            lock["candidate_order"],
            ["CAND-LRT-G4E2B-MOBILE-R1", "CAND-LRT-Q25-15B-Q8-R1"],
        )
        self.assertEqual(streaming_digest(CANDIDATES), lock["candidate_set_sha256"])
        for item in lock["artifacts"].values():
            path = ROOT / item["path"]
            self.assertEqual(streaming_digest(path), item["sha256"], path)

    def test_configs_bind_correct_model_and_formal_ready_deadline(self) -> None:
        schema = json.loads(CONFIG_SCHEMA.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        candidates = json.loads(CANDIDATES.read_text(encoding="utf-8"))["candidates"]
        for candidate in candidates:
            config_path = ROOT / candidate["standard_config"]["path"]
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertTrue(validator.is_valid(config), config_path)
            self.assertEqual(config["candidate_id"], candidate["candidate_id"])
            self.assertEqual(config["model_sha256"], candidate["model_sha256"])
            self.assertIn(candidate["candidate_id"], config["model_path"])
            self.assertEqual(config["ready_timeout_ms"], 10_000)
            self.assertEqual(config["rebuild_timeout_ms"], 10_000)
            self.assertEqual(config["max_output_tokens"], 16)
            expected_context = (
                1024
                if candidate["candidate_id"] == "CAND-LRT-G4E2B-MOBILE-R1"
                else 512
            )
            self.assertEqual(config["engine_max_num_tokens"], expected_context)
            invalid = {**config, "engine_max_num_tokens": 512 if expected_context == 1024 else 1024}
            self.assertFalse(validator.is_valid(invalid), candidate["candidate_id"])

    def test_model_authentication_streams_once_without_read_bytes(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            model = Path(directory) / "model.litertlm"
            model.write_bytes(b"model-bytes" * 1024)
            expected = hashlib.sha256(model.read_bytes()).hexdigest()
            model.chmod(0o444)
            with patch.object(Path, "read_bytes", side_effect=AssertionError("whole-file allocation")):
                record = authenticate_model(model, expected, model.stat().st_size)
            self.assertEqual(record["sha256"], expected)
            self.assertEqual(record["size_bytes"], model.stat().st_size)

    def test_receipt_detects_metadata_drift_without_rehash(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            model = Path(directory) / "model.litertlm"
            model.write_bytes(b"original")
            expected = streaming_digest(model)
            model.chmod(0o444)
            record = authenticate_model(model, expected, model.stat().st_size)
            model.chmod(0o644)
            model.write_bytes(b"modified")
            model.chmod(0o444)
            os.utime(
                model,
                ns=(
                    record["stat"]["mtime_ns"] + 2_000_000_000,
                    record["stat"]["mtime_ns"] + 2_000_000_000,
                ),
            )
            with self.assertRaises(ArtifactAuthenticationError):
                verify_model_receipt(record, model, expected)

    def test_child_config_load_does_not_open_model_contents(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            root = Path(directory)
            model = (root / "model.litertlm").resolve()
            model.write_bytes(b"authenticated-model")
            model_sha = streaming_digest(model)
            model.chmod(0o444)
            config = {
                "candidate_id": "CAND-LRT-G4E2B-MOBILE-R1",
                "pairing_revision": "litert-lm-v0.16.0-pi-r2",
                "platform": "pi-debian13-aarch64",
                "protocol_version": "snowboard.llm/1",
                "driver": "litert_lm",
                "runtime_path": "/tmp/runtime.whl",
                "model_path": str(model),
                "runtime_sha256": "a" * 64,
                "model_sha256": model_sha,
                "test_profile": "standard",
                "max_input_tokens": 128,
                "max_output_tokens": 16,
                "engine_max_num_tokens": 1024,
                "temperature": 0.0,
                "top_p": 1.0,
                "threads": 4,
                "ready_timeout_ms": 10000,
                "generate_timeout_ms": 15000,
                "cancel_timeout_ms": 500,
                "term_timeout_ms": 2000,
                "kill_timeout_ms": 1000,
                "rebuild_timeout_ms": 10000,
                "runtime_download": False,
                "network_fallback": False,
                "fallback_model": None,
            }
            config_path = root / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            receipt = {
                "receipt_version": "pi-artifact-auth/2",
                "packet_id": "G1-PI-COMPAT-007",
                "run_id": "G1-PI-COMPAT-007-TEST",
                "execution_sha": "b" * 40,
                "execution_surface_sha256": "d" * 64,
                "candidate_id": config["candidate_id"],
                "runtime_sha256": config["runtime_sha256"],
                "model": authenticate_model(model, model_sha, model.stat().st_size),
            }
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            original_open = Path.open

            def guarded_open(path: Path, *args: object, **kwargs: object):
                if path.resolve() == model:
                    raise AssertionError("child reopened complete model")
                return original_open(path, *args, **kwargs)

            with patch.object(Path, "open", guarded_open):
                loaded, loaded_receipt = load_pi_config_v2(
                    config_path,
                    streaming_digest(config_path),
                    CONFIG_SCHEMA,
                    receipt_path,
                    streaming_digest(receipt_path),
                    RECEIPT_SCHEMA,
                )
            self.assertEqual(loaded["model_sha256"], model_sha)
            self.assertEqual(loaded_receipt["model"]["sha256"], model_sha)

    def test_runner_has_one_model_authentication_call_and_no_wheel_prehash(self) -> None:
        tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        auth_calls = [
            node
            for node in calls
            if isinstance(node.func, ast.Name) and node.func.id == "authenticate_model"
        ]
        self.assertEqual(len(auth_calls), 1)
        source = RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("streaming_digest(wheel)", source)
        self.assertNotIn("read_bytes()", ADAPTER.read_text(encoding="utf-8"))
        for option in (
            "--config-schema-sha256",
            "--protocol-schema-sha256",
            "--prompt-schema-sha256",
            "--response-schema-sha256",
            "--artifact-receipt-schema-sha256",
        ):
            self.assertIn(option, ADAPTER.read_text(encoding="utf-8"))

    def test_license_metadata_covers_only_the_frozen_candidate_pair(self) -> None:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        metadata = json.loads(
            (ROOT / lock["artifacts"]["license_metadata"]["path"]).read_text(
                encoding="utf-8"
            )
        )["candidates"]
        for candidate_id in lock["candidate_order"]:
            self.assertEqual(metadata[candidate_id]["license"], "apache-2.0")
            self.assertRegex(metadata[candidate_id]["revision"], r"^[0-9a-f]{40}$")
            self.assertRegex(metadata[candidate_id]["metadata_sha256"], r"^[0-9a-f]{64}$")

    def test_all_scored_catalog_inputs_match_prompt_schema(self) -> None:
        schema = json.loads(
            (ROOT / "poc_llm/contracts/m1/prompt-input.schema.json").read_text(
                encoding="utf-8"
            )
        )
        catalog = json.loads(
            (ROOT / "poc_llm/fixtures/gate2/gate2a-public-catalog-001.json").read_text(
                encoding="utf-8"
            )
        )
        validator = Draft202012Validator(schema)
        for entry in catalog["valid_cases"]:
            self.assertTrue(validator.is_valid(catalog_input(entry)), entry["id"])

    def test_v2_installer_hashes_once_and_extracts_safely(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            root = Path(directory)
            wheel = root / "runtime.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("litert_lm/__init__.py", "VALUE = 1\n")
            target = root / "install"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    "--wheel",
                    str(wheel),
                    "--wheel-sha256",
                    streaming_digest(wheel),
                    "--target",
                    str(target),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertTrue((target / "litert_lm/__init__.py").is_file())
            self.assertNotIn("testzip(", INSTALLER.read_text(encoding="utf-8"))

    def test_cumulative_matrix_and_scored_scope_are_frozen(self) -> None:
        packet = (ROOT / "poc_llm/tests/gate1/GATE1-PI-COMPAT-PACKET-007.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("P1, P6, P7, P10A, P11, P12", packet)
        self.assertIn("P2, P3, P4, P5 and P8", packet)
        self.assertIn("Gate 2B runs P9 and P10B", packet)
        self.assertRegex(packet, r"P5\s+remains Pi-only")
        self.assertIn("execution_surface_sha256", packet)
        self.assertIn("ancestor", packet)

    def test_p10a_math_helpers_match_frozen_rules(self) -> None:
        stable = [100.0 + index for index in range(15)]
        self.assertAlmostEqual(ols_slope(stable), 1.0)
        self.assertEqual(percentile([1.0, 2.0, 3.0, 4.0], 50), 2.0)
        self.assertEqual(percentile([1.0, 2.0, 3.0, 4.0], 95), 4.0)

        def session(sequence: int, growth: float) -> dict[str, object]:
            return {
                "resources": {
                    "process_count": 1.0,
                    "rss_mib": 100.0,
                    "pss_mib": 100.0 + sequence * growth,
                    "threads": 4.0,
                    "cpu_ticks": 1.0 + sequence,
                    "mem_available_mib": 2000.0,
                    "system_used_mib": 1000.0 + sequence * growth,
                },
                "thermal": {"temperature_c": 60.0, "throttled": "0x0"},
            }

        passed, _ = evaluate_p10a([session(index, 1.0) for index in range(20)])
        failed, _ = evaluate_p10a([session(index, 5.0) for index in range(20)])
        self.assertTrue(passed)
        self.assertFalse(failed)

    def test_native_token_metrics_use_rendered_capacity_not_structured_size(self) -> None:
        valid = {"prefill_tokens": 169, "decode_tokens": 16, "kv_tokens": 185}
        self.assertTrue(session_metrics_valid(valid, 1024))
        self.assertTrue(session_metrics_valid(valid, 512))
        self.assertFalse(session_metrics_valid({**valid, "decode_tokens": 17}, 1024))
        self.assertFalse(session_metrics_valid({**valid, "kv_tokens": 1025}, 1024))
        self.assertFalse(session_metrics_valid({**valid, "prefill_tokens": 0}, 1024))
        self.assertNotIn(
            '> 144',
            RUNNER.read_text(encoding="utf-8"),
        )

    def test_p12_requires_completed_offline_inference_lifecycle(self) -> None:
        self.assertEqual(p12_disposition({"p_results": {"P1": "PASS"}}), "PASS")
        for disposition in ("FAIL", "INCONCLUSIVE", "Blocked"):
            self.assertEqual(
                p12_disposition({"p_results": {"P1": disposition}}),
                "Blocked",
            )

    def test_result_schema_rejects_wrong_packet(self) -> None:
        validator = Draft202012Validator(json.loads(RESULT_SCHEMA.read_text(encoding="utf-8")))
        self.assertFalse(validator.is_valid({"packet_id": "G1-PI-COMPAT-006"}))

    def test_result_schema_binds_outcome_order_and_p_states(self) -> None:
        validator = Draft202012Validator(json.loads(RESULT_SCHEMA.read_text(encoding="utf-8")))
        environment = {
            "git_sha": "b" * 40,
            "os_id": "debian",
            "os_version": "13",
            "machine": "aarch64",
            "mem_total_bytes": 4_000_000_000,
            "swap_total_bytes": 0,
            "network": {"routes_offline": True},
            "throttled_prelaunch": "throttled=0x0",
        }

        def candidate(candidate_id: str) -> dict[str, object]:
            return {
                "candidate_id": candidate_id,
                "p_results": {
                    "P1": "PASS", "P6": "Conditional escalation", "P7": "PASS",
                    "P10A": "PASS", "P11": "PASS", "P12": "PASS",
                },
                "artifact_authentication": {}, "normal_lifecycle": {}, "stability": {},
                "cancel": {}, "recovery": {}, "violations": [], "result": "PASS",
            }

        aggregate = {
            "packet_id": "G1-PI-COMPAT-007",
            "run_id": "G1-PI-COMPAT-007-TEST",
            "execution_sha": "b" * 40,
            "execution_surface_sha256": "d" * 64,
            "core_acceptance": "PENDING",
            "gate2_credit_scope": ["P1", "P6", "P7", "P10A", "P11", "P12"],
            "environment": environment,
            "environment_post": environment,
            "runtime": {
                "native_library_sha256": "c" * 64,
                "elf_machine": "AArch64", "linkage": "resolved", "python_import": "PASS",
            },
            "candidates": [
                candidate("CAND-LRT-G4E2B-MOBILE-R1"),
                candidate("CAND-LRT-Q25-15B-Q8-R1"),
            ],
            "proposed_finalists": ["CAND-LRT-G4E2B-MOBILE-R1"],
            "violations": [],
            "result": "PASS",
            "elapsed_ms": 1.0,
        }
        self.assertTrue(validator.is_valid(aggregate), list(validator.iter_errors(aggregate)))
        swapped = deepcopy(aggregate)
        swapped["candidates"].reverse()
        self.assertFalse(validator.is_valid(swapped))
        no_finalist = deepcopy(aggregate)
        no_finalist["proposed_finalists"] = []
        self.assertFalse(validator.is_valid(no_finalist))
        no_surface = deepcopy(aggregate)
        del no_surface["execution_surface_sha256"]
        self.assertFalse(validator.is_valid(no_surface))
        blocked_p7 = deepcopy(aggregate)
        blocked_p7["candidates"][0]["p_results"]["P7"] = "Blocked"
        self.assertFalse(validator.is_valid(blocked_p7))
        unexplained = deepcopy(aggregate)
        unexplained["result"] = "INCONCLUSIVE"
        self.assertFalse(validator.is_valid(unexplained))

    def test_fatal_outcome_self_test_is_exit_four(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(RUNNER), "--fatal-outcome-self-test"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 4)


if __name__ == "__main__":
    unittest.main()
