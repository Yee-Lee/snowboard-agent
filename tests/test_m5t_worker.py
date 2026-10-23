"""M5T-WRK-001/002: v4 child paths keep exact text and semantic terminal."""

from sbd.cognition.litert_lm.worker import WorkerSession
from sbd.cognition.semantic import ToolSemantic


class Engine:
    def tokenize(self, text):
        return list(text)


class Runtime:
    protocol_version = 4
    _engine = Engine()

    def __init__(self, semantic):
        self.semantic = semantic
        self.sent = []

    def open_conversation(self):
        pass

    def measure(self, text):
        self.sent.append(("measure", text))
        return {"user_tokens": len(text), "current_kv_tokens": 0,
                "rendered_incremental_tokens": 100, "runtime_prefill_tokens": 101,
                "output_reserve_tokens": 128, "engine_context_tokens": 1024}

    def generate_stream(self, text, emit):
        self.sent.append(("generate", text))
        if self.semantic.text:
            emit(self.semantic.text)
        return self.semantic, 8, 109, 101

    def scrub_ticket(self):
        pass


def command(session, op, request_id, **extra):
    frame = {"protocol": 4, "op": op, "request_id": request_id,
             "session_id": "s", "generation": 1, **extra}
    session.ledger.command(frame)
    events = session.execute(frame)
    for event in events:
        session.ledger.event(event)
    return events


def test_v4_worker_tool_emits_semantic_without_safe_text_or_digest():
    runtime = Runtime(ToolSemantic("tool", "", "mock.send", {"message": "買牛奶"}))
    session = WorkerSession(runtime)
    command(session, "OPEN", 1)
    text = "請幫我送出訊息"
    measured = command(session, "MEASURE", 2, text=text, output_reserve_tokens=128)
    assert "input_sha256" not in measured[0]
    safe = []
    frame = {"protocol": 4, "op": "GENERATE", "request_id": 3,
             "session_id": "s", "generation": 1, "text": text,
             "conversation_revision": 0, "ticket": measured[0]["ticket"]}
    session.ledger.command(frame)
    events = session.execute(frame, lambda seq, fragment, instant: safe.append(fragment))
    assert safe == []
    assert events[0]["semantic"] == {"intent": "tool", "text": "",
                                    "tool_name": "mock.send", "arguments": {"message": "買牛奶"}}
    assert "input_sha256" not in events[0]
    session.ledger.event(events[0])


def test_v4_worker_status_user_tokens_use_original_utterance():
    runtime = Runtime(ToolSemantic("speak", "你好。", "", {"message": ""}))
    session = WorkerSession(runtime)
    command(session, "OPEN", 1)
    text = '{"source":"listen","last_dispatch_status":"ok","text":"你好"}'
    measured = command(session, "MEASURE", 2, text=text,
                       user_text="你好", output_reserve_tokens=128)
    assert measured[0]["user_tokens"] == 2
    assert runtime.sent == [("measure", text)]
