from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from poc_llm.harness.mva_controller import CATALOG, Controller, ORDER, steady_analysis, verify_next_case
from poc_llm.harness.mva_evidence import EvidenceError, EvidenceWriter, fill_missing_reasons, validate_sample
from poc_llm.harness.mva_process import Child, RunError
from poc_llm.harness.mva_resources import stop_reason


class Sampler:
    initial_swap = 0
    def sample(self, owners):
        return {"owner_pss_mib": 100.0 if owners else None, "owner_rss_mib": 110.0 if owners else None,
                "mem_total_mib": 4000.0, "mem_available_mib": 3000.0, "system_used_mib": 1000.0,
                "swap_used_kib": 0, "temperature_c": 40.0, "throttled": "0x0", "oom_or_kernel_fault": False}


class Writer:
    def __init__(self):
        self.rows, self.checkpoints = [], []
    def append(self, sample, *, checkpoint=False):
        validate_sample(sample)
        (self.checkpoints if checkpoint else self.rows).append(deepcopy(sample))


class FakeChild:
    def __init__(self, *args, **kwargs):
        self.calls = []
        self.closed = False
        self.active_session = None
    def owners(self):
        return [] if self.closed else [123]
    def send(self, request):
        self.calls.append(request)
    def receive(self, timeout, monitor=lambda: None):
        monitor()
        cases = [CATALOG["timing"], CATALOG["prewarm"], *CATALOG["development_semantics"]]
        return {"terminal": "ENGINE_READY", "census": {case["case_id"]: [10] * len(case["turns"]) for case in cases}}
    def call(self, op, *, timeout=30, monitor=lambda: None, **kwargs):
        self.calls.append({"op": op, **kwargs})
        monitor()
        if op == "OPEN":
            assert self.active_session is None
            self.active_session = kwargs["session"]
            return {"terminal": "SESSION_OPENED", "metrics": {"open_ms": 1.0, "initial_kv_tokens": 10}}
        if op == "CLOSE":
            assert self.active_session == kwargs["session"]
            self.active_session = None
            return {"terminal": "SESSION_CLOSED", "metrics": {"close_ms": 1.0}}
        if op == "PREWARM":
            assert self.active_session is None
            return {"terminal": "READY", "metrics": {}}
        assert self.active_session == kwargs["session"]
        return {"terminal": "RESULT", "semantic": {"text": "PUBLIC_FAKE_RESPONSE", "end": False},
                "metrics": {"ttft_ms": 1.0, "ttc_ms": 2.0, "new_user_tokens": 10,
                            "rendered_tokens": 20, "incremental_tokens": 20, "kv_tokens": 30, "output_tokens": 5}}
    def cleanup(self):
        self.closed = True
        return {"status": "PASS", "owners_absent": True, "alsa_owners_zero": None, "cooperative": True, "exit_code": 0}


def controller(case="cold-N1", **kwargs):
    writer = kwargs.pop("writer", Writer())
    identity = {key: "a" * 64 for key in ("plan_sha256", "surface_sha256", "profile_sha256", "semantic_schema_sha256",
        "wire_schema_sha256", "config_sha256", "model_sha256", "runtime_sha256",
        "product_storage_sha256", "cache_key")}
    identity["audio_sha256"] = None
    return Controller(case=case, run_id="MVA-001-" + case, implementation_sha="b" * 40, identity=identity,
        config={"model_path": "/unused-artifact/payload", "runtime_root": "/unused-runtime",
                "runtime_native_library": "/unused-runtime/lib/python3.13/site-packages/litert_lm/liblitert-lm.so",
                "cache_root": "/unused-cache", "active_cache_key": "c" * 64},
        writer=writer, sampler=kwargs.pop("sampler", Sampler()), verify_install=kwargs.pop("verify_install", lambda: None),
        child_factory=kwargs.pop("child_factory", FakeChild), **kwargs)


