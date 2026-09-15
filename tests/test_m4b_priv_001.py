"""M4B-PRIV-001 — scanner and sanitized protocol failures."""

from __future__ import annotations

from scripts.m4b_target_metrics import privacy_hits
from sbd.cognition.llm_child_protocol import LLMProtocolError
import base64
import json
import pytest
from sbd.cognition.observability import (PromptDashboard, ObservationError, TIMING_NODES,
    CognitionObserver, failure_row, memory_row, runtime_row, timing_row)
from tests.test_m4b_mem_001 import sample
import asyncio
import dataclasses
import inspect
from collections import deque
from pathlib import Path


def _live_product_canary_paths(canary, *roots):
    """Probe production-owned containers/frames, excluding test-owned inputs and observers."""
    seen, hits = set(), []
    def visit(value, path):
        if isinstance(value, (str, bytes)):
            needle = canary.encode() if isinstance(value, bytes) else canary
            if needle in value:
                hits.append(path)
            return
        if id(value) in seen:
            return
        seen.add(id(value))
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, f"{path}.{key}")
        elif isinstance(value, (tuple, list, set, frozenset, deque)):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")
        elif inspect.iscoroutine(value) or inspect.isgenerator(value):
            frame = getattr(value, "cr_frame", None) or getattr(value, "gi_frame", None)
            if frame is not None and "/src/sbd/" in frame.f_code.co_filename:
                visit(frame.f_locals, f"{path}.{frame.f_code.co_name}")
            visit(getattr(value, "cr_await", None) or getattr(value, "gi_yieldfrom", None), path + ".await")
        elif isinstance(value, asyncio.Task):
            visit(value.get_coro(), path + ".coroutine")
        elif inspect.isfunction(value):
            if value.__module__.startswith("sbd."):
                for name, cell in zip(value.__code__.co_freevars, value.__closure__ or ()):
                    try:
                        visit(cell.cell_contents, path + ".closure." + name)
                    except ValueError:
                        pass
        elif dataclasses.is_dataclass(value) and not isinstance(value, type):
            if type(value).__module__.startswith("sbd."):
                for field in dataclasses.fields(value):
                    visit(getattr(value, field.name), path + "." + field.name)
        elif type(value).__module__.startswith(("sbd.", "asyncio.")) and hasattr(value, "__dict__"):
            visit(vars(value), path)
    for index, root in enumerate(roots):
        visit(root, f"root{index}")
    for task in asyncio.all_tasks():
        visit(task, "task")
    return hits


async def _privacy_sm(adapter, canary):
    from sbd.cognition.prompt_builder import ListenProjector
    from sbd.cognition.reasoner import Reasoner
    from sbd.core.event_bus import EventBus
    from sbd.core.events import PerceptionResult
    from sbd.core.resource_manager.catalog import WorkerCatalog
    from sbd.core.state_manager.manager import StateManager
    from sbd.core.state_manager.session import SessionContext
    from tests.test_state_manager import Worker
    from tests.test_m2_wrk_003 import _validator
    bus = EventBus()
    reasoner = Reasoner(adapter, ListenProjector(), bus, {"listen", "speak"}.__contains__, _validator())
    catalog = WorkerCatalog()
    catalog.register_perception("listen", Worker(bus, "listen", "perception"))
    catalog.set_reasoner(reasoner)
    for kind in ("speak", "rest"):
        catalog.register_action(kind, Worker(bus, kind, "action"))
    catalog.seal()
    sm = StateManager(bus=bus, workers=catalog, action_validator=_validator())
    sm._session = SessionContext("session", "button", turn_id=1, selected_perceptions=("listen",),
        conversation_generation=1, conversation_state="ready", model_admission_blocked=False)
    sm._session.perception_results.append(PerceptionResult("listen", "ok", canary,
        session_id="session", turn_id=1))
    return sm, reasoner, bus


