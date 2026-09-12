"""M4B generation: real adapter/worker logic, private one-use admission."""
import asyncio
from dataclasses import replace
import pytest
from sbd.cognition.llm import LLMFatalError, ReplaceableGenerationFailure
from sbd.cognition.litert_lm.adapter import AdapterState
from tests.fakes.m4b_llm_child import adapter_fixture

@pytest.mark.asyncio
async def test_generation_consumes_ticket_and_reuses_conversation():
    adapter, children, tickets, sampler = adapter_fixture()
    await adapter.start()
    await adapter.control.open_conversation("session", 1)
    child = children[0]
    history = child.runtime.history
    for index, text in enumerate(("你好", "再次")):
        snapshot = await adapter.measure("session", 1, text)
        assert snapshot.input_sha256 and snapshot.user_tokens == 2
        assert child.runtime.sends == index
        result = await adapter.generate(snapshot, text)
        assert result.text == "你好" and result.end is False
        assert adapter.conversation_revision == index + 1
        assert child.runtime.history is history
    assert child.runtime.history == ["你好", "再次"]
    assert sampler.calls == 3 and not tickets
    await adapter.control.close_conversation("session", 1, "session_end")
    assert child.runtime.history is None
    await adapter.stop()


@pytest.mark.asyncio
async def test_actual_adapter_callbacks_emit_private_free_runtime_and_lifecycle_observations():
    from sbd.cognition.observability import CognitionObserver
    from itertools import count
    rows = []
    observer = CognitionObserver(sink=rows.append, clock=count(100).__next__)
    adapter, children, _, sampler = adapter_fixture()
    adapter._observer = observer
    await adapter.start()
    await adapter.open_conversation("private-session", 1)
    observer.mark("asr_final")
    observer.begin_turn(1, 1, 2)
    snapshot = await adapter.measure("private-session", 1, "私密")
    before_generate = sampler.calls
    result = await adapter.generate(snapshot, "私密")
    assert sampler.calls == before_generate + 2  # one pre-admission, one post-terminal
    observer.outcome("GENERATE")
    observer.finish()
    await adapter.close_conversation("private-session", 1, "session_end")
    await adapter.stop()
    memory = [row["values"] for row in rows if row["dashboard"] == "memory"]
    assert [row["lifecycle_point"] for row in memory] == ["engine_ready",
        "conversation_preparation", "conversation_ready", "pre_generate", "post_generate",
        "post_session_close"]
    assert len([row for row in rows if row["dashboard"] == "prompt"]) == 1
    runtime = next(row["values"] for row in rows if row["dashboard"] == "runtime")
    assert runtime["decode_tokens"] == result.metrics.decode_tokens
    assert runtime["runtime_prefill_tokens"] == snapshot.runtime_prefill_tokens
    assert runtime["admission_result"] == "GENERATE"
    assert "私密" not in repr(rows) and "private-session" not in repr(rows)
    assert children[0].runtime.sends == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("proof", ["missing", "stable", "changed"])
async def test_native_timing_requires_stable_process_and_clock_namespace_proof(proof):
    from sbd.cognition.observability import CognitionObserver
    rows = []
    observer = CognitionObserver(sink=rows.append)
    adapter, children, _, _ = adapter_fixture()
    adapter._observer = observer
    await adapter.start()
    await adapter.open_conversation("s", 1)
    if proof != "missing":
        values = iter([(101, 77, 1, 2), (101, 77 if proof == "stable" else 78, 1, 2)])
        children[0].clock_mapping_token = lambda: next(values)
    observer.begin_turn(1, 1, 2)
    snapshot = await adapter.measure("s", 1, "你好")
    result = await adapter.generate(snapshot, "你好")
    observer.outcome("GENERATE")
    observer.finish()
    events = next(row["values"]["events"] for row in rows if row["dashboard"] == "timing")
    if proof == "stable":
        assert events["llm_send"]["monotonic_ns"] == result.metrics.llm_send_monotonic_ns
        assert events["llm_terminal"]["monotonic_ns"] == result.metrics.terminal_monotonic_ns
    else:
        assert events["llm_send"] == events["llm_terminal"] == {
            "monotonic_ns": None, "null_reason": "NOT_OBSERVED"}
    assert events["first_safe_text"] == {"monotonic_ns": None, "null_reason": "NOT_OBSERVED"}
    await adapter.stop()

