"""M4B outcome and admission integration, including acknowledged ticket disposal."""
import asyncio
import hashlib
from contextlib import asynccontextmanager
from dataclasses import replace
import pytest
from sbd.cognition.llm import (AdmissionSnapshot, GenerationMetrics, SemanticGeneration,
    LLMFatalError, MemoryAdmissionDenied, ReplaceableGenerationFailure)
from sbd.cognition.prompt_builder import ListenProjector
from sbd.cognition.reasoner import Reasoner
from sbd.core.events import PerceptionResult
from sbd.core.lifecycle import ForceAbortReport
from tests.test_m2_wrk_003 import _bus_records, _validator


class ProductLLM:
    """Separate admission/native-send/mutation ledgers and task ownership proof."""
    def __init__(self, *, result=None, counts=None, revision=0, blocked=False):
        self.control = object()
        self.result = result or SemanticGeneration("好",False,("好",),
            GenerationMetrics(1,0,80,80,1,81,1,2,3))
        self.counts = counts or {}
        self.conversation_revision = revision
        self.measures = []
        self.native_sends = []
        self.checks = []
        self.owner = None
        self.task_ledger = []
        self.generate_entered = asyncio.Event()
        self.release = asyncio.Event()
        self.aborted = False
        self.closes = []
        self.discard_calls = 0
        self.discard_entered = asyncio.Event()
        self.discard_release = asyncio.Event()
        self.discard_release.set()
        self.discard_failure = None
        if not blocked:
            self.release.set()

    @asynccontextmanager
    async def serialized(self):
        assert self.owner is None
        self.owner = asyncio.current_task()
        try:
            yield
        finally:
            self.owner = None

    def assert_conversation(self,sid,generation):
        assert self.owner is asyncio.current_task()
        self.task_ledger.append(asyncio.current_task())
        self.checks.append((sid,generation))
        if (sid,generation) != ("session",1):
            raise LLMFatalError("private wrong identity")

    async def measure(self,sid,generation,text):
        assert self.owner is asyncio.current_task()
        self.task_ledger.append(asyncio.current_task())
        self.measures.append(text)
        return AdmissionSnapshot("a"*32,sid,generation,hashlib.sha256(text.encode()).hexdigest(),
            **{"user_tokens":1,"current_kv_tokens":0,"rendered_incremental_tokens":80,
               "runtime_prefill_tokens":80,"output_reserve_tokens":128,"engine_context_tokens":1024,
               **self.counts})

    async def generate(self,snapshot,text):
        assert self.owner is asyncio.current_task()
        self.task_ledger.append(asyncio.current_task())
        self.generate_entered.set()
        await self.release.wait()
        if self.aborted:
            raise asyncio.CancelledError()
        if isinstance(self.result,MemoryAdmissionDenied):
            raise self.result
        self.native_sends.append(text)
        if isinstance(self.result,Exception):
            raise self.result
        self.conversation_revision += 1
        return self.result

    async def discard_ticket(self,snapshot):
        from sbd.cognition.llm import TicketDiscardProof
        assert self.owner is asyncio.current_task()
        self.discard_calls += 1
        self.measures.clear()
        self.discard_entered.set()
        await self.discard_release.wait()
        if self.discard_failure is not None:
            raise self.discard_failure
        return TicketDiscardProof(snapshot.session_id,snapshot.generation,
            self.conversation_revision,snapshot.ticket,snapshot.input_sha256,
            True,True,True,"ready")

    async def abort(self):
        self.aborted = True
        self.release.set()
        if self.discard_entered.is_set():
            await self.discard_release.wait()

    async def force_abort(self):
        await self.abort()
        return ForceAbortReport()

    async def start(self): pass
    async def stop(self): pass


def fact(text="你好",status="ok",**overrides):
    return replace(PerceptionResult("listen",status,text,session_id="session",turn_id=1),**overrides)


async def run(llm, perceptions=None, *, capabilities=None, validator=None, pending=()):
    bus,responses,errors = _bus_records()
    reasoner = Reasoner(llm,ListenProjector(),bus,
        (capabilities if capabilities is not None else {"listen","speak"}).__contains__,
        validator or _validator())
    await reasoner.reason("session",1,9,(fact(),) if perceptions is None else perceptions,pending,conversation_generation=1)
    return reasoner,responses,errors


