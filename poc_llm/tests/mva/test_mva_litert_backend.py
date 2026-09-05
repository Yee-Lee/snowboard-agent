from __future__ import annotations

import json
from pathlib import Path
import threading
import unittest

from poc_llm.harness.mva_contract import SESSION_FACTS
from poc_llm.harness.mva_litert_backend import MvaBackendError, MvaLiteRtBackend


ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "poc_llm/contracts/mva"


class FakeBenchmark:
    time_to_first_token_in_second = 0.001
    last_prefill_token_count = 7
    last_decode_token_count = 4


class FakeConversation:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.messages: list[str] = []
        self.closed = False
        self.cancel_count = 0
        self._token_count = 10

    @property
    def token_count(self) -> int:
        return self._token_count

    def render_message_to_string(self, prompt: str) -> str:
        return "rendered:" + prompt

    def send_message_async(self, prompt: str, *, response_format: object):
        self.messages.append(prompt)
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        self._token_count += 11
        yield {"content": [{"type": "text", "text": text}]}

    def get_benchmark_info(self) -> FakeBenchmark:
        return FakeBenchmark()

    def cancel_process(self) -> None:
        self.cancel_count += 1

    def close(self) -> None:
        self.closed = True


class BlockingConversation(FakeConversation):
    def __init__(self) -> None:
        super().__init__([])
        self.started = threading.Event()
        self.release = threading.Event()

    def send_message_async(self, prompt: str, *, response_format: object):
        self.messages.append(prompt)
        self.started.set()
        self.release.wait(timeout=2)
        raise RuntimeError("CANCELLED")
        yield  # pragma: no cover - preserves generator shape


class FakeEngine:
    def __init__(self, response_sets: list[list[dict]]) -> None:
        self.response_sets = response_sets
        self.created: list[FakeConversation] = []
        self.create_kwargs: list[dict] = []
        self.closed = False

    def create_conversation(self, **kwargs):
        self.create_kwargs.append(kwargs)
        conversation = FakeConversation(self.response_sets.pop(0))
        self.created.append(conversation)
        return conversation

    def tokenize(self, text: str) -> list[str]:
        return list(text)

    def close(self) -> None:
        self.closed = True


class FakeSamplerConfig:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class FakeConstrainedConfig:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class FakeResponseFormat:
    @staticmethod
    def json(schema: dict) -> tuple[str, dict]:
        return "json", schema


class FakeConstraintProvider:
    LL_GUIDANCE = "LL_GUIDANCE"


class FakeLiteRt:
    SamplerConfig = FakeSamplerConfig
    ConstrainedDecodingConfig = FakeConstrainedConfig
    ResponseFormat = FakeResponseFormat
    LiteRtLmConstraintProviderType = FakeConstraintProvider


def config(**overrides) -> dict:
    value = {
        "temperature": 0.0,
        "top_p": 1.0,
        "threads": 4,
        "maximum_output_tokens": 128,
        "user_new_token_admission": 32,
        "engine_kv_tokens": 1024,
    }
    value.update(overrides)
    return value


def backend(engine: FakeEngine, **overrides) -> MvaLiteRtBackend:
    return MvaLiteRtBackend.from_paths(
        config(**overrides),
        system_prompt_path=CONTRACT / "system-prompt-v1.txt",
        user_template_path=CONTRACT / "user-turn-template-v1.txt",
        semantic_schema_path=CONTRACT / "semantic-output-v1.schema.json",
        litert_lm_module=FakeLiteRt,
        engine=engine,
    )


