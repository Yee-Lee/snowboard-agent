"""M4B-WIRE-001 real-process and parent ledger failures; PS requires Linux separately."""
import asyncio
from dataclasses import replace
from itertools import product
import pytest
from sbd.cognition.llm import LLMFatalError
from sbd.cognition.llm_child_protocol import CLOSE_REASONS, ProtocolLedger, digest
from sbd.cognition.litert_lm.adapter import AdapterState
from tests.fakes.m4b_llm_child import adapter_fixture, ProcessChild


@pytest.mark.asyncio
async def test_W03_real_process_continuity_and_shutdown():
    adapter, _, _, _ = adapter_fixture()
    adapter._child_factory = ProcessChild
    await adapter.start()
    child = adapter._child
    process = child._process
    assert child.pid == child.pgid == process.pid
    await adapter.open_conversation("s", 1)
    for text in ("第一", "第二"):
        snapshot = await adapter.measure("s", 1, text)
        result = await adapter.generate(snapshot, text)
        assert result.text == "你好"
    assert adapter.conversation_revision == 2
    await adapter.close_conversation("s", 1, "session_end")
    await adapter.stop()
    assert process.returncode == 0
    assert not child._live_process_group_members(child.pgid)


@pytest.mark.asyncio
async def test_W09_term_kill_descendant_and_next_attested_child():
    adapter, _, _, _ = adapter_fixture()
    adapter._cfg = replace(adapter._cfg, child_terminate_timeout_seconds=0.1,
                           child_kill_wait_timeout_seconds=2)
    adapter._child_factory = lambda *args: ProcessChild(*args, options=("--ignore-term", "--descendant"))
    await adapter.start()
    child = adapter._child
    await adapter.force_abort()
    evidence = child.termination_evidence
    assert evidence.term_sent and evidence.kill_sent and evidence.orphan_count == 0
    assert not child._live_process_group_members(child.pgid)
    adapter._child_factory = ProcessChild
    await adapter.rebuild()
    assert adapter._child.pid != child.pid
    await adapter.open_conversation("s", 2)
    snapshot = await adapter.measure("s", 2, "你好")
    assert (await adapter.generate(snapshot, "你好")).text == "你好"
    await adapter.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", sorted(CLOSE_REASONS))
@pytest.mark.parametrize("proofs", list(product((False, True), repeat=3)))
async def test_W06_close_reason_and_all_proof_combinations(reason, proofs):
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    await adapter.measure("s", 1, "你好")
    names = ("request_terminal_proven", "cleanup_proven", "engine_usable")
    children[0].transform = lambda frame: frame | dict(zip(names, proofs))
    if all(proofs):
        proof = await adapter.close_conversation("s", 1, reason)
        assert all(getattr(proof, name) for name in names)
        assert adapter._ledger.ticket is None and adapter._ledger.claim is None
        await adapter.stop()
    else:
        with pytest.raises(LLMFatalError):
            await adapter.close_conversation("s", 1, reason)
        assert children[0].terminated == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("request_id", 77), ("generation", 2), ("conversation_revision", 0),
    ("user_tokens", 99), ("decode_tokens", True), ("decode_tokens", 129),
    ("conversation_kv_tokens", 1025), ("first_safe_text_monotonic_ns", 1),
    ("llm_send_monotonic_ns", 2**63), ("text", ""), ("end", 1),
])
async def test_W08_invalid_result_proves_destroy_before_failure(field, value):
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "你好")
    children[0].transform = lambda frame: frame | {field: value}
    with pytest.raises(LLMFatalError):
        await adapter.generate(snapshot, "你好")
    assert children[0].terminated == 1 and adapter.state is AdapterState.DESTROYED


@pytest.mark.asyncio
async def test_W08_duplicate_terminal_blocks_admission_without_next_request():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "你好")
    await adapter.generate(snapshot, "你好")
    child = children[0]
    cleanup = asyncio.Event()
    original = child.force_terminate
    async def terminate():
        await original()
        cleanup.set()
    child.force_terminate = terminate
    await child.queue.put({"protocol": 3, "event": "RESULT", "request_id": 3})
    await asyncio.wait_for(cleanup.wait(), 2)
    assert adapter.state is AdapterState.DESTROYED and child.terminated == 1


def test_W07_shutdown_is_engine_ready_only():
    ledger = ProtocolLedger()
    ledger.command({"protocol": 3, "op": "SHUTDOWN"})
    ledger.event({"protocol": 3, "event": "SHUTDOWN_ACK"})
    assert ledger.state == "STOPPED"
    ledger = ProtocolLedger()
    ledger.command({"protocol": 3, "op": "OPEN", "request_id": 1, "session_id": "s", "generation": 1})
    with pytest.raises(LLMFatalError):
        ledger.command({"protocol": 3, "op": "SHUTDOWN"})


