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
    assert prompt.attest_prompt(tokenize) == {"core":59,"personality":9,"system":68}
    assert seen == list(values.values())
    assert values["system"] == values["core"] + values["personality"]
    for name,text in values.items():
        assert not text.startswith("\ufeff") and not text.endswith("\n")


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


def test_native_stream_waits_for_callbacks_after_c_call_returns(monkeypatch, tmp_path):
    from sbd.cognition.litert_lm.worker import LiteRTRuntime
    import sys
    from types import ModuleType
    from sbd.cognition import observability
    from sbd.cognition.litert_lm import worker
    directory = tmp_path / "private-timing"
    directory.mkdir(mode=0o700)
    recorder = observability.PrivateTimingRecorder(directory)
    monkeypatch.setattr(observability, "_PRIVATE_TIMING_RECORDER", recorder)
    monkeypatch.setattr(worker, "_ACTIVE_TIMING_FRAME", {
        "request_id": 3, "session_id": "private-session", "generation": 1})
    io_counts = iter(({"major_fault_count": 5, "input_block_count": 10, "cpu_time_ns": 1_000_000},
                     {"major_fault_count": 8, "input_block_count": 42, "cpu_time_ns": 9_000_000}))
    monkeypatch.setattr(worker, "_native_request_counters", lambda: next(io_counts))

    package = ModuleType("litert_lm")
    package.__path__ = []
    ffi = ModuleType("litert_lm._ffi")
    ffi.STREAM_CALLBACK_TYPE = lambda callback: callback
    messages = ModuleType("litert_lm._messages")
    messages.normalize_message = lambda text: {
        "role": "user", "content": [{"type": "text", "text": text}]
    }
    monkeypatch.setitem(sys.modules, "litert_lm", package)
    monkeypatch.setitem(sys.modules, "litert_lm._ffi", ffi)
    monkeypatch.setitem(sys.modules, "litert_lm._messages", messages)

    wire = '{"text":"延後回覆。","end":false}'
    callback_thread = None

    class Lib:
        @staticmethod
        def litert_lm_stream_chunk_get_error(chunk):
            return chunk.get("error")

        @staticmethod
        def litert_lm_stream_chunk_get_text(chunk):
            value = chunk.get("text")
            return None if value is None else value.encode()

        @staticmethod
        def litert_lm_stream_chunk_is_final(chunk):
            return chunk["final"]

        @staticmethod
        def litert_lm_conversation_send_message_stream(
            pointer, message, context, optional, callback, data
        ):
            nonlocal callback_thread
            assert pointer == 1 and optional == "optional"

            def deliver():
                threading.Event().wait(0.02)
                callback(None, {"text": wire[:11], "final": False})
                callback(None, {"text": wire[11:], "final": False})
                callback(None, {"text": None, "final": True})

            callback_thread = threading.Thread(target=deliver)
            callback_thread.start()
            return 0

    class Conversation:
        automatic_tool_calling = False
        _ptr = 1
        _lib = Lib()
        extra_context = {}
        token_count = 105

        @staticmethod
        def _resolve_response_format(message, response_format):
            return response_format

        @staticmethod
        def _create_optional_args(**kwargs):
            assert kwargs["response_format"] == "json-constraint"
            return "optional"

        @staticmethod
        def _delete_optional_args(optional):
            assert optional == "optional"

        @staticmethod
        def get_benchmark_info():
            return SimpleNamespace(last_decode_token_count=9,
                                   last_prefill_token_count=83,
                                   last_prefill_tokens_per_second=83.0,
                                   last_decode_tokens_per_second=9.0,
                                   init_time_in_second=0.25,
                                   time_to_first_token_in_second=0.015)

    class ResponseFormat:
        @staticmethod
        def json(schema):
            assert schema == load_response_schema()
            return "json-constraint"

    runtime = LiteRTRuntime.__new__(LiteRTRuntime)
    runtime._conversation = Conversation()
    runtime._response_format = ResponseFormat
    runtime._pending_cancel = False
    runtime._active = None
    runtime._lock = threading.Lock()
    emitted = []

    semantic, decode, conversation, prefill = runtime.generate_stream(
        "問題", emitted.append
    )
    assert callback_thread is not None
    callback_thread.join()
    assert semantic.text == "延後回覆。" and semantic.end is False
    assert emitted == ["延後回覆。"]
    assert (decode, conversation, prefill) == (9, 105, 83)
    rows = [json.loads(line) for line in recorder.path.read_text().splitlines()]
    stages = {row["stage"]: row for row in rows}
    assert sum(row["stage"] == "first_generated_output" for row in rows) == 1
    assert all(row["request_id"] == 3 for row in rows)
    assert stages["response_format_begin"]["monotonic_ns"] <= stages["response_format_end"]["monotonic_ns"]
    assert stages["optional_args_begin"]["monotonic_ns"] <= stages["optional_args_end"]["monotonic_ns"]
    assert stages["native_submit_begin"]["monotonic_ns"] <= stages["native_submit_end"]["monotonic_ns"]
    assert stages["native_submit_end"]["monotonic_ns"] < stages["first_generated_output"]["monotonic_ns"]
    assert stages["native_benchmark"]["reported_init_ns"] == 250_000_000
    assert stages["native_benchmark"]["reported_ttft_ns"] == 15_000_000
    assert stages["native_benchmark"]["derived_prefill_ns"] == 1_000_000_000
    assert stages["native_benchmark"]["derived_decode_ns"] == 1_000_000_000
    assert stages["native_submit_begin"]["major_fault_count"] == 5
    assert stages["first_generated_output"]["major_fault_count"] == 8
    assert stages["first_generated_output"]["input_block_count"] == 42
    assert stages["first_generated_output"]["cpu_time_ns"] - stages["native_submit_begin"]["cpu_time_ns"] == 8_000_000
    assert "延後回覆" not in recorder.path.read_text()