@pytest.mark.asyncio
async def test_V07_actual_sm_reasoner_releases_input_before_discard_and_r1(caplog):
    from tests.fakes.m4b_llm_child import adapter_fixture
    from sbd.core.events import LLMResponse, ErrorOccurred
    from sbd.cognition.llm_child_protocol import TICKET_SCRUB_TEXT
    canary = "拒絕輸入私密七"
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("session", 1)
    child = children[0]
    child.runtime.user_tokens = 33
    sm, reasoner, bus = await _privacy_sm(adapter, canary)
    entered, release, published = asyncio.Event(), asyncio.Event(), asyncio.Event()
    original = adapter.discard_ticket
    snapshots, responses, errors, probes = [], [], [], []
    async def discard(snapshot):
        snapshots.append(snapshot)  # The test owns this reference, not product state.
        probes.append(_live_product_canary_paths(canary, sm, reasoner, adapter))
        assert canary in child.runtime.scratch
        assert canary not in json.dumps(child.session.ledger.ticket)
        entered.set()
        await release.wait()
        return await original(snapshot)
    adapter.discard_ticket = discard
    async def on_response(response):
        probes.append(_live_product_canary_paths(canary, sm, reasoner, adapter,
                                                vars(child.runtime), vars(child.session.ledger)))
        responses.append(response)
        published.set()
    bus.subscribe(LLMResponse, on_response)
    async def on_error(error):
        errors.append(error)
    bus.subscribe(ErrorOccurred, on_error)
    try:
        await sm._enter_think()
        await asyncio.wait_for(entered.wait(), 1)
        assert sm._session.perception_results == [] and responses == []
        assert probes == [[]]
        release.set()
        await asyncio.wait_for(published.wait(), 1)
        await asyncio.gather(*(record.task for record in sm._in_flight.values()))
        assert probes == [[], []] and errors == []
        assert responses[0].action_payload == {"text": "這句有點長，請縮短後再說一次。"}
        assert child.runtime.sends == 0 and child.runtime.scrubs == 1
        assert child.runtime.scratch == "rendered:" + TICKET_SCRUB_TEXT
        assert adapter._ledger.ticket is None and child.session.ledger.ticket is None
        assert canary not in caplog.text
        assert all("text" not in command for command in child.commands)
    finally:
        release.set()
        await adapter.stop()


@pytest.mark.asyncio
async def test_V08_native_scrub_is_public_once_and_ticket_never_contains_raw_text():
    from tests.fakes.m4b_llm_child import adapter_fixture
    from sbd.cognition.llm_child_protocol import TICKET_SCRUB_TEXT
    from sbd.cognition.litert_lm.worker import LiteRTRuntime
    from types import SimpleNamespace
    canary = "私密內容八"
    adapter, children, _, _ = adapter_fixture()
    await adapter.start()
    await adapter.open_conversation("session", 1)
    child = children[0]
    snapshot = await adapter.measure("session", 1, canary)
    assert child.runtime.scratch == "rendered:" + canary
    assert canary not in json.dumps(vars(child.session.ledger), default=str)
    native = SimpleNamespace(token_count=0, last_rendered_message="rendered:" + canary)
    calls = []
    def render(text):
        calls.append(text)
        native.last_rendered_message = "rendered:" + text
        return native.last_rendered_message
    native.render_message_to_string = render
    runtime = LiteRTRuntime.__new__(LiteRTRuntime)
    runtime._conversation = native
    child.runtime.scrub_ticket = runtime.scrub_ticket
    proof = await adapter.discard_ticket(snapshot)
    assert proof.private_input_erased is True and proof.ticket_invalidated is True
    assert calls == [TICKET_SCRUB_TEXT] and native.last_rendered_message == "rendered:" + TICKET_SCRUB_TEXT
    assert native.token_count == 0 and child.runtime.sends == 0
    assert adapter._ledger.ticket is None and child.session.ledger.ticket is None
    await adapter.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["scrub", "false_proof", "missing_proof", "wrong_terminal", "wrong_ticket", "eof", "timeout"])