@pytest.mark.asyncio
@pytest.mark.parametrize("code", ["INVALID_SEMANTIC", "GENERATION_REJECTED", "GENERATION_TIMEOUT", "UNKNOWN"])
@pytest.mark.parametrize("terminal,usable", list(product((False, True), repeat=2)))
async def test_W04_failed_terminal_code_and_proof_matrix(code, terminal, usable):
    from sbd.cognition.llm import ReplaceableGenerationFailure
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "你好")
    def transform(frame):
        return {key: frame[key] for key in ("protocol", "request_id", "session_id", "generation")} | {
            "event": "REQUEST_FAILED", "code": code, "request_terminal_proven": terminal,
            "engine_usable": usable, "terminal_monotonic_ns": 1}
    children[0].transform = transform
    if terminal and usable and code != "UNKNOWN":
        with pytest.raises(ReplaceableGenerationFailure) as raised:
            await adapter.generate(snapshot, "你好")
        assert raised.value.code == code and adapter.state is AdapterState.TAINTED
        children[0].transform = lambda frame: frame
        await adapter.stop()
    else:
        with pytest.raises(LLMFatalError):
            await adapter.generate(snapshot, "你好")
        assert children[0].terminated == 1


def test_W05_cancel_once_matching_identity_and_deferred_proof():
    ledger = ProtocolLedger()
    ledger.command({"protocol": 3, "op": "OPEN", "request_id": 1, "session_id": "s", "generation": 1})
    with pytest.raises(LLMFatalError):
        ledger.command({"protocol": 3, "op": "CANCEL", "request_id": 2})
    cancel = {"protocol": 3, "op": "CANCEL", "request_id": 1}
    ledger.command(cancel)
    with pytest.raises(LLMFatalError):
        ledger.command(cancel)
    deferred = {"protocol": 3, "event": "CANCEL_DEFERRED", "request_id": 1}
    assert ledger.event(deferred) is False
    assert ledger.state == "OPENING"
    with pytest.raises(LLMFatalError):
        ledger.event(deferred)
    ledger.event({"protocol": 3, "event": "CANCELLED", "request_id": 1,
        "operation": "OPEN", "request_terminal_proven": True,
        "operation_cleanup_proven": True, "engine_usable": True, "conversation_state": "none"})
    assert ledger.state == "ENGINE_READY"


@pytest.mark.asyncio
async def test_W05_cancelled_close_incomplete_proof_destroys_owner():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    child = children[0]
    child.release.clear()
    child.entered.clear()
    closing = asyncio.create_task(adapter.close_conversation("s", 1, "session_end"))
    await child.entered.wait()
    # Native close result held: the explicit cancel terminal has false cleanup.
    aborting = asyncio.create_task(adapter.abort())
    with pytest.raises(LLMFatalError):
        await closing
    await aborting
    assert child.terminated == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("raises", [False, True], ids=["joined-result", "known-native-cancel"])
