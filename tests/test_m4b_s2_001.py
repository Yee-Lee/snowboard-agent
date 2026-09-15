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


@pytest.mark.parametrize("wire", [b'{"text":"a","end":false}x', b'{"text":"a","end":0}', b'{"text":"\xff","end":true}', b'{"text":"\xe4', b'{"text":"a","end":true,"x":0}'], ids=lambda x:"X04-"+str(len(x)))
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


def test_json_schema_multiline_wire_X06():
    wire = b' {\n "text" : "hello",\n "end" : false\n}\n'
    parser = IncrementalSemanticParser()
    fragments = []
    for byte in wire:
        fragments.extend(parser.feed(bytes([byte])))
    assert "".join(fragments) == "hello"
    assert parser.finish() == SemanticOutput("hello", False)


def test_end_before_text_incremental_X06():
    wire = b'{"end":false,"text":"hello"}'
    parser = IncrementalSemanticParser()
    fragments = []
    for byte in wire:
        fragments.extend(parser.feed(bytes([byte])))
    assert fragments == ["hello"]
    assert parser.finish() == SemanticOutput("hello", False)


@pytest.mark.parametrize("wire", [
    b'{"text":"","end":false}', b'{"text":" \\t\\n","end":false}',
], ids=["X07-empty-false", "X07-normalizes-empty-false"])
def test_empty_terminal_never_emits_safe_text_or_result_X07(wire):
    parser = IncrementalSemanticParser()
    assert parser.feed(wire) == ()
    with pytest.raises(SemanticError, match="^INVALID_SEMANTIC$"):
        parser.finish()
    assert parser._buffer == parser._prefix == ""


@pytest.mark.parametrize("wire", [
    b'{"text":"","end":true}', b'{"end":true,"text":" \\t\\n"}',
], ids=["X08-empty-end", "X08-normalizes-empty-end-reordered"])
def test_empty_end_terminal_is_valid_and_emits_no_safe_text_X08(wire):
    parser = IncrementalSemanticParser()
    assert parser.feed(wire) == ()
    assert parser.finish() == SemanticOutput("", True)