def test_cache_prefetch_reads_once_without_changing_file_and_closes(tmp_path):
    from sbd.cognition.litert_lm.worker import WeightCachePrefetch
    cache = tmp_path / "weights.xnnpack_cache"
    data = b"cache" * 300_000
    cache.write_bytes(data)
    reader = WeightCachePrefetch(cache, {"request_id": 1, "session_id": "s", "generation": 1})
    reader.start()
    assert reader.done.wait(2)
    original_thread = reader.thread
    reader.start()
    reader.stop()
    assert reader.thread is original_thread and not reader.thread.is_alive()
    assert reader.status == "COMPLETED" and reader.bytes_read == len(data)
    assert cache.read_bytes() == data
    assert reader.done.is_set()


def test_cache_prefetch_missing_file_falls_back_without_generation_failure(tmp_path):
    from sbd.cognition.litert_lm.worker import WeightCachePrefetch
    reader = WeightCachePrefetch(tmp_path / "absent", {"request_id": 1, "session_id": "s", "generation": 1})
    reader.start()
    assert reader.done.wait(2)
    reader.stop()
    assert reader.status == "FAILED" and reader.bytes_read == 0
    assert not reader.thread.is_alive()


def test_cache_prefetch_shutdown_cancels_reader_and_closes_fd(tmp_path, monkeypatch):
    from sbd.cognition.litert_lm.worker import WeightCachePrefetch
    entered, release = threading.Event(), threading.Event()
    cache = tmp_path / "cache"
    cache.write_bytes(b"x" * 4096)
    source = cache.open("rb", buffering=0)
    class ControlledRead:
        def __enter__(self): return self
        def __exit__(self, *args): source.close()
        def fileno(self): return source.fileno()
        def read(self, size):
            entered.set()
            assert release.wait(2)
            return source.read(size)
    monkeypatch.setattr(type(cache), "open", lambda self, *args, **kw: ControlledRead())
    reader = WeightCachePrefetch(cache, {"request_id": 1, "session_id": "s", "generation": 1})
    reader.start()
    assert entered.wait(2)
    reader.cancelled.set()
    release.set()
    reader.stop()
    assert reader.status == "CANCELLED" and reader.done.is_set()
    assert not reader.thread.is_alive() and source.closed


def test_runtime_prefetch_is_engine_owned_once_and_never_waits_for_reader(tmp_path, monkeypatch):
    from sbd.cognition.litert_lm import worker
    model = tmp_path / "model.litertlm"
    cache = tmp_path / "model.litertlm_123_456.xnnpack_cache"
    monkeypatch.setattr(Path, "read_text", lambda *args, **kwargs:
        f"1000-2000 r--p 0000 00:00 1 {cache}\n")
    readers = []
    class Reader:
        def __init__(self, path, frame):
            self.path = path
            self.started = self.stopped = False
            readers.append(self)
        def start(self): self.started = True
        def stop(self): self.stopped = True
    monkeypatch.setattr(worker, "WeightCachePrefetch", Reader)
    class Conversation:
        def close(self): pass
    class Engine:
        def create_conversation(self, **kwargs): return Conversation()
        def close(self): pass
    runtime = worker.LiteRTRuntime.__new__(worker.LiteRTRuntime)
    runtime._model_path = model
    runtime._conversation = None
    runtime._cache_prefetch = None
    runtime._cache_prefetch_attempted = False
    runtime._engine = Engine()
    runtime._constraint = runtime._sampler_config = object()
    runtime.open_conversation()
    assert runtime._conversation is not None and len(readers) == 1 and readers[0].started
    runtime.close_conversation()
    assert not readers[0].stopped  # Conversation close retains the engine-owned read.
    runtime.open_conversation()
    assert len(readers) == 1
    runtime.close_conversation()
    runtime.close()
    assert readers[0].stopped
