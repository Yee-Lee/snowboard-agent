"""M4B private framing: exact bytes, identity, sequence, and proof failures."""
import asyncio
import pytest
from sbd.cognition.llm_child_protocol import (
    decode_frame, encode_frame, read_frame, LLMProtocolError, MAX_CONTROL_BYTES)

@pytest.mark.asyncio
async def test_fragmented_and_coalesced_frame_roundtrip():
    frame = {"protocol": 3, "op": "OPEN", "request_id": 1, "session_id": "s", "generation": 1}
    reader = asyncio.StreamReader(limit=MAX_CONTROL_BYTES + 1)
    raw = encode_frame(frame)
    for byte in raw:
        reader.feed_data(bytes([byte]))
    reader.feed_data(raw + raw)
    assert [await read_frame(reader) for _ in range(3)] == [frame] * 3

@pytest.mark.parametrize("raw", [
    b"", b"{}", b"\xff\n", b"{\n", b"[]\n", b'{"protocol":3,"protocol":3}\n',
    b'{"protocol":true}\n', b'{"protocol":3,"n":NaN}\n',
    b'{"protocol":3,"n":Infinity}\n', b"x" * (MAX_CONTROL_BYTES + 1) + b"\n",
])
def test_W08_malformed_frames_fail_closed(raw):
    with pytest.raises(LLMProtocolError):
        decode_frame(raw)

@pytest.mark.asyncio
async def test_W08_eof_mid_frame():
    reader = asyncio.StreamReader()
    reader.feed_data(b'{"protocol":3')
    reader.feed_eof()
    with pytest.raises(LLMProtocolError):
        await read_frame(reader)

def test_maximum_framing_boundary():
    overhead = len(encode_frame({"protocol": 3, "text": ""}))
    frame = {"protocol": 3, "text": "x" * (MAX_CONTROL_BYTES - overhead)}
    assert len(encode_frame(frame)) == MAX_CONTROL_BYTES
    frame["text"] += "x"
    with pytest.raises(LLMProtocolError):
        encode_frame(frame)