class MvaLiteRtBackendTests(unittest.TestCase):
    def test_two_turns_use_one_conversation_and_compact_constraint(self) -> None:
        engine = FakeEngine([[
            {"text": "第一輪回答", "end": False},
            {"text": "第二輪回答", "end": False},
        ]])
        subject = backend(engine)
        subject.open_session("session-a", SESSION_FACTS)
        first = subject.generate("session-a", 1, "天空為什麼是藍色？")
        second = subject.generate("session-a", 2, "再簡單一點。")
        self.assertEqual(first.semantic, {"text": "第一輪回答", "end": False})
        self.assertEqual(second.semantic, {"text": "第二輪回答", "end": False})
        self.assertEqual(len(engine.created), 1)
        self.assertEqual(len(engine.created[0].messages), 2)
        self.assertFalse(engine.created[0].closed)
        self.assertEqual(subject.session_id, "session-a")
        kwargs = engine.create_kwargs[0]
        self.assertFalse(kwargs["automatic_tool_calling"])
        self.assertEqual(kwargs["max_output_tokens"], 128)
        self.assertIn("你是「雪板」", kwargs["system_message"])
        self.assertEqual(kwargs["constrained_decoding_config"].kwargs["provider"], "LL_GUIDANCE")

    def test_close_discards_history_before_next_product_session(self) -> None:
        engine = FakeEngine([
            [{"text": "第一個session", "end": False}],
            [{"text": "第二個session", "end": False}],
        ])
        subject = backend(engine)
        subject.open_session("session-a", SESSION_FACTS)
        subject.generate("session-a", 1, "問題一")
        subject.close_session("session-a")
        self.assertTrue(engine.created[0].closed)
        subject.open_session("session-b", SESSION_FACTS)
        subject.generate("session-b", 1, "問題二")
        self.assertEqual(len(engine.created), 2)
        self.assertEqual(engine.created[1].messages, ['{"perceptions":[{"kind":"listen","status":"ok","text":"問題二"}]}'])

    def test_input_too_large_is_rejected_before_inference_and_retains_session(self) -> None:
        engine = FakeEngine([[{"text": "unused", "end": False}]])
        subject = backend(engine, user_new_token_admission=2)
        subject.open_session("session-a", SESSION_FACTS)
        with self.assertRaisesRegex(MvaBackendError, "INPUT_TOO_LARGE") as caught:
            subject.generate("session-a", 1, "三個字")
        self.assertFalse(caught.exception.dirty)
        self.assertEqual(engine.created[0].messages, [])
        self.assertEqual(subject.session_id, "session-a")

    def test_context_limit_closes_without_inference(self) -> None:
        engine = FakeEngine([[{"text": "unused", "end": False}]])
        subject = backend(engine, engine_kv_tokens=140)
        subject.open_session("session-a", SESSION_FACTS)
        with self.assertRaisesRegex(MvaBackendError, "CONTEXT_LIMIT"):
            subject.generate("session-a", 1, "問題")
        self.assertEqual(engine.created[0].messages, [])
        self.assertTrue(engine.created[0].closed)
        self.assertIsNone(subject.session_id)

    def test_invalid_output_is_dirty_and_discards_conversation(self) -> None:
        engine = FakeEngine([[{"text": "不合法結束", "end": True}]])
        subject = backend(engine)
        subject.open_session("session-a", SESSION_FACTS)
        with self.assertRaisesRegex(MvaBackendError, "INVALID_OUTPUT") as caught:
            subject.generate("session-a", 1, "結束嗎")
        self.assertTrue(caught.exception.dirty)
        self.assertTrue(engine.created[0].closed)
        self.assertIsNone(subject.session_id)

    def test_native_failure_is_dirty_and_discards_conversation(self) -> None:
        engine = FakeEngine([[RuntimeError("private failure")]])
        subject = backend(engine)
        subject.open_session("session-a", SESSION_FACTS)
        with self.assertRaisesRegex(MvaBackendError, "GENERATION_FAILED") as caught:
            subject.generate("session-a", 1, "問題")
        self.assertTrue(caught.exception.dirty)
        self.assertNotIn("private failure", str(caught.exception))
        self.assertTrue(engine.created[0].closed)

    def test_cancel_is_once_and_worker_discards_after_typed_terminal(self) -> None:
        engine = FakeEngine([])
        conversation = BlockingConversation()
        engine.create_conversation = lambda **kwargs: (
            engine.create_kwargs.append(kwargs)
            or engine.created.append(conversation)
            or conversation
        )
        subject = backend(engine)
        subject.open_session("session-a", SESSION_FACTS)
        outcome: list[Exception] = []

        def run() -> None:
            try:
                subject.generate("session-a", 1, "問題")
            except Exception as error:  # test captures the typed worker terminal
                outcome.append(error)

        worker = threading.Thread(target=run)
        worker.start()
        self.assertTrue(conversation.started.wait(timeout=1))
        subject.cancel()
        subject.cancel()
        self.assertEqual(conversation.cancel_count, 1)
        conversation.release.set()
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(len(outcome), 1)
        self.assertIsInstance(outcome[0], MvaBackendError)
        self.assertEqual(outcome[0].code, "CANCELLED")
        self.assertTrue(outcome[0].dirty)
        self.assertTrue(conversation.closed)
        self.assertIsNone(subject.session_id)

    def test_once_prewarm_is_disposable_and_product_session_is_separate(self) -> None:
        engine = FakeEngine([
            [{"text": "你好", "end": False}],
            [{"text": "產品回答", "end": False}],
        ])
        subject = backend(engine)
        subject.prewarm_once("請用一句話打招呼。")
        self.assertTrue(engine.created[0].closed)
        self.assertIsNone(subject.session_id)
        subject.open_session("session-a", SESSION_FACTS)
        subject.generate("session-a", 1, "天空為什麼是藍色的？")
        self.assertEqual(len(engine.created), 2)
        self.assertFalse(engine.created[1].closed)


if __name__ == "__main__":
    unittest.main()