async def test_W05_coalesced_generate_cancel_reaches_blocked_native_thread(raises):
    from sbd.core.config.models import LLMConfig
    from sbd.cognition.llm_child_protocol import encode_frame
    from tests.fakes.m4b_llm_child import product_lock
    options = ("--hold-generate", "--cancel-raises") if raises else ("--hold-generate",)
    child = ProcessChild(LLMConfig(), product_lock(), 1, options=options)
    await child.start()
    common = {"protocol": 3, "session_id": "s", "generation": 1}
    try:
        await child.send({**common, "op": "OPEN", "request_id": 1})
        assert (await child.receive())["event"] == "OPENED"
        await child.send({**common, "op": "MEASURE", "request_id": 2,
                          "text": "你好", "input_sha256": digest("你好"), "output_reserve_tokens": 128})
        measured = await child.receive()
        frame = {**common, "op": "GENERATE", "request_id": 3, "text": "你好",
                 "input_sha256": digest("你好"), "conversation_revision": 0, "ticket": measured["ticket"]}
        cancel = {"protocol": 3, "op": "CANCEL", "request_id": 3}
        child._process.stdin.write(encode_frame(frame) + encode_frame(cancel))
        await child._process.stdin.drain()
        deferred = await asyncio.wait_for(child.receive(), 2)
        terminal = await asyncio.wait_for(child.receive(), 2)
        assert deferred["event"] == "CANCEL_DEFERRED"
        assert terminal["event"] == "CANCELLED" and terminal["operation"] == "GENERATE"
        assert all(terminal[name] is True for name in ("request_terminal_proven", "operation_cleanup_proven", "engine_usable"))
        await child.send({**common, "op": "CLOSE", "request_id": 4, "reason": "interrupt"})
        assert (await child.receive())["cleanup_proven"] is True
        await child.stop()
    finally:
        await child.force_terminate()


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", [None, "sequence", "duplicate", "prefix", "clock", "extra"])
async def test_W03_safe_text_sequence_prefix_and_clock(fault):
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "你好")
    def transform(frame):
        first = {"protocol": 3, "event": "SAFE_TEXT", "request_id": frame["request_id"],
                 "sequence": 0, "text": "你", "monotonic_ns": frame["llm_send_monotonic_ns"]}
        second = {**first, "sequence": 1, "text": "好", "monotonic_ns": frame["terminal_monotonic_ns"]}
        if fault == "sequence": first["sequence"] = 1
        if fault == "duplicate": second["sequence"] = 0
        if fault == "prefix": first["text"] = "錯"
        if fault == "clock": second["monotonic_ns"] += 1
        if fault == "extra": first["extra"] = True
        return [first, second, frame | {"first_safe_text_monotonic_ns": first["monotonic_ns"]}]
    children[0].transform = transform
    if fault is None:
        result = await adapter.generate(snapshot, "你好")
        assert result.safe_fragments == ("你", "好")
        assert result.metrics.first_safe_text_monotonic_ns == result.metrics.llm_send_monotonic_ns
        children[0].transform = lambda frame: frame
        await adapter.stop()
    else:
        with pytest.raises(LLMFatalError):
            await adapter.generate(snapshot, "你好")
        assert children[0].terminated == 1 and not adapter._ledger.fragments


@pytest.mark.asyncio
async def test_W10_real_process_discard_then_normal_generation():
    adapter, _, _, _ = adapter_fixture()
    adapter._child_factory = ProcessChild
    await adapter.start()
    child = adapter._child
    process = child._process
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "私密測試")
    proof = await adapter.discard_ticket(snapshot)
    assert proof.private_input_erased and proof.ticket_invalidated and proof.native_render_scrubbed
    assert adapter.conversation_revision == 0 and adapter._child is child
    fresh = await adapter.measure("s", 1, "正常")
    assert fresh.ticket != snapshot.ticket
    assert (await adapter.generate(fresh, "正常")).text == "你好"
    await adapter.stop()
    assert process.returncode == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("option", ["--discard-scrub-fails", "--discard-bad-proof", "--discard-lost-ack"])
async def test_W11_real_process_discard_failure_joins_pgid(option):
    adapter, _, _, _ = adapter_fixture()
    adapter._cfg = replace(adapter._cfg, terminal_grace_seconds=0.1,
                           child_terminate_timeout_seconds=0.2)
    adapter._child_factory = lambda *args: ProcessChild(*args, options=(option,))
    await adapter.start()
    child = adapter._child
    process = child._process
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "私密測試")
    with pytest.raises(LLMFatalError):
        await adapter.discard_ticket(snapshot)
    assert process.returncode is not None
    assert child.termination_evidence.orphan_count == 0
    assert not child._live_process_group_members(child.pgid)
    assert adapter.state is AdapterState.DESTROYED


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["protocol", "event", "request_id", "session_id", "generation",
    "conversation_revision", "ticket", "input_sha256", "native_render_scrubbed",
    "ticket_invalidated", "private_input_erased", "conversation_state"])
@pytest.mark.parametrize("fault", ["missing", "wrong"])
async def test_W11_discard_terminal_exact_field_matrix(field, fault):
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "私密測試")
    def transform(frame):
        frame = dict(frame)
        if fault == "missing": del frame[field]
        else: frame[field] = "private-wrong-proof"
        return frame
    children[0].transform = transform
    with pytest.raises(LLMFatalError) as raised:
        await adapter.discard_ticket(snapshot)
    assert "private-wrong-proof" not in str(raised.value)
    assert children[0].runtime.scrubs == 1 and children[0].runtime.sends == 0
    assert children[0].terminated == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("flag", ["native_render_scrubbed", "ticket_invalidated", "private_input_erased"])
async def test_W11_false_discard_proofs_are_not_clean_disposal(flag):
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "私密測試")
    children[0].transform = lambda frame: frame | {flag: False}
    with pytest.raises(LLMFatalError):
        await adapter.discard_ticket(snapshot)
    assert children[0].terminated == 1


