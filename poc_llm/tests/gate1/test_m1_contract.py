#!/usr/bin/env python3
"""Negative regressions for the M1 contract freeze candidate."""

from __future__ import annotations

import copy
import unittest

from poc_llm.harness.m1_contract_validator import load, validate_contract, validate_sequence, CONTRACT_ROOT
from jsonschema import Draft202012Validator


class M1ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = load(CONTRACT_ROOT / "contract-fixtures.json")
        cls.protocol = Draft202012Validator(load(CONTRACT_ROOT / "protocol-frame.schema.json"))
        cls.response = Draft202012Validator(load(CONTRACT_ROOT / "response.schema.json"))

    def test_complete_contract_self_test_passes(self) -> None:
        report = validate_contract()
        self.assertEqual(report["result"], "PASS", report["violations"])
        self.assertEqual(report["schema_negative_cases"], 7)
        self.assertEqual(report["invalid_sequences"], 3)

    def test_unknown_tool_is_rejected_by_capability_context(self) -> None:
        prompt = self.fixtures["valid_prompt"]
        response = copy.deepcopy(self.fixtures["valid_responses"][1])
        response["action_payload"]["name"] = "device.unregistered.run"
        self.assertTrue(self.response.is_valid(response))
        registered = {item["name"] for item in prompt["capabilities"]["tools"]}
        self.assertNotIn(response["action_payload"]["name"], registered)

    def test_duplicate_terminal_result_is_rejected(self) -> None:
        frames = copy.deepcopy(self.fixtures["valid_sequences"][0]["frames"])
        frames.insert(3, copy.deepcopy(frames[2]))
        errors = validate_sequence(frames, self.protocol)
        self.assertTrue(any("does not match active request" in error for error in errors), errors)

    def test_cancel_for_stale_request_is_rejected(self) -> None:
        frames = copy.deepcopy(self.fixtures["valid_sequences"][1]["frames"])
        frames[2]["request_id"] = "req-stale"
        errors = validate_sequence(frames, self.protocol)
        self.assertTrue(any("does not target active request" in error for error in errors), errors)

    def test_protocol_stdout_extra_field_is_rejected(self) -> None:
        frame = copy.deepcopy(self.fixtures["valid_sequences"][0]["frames"][0])
        frame["debug"] = "not allowed on protocol stdout"
        self.assertFalse(self.protocol.is_valid(frame))


if __name__ == "__main__":
    unittest.main()
