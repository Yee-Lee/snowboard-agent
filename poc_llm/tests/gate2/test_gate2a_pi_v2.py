from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
import uuid
from unittest.mock import patch

from jsonschema import Draft202012Validator

from poc_llm.harness.litert_lm_child_adapter import Cancelled
from poc_llm.harness.litert_lm_pi_child_adapter import PiChild
from poc_llm.harness.gate2_errors_v1 import CandidateViolation, EvidenceInvalid, error_result
from poc_llm.harness.pi_runtime import PiPacketFailure
from poc_llm.harness.m1_contract_boundary import normalize_response
from poc_llm.tools.run_gate2a_pi_v2 import (
    CANDIDATES,
    EXECUTED_ITEMS,
    STANDARD_INPUT,
    p2_valid,
    p5_result_disposition,
    p5_runner_disposition,
    ready_observation_config,
    valid_run_id as valid_gate2a_run_id,
    p4_summary,
    scan_owned_logs,
    scored_generate,
    scored_pong,
    scored_close_child,
    verify_gate2a_result,
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
    metrics = {"prefill_tokens":8,"decode_tokens":4,"kv_tokens":12,
               "ttft_ms":1.0,"decode_tokens_per_second":5.0}
    cold = {"ready_ms":1.0,"wall_ms":1.0,"metrics":dict(metrics),
            "resources":{"pss_mib":1.0},
            "thermal":{"temperature_c":50.0,"throttled":"0x0"}}
    warm = {"wall_ms":1.0,"metrics":dict(metrics)}
    hot = {**warm,"resources":{"pss_mib":1.0},
           "thermal":{"temperature_c":50.0,"throttled":"0x0"}}
    return {
        "p2":{"ready_ms":1.0,"cases":[
            {"id":f"P2-{case:03d}","repetition":rep,"wall_ms":1.0,"valid":True,
             "prefill_tokens":8,"decode_tokens":4,"kv_tokens":12,"response_sha256":"a"*64}
            for case in range(1,11) for rep in range(3)
        ],"error_type":None},
        "p3":[{"id":f"P3-{case:03d}","repetitions":3,"deterministic":True,
               "fallback":True,"diagnostic_sha256":"b"*64} for case in range(11,21)],
        "p4":{"resident_ready_ms":1.0,"cold":[dict(cold) for _ in range(3)],
              "warmups":[dict(warm) for _ in range(3)],"hot":[dict(hot) for _ in range(20)],
              "summary":{"cold_wall_p50_ms":1.0,"hot_wall_p50_ms":1.0,
                "hot_wall_p95_ms":1.0,"ttft_p50_ms":1.0,"ttft_p95_ms":1.0,
                "decode_p50_tokens_per_second":5.0,"decode_p95_tokens_per_second":5.0},
              "failures":[]},
        "p5":{"ready_ms":1.0,"terminal":"ERROR","code":"TIMEOUT","elapsed_ms":15000.0,
              "observation_error_type":None,"candidate_error_type":None,
              "timeout_mode":"ACTIVE_CHUNK_CANCEL",
              "marker_counts":{"chunk_started":1,"chunk_completed":0,"native_cancel_once":1,
                "native_cancel_failed":0,
                "timeout_between_chunks":0,"continuous_terminal_cancelled":1,
                "conversation_discarded":1},"same_child_pong":"PONG",
              "same_child_health_terminal":"RESULT","same_child_health_ms":1.0,
              "rebuild_ready_ms":1.0,"rebuild_health_terminal":"RESULT",
              "rebuild_health_ms":1.0,"rebuild_error_type":None,
              "rebuild_candidate_error_type":None},
        "p8":{"ready_ms":1.0,"cases":[
            {"id":f"P8-{case:03d}","wall_ms":1.0,"terminal":"RESULT",
             "response_sha256":"c"*64,"prior_marker_leaked":False,
             "current_marker_present_once":True,"current_trap_absent":True,
             "prefill_tokens":8,"decode_tokens":4,"kv_tokens":12,"kv_is_single_turn":True}
            for case in range(1,6)],"error_type":None},
        "log_hygiene":{"passed":True,"scanned_files":[{"name":"standard.stderr","sha256":"d"*64}],
                       "static_marker_count":7,"runtime_marker_count":31},
    }


def complete_cleanup() -> dict:
    value = {
        name:dict(CLEANUP_PROOF)
        for name in ("p2","standard","p8","p5_same_child","p5_rebuild")
    }
    value["p4_cold"] = [dict(CLEANUP_PROOF) for _ in range(3)]
    return value


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
        self.close_count = 0
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
        self.close_count += 1


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
        self.assertEqual(lock["ready_observation_ms"], {
            "default": 10000,
            CANDIDATES[1]: 30000,
        })
        for item in lock["artifacts"].values():
            path = ROOT / item["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"], path)
        for candidate in lock["candidates"].values():
            for item in candidate.values():
                path = ROOT / item["path"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"], path)

    def test_ready_observation_is_controller_only_and_forbids_gate_credit(self) -> None:
        policy = {"default": 10000, CANDIDATES[1]: 30000}
        frozen = {"candidate_id": CANDIDATES[1], "ready_timeout_ms": 10000, "threads": 4}
        observed, metadata = ready_observation_config(frozen, CANDIDATES[1], policy)
        self.assertEqual(frozen["ready_timeout_ms"], 10000)
        self.assertEqual(observed["ready_timeout_ms"], 30000)
        self.assertEqual(observed["threads"], frozen["threads"])
        self.assertEqual(metadata, {
            "contract_ms": 10000,
            "operational_ms": 30000,
            "workaround": "P1.2_COLD_READY_OBSERVATION",
            "gate_credit": "FORBIDDEN",
        })

        gemma, gemma_metadata = ready_observation_config(frozen, CANDIDATES[0], policy)
        self.assertEqual(gemma["ready_timeout_ms"], 10000)
        self.assertEqual(gemma_metadata["workaround"], "NONE")

    def test_ready_observation_rejects_contract_or_policy_relaxation(self) -> None:
        with self.assertRaises(PiPacketFailure):
            ready_observation_config(
                {"ready_timeout_ms": 9000}, CANDIDATES[1],
                {"default": 10000, CANDIDATES[1]: 30000},
            )
        with self.assertRaises(PiPacketFailure):
            ready_observation_config(
                {"ready_timeout_ms": 10000}, CANDIDATES[1],
                {"default": 10000, CANDIDATES[1]: 5000},
            )

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

    def test_p5_between_chunks_timeout_is_deterministic_without_native_cancel(self) -> None:
        class FastEngine(Engine):
            def create_conversation(self, **_kwargs) -> Conversation:
                value = Conversation(blocking=False)
                self.created.append(value)
                return value

        fake_module = types.SimpleNamespace(
            Backend=types.SimpleNamespace(CPU=lambda **_kwargs: object()),
            Engine=FastEngine, SamplerConfig=lambda **_kwargs: object(),
        )
        reached, release = threading.Event(), threading.Event()
        stderr = io.StringIO()
        with patch.dict(sys.modules, {"litert_lm": fake_module}), patch("sys.stderr", stderr):
            from poc_llm.harness.litert_lm_pi_p5_child_adapter_v1 import LiteRtContinuousBackend
            backend = LiteRtContinuousBackend({"model_path":"/model","threads":4,
                "engine_max_num_tokens":1024,"temperature":0.0,"top_p":1.0})
            backend._between_chunks_hook = lambda: (reached.set(), release.wait(2))
            caught: list[Exception] = []
            worker = threading.Thread(target=lambda: self._capture_error(
                caught, lambda: backend.generate("prompt", max_output_tokens=512)
            ))
            worker.start()
            self.assertTrue(reached.wait(1))
            backend.cancel()
            release.set()
            worker.join(2)
        self.assertIsInstance(caught[0], Cancelled)
        self.assertEqual(stderr.getvalue().count("P5_EVENT native_cancel_once"), 0)
        self.assertEqual(stderr.getvalue().count("P5_EVENT timeout_between_chunks"), 1)

    def test_p5_completion_arbitration_has_only_two_valid_schedules(self) -> None:
        class FastEngine(Engine):
            def create_conversation(self, **_kwargs) -> Conversation:
                value = Conversation(blocking=False)
                self.created.append(value)
                return value

        fake_module = types.SimpleNamespace(
            Backend=types.SimpleNamespace(CPU=lambda **_kwargs: object()),
            Engine=FastEngine, SamplerConfig=lambda **_kwargs: object(),
        )
        for hook_name, expected_native, expected_completed, expected_boundary in (
            ("_before_completion_arbitration_hook", 1, 0, 0),
            ("_after_completion_arbitration_hook", 0, 1, 1),
        ):
            with self.subTest(hook=hook_name):
                reached, release = threading.Event(), threading.Event()
                stderr = io.StringIO()
                with patch.dict(sys.modules, {"litert_lm": fake_module}), patch("sys.stderr", stderr):
                    from poc_llm.harness.litert_lm_pi_p5_child_adapter_v1 import LiteRtContinuousBackend
                    backend = LiteRtContinuousBackend({"model_path":"/model","threads":4,
                        "engine_max_num_tokens":1024,"temperature":0.0,"top_p":1.0})
                    setattr(backend, hook_name, lambda: (reached.set(), release.wait(2)))
                    caught: list[Exception] = []
                    worker = threading.Thread(target=lambda: self._capture_error(
                        caught, lambda: backend.generate("prompt", max_output_tokens=512)
                    ))
                    worker.start()
                    self.assertTrue(reached.wait(1))
                    backend.cancel()
                    release.set()
                    worker.join(2)
                    self.assertFalse(worker.is_alive())
                    self.assertIsInstance(caught[0], Cancelled)
                    health = backend.generate("health", max_output_tokens=16)
                    self.assertEqual(health.text, "chunk")
                    backend.close()
                    rebuild = LiteRtContinuousBackend({"model_path":"/model","threads":4,
                        "engine_max_num_tokens":1024,"temperature":0.0,"top_p":1.0})
                    rebuilt_health = rebuild._chunk("health", 16, 0)
                    self.assertEqual(rebuilt_health.text, "chunk")
                    rebuild.close()
                    self.assertTrue(all(
                        conversation.close_count >= 1
                        for conversation in backend._engine.created + rebuild._engine.created
                    ))
                markers = stderr.getvalue()
                self.assertEqual(markers.count("P5_EVENT native_cancel_once"), expected_native)
                # One completion is same-child health and one is the fresh rebuild probe.
                self.assertEqual(markers.count("P5_EVENT chunk_completed"), expected_completed + 2)
                self.assertEqual(markers.count("P5_EVENT timeout_between_chunks"), expected_boundary)
                self.assertEqual(markers.count("P5_EVENT continuous_terminal_cancelled"), 1)

    def test_native_cancel_lifetime_is_reserved_until_success_or_failure(self) -> None:
        class LifetimeConversation(Conversation):
            def __init__(self, fail: bool):
                super().__init__(blocking=False)
                self.fail = fail
                self.finish_generation = threading.Event()
                self.native_entered = threading.Event()
                self.native_release = threading.Event()

            def send_message_async(self, _prompt: str):
                yield {"text":"chunk"}
                self.finish_generation.wait(2)

            def cancel_process(self) -> None:
                self.cancel_count += 1
                self.native_entered.set()
                self.native_release.wait(2)
                self.cancelled.set()
                if self.fail:
                    raise RuntimeError("injected native cancel failure")

        for fail in (False, True):
            with self.subTest(native_failure=fail):
                conversation = LifetimeConversation(fail)

                class LifetimeEngine(Engine):
                    def create_conversation(self, **_kwargs):
                        self.created.append(conversation)
                        return conversation

                fake_module = types.SimpleNamespace(
                    Backend=types.SimpleNamespace(CPU=lambda **_kwargs: object()),
                    Engine=LifetimeEngine, SamplerConfig=lambda **_kwargs: object(),
                )
                stderr = io.StringIO()
                with patch.dict(sys.modules, {"litert_lm":fake_module}), patch("sys.stderr", stderr):
                    from poc_llm.harness.litert_lm_pi_p5_child_adapter_v1 import LiteRtContinuousBackend
                    backend = LiteRtContinuousBackend({"model_path":"/model","threads":4,
                        "engine_max_num_tokens":1024,"temperature":0.0,"top_p":1.0})
                    finalization_reached = threading.Event()
                    backend._before_conversation_close_hook = finalization_reached.set
                    caught: list[Exception] = []
                    worker = threading.Thread(target=lambda: self._capture_error(
                        caught, lambda: backend.generate("prompt", max_output_tokens=512)))
                    worker.start()
                    while not backend._engine.created:
                        pass
                    cancel_errors: list[Exception] = []
                    canceller = threading.Thread(target=lambda: self._capture_error(
                        cancel_errors, backend.cancel))
                    canceller.start()
                    self.assertTrue(conversation.native_entered.wait(1))
                    conversation.finish_generation.set()
                    self.assertTrue(finalization_reached.wait(1))
                    self.assertTrue(worker.is_alive())
                    self.assertEqual(conversation.close_count, 0)
                    conversation.native_release.set()
                    canceller.join(2)
                    worker.join(2)
                    self.assertFalse(canceller.is_alive())
                    self.assertFalse(worker.is_alive())
                    self.assertEqual(cancel_errors, [])
                    self.assertEqual(conversation.cancel_count, 1)
                    self.assertEqual(conversation.close_count, 1)
                markers = stderr.getvalue()
                self.assertEqual(markers.count("P5_EVENT native_cancel_once"), 0 if fail else 1)
                self.assertEqual(markers.count("P5_EVENT native_cancel_failed"), 1 if fail else 0)
                if fail:
                    self.assertEqual(p5_runner_disposition(
                        {"type":"ERROR","code":"TIMEOUT","request_id":"p5-continuous"},
                        16000.0, markers_ok=False, health_ok=True, rebuild_ok=True,
                        candidate_error=None, observation_error=None,
                        rebuild_candidate_error=None, rebuild_observation_error=None,
                    ), "FAIL")

    def test_p5_protocol_integration_cancel_and_completion_first(self) -> None:
        class FastEngine(Engine):
            def create_conversation(self, **_kwargs):
                value = Conversation(blocking=False)
                self.created.append(value)
                return value

        for mode, engine_type in (("active", Engine), ("boundary", FastEngine)):
            with self.subTest(mode=mode):
                fake_module = types.SimpleNamespace(
                    Backend=types.SimpleNamespace(CPU=lambda **_kwargs: object()),
                    Engine=engine_type, SamplerConfig=lambda **_kwargs: object(),
                )
                output, stderr = io.StringIO(), io.StringIO()
                with patch.dict(sys.modules, {"litert_lm":fake_module}), patch("sys.stderr", stderr):
                    from poc_llm.harness.litert_lm_pi_p5_child_adapter_v1 import LiteRtContinuousBackend
                    config = {"model_path":"/model","threads":4,"engine_max_num_tokens":1024,
                        "temperature":0.0,"top_p":1.0,"max_output_tokens":16,
                        "generate_timeout_ms":20,"term_timeout_ms":1000,
                        "candidate_id":"candidate","pairing_revision":"r1","platform":"pi",
                        "runtime_sha256":"a"*64,"model_sha256":"b"*64}
                    backend = LiteRtContinuousBackend(config)
                    if mode == "boundary":
                        backend._between_chunks_hook = lambda: self._wait_cancel_requested(backend)
                    child = PiChild(config, "c"*64, backend, output)
                    child.protocol = types.SimpleNamespace(iter_errors=lambda _frame: [])
                    request = {"type":"GENERATE","protocol_version":"snowboard.llm/1",
                        "request_id":"p5-continuous","input":STANDARD_INPUT}
                    self.assertTrue(child.handle(request))
                    child.worker.join(2)
                    self.assertFalse(child.worker.is_alive())
                    frames = [json.loads(line) for line in output.getvalue().splitlines()]
                    self.assertEqual(frames[-1]["type"], "ERROR")
                    self.assertEqual(frames[-1]["code"], "TIMEOUT")
                    self.assertEqual(frames[-1]["request_id"], "p5-continuous")
                    self.assertTrue(child.handle({"type":"PING","protocol_version":"snowboard.llm/1"}))
                    self.assertTrue(child.handle({**request,"request_id":"p5-health"}))
                    child.worker.join(2)
                    frames = [json.loads(line) for line in output.getvalue().splitlines()]
                    self.assertEqual(frames[-1]["type"], "RESULT")
                    self.assertFalse(child.handle({"type":"SHUTDOWN","protocol_version":"snowboard.llm/1"}))
                    child.close()
                    rebuild = LiteRtContinuousBackend(config)
                    self.assertEqual(rebuild._chunk("health", 16, 0).text, "chunk")
                    rebuild.close()
                markers = stderr.getvalue()
                self.assertEqual(markers.count("P5_EVENT native_cancel_failed"), 0, markers)
                self.assertEqual(markers.count("P5_EVENT native_cancel_once"), 1 if mode == "active" else 0)
                self.assertEqual(markers.count("P5_EVENT timeout_between_chunks"), 0 if mode == "active" else 1)

    @staticmethod
    def _wait_cancel_requested(backend) -> None:
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            with backend._lock:
                if backend._cancel_requested:
                    return
            time.sleep(0.001)
        raise AssertionError("controlled timeout did not request cancellation")

    def test_scored_generate_maps_actual_post_ready_protocol_faults_to_fail(self) -> None:
        for message in (
            "protocol frame deadline exceeded",
            "candidate stdout closed",
            "candidate emitted invalid JSONL",
            "candidate emitted protocol-invalid frame",
        ):
            with self.subTest(message=message), patch(
                "poc_llm.tools.run_gate2a_pi_v2.generate",
                side_effect=PiPacketFailure(message),
            ):
                with self.assertRaises(CandidateViolation) as caught:
                    scored_generate(object(), object(), "p5-continuous", {})
                self.assertEqual(error_result(caught.exception), "FAIL")
        self.assertEqual(error_result(EvidenceInvalid("probe")), "INCONCLUSIVE")

    def test_scored_pipe_ping_and_shutdown_exception_matrix(self) -> None:
        process = types.SimpleNamespace(stdout=object())
        for error in (BrokenPipeError("closed"), ConnectionResetError("reset")):
            with self.subTest(kind=type(error).__name__), patch(
                "poc_llm.tools.run_gate2a_pi_v2.generate", side_effect=error,
            ), self.assertRaises(CandidateViolation):
                scored_generate(process, object(), "p5", {})
            with patch("poc_llm.tools.run_gate2a_pi_v2.send", side_effect=error), \
                    self.assertRaises(CandidateViolation):
                scored_pong(process, object())
        timeout = subprocess.TimeoutExpired(["child"], 2)
        with patch("poc_llm.tools.run_gate2a_pi_v2.close_child", side_effect=timeout), \
                self.assertRaises(CandidateViolation):
            scored_close_child(process, object())

    def test_p5_two_stage_precedence_matrix(self) -> None:
        valid = {"type":"ERROR","code":"TIMEOUT","request_id":"p5-continuous"}
        cases = (
            (valid, True, True, "CandidateViolation", None, None, "OSError", True, "FAIL"),
            (valid, False, True, None, None, None, "OSError", True, "FAIL"),
            (valid, True, True, None, "OSError", "CandidateViolation", None, True, "INCONCLUSIVE"),
            (valid, True, True, None, None, "CandidateViolation", None, True, "FAIL"),
            (valid, True, True, None, None, None, "OSError", True, "INCONCLUSIVE"),
            (valid, True, True, None, None, None, None, False, "FAIL"),
            (valid, True, True, None, None, None, None, True, "PASS"),
            ({"type":"RESULT"}, False, True, None, "PacketDefect", None, None, True, "INCONCLUSIVE"),
        )
        for terminal, markers, health, candidate, observation, rebuild_candidate, rebuild_observation, rebuild_ok, expected in cases:
            with self.subTest(expected=expected, candidate=candidate, observation=observation):
                self.assertEqual(p5_runner_disposition(
                    terminal, 16000.0 if terminal is valid else 14000.0,
                    markers_ok=markers, health_ok=health, rebuild_ok=rebuild_ok,
                    candidate_error=candidate, observation_error=observation,
                    rebuild_candidate_error=rebuild_candidate,
                    rebuild_observation_error=rebuild_observation,
                ), expected)
                evidence = complete_samples()
                p5 = evidence["p5"]
                p5.update({
                    "terminal":terminal.get("type"), "code":terminal.get("code"),
                    "elapsed_ms":16000.0 if terminal is valid else 14000.0,
                    "candidate_error_type":candidate,
                    "observation_error_type":observation,
                    "rebuild_candidate_error_type":rebuild_candidate,
                    "rebuild_error_type":rebuild_observation,
                    "rebuild_health_terminal":"RESULT" if rebuild_ok else "ERROR",
                })
                if not markers:
                    p5["marker_counts"]["native_cancel_once"] = 0
                if not health:
                    p5["same_child_health_terminal"] = "ERROR"
                catalog = json.loads(CATALOG.read_text())
                p8 = json.loads((ROOT / "poc_llm/fixtures/gate2/p8-state-isolation-001.json").read_text())
                observed = verify_gate2a_result(
                    {"samples":evidence,"cleanup":complete_cleanup(),
                     "executed_results":{"P2":"PASS","P3":"PASS","P4":"PASS",
                                         "P5":expected,"P8":"PASS"}},
                    catalog, p8, engine_capacity=1024, max_output_tokens=64,
                )
                self.assertEqual(observed["P5"], expected)

    def test_p5_real_runner_path_distinguishes_no_late_terminal_and_probe_fault(self) -> None:
        with patch(
            "poc_llm.tools.run_gate2a_pi_v2.generate",
            side_effect=PiPacketFailure("protocol frame deadline exceeded"),
        ):
            with self.assertRaises(CandidateViolation) as no_terminal:
                scored_generate(object(), object(), "p5-continuous", {})
        self.assertEqual(p5_runner_disposition(
            {"type":"NO_TERMINAL"}, 17500.0, markers_ok=False, health_ok=False,
            rebuild_ok=True, candidate_error=type(no_terminal.exception).__name__,
            observation_error=None, rebuild_candidate_error=None,
            rebuild_observation_error=None,
        ), "FAIL")

        late = {"type":"ERROR","code":"TIMEOUT","request_id":"p5-continuous"}
        with patch("poc_llm.tools.run_gate2a_pi_v2.generate", return_value=(late, 17000.001)):
            terminal, elapsed = scored_generate(object(), object(), "p5-continuous", {})
        self.assertEqual(p5_runner_disposition(
            terminal, elapsed, markers_ok=True, health_ok=True, rebuild_ok=True,
            candidate_error=None, observation_error=None, rebuild_candidate_error=None,
            rebuild_observation_error=None,
        ), "FAIL")

        with patch("poc_llm.tools.run_gate2a_pi_v2.generate", side_effect=OSError("probe I/O")):
            with self.assertRaises(OSError) as probe:
                scored_generate(object(), object(), "p5-continuous", {})
        self.assertEqual(p5_runner_disposition(
            {"type":"NO_TERMINAL"}, 1.0, markers_ok=False, health_ok=False,
            rebuild_ok=False, candidate_error=None,
            observation_error=type(probe.exception).__name__, rebuild_candidate_error=None,
            rebuild_observation_error=None,
        ), "INCONCLUSIVE")

    @staticmethod
    def _capture_error(target: list[Exception], operation) -> None:
        try:
            operation()
        except Exception as error:
            target.append(error)

    def test_independent_verifier_rejects_mutated_pass_samples(self) -> None:
        catalog = json.loads(CATALOG.read_text())
        p8 = json.loads((ROOT / "poc_llm/fixtures/gate2/p8-state-isolation-001.json").read_text())
        value = {"samples":complete_samples(),"cleanup":complete_cleanup(),
                 "executed_results":{"P2":"PASS","P3":"PASS","P4":"PASS","P5":"PASS","P8":"PASS"}}
        self.assertEqual(verify_gate2a_result(
            value, catalog, p8, engine_capacity=1024, max_output_tokens=64
        )["P5"], "PASS")
        mutations = [
            lambda copy: copy["samples"]["p2"]["cases"].pop(),
            lambda copy: copy["samples"]["p3"][0].update({"fallback":False}),
            lambda copy: copy["samples"]["p4"]["hot"][0].pop("metrics"),
            lambda copy: copy["samples"]["p5"]["marker_counts"].update({"native_cancel_once":0}),
            lambda copy: copy["samples"]["p8"]["cases"][0].update({"prior_marker_leaked":True}),
        ]
        for mutate in mutations:
            changed = json.loads(json.dumps(value))
            mutate(changed)
            with self.assertRaises(EvidenceInvalid):
                verify_gate2a_result(
                    changed, catalog, p8, engine_capacity=1024, max_output_tokens=64
                )

    def test_runtime_p8_canary_leak_is_detected_without_persisting_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "standard.stderr"
            path.write_text("diagnostic P8N00003 only", encoding="utf-8")
            report = scan_owned_logs(Path(directory), {"P8N00003"})
        self.assertFalse(report["passed"])
        self.assertNotIn("P8N00003", json.dumps(report))

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

    def test_preflight_failure_is_preserved_before_model_access(self) -> None:
        run_id = f"g2a-preflight-{uuid.uuid4().hex}"
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory)
            argv = [
                "run_gate2a_pi_v2.py", "--packet-lock", str(LOCK),
                "--gate1-entry", str(ENTRY),
                "--artifact-receipt", str(evidence / "unused-receipt.json"),
                "--candidate-id", CANDIDATES[1], "--execution-sha", "a" * 40,
                "--run-id", run_id, "--evidence-root", str(evidence),
            ]
            output = io.StringIO()
            with patch.object(sys, "argv", argv), patch("sys.stdout", output), \
                    patch("poc_llm.tools.run_gate2a_pi_v2.ancestor_check"), \
                    patch("poc_llm.tools.run_gate2a_pi_v2.isolation_state", return_value={
                        "boot_id_sha256": "b" * 64,
                        "prelaunch_uptime_s": 1.0,
                        "preexisting_adapter_processes": 0,
                    }), patch(
                        "poc_llm.tools.run_gate2a_pi_v2.target_preflight",
                        side_effect=PiPacketFailure("controlled preflight failure"),
                    ):
                self.assertEqual(gate2a_main(), 2)
            preserved = evidence / run_id / "gate2a-sanitized.json"
            self.assertTrue(preserved.is_file())
            value = json.loads(preserved.read_text(encoding="utf-8"))
            self.assertEqual(value["result"], "INCONCLUSIVE")
            self.assertEqual(value["executed_results"], {
                item: "Blocked" for item in EXECUTED_ITEMS
            })
            self.assertEqual(value["artifact_authentication"], {})


if __name__ == "__main__":
    unittest.main()
