"""M4B-SEM-001 terminal semantic assertions (shared action validation in D)."""
import json
import pytest
from sbd.cognition.semantic import SemanticError, SemanticOutput, spoken_length, validate_semantic


@pytest.mark.parametrize("text,end,valid", [("嗨",False,True),("嗨",True,True),("",True,True),("",False,False)], ids=["S01-nonempty-continue","S01-nonempty-end","S01-empty-end","S01-empty-continue"])
def test_terminal_combinations(text, end, valid):
    wire = json.dumps({"text":text,"end":end},ensure_ascii=False,separators=(",",":"))
    if valid:
        assert validate_semantic(wire) == SemanticOutput(text,end)
    else:
        with pytest.raises(SemanticError,match="^INVALID_SEMANTIC$"):
            validate_semantic(wire)


@pytest.mark.parametrize("wire,expected", [
    (r'{"text":"\"\\\/\u4f60\u597d\ud83d\ude42","end":false}', '"\\/你好🙂'),
    (r'{"text":"\uff21\t B\n","end":false}', "A B"),
], ids=["S02-escapes","S02-normalize-once"])
def test_escapes(wire, expected):
    assert validate_semantic(wire).text == expected


@pytest.mark.parametrize("escape", [r"\u0000",r"\ud800",r"\udfff",r"\u000b",r"\u007f",r"\q", "\\"], ids=lambda x:"S03-"+repr(x))
def test_invalid_controls_and_surrogates(escape):
    with pytest.raises(SemanticError):
        validate_semantic('{"text":"'+escape+'","end":false}')


def test_spoken_boundary_S04():
    text = "字， " * 30
    assert spoken_length(text) == 30
    assert validate_semantic({"text":text,"end":False}).text == ("字, " * 30).strip()
    with pytest.raises(SemanticError):
        validate_semantic({"text":text+"🙂","end":False})


@pytest.mark.parametrize("text,count",[("「你好嗎？」",3),("嗨🙂！",2)],ids=["S05-three","S05-two"])
def test_spoken_examples(text,count):
    assert spoken_length(text) == count