@pytest.mark.parametrize("perception,expected",[
    (fact("","ok"),"我沒聽清楚，請再說一次。"),
    (fact(" \t\n","ok"),"我沒聽清楚，請再說一次。"),
    (fact(object(),"timeout"),"我沒聽清楚，請再說一次。"),
    (fact(object(),"error"),"我沒聽清楚，請再說一次。"),
    (fact("字"*21),"這句有點長，請縮短後再說一次。"),
],ids=["O01-N05-empty","O01-N05-whitespace","O01-N05-timeout","O01-N05-error","O01-N06-codepoints"])
def test_r1_has_no_measure_or_mutation(perception,expected):
    async def scenario():
        llm=ProductLLM()
        _,responses,errors=await run(llm,(perception,))
        assert errors == [] and len(responses) == 1
        response=responses[0]
        assert (response.action_kind,response.action_payload,response.post_action_route,response.next_perceptions) == ("speak",{"text":expected},"KEEP_NEXT",("listen",))
        assert (response.session_id,response.turn_id,response.correlation_id) == ("session",1,9)
        assert llm.measures == llm.native_sends == []
        assert llm.conversation_revision == 0
    asyncio.run(scenario())


@pytest.mark.parametrize("total,route,send",[(1024,"KEEP_NEXT",True),(1025,"REPLACE_NEXT",False)],ids=["A02-inclusive","O02-A02-overflow"])
def test_context_equation(total,route,send):
    async def scenario():
        llm=ProductLLM(revision=1,counts={"current_kv_tokens":total-228,"rendered_incremental_tokens":100,"runtime_prefill_tokens":100})
        _,responses,errors=await run(llm)
        assert errors == [] and len(responses) == 1
        assert responses[0].post_action_route == route
        assert bool(llm.native_sends) is send
        assert llm.conversation_revision == (2 if send else 1)
        if not send:
            assert responses[0].action_payload == {"text":"對話內容已滿，請再說一次。"}
            assert llm.closes == []
    asyncio.run(scenario())


@pytest.mark.parametrize("allow,text,kind",[(True,"系統需要整理，請稍後再試。","speak"),(False,"","rest")],ids=["O03","O04"])
def test_memory_denial_has_no_generation(allow,text,kind):
    async def scenario():
        llm=ProductLLM(result=MemoryAdmissionDenied(speak_allowed=allow))
        _,responses,errors=await run(llm)
        assert errors == [] and len(responses) == 1
        response=responses[0]
        assert (response.action_kind,response.post_action_route,response.next_perceptions) == (kind,"END_SESSION",())
        assert response.action_payload == ({"text":text} if text else {})
        assert llm.native_sends == [] and llm.conversation_revision == 0
    asyncio.run(scenario())


@pytest.mark.parametrize("text,end,kind,route",[("嗨🙂！",False,"speak","KEEP_NEXT"),("再見",True,"speak","END_SESSION"),("",True,"rest","END_SESSION")],ids=["O05","O06","O07"])
def test_model_owns_semantics_only(text,end,kind,route):
    async def scenario():
        base=ProductLLM()
        base.result=replace(base.result,text=text,end=end,safe_fragments=())
        reasoner,responses,errors=await run(base)
        assert errors == [] and len(responses)==1
        response=responses[0]
        assert response.action_kind == kind and response.post_action_route == route
        assert response.action_payload == ({"text":text.replace("！","!")} if text else {})
        assert len(base.native_sends)==1 and base.conversation_revision==1
        assert reasoner.control is base.control
        assert len(set(base.task_ledger))==1
    asyncio.run(scenario())


@pytest.mark.parametrize("code",["INVALID_SEMANTIC","GENERATION_REJECTED","GENERATION_TIMEOUT"],ids=lambda x:"O08-"+x)
def test_proven_replaceable_failure(code):
    async def scenario():
        llm=ProductLLM(result=ReplaceableGenerationFailure(code))
        _,responses,errors=await run(llm)
        assert errors == [] and len(responses)==1
        assert responses[0].action_payload == {"text":"剛才沒有成功，請再說一次。"}
        assert responses[0].post_action_route == "REPLACE_NEXT"
        assert len(llm.native_sends)==1 and llm.conversation_revision==0 and llm.closes==[]
    asyncio.run(scenario())


