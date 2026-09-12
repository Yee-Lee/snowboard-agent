"""M4B-NORM-001 projector; input admission/mutation integration is owned by D."""
from dataclasses import replace
import pytest
from sbd.cognition.prompt_builder import ListenProjector, UnsupportedInputError
from sbd.core.events import PerceptionResult

FACT = PerceptionResult("listen","ok","你好",session_id="private-session",turn_id=7)


def project(fact=FACT, **overrides):
    values = dict(perceptions=(fact,), session_id="private-session",turn_id=7,
                  pending_message_count=0,available_perceptions=("listen",),available_actions=("speak",))
    values.update(overrides)
    return ListenProjector().project(**values)


@pytest.mark.parametrize("text,expected",[("　Ａ\t\nＢ\u00a0🙂  ","A B 🙂"),("\t你\r\n好\t","你 好")],ids=["N01","N02"])
def test_normalization(text,expected):
    assert project(replace(FACT,text=text)) == expected
    assert "private" not in expected


@pytest.mark.parametrize("text",["\x00","\ud800","\udfff",*[chr(i) for i in range(32) if i not in (9,10,13)],"\x7f","\x85"],ids=lambda x:"N03-"+repr(x))
def test_invalid_text(text):
    with pytest.raises(UnsupportedInputError,match="^UNSUPPORTED_INPUT$"):
        project(replace(FACT,text=text))


@pytest.mark.parametrize("text",[None,0,False,{},b"hello"],ids=lambda x:"N04-"+type(x).__name__)
def test_non_string(text):
    with pytest.raises(UnsupportedInputError):
        project(replace(FACT,text=text))


@pytest.mark.parametrize("status,text",[("ok",""),("ok"," \t\n"),("timeout",object()),("error",object())],ids=["N05-empty","N05-whitespace","N05-timeout","N05-error"])
def test_no_input(status,text):
    assert project(replace(FACT,status=status,text=text,extra={"hostile":object()})) is None


def test_no_truncation_and_python_codepoints_N06():
    for count in (20,21):
        text = "🙂 " + "字" * (count-2)
        result = project(replace(FACT,text=text))
        assert result == text and len(result) == count


@pytest.mark.parametrize("overrides",[
    {"perceptions":()}, {"perceptions":(FACT,FACT)}, {"perceptions":[FACT]},
    {"pending_message_count":1},{"pending_message_count":False},
    {"session_id":"wrong"},{"turn_id":8},{"available_perceptions":()}, {"available_actions":()},
    *[{"perceptions":(replace(FACT,kind=k),)} for k in ("read","look")],
    {"perceptions":(replace(FACT,status="unknown"),)},
],ids=lambda x:"N08-"+next(iter(x)))
def test_unsupported_envelope(overrides):
    with pytest.raises(UnsupportedInputError):
        project(**overrides)
