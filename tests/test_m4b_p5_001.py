"""M4B-P5-001 — recoverable fallback and fatal boundary."""

from __future__ import annotations

import asyncio

import pytest

from sbd.cognition.litert_lm.adapter import LLMFatalError
from sbd.cognition.llm import MockLLMEngineAdapter
from sbd.cognition.llm_child_protocol import ReasoningInputContractError
from sbd.adaptor.errors import AdapterTimeout
from sbd.cognition.prompt_builder import PromptBuilder
from sbd.cognition.reasoner import Reasoner
from tests.test_m2_wrk_003 import _bus_records, _response, _validator


def test_m4b_p5_001_fatal_adapter_error_is_not_translated_to_fallback() -> None:
    async def scenario() -> None:
        bus, responses, errors = _bus_records()
        reasoner = Reasoner(
            MockLLMEngineAdapter((LLMFatalError("private-fatal"),)), PromptBuilder(),
            bus, {"listen", "speak"}.__contains__, _validator(),
        )
        with pytest.raises(LLMFatalError):
            await reasoner.reason("s", 1, 1, (), ())
        assert responses == [] and len(errors) == 1
        assert errors[0].error == "reasoner failed"
    asyncio.run(scenario())


def test_m4b_p5_001_local_contract_error_publishes_error_without_llm_write() -> None:
    class InvalidBuilder:
        def build(self, **kwargs):
            raise ReasoningInputContractError(field="input", reason="invalid")

    async def scenario() -> None:
        bus, responses, errors = _bus_records()
        llm = MockLLMEngineAdapter((_response("rest", {}, []),))
        reasoner = Reasoner(llm, InvalidBuilder(), bus, set().__contains__, _validator())  # type: ignore[arg-type]
        with pytest.raises(ReasoningInputContractError):
            await reasoner.reason("s", 1, 1, (), ())
        assert llm.inputs == [] and responses == [] and len(errors) == 1
    asyncio.run(scenario())


def test_m4b_p5_001_outer_timeout_keeps_generation_alive_for_typed_abort() -> None:
    class DeadlineLLM:
        def __init__(self) -> None:
            self.release = asyncio.Event()
            self.done = asyncio.Event()
            self.cancelled = False
            self.abort_calls = 0

        async def start(self) -> None:
            return None

        async def stop(self) -> None:
            return None

        async def generate(self, value):
            try:
                await self.release.wait()
                raise AdapterTimeout("typed cancellation terminal")
            except asyncio.CancelledError:
                self.cancelled = True
                raise
            finally:
                self.done.set()

        async def abort(self) -> None:
            self.abort_calls += 1
            assert not self.cancelled
            self.release.set()
            await self.done.wait()

        async def force_abort(self):
            raise AssertionError("cooperative cancellation must not escalate")

    async def scenario() -> None:
        bus, responses, errors = _bus_records()
        llm = DeadlineLLM()
        reasoner = Reasoner(
            llm, PromptBuilder(), bus, {"listen", "speak"}.__contains__,
            _validator(), reason_timeout_seconds=0.01,
        )
        await reasoner.reason("s", 1, 1, (), ())
        assert llm.abort_calls == 1 and llm.cancelled is False
        assert llm.done.is_set() and errors == []
        assert len(responses) == 1
        assert responses[0].action_payload == {
            "text": "抱歉，我現在無法完成回應，請再試一次。",
        }

    asyncio.run(scenario())
