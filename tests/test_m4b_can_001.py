"""M4B cancellation and shared destruction proof."""
import asyncio
import pytest
from sbd.cognition.llm import LLMFatalError
from sbd.cognition.litert_lm.adapter import AdapterState
from tests.fakes.m4b_llm_child import adapter_fixture

@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["OPEN", "MEASURE", "GENERATE"], ids=["W05-open", "W05-measure", "W05-generate"])
async def test_cooperative_abort_waits_for_outer_completion(operation):
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    if operation != "OPEN":
        await adapter.open_conversation("s", 1)
    snapshot = None
    if operation == "GENERATE":
        snapshot = await adapter.measure("s", 1, "你好")
    child = children[0]
    child.release.clear()
    child.entered.clear()
    call = {"OPEN": lambda: adapter.open_conversation("s", 1),
            "MEASURE": lambda: adapter.measure("s", 1, "你好"),
            "GENERATE": lambda: adapter.generate(snapshot, "你好")}[operation]
    task = asyncio.create_task(call())
    await child.entered.wait()
    await asyncio.wait_for(adapter.abort(), 2)
    with pytest.raises(asyncio.CancelledError):
        await task
    assert child.runtime.cancels == 1
    assert adapter._operation_done.is_set()
    assert adapter._ledger.state == {"OPEN": "ENGINE_READY", "MEASURE": "CONVERSATION_READY", "GENERATE": "TAINTED"}[operation]
    if operation == "MEASURE":
        from sbd.cognition.llm_child_protocol import TICKET_SCRUB_TEXT
        assert child.runtime.scrubs == 1
        assert child.runtime.scratch == "rendered:" + TICKET_SCRUB_TEXT
        assert child.runtime.sends == child.runtime.kv == 0
        assert child.session.ledger.ticket is adapter._ledger.ticket is None
    await adapter.stop()


@pytest.mark.asyncio
async def test_cancelled_measure_scrub_failure_destroys_before_false_cleanup_is_usable():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    child = children[0]
    def fail_scrub():
        raise RuntimeError("private scrub failure")
    child.runtime.scrub_ticket = fail_scrub
    child.release.clear()
    child.entered.clear()
    measuring = asyncio.create_task(adapter.measure("s", 1, "私密"))
    await child.entered.wait()
    await asyncio.wait_for(adapter.abort(), 2)
    with pytest.raises(LLMFatalError):
        await measuring
    assert child.terminated == 1 and adapter.state is AdapterState.DESTROYED
    assert child.runtime.scratch is None and child.session.ledger.ticket is None
    assert child.runtime.sends == 0


@pytest.mark.asyncio
async def test_cancelled_measure_uses_native_wrapper_fixed_renderer_without_token_mutation():
    from types import SimpleNamespace
    from sbd.cognition.litert_lm.worker import LiteRTRuntime
    from sbd.cognition.llm_child_protocol import TICKET_SCRUB_TEXT
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    child = children[0]
    native = SimpleNamespace(token_count=0, last_rendered_message="私密")
    calls = []
    def render(text):
        calls.append(text)
        native.last_rendered_message = "native:" + text
        return native.last_rendered_message
    native.render_message_to_string = render
    runtime = LiteRTRuntime.__new__(LiteRTRuntime)
    runtime._conversation = native
    child.runtime.scrub_ticket = runtime.scrub_ticket
    child.release.clear()
    child.entered.clear()
    measuring = asyncio.create_task(adapter.measure("s", 1, "私密"))
    await child.entered.wait()
    await asyncio.wait_for(adapter.abort(), 2)
    with pytest.raises(asyncio.CancelledError):
        await measuring
    assert calls == [TICKET_SCRUB_TEXT]
    assert native.last_rendered_message == "native:" + TICKET_SCRUB_TEXT
    assert native.token_count == adapter.conversation_revision == child.runtime.sends == 0
    assert adapter._ledger.ticket is None and adapter._ledger.state == "CONVERSATION_READY"
    await adapter.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize("scrub_fails", [False, True])
