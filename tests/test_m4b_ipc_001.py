"""M4B-IPC-001 — structured ``snowboard.llm/1`` codec regressions."""

from __future__ import annotations

import asyncio
import dataclasses
import json
import math
from types import SimpleNamespace

import pytest

from sbd.cognition.llm import LLMGeneration, LLMGenerationMetrics, LLMResourceSample
from sbd.cognition.llm_child_protocol import (
    LLMProtocolError,
    LLMReadyIdentity,
    LLMWireCancelled,
    LLMWireError,
    LLMWireResult,
    MAX_CONTROL_BYTES,
    PROTOCOL_VERSION,
    ReasoningInputContractError,
    ReasoningInputTooLarge,
    encode_cancel,
    encode_frame,
    encode_generate,
    encode_reasoning_input,
    parse_cancel,
    parse_generate,
    parse_ready,
    parse_terminal,
    read_frame,
)
from sbd.cognition.prompt_builder import ReasoningInput, ReasoningPerception
from sbd.cognition.litert_lm.worker import _advance_request_identity


def _reader(*parts: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader(limit=MAX_CONTROL_BYTES + 1)
    for part in parts:
        reader.feed_data(part)
    reader.feed_eof()
    return reader


def _input(*, text: str | None = "hello") -> ReasoningInput:
    return ReasoningInput(
        perceptions=(
            ReasoningPerception("look", "ok", "" if text is None else text),
            ReasoningPerception("listen", "timeout", ""),
        ),
        pending_message_count=1,
        available_perceptions=("look", "listen"),
        available_actions=("rest", "speak"),
        tool_schemas=(),
    )


def test_m4b_ipc_001_worker_request_identity_is_monotonic_per_generation() -> None:
    generation, counter = _advance_request_identity("llm.3.1", None, 0)
    assert (generation, counter) == (3, 1)
    assert _advance_request_identity("llm.3.2", generation, counter) == (3, 2)
    for request_id in ("llm.3.1", "llm.3.3", "llm.4.2", "llm.0.2"):
        with pytest.raises(ValueError, match="identity sequence"):
            _advance_request_identity(request_id, generation, counter)


def test_m4b_ipc_001_shutdown_ack_precedes_native_runtime_teardown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sbd.cognition.litert_lm import worker

    order: list[str] = []

    class Runtime:
        def close(self) -> None:
            order.append("runtime.close")

    runtime = Runtime()
    args = SimpleNamespace(
        model="model", runtime_root="runtime", native_sha256="a" * 64,
        startup_evidence="evidence", candidate_id="candidate",
        pairing_revision="revision", platform="platform",
        runtime_sha256="b" * 64, model_sha256="c" * 64,
        config_sha256="d" * 64,
    )
    monkeypatch.setattr(worker, "LiteRTRuntime", lambda **kwargs: runtime)
    monkeypatch.setattr(worker, "_prewarm", lambda value: None)
    monkeypatch.setattr(worker, "_write_startup_evidence", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker.select, "select", lambda *args: ([object()], [], []))
    monkeypatch.setattr(
        worker, "_read_line",
        lambda: {"type": "SHUTDOWN", "protocol_version": PROTOCOL_VERSION},
    )
    monkeypatch.setattr(worker, "_write", lambda value: order.append(str(value["type"])))
    monkeypatch.setattr(
        worker, "_exit_after_shutdown_ack", lambda: order.append("direct-exit"),
    )

    assert worker.run(args) == 0
    assert order == ["READY", "SHUTDOWN_ACK", "direct-exit", "runtime.close"]


def _identity() -> LLMReadyIdentity:
    return LLMReadyIdentity(
        candidate_id="CAND-LRT-G4E2B-MOBILE-R1",
        pairing_revision="litert-lm-v0.16.0-pi-g2b-r5",
        platform="pi-debian13-aarch64",
        runtime_sha256="a" * 64,
        model_sha256="b" * 64,
        config_sha256="c" * 64,
    )


def _ready(identity: LLMReadyIdentity | None = None) -> dict[str, object]:
    value = identity or _identity()
    return {
        "type": "READY",
        "protocol_version": PROTOCOL_VERSION,
        "state": "READY",
        "identity": dataclasses.asdict(value),
    }


def _metrics() -> dict[str, object]:
    return {
        "init_ms": 0.0,
        "ttft_ms": 1.0,
        "prefill_tokens": 1,
        "prefill_tokens_per_second": 2.0,
        "decode_tokens": 128,
        "decode_tokens_per_second": 3.0,
        "kv_tokens": 1024,
    }


def _result(
    request_id: str = "llm.1.1",
    *,
    metrics: object | None = None,
) -> dict[str, object]:
    return {
        "type": "RESULT",
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "response": {
            "action_kind": "rest",
            "action_payload": {},
            "next_perceptions": [],
        },
        "metrics": _metrics() if metrics is None else metrics,
        "state": "READY",
    }


def test_m4b_ipc_001_public_structured_values_have_exact_fields() -> None:
    assert [field.name for field in dataclasses.fields(LLMGenerationMetrics)] == [
        "init_ms", "ttft_ms", "prefill_tokens", "prefill_tokens_per_second",
        "decode_tokens", "decode_tokens_per_second", "kv_tokens",
    ]
    assert [field.name for field in dataclasses.fields(LLMGeneration)] == [
        "response", "metrics",
    ]
    assert [field.name for field in dataclasses.fields(LLMResourceSample)] == [
        "owner_pss_bytes", "mem_available_bytes",
    ]


def test_m4b_ipc_001_generate_is_canonical_and_excludes_private_control() -> None:
    encoded = encode_generate("llm.3.12", _input())
    assert set(encoded) == {"type", "protocol_version", "request_id", "input"}
    assert encoded["type"] == "GENERATE"
    projected = encoded["input"]
    assert projected == {
        "perceptions": [
            {"kind": "listen", "status": "timeout", "text": ""},
            {"kind": "look", "status": "ok", "text": "hello"},
        ],
        "pending_message_count": 1,
        "capabilities": {
            "perceptions": ["listen", "look"],
            "actions": ["speak", "rest"],
            "tools": [],
        },
    }
    wire = encode_frame(encoded)
    assert b"session" not in wire
    assert b"pending_message_ids" not in wire
    assert b"extra" not in wire
    request_id, received = parse_generate(encoded)
    assert request_id == "llm.3.12" and received == projected


@pytest.mark.parametrize("frame_type", ["GENERATE", "CANCEL"])
@pytest.mark.parametrize("mutation", ["missing", "extra", "wrong_type"])
def test_m4b_ipc_001_generate_cancel_exact_schema_negative_matrix(
    frame_type: str,
    mutation: str,
) -> None:
    frame = (
        encode_generate("llm.1.1", _input())
        if frame_type == "GENERATE"
        else encode_cancel("llm.1.1")
    )
    if mutation == "missing":
        frame.pop("request_id")
    elif mutation == "extra":
        frame["extra"] = True
    else:
        frame["request_id"] = 1
    parser = parse_generate if frame_type == "GENERATE" else parse_cancel
    with pytest.raises(LLMProtocolError):
        parser(frame)


@pytest.mark.parametrize(
    "request_id",
    ["", "1", "llm.1", "llm.a.1", "llm.1.-1", "llm.1." + "1" * 130, True],
)
def test_m4b_ipc_001_rejects_invalid_request_ids_without_echo(request_id: object) -> None:
    with pytest.raises(LLMProtocolError, match="invalid identity") as captured:
        encode_cancel(request_id)  # type: ignore[arg-type]
    if str(request_id):
        assert str(request_id) not in str(captured.value)


def test_m4b_ipc_001_control_boundary_fragment_and_coalesce() -> None:
    async def run() -> None:
        prefix = encode_frame({"protocol_version": PROTOCOL_VERSION, "value": ""})
        exact = encode_frame({
            "protocol_version": PROTOCOL_VERSION,
            "value": "x" * (MAX_CONTROL_BYTES - len(prefix)),
        })
        assert len(exact) == MAX_CONTROL_BYTES
        split = len(exact) // 2
        assert (await read_frame(_reader(exact[:split], exact[split:]))) ["value"]
        second = encode_frame({"protocol_version": PROTOCOL_VERSION, "value": "second"})
        reader = _reader(exact + second)
        assert (await read_frame(reader))["value"].startswith("x")
        assert (await read_frame(reader))["value"] == "second"
        with pytest.raises(ReasoningInputTooLarge):
            encode_frame({
                "protocol_version": PROTOCOL_VERSION,
                "value": "x" * (MAX_CONTROL_BYTES - len(prefix) + 1),
            })

    asyncio.run(run())


@pytest.mark.parametrize("raw", [b"not-json\n", b"\xff\n", b"[]\n", b'{}\n'])
def test_m4b_ipc_001_rejects_invalid_utf8_json_and_protocol(raw: bytes) -> None:
    async def run() -> None:
        with pytest.raises(LLMProtocolError):
            await read_frame(_reader(raw))

    asyncio.run(run())


def test_m4b_ipc_001_ready_exact_keys_and_each_identity_mismatch() -> None:
    expected = _identity()
    assert parse_ready(_ready(), expected_identity=expected).identity == expected
    for field in (item.name for item in dataclasses.fields(LLMReadyIdentity)):
        wrong = _ready()
        identity = wrong["identity"]
        assert isinstance(identity, dict)
        identity[field] = "d" * 64 if field.endswith("sha256") else "wrong"
        with pytest.raises(LLMProtocolError, match=field):
            parse_ready(wrong, expected_identity=expected)
    for mutation in (
        lambda value: value.__setitem__("extra", True),
        lambda value: value.__setitem__("state", "GENERATING"),
        lambda value: value.__setitem__("protocol_version", "wrong"),
    ):
        wrong = _ready()
        mutation(wrong)
        with pytest.raises(LLMProtocolError):
            parse_ready(wrong, expected_identity=expected)


def test_m4b_ipc_001_result_metrics_boundaries_and_typed_terminals() -> None:
    result = parse_terminal(_result(), active_request_id="llm.1.1")
    assert isinstance(result, LLMWireResult)
    assert result.metrics.prefill_tokens == 1
    assert result.metrics.decode_tokens == 128
    assert result.metrics.kv_tokens == 1024
    cancelled = parse_terminal({
        "type": "CANCELLED",
        "protocol_version": PROTOCOL_VERSION,
        "request_id": "llm.1.1",
        "state": "READY",
    }, active_request_id="llm.1.1")
    assert isinstance(cancelled, LLMWireCancelled)
    fatal = parse_terminal({
        "type": "ERROR",
        "protocol_version": PROTOCOL_VERSION,
        "request_id": "llm.1.1",
        "code": "PROTOCOL_ERROR",
        "state": "FATAL",
    }, active_request_id="llm.1.1")
    assert isinstance(fatal, LLMWireError) and fatal.state == "FATAL"


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("init_ms", -0.1),
        ("ttft_ms", math.nan),
        ("prefill_tokens", True),
        ("prefill_tokens", 0),
        ("prefill_tokens", 129),
        ("prefill_tokens_per_second", 0.0),
        ("decode_tokens", 0),
        ("decode_tokens", 129),
        ("decode_tokens_per_second", math.inf),
        ("kv_tokens", 0),
        ("kv_tokens", 1025),
    ],
)
def test_m4b_ipc_001_rejects_invalid_metric_without_private_echo(
    field: str,
    bad: object,
) -> None:
    metrics = _metrics()
    metrics[field] = bad
    with pytest.raises(LLMProtocolError, match=field) as captured:
        parse_terminal(_result(metrics=metrics), active_request_id="llm.1.1")
    assert "hello" not in str(captured.value)


