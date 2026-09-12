"""M4B-ADM-001: exact admission and approved snapshot-only ticket disposal."""
from dataclasses import replace
import pytest
from sbd.cognition.llm import LLMFatalError
from sbd.cognition.llm_child_protocol import validate_counts
from tests.fakes.m4b_llm_child import adapter_fixture

@pytest.mark.asyncio
async def test_A01_measure_is_non_mutating():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    runtime = children[0].runtime
    original = (runtime.history.copy(), runtime.kv, runtime.opens, runtime.closes, runtime.sends)
    snapshot = await adapter.measure("s", 1, "你好")
    assert snapshot.runtime_prefill_tokens == snapshot.rendered_incremental_tokens == 84
    assert original == (runtime.history, runtime.kv, runtime.opens, runtime.closes, runtime.sends)
    assert adapter.conversation_revision == 0
    assert "text" not in adapter._ledger.ticket
    await adapter.stop()

@pytest.mark.parametrize("key", ["user_tokens", "current_kv_tokens", "rendered_incremental_tokens",
                                  "runtime_prefill_tokens", "output_reserve_tokens", "engine_context_tokens"])
@pytest.mark.parametrize("value", [-1, True, 1.5, 2**64])
def test_A03_invalid_metric_is_never_coerced(key, value):
    row = dict(user_tokens=2, current_kv_tokens=0, rendered_incremental_tokens=84,
               runtime_prefill_tokens=84, output_reserve_tokens=128, engine_context_tokens=1024)
    row[key] = value
    with pytest.raises(LLMFatalError):
        validate_counts(row)

@pytest.mark.asyncio
async def test_A04_A05_consumed_ticket_permanently_rejected():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    old = await adapter.measure("s", 1, "你好")
    await adapter.generate(old, "你好")
    with pytest.raises(LLMFatalError):
        await adapter.generate(old, "你好")
    assert children[0].runtime.sends == 1
    await adapter.stop()

@pytest.mark.asyncio
async def test_A06_close_discards_unconsumed_ticket():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    old = await adapter.measure("s", 1, "你好")
    await adapter.close_conversation("s", 1, "replace_context")
    await adapter.open_conversation("s", 2)
    with pytest.raises(LLMFatalError):
        await adapter.generate(old, "你好")
    assert children[0].runtime.sends == 0
    assert children[0].runtime.history is None and children[0].terminated == 1
    await adapter.stop()

@pytest.mark.asyncio
async def test_A05_next_measure_requires_explicit_discard():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    await adapter.measure("s", 1, "你好")
    with pytest.raises(LLMFatalError):
        await adapter.measure("s", 1, "再次")
    assert children[0].runtime.sends == 0
    assert children[0].terminated == 1


def test_A01_native_wrapper_uses_exact_runtime_renderer_and_tokenizer():
    from types import SimpleNamespace
    from sbd.cognition.litert_lm.worker import LiteRTRuntime
    calls = []
    conversation = SimpleNamespace(token_count=90)
    def render(text):
        calls.append(("render", text))
        return "rendered-by-native"
    def tokenize(text):
        calls.append(("tokenize", text))
        return [10] * (32 if text == "你好" else 84)
    conversation.render_message_to_string = render
    runtime = LiteRTRuntime.__new__(LiteRTRuntime)
    runtime._conversation = conversation
    runtime._engine = SimpleNamespace(tokenize=tokenize)
    counts = runtime.measure("你好")
    assert calls == [("render", "你好"), ("tokenize", "你好"), ("tokenize", "rendered-by-native")]
    assert counts["user_tokens"] == 32 and counts["current_kv_tokens"] == 90
    assert counts["rendered_incremental_tokens"] == counts["runtime_prefill_tokens"] == 84
    assert conversation.token_count == 90


def test_A03_native_observed_prefill_cannot_be_replaced_by_prediction():
    from sbd.cognition.litert_lm.worker import WorkerSession
    from sbd.cognition.llm_child_protocol import digest
    from tests.fakes.m4b_llm_child import Runtime
    runtime = Runtime()
    session = WorkerSession(runtime)
    for frame in (
        {"protocol": 3, "op": "OPEN", "request_id": 1, "session_id": "s", "generation": 1},
        {"protocol": 3, "op": "MEASURE", "request_id": 2, "session_id": "s", "generation": 1,
         "text": "你好", "input_sha256": digest("你好"), "output_reserve_tokens": 128},
    ):
        session.ledger.command(frame)
        session.ledger.event(session.execute(frame)[0])
    ticket = session.ledger.ticket
    frame = {"protocol": 3, "op": "GENERATE", "request_id": 3, "session_id": "s", "generation": 1,
             "text": "你好", "input_sha256": digest("你好"), "conversation_revision": 0, "ticket": ticket["ticket"]}
    session.ledger.command(frame)
    runtime.prefill = 85
    with pytest.raises(LLMFatalError):
        session.execute(frame)
    assert session.ledger.revision == 0


