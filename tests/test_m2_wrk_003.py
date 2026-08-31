"""M2-WRK-003 deterministic PromptBuilder and Reasoner tests."""

from __future__ import annotations

import asyncio

import pytest

from sbd.action.payload_validator import ActionPayloadValidator
from sbd.action.tool import ToolRegistry
from sbd.adaptor.errors import AdapterRejected, AdapterTimeout
from sbd.cognition.llm import (
    LLMGeneration,
    LLMGenerationMetrics,
    MockLLMEngineAdapter,
)
from sbd.cognition.prompt_builder import PromptBuilder
from sbd.cognition.reasoner import Reasoner
from sbd.core.event_bus import EventBus
from sbd.core.events import ErrorOccurred, LLMResponse, PerceptionResult


def _validator() -> ActionPayloadValidator:
    tools = ToolRegistry()
    tools.seal()
    return ActionPayloadValidator(tools=tools)


def _response(
    kind: str,
    payload: dict,
    next_perceptions: list[str],
) -> LLMGeneration:
    return LLMGeneration(
        {
            "action_kind": kind,
            "action_payload": payload,
            "next_perceptions": next_perceptions,
        },
        _metrics(),
    )


def _metrics() -> LLMGenerationMetrics:
    return LLMGenerationMetrics(0.0, 1.0, 1, 1.0, 1, 1.0, 1)


def _bus_records() -> tuple[EventBus, list[LLMResponse], list[ErrorOccurred]]:
    bus = EventBus()
    responses: list[LLMResponse] = []
    errors: list[ErrorOccurred] = []

    async def response(event: LLMResponse) -> None:
        responses.append(event)

    async def error(event: ErrorOccurred) -> None:
        errors.append(event)

    bus.subscribe(LLMResponse, response)
    bus.subscribe(ErrorOccurred, error)
    return bus, responses, errors


def test_m2_wrk_003_prompt_is_canonical_opaque_and_turn_stateless() -> None:
    async def run() -> None:
        bus, responses, errors = _bus_records()
        llm = MockLLMEngineAdapter(
            (
                _response("speak", {"text": "ok"}, ["listen"]),
                _response("rest", {}, []),
            )
        )
        available = {"listen", "read", "speak"}
        reasoner = Reasoner(
            llm,
            PromptBuilder(),
            bus,
            available.__contains__,
            _validator(),
        )
        perceptions = (
            PerceptionResult("look", "ok", "seen"),
            PerceptionResult("listen", "timeout", None),
            PerceptionResult("read", "error", None),
        )
        await reasoner.reason("s", 1, 7, perceptions, ("opaque-2", "opaque-1"))
        await reasoner.reason(
            "s",
            2,
            8,
            (PerceptionResult("read", "ok", "new turn"),),
            (),
        )

        first = llm.inputs[0]
        second = llm.inputs[1]
        assert [item.kind for item in first.perceptions] == [
            "listen",
            "read",
            "look",
        ]
        assert [item.status for item in first.perceptions] == [
            "timeout",
            "error",
            "ok",
        ]
        assert first.pending_message_count == 2
        assert not hasattr(first, "pending_message_ids")
        assert [item.text for item in second.perceptions] == ["new turn"]
        assert all(item.text != "seen" for item in second.perceptions)
        assert responses[0].next_perceptions == ("listen",)
        assert responses[0].session_id == "s" and responses[0].correlation_id == 7
        assert responses[1].action_kind == "rest"
        assert responses[1].next_perceptions == ()
        assert errors == []

    asyncio.run(run())


def test_m2_wrk_003_clean_failures_fallback_without_raw_output(caplog) -> None:
    async def run() -> None:
        bus, responses, errors = _bus_records()
        llm = MockLLMEngineAdapter(
            (
                AdapterTimeout("timeout-raw-secret"),
                AdapterRejected("rejected-raw-secret"),
                LLMGeneration({"invalid": "bad-json-raw-secret"}, _metrics()),
            )
        )
        validator = _validator()
        reasoner = Reasoner(
            llm,
            PromptBuilder(),
            bus,
            {"listen", "speak"}.__contains__,
            validator,
        )
        for turn in range(1, 4):
            await reasoner.reason("s", turn, turn, (), ())

        assert [item.action_kind for item in responses] == [
            "speak",
            "speak",
            "speak",
        ]
        assert all(item.next_perceptions == ("listen",) for item in responses)
        assert all(set(item.action_payload) == {"text"} for item in responses)
        assert errors == []
        assert "raw-secret" not in caplog.text
        assert all("raw-secret" not in repr(item) for item in responses)

        rest_bus, rest_responses, rest_errors = _bus_records()
        rest_reasoner = Reasoner(
            MockLLMEngineAdapter((LLMGeneration({}, _metrics()),)),
            PromptBuilder(),
            rest_bus,
            set().__contains__,
            validator,
        )
        await rest_reasoner.reason("s", 4, 4, (), ())
        assert rest_responses == [LLMResponse("rest", {}, (), "s", 4, 4)]
        assert rest_errors == []

    asyncio.run(run())


def test_m2_wrk_003_cancel_and_unexpected_error_are_mutually_exclusive() -> None:
    async def run() -> None:
        bus, responses, errors = _bus_records()
        blocked = MockLLMEngineAdapter((_response("rest", {}, []),), blocked=True)
        reasoner = Reasoner(
            blocked,
            PromptBuilder(),
            bus,
            {"listen", "speak"}.__contains__,
            _validator(),
        )
        task = asyncio.create_task(reasoner.reason("s", 1, 1, (), ()))
        await blocked.entered.wait()
        await reasoner.abort()
        await task
        assert task.done() and not task.cancelled()
        assert responses == [] and errors == []

        failed = Reasoner(
            MockLLMEngineAdapter((RuntimeError("raw-secret"),)),
            PromptBuilder(),
            bus,
            {"listen", "speak"}.__contains__,
            _validator(),
        )
        with pytest.raises(RuntimeError, match="raw-secret"):
            await failed.reason("s", 2, 2, (), ())
        assert responses == []
        assert len(errors) == 1
        assert errors[0].exception_type == "RuntimeError"
        assert "raw-secret" not in errors[0].error

    asyncio.run(run())
