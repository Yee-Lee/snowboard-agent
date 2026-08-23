#!/usr/bin/env python3
from __future__ import annotations
import contextlib, io, json, sys, threading, types, unittest
from unittest import mock

from poc_llm.harness.litert_lm_child_adapter import BackendFailure, Cancelled, Child, LiteRtBackend

PROMPT = {
    "perceptions":[],
    "pending_message_count":0,
    "capabilities":{"perceptions":[],"actions":["rest"],"tools":[]},
}
CONFIG = {
    "candidate_id":"CAND-ARM64-TEST","pairing_revision":"synthetic-arm64-v1",
    "platform":"ubuntu-aarch64","runtime_sha256":"1"*64,"model_sha256":"2"*64,
    "max_output_tokens":16,"generate_timeout_ms":15000,"term_timeout_ms":2000,
}

class FakeBackend:
    def __init__(self, block: bool = False):
        self.block = block
        self.started = threading.Event()
        self.release = threading.Event()
        self.cancelled = False
        self.closed = False
    def generate(self, prompt: str, *, max_output_tokens: int) -> str:
        self.started.set()
        if self.block:
            self.release.wait(2)
        if self.cancelled:
            raise Cancelled("cancelled")
        return '{"action_kind":"rest","action_payload":{},"next_perceptions":[]}'
    def cancel(self) -> None:
        self.cancelled = True
        self.release.set()
    def close(self) -> None:
        self.closed = True

def frame(kind: str, request_id: str | None = None) -> dict:
    value = {"type":kind,"protocol_version":"snowboard.llm/1"}
    if request_id is not None:
        value["request_id"] = request_id
    if kind == "GENERATE":
        value["input"] = PROMPT
    return value

class ChildAdapterTest(unittest.TestCase):
    def make_child(self, backend: FakeBackend):
        output = io.StringIO()
        return Child(CONFIG, "3"*64, backend, output), output
    def frames(self, output: io.StringIO):
        return [json.loads(line) for line in output.getvalue().splitlines()]
    def test_ready_generate_result_shutdown(self):
        backend = FakeBackend()
        child, output = self.make_child(backend)
        child.ready()
        self.assertTrue(child.protocol.is_valid(self.frames(output)[0]))
        self.assertTrue(child.handle(frame("GENERATE", "req-1")))
        child.worker.join(2)
        self.assertFalse(child.handle(frame("SHUTDOWN")))
        child.close()
        self.assertEqual([item["type"] for item in self.frames(output)], ["READY","RESULT","SHUTDOWN_ACK"])
        self.assertTrue(backend.closed)
    def test_busy_preserves_active_request(self):
        backend = FakeBackend(block=True)
        child, output = self.make_child(backend)
        child.handle(frame("GENERATE", "req-a"))
        self.assertTrue(backend.started.wait(1))
        self.assertTrue(child.handle(frame("GENERATE", "req-b")))
        self.assertEqual(self.frames(output)[0], {
            "code":"BUSY","protocol_version":"snowboard.llm/1",
            "request_id":"req-b","state":"GENERATING","type":"ERROR",
        })
        backend.cancel()
        child.worker.join(2)
        child.close()
    def test_cooperative_cancel_correlates_terminal(self):
        backend = FakeBackend(block=True)
        child, output = self.make_child(backend)
        child.handle(frame("GENERATE", "req-cancel"))
        self.assertTrue(backend.started.wait(1))
        self.assertTrue(child.handle(frame("CANCEL", "req-cancel")))
        child.worker.join(2)
        self.assertEqual(self.frames(output)[0]["type"], "CANCELLED")
        self.assertEqual(self.frames(output)[0]["request_id"], "req-cancel")
        child.close()
    def test_stale_cancel_is_invalid_and_nonterminal(self):
        backend = FakeBackend()
        child, output = self.make_child(backend)
        self.assertTrue(child.handle(frame("CANCEL", "req-stale")))
        self.assertEqual(self.frames(output)[0]["code"], "INVALID_REQUEST")
        self.assertEqual(self.frames(output)[0]["state"], "READY")
        child.close()
    def test_timeout_is_not_reported_as_cancel(self):
        backend = FakeBackend(block=True)
        config = {**CONFIG, "generate_timeout_ms":10}
        output = io.StringIO()
        child = Child(config, "3"*64, backend, output)
        child.handle(frame("GENERATE", "req-timeout"))
        child.worker.join(2)
        terminal = self.frames(output)[0]
        self.assertEqual(terminal["type"], "ERROR")
        self.assertEqual(terminal["code"], "TIMEOUT")
        self.assertEqual(terminal["request_id"], "req-timeout")
        child.close()

    def test_engine_uses_model_kv_cache_default(self):
        captured = {}

        class Conversation:
            def send_message(self, prompt):
                captured["prompt_type"] = type(prompt).__name__
                return {"content": [{"type": "text", "text": "ok"}]}
            def send_message_async(self, prompt):
                raise AssertionError("async stream must not be used")
            def cancel_process(self):
                pass
            def close(self):
                pass

        class Engine:
            def __init__(self, model_path, **kwargs):
                captured["model_path"] = model_path
                captured["kwargs"] = kwargs
            def create_conversation(self, **kwargs):
                captured["conversation_kwargs"] = kwargs
                return Conversation()
            def close(self):
                pass

        fake = types.SimpleNamespace(
            Engine=Engine,
            Backend=types.SimpleNamespace(CPU=lambda **kwargs: ("CPU", kwargs)),
            SamplerConfig=lambda **kwargs: ("SAMPLER", kwargs),
        )
        config = {
            **CONFIG,
            "model_path": "/tmp/model.litertlm",
            "threads": 4,
            "temperature": 0.0,
            "top_p": 1.0,
            "max_input_tokens": 128,
        }
        with mock.patch.dict(sys.modules, {"litert_lm": fake}):
            backend = LiteRtBackend(config)
        self.assertEqual(captured["model_path"], config["model_path"])
        self.assertNotIn("max_num_tokens", captured["kwargs"])
        self.assertEqual(backend.generate("hello", max_output_tokens=16), "ok")
        self.assertEqual(captured["prompt_type"], "str")
        self.assertEqual(captured["conversation_kwargs"]["max_output_tokens"], 16)
        backend.close()

    def test_backend_failure_diagnostic_redacts_message(self):
        secret = "sensitive backend detail"
        failure = BackendFailure("send_message_async", RuntimeError(secret))
        backend = FakeBackend()
        child, output = self.make_child(backend)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            child._active_input = PROMPT
            child.active_request = "req-failed"
            child._terminal("req-failed", None, failure)
        diagnostic = stderr.getvalue()
        self.assertIn('"stage":"send_message_async"', diagnostic)
        self.assertIn('"cause_class":"RuntimeError"', diagnostic)
        self.assertNotIn(secret, diagnostic)
        self.assertEqual(self.frames(output)[0]["code"], "GENERATION_FAILED")
        child.close()

if __name__ == "__main__":
    unittest.main()