async def test_V09_disposal_failures_destroy_before_error_and_leave_no_live_canary(failure, caplog):
    from dataclasses import replace
    from tests.fakes.m4b_llm_child import adapter_fixture
    from sbd.core.events import LLMResponse, ErrorOccurred
    from sbd.cognition.llm import LLMFatalError
    canary = "錯誤私密九"
    adapter, children, _, _ = adapter_fixture()
    adapter._cfg = replace(adapter._cfg, terminal_grace_seconds=.02)
    await adapter.start()
    await adapter.open_conversation("session", 1)
    child = children[0]
    child.runtime.user_tokens = 33
    if failure == "scrub":
        def bad_scrub():
            raise RuntimeError("native scrub failed")
        child.runtime.scrub_ticket = bad_scrub
    def transform(event):
        if event["event"] != "TICKET_DISCARDED":
            return event
        if failure == "false_proof":
            return {**event, "private_input_erased": False}
        if failure == "missing_proof":
            return {key: value for key, value in event.items() if key != "private_input_erased"}
        if failure == "wrong_terminal":
            return {**event, "event": "RESULT"}
        if failure == "wrong_ticket":
            return {**event, "ticket": "0" * 32}
        if failure == "eof":
            raise EOFError
        if failure == "timeout":
            return []
        return event
    child.transform = transform
    sm, reasoner, bus = await _privacy_sm(adapter, canary)
    responses, errors = [], []
    async def on_response(response):
        responses.append(response)
    async def on_error(error):
        errors.append(error)
    bus.subscribe(LLMResponse, on_response)
    bus.subscribe(ErrorOccurred, on_error)
    await sm._enter_think()
    results = await asyncio.gather(*(record.task for record in sm._in_flight.values()), return_exceptions=True)
    assert len(results) == 1 and isinstance(results[0], LLMFatalError)
    assert responses == [] and len(errors) == 1
    assert child.terminated == 1 and child.runtime.scratch is None
    assert adapter._ledger.ticket is None and child.session.ledger.ticket is None
    assert _live_product_canary_paths(canary, sm, reasoner, adapter, vars(child.runtime)) == []
    assert canary not in caplog.text and canary not in repr(errors)
    assert all(command["op"] != "GENERATE" for command in child.commands)
    await adapter.stop()


def test_m4b_priv_001_scanner_detects_private_prompt_response_and_credentials() -> None:
    sentinels = ("PRIVATE_PROMPT", "PRIVATE_RESPONSE", b"PRIVATE_CREDENTIAL")
    blobs = [("one", b"PRIVATE_PROMPT"), ("two", b"PRIVATE_CREDENTIAL"), ("clean", b'{"status":"Pass"}')]
    assert privacy_hits(blobs, sentinels) == ["one", "two"]


def test_m4b_priv_001_protocol_exception_has_only_sanitized_fields() -> None:
    error = LLMProtocolError(stage="RESULT", field="response", reason="invalid")
    assert str(error) == "stage=RESULT field=response reason=invalid"


def test_V01_reversible_encoding_and_arbitrary_failure_detail_are_rejected():
    canary = b"PRIVATE_CANARY"
    assert privacy_hits([("b64", base64.b64encode(canary).rstrip(b"=")),
                         ("hex", canary.hex().upper().encode())],
                        [canary]) == ["b64", "hex"]
    with pytest.raises(ObservationError) as error:
        failure_row(code=canary.decode(), stage="GENERATE", request_id=1,
                    conversation_generation=1, cleanup_proven=True)
    assert canary.decode() not in str(error.value)


def test_V02_prompt_emits_once_and_is_separate_from_runtime():
    dashboard = PromptDashboard()
    args = dict(profile_id="core-m4b-cognition-001", counts={"core": 57, "personality": 9, "combined": 66},
        hashes={"core": "8caba35159407882407c1ac1be22c66791ac66236e323bc1b63fa072c1340eec",
        "personality": "57191898561df177e820a10eed88ad9d47649ba9e5e19c059b554acedda777e5",
        "combined": "872ae6b6418761b271cd6762c08eeaabe1f20d3a1c4aa72602a09eab1f1eb643"})
    row = dashboard.record(**args)
    assert len(row) == 7 and row["combined_tokens"] == 66
    assert dashboard.record(**args) is None
    assert "prompt" not in row and "text" not in row


