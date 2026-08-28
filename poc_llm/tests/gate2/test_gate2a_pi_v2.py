from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import types
import unittest
import uuid
from unittest.mock import patch

from jsonschema import Draft202012Validator

from poc_llm.harness.litert_lm_child_adapter import Cancelled
from poc_llm.harness.m1_contract_boundary import normalize_response
from poc_llm.tools.run_gate2a_pi_v2 import (
    CANDIDATES,
    EXECUTED_ITEMS,
    STANDARD_INPUT,
    p2_valid,
    p5_result_disposition,
    valid_run_id as valid_gate2a_run_id,
    p4_summary,
    main as gate2a_main,
)


ROOT = Path(__file__).resolve().parents[3]
LOCK = ROOT / "poc_llm/harness/gate2a-pi-lock-v2.json"
RUNNER = ROOT / "poc_llm/tools/run_gate2a_pi_v2.py"
P5_ADAPTER = ROOT / "poc_llm/harness/litert_lm_pi_p5_child_adapter_v1.py"
P5_FIXTURE = ROOT / "poc_llm/fixtures/gate2/p5-continuous-timeout-002.json"
CATALOG = ROOT / "poc_llm/fixtures/gate2/gate2a-public-catalog-002.json"
ENTRY = ROOT / "poc_llm/fixtures/gate2/gate1-closure-entry-001.json"
ENTRY_SCHEMA = ROOT / "poc_llm/evidence/m4b/gate1-closure-entry-v1.schema.json"
RESULT_SCHEMA = ROOT / "poc_llm/evidence/m4b/gate2a-pi-v2-result.schema.json"
P5_SCHEMA = ROOT / "poc_llm/contracts/m1/strict-config-pi-p5-v1.schema.json"
PRODUCT_SCHEMA = ROOT / "poc_llm/contracts/m1/strict-config-pi-product-v1.schema.json"
CLEANUP_PROOF = {
    "exit_code":0, "waited":True, "term_sent":False,
    "kill_sent":False, "process_group_absent":True,
}


def complete_samples() -> dict:
    return {
        "p2":{"ready_ms":1.0,"cases":[{} for _ in range(30)],"error_type":None},
        "p3":[{} for _ in range(10)],
        "p4":{"resident_ready_ms":1.0,"cold":[{} for _ in range(3)],
              "warmups":[{} for _ in range(3)],"hot":[{} for _ in range(20)],
              "summary":{str(index):index for index in range(7)},"failures":[]},
        "p5":{"ready_ms":1.0,"terminal":"ERROR","code":"TIMEOUT","elapsed_ms":15000.0,
              "observation_error_type":None,"marker_counts":{},"same_child_pong":"PONG",
              "same_child_health_terminal":"RESULT","rebuild_ready_ms":1.0,
              "rebuild_health_terminal":"RESULT","rebuild_error_type":None},
        "p8":{"ready_ms":1.0,"cases":[{} for _ in range(5)],"error_type":None},
    }


def complete_cleanup() -> dict:
    return {
        name:dict(CLEANUP_PROOF)
        for name in ("p2","standard","p8","p5_same_child","p5_rebuild")
    }


class Benchmark:
    init_time_in_second = 0.001
    time_to_first_token_in_second = 0.002
    last_prefill_token_count = 8
    last_prefill_tokens_per_second = 100.0
    last_decode_token_count = 4
    last_decode_tokens_per_second = 20.0


class Conversation:
    def __init__(self, blocking: bool):
        self.blocking = blocking
        self.cancelled = threading.Event()
        self.cancel_count = 0
        self.token_count = 12

    def send_message_async(self, _prompt: str):
        yield {"text": "chunk"}
        if self.blocking:
            self.cancelled.wait(2)

    def cancel_process(self) -> None:
        self.cancel_count += 1
        self.cancelled.set()

    def get_benchmark_info(self) -> Benchmark:
        return Benchmark()

    def close(self) -> None:
        pass


class Engine:
    def __init__(self, *_args, **_kwargs):
        self.created: list[Conversation] = []

    def create_conversation(self, **_kwargs) -> Conversation:
        value = Conversation(blocking=not self.created)
        self.created.append(value)
        return value

    def close(self) -> None:
        pass