@pytest.mark.asyncio
async def test_W12_interrupt_waits_atomic_disposal_without_cancel_command():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "私密測試")
    child = children[0]
    child.release.clear()
    child.entered.clear()
    abort_entered = asyncio.Event()
    original_wait = adapter._operation_done.wait
    async def observed_wait():
        abort_entered.set()
        await original_wait()
    adapter._operation_done.wait = observed_wait
    discarding = asyncio.create_task(adapter.discard_ticket(snapshot))
    await child.entered.wait()
    aborting = asyncio.create_task(adapter.abort())
    await abort_entered.wait()
    assert not aborting.done() and not discarding.done()
    assert child.runtime.cancels == 0 and all(frame["op"] != "CANCEL" for frame in child.commands)
    child.release.set()
    await aborting
    with pytest.raises(asyncio.CancelledError):
        await discarding
    assert adapter._ledger.state == "CONVERSATION_READY" and adapter.conversation_revision == 0
    await adapter.close_conversation("s", 1, "interrupt")
    await adapter.stop()


def _discarding_session():
    from tests.fakes.m4b_llm_child import Runtime
    from sbd.cognition.litert_lm.worker import WorkerSession
    session = WorkerSession(Runtime())
    common = {"protocol": 3, "session_id": "s", "generation": 1}
    for frame in (
        {**common, "op": "OPEN", "request_id": 1},
        {**common, "op": "MEASURE", "request_id": 2, "text": "私密",
         "input_sha256": digest("私密"), "output_reserve_tokens": 128},
    ):
        session.ledger.command(frame)
        session.ledger.event(session.execute(frame)[0])
    ticket = session.ledger.ticket
    discard = {**common, "op": "DISCARD_TICKET", "request_id": 3,
               **{key: ticket[key] for key in ("ticket", "conversation_revision", "input_sha256")}}
    return session, discard


@pytest.mark.parametrize("operation", ["CANCEL", "OPEN", "MEASURE", "DISCARD_TICKET", "GENERATE", "CLOSE", "SHUTDOWN"])
def test_W12_discarding_rejects_every_command_before_any_native_work(operation):
    session, discard = _discarding_session()
    session.ledger.command(discard)
    assert session.ledger.state == "DISCARDING"
    command = {**discard, "op": operation, "request_id": 4}
    if operation == "CANCEL":
        command = {"protocol": 3, "op": operation, "request_id": 3}
    elif operation == "SHUTDOWN":
        command = {"protocol": 3, "op": operation}
    with pytest.raises(LLMFatalError):
        session.ledger.command(command)
    assert session.runtime.scrubs == session.runtime.sends == session.runtime.cancels == 0
    assert session.ledger.revision == 0 and session.runtime.history == []


@pytest.mark.parametrize("field,value", [("request_id", 4), ("session_id", "stale"),
    ("generation", 2), ("conversation_revision", 1), ("ticket", "f" * 32),
    ("input_sha256", "f" * 64)])
def test_W11_child_discard_identity_matrix_precedes_scrub(field, value):
    session, discard = _discarding_session()
    with pytest.raises(LLMFatalError):
        session.ledger.command(discard | {field: value})
    assert session.runtime.scrubs == session.runtime.sends == 0
    assert session.ledger.state == "MEASURED"


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["CANCEL", "OPEN", "MEASURE", "DISCARD_TICKET", "GENERATE", "CLOSE", "SHUTDOWN"])
async def test_W12_real_process_coalesced_reentry_has_no_disposal_ack(operation):
    from sbd.cognition.llm_child_protocol import encode_frame
    adapter, _, _, _ = adapter_fixture()
    child = ProcessChild(adapter._cfg, adapter._lock, 1)
    await child.start()
    process = child._process
    try:
        common = {"protocol": 3, "session_id": "s", "generation": 1}
        await child.send({**common, "op": "OPEN", "request_id": 1})
        assert (await child.receive())["event"] == "OPENED"
        await child.send({**common, "op": "MEASURE", "request_id": 2,
                          "text": "私密", "input_sha256": digest("私密"), "output_reserve_tokens": 128})
        ticket = await child.receive()
        discard = {**common, "op": "DISCARD_TICKET", "request_id": 3,
                   **{key: ticket[key] for key in ("ticket", "conversation_revision", "input_sha256")}}
        reentry = {**discard, "op": operation, "request_id": 4}
        if operation == "CANCEL":
            reentry = {"protocol": 3, "op": operation, "request_id": 3}
        elif operation == "SHUTDOWN":
            reentry = {"protocol": 3, "op": operation}
        child._process.stdin.write(encode_frame(discard) + encode_frame(reentry))
        await child._process.stdin.drain()
        with pytest.raises(LLMFatalError):
            await asyncio.wait_for(child.receive(), 2)
    finally:
        await child.force_terminate()
    assert process.returncode is not None
    assert child.termination_evidence.orphan_count == 0
    assert not child._live_process_group_members(child.pgid)