def test_V03_runtime_checks_exact_equation_and_no_private_extra_fields():
    values = dict(conversation_generation=1, turn_index=1, input_codepoints=3, user_tokens=4,
        current_kv_tokens=66, rendered_incremental_tokens=10, runtime_prefill_tokens=76,
        output_reserve_tokens=128, projected_total_tokens=204, admission_result="GENERATE",
        decode_tokens=4, terminal_conversation_kv_tokens=80)
    assert runtime_row(values) == values
    with pytest.raises(ObservationError):
        runtime_row({**values, "projected_total_tokens": 205})
    with pytest.raises(ObservationError):
        runtime_row({**values, "text": "PRIVATE_CANARY"})


def test_V04_memory_rows_do_not_add_conversation_delta():
    row = memory_row(sample(), conversation_generation=1, lifecycle_point="conversation_ready")
    assert row["combined_pss_bytes"] == 50 and row["system_used_bytes"] == 1000
    assert set(row["owners"]) == {"core", "vad", "asr", "tts", "llm"}
    assert "delta" not in json.dumps(row) and "private" not in json.dumps(row)


def test_V05_one_clock_requires_explicit_null_reason_and_order():
    events = dict(zip(TIMING_NODES, [1, 2, 3, None, 5, None, None], strict=True))
    reasons = {"first_safe_text": "NOT_OBSERVED", "tts_pcm_ready": "NOT_APPLICABLE",
               "audio_first_write": "NOT_APPLICABLE"}
    row = timing_row(clock_domain="controller_monotonic", events=events, null_reasons=reasons)
    assert row["events"]["audio_first_write"] == {"monotonic_ns": None, "null_reason": "NOT_APPLICABLE"}
    for bad in (dict(clock_domain="wall_clock", events=events, null_reasons=reasons),
                dict(clock_domain="controller_monotonic", events=events, null_reasons={}),
                dict(clock_domain="controller_monotonic", events={**events, "asr_final": 0}, null_reasons=reasons)):
        with pytest.raises(ObservationError):
            timing_row(**bad)


def test_V02_V03_V05_live_observer_retains_only_counters_and_controller_clock():
    from sbd.cognition.llm import AdmissionSnapshot, GenerationMetrics
    rows = []
    clock = iter(range(100, 120))
    observer = CognitionObserver(sink=rows.append, clock=lambda: next(clock))
    profile = json.loads(Path("requirements/m4b/product-profile.json").read_text())
    observer.prompt(profile)
    observer.prompt(profile)
    observer.conversation_ready(2)
    observer.mark("asr_final")
    observer.begin_turn(2, 3, 4)
    snapshot = AdmissionSnapshot("PRIVATE_CANARY", "PRIVATE_CANARY", 2, "PRIVATE_CANARY",
                                 4, 66, 10, 76, 128, 1024)
    observer.measured(snapshot)
    observer.mark("llm_send")
    observer.mark("llm_terminal")
    observer.generated(GenerationMetrics(4, 66, 10, 76, 5, 81, 999999, 999998, 999997))
    observer.mark("tts_pcm_ready")
    observer.mark("audio_first_write")
    observer.outcome("GENERATE")
    observer.finish()
    observer.finish()
    assert [row["dashboard"] for row in rows] == ["prompt", "runtime", "timing"]
    assert rows[1]["values"]["projected_total_tokens"] == 204
    assert rows[1]["values"]["terminal_conversation_kv_tokens"] == 81
    events = rows[2]["values"]["events"]
    assert events["asr_final"]["monotonic_ns"] == 101
    assert events["llm_terminal"]["monotonic_ns"] == 103
    assert events["first_safe_text"] == {"monotonic_ns": None, "null_reason": "NOT_OBSERVED"}
    assert "PRIVATE_CANARY" not in repr(vars(observer)) + json.dumps(rows)
    assert "99999" not in json.dumps(rows)


