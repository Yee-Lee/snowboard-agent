"""M4B-SEM-001 terminal semantic assertions (shared action validation in D)."""
import json
import pytest
from sbd.cognition.semantic import SemanticError, SemanticOutput, spoken_length, validate_semantic


@pytest.mark.parametrize("text,end,valid", [
    ("嗨",False,True), ("嗨",True,True),
    ("",False,False), ("",True,True),
    (" \t\n",False,False), (" \t\n",True,True),
], ids=["S01-nonempty-continue","S01-nonempty-end","S01-empty-continue",
        "S01-empty-end","S01-normalizes-empty-continue","S01-normalizes-empty-end"])
def test_terminal_combinations(text, end, valid):
    wire = json.dumps({"text":text,"end":end},ensure_ascii=False,separators=(",",":"))
    if valid:
        assert validate_semantic(wire) == SemanticOutput(" ".join(text.split()), end)
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


@pytest.mark.parametrize("text,valid", [
    ("。" * 4096, True), ("。" * 4097, False),
    ("字" * 30 + "。" * 4066, True), ("字" * 30 + "。" * 4067, False),
], ids=["punctuation-4096", "punctuation-4097", "countable-4096", "countable-4097"])
@pytest.mark.parametrize("surface", ["raw-json", "decoded-mapping"])
def test_native_schema_max_length_is_terminally_enforced(text, valid, surface):
    value = {"text": text, "end": False}
    input_value = (json.dumps(value, ensure_ascii=False) if surface == "raw-json" else value)
    if valid:
        assert validate_semantic(input_value).text
    else:
        with pytest.raises(SemanticError, match="^INVALID_SEMANTIC$"):
            validate_semantic(input_value)


@pytest.mark.parametrize("text,count",[("「你好嗎？」",3),("嗨🙂！",2)],ids=["S05-three","S05-two"])
def test_spoken_examples(text,count):
    assert spoken_length(text) == count


@pytest.mark.parametrize("wire,expected", [
    (' { "end" : false, "text" : "順序可交換" }\n', SemanticOutput("順序可交換", False)),
    ('{"end":true,"text":""}', SemanticOutput("", True)),
], ids=["S06-whitespace-reordered", "S06-empty-end"])
def test_json_lexical_equivalence(wire, expected):
    assert validate_semantic(wire) == expected


@pytest.mark.parametrize("wire", [
    '{"text":"a","end":false,"text":"b"}',
    '{"end":false,"end":true,"text":"a"}',
], ids=["S07-duplicate-text", "S07-duplicate-end"])
def test_duplicate_members_are_rejected(wire):
    with pytest.raises(SemanticError, match="^INVALID_SEMANTIC$"):
        validate_semantic(wire)
