from __future__ import annotations

import unittest

from poc_llm.efficiency.reasoner import ListenReasoner, ReasonerCode, ReasonerError
from poc_llm.harness.mva_contract import SESSION_FACTS


def turn(text: str = "你好", *, status: str = "ok", kind: str = "listen") -> dict[str, object]:
    return {"perceptions": [{"kind": kind, "status": status, "text": text}]}


class ListenReasonerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.subject = ListenReasoner()

    def test_unwraps_exact_listen_envelope(self) -> None:
        projected = self.subject.project_turn(SESSION_FACTS, turn("天空為什麼是藍色？"))
        admitted = self.subject.admit(
            projected,
            tokenize=list,
            render_for_conversation=lambda value: "chat:" + value,
            current_kv_tokens=10,
        )
        self.assertEqual(admitted.user_text, "天空為什麼是藍色？")
        self.assertEqual(admitted.rendered_user, "天空為什麼是藍色？")
        self.assertLessEqual(admitted.rendered_tokens, 128)
        self.assertEqual(admitted.rendered_input_tier, "prefill_128")

    def test_empty_failed_multiple_and_unsupported_inputs_are_typed(self) -> None:
        cases = (
            (turn(""), ReasonerCode.NO_ACTIONABLE_INPUT),
            (turn(status="timeout"), ReasonerCode.NO_ACTIONABLE_INPUT),
            ({"perceptions": [turn()["perceptions"][0], turn("再說一次")["perceptions"][0]]},
             ReasonerCode.INVALID_INPUT),
            (turn(kind="look"), ReasonerCode.UNSUPPORTED_PERCEPTION),
        )
        for value, code in cases:
            with self.subTest(code=code), self.assertRaises(ReasonerError) as raised:
                self.subject.project_turn(SESSION_FACTS, value)
            self.assertEqual(raised.exception.code, code)

    def test_codepoint_token_and_kv_boundaries_are_independent(self) -> None:
        with self.assertRaises(ReasonerError) as raised:
            self.subject.project_turn(SESSION_FACTS, turn("字" * 21))
        self.assertEqual(raised.exception.code, ReasonerCode.INPUT_TOO_LARGE)

        projected = self.subject.project_turn(SESSION_FACTS, turn("字" * 20))
        with self.assertRaises(ReasonerError) as raised:
            self.subject.admit(
                projected, tokenize=lambda value: list(value) * 2,
                render_for_conversation=lambda value: value, current_kv_tokens=0)
        self.assertEqual(raised.exception.code, ReasonerCode.INPUT_TOO_LARGE)

        with self.assertRaises(ReasonerError) as raised:
            self.subject.admit(
                projected, tokenize=list, render_for_conversation=lambda value: value,
                current_kv_tokens=900)
        self.assertEqual(raised.exception.code, ReasonerCode.CONTEXT_LIMIT)

    def test_crossing_128_is_telemetry_not_rejection(self) -> None:
        projected = self.subject.project_turn(SESSION_FACTS, turn())
        admitted = self.subject.admit(
            projected, tokenize=list, render_for_conversation=lambda value: value + "x" * 128,
            current_kv_tokens=0, output_reserve_tokens=1,
        )
        self.assertGreater(admitted.rendered_tokens, 128)
        self.assertEqual(admitted.rendered_input_tier, "prefill_1024")

    def test_semantic_projection_and_invalid_output_fallback(self) -> None:
        self.assertEqual(
            self.subject.project_generation({"text": "回答", "end": False}),
            {"action_kind": "speak", "action_payload": {"text": "回答"},
             "next_perceptions": ["listen"]},
        )
        self.assertEqual(
            self.subject.project_generation({"text": "", "end": True}),
            {"action_kind": "rest", "action_payload": {}, "next_perceptions": []},
        )
        self.assertEqual(
            self.subject.project_generation({"text": "好的，再見", "end": True}),
            {"action_kind": "speak", "action_payload": {"text": "好的，再見"},
             "next_perceptions": []},
        )
        with self.assertRaises(ReasonerError) as raised:
            self.subject.project_generation({"text": "", "end": False})
        self.assertEqual(raised.exception.code, ReasonerCode.INVALID_OUTPUT)

    def test_instances_do_not_share_session_state(self) -> None:
        first = self.subject.project_turn(SESSION_FACTS, turn("第一個"))
        second = ListenReasoner().project_turn(SESSION_FACTS, turn("第二個"))
        self.assertEqual((first.user_text, second.user_text), ("第一個", "第二個"))


if __name__ == "__main__":
    unittest.main()
