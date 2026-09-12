"""M4B-PREFILL-001 adapter-side independent admission defense."""
import pytest
from sbd.cognition.llm import LLMFatalError
from tests.fakes.m4b_llm_child import adapter_fixture

@pytest.mark.asyncio
@pytest.mark.parametrize("prefill,accept", [(128, True), (129, False)], ids=["F01", "F02"])
async def test_fresh_tier(prefill, accept):
    adapter, children, _, sampler = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    children[0].runtime.incremental = children[0].runtime.prefill = prefill
    snapshot = await adapter.measure("s", 1, "你好")
    if accept:
        await adapter.generate(snapshot, "你好")
        assert sampler.calls == 2
    else:
        with pytest.raises(LLMFatalError):
            await adapter.generate(snapshot, "你好")
        assert sampler.calls == 1 and children[0].runtime.sends == 0
    await adapter.stop()

@pytest.mark.asyncio
async def test_F03_following_turn_has_no_fresh_ceiling():
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "你好")
    await adapter.generate(snapshot, "你好")
    children[0].runtime.incremental = children[0].runtime.prefill = 129
    snapshot = await adapter.measure("s", 1, "再次")
    await adapter.generate(snapshot, "再次")
    assert children[0].runtime.sends == 2
    await adapter.stop()

@pytest.mark.asyncio
@pytest.mark.parametrize("tokens,kv", [(33, 0), (2, 897)], ids=["F04-input", "F04-context"])
async def test_F04_independent_limits_never_send(tokens, kv):
    adapter, children, _, sampler = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("s", 1)
    children[0].runtime.user_tokens = tokens
    children[0].runtime.kv = kv
    children[0].runtime.incremental = children[0].runtime.prefill = 128
    snapshot = await adapter.measure("s", 1, "你好")
    with pytest.raises(LLMFatalError):
        await adapter.generate(snapshot, "你好")
    assert sampler.calls == 1 and children[0].runtime.sends == 0
    await adapter.stop()