class ControllerTests(unittest.TestCase):
    def test_child_receives_run_owned_litertlm_presentation_path(self):
        children = []
        def factory(*args, **kwargs):
            child = FakeChild()
            children.append(child)
            return child
        subject = controller(child_factory=factory)
        self.assertEqual(subject.run()["status"], "PASS")
        model_path = Path(children[0].calls[0]["config"]["model_path"])
        self.assertEqual(model_path.name, "model.litertlm")
        self.assertFalse(model_path.exists())

    def test_normal_two_turn_session_costs_and_sanitization(self):
        subject = controller()
        result = subject.run()
        self.assertEqual(result["status"], "PASS")
        rows = subject.writer.rows
        self.assertEqual([r["turn_id"] for r in rows if r["terminal"] == "RESULT"], [1, 2])
        self.assertEqual(sum(r["terminal"] == "SESSION_CLOSED" for r in rows), 1)
        self.assertNotIn("PUBLIC_FAKE_RESPONSE", json.dumps(rows))
        self.assertNotIn(CATALOG["timing"]["turns"][0], json.dumps(rows))
        self.assertTrue(all(r["cleanup"]["owners_absent"] for r in rows))
        self.assertTrue(result["token_census"])

    def test_memory_twenty_sessions_one_child_fixed_window(self):
        subject = controller("memory-1")
        result = subject.run()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(subject.generation, 1)
        self.assertEqual(sum(r["terminal"] == "RESULT" for r in subject.rows), 40)
        self.assertEqual(result["steady_analysis"]["window"], list(range(11, 21)))
        self.assertEqual(result["steady_analysis"]["metrics"]["owner_pss_mib"]["ols_mib_per_session"], 0)
        self.assertEqual(steady_analysis(subject.rows[:10])["status"], "Incomplete")

    def test_once_prewarm_precedes_product_open(self):
        children = []
        def factory(*args, **kwargs):
            child = FakeChild()
            children.append(child)
            return child
        subject = controller("cold-O1", child_factory=factory)
        self.assertEqual(subject.run()["status"], "PASS")
        operations = [call["op"] for call in children[0].calls]
        self.assertLess(operations.index("PREWARM"), operations.index("OPEN"))
        self.assertEqual(operations.count("PREWARM"), 1)

    def test_recovery_waits_for_old_owner_exit(self):
        children = []
        def factory(*args, **kwargs):
            self.assertTrue(all(child.closed for child in children))
            child = FakeChild()
            children.append(child)
            return child
        subject = controller("recovery-1", child_factory=factory)
        self.assertEqual(subject.run()["status"], "PASS")
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0].calls[0]["config"], children[1].calls[0]["config"])
        self.assertEqual(sum(r["terminal"] == "RECOVERY_READY" for r in subject.rows), 1)

    def test_native_failure_preserved_without_error_text(self):
        class Broken(FakeChild):
            def call(self, op, **kwargs):
                if op == "GENERATE":
                    raise RuntimeError("PRIVATE_ERROR_PAYLOAD")
                return super().call(op, **kwargs)
        subject = controller(child_factory=Broken)
        self.assertEqual(subject.run()["status"], "INCONCLUSIVE")
        self.assertNotIn("PRIVATE_ERROR_PAYLOAD", json.dumps(subject.writer.rows))
        self.assertTrue(subject.writer.rows[-1]["cleanup"]["owners_absent"])

    def test_timeout_is_not_a_successful_sample(self):
        class Timeout(FakeChild):
            def call(self, op, **kwargs):
                if op == "GENERATE":
                    raise RunError("TIMEOUT")
                return super().call(op, **kwargs)
        subject = controller(child_factory=Timeout)
        self.assertEqual(subject.run()["status"], "FAIL")
        self.assertIn("TIMEOUT", [r["terminal"] for r in subject.rows])

    def test_cleanup_failure_prevents_next_recovery_child(self):
        class Unclean(FakeChild):
            def cleanup(self):
                return {"status": "FAIL", "owners_absent": False, "alsa_owners_zero": None, "cooperative": False, "exit_code": -9}
        subject = controller("recovery-1", child_factory=Unclean)
        self.assertEqual(subject.run()["status"], "FAIL")
        self.assertEqual(subject.generation, 1)
        self.assertTrue(all(r["cleanup"]["status"] == "FAIL" for r in subject.rows))

    def test_resource_stop_preserves_partial_memory_cycle(self):
        class LowMemory(Sampler):
            def __init__(self):
                self.calls = 0
            def sample(self, owners):
                self.calls += 1
                sample = super().sample(owners)
                if self.calls > 15:
                    sample.update(mem_available_mib=511, system_used_mib=3489)
                return sample
        subject = controller("memory-1", sampler=LowMemory())
        result = subject.run()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["steady_analysis"]["status"], "Incomplete")
        self.assertLess(sum(r["terminal"] == "RESULT" for r in subject.rows), 40)
        self.assertTrue(subject.writer.checkpoints)

    def test_identity_drift_before_launch_remains_blocked_evidence(self):
        def fail():
            raise RunError("IDENTITY_DRIFT")
        subject = controller(verify_install=fail)
        self.assertEqual(subject.run()["status"], "INCONCLUSIVE")
        self.assertEqual(subject.generation, 0)
        self.assertEqual(subject.rows[-1]["terminal"], "IDENTITY_DRIFT")

    def test_early_end_stops_frozen_two_turn_case(self):
        class End(FakeChild):
            def call(self, op, **kwargs):
                reply = super().call(op, **kwargs)
                if op == "GENERATE":
                    reply["semantic"] = {"text": "", "end": True}
                return reply
        subject = controller(child_factory=End)
        self.assertEqual(subject.run()["status"], "FAIL")
        self.assertIn("EARLY_END", [r["terminal"] for r in subject.rows])