def test_repeated_r2_does_not_escalate_O09():
    async def scenario():
        llm=ProductLLM(result=ReplaceableGenerationFailure("GENERATION_REJECTED"))
        bus,responses,errors=_bus_records()
        reasoner=Reasoner(llm,ListenProjector(),bus,{"listen","speak"}.__contains__,_validator())
        for turn in range(1,4):
            await reasoner.reason("session",turn,turn,(fact(turn_id=turn),),(),conversation_generation=1)
        assert errors==[] and len(responses)==3
        assert all(r.post_action_route=="REPLACE_NEXT" for r in responses)
        assert len(llm.native_sends)==3
    asyncio.run(scenario())


def test_33_tokens_acknowledged_before_r1_N07_O01():
    async def scenario():
        llm=ProductLLM(counts={"user_tokens":33})
        bus,responses,errors=_bus_records()
        reasoner=Reasoner(llm,ListenProjector(),bus,{"listen","speak"}.__contains__,_validator())
        await reasoner.reason("session",1,1,(fact(),),(),conversation_generation=1)
        assert llm.discard_calls==1 and llm.native_sends==[] and llm.conversation_revision==0
        assert len(responses)==1 and errors==[] and llm.closes==[]
        assert responses[0].action_payload=={"text":"這句有點長，請縮短後再說一次。"}
        assert responses[0].post_action_route=="KEEP_NEXT" and responses[0].next_perceptions==("listen",)
    asyncio.run(scenario())


@pytest.mark.parametrize("text,normalized",[("　Ａ\t\nＢ\u00a0🙂  ","A B 🙂"),("\t你\r\n好\t","你 好"),("🙂 "+"字"*18,"🙂 "+"字"*18)],ids=["N01-integrated","N02-integrated","N06-20-codepoints-32-tokens"])
def test_exact_normalized_content_is_only_model_input(text,normalized):
    async def scenario():
        llm=ProductLLM(counts={"user_tokens":32})
        _,responses,errors=await run(llm,(fact(text,extra={"PRIVATE":"never serialize"}),))
        assert errors==[] and len(responses)==1
        assert llm.measures==llm.native_sends==[normalized]
        assert llm.conversation_revision==1
    asyncio.run(scenario())


@pytest.mark.parametrize("perceptions,pending",[
    ((fact("\x00"),),()), ((fact("\ud800"),),()), ((fact(None),),()),
    ((),()), ((fact(),fact()),()), ((fact(kind="read"),),()),
    ((fact(session_id="wrong"),),()), ((fact(turn_id=2),),()),
    ((fact(status="unknown"),),()), ((fact(),),("private-pending",)),
],ids=["N03-nul","N03-surrogate","N04-nonstr","N08-zero","N08-multiple","N08-read","N08-session","N08-turn","N08-status","N08-pending"])
def test_unsupported_projection_has_no_measure_mutation_or_retry(perceptions,pending):
    async def scenario():
        llm=ProductLLM()
        bus,responses,errors=_bus_records()
        reasoner=Reasoner(llm,ListenProjector(),bus,{"listen","speak"}.__contains__,_validator())
        with pytest.raises(LLMFatalError,match="UNSUPPORTED_INPUT"):
            await reasoner.reason("session",1,1,perceptions,pending,conversation_generation=1)
        assert llm.measures==llm.native_sends==[] and llm.conversation_revision==0
        assert responses==[] and len(errors)==1
    asyncio.run(scenario())


def test_fresh_prefill_does_not_override_context_F04():
    async def scenario():
        llm=ProductLLM(counts={"current_kv_tokens":769,"rendered_incremental_tokens":128,"runtime_prefill_tokens":128})
        _,responses,errors=await run(llm)
        assert len(responses)==1 and errors==[]
        assert responses[0].post_action_route=="REPLACE_NEXT"
        assert llm.native_sends==[] and llm.conversation_revision==0
    asyncio.run(scenario())


