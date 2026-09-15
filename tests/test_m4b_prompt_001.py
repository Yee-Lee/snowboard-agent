"""M4B-PROMPT-001 exact prompt and constrained-JSON schema corpus."""
import hashlib
import json
import threading
from types import SimpleNamespace
import pytest
from pathlib import Path
import sbd.cognition.prompt_builder as prompt
from sbd.cognition.semantic import (
    RESPONSE_SCHEMA_LOCATOR, RESPONSE_SCHEMA_SHA256, RESPONSE_SCHEMA_SIZE_BYTES,
    ResponseSchemaError, SemanticError, load_response_schema, validate_semantic,
)


EXPECTED_RESPONSE_SCHEMA_SHA256 = "796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9"
SUPERSEDED_GRAMMAR_SHA256 = "fe97dc391364d875b9955cdfb283bd160b7845eae1e63734075da806973207b3"


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


def test_response_schema_identity_P03():
    schema_path = Path(__file__).parents[1] / RESPONSE_SCHEMA_LOCATOR
    raw = schema_path.read_bytes()
    assert len(raw) == RESPONSE_SCHEMA_SIZE_BYTES == 352
    assert raw.endswith(b"\n") and not raw.startswith(b"\xef\xbb\xbf")
    assert hashlib.sha256(raw).hexdigest() == RESPONSE_SCHEMA_SHA256
    assert RESPONSE_SCHEMA_SHA256 == EXPECTED_RESPONSE_SCHEMA_SHA256
    expected = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:snowboard:m4b-mva:semantic-output:v1",
        "title": "M4B-MVA compact semantic output",
        "type": "object",
        "additionalProperties": False,
        "required": ["text", "end"],
        "properties": {
            "text": {"type": "string", "maxLength": 4096},
            "end": {"type": "boolean"},
        },
    }
    loaded = load_response_schema()
    assert loaded == expected == json.loads(raw)
    assert all(keyword not in raw.decode() for keyword in (
        '"oneOf"', '"const"', '"minLength"', '"pattern"', '"if"', '"then"', '"else"'))
    profile = json.loads((Path(__file__).parents[1]/"requirements/m4b/product-profile.json").read_text())
    lock = json.loads((Path(__file__).parents[1]/"requirements/m4b/llm-artifacts.json").read_text())
    assert profile["response_schema_locator"] == lock["product_profile"]["response_schema_locator"] == RESPONSE_SCHEMA_LOCATOR
    assert profile["response_schema_sha256"] == lock["product_profile"]["response_schema_sha256"] == RESPONSE_SCHEMA_SHA256
    assert "grammar_sha256" not in profile and "grammar_locator" not in profile
    assert SUPERSEDED_GRAMMAR_SHA256 not in (json.dumps(profile) + json.dumps(lock))


@pytest.mark.parametrize("variant", ["missing", "no-final-lf", "bom", "byte-change", "extra-byte"],
                         ids=lambda value: "P09-" + value)
def test_deployed_schema_mutation_fails_before_decoding(tmp_path, variant):
    source = (Path(__file__).parents[1] / RESPONSE_SCHEMA_LOCATOR).read_bytes()
    path = tmp_path / RESPONSE_SCHEMA_LOCATOR
    path.parent.mkdir(parents=True)
    if variant != "missing":
        mutated = {"no-final-lf": source[:-1], "bom": b"\xef\xbb\xbf" + source,
                   "byte-change": source.replace(b"4096", b"4097"),
                   "extra-byte": source + b" "}[variant]
        path.write_bytes(mutated)
    with pytest.raises(ResponseSchemaError, match="RESPONSE_SCHEMA_IDENTITY_MISMATCH"):
        load_response_schema(repo_root=tmp_path)


@pytest.mark.parametrize("wire",[
    '{"text":"a","text":"b","end":false}', '{"text":"a","end":false,"x":0}',
    '{"text":"a"}', '{"end":true}', '{"text":1,"end":false}',
    '{"text":"a","end":0}', '{"text":"a","end":"false"}',
    '{"text":"","end":false}',
    '{"text":"a","end":false}x', b'{"text":"\xff","end":false}',
    r'{"text":"\z","end":false}', r'{"text":"\ud800","end":false}',
],ids=lambda x:"P05-"+str(len(x)))
def test_canonical_wire_rejects_mutations(wire):
    with pytest.raises(SemanticError):
        validate_semantic(wire)


@pytest.mark.parametrize("wire",[
    '{"text":"a","end":false}', r'{"text":"a\/b","end":true}',
    '{"text":"","end":true}', '{"end":false,"text":"a"}',
], ids=["P05-continue", "P05-end-escapes", "P05-empty-end", "P05-reordered"])
def test_canonical_wire_accepts(wire):
    assert type(validate_semantic(wire).end) is bool


@pytest.mark.parametrize("wire", [
    '{"text":"a", "end":false}',
    ' {\n "text" : "a",\n "end" : false\n}\n',
], ids=["P05-inline-schema-whitespace", "P05-multiline-schema-whitespace"])
def test_json_schema_wire_whitespace_is_accepted(wire):
    assert validate_semantic(wire).text == "a"


def test_native_generation_uses_json_schema_and_never_regex():
    from sbd.cognition.litert_lm.worker import LiteRTRuntime

    calls = []

    class ResponseFormat:
        @staticmethod
        def json(schema):
            calls.append(("json", schema))
            return "json-constraint"

        @staticmethod
        def regex(_pattern):
            pytest.fail("native generation must not use the punctuation-producing regex")

    class Conversation:
        token_count = 106

        @staticmethod
        def send_message(text, *, max_output_tokens, response_format):
            assert (text, max_output_tokens, response_format) == (
                "你是誰？", 128, "json-constraint")
            return {"role": "assistant", "content": [{"type": "text", "text":
                '{\n"text":"我是雪板，很高興為您服務！",\n"end":false\n}'}]}

        @staticmethod
        def get_benchmark_info():
            return SimpleNamespace(last_decode_token_count=23,
                                   last_prefill_token_count=83)

    runtime = LiteRTRuntime.__new__(LiteRTRuntime)
    runtime._conversation = Conversation()
    runtime._response_format = ResponseFormat
    runtime._cancelled_error = RuntimeError
    runtime._pending_cancel = False
    runtime._cancel_requested = False
    runtime._active = None
    runtime._lock = threading.Lock()

    raw, decode, conversation, prefill = runtime.generate("你是誰？")

    assert calls == [("json", load_response_schema())]
    assert validate_semantic(raw).text == "我是雪板,很高興為您服務!"
    assert (decode, conversation, prefill) == (23, 106, 83)
