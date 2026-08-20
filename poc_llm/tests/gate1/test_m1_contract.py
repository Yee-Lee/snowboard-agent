#!/usr/bin/env python3
"""Executable regressions for the M1 replacement freeze candidate."""

from __future__ import annotations

import copy
import io
import inspect
import json
import logging
from pathlib import Path
import tempfile
import unittest

from poc_llm.harness.m1_contract_boundary import (
    APOLOGY,
    REST,
    BoundaryValidationError,
    normalize_response,
    project_reasoning_input,
    validate_identity,
)
from poc_llm.harness.m1_contract_validator import (
    CONTRACT_ROOT,
    load,
    make_validators,
    validate_contract,
    validate_sequence,
)


class M1ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = load(CONTRACT_ROOT / "contract-fixtures.json")
        cls.validators = make_validators()
        cls.protocol = cls.validators["protocol"]
        cls.prompt = cls.fixtures["valid_prompt"]

    def test_complete_contract_self_test_passes(self) -> None:
        report = validate_contract()
        self.assertEqual(report["result"], "PASS", report["violations"])
        self.assertEqual(report["schema_negative_cases"], 9)
        self.assertEqual(report["valid_sequences"], 2)
        self.assertEqual(report["invalid_sequences"], 3)

    def test_core_reasoning_input_projects_to_private_child_input(self) -> None:
        reasoning = self.fixtures["valid_reasoning_input"]
        projection = project_reasoning_input(reasoning)
        self.assertEqual(projection, self.prompt)
        encoded = json.dumps(projection, sort_keys=True)
        self.assertNotIn("pending_message_ids", encoded)
        self.assertNotIn("opaque-001", encoded)
        self.assertNotIn("request_id", projection)
        self.assertEqual(projection["pending_message_count"], 2)
        self.assertEqual(
            set(projection["capabilities"]["tools"][0]),
            {"name", "description", "input_schema"},
        )

    def test_projection_is_deterministic_and_normalizes_missing_text(self) -> None:
        shuffled = copy.deepcopy(self.fixtures["valid_reasoning_input"])
        shuffled["perceptions"].reverse()
        shuffled["available_perceptions"].reverse()
        shuffled["available_actions"].reverse()
        self.assertEqual(project_reasoning_input(shuffled), self.prompt)
        explicit_empty = copy.deepcopy(self.fixtures["valid_reasoning_input"])
        explicit_empty["perceptions"][0]["text"] = ""
        self.assertEqual(project_reasoning_input(explicit_empty), self.prompt)

    def test_core_and_child_input_shapes_are_not_interchangeable(self) -> None:
        self.assertFalse(self.validators["reasoning"].is_valid(self.prompt))
        self.assertFalse(
            self.validators["prompt"].is_valid(self.fixtures["valid_reasoning_input"])
        )

    def test_invalid_public_tool_schema_is_rejected_before_projection(self) -> None:
        reasoning = copy.deepcopy(self.fixtures["valid_reasoning_input"])
        reasoning["tool_schemas"][0]["input_schema"] = {"type": "not-a-json-type"}
        with self.assertRaisesRegex(BoundaryValidationError, "invalid-schema"):
            project_reasoning_input(reasoning)

    def test_valid_responses_pass_through_callable_normalizer(self) -> None:
        self.assertNotIn("handler", inspect.signature(normalize_response).parameters)
        for response in self.fixtures["valid_responses"]:
            with self.subTest(action=response["action_kind"]):
                normalized, diagnostics = normalize_response(response, self.prompt)
                self.assertEqual(normalized, response)
                self.assertEqual(diagnostics, ("valid",))

    def test_p5_invalid_output_table_uses_locked_fallback(self) -> None:
        cases = {
            "malformed-json": "{",
            "non-object": [],
            "wrong-key": {
                "action_kind": "tool",
                "action_payload": {"tool": "device.light.on", "args": {}},
                "next_perceptions": ["listen"],
            },
            "blank-speak": {
                "action_kind": "speak",
                "action_payload": {"text": " \t"},
                "next_perceptions": ["listen"],
            },
            "unknown-action": {
                "action_kind": "dance",
                "action_payload": {},
                "next_perceptions": [],
            },
            "unknown-tool": {
                "action_kind": "tool",
                "action_payload": {"name": "device.unknown.run", "arguments": {}},
                "next_perceptions": ["listen"],
            },
            "invalid-tool-arguments": {
                "action_kind": "tool",
                "action_payload": {"name": "device.light.on", "arguments": {}},
                "next_perceptions": ["listen"],
            },
        }
        for case_id, raw in cases.items():
            with self.subTest(case_id=case_id):
                normalized, diagnostics = normalize_response(raw, self.prompt)
                self.assertEqual(normalized, APOLOGY)
                self.assertNotEqual(diagnostics, ("valid",))
        restricted = copy.deepcopy(self.prompt)
        restricted["capabilities"]["perceptions"] = ["listen"]
        unavailable = {
            "action_kind": "speak",
            "action_payload": {"text": "Synthetic response."},
            "next_perceptions": ["look"],
        }
        normalized, diagnostics = normalize_response(unavailable, restricted)
        self.assertEqual(normalized, APOLOGY)
        self.assertIn("unavailable", diagnostics[0])
        unavailable_action = copy.deepcopy(self.prompt)
        unavailable_action["capabilities"]["actions"] = ["rest"]
        normalized, diagnostics = normalize_response(
            self.fixtures["valid_responses"][0], unavailable_action
        )
        self.assertEqual(normalized, REST)
        self.assertIn("unavailable", diagnostics[0])
        refused, diagnostics = normalize_response({}, self.prompt, refused=True)
        self.assertEqual(refused, APOLOGY)
        self.assertIn("refused", diagnostics[0])

    def test_p5_fallback_respects_capability_combinations(self) -> None:
        cases = [
            (["speak", "rest"], ["listen"], APOLOGY),
            (["rest"], ["listen"], REST),
            (["speak", "rest"], ["read"], REST),
            (["rest"], [], REST),
        ]
        for actions, perceptions, expected in cases:
            prompt = copy.deepcopy(self.prompt)
            prompt["capabilities"]["actions"] = actions
            prompt["capabilities"]["perceptions"] = perceptions
            normalized, _ = normalize_response("not-json", prompt)
            self.assertEqual(normalized, expected)

    def test_normalizer_deduplicates_next_perceptions(self) -> None:
        response = copy.deepcopy(self.fixtures["valid_responses"][0])
        response["next_perceptions"] = ["listen", "listen"]
        normalized, diagnostics = normalize_response(response, self.prompt)
        self.assertEqual(normalized["next_perceptions"], ["listen"])
        self.assertEqual(diagnostics, ("valid",))

    def test_normalizer_emits_no_raw_output_to_logs(self) -> None:
        prompt_sentinel = "PRIVATE-PROMPT-SENTINEL"
        raw_sentinel = "PRIVATE-RAW-OUTPUT-SENTINEL"
        payload_sentinel = "PRIVATE-TOOL-PAYLOAD-SENTINEL"
        prompt = copy.deepcopy(self.prompt)
        prompt["perceptions"][0]["text"] = prompt_sentinel
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            normalize_response(
                {
                    "action_kind": "tool",
                    "action_payload": {
                        "name": "device.light.on",
                        "arguments": {"room": payload_sentinel, "raw": raw_sentinel},
                    },
                    "next_perceptions": ["listen"],
                },
                prompt,
            )
        finally:
            root_logger.removeHandler(handler)
        logs = stream.getvalue()
        self.assertNotIn(prompt_sentinel, logs)
        self.assertNotIn(raw_sentinel, logs)
        self.assertNotIn(payload_sentinel, logs)

    def test_protocol_binds_generate_input_and_result_response(self) -> None:
        sequence = copy.deepcopy(self.fixtures["valid_sequences"][0]["frames"])
        self.assertTrue(self.protocol.is_valid(sequence[1]))
        self.assertTrue(self.protocol.is_valid(sequence[2]))
        sequence[1]["input"] = {}
        sequence[2]["response"]["action_payload"]["text"] = "   "
        self.assertFalse(self.protocol.is_valid(sequence[1]))
        self.assertFalse(self.protocol.is_valid(sequence[2]))

    def test_busy_rejects_only_second_request_and_active_request_continues(self) -> None:
        frames = self.fixtures["valid_sequences"][1]["frames"]
        self.assertEqual(validate_sequence(frames, self.protocol), [])
        self.assertEqual(frames[3]["request_id"], "req-b")
        self.assertEqual(frames[3]["state"], "GENERATING")
        self.assertEqual(frames[4]["request_id"], "req-a")
        self.assertEqual(frames[4]["state"], "READY")

    def test_stale_invalid_request_is_nonterminal(self) -> None:
        frames = copy.deepcopy(self.fixtures["valid_sequences"][1]["frames"])
        frames[3]["code"] = "INVALID_REQUEST"
        self.assertEqual(validate_sequence(frames, self.protocol), [])

    def test_timeout_and_cancel_cleanup_restore_terminal_readiness(self) -> None:
        ready = copy.deepcopy(self.fixtures["valid_sequences"][0]["frames"][0])
        prompt = copy.deepcopy(self.fixtures["valid_sequences"][1]["frames"][1]["input"])
        frames = [
            ready,
            {"type": "GENERATE", "protocol_version": "snowboard.llm/1", "request_id": "req-timeout", "input": prompt},
            {
                "type": "ERROR",
                "protocol_version": "snowboard.llm/1",
                "request_id": "req-timeout",
                "code": "TIMEOUT",
                "state": "READY",
            },
            {"type": "GENERATE", "protocol_version": "snowboard.llm/1", "request_id": "req-cancel", "input": prompt},
            {"type": "CANCEL", "protocol_version": "snowboard.llm/1", "request_id": "req-cancel"},
            {"type": "CANCELLED", "protocol_version": "snowboard.llm/1", "request_id": "req-cancel", "state": "READY"},
            {"type": "SHUTDOWN", "protocol_version": "snowboard.llm/1"},
            {"type": "SHUTDOWN_ACK", "protocol_version": "snowboard.llm/1"},
        ]
        self.assertEqual(validate_sequence(frames, self.protocol), [])

    def test_duplicate_terminal_and_stale_cancel_are_rejected(self) -> None:
        result_frames = copy.deepcopy(self.fixtures["valid_sequences"][0]["frames"])
        result_frames.insert(3, copy.deepcopy(result_frames[2]))
        self.assertTrue(validate_sequence(result_frames, self.protocol))
        busy_frames = copy.deepcopy(self.fixtures["valid_sequences"][1]["frames"])
        busy_frames[2] = {
            "type": "CANCEL",
            "protocol_version": "snowboard.llm/1",
            "request_id": "req-stale",
        }
        self.assertTrue(validate_sequence(busy_frames, self.protocol))

    def test_error_code_state_table_is_schema_enforced(self) -> None:
        base = {
            "type": "ERROR",
            "protocol_version": "snowboard.llm/1",
            "request_id": "req-a",
        }
        cases = [
            ("BUSY", "GENERATING", True),
            ("BUSY", "READY", False),
            ("INVALID_REQUEST", "READY", True),
            ("INVALID_REQUEST", "GENERATING", True),
            ("TIMEOUT", "READY", True),
            ("TIMEOUT", "GENERATING", False),
            ("GENERATION_FAILED", "READY", True),
            ("CANCEL_FAILED", "FATAL", True),
            ("CANCEL_FAILED", "READY", False),
            ("PROTOCOL_ERROR", "FATAL", True),
        ]
        for code, state, expected in cases:
            with self.subTest(code=code, state=state):
                frame = {**base, "code": code, "state": state}
                self.assertEqual(self.protocol.is_valid(frame), expected)

    def test_fatal_rejects_every_trailing_frame_type(self) -> None:
        ready = copy.deepcopy(self.fixtures["valid_sequences"][0]["frames"][0])
        generate = copy.deepcopy(self.fixtures["valid_sequences"][0]["frames"][1])
        fatal = {
            "type": "ERROR",
            "protocol_version": "snowboard.llm/1",
            "request_id": "req-001",
            "code": "PROTOCOL_ERROR",
            "state": "FATAL",
        }
        trailing_frames = {
            "READY": ready,
            "ERROR": {
                "type": "ERROR",
                "protocol_version": "snowboard.llm/1",
                "request_id": "req-stale",
                "code": "INVALID_REQUEST",
                "state": "READY",
            },
            "RESULT": copy.deepcopy(
                self.fixtures["valid_sequences"][0]["frames"][2]
            ),
            "CANCEL": {
                "type": "CANCEL",
                "protocol_version": "snowboard.llm/1",
                "request_id": "req-001",
            },
            "SHUTDOWN": {
                "type": "SHUTDOWN",
                "protocol_version": "snowboard.llm/1",
            },
            "SHUTDOWN_ACK": {
                "type": "SHUTDOWN_ACK",
                "protocol_version": "snowboard.llm/1",
            },
        }
        for frame_type, trailing in trailing_frames.items():
            with self.subTest(frame_type=frame_type):
                errors = validate_sequence(
                    [ready, generate, fatal, trailing], self.protocol
                )
                self.assertTrue(
                    any("frame after FATAL" in error for error in errors), errors
                )

    def test_protocol_stdout_extra_field_is_rejected(self) -> None:
        frame = copy.deepcopy(self.fixtures["valid_sequences"][0]["frames"][0])
        frame["debug"] = "not allowed on protocol stdout"
        self.assertFalse(self.protocol.is_valid(frame))

    def test_identity_context_accepts_only_exact_frozen_tuple(self) -> None:
        self._validate_identity()
        mutations = {
            "candidate": lambda config, candidate, acquisition, ready: candidate.update(candidate_id="CAND-WRONG"),
            "acquisition": lambda config, candidate, acquisition, ready: acquisition.update(pairing_revision="wrong"),
            "runtime-path": lambda config, candidate, acquisition, ready: config.update(
                runtime_path="/arbitrary/runtime.whl"
            ),
            "model-path": lambda config, candidate, acquisition, ready: config.update(
                model_path="/approved/../other.task"
            ),
            "runtime-hash": lambda config, candidate, acquisition, ready: config.update(runtime_sha256="f" * 64),
            "model-hash": lambda config, candidate, acquisition, ready: config.update(model_sha256="e" * 64),
            "config-hash": lambda config, candidate, acquisition, ready: candidate["config"].update(sha256="d" * 64),
            "ready-drift": lambda config, candidate, acquisition, ready: ready.update(platform="pi-debian13-aarch64"),
        }
        for case_id, mutate in mutations.items():
            with self.subTest(case_id=case_id):
                with self.assertRaises(BoundaryValidationError):
                    self._validate_identity(mutate)

    def test_identity_rejects_symlink_alias(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "runtime.whl"
            target.touch()
            alias = Path(directory) / "alias.whl"
            alias.symlink_to(target)

            def mutate(config, candidate, acquisition, ready):
                config["runtime_path"] = str(alias)
                acquisition["platforms"][config["platform"]]["runtime_artifact"]["path"] = str(target)

            with self.assertRaisesRegex(BoundaryValidationError, "alias"):
                self._validate_identity(mutate)

    def _validate_identity(self, mutate=None) -> None:
        config = copy.deepcopy(self.fixtures["valid_config"])
        identity = copy.deepcopy(self.fixtures["valid_identity"])
        if mutate is not None:
            mutate(config, identity["candidate"], identity["acquisition"], identity["ready"])
        validate_identity(
            config,
            identity["candidate"],
            identity["acquisition"],
            identity["ready"],
            config_sha256=identity["config_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
