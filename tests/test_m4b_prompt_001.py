"""M4B-PROMPT-001 exact canonical prompt and terminal grammar corpus."""
import hashlib
import pytest
from pathlib import Path
import sbd.cognition.prompt_builder as prompt
from sbd.cognition.semantic import GRAMMAR_BYTES, GRAMMAR_SHA256, SemanticError, validate_semantic


def test_exact_prompt_and_tokenizer_P01():
    values = dict(core=prompt.CORE_PROMPT,personality=prompt.PERSONALITY_PROMPT,system=prompt.SYSTEM_PROMPT)
    seen = []
    def tokenize(text):
        seen.append(text)
        return list(range(prompt.PROMPT_COUNTS[next(k for k,v in values.items() if v == text)]))
    assert prompt.attest_prompt(tokenize) == {"core":57,"personality":9,"system":66}
    assert seen == list(values.values())
    assert values["system"] == values["core"] + values["personality"]
    for name,text in values.items():
        assert not text.startswith("\ufeff") and not text.endswith("\n")
        assert hashlib.sha256(text.encode()).hexdigest() == prompt.PROMPT_HASHES[name]


@pytest.mark.parametrize("name",["CORE_PROMPT","PERSONALITY_PROMPT","SYSTEM_PROMPT"],ids=lambda x:"P02-"+x)
@pytest.mark.parametrize("mutation",[lambda x:x+"\n",lambda x:"\ufeff"+x,lambda x:x[:-1],lambda x:x+"suffix"],ids=["newline","BOM","removed-byte","suffix"])
def test_prompt_mutation_fails(monkeypatch,name,mutation):
    monkeypatch.setattr(prompt,name,mutation(getattr(prompt,name)))
    seen = []
    with pytest.raises(ValueError,match="PROMPT_IDENTITY_MISMATCH"):
        prompt.attest_prompt(lambda text: seen.append(text))
    assert seen == []


def test_grammar_artifact_identity_P03():
    raw = (Path(__file__).parents[1]/"requirements/m4b/semantic.gbnf").read_bytes()
    assert raw == GRAMMAR_BYTES
    assert hashlib.sha256(raw).hexdigest() == GRAMMAR_SHA256


@pytest.mark.parametrize("wire",[
    '{"end":false,"text":"a"}', '{"text":"a", "end":false}',
    ' {"text":"a","end":false}', '{"text":"a","end":false}\n',
    '{"text":"a","text":"b","end":false}', '{"text":"a","end":false,"x":0}',
    '{"text":"a"}', '{"end":true}', '{"text":1,"end":false}',
    '{"text":"a","end":0}', '{"text":"a","end":"false"}',
    '{"text":"a","end":false}x', b'{"text":"\xff","end":false}',
    r'{"text":"\z","end":false}', r'{"text":"\ud800","end":false}',
],ids=lambda x:"P05-"+str(len(x)))
def test_canonical_wire_rejects_mutations(wire):
    with pytest.raises(SemanticError):
        validate_semantic(wire)


@pytest.mark.parametrize("wire",['{"text":"a","end":false}','{"text":"","end":true}',r'{"text":"a\/b","end":true}'],ids=["P05-continue","P05-rest","P05-escapes"])
def test_canonical_wire_accepts(wire):
    assert type(validate_semantic(wire).end) is bool
