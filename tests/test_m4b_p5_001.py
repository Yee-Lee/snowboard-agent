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
from sbd.cognition.prompt_builder import ListenProjector
from sbd.cognition.llm import ReplaceableGenerationFailure
from tests.test_m4b_outcome_001 import ProductLLM, fact


def test_m4b_p5_001_fatal_adapter_error_is_not_translated_to_fallback() -> None:
    async def scenario() -> None:
        bus, responses, errors = _bus_records()
        reasoner = Reasoner(
            MockLLMEngineAdapter((LLMFatalError("private-fatal"),)), PromptBuilder(),
            bus, {"listen", "speak"}.__contains__, _validator(),
        )
        with pytest.raises(LLMFatalError):
            await reasoner.reason("s", 1, 1, (), (), conversation_generation=1)
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
            await reasoner.reason("s", 1, 1, (), (), conversation_generation=1)
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
        await reasoner.reason("s", 1, 1, (), (), conversation_generation=1)
        assert llm.abort_calls == 1 and llm.cancelled is False
        assert llm.done.is_set() and errors == []
        assert len(responses) == 1
        assert responses[0].action_payload == {
            "text": "抱歉，我現在無法完成回應，請再試一次。",
        }

    asyncio.run(scenario())


@pytest.mark.parametrize("problem",["untyped","fatal","proof","prefix","semantic","capability","unsupported","generation"],ids=lambda x:"O11-"+x)
def test_product_fatal_boundary_has_no_normal_fact_and_sanitized_traceback(problem):
    import traceback
    from dataclasses import replace
    async def scenario():
        llm=ProductLLM()
        capabilities={"listen","speak"}
        perceptions=(fact(),)
        generation=1
        if problem=="untyped": llm.result=ValueError("PRIVATE-OUTPUT-CANARY")
        elif problem=="fatal": llm.result=LLMFatalError("PRIVATE-OUTPUT-CANARY")
        elif problem=="proof":
            llm.result=ReplaceableGenerationFailure("INVALID_SEMANTIC")
            llm.result.request_terminal_proven=False
        elif problem=="prefix": llm.result=replace(llm.result,safe_fragments=("PRIVATE-OUTPUT-CANARY",))
        elif problem=="semantic": llm.result=replace(llm.result,text="",end=False,safe_fragments=())
        elif problem=="capability": capabilities={"listen"}
        elif problem=="unsupported": perceptions=(fact(kind="look"),)
        elif problem=="generation": generation=2
        bus,responses,errors=_bus_records()
        reasoner=Reasoner(llm,ListenProjector(),bus,capabilities.__contains__,_validator())
        try:
            await reasoner.reason("session",1,1,perceptions,(),conversation_generation=generation)
        except LLMFatalError as error:
            assert "PRIVATE-OUTPUT-CANARY" not in "".join(traceback.format_exception(error))
            assert error.__cause__ is None
        else:
            pytest.fail("unsafe result accepted")
        assert responses==[] and len(errors)==1
        if problem in {"capability","unsupported","generation"}:
            assert llm.measures==llm.native_sends==[]
    asyncio.run(scenario())


def test_cancelled_product_has_no_normal_fact_O10():
    async def scenario():
        llm=ProductLLM(blocked=True)
        bus,responses,errors=_bus_records()
        reasoner=Reasoner(llm,ListenProjector(),bus,{"listen","speak"}.__contains__,_validator())
        task=asyncio.create_task(reasoner.reason("session",1,1,(fact(),),(),conversation_generation=1))
        await asyncio.wait_for(llm.generate_entered.wait(),1)
        await asyncio.wait_for(reasoner.abort(),1)
        await asyncio.wait_for(task,1)
        assert responses==errors==[] and llm.aborted and llm.owner is None
    asyncio.run(scenario())


def test_fragments_never_dispatch_before_terminal_X05():
    async def scenario():
        llm=ProductLLM(blocked=True)
        bus,responses,errors=_bus_records()
        reasoner=Reasoner(llm,ListenProjector(),bus,{"listen","speak"}.__contains__,_validator())
        task=asyncio.create_task(reasoner.reason("session",1,1,(fact(),),(),conversation_generation=1))
        await asyncio.wait_for(llm.generate_entered.wait(),1)
        assert llm.result.safe_fragments==("好",)
        assert responses==errors==[]
        llm.release.set()
        await asyncio.wait_for(task,1)
        assert len(responses)==1 and responses[0].action_payload=={"text":"好"}
    asyncio.run(scenario())


@pytest.mark.parametrize("prefill,revision,valid",[(128,0,True),(129,0,False),(129,1,True)],ids=["F01","F02","F03"])
def test_fresh_prefill_is_profile_tier(prefill,revision,valid):
    async def scenario():
        llm=ProductLLM(revision=revision,counts={"rendered_incremental_tokens":prefill,"runtime_prefill_tokens":prefill})
        bus,responses,errors=_bus_records()
        reasoner=Reasoner(llm,ListenProjector(),bus,{"listen","speak"}.__contains__,_validator())
        if valid:
            await reasoner.reason("session",1,1,(fact(),),(),conversation_generation=1)
            assert len(responses)==1 and errors==[] and len(llm.native_sends)==1
        else:
            with pytest.raises(LLMFatalError):
                await reasoner.reason("session",1,1,(fact(),),(),conversation_generation=1)
            assert responses==[] and len(errors)==1 and llm.native_sends==[]
    asyncio.run(scenario())


@pytest.mark.parametrize("field,value",[("user_tokens",True),("current_kv_tokens",-1),("rendered_incremental_tokens",1.0),("runtime_prefill_tokens",79),("output_reserve_tokens",127),("engine_context_tokens",1025)],ids=lambda x:"A03-"+str(x))
def test_invalid_admission_counts_are_fatal(field,value):
    async def scenario():
        llm=ProductLLM(counts={field:value})
        bus,responses,errors=_bus_records()
        reasoner=Reasoner(llm,ListenProjector(),bus,{"listen","speak"}.__contains__,_validator())
        with pytest.raises(LLMFatalError):
            await reasoner.reason("session",1,1,(fact(),),(),conversation_generation=1)
        assert responses==[] and len(errors)==1 and llm.native_sends==[]
    asyncio.run(scenario())
