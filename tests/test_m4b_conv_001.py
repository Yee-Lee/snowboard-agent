"""M4B-CONV-001 adapter continuity and explicit generation replacement."""
import pytest
from sbd.cognition.llm import LLMFatalError
from tests.fakes.m4b_llm_child import adapter_fixture

@pytest.mark.asyncio
async def test_C01_C03_C04_clean_replacement_and_explicit_repeat():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    for generation, texts in [(1, ("第一", "第二")), (2, ("重說", "繼續"))]:
        await adapter.control.open_conversation("same-session", generation)
        runtime = children[0].runtime
        assert runtime.history == []
        history = runtime.history
        for text in texts:
            snapshot = await adapter.measure("same-session", generation, text)
            await adapter.generate(snapshot, text)
            assert runtime.history is history
        proof = await adapter.control.close_conversation("same-session", generation, "replacement")
        assert proof.request_terminal_proven and proof.cleanup_proven and proof.engine_usable
        assert history == [] and runtime.history is None
    assert len(children) == 1 and children[0].runtime.sends == 4
    await adapter.stop()

@pytest.mark.asyncio
@pytest.mark.parametrize("session,generation", [("wrong", 1), ("s", 2)], ids=["C06-session", "C06-generation"])
async def test_C06_stale_identity_never_changes_active_claim(session, generation):
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    with pytest.raises(LLMFatalError):
        adapter.assert_conversation(session, generation)
    assert adapter._ledger.claim == ("s", 1) and adapter.conversation_revision == 0
    assert children[0].runtime.sends == 0
    await adapter.stop()