class Gate2APiV2Tests(unittest.TestCase):
    def test_run_id_is_single_safe_slug(self) -> None:
        self.assertTrue(valid_gate2a_run_id("G2A-PI-GEMMA-001"))
        for value in ("../escape", "/tmp/escape", "nested/run", "", "a" * 129):
            self.assertFalse(valid_gate2a_run_id(value))

    def test_lock_authenticates_complete_002_surface(self) -> None:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["packet_id"], "G2A-PI-LLM-002")
        self.assertEqual(lock["executed_items"], list(EXECUTED_ITEMS))
        self.assertEqual(set(lock["candidates"]), set(CANDIDATES))
        for item in lock["artifacts"].values():
            path = ROOT / item["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"], path)
        for candidate in lock["candidates"].values():
            for item in candidate.values():
                path = ROOT / item["path"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"], path)

    def test_candidate_specific_p5_and_product_profiles_are_bounded(self) -> None:
        validator = Draft202012Validator(json.loads(P5_SCHEMA.read_text()))
        product_validator = Draft202012Validator(json.loads(PRODUCT_SCHEMA.read_text()))
        expected = {
            CANDIDATES[0]: (1024, 512),
            CANDIDATES[1]: (512, 256),
        }
        lock = json.loads(LOCK.read_text())
        for candidate_id, (capacity, chunk) in expected.items():
            value = json.loads((ROOT / lock["candidates"][candidate_id]["p5_config"]["path"]).read_text())
            self.assertTrue(validator.is_valid(value))
            self.assertEqual(value["engine_max_num_tokens"], capacity)
            self.assertEqual(value["max_output_tokens"], chunk)
            invalid = {**value, "engine_max_num_tokens": 4096}
            self.assertFalse(validator.is_valid(invalid))
            product = json.loads((ROOT / lock["candidates"][candidate_id]["product_config"]["path"]).read_text())
            self.assertTrue(product_validator.is_valid(product))
            self.assertEqual(product["engine_max_num_tokens"], capacity)
            self.assertEqual(product["max_output_tokens"], 64)

    def test_gate1_entry_keeps_qwen_p7_1_fail_and_receipt_identities(self) -> None:
        entry = json.loads(ENTRY.read_text())
        schema = json.loads(ENTRY_SCHEMA.read_text())
        self.assertTrue(Draft202012Validator(schema).is_valid(entry))
        qwen = entry["candidates"][CANDIDATES[1]]
        self.assertEqual(qwen["P7.1"], "FAIL")
        self.assertEqual(qwen["workaround_disposition"], "REQUIRED_BEFORE_PROVISIONAL_RECOMMENDATION")
        self.assertEqual(len(entry["replacement_receipts"]), 4)

    def test_result_schema_rejects_qwen_normal_eligibility(self) -> None:
        value = {
            "packet_id": "G2A-PI-LLM-002", "run_id": "run", "candidate_id": CANDIDATES[1],
            "execution_sha": "a" * 40, "execution_surface_sha256": "b" * 64,
            "gate1_entry": {}, "isolation": {}, "environment": {}, "environment_post": {},
            "runtime": {}, "artifact_authentication": {
                "reused_receipt_sha256":"c"*64,"model_sha256":"d"*64,
                "model_size_bytes":1,"full_model_hash_count":0,"metadata_unchanged":True,
            },
            "carried_results": {"P1":"PASS","P6.1":"PASS","P7.1":"FAIL","P10A":"PASS","P11":"PASS","P12":"PASS"},
            "executed_results": {"P2":"PASS","P3":"PASS","P4":"PASS","P5":"PASS","P8":"PASS"},
            "samples": complete_samples(), "cleanup": complete_cleanup(), "violations": [], "gate2a_scope_result": "PASS",
            "provisional_eligibility": "WORKAROUND_DISPOSITION_REQUIRED", "result": "PASS",
        }
        validator = Draft202012Validator(json.loads(RESULT_SCHEMA.read_text()))
        self.assertTrue(validator.is_valid(value))
        empty = {**value, "samples":{}}
        self.assertFalse(validator.is_valid(empty))
        value["provisional_eligibility"] = "ELIGIBLE_FOR_USER_REVIEW"
        self.assertFalse(validator.is_valid(value))
        value["provisional_eligibility"] = "WORKAROUND_DISPOSITION_REQUIRED"
        value["carried_results"]["P7.1"] = "PASS"
        self.assertFalse(validator.is_valid(value))

    def test_p3_catalog_is_exact_deterministic_fallback_30_of_30(self) -> None:
        catalog = json.loads(CATALOG.read_text())
        count = 0
        for entry in catalog["failure_raw_outputs"]:
            observed = [
                normalize_response(entry["raw"], STANDARD_INPUT, refused=entry["refused"])
                for _ in range(catalog["repetitions"])
            ]
            self.assertTrue(all(item == observed[0] for item in observed))
            self.assertTrue(all(item[0] == catalog["expected_fallback"] for item in observed))
            count += len(observed)
        self.assertEqual(count, 30)

    def test_p2_exact_disposition_rejects_wrong_tool(self) -> None:
        entry = {"expected_kind": "tool", "tool": "device.light.on"}
        metrics = {"prefill_tokens":20,"decode_tokens":10,"kv_tokens":30}
        good = {"type":"RESULT","response":{"action_kind":"tool","action_payload":{"name":"device.light.on"}},"metrics":metrics}
        bad = {"type":"RESULT","response":{"action_kind":"tool","action_payload":{"name":"device.light.off"}},"metrics":metrics}
        fallback = {"action_kind":"speak","action_payload":{"text":"Sorry, please try again."},"next_perceptions":["listen"]}
        self.assertTrue(p2_valid(good, entry, fallback, engine_capacity=512, max_output_tokens=64))
        self.assertFalse(p2_valid(bad, entry, fallback, engine_capacity=512, max_output_tokens=64))
        self.assertFalse(p2_valid({"type":"RESULT","response":fallback,"metrics":metrics}, {"expected_kind":"speak"}, fallback, engine_capacity=512, max_output_tokens=64))

    def test_p4_summary_uses_required_3_cold_and_20_hot_metrics(self) -> None:
        cold = [{"wall_ms": float(value)} for value in (3, 1, 2)]
        hot = [
            {"wall_ms": float(value), "metrics": {"ttft_ms": float(value), "decode_tokens_per_second": 5.0}}
            for value in range(1, 21)
        ]
        summary = p4_summary(cold, hot)
        self.assertEqual(summary["cold_wall_p50_ms"], 2.0)
        self.assertEqual(summary["ttft_p95_ms"], 19.0)
        self.assertEqual(summary["decode_p50_tokens_per_second"], 5.0)

    def test_p5_backend_cancels_once_then_serves_one_shot_health(self) -> None:
        fake_module = types.SimpleNamespace(
            Backend=types.SimpleNamespace(CPU=lambda **_kwargs: object()),
            Engine=Engine,
            SamplerConfig=lambda **_kwargs: object(),
        )
        stderr = io.StringIO()
        with patch.dict(sys.modules, {"litert_lm": fake_module}), patch("sys.stderr", stderr):
            from poc_llm.harness.litert_lm_pi_p5_child_adapter_v1 import LiteRtContinuousBackend

            backend = LiteRtContinuousBackend({
                "model_path":"/model", "threads":4, "engine_max_num_tokens":1024,
                "temperature":0.0, "top_p":1.0,
            })
            caught: list[Exception] = []

            def run() -> None:
                try:
                    backend.generate("prompt", max_output_tokens=512)
                except Exception as error:
                    caught.append(error)

            worker = threading.Thread(target=run)
            worker.start()
            while not backend._engine.created:
                pass
            backend.cancel()
            backend.cancel()
            worker.join(2)
            self.assertFalse(worker.is_alive())
            self.assertIsInstance(caught[0], Cancelled)
            self.assertEqual(backend._engine.created[0].cancel_count, 1)
            health = backend.generate("health", max_output_tokens=16)
            self.assertEqual(health.text, "chunk")
            backend.close()
        self.assertEqual(stderr.getvalue().count("P5_EVENT native_cancel_once"), 1)
        self.assertEqual(stderr.getvalue().count("P5_EVENT continuous_terminal_cancelled"), 1)

    def test_p5_no_or_late_terminal_is_fail_but_early_result_is_definition_inconclusive(self) -> None:
        self.assertEqual(
            p5_result_disposition(
                {"type":"NO_TERMINAL"}, 17500.0,
                markers_ok=False, health_ok=False, rebuild_ok=True,
            ),
            "FAIL",
        )
        self.assertEqual(
            p5_result_disposition(
                {"type":"ERROR","code":"TIMEOUT","request_id":"p5-continuous"},
                17000.001, markers_ok=True, health_ok=True, rebuild_ok=True,
            ),
            "FAIL",
        )
        self.assertEqual(
            p5_result_disposition(
                {"type":"RESULT"}, 14000.0,
                markers_ok=False, health_ok=True, rebuild_ok=True,
            ),
            "INCONCLUSIVE",
        )

    def test_runner_only_scores_remaining_items_and_freezes_p5(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        fixture = json.loads(P5_FIXTURE.read_text())
        self.assertEqual(fixture["completed_chunk_disposition"], "CONTINUE")
        self.assertEqual(fixture["timeout_pass_window_ms"], [15000, 17000])
        self.assertIn('EXECUTED_ITEMS = ("P2", "P3", "P4", "P5", "P8")', source)
        self.assertNotIn('executed_results"]["P6', source)
        self.assertNotIn('executed_results"]["P7', source)
        adapter_source = P5_ADAPTER.read_text(encoding="utf-8")
        self.assertIn("conversation.send_message_async(prompt)", adapter_source)
        self.assertIn("while True:", adapter_source)
        self.assertIn("conversation.cancel_process()", adapter_source)
        self.assertIn('current_marker_present_once', source)

    def test_preexisting_run_paths_are_rejected_without_deletion(self) -> None:
        run_id = f"g2a-ownership-{uuid.uuid4().hex}"
        install = Path(f"/tmp/llm-poc-g2a-002/install-{run_id}")
        install.mkdir(parents=True)
        try:
            with tempfile.TemporaryDirectory() as directory:
                evidence = Path(directory)
                raw = evidence / run_id
                raw.mkdir()
                argv = [
                    "run_gate2a_pi_v2.py", "--packet-lock", str(LOCK),
                    "--gate1-entry", str(ENTRY), "--artifact-receipt", str(raw / "receipt.json"),
                    "--candidate-id", CANDIDATES[0], "--execution-sha", "a" * 40,
                    "--run-id", run_id, "--evidence-root", str(evidence),
                ]
                with patch.object(sys, "argv", argv), patch("sys.stdout", io.StringIO()):
                    self.assertEqual(gate2a_main(), 2)
                self.assertTrue(raw.is_dir())
                self.assertTrue(install.is_dir())
        finally:
            if install.exists():
                shutil.rmtree(install)


if __name__ == "__main__":
    unittest.main()
