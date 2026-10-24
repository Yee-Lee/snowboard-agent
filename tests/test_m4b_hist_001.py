"""Replacement history privacy; no legacy per-turn fresh Conversation behavior."""
import pytest
from tests.fakes.m4b_llm_child import adapter_fixture

@pytest.mark.asyncio
async def test_history_is_private_and_destroyed_at_close():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("private-session", 1)
    text = "私密內容"
    snapshot = await adapter.measure("private-session", 1, text)
    await adapter.generate(snapshot, text)
    runtime = children[0].runtime
    assert runtime.history == [text]
    assert text not in repr(children[0].commands)
    await adapter.close_conversation("private-session", 1, "session_end")
    assert runtime.history is None
    assert adapter._ledger.ticket is None and adapter._ledger.claim is None
    assert not adapter._ledger.fragments
    await adapter.stop()
