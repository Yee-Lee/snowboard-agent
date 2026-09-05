from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from poc_llm.harness.mva_contract import (
    ContractViolation,
    FATAL,
    MvaLifecycleOracle,
    READY_NO_SESSION,
    SESSION_FACTS,
    SESSION_IDLE,
    admit_tokens,
    fixed_steady_window,
    ordinary_least_squares_slope,
    reasoner_projection,
    render_user_turn,
    validate_semantic,
    validate_session_facts,
)


ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "poc_llm/contracts/mva"
CATALOG_PATH = ROOT / "poc_llm/fixtures/mva/public-catalog-001.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class MvaSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.semantic_schema = load_json(CONTRACT / "semantic-output-v1.schema.json")
        self.facts_schema = load_json(CONTRACT / "session-facts-v1.schema.json")
        self.wire_schema = load_json(CONTRACT / "wire-frame-v1.schema.json")
        self.machine_schema = load_json(CONTRACT / "machine-sample-v1.schema.json")
        self.manual_schema = load_json(CONTRACT / "manual-sample-v1.schema.json")

    def test_all_contract_schemas_are_valid_draft_2020_12(self) -> None:
        for schema in (
            self.semantic_schema,
            self.facts_schema,
            self.wire_schema,
            self.machine_schema,
            self.manual_schema,
        ):
            Draft202012Validator.check_schema(schema)

    def test_semantic_schema_accepts_only_compact_text_end(self) -> None:
        validator = Draft202012Validator(self.semantic_schema)
        validator.validate({"text": "天空中的光會散射。", "end": False})
        validator.validate({"text": "", "end": True})
        invalid = (
            {"text": "", "end": False},
            {"text": "再見", "end": True},
            {"text": "好", "end": 0},
            {"text": "好", "end": False, "next_perceptions": ["listen"]},
            {"action_kind": "speak", "action_payload": {"text": "好"}, "next_perceptions": ["listen"]},
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validator.validate(value)

    def test_session_facts_are_product_exact_and_tool_free(self) -> None:
        validator = Draft202012Validator(self.facts_schema)
        validator.validate(SESSION_FACTS)
        invalid = dict(SESSION_FACTS)
        invalid["available_actions"] = ["speak", "rest", "tool"]
        with self.assertRaises(ValidationError):
            validator.validate(invalid)

    def test_wire_uses_snowboard_llm_v2_and_session_control(self) -> None:
        validator = Draft202012Validator(self.wire_schema)
        open_frame = {
            "type": "OPEN_SESSION",
            "protocol_version": "snowboard.llm/2",
            "request_id": "llm.1.1",
            "session_id": "session-01",
            "facts": SESSION_FACTS,
        }
        result_frame = {
            "type": "RESULT",
            "protocol_version": "snowboard.llm/2",
            "request_id": "llm.1.2",
            "session_id": "session-01",
            "semantic": {"text": "簡短回答。", "end": False},
            "metrics": {"ttft_ms": 1.0, "ttc_ms": 2.0, "new_input_tokens": 8, "output_tokens": 4, "kv_tokens": 40},
            "state": "SESSION_IDLE",
        }
        validator.validate(open_frame)
        validator.validate(result_frame)
        old = dict(result_frame)
        old["protocol_version"] = "snowboard.llm/1"
        with self.assertRaises(ValidationError):
            validator.validate(old)

    def test_manual_schema_never_contains_raw_prompt_answer_or_audio(self) -> None:
        validator = Draft202012Validator(self.manual_schema)
        sample = {
            "run_id": "MVA-MANUAL-001",
            "case_id": "H01",
            "operator": "operator-1",
            "utc": "2026-09-05T00:00:00Z",
            "rubric": {
                "identity_consistent": "Pass",
                "knowledge_basic_correct": "NA",
                "capability_honest": "Pass",
                "continuity": "Pass",
                "concise": "Pass",
                "end_intent_correct": "NA",
            },
            "overall": "Pass",
            "sanitized_reason": "All applicable rubric rows passed.",
        }
        validator.validate(sample)
        sample["raw_answer"] = "private"
        with self.assertRaises(ValidationError):
            validator.validate(sample)


class MvaSemanticAndLifecycleTests(unittest.TestCase):
    def test_python_oracle_matches_compact_semantic_rules(self) -> None:
        self.assertEqual(validate_semantic({"text": "回答", "end": False}), {"text": "回答", "end": False})
        self.assertEqual(validate_semantic({"text": "", "end": True}), {"text": "", "end": True})
        for invalid in (
            {"text": " ", "end": False},
            {"text": "回答", "end": True},
            {"text": "回答", "end": False, "tool": {}},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ContractViolation):
                validate_semantic(invalid)

    def test_reasoner_not_model_owns_canonical_action(self) -> None:
        self.assertEqual(
            reasoner_projection({"text": "簡短回答", "end": False}),
            {"action_kind": "speak", "action_payload": {"text": "簡短回答"}, "next_perceptions": ["listen"]},
        )
        self.assertEqual(
            reasoner_projection({"text": "", "end": True}),
            {"action_kind": "rest", "action_payload": {}, "next_perceptions": []},
        )
        self.assertEqual(
            reasoner_projection({"text": "不應派發", "end": False}, listen_available=False),
            {"action_kind": "rest", "action_payload": {}, "next_perceptions": []},
        )

    def test_two_turns_reuse_one_conversation_then_next_session_is_fresh(self) -> None:
        oracle = MvaLifecycleOracle()
        oracle.open_session("session-a", SESSION_FACTS)
        oracle.begin_generate("session-a", 1)
        oracle.finish_generate("session-a", 1, {"text": "第一輪", "end": False})
        oracle.begin_generate("session-a", 2)
        oracle.finish_generate("session-a", 2, {"text": "第二輪", "end": False})
        self.assertEqual(oracle.state, SESSION_IDLE)
        self.assertEqual(oracle.conversation_creates, 1)
        self.assertEqual(oracle.conversation_closes, 0)
        oracle.close_session("session-a", "rest")
        oracle.open_session("session-b", SESSION_FACTS)
        self.assertEqual(oracle.conversation_creates, 2)
        self.assertEqual(oracle.conversation_closes, 1)
        with self.assertRaisesRegex(ContractViolation, "SESSION_MISMATCH"):
            oracle.close_session("session-a", "rest")
        self.assertEqual(oracle.session_id, "session-b")

    def test_dirty_terminal_discards_conversation_and_requires_new_session(self) -> None:
        oracle = MvaLifecycleOracle()
        oracle.open_session("session-a", SESSION_FACTS)
        oracle.begin_generate("session-a", 1)
        oracle.dirty_terminal("session-a", "TIMEOUT")
        self.assertEqual(oracle.state, READY_NO_SESSION)
        self.assertEqual(oracle.conversation_closes, 1)
        with self.assertRaisesRegex(ContractViolation, "SESSION_MISMATCH"):
            oracle.begin_generate("session-a", 2)

    def test_cleanup_failure_is_fatal_not_fake_session_closed(self) -> None:
        oracle = MvaLifecycleOracle()
        oracle.open_session("session-a", SESSION_FACTS)
        oracle.cleanup_failed("session-a")
        self.assertEqual(oracle.state, FATAL)
        self.assertEqual(oracle.conversation_closes, 0)

    def test_close_is_idempotent_only_before_a_new_session(self) -> None:
        oracle = MvaLifecycleOracle()
        oracle.open_session("session-a", SESSION_FACTS)
        oracle.close_session("session-a", "interrupt")
        oracle.close_session("session-a", "interrupt")
        self.assertEqual(oracle.conversation_closes, 1)
        self.assertEqual(oracle.events[-1], "close-noop:session-a")

    def test_capability_drift_is_rejected(self) -> None:
        changed = dict(SESSION_FACTS)
        changed["available_perceptions"] = ["listen", "look"]
        with self.assertRaises(ContractViolation):
            validate_session_facts(changed)


class MvaPromptTokenAndPlanTests(unittest.TestCase):
    def test_turn_renderer_sends_only_current_perception(self) -> None:
        template = (CONTRACT / "user-turn-template-v1.txt").read_text(encoding="utf-8").rstrip("\n")
        rendered = render_user_turn(template, "再簡單一點。")
        self.assertEqual(
            json.loads(rendered),
            {"perceptions": [{"kind": "listen", "status": "ok", "text": "再簡單一點。"}]},
        )
        self.assertNotIn("history", rendered)
        self.assertNotIn("transcript", rendered)

    def test_new_user_and_total_context_admission_are_separate(self) -> None:
        admit_tokens(new_user_tokens=32, incremental_tokens=40, current_kv_tokens=800)
        with self.assertRaisesRegex(ContractViolation, "INPUT_TOO_LARGE"):
            admit_tokens(new_user_tokens=33, incremental_tokens=40, current_kv_tokens=100)
        with self.assertRaisesRegex(ContractViolation, "CONTEXT_LIMIT"):
            admit_tokens(new_user_tokens=10, incremental_tokens=100, current_kv_tokens=800)

    def test_profile_has_fixed_orders_and_no_legacy_recycle_triggers(self) -> None:
        profile = load_json(CONTRACT / "mva-profile-001.json")
        self.assertEqual(profile["matrix"]["cold_order"], ["N1", "O1", "N2", "O2", "N3", "O3"])
        self.assertEqual(
            profile["matrix"]["replacement_order"],
            ["N1", "O1", "N2", "O2", "N3", "O3", "N4", "O4", "N5", "O5"],
        )
        self.assertEqual(profile["matrix"]["steady_window_sessions"], list(range(11, 21)))
        self.assertEqual(profile["matrix"]["memory_cycles"] * profile["matrix"]["sessions_per_memory_cycle"], 60)
        for section in (profile, profile["inference"], profile["resource_stop"]):
            self.assertNotIn("recycle_max_inference_attempts", section)
            self.assertNotIn("recycle_owner_pss_delta_mib", section)

    def test_public_catalog_does_not_track_holdout_contents(self) -> None:
        catalog = load_json(CATALOG_PATH)
        self.assertFalse(catalog["private_holdout_included"])
        self.assertEqual(catalog["timing"]["turns"], ["天空為什麼是藍色的？", "再簡單一點。"])
        self.assertEqual(catalog["prewarm"]["turns"], ["請用一句話打招呼。"])
        self.assertEqual(catalog["manual_holdout"]["contents"], "operator_controlled_not_tracked")
        self.assertEqual(len(catalog["manual_holdout"]["case_ids"]), 12)

    def test_steady_window_is_fixed_and_ols_is_per_cycle(self) -> None:
        values = {index: 100.0 + 2.0 * index for index in range(1, 21)}
        window = fixed_steady_window(values)
        self.assertEqual([item[0] for item in window], list(range(11, 21)))
        self.assertAlmostEqual(ordinary_least_squares_slope(window), 2.0)
        del values[15]
        with self.assertRaisesRegex(ContractViolation, "incomplete"):
            fixed_steady_window(values)


if __name__ == "__main__":
    unittest.main()