class OrderAndEvidenceTests(unittest.TestCase):
    def test_order_requires_api_proof_unique_cold_boot_and_same_replacement_boot(self):
        entries = []
        for index, case in enumerate(ORDER):
            boot = str(index) if not case.startswith("replacement-") else "replacement-boot"
            verify_next_case(entries, case, boot, "identity")
            entries.append({"case": case, "boot_digest": boot, "identity": "identity", "status": "PASS"})
        with self.assertRaises(RunError):
            verify_next_case([], "cold-N1", "boot", "identity")
        with self.assertRaises(RunError):
            verify_next_case(entries[:1], "cold-N1", "0", "identity")
        with self.assertRaises(RunError):
            verify_next_case(entries[:8], ORDER[8], "another-boot", "identity")
        bad = deepcopy(entries[:1])
        bad[0]["status"] = "FAIL"
        with self.assertRaises(RunError):
            verify_next_case(bad, "cold-N1", "boot", "identity")

    def test_exact_resource_stop_boundaries(self):
        original = Sampler().sample([123])
        self.assertIsNone(stop_reason(original, 0))
        for key, value in {"mem_available_mib": 511.99, "swap_used_kib": 1, "temperature_c": 80,
                           "throttled": "0x1", "oom_or_kernel_fault": True}.items():
            sample = dict(original, **{key: value})
            self.assertEqual(stop_reason(sample, 0), "RESOURCE_STOP")
        self.assertIsNone(stop_reason(dict(original, mem_available_mib=512), 0))
        self.assertEqual(stop_reason(dict(original, temperature_c=None), 0), "SAMPLER_FAILED")

    def test_writer_rejects_raw_values_nonfinite_missing_reason_and_overwrite(self):
        subject = controller()
        subject.run()
        original = subject.writer.rows[-1]
        for key, value in (("terminal", "PRIVATE_ANSWER"), ("command", ["private-command"]),
                           ("raw_sanitized_log_path", "/private/path")):
            with self.subTest(key=key), self.assertRaises(EvidenceError):
                validate_sample(dict(original, **{key: value}))
        bad = deepcopy(original)
        bad["timing_ms"]["ready"] = float("nan")
        with self.assertRaises(ValueError):
            validate_sample(bad)
        with self.assertRaises(EvidenceError):
            validate_sample(dict(original, missing_reasons={}))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            writer = EvidenceWriter(root, subject.run_id)
            writer.append(original)
            with self.assertRaises(FileExistsError):
                EvidenceWriter(root, subject.run_id)
            data = (writer.directory / "samples.jsonl").read_text()
            self.assertEqual(json.loads(data), original)

    def test_replacement_attempt_series_is_explicit_and_previous_series_remains_valid(self):
        subject = controller()
        subject.run()
        original = subject.writer.rows[-1]
        for series in ("MVA-001", "MVA-002"):
            sample = deepcopy(original)
            sample["run_id"] = series + "-" + sample["case_id"]
            sample["raw_sanitized_log_path"] = sample["run_id"] + "/samples.jsonl"
            validate_sample(sample)
        sample["run_id"] = "MVA-003-" + sample["case_id"]
        sample["raw_sanitized_log_path"] = sample["run_id"] + "/samples.jsonl"
        with self.assertRaises(EvidenceError):
            validate_sample(sample)


