"""M5T-PAY-001/002: side-effect admission and model-facing projection."""

import json

import pytest

from sbd.action.tool.mock_send import MockSend
from sbd.action.tool.registry import ToolArgumentsInvalid, ToolRegistry
from sbd.cognition.prompt_builder import ToolProjector, UnsupportedInputError, is_m5_look_wrapper
from sbd.cognition.semantic import (IncrementalToolSemanticParser, IncrementalM5ModelParser,
                                    SemanticError, validate_m5_model_semantic,
                                    validate_tool_semantic, load_m5_response_schema)
from sbd.core.events import PerceptionResult


def envelope(intent, text="", name="", message=""):
    return {"intent": intent, "text": text, "tool_name": name,
            "arguments": {"message": message}}


@pytest.mark.parametrize("value,source", [
    (envelope("speak", "你好呀！"), "listen"),
    (envelope("end", "再見。"), "listen"),
    (envelope("end"), "look"),
    (envelope("tool", name="mock.send", message="請幫我拿水"), "listen"),
    (envelope("look"), "listen"),
])
def test_valid_envelopes(value, source):
    result = validate_tool_semantic(json.dumps(value), source=source)
    assert result.intent == value["intent"]


@pytest.mark.parametrize("value,source", [
    (envelope("tool", name="mqtt.send", message="水"), "listen"),
    (envelope("tool", name="mock.send", message=" "), "listen"),
    (envelope("tool", name="mock.send", message="水" * 41), "listen"),
    (envelope("tool", text="已送", name="mock.send", message="水"), "listen"),
    (envelope("look"), "look"),
    (envelope("tool", name="mock.send", message="水"), "look"),
    (envelope("speak", "話" * 31), "listen"),
    (envelope("speak", "好", message="私訊"), "listen"),
])
def test_invalid_envelopes_block_side_effect(value, source):
    with pytest.raises(SemanticError):
        validate_tool_semantic(value, source=source)


def test_duplicate_and_extra_keys_rejected():
    with pytest.raises(SemanticError):
        validate_tool_semantic('{"intent":"look","intent":"tool","text":"",'
                               '"tool_name":"","arguments":{"message":""}}')
    with pytest.raises(SemanticError):
        validate_tool_semantic({**envelope("look"), "route": "KEEP_NEXT"})


def test_stream_text_before_intent_and_late_conflict():
    parser = IncrementalToolSemanticParser()
    assert parser.feed(b'{"text":"hello",') == ()
    assert parser.feed(b'"intent":"speak",') == ("hello",)
    assert parser.feed(b'"tool_name":"mock.send","arguments":{"message":"x"}}') == ()
    with pytest.raises(SemanticError):
        parser.finish()


def test_tool_and_look_streams_never_release_text():
    for intent, name, message in (("tool", "mock.send", "x"), ("look", "", "")):
        parser = IncrementalToolSemanticParser()
        raw = json.dumps(envelope(intent, name=name, message=message)).encode()
        assert parser.feed(raw) == ()
        assert parser.finish().intent == intent


def test_two_field_model_tool_uses_fixed_private_payload_and_never_speaks_claim():
    raw = '{"text":"遠端連線已啟用。","intent":"tool"}'
    parser = IncrementalM5ModelParser()
    assert parser.feed(raw[:24].encode()) == ()
    assert parser.feed(raw[24:].encode()) == ()
    semantic = parser.finish()
    assert semantic == validate_m5_model_semantic(raw)
    assert semantic.text == ""
    assert semantic.tool_name == "mock.send"
    assert semantic.arguments == {"message": "啟用遠端連線"}
    assert set(load_m5_response_schema()["properties"]) == {"intent", "text"}


def test_two_field_model_observation_discards_text_and_rejects_extra_fields():
    semantic = validate_m5_model_semantic({"intent": "look", "text": "我看到雪花。"})
    assert semantic.text == "" and semantic.tool_name == ""
    with pytest.raises(SemanticError):
        validate_m5_model_semantic({"intent": "tool", "text": "", "tool_name": "mqtt.send"})
    with pytest.raises(SemanticError):
        validate_m5_model_semantic('{"intent":"look","intent":"tool","text":""}')


def fact(kind, text, *, status="ok"):
    return PerceptionResult(kind, status, text, {}, "session", 1, 2)


def test_listen_status_counts_original_text_separately():
    projection = ToolProjector().project(perceptions=(fact("listen", " 剛才送出了嗎 "),),
        session_id="session", turn_id=1, pending_message_count=0,
        last_dispatch_status="ok")
    assert projection.user_text == "剛才送出了嗎"
    assert json.loads(projection.text) == {"source": "listen", "last_dispatch_status": "ok",
                                           "text": "剛才送出了嗎"}


def test_look_preserves_longer_fact_and_source_boundary():
    content = "書" * 80
    projection = ToolProjector().project(perceptions=(fact("look", content),),
        session_id="session", turn_id=1, pending_message_count=0)
    assert projection.source == "look"
    assert projection.user_text is None
    assert json.loads(projection.text)["facts"] == content
    assert is_m5_look_wrapper(projection.text)
    assert is_m5_look_wrapper(json.dumps(json.loads(projection.text),
        ensure_ascii=False, sort_keys=True))
    with pytest.raises(UnsupportedInputError):
        ToolProjector().project(perceptions=(fact("look", content),), session_id="other",
                                turn_id=1, pending_message_count=0)


@pytest.mark.asyncio
async def test_mock_send_validates_before_dispatch_and_records_once():
    send = MockSend()
    registry = ToolRegistry()
    registry.register(send.registered_tool())
    registry.seal()
    with pytest.raises(ToolArgumentsInvalid):
        await registry.dispatch("mock.send", {"message": " "})
    assert send.calls == []
    assert await registry.dispatch("mock.send", {"message": " 買牛奶 "}) == {}
    assert send.calls == ["買牛奶"]


@pytest.mark.asyncio
async def test_mock_send_known_error_is_not_success():
    send = MockSend(outcome="error")
    registry = ToolRegistry()
    registry.register(send.registered_tool())
    registry.seal()
    with pytest.raises(ToolArgumentsInvalid):
        await registry.dispatch("mock.send", {"message": "買牛奶"})
    assert send.calls == ["買牛奶"]
