#!/usr/bin/env python3
from __future__ import annotations
import io, json, threading, unittest

from poc_llm.harness.litert_lm_child_adapter import Cancelled, Child

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

if __name__ == "__main__":
    unittest.main()