async def test_real_process_cancelled_measure_scrubs_after_join_before_cleanup_proof(scrub_fails):
    from tests.fakes.m4b_llm_child import ProcessChild
    from sbd.cognition.llm_child_protocol import encode_frame, digest
    adapter, _, _, _ = adapter_fixture()
    options = ("--hold-measure",) + (("--discard-scrub-fails",) if scrub_fails else ())
    child = ProcessChild(adapter._cfg, adapter._lock, 1, options=options)
    await child.start()
    process = child._process
    try:
        common = {"protocol": 3, "session_id": "s", "generation": 1}
        await child.send({**common, "op": "OPEN", "request_id": 1})
        assert (await child.receive())["event"] == "OPENED"
        measure = {**common, "op": "MEASURE", "request_id": 2, "text": "私密",
                   "input_sha256": digest("私密"), "output_reserve_tokens": 128}
        cancel = {"protocol": 3, "op": "CANCEL", "request_id": 2}
        process.stdin.write(encode_frame(measure) + encode_frame(cancel))
        await process.stdin.drain()
        assert (await asyncio.wait_for(child.receive(), 2))["event"] == "CANCEL_DEFERRED"
        terminal = await asyncio.wait_for(child.receive(), 2)
        assert terminal["event"] == "CANCELLED" and terminal["operation"] == "MEASURE"
        assert terminal["operation_cleanup_proven"] is (not scrub_fails)
        assert terminal["engine_usable"] is (not scrub_fails)
        assert terminal["conversation_state"] == ("tainted" if scrub_fails else "ready")
        if not scrub_fails:
            await child.send({**common, "op": "CLOSE", "request_id": 3, "reason": "interrupt"})
            assert (await child.receive())["event"] == "CLOSED"
        else:
            assert await asyncio.wait_for(process.wait(), 2) == 2
    finally:
        await child.force_terminate()
    assert process.returncode is not None and child.termination_evidence.orphan_count == 0

@pytest.mark.asyncio
async def test_concurrent_fault_and_force_abort_share_cleanup_proof():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    child = children[0]
    entered, release = asyncio.Event(), asyncio.Event()
    original = child.force_terminate
    async def held_cleanup():
        entered.set()
        await release.wait()
        await original()
    child.force_terminate = held_cleanup
    await child.queue.put({"protocol": 3, "event": "unexpected", "request_id": 77})
    await entered.wait()
    forced = asyncio.create_task(adapter.force_abort())
    await asyncio.wait_for(asyncio.shield(entered.wait()), 1)
    assert not forced.done()
    release.set()
    report = await asyncio.wait_for(forced, 2)
    assert report.destroyed_backends == ("backend.cognition.reasoner.llm",)
    assert child.terminated == 1
    assert adapter.state is AdapterState.DESTROYED

@pytest.mark.asyncio
async def test_busyness_cannot_start_second_operation():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    child = children[0]
    child.release.clear()
    opening = asyncio.create_task(adapter.open_conversation("s", 1))
    await child.entered.wait()
    with pytest.raises(LLMFatalError, match="BUSY"):
        await adapter.open_conversation("other", 2)
    await adapter.abort()
    with pytest.raises(LLMFatalError):
        await opening
    assert child.terminated == 1
    await adapter.stop()


@pytest.mark.asyncio
async def test_rebuild_cancel_joins_old_cleanup_before_return_without_spawn():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    entered, release = asyncio.Event(), asyncio.Event()
    child = children[0]
    original = child.force_terminate
    async def cleanup():
        entered.set()
        await release.wait()
        await original()
    child.force_terminate = cleanup
    rebuilding = asyncio.create_task(adapter.rebuild())
    await entered.wait()
    rebuilding.cancel()
    assert not rebuilding.done() and len(children) == 1
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await rebuilding
    assert child.terminated == 1 and len(children) == 1


@pytest.mark.asyncio
async def test_rebuild_cancel_destroys_partial_new_child():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    entered, release = asyncio.Event(), asyncio.Event()
    original = adapter._child_factory
    def factory(*args):
        child = original(*args)
        start = child.start
        async def held():
            entered.set()
            await release.wait()
            return await start()
        child.start = held
        return child
    adapter._child_factory = factory
    rebuilding = asyncio.create_task(adapter.rebuild())
    await entered.wait()
    rebuilding.cancel()
    with pytest.raises(asyncio.CancelledError):
        await rebuilding
    assert len(children) == 2 and all(child.terminated == 1 for child in children)