def test_m4b_ipc_001_rejects_missing_partial_extra_wrong_and_late_terminal() -> None:
    for metrics in ({}, {"init_ms": 0.0}, {**_metrics(), "extra": 1}):
        with pytest.raises(LLMProtocolError, match="metrics"):
            parse_terminal(_result(metrics=metrics), active_request_id="llm.1.1")
    for mutation in (
        lambda value: value.pop("metrics"),
        lambda value: value.__setitem__("extra", True),
        lambda value: value.__setitem__("request_id", "llm.1.2"),
    ):
        wrong = _result()
        mutation(wrong)
        with pytest.raises(LLMProtocolError):
            parse_terminal(wrong, active_request_id="llm.1.1")


def test_m4b_ipc_001_reasoning_input_bounds_and_contract_fail_closed() -> None:
    assert encode_reasoning_input(_input(text="x" * 4096))["perceptions"]
    with pytest.raises(ReasoningInputTooLarge, match="codepoint"):
        encode_reasoning_input(_input(text="private" + "x" * 4097))
    duplicate = ReasoningInput(
        perceptions=(
            ReasoningPerception("listen", "ok", "one"),
            ReasoningPerception("listen", "ok", "two"),
        ),
        pending_message_count=0,
        available_perceptions=("listen",),
        available_actions=("rest",),
        tool_schemas=(),
    )
    with pytest.raises(ReasoningInputContractError, match="duplicate") as captured:
        encode_reasoning_input(duplicate)
    assert "one" not in str(captured.value) and "two" not in str(captured.value)