class ProcessTests(unittest.TestCase):
    def make_child(self, script):
        import os
        return Child([sys.executable, "-u", "-c", script], cwd=tempfile.gettempdir(), env=dict(os.environ))

    def test_real_process_hang_is_bounded_and_reaped(self):
        child = self.make_child("import time; time.sleep(60)")
        try:
            with self.assertRaises(RunError) as raised:
                child.receive(0.05)
            self.assertEqual(raised.exception.code, "TIMEOUT")
        finally:
            cleanup = child.cleanup()
        self.assertTrue(cleanup["owners_absent"])
        self.assertIsNotNone(cleanup["exit_code"])

    def test_native_sized_shutdown_can_finish_cooperatively(self):
        child = self.make_child(
            "import json,sys,time; "
            "json.loads(sys.stdin.readline()); "
            "time.sleep(2.2); "
            "print(json.dumps({'ticket':1,'terminal':'SHUTDOWN_ACK'}),flush=True)"
        )
        cleanup = child.cleanup()
        self.assertTrue(cleanup["cooperative"])
        self.assertTrue(cleanup["owners_absent"])
        self.assertEqual(cleanup["exit_code"], 0)

    def test_watchdog_stops_native_child_while_monitor_is_stalled(self):
        import time
        child = self.make_child("import time; time.sleep(60)")
        def stalled_monitor():
            time.sleep(2.3)
            self.assertIsNotNone(child.process.poll())
        try:
            with self.assertRaises(RunError) as raised:
                child.receive(0.05, stalled_monitor)
            self.assertEqual(raised.exception.code, "TIMEOUT")
        finally:
            self.assertTrue(child.cleanup()["owners_absent"])

    def test_oversized_or_invalid_rpc_is_rejected_and_reaped(self):
        for script in ("print('x' * 70000)", "print('not json')"):
            child = self.make_child(script)
            try:
                with self.assertRaises(RunError) as raised:
                    child.receive(2)
                self.assertEqual(raised.exception.code, "PROTOCOL_ERROR")
            finally:
                self.assertTrue(child.cleanup()["owners_absent"])

    def test_stale_ticket_cannot_complete_request(self):
        child = self.make_child('import json,sys; sys.stdin.readline(); print(json.dumps({"ticket":99,"terminal":"RESULT"}))')
        try:
            with self.assertRaises(RunError):
                child.call("OPEN", timeout=2, session="session-1")
        finally:
            self.assertTrue(child.cleanup()["owners_absent"])

    def test_real_worker_api_proof_with_fake_runtime_and_private_native_noise(self):
        source = '''
from poc_llm.tests.mva.test_mva_litert_backend import (
    FakeSamplerConfig as SamplerConfig, FakeConstrainedConfig as ConstrainedDecodingConfig,
    FakeConstraintProvider as LiteRtLmConstraintProviderType, FakeResponseFormat as ResponseFormat,
    FakeConversation, BlockingConversation)
class Backend:
    @staticmethod
    def CPU(**kwargs): return kwargs
class CancelConversation(BlockingConversation):
    def cancel_process(self):
        super().cancel_process()
        self.release.set()
class Engine:
    def __init__(self, *args, **kwargs):
        self.count = 0
        print("PRIVATE_NATIVE_SENTINEL", flush=True)
    def tokenize(self, text): return list(text)
    def create_conversation(self, **kwargs):
        self.count += 1
        if self.count == 2: return CancelConversation()
        return FakeConversation([{"text":"PUBLIC_FAKE_RESPONSE","end":False}] * 2)
    def close(self): pass
'''
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory).resolve()
            import_root = runtime / "lib/python3.13/site-packages"
            package = import_root / "litert_lm"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text(source)
            subject = controller("api-proof", child_factory=Child)
            subject.config["runtime_root"] = str(runtime)
            subject.config["runtime_native_library"] = str(package / "liblitert-lm.so")
            result = subject.run()
        self.assertEqual(result["status"], "PASS")
        self.assertIn("API_PROOF", [row["terminal"] for row in subject.rows])
        self.assertIn("CANCELLED", [row["terminal"] for row in subject.rows])
        self.assertNotIn("PRIVATE_NATIVE_SENTINEL", json.dumps(subject.writer.rows))
        self.assertTrue(result["cleanup"][1]["cooperative"])


if __name__ == "__main__":
    unittest.main()
