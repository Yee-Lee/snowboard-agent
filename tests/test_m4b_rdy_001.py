"""M4B READY attestation and proof matrices using the live parent adapter."""
import pytest
from sbd.cognition.llm import LLMFatalError
from sbd.cognition.llm_child_protocol import READY_FIELDS
from tests.fakes.m4b_llm_child import adapter_fixture

@pytest.mark.asyncio
@pytest.mark.parametrize("field", sorted(READY_FIELDS | {"protocol", "event"}))
@pytest.mark.parametrize("mutation", ["missing", "wrong"])
async def test_W01_every_ready_field_authenticated(field, mutation):
    adapter, children, _, _ = adapter_fixture()
    original = adapter._child_factory
    def factory(*args):
        child = original(*args)
        start = child.start
        async def corrupted():
            frame = await start()
            if mutation == "missing":
                del frame[field]
            else:
                frame[field] = "private-attestation-canary"
            return frame
        child.start = corrupted
        return child
    adapter._child_factory = factory
    with pytest.raises(LLMFatalError) as raised:
        await adapter.start()
    assert "private-attestation-canary" not in str(raised.value)
    assert children[0].terminated == 1

@pytest.mark.asyncio
async def test_W01_extra_ready_field_is_fatal():
    adapter, children, _, _ = adapter_fixture()
    original = adapter._child_factory
    def factory(*args):
        child = original(*args)
        start = child.start
        async def corrupted():
            return {**await start(), "extra": 1}
        child.start = corrupted
        return child
    adapter._child_factory = factory
    with pytest.raises(LLMFatalError):
        await adapter.start()
    assert children[0].terminated == 1

@pytest.mark.asyncio
@pytest.mark.parametrize("event,proofs", [
    ("OPEN_REJECTED", {"cleanup_proven": True, "engine_usable": True}),
    ("OPEN_REJECTED", {"cleanup_proven": False, "engine_usable": True}),
    ("OPEN_REJECTED", {"cleanup_proven": True, "engine_usable": False}),
])
async def test_W02_open_rejection_proof(event, proofs):
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    def transform(frame):
        children[0].runtime.close_conversation()
        return {key: frame[key] for key in ("protocol", "request_id", "session_id", "generation")} | {
            "event": event, "code": "OPEN_REJECTED", **proofs}
    children[0].transform = transform
    if all(proofs.values()):
        result = await adapter.open_conversation("s", 1)
        assert result.cleanup_proven and result.engine_usable
        await adapter.stop()
    else:
        with pytest.raises(LLMFatalError):
            await adapter.open_conversation("s", 1)
        assert children[0].terminated == 1