def test_V03_live_unmeasured_turn_has_null_counters_not_fabricated_zero():
    rows = []
    observer = CognitionObserver(sink=rows.append, clock=lambda: 10)
    observer.conversation_ready(1)
    observer.begin_turn(1, 1, 21)
    observer.outcome("R1")
    observer.finish("NOT_APPLICABLE")
    runtime = rows[0]
    assert runtime["values"]["user_tokens"] is None
    assert runtime["null_reasons"]["user_tokens"] == "NOT_APPLICABLE"
    assert runtime["values"]["input_codepoints"] == 21
    assert runtime["values"]["admission_result"] == "R1"


def test_V05_native_mapping_cannot_mix_an_injected_controller_clock():
    rows = []
    observer = CognitionObserver(sink=rows.append, clock=lambda: 100)
    observer.conversation_ready(1)
    observer.begin_turn(1, 1)
    observer.native_timing(llm_send=101, llm_terminal=105, clock_mapped=True)
    observer.finish()
    events = rows[-1]["values"]["events"]
    assert events["llm_send"] == events["llm_terminal"] == {
        "monotonic_ns": None, "null_reason": "NOT_OBSERVED"}


def test_V01_default_observer_log_is_allowlisted(caplog):
    import logging
    observer = CognitionObserver(clock=lambda: 10)
    with caplog.at_level(logging.INFO, logger="sbd.cognition.observation"):
        observer.conversation_ready(1)
        observer.begin_turn(1, 1)
        observer.outcome("E1")
        observer.finish("FAILED")
    rows = [json.loads(record.message) for record in caplog.records]
    assert [row["dashboard"] for row in rows] == ["runtime", "timing"]
    assert set(rows[0]["values"]) == set(runtime_row.__globals__["RUNTIME_FIELDS"])


def test_V01_observer_sink_failure_traceback_does_not_expose_private_exception():
    import traceback
    def broken_sink(row):
        raise RuntimeError("PRIVATE_CANARY")
    observer = CognitionObserver(sink=broken_sink)
    observer.begin_turn(1, 1)
    with pytest.raises(ObservationError) as error:
        observer.finish("FAILED")
    assert "PRIVATE_CANARY" not in "".join(traceback.format_exception(error.value))
    assert error.value.__suppress_context__


def test_V05_replacement_ready_preserves_current_turn_clock_and_seeds_next_turn():
    rows = []
    stamps = iter(range(10, 20))
    observer = CognitionObserver(sink=rows.append, clock=lambda: next(stamps))
    observer.conversation_ready(1)
    observer.mark("asr_final")
    observer.begin_turn(1, 1, 2)
    observer.conversation_ready(2)
    observer.outcome("R2")
    observer.mark("tts_pcm_ready")
    observer.finish()
    assert rows[-1]["values"]["events"]["conversation_ready"]["monotonic_ns"] == 10
    observer.mark("asr_final")
    observer.begin_turn(2, 2, 2)
    observer.outcome("R1")
    observer.finish()
    assert rows[-1]["values"]["events"]["conversation_ready"]["monotonic_ns"] == 12


@pytest.mark.asyncio
async def test_V05_actual_listener_boundary_observes_final_once_without_payload():
    from sbd.perception.listen.listener import Listen
    from sbd.perception.listen.asr import ASRResult, MockASRAdapter
    ledger = []
    class Input:
        async def frames(self):
            yield b"pcm"
    class Bus:
        async def publish(self, event):
            ledger.append("published")
    listener = Listen(audio_input=Input(), asr=MockASRAdapter((ASRResult("PRIVATE_CANARY"),)),
                      bus=Bus(), observe=ledger.append)
    await listener.perceive("PRIVATE_SESSION", 1, 1, 1)
    assert ledger == ["asr_final", "published"]


