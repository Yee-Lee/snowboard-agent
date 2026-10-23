"""M5T-WRK-001: v4 framing, text-bound ticket and no digest fields."""

import pytest

from sbd.cognition.llm_child_protocol import (
    LLMProtocolError, ProtocolLedger, V4_READY_FIELDS, parse_ready,
)


def command(ledger, op, **extra):
    frame = {"protocol": 4, "op": op, "request_id": ledger.counter + 1,
             "session_id": "s", "generation": 1, **extra}
    ledger.command(frame)
    return frame


def event(ledger, name, **extra):
    frame = {"protocol": 4, "event": name, "request_id": ledger.counter,
             "session_id": "s", "generation": 1, **extra}
    ledger.event(frame)
    return frame


def open_conversation(ledger):
    command(ledger, "OPEN")
    event(ledger, "OPENED", conversation_revision=0)


def measured(ledger, text="你好", **extra):
    command(ledger, "MEASURE", text=text, output_reserve_tokens=128, **extra)
    event(ledger, "MEASURED", conversation_revision=ledger.revision,
          ticket="a" * 32, user_tokens=4, current_kv_tokens=0,
          rendered_incremental_tokens=20, runtime_prefill_tokens=21,
          output_reserve_tokens=128, engine_context_tokens=1024)


def test_v4_ready_exact_fields_rejects_v3_and_digest():
    identity = {key: ("snowboard.llm/4" if key == "protocol_name" else
                      "core-m5-tool-001" if key == "profile_id" else
                      "requirements/m5tool/semantic-output-v1.schema.json"
                      if key == "response_schema_locator" else
                      "none" if key == "conversation_state" else
                      "disabled" if key == "network" else
                      1 if key in {"prompt_tokens", "max_output_tokens", "engine_context_tokens",
                                   "threads", "min_mem_available_generate_bytes",
                                   "min_mem_available_speak_bytes"} else
                      0.0 if key in {"temperature", "top_p"} else "fixed")
                for key in V4_READY_FIELDS - {"pid", "pgid"}}
    frame = {**identity, "pid": 100, "pgid": 100, "protocol": 4, "event": "READY"}
    parse_ready(frame, expected_identity=identity, pid=100, pgid=100)
    with pytest.raises(LLMProtocolError):
        parse_ready({**frame, "protocol": 3}, expected_identity=identity, pid=100, pgid=100)
    with pytest.raises(LLMProtocolError):
        parse_ready({**frame, "model_sha256": "legacy"}, expected_identity=identity, pid=100, pgid=100)


def test_v4_measure_status_wrapper_and_exact_ticket_text():
    ledger = ProtocolLedger(version=4)
    open_conversation(ledger)
    text = '{"source":"listen","last_dispatch_status":"ok","text":"你好"}'
    measured(ledger, text, user_text="你好")
    with pytest.raises(LLMProtocolError):
        command(ledger, "GENERATE", text=text + " ", conversation_revision=0, ticket="a" * 32)
    assert ledger.state == "MEASURED"
    command(ledger, "DISCARD_TICKET", conversation_revision=0, ticket="a" * 32)
    event(ledger, "TICKET_DISCARDED", conversation_revision=0, ticket="a" * 32,
          native_render_scrubbed=True, ticket_invalidated=True,
          private_input_erased=True, conversation_state="ready")
    assert ledger.state == "CONVERSATION_READY"


def test_v4_wrapper_mismatch_and_digest_field_rejected():
    ledger = ProtocolLedger(version=4)
    open_conversation(ledger)
    text = '{"source":"listen","last_dispatch_status":"ok","text":"你好"}'
    with pytest.raises(LLMProtocolError):
        command(ledger, "MEASURE", text=text, user_text="別的", output_reserve_tokens=128)
    with pytest.raises(LLMProtocolError):
        command(ledger, "MEASURE", text="你好", input_sha256="x", output_reserve_tokens=128)
