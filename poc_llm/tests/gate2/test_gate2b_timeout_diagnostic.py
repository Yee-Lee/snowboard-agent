from __future__ import annotations

import hashlib
import json
import unittest
from unittest.mock import patch

from poc_llm.harness.litert_lm_gate2b_child_adapter_v1 import gate2b_product_prompt
from poc_llm.tools.run_gate2b_pi_v1 import CombinedLlmDomain
from poc_llm.tools.run_gate2b_timeout_diagnostic import (
    FORMAL_TIMEOUT_SECONDS,
    NONCE,
    SESSION_ID,
    TRAP,
    request_value,
    sanitized_generation,
)


class FakeGeneration:
    def __init__(self, text: str, metrics: dict) -> None:
        self.text = text
        self.metrics = metrics


class FakeBackend:
    def __init__(self) -> None:
        self.prompt = ""
        self.max_output_tokens = 0

    def generate(self, prompt: str, *, max_output_tokens: int) -> FakeGeneration:
        self.prompt = prompt
        self.max_output_tokens = max_output_tokens
        return FakeGeneration(
            json.dumps({
                "action_kind": "speak",
                "action_payload": {"text": f"ack {NONCE}"},
                "next_perceptions": ["listen"],
            }),
            {
                "init_ms": 1.0,
                "ttft_ms": 2.0,
                "prefill_tokens": 190,
                "prefill_tokens_per_second": 20.0,
                "decode_tokens": 12,
                "decode_tokens_per_second": 10.0,
                "kv_tokens": 202,
            },
        )


class Gate2BTimeoutDiagnosticTests(unittest.TestCase):
    def test_corrected_domain_uses_compact_input_and_terminal_grace(self) -> None:
        class Process:
            pid = 100

            @staticmethod
            def poll() -> None:
                return None

        terminal = {
            "type": "RESULT",
            "request_id": "M4-SESSION-01",
            "response": {
                "action_kind": "speak",
                "action_payload": {"text": f"ack {NONCE}"},
                "next_perceptions": ["listen"],
            },
            "metrics": {
                "prefill_tokens": 10,
                "decode_tokens": 2,
                "kv_tokens": 12,
            },
        }
        domain = CombinedLlmDomain(
            common={"validator": object(), "config_value":{
                "generate_timeout_ms":15000, "terminal_grace_ms":2000,
                "max_input_tokens":128,
            }}, stderr=None, engine_capacity=1024
        )
        domain.process = Process()
        with patch(
            "poc_llm.tools.run_gate2b_pi_v1.generate",
            return_value=(terminal, 1.0),
        ) as generate:
            domain._run(SESSION_ID, "private transcript", NONCE, TRAP)
        value = generate.call_args.args[3]
        self.assertEqual(
            value["perceptions"][0]["text"],
            f"USER=private transcript\nINCLUDE={NONCE}\nOMIT={TRAP}",
        )
        self.assertEqual(generate.call_args.kwargs["timeout_s"], 17.0)

    def test_request_reproduces_formal_first_session_value(self) -> None:
        transcript = "private transcript"
        value = request_value(transcript)
        self.assertEqual(value["perceptions"][0]["kind"], "listen")
        self.assertEqual(value["perceptions"][0]["status"], "ok")
        self.assertIn(transcript, value["perceptions"][0]["text"])
        self.assertIn(NONCE, value["perceptions"][0]["text"])
        self.assertIn(TRAP, value["perceptions"][0]["text"])
        self.assertEqual(value["capabilities"]["actions"], ["speak"])
        self.assertEqual(
            gate2b_product_prompt(value),
            gate2b_product_prompt(json.loads(json.dumps(value))),
        )

    def test_sanitized_generation_keeps_only_hashes_lengths_and_metrics(self) -> None:
        backend = FakeBackend()
        value = request_value("private transcript")
        result = sanitized_generation(
            backend,
            {"max_input_tokens": 128, "max_output_tokens": 64},
            value,
        )
        serialized = json.dumps(result)
        self.assertNotIn("private transcript", serialized)
        self.assertNotIn("ack ", serialized)
        self.assertEqual(backend.max_output_tokens, 64)
        self.assertEqual(
            result["prompt_sha256"],
            hashlib.sha256(backend.prompt.encode()).hexdigest(),
        )
        self.assertEqual(result["metrics"]["prefill_tokens"], 190)
        self.assertFalse(result["runtime_prefill_within_declared_input_limit"])
        self.assertTrue(result["current_marker_present_once"])
        self.assertTrue(result["current_trap_absent"])
        self.assertEqual(result["formal_timeout_ms"], FORMAL_TIMEOUT_SECONDS * 1000)


if __name__ == "__main__":
    unittest.main()
