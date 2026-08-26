from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from poc_llm.harness.litert_lm_child_adapter import Generation
from poc_llm.harness.litert_lm_pi_child_adapter import PiChild
from poc_llm.harness.pi_runtime import native_library_preflight, protocol_validator


ROOT = Path(__file__).resolve().parents[3]
LOCK = ROOT / "poc_llm/harness/gate1-pi-compat-lock-v6.json"
G2_LOCK = ROOT / "poc_llm/harness/gate2a-pi-lock-v1.json"
G2_RUNNER = ROOT / "poc_llm/tools/run_gate2a_pi.py"
PROTOCOL = ROOT / "poc_llm/contracts/m1/protocol-frame-pi.schema.json"
CONFIG_SCHEMA = ROOT / "poc_llm/contracts/m1/strict-config-pi.schema.json"
PROMPT_SCHEMA = ROOT / "poc_llm/contracts/m1/prompt-input.schema.json"
RESPONSE_SCHEMA = ROOT / "poc_llm/contracts/m1/response.schema.json"
P5 = ROOT / "poc_llm/fixtures/gate2/p5-extreme-generation-001.json"
P5_V2 = ROOT / "poc_llm/fixtures/gate2/p5-continuous-timeout-002.json"
G2_PACKET_V2 = ROOT / "poc_llm/tests/gate2/GATE2A-PI-PACKET-002.md"


class FakeBackend:
    def generate(self, _prompt: str, *, max_output_tokens: int) -> Generation:
        return Generation(
            text='{"action_kind":"rest","action_payload":{},"next_perceptions":[]}',
            metrics={"init_ms": 1.0, "ttft_ms": 1.0, "prefill_tokens": 1,
                     "prefill_tokens_per_second": 1.0, "decode_tokens": max_output_tokens,
                     "decode_tokens_per_second": 1.0, "kv_tokens": 1},
        )

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        pass


class PiPacketDefinitionTests(unittest.TestCase):
    def test_pi_config_schema_locks_standard_and_p5_profiles(self) -> None:
        schema = json.loads(CONFIG_SCHEMA.read_text(encoding="utf-8"))
        standard = json.loads((ROOT / "poc_llm/fixtures/gate2/pi-configs/CAND-LRT-G4E2B-MOBILE-R1-standard.json").read_text())
        p5 = json.loads((ROOT / "poc_llm/fixtures/gate2/pi-configs/CAND-LRT-G4E2B-MOBILE-R1-p5.json").read_text())
        from jsonschema import Draft202012Validator

        validator = Draft202012Validator(schema)
        self.assertTrue(validator.is_valid(standard))
        self.assertTrue(validator.is_valid(p5))
        p5["max_output_tokens"] = 16
        self.assertFalse(validator.is_valid(p5))

    def test_pi_protocol_supports_ping_pong_and_exact_platform_identity(self) -> None:
        validator = protocol_validator(PROTOCOL, PROMPT_SCHEMA, RESPONSE_SCHEMA)
        config = json.loads((ROOT / "poc_llm/fixtures/gate2/pi-configs/CAND-LRT-G4E2B-MOBILE-R1-standard.json").read_text())
        output = io.StringIO()
        child = PiChild(config, "a" * 64, FakeBackend(), output)
        child.protocol = validator
        child.ready()
        self.assertTrue(child.handle({"type": "PING", "protocol_version": "snowboard.llm/1"}))
        frames = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([frame["type"] for frame in frames], ["READY", "PONG"])
        self.assertEqual(frames[0]["identity"]["platform"], "pi-debian13-aarch64")
        self.assertTrue(validator.is_valid(frames[0]))
        self.assertTrue(validator.is_valid(frames[1]))

    def test_p5_fixture_freezes_timeout_and_no_adaptive_success(self) -> None:
        fixture = json.loads(P5.read_text(encoding="utf-8"))
        self.assertEqual(fixture["timeout_ms"], 15000)
        self.assertEqual(fixture["max_output_tokens"], 512)
        self.assertEqual(fixture["early_completion_disposition"], "INCONCLUSIVE")
        self.assertEqual(fixture["timeout_pass_window_ms"], [15000, 17000])

    def test_p5_v2_predeclares_continuous_fast_model_disposition(self) -> None:
        fixture = json.loads(P5_V2.read_text(encoding="utf-8"))
        self.assertEqual(fixture["profile"], "p5-continuous-chunks-v1")
        self.assertEqual(fixture["chunk_max_output_tokens"], 512)
        self.assertEqual(fixture["timeout_ms"], 15000)
        self.assertEqual(fixture["completed_chunk_disposition"], "CONTINUE")
        self.assertTrue(fixture["result_before_timeout_forbidden"])
        self.assertTrue(fixture["adaptive_fixture_forbidden"])
        packet = G2_PACKET_V2.read_text(encoding="utf-8")
        self.assertIn("M4B-P5-CONTINUOUS-TIMEOUT-002", packet)
        self.assertIn("execution-surface SHA-256", packet)
        self.assertIn("Git ancestor", packet)

    def test_gate1_lock_authenticates_every_repository_artifact(self) -> None:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["packet_id"], "G1-PI-COMPAT-006")
        self.assertEqual(lock["candidate_order"], ["CAND-LRT-G4E2B-MOBILE-R1", "CAND-LRT-Q25-15B-Q8-R1"])
        for item in lock["artifacts"].values():
            path = ROOT / item["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"], path)

    def test_gate2_lock_authenticates_artifacts_and_freezes_two_candidates(self) -> None:
        lock = json.loads(G2_LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["packet_id"], "G2A-PI-LLM-001")
        self.assertEqual(set(lock["candidates"]), {"CAND-LRT-G4E2B-MOBILE-R1", "CAND-LRT-Q25-15B-Q8-R1"})
        for item in lock["artifacts"].values():
            path = ROOT / item["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"], path)
        for candidate in lock["candidates"].values():
            for item in candidate.values():
                path = ROOT / item["path"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"], path)

    def test_gate2_fatal_outcome_fixture_has_product_exit_code(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(G2_RUNNER), "--fatal-outcome-self-test"],
            cwd=ROOT, check=False, capture_output=True, text=True,
        )
        self.assertEqual(completed.returncode, 4)

    def test_native_library_preflight_requires_aarch64_elf_and_resolved_linkage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            native = Path(directory) / "liblitert-lm.so"
            native.write_bytes(b"locked-native")
            expected = hashlib.sha256(native.read_bytes()).hexdigest()
            calls = [
                subprocess.CompletedProcess(["readelf"], 0, "  Class: ELF64\n  Machine: AArch64\n", ""),
                subprocess.CompletedProcess(["ldd"], 0, "libc.so.6 => /lib/aarch64-linux-gnu/libc.so.6\n", ""),
            ]
            with patch("poc_llm.harness.pi_runtime.subprocess.run", side_effect=calls):
                report = native_library_preflight(native, expected)
            self.assertEqual(report["elf_machine"], "AArch64")
            self.assertEqual(report["linkage"], "resolved")


if __name__ == "__main__":
    unittest.main()