@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("ticket", "0" * 32), ("session_id", "wrong"), ("generation", 2),
    ("input_sha256", "f" * 64), ("user_tokens", 3),
])
async def test_modified_snapshot_never_sends(field, value):
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("session", 1)
    snapshot = await adapter.measure("session", 1, "你好")
    with pytest.raises(LLMFatalError):
        await adapter.generate(replace(snapshot, **{field: value}), "你好")
    assert children[0].runtime.sends == 0
    await adapter.force_abort()

@pytest.mark.asyncio
async def test_clean_semantic_failure_is_tainted_replaceable():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("session", 1)
    children[0].runtime.output = '{"text":"","end":false}'
    snapshot = await adapter.measure("session", 1, "你好")
    with pytest.raises(ReplaceableGenerationFailure) as raised:
        await adapter.generate(snapshot, "你好")
    assert raised.value.code == "INVALID_SEMANTIC"
    assert adapter.state is AdapterState.TAINTED
    assert adapter.conversation_revision == 0
    await adapter.close_conversation("session", 1, "replacement")
    assert children[0].commands[-1]["reason"] == "replace_generation_failure"
    await adapter.open_conversation("session", 2)
    assert children[0].runtime.history == []
    await adapter.stop()

@pytest.mark.asyncio
async def test_shared_serialized_transaction_is_reentrant():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    async with adapter.serialized():
        await adapter.open_conversation("session", 1)
        snapshot = await adapter.measure("session", 1, "你好")
        await adapter.generate(snapshot, "你好")
    assert children[0].runtime.sends == 1
    await adapter.stop()


@pytest.mark.asyncio
async def test_each_capacity_session_requires_one_new_authorized_recovery():
    from sbd.cognition.llm import MemoryAdmissionDenied
    adapter, children, tickets, sampler = adapter_fixture()
    await adapter.start()
    for generation in (1, 2):
        await adapter.open_conversation("s", generation)
        snapshot = await adapter.measure("s", generation, "你好")
        sampler.available = 150
        with pytest.raises(MemoryAdmissionDenied) as raised:
            await adapter.generate(snapshot, "你好")
        assert raised.value.speak_allowed and len(tickets) == generation - 1
        proof = await adapter.close_conversation("s", generation, "session_rest")
        assert len(tickets) == generation - 1
        sampler.available = 1000
        await adapter.authorize_recovery("s", generation, proof)
        assert len(tickets) == generation and not adapter.recovery_pending
    assert len(children) == 3
    await adapter.stop()


@pytest.mark.asyncio
async def test_shutdown_joins_held_recovery_and_unblocks_waiter():
    from sbd.cognition.llm import MemoryAdmissionDenied
    adapter, children, _, sampler = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "你好")
    sampler.available = 150
    with pytest.raises(MemoryAdmissionDenied):
        await adapter.generate(snapshot, "你好")
    proof = await adapter.close_conversation("s", 1, "session_end")
    entered, release = asyncio.Event(), asyncio.Event()
    async def wait(ticket):
        entered.set()
        await release.wait()
    adapter._wait_recovery = wait
    waiter = asyncio.create_task(adapter.authorize_recovery("s", 1, proof))
    await entered.wait()
    await adapter.stop()
    with pytest.raises(LLMFatalError, match="planned recovery"):
        await waiter
    assert adapter.state is AdapterState.STOPPED and children[0].terminated == 1
