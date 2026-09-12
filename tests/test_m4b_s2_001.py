"""M4B-S2-001 executes real byte parser; action dispatch assertions belong to D."""
import pytest
from sbd.cognition.semantic import IncrementalSemanticParser, SemanticError, SemanticOutput

WIRE = '{"text":" Ａ e\\u0301🙂\\n你\\"好 ","end":false}'.encode()


@pytest.mark.parametrize("boundary",range(len(WIRE)+1),ids=lambda x:f"X01-X02-boundary-{x}")
def test_every_byte_boundary(boundary):
    parser = IncrementalSemanticParser()
    fragments = parser.feed(WIRE[:boundary]) + parser.feed(WIRE[boundary:])
    result = parser.finish()
    assert result == SemanticOutput('A é🙂 你"好',False)
    assert fragments and all(fragments)
    assert result.text.startswith("".join(fragments))
    assert "\\u" not in "".join(fragments)


def test_one_byte_partitions_X03():
    parser = IncrementalSemanticParser()
    fragments = []
    for byte in WIRE:
        fragments.extend(parser.feed(bytes([byte])))
    terminal = parser.finish()
    assert "".join(fragments) == terminal.text


@pytest.mark.parametrize("wire", [b'{"text":"a","end":false}x', b'{"text":"a","end":0}', b'{"text":"\xff","end":true}', b'{"text":"a","end":false}\n', b'{"text":"\xe4', b'{"text":"a","end":true,"x":0}'], ids=lambda x:"X04-"+str(len(x)))
def test_invalid_terminal(wire):
    parser = IncrementalSemanticParser()
    with pytest.raises(SemanticError):
        parser.feed(wire)
        parser.finish()
    with pytest.raises(SemanticError):
        parser.feed(b"anything")
    assert parser._buffer == parser._prefix == ""


@pytest.mark.parametrize("late",["feed","finish"],ids=["X04-late-fragment","X04-duplicate-terminal"])
def test_terminal_is_final(late):
    parser = IncrementalSemanticParser()
    parser.feed(WIRE)
    parser.finish()
    with pytest.raises(SemanticError):
        parser.feed(b"x") if late == "feed" else parser.finish()


def test_conservative_normalization_X06():
    parser = IncrementalSemanticParser()
    assert parser.feed(b'{"text":"e') == ()
    assert parser.feed(b'\\u0301') == ()
    assert parser.feed(b'","end":false}') == ("é",)
    assert parser.finish().text == "é"
    empty = IncrementalSemanticParser()
    assert empty.feed(b'{"text":"","end":true}') == ()
    assert empty.finish().end is True