def test_three_acknowledged_rejects_then_next_turn_generates_A10_N07():
    from tests.fakes.m4b_llm_child import adapter_fixture
    async def scenario():
        adapter,children,_,_=adapter_fixture()
        await adapter.start()
        await adapter.open_conversation("session",1)
        runtime=children[0].runtime
        runtime.user_tokens=33
        conversation=runtime.history
        bus,responses,errors=_bus_records()
        reasoner=Reasoner(adapter,ListenProjector(),bus,{"listen","speak"}.__contains__,_validator())
        for turn in range(1,4):
            await reasoner.reason("session",turn,turn,(fact("這句被拒絕",turn_id=turn),),(),conversation_generation=1)
            assert len(responses)==turn and responses[-1].post_action_route=="KEEP_NEXT"
            assert runtime.history is conversation and conversation==[]
            assert adapter.conversation_revision==0 and runtime.sends==0 and runtime.closes==0
            assert adapter._ledger.ticket is None
        discards=[c for c in children[0].commands if c["op"]=="DISCARD_TICKET"]
        assert len(discards)==3 and len({c["ticket"] for c in discards})==3
        runtime.user_tokens=2
        await reasoner.reason("session",4,4,(fact("短句",turn_id=4),),(),conversation_generation=1)
        assert errors==[] and len(responses)==4
        assert runtime.sends==1 and runtime.history==["短句"] and runtime.opens==1
        await adapter.stop()
    asyncio.run(scenario())


@pytest.mark.parametrize("mode",["release","false-proof","interrupt"],ids=["O12-ack-barrier","O12-failure","O12-W12-interrupt"])
def test_actual_discard_barrier_prevents_early_r1(mode):
    from tests.fakes.m4b_llm_child import adapter_fixture
    async def scenario():
        adapter,children,_,_=adapter_fixture()
        await adapter.start(); await adapter.open_conversation("session",1)
        child=children[0]
        child.runtime.user_tokens=33
        discard_entered=asyncio.Event()
        original=child.send
        async def held_send(frame):
            if frame["op"]=="DISCARD_TICKET":
                child.release.clear()
                discard_entered.set()
            await original(frame)
        child.send=held_send
        if mode=="false-proof":
            child.transform=lambda event: {**event,"private_input_erased":False} if event["event"]=="TICKET_DISCARDED" else event
        bus,responses,errors=_bus_records()
        reasoner=Reasoner(adapter,ListenProjector(),bus,{"listen","speak"}.__contains__,_validator())
        task=asyncio.create_task(reasoner.reason("session",1,1,(fact("拒絕輸入"),),(),conversation_generation=1))
        await asyncio.wait_for(discard_entered.wait(),1)
        assert adapter._ledger.state=="DISCARDING"
        assert responses==errors==[] and child.runtime.sends==0
        transaction=reasoner._active.operation_task.get_coro()
        assert "text" not in transaction.cr_frame.f_locals
        assert "perceptions" not in transaction.cr_frame.f_locals
        assert "perception_results" not in task.get_coro().cr_frame.f_locals
        if mode=="interrupt":
            # Start abort to its cooperative wait, then release the atomic ACK.
            aborting=asyncio.create_task(reasoner.abort())
            await asyncio.wait_for(reasoner._active.cancel_requested.wait(),1)
            assert responses==[] and not aborting.done()
        child.release.set()
        if mode=="false-proof":
            with pytest.raises(LLMFatalError): await asyncio.wait_for(task,2)
            assert responses==[] and len(errors)==1 and child.terminated==1
        else:
            await asyncio.wait_for(task,2)
            if mode=="interrupt":
                await asyncio.wait_for(aborting,2)
                assert responses==errors==[]
                assert not any(c["op"]=="CANCEL" for c in child.commands)
            else:
                assert len(responses)==1 and errors==[]
                assert responses[0].action_payload=={"text":"這句有點長，請縮短後再說一次。"}
                assert adapter._ledger.ticket is None and adapter.conversation_revision==0
        await adapter.stop()
    asyncio.run(scenario())


@pytest.mark.parametrize("field,value",[("session_id","wrong"),("generation",2),("conversation_revision",1),("ticket","b"*32),("input_sha256","0"*64),("native_render_scrubbed",False),("ticket_invalidated",False),("private_input_erased",False),("conversation_state","tainted")],ids=lambda x:"O12-proof-"+str(x))
def test_reasoner_checks_typed_discard_proof(field,value):
    async def scenario():
        llm=ProductLLM(counts={"user_tokens":33})
        original=llm.discard_ticket
        async def bad_proof(snapshot):
            return replace(await original(snapshot),**{field:value})
        llm.discard_ticket=bad_proof
        bus,responses,errors=_bus_records()
        reasoner=Reasoner(llm,ListenProjector(),bus,{"listen","speak"}.__contains__,_validator())
        with pytest.raises(LLMFatalError):
            await reasoner.reason("session",1,1,(fact(),),(),conversation_generation=1)
        assert responses==[] and len(errors)==1 and llm.native_sends==[]
    asyncio.run(scenario())