@pytest.mark.asyncio
async def test_V05_actual_speaker_first_nonempty_pcm_and_completion_close_source():
    from sbd.action.speak.speaker import Speak
    ledger = []
    class TTS:
        async def synthesize(self, text):
            try:
                yield b""
                yield b"12"
                yield b"34"
            finally:
                ledger.append("source_closed")
    class Output:
        async def play(self, pcm):
            async for chunk in pcm:
                ledger.append(("play", len(chunk)))
    class Bus:
        async def publish(self, event):
            ledger.append("published")
    speaker = Speak(tts=TTS(), audio_output=Output(), bus=Bus(), observe=ledger.append,
                    on_completion=lambda status: ledger.append(("complete", status)))
    await speaker.execute("PRIVATE_SESSION", 1, 1, {"text": "PRIVATE_CANARY"})
    assert ledger == [("play", 0), "tts_pcm_ready", ("play", 2), ("play", 2),
                      "source_closed", ("complete", "ok"), "published"]
    assert speaker._pcm is None


@pytest.mark.asyncio
async def test_V05_speaker_observation_preserves_cancel_and_async_completion_barriers():
    from sbd.action.speak.speaker import Speak
    ledger = []
    entered, held, completion_entered, release_completion = (asyncio.Event() for _ in range(4))
    class TTS:
        async def synthesize(self, text):
            try:
                entered.set()
                yield b"12"
                await held.wait()
            finally:
                ledger.append("source_closed")
        async def abort(self):
            ledger.append("abort")
    class Output:
        async def play(self, pcm):
            async for chunk in pcm:
                pass
    class Bus:
        async def publish(self, event):
            ledger.append("forbidden_publish")
    async def before_start():
        ledger.append("pre_speak")
    async def completed(status):
        ledger.append(status)
        completion_entered.set()
        await release_completion.wait()
    speaker = Speak(tts=TTS(), audio_output=Output(), bus=Bus(), observe=ledger.append,
                    before_start=before_start, on_completion=completed)
    running = asyncio.create_task(speaker.execute("PRIVATE_SESSION", 1, 1, {"text": "PRIVATE_CANARY"}))
    await asyncio.wait_for(entered.wait(), 1)
    abort = asyncio.create_task(speaker.abort())
    await asyncio.wait_for(completion_entered.wait(), 1)
    assert not abort.done() and not running.done()
    assert ledger == ["pre_speak", "tts_pcm_ready", "abort", "source_closed", "cancelled"]
    release_completion.set()
    await asyncio.wait_for(asyncio.gather(abort, running), 1)
    assert "forbidden_publish" not in ledger and speaker._pcm is None


@pytest.mark.asyncio
async def test_V01_completion_callback_failure_reaches_worker_supervision():
    from sbd.action.speak.speaker import Speak
    from sbd.core.events import ErrorOccurred
    events = []
    class TTS:
        async def synthesize(self, text):
            yield b"12"
    class Output:
        async def play(self, pcm):
            async for chunk in pcm:
                pass
    class Bus:
        async def publish(self, event):
            events.append(event)
    async def failed(status):
        raise ObservationError()
    speaker = Speak(tts=TTS(), audio_output=Output(), bus=Bus(), on_completion=failed)
    with pytest.raises(ObservationError):
        await speaker.execute("PRIVATE_SESSION", 1, 1, {"text": "PRIVATE_CANARY"})
    assert len(events) == 1 and isinstance(events[0], ErrorOccurred)
    assert "PRIVATE_CANARY" not in repr(events) and speaker._pcm is None


@pytest.mark.parametrize("writes,expected", [([1, 1], ["audio_first_write"]), ([0], []), ([-2], [])])
def test_V05_native_audio_write_observation_only_after_positive_valid_write(writes, expected):
    from sbd.core.audio.alsa.output import AlsaAudioOutput
    from tests.test_m3_audo_001_002_003_004_005_006_007 import _passthrough_config
    observed = []
    values = iter(writes)
    class PCM:
        def write(self, chunk):
            return next(values)
    output = AlsaAudioOutput(_passthrough_config(), observe=observed.append)
    output._pcm = PCM()
    if writes[0] > 0:
        output._write_worker(bytes(16))
    else:
        with pytest.raises(OSError):
            output._write_worker(bytes(16))
    assert observed == expected
