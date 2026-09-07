from __future__ import annotations

import json
from pathlib import Path
import unittest

from poc_llm.efficiency.backend import EfficiencyLiteRtBackend
from poc_llm.efficiency.raw_stream import RawStreamChunk, RawStreamError
from poc_llm.harness.mva_contract import SESSION_FACTS
from poc_llm.harness.mva_litert_backend import MvaBackendError


ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "poc_llm/contracts/mva"


class Benchmark:
    time_to_first_token_in_second = 0.001
    last_prefill_token_count = 7
    last_decode_token_count = 4


class Conversation:
    def __init__(self):
        self.token_count = 10
        self.closed = False
        self.messages = []
        self.cancelled = 0
    def render_message_to_string(self, prompt):
        return "rendered:" + prompt
    def get_benchmark_info(self):
        return Benchmark()
    def cancel_process(self):
        self.cancelled += 1
    def close(self):
        self.closed = True


class Engine:
    def __init__(self):
        self.created = []
        self.closed = False
    def create_conversation(self, **kwargs):
        value = Conversation()
        self.created.append(value)
        return value
    def tokenize(self, text):
        return list(text)
    def close(self):
        self.closed = True


class ConfigValue:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class ResponseFormat:
    @staticmethod
    def json(schema):
        return ("J", schema)
    @staticmethod
    def regex(pattern):
        return ("P", pattern)


class Provider:
    LL_GUIDANCE = 1


class LiteRt:
    SamplerConfig = ConfigValue
    ConstrainedDecodingConfig = ConfigValue
    ResponseFormat = ResponseFormat
    LiteRtLmConstraintProviderType = Provider


def config():
    return {"temperature": 0.0, "top_p": 1.0, "maximum_output_tokens": 128,
            "user_new_token_admission": 32, "engine_kv_tokens": 1024}


def backend(encoding="J", responses=None):
    engine = Engine()
    values = iter(responses or [])
    def sender(conversation, prompt, *, response_format):
        conversation.messages.append(prompt)
        value = next(values)
        if isinstance(value, Exception):
            raise value
        return iter([RawStreamChunk(value, False), RawStreamChunk("", True)])
    return EfficiencyLiteRtBackend(config(), encoding=encoding,
        system_message=(CONTRACT / "system-prompt-v1.txt").read_text(),
        user_template=(CONTRACT / "user-turn-template-v1.txt").read_text(),
        semantic_schema=json.loads((CONTRACT / "semantic-output-v1.schema.json").read_text()),
        profile_digest="a" * 64, child_generation=1, litert_lm_module=LiteRt,
        engine=engine, raw_sender=sender), engine


class EfficiencyBackendTests(unittest.TestCase):
    def test_j_and_p_use_same_internal_semantics(self):
        j, _ = backend("J", ['{"text":"回答","end":false}'])
        j.open_session("j", SESSION_FACTS)
        self.assertEqual(j.generate("j", 1, "問題").semantic, {"text": "回答", "end": False})
        p, _ = backend("P", ["S\n回答"])
        p.open_session("p", SESSION_FACTS)
        self.assertEqual(p.generate("p", 1, "問題").semantic, {"text": "回答", "end": False})

    def test_hold_adoption_reuses_exact_clean_conversation(self):
        subject, engine = backend("J", ['{"text":"回答","end":false}'])
        prepared = subject.prepare_clean(SESSION_FACTS)
        self.assertEqual(subject.readiness_state, "HELD")
        opened = subject.open_session("held", SESSION_FACTS, readiness="H")
        self.assertTrue(opened["held_adopted"])
        subject.generate("held", 1, "問題")
        subject.close_session("held")
        self.assertEqual(len(engine.created), 1)
        self.assertTrue(engine.created[0].closed)
        self.assertGreaterEqual(prepared.open_ms, 0)

    def test_mismatch_refuses_adoption_and_explicit_fallback_is_fresh(self):
        subject, engine = backend("J")
        subject.prepare_clean(SESSION_FACTS)
        subject._profile_digest = "b" * 64
        with self.assertRaisesRegex(MvaBackendError, "READINESS_MISMATCH"):
            subject.open_session("mismatch", SESSION_FACTS, readiness="H")
        opened = subject.open_session("fallback", SESSION_FACTS, readiness="H", allow_fallback=True)
        self.assertEqual(opened["readiness_mode"], "FALLBACK_D")
        self.assertEqual(len(engine.created), 2)
        self.assertTrue(engine.created[0].closed)

    def test_token_limit_is_dirty_and_never_success(self):
        subject, engine = backend("P", [RawStreamError("TOKEN_LIMIT")])
        subject.open_session("session", SESSION_FACTS)
        with self.assertRaisesRegex(MvaBackendError, "INVALID_OUTPUT") as raised:
            subject.generate("session", 1, "問題")
        self.assertTrue(raised.exception.dirty)
        self.assertTrue(engine.created[0].closed)
        self.assertIsNone(subject.session_id)

    def test_no_request_hold_close_and_new_session_has_fresh_conversation(self):
        subject, engine = backend("J")
        subject.prepare_clean(SESSION_FACTS)
        self.assertTrue(subject.close_unclaimed())
        subject.open_session("new", SESSION_FACTS)
        self.assertEqual(len(engine.created), 2)
        self.assertIsNot(engine.created[0], engine.created[1])


if __name__ == "__main__":
    unittest.main()