@pytest.mark.asyncio
async def test_A07_A08_A09_A10_three_rejections_keep_claim_then_normal_turn():
    from sbd.cognition.llm import TicketDiscardProof
    from sbd.cognition.llm_child_protocol import TICKET_SCRUB_TEXT
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    runtime = children[0].runtime
    history = runtime.history
    old = []
    for index in range(3):
        runtime.user_tokens = 33
        snapshot = await adapter.measure("s", 1, "私密測試")
        old.append(snapshot.ticket)
        assert runtime.scratch == "rendered:私密測試"
        proof = await adapter.discard_ticket(snapshot)
        assert type(proof) is TicketDiscardProof
        assert (proof.session_id, proof.generation, proof.conversation_revision,
                proof.ticket, proof.input_sha256) == ("s", 1, 0, snapshot.ticket, snapshot.input_sha256)
        assert proof.native_render_scrubbed is proof.ticket_invalidated is proof.private_input_erased is True
        assert proof.conversation_state == "ready"
        assert runtime.scratch == "rendered:" + TICKET_SCRUB_TEXT
        assert runtime.scrubs == index + 1 and runtime.history is history and history == []
        assert runtime.sends == runtime.kv == adapter.conversation_revision == 0
        assert adapter._ledger.ticket is None and children[0].session.ledger.ticket is None
        discard = children[0].commands[-1]
        assert set(discard) == {"protocol", "op", "request_id", "session_id", "generation", "conversation_revision", "ticket", "input_sha256"}
        assert discard["op"] == "DISCARD_TICKET"
    assert len(set(old)) == 3
    runtime.user_tokens = 2
    snapshot = await adapter.measure("s", 1, "短句")
    await adapter.generate(snapshot, "短句")
    assert runtime.history is history and history == ["短句"]
    assert runtime.sends == adapter.conversation_revision == 1
    await adapter.stop()


@pytest.mark.asyncio
async def test_A05_discarded_ticket_rejected_after_new_measure():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    old = await adapter.measure("s", 1, "相同句")
    await adapter.discard_ticket(old)
    fresh = await adapter.measure("s", 1, "相同句")
    assert old.ticket != fresh.ticket
    with pytest.raises(LLMFatalError):
        await adapter.generate(old, "相同句")
    assert children[0].runtime.sends == 0 and children[0].terminated == 1


@pytest.mark.parametrize("fault", [None, "raise", "empty", "old_canary", "count", "count_bool"])
def test_A11_native_scrub_exact_call_and_failure_proof(fault):
    from types import SimpleNamespace
    from sbd.cognition.litert_lm.worker import LiteRTRuntime
    from sbd.cognition.llm_child_protocol import TICKET_SCRUB_TEXT
    calls = []
    conversation = SimpleNamespace(token_count=90, last_rendered_message="private-canary")
    def render(text):
        calls.append(text)
        if fault == "raise": raise RuntimeError("private-canary")
        if fault == "empty": return ""
        if fault == "old_canary": return conversation.last_rendered_message
        if fault == "count": conversation.token_count = 91
        if fault == "count_bool": conversation.token_count = True
        conversation.last_rendered_message = "native:" + text
        return conversation.last_rendered_message
    conversation.render_message_to_string = render
    runtime = LiteRTRuntime.__new__(LiteRTRuntime)
    runtime._conversation = conversation
    if fault is None:
        runtime.scrub_ticket()
        assert conversation.last_rendered_message == "native:" + TICKET_SCRUB_TEXT
        assert conversation.token_count == 90
    else:
        with pytest.raises(RuntimeError):
            runtime.scrub_ticket()
    assert calls == [TICKET_SCRUB_TEXT]


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("ticket", "f" * 32), ("session_id", "stale"),
    ("generation", 2), ("input_sha256", "f" * 64), ("runtime_prefill_tokens", 85)])
async def test_A12_bad_snapshot_discard_never_scrubs_or_sends(field, value):
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "私密測試")
    with pytest.raises(LLMFatalError):
        await adapter.discard_ticket(replace(snapshot, **{field: value}))
    assert children[0].runtime.scrubs == children[0].runtime.sends == 0
    assert children[0].terminated == 1 and children[0].runtime.scratch is None


@pytest.mark.asyncio
async def test_A12_duplicate_discard_is_fatal():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "私密測試")
    await adapter.discard_ticket(snapshot)
    with pytest.raises(LLMFatalError):
        await adapter.discard_ticket(snapshot)
    assert children[0].runtime.scrubs == 1 and children[0].runtime.sends == 0
    assert children[0].terminated == 1


@pytest.mark.asyncio
async def test_A05_child_reissuing_discarded_ticket_is_rejected_before_generate():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    old = await adapter.measure("s", 1, "相同句")
    await adapter.discard_ticket(old)
    children[0].transform = lambda frame: frame | {"ticket": old.ticket}
    with pytest.raises(LLMFatalError):
        await adapter.measure("s", 1, "相同句")
    assert children[0].runtime.sends == 0 and children[0].terminated == 1


@pytest.mark.asyncio
async def test_A05_native_ticket_collision_is_rejected_by_child_ledger(monkeypatch):
    from sbd.cognition.litert_lm import worker
    monkeypatch.setattr(worker.secrets, "token_hex", lambda size: "a" * 32)
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    old = await adapter.measure("s", 1, "相同句")
    await adapter.discard_ticket(old)
    with pytest.raises(LLMFatalError):
        await adapter.measure("s", 1, "相同句")
    assert children[0].runtime.sends == 0 and children[0].terminated == 1
    assert children[0].session.ledger.ticket is None


def test_A13_ticket_disposal_does_not_expand_public_state_fact_or_event_schema():
    from dataclasses import fields
    from typing import get_args
    from sbd.core import events
    assert get_args(events.State) == ("IDLE", "WAKE", "PERCEPTION", "THINK", "ACTION", "ERROR")
    assert {item.__name__ for item in get_args(events.WorkerFact)} == {
        "PerceptionResult", "LLMResponse", "ActionCompleted", "ErrorOccurred"}
    assert tuple(item.name for item in fields(events.LLMResponse)) == (
        "action_kind", "action_payload", "post_action_route", "next_perceptions",
        "session_id", "turn_id", "correlation_id")
    assert {item.__name__ for item in get_args(events.Event)} == {
        "PerceptionResult", "LLMResponse", "ActionCompleted", "ErrorOccurred",
        "StateChanged", "ButtonPressed", "ExternalMessageArrived", "WakeWordDetected",
        "InterruptRequested", "ShutdownRequested"}
