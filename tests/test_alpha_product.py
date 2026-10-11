"""Portable ALPHA driver regressions; these do not claim native Pi acceptance."""
import asyncio
import json
import sys
from types import SimpleNamespace as NS
import wave

import pytest

from scripts.alpha_product import ProductProbe, resolve_fixtures, session_plan
from scripts.alpha_oracle import InvalidObservation
from sbd.core.event_bus import EventBus
from sbd.core.events import ButtonPressed, ShutdownRequested
from sbd.core.gpio.base import GPIOEvent
from sbd.input_events.button import ButtonInputSource


def test_realtime_pcm_records_schedule_padding_and_speech_boundary():
    from scripts.alpha_product import paced_pcm, FRAME_NS
    async def scenario():
        now = 1_000_000_000
        def clock():
            return now
        async def sleep(seconds):
            nonlocal now
            now += round(seconds * 1_000_000_000)
        observation = {}
        frames = [frame async for frame in paced_pcm(b"\1\0" * 321 + b"\0" * 640,
                  observation, clock=clock, sleep=sleep)]
        assert len(frames) == 3 and all(len(frame) == 640 for frame in frames)
        assert frames[1] == b"\1\0" + b"\0" * 638
        assert observation["complete"] is True
        assert [row["delivered_ns"] for row in observation["frames"]] == [
            1_000_000_000 + index * FRAME_NS for index in range(3)]
        assert observation["speech_end_ns"] == 1_000_000_000 + 2 * FRAME_NS
        assert observation["delivery_span_error_ns"] == 0
    asyncio.run(scenario())


def test_realtime_pcm_retains_stall_and_never_bursts_to_catch_up():
    from scripts.alpha_product import paced_pcm, FRAME_NS
    async def scenario():
        now = 1_000_000_000
        def clock(): return now
        async def sleep(seconds):
            nonlocal now
            now += round(seconds * 1_000_000_000)
        observation = {}
        source = paced_pcm(b"\1\0" * 960, observation, clock=clock, sleep=sleep)
        assert len(await anext(source)) == 640
        now += 3 * FRAME_NS  # Actual consumer stalled for multiple frames.
        with pytest.raises(InvalidObservation, match="PACING_DISTORTED"):
            await anext(source)
        assert len(observation["frames"]) == 2
        assert observation["frames"][-1]["lateness_ns"] == 2 * FRAME_NS
        assert observation["complete"] is False
    asyncio.run(scenario())


def test_human_probe_preserves_live_microphone_frames(capsys):
    async def scenario():
        probe = ProductProbe("ph", {}, 1)
        probe.sm = NS(_session=NS(session_id="human", turn_id=1))
        probe.pending.append(("PH02", "FX-SHORT-B", "KEEP_NEXT"))
        calls = []
        async def microphone():
            calls.append("actual input")
            yield b"\2\0" * 320
            yield b"\3\0" * 320
        probe.live_frames = microphone
        frames = [frame async for frame in probe.frames()]
        assert calls == ["actual input"]
        assert frames == [b"\2\0" * 320, b"\3\0" * 320]
        assert "speech_end" not in probe.rows[0]["nodes"]
        assert probe.rows[0]["capture_closed"] is True
    asyncio.run(scenario())
    assert "ALPHA_GUIDE SAY FX-SHORT-B" in capsys.readouterr().out


def test_human_probe_releases_live_microphone_after_early_asr_stop():
    async def scenario():
        probe = ProductProbe("ph", {}, 1)
        probe.sm = NS(_session=NS(session_id="human", turn_id=1))
        probe.pending.extend((("PH02", "FX-SHORT-B", "KEEP_NEXT"),
                              ("PH04", "FX-FOLLOW-UP", "KEEP_NEXT")))
        active = False

        async def microphone():
            nonlocal active
            assert not active
            active = True
            try:
                yield b"\2\0" * 320
                yield b"\3\0" * 320
            finally:
                active = False

        probe.live_frames = microphone
        first = probe.frames()
        assert await anext(first) == b"\2\0" * 320
        await first.aclose()
        assert not active
        probe.sm._session.turn_id = 2
        second = probe.frames()
        assert await anext(second) == b"\2\0" * 320
        await second.aclose()
        assert not active

    asyncio.run(scenario())


def test_batch_audio_writes_are_observed_under_real_volume_wrapper():
    from scripts.alpha_product import observe_audio_output
    from sbd.core.audio.volume import VolumeControlledAudioOutput
    async def scenario():
        writes, observed = [], []
        class Native:
            def __init__(self): self._observe = observed.append
            async def start(self): pass
            async def stop(self): pass
            async def play(self, pcm):
                async for chunk in pcm:
                    self._observe("audio_first_write")
                    writes.append(chunk)
        native = Native()
        output = VolumeControlledAudioOutput(native, 100)
        probe = ProductProbe("pn", {}, 1)
        probe.sm = NS(_session=object())
        first, second = {"sequence": 0, "tts_start": 1}, {"sequence": 1}
        probe.current = {"fragments": [first, second]}
        observe_audio_output(output, probe)
        async def pcm(): yield b"\1\0" * 320
        await output.play(pcm())
        assert first["audio_start"] <= first["audio_first_write"] <= first["audio_complete"]
        assert "audio_first_write" not in second
        second["tts_start"] = first["audio_complete"]
        await output.play(pcm())
        assert second["audio_start"] <= second["audio_first_write"] <= second["audio_complete"]
        assert first["audio_complete"] <= second["audio_first_write"]
        assert observed == ["audio_first_write"] * 2
        assert writes == [b"\1\0" * 320] * 2
    asyncio.run(scenario())


def test_private_timing_retains_complete_rows_and_rejects_content(tmp_path, monkeypatch):
    from sbd.cognition import observability
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    recorder = observability.PrivateTimingRecorder(directory)
    monkeypatch.setattr(observability, "_PRIVATE_TIMING_RECORDER", recorder)
    frame = {"request_id": 3, "session_id": "session-" + "a" * 700, "generation": 1}
    observability.private_timing("native_generation_start", frame, 100,
        user_tokens=3, current_kv_tokens=7, rendered_incremental_tokens=12, runtime_prefill_tokens=12)
    observability.private_timing("child_safe_text_emit", frame, 200, sequence=0, output_codepoints=5)
    observability.private_startup_timing("engine_init_begin", 50)
    observability.private_startup_timing("engine_init_end", 90)
    rows = [json.loads(line) for line in recorder.path.read_text().splitlines()]
    assert [row["monotonic_ns"] for row in rows] == [100, 200]
    assert all(row["session_id"] == frame["session_id"] for row in rows)
    assert recorder.path.stat().st_mode & 0o777 == 0o600
    startup_path = recorder.path.with_name(recorder.path.name.replace("timing-", "startup-timing-"))
    assert [json.loads(line)["monotonic_ns"] for line in startup_path.read_text().splitlines()] == [50, 90]
    with pytest.raises(observability.ObservationError):
        observability.private_timing("child_safe_text_emit", frame, 300, text="private speech")
    assert len(recorder.path.read_text().splitlines()) == 2


def test_parent_timing_observes_actual_wire_send_and_receive(tmp_path, monkeypatch):
    from sbd.cognition import observability
    from sbd.cognition.litert_lm.adapter import SubprocessLLMChild
    from sbd.cognition.llm_child_protocol import encode_frame
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    recorder = observability.PrivateTimingRecorder(directory)
    monkeypatch.setattr(observability, "_PRIVATE_TIMING_RECORDER", recorder)
    async def scenario():
        class Writer:
            def write(self, raw): self.raw = raw
            async def drain(self): pass
        reader, writer = asyncio.StreamReader(), Writer()
        child = SubprocessLLMChild(None, None, 1)
        child._process = NS(stdin=writer, stdout=reader, returncode=None)
        frame = {"protocol": 3, "op": "GENERATE", "request_id": 3,
                 "session_id": "private-session", "generation": 1}
        await child.send(frame)
        assert json.loads(writer.raw)["request_id"] == 3
        reader.feed_data(encode_frame({"protocol": 3, "event": "SAFE_TEXT",
            "request_id": 3, "sequence": 0, "text": "private answer", "monotonic_ns": 10}))
        assert (await child.receive())["text"] == "private answer"
        reader.feed_data(encode_frame({"protocol": 3, "event": "RESULT", "request_id": 3}))
        await child.receive()
    asyncio.run(scenario())
    rows = [json.loads(line) for line in recorder.path.read_text().splitlines()]
    assert [row["stage"] for row in rows] == ["parent_request_send", "parent_safe_text_receive",
                                             "parent_terminal_receive"]
    assert all(row["request_id"] == 3 and row["session_id"] == "private-session" for row in rows)
    assert rows[0]["monotonic_ns"] <= rows[1]["monotonic_ns"] <= rows[2]["monotonic_ns"]
    assert "private answer" not in recorder.path.read_text()


def test_recovery_retains_real_process_proof_after_child_cleanup(monkeypatch):
    from scripts.alpha_product import process_reaped

    async def scenario():
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", "import time; time.sleep(30)")
        child = NS(_process=process)
        retained = child._process
        try:
            assert not process_reaped(retained)
            process.kill()
            await process.wait()
            child._process = None  # Production cleanup clears this field after waitpid.
            assert not process_reaped(child._process)
            assert process_reaped(retained)
            monkeypatch.setattr("scripts.alpha_product.process_identity", lambda pid: ("live", "pid"))
            assert not process_reaped(retained)
        finally:
            if process.returncode is None:
                process.kill()
            await process.wait()

    asyncio.run(scenario())


def test_privacy_observes_actual_file_logs_without_short_answer_false_positive(tmp_path):
    import logging
    from scripts.alpha_product import PublicLogObservation
    observer = PublicLogObservation()
    handler = logging.FileHandler(tmp_path / "product.log")
    turns = [{"responses": [{"payload": {"text": "2"}}],
              "asr": [{"text": "私密提問內容"}]}]
    try:
        observer.handle(handler, logging.LogRecord("app", 20, "", 0, "L2-T1 completed", (), None))
        assert observer.matches(turns) == 0
        observer.handle(handler, logging.LogRecord("app", 20, "", 0, "ASR: 私密提問內容", (), None))
        observer.handle(handler, logging.LogRecord("app", 20, "", 0, "2", (), None))
        observer.handle(handler, logging.LogRecord("app", 20, "", 0, '{"password":"secret"}', (), None))
        assert observer.matches(turns) == 3
        assert "私密提問內容" in (tmp_path / "product.log").read_text()
    finally:
        handler.close()


def test_privacy_scans_formatted_unicode_and_not_redacted_secrets(tmp_path):
    import logging
    from scripts.alpha_product import PublicLogObservation
    from sbd.core.logger import SbdJsonFormatter
    observer = PublicLogObservation()
    observer.secrets.append("private-credential-value")
    handler = logging.FileHandler(tmp_path / "product.jsonl")
    handler.setFormatter(SbdJsonFormatter())
    try:
        observer.handle(handler, logging.LogRecord("app", 20, "", 0, "私密提問內容", (), None))
        assert observer.matches([{"asr": [{"text": "私密提問內容"}]}]) == 1
        observer.handle(handler, logging.LogRecord("app", 20, "", 0, "private-credential-value", (), None))
        assert observer.matches([]) == 1
    finally:
        handler.close()


def wav_file(path, *, rate=16000, channels=1, payload=b"\1\0" * 321):
    with wave.open(str(path), "wb") as sink:
        sink.setnchannels(channels)
        sink.setsampwidth(2)
        sink.setframerate(rate)
        sink.writeframes(payload)


def test_fixture_binding_is_shared_and_not_reread(tmp_path):
    pcm = tmp_path / "short.wav"
    wav_file(pcm)
    mapping = tmp_path / "fixtures.json"
    mapping.write_text(json.dumps({"FX-SHORT-B": "short.wav"}))
    resolved = resolve_fixtures(mapping, {"FX-SHORT-B"})
    before = resolved["FX-SHORT-B"]
    wav_file(pcm, payload=b"\2\0" * 321)
    # P02/P03 use the same in-memory binding despite later on-disk mutation.
    assert resolved["FX-SHORT-B"] is before
    assert resolved["FX-SHORT-B"] != pcm.read_bytes()


@pytest.mark.parametrize("rate,channels", [(48000, 1), (16000, 2)])
def test_pcm_requires_actual_asr_frame_format(tmp_path, rate, channels):
    wav_file(tmp_path / "input.wav", rate=rate, channels=channels, payload=b"\1\0" * 640)
    mapping = tmp_path / "fixtures.json"
    mapping.write_text(json.dumps({"FX-SHORT-A": "input.wav"}))
    with pytest.raises(InvalidObservation, match="FIXTURE_FORMAT_INVALID"):
        resolve_fixtures(mapping, {"FX-SHORT-A"})


def test_fixed_pcm_turn_consumption_is_once_and_padded_to_real_asr_frames():
    async def scenario():
        probe = ProductProbe("lifecycle", {"FX-SHORT-A": b"\1\0" * 321}, 1)
        probe.sm = NS(_session=NS(session_id="private", turn_id=1))
        probe.pending.append(("L1-T1", "FX-SHORT-A", "KEEP_NEXT"))
        stream = probe.frames()
        frames = [frame async for frame in stream]
        assert [len(frame) for frame in frames] == [640, 640]
        assert frames[0] == b"\1\0" * 320
        assert frames[1] == b"\1\0" + b"\0" * 638
        assert probe.rows[0]["capture_closed"] is True
        assert probe.rows[0]["nodes"]["speech_end"] > 0
        assert not probe.pending
        with pytest.raises(InvalidObservation, match="UNPLANNED_TURN"):
            await anext(probe.frames())
    asyncio.run(scenario())


def test_driver_uses_real_button_policy_for_start_and_graceful_shutdown():
    async def scenario():
        bus = EventBus()
        events = []
        async def observe(event):
            events.append(event)
        bus.subscribe(ButtonPressed, observe, name="alpha.test.button")
        bus.subscribe(ShutdownRequested, observe, name="alpha.test.shutdown")
        config = NS(conversation_pin="conversation", short_press_min_ms=50, long_press_min_ms=1500)
        source = ButtonInputSource(gpio=None, bus=bus, config=config,
                                  pin_config=NS(pin=23, active_low=True))
        source._started = source._armed = True
        probe = ProductProbe("lifecycle", {}, 1)
        probe.composition = NS(button=source)
        await probe.button()
        await probe.button(shutdown=True)
        assert events == [ButtonPressed("conversation", 50), ShutdownRequested()]
        assert probe.buttons == 1
    asyncio.run(scenario())


def test_input_limit_or_missing_llm_never_earns_pipeline_credit():
    probe = ProductProbe("quality", {}, 1)
    probe.composition = NS(action_validator=NS(validate=lambda *args: None))
    row = {"case_id": "ALPHA-Q04-INSTRUCTION", "fixture_id": "FX-Q04",
           "expected_route": "KEEP_NEXT", "asr": [{"status": "ok", "text": "private input"}],
           "responses": [{"kind": "speak", "payload": {"text": "private input-limit reply"},
                          "route": "KEEP_NEXT"}], "actions": [{"kind": "speak", "status": "ok"}],
           "runtime": [{"admission_result": "R1"}], "delivered": ["private input-limit reply"]}
    probe.rows = [row]
    probe.finish_turns()
    assert row["asr_terminal"] is True
    assert row["speech_equal"] is True
    assert row["audio_complete"] is True
    assert row["llm_terminal"] is False


def test_performance_plan_keeps_close_turns_outside_case_views():
    plan = session_plan("performance")
    assert [[row[0] for row in session] for session in plan] == [
        ["P02-FIRST-TURN", "P04-FOLLOW-UP", "CLOSE"],
        ["P03-WARM-SESSION", "P05-STREAMING", "CLOSE"]]
    assert plan[0][0][1] == plan[1][0][1] == "FX-SHORT-B"


def test_quality_fixed_case_order_and_context_turns():
    plan = session_plan("quality")
    assert len(plan) == 6
    assert [row[1] for row in plan[4]] == ["FX-Q05-T1", "FX-Q05-T2"]
    assert [row[1] for row in plan[5]] == ["FX-Q06-T1", "FX-Q06-T2"]
    assert plan[5][0][2] == "KEEP_NEXT" and plan[5][1][2] == "END_SESSION"


def test_fixture_preparation_binds_once_and_outputs_real_asr_format(tmp_path, monkeypatch):
    from scripts.alpha_product import FIXTURE_TEXT, prepare_fixtures, quality_revision
    calls = []
    class TTS:
        async def start(self): pass
        async def stop(self): pass
        def synthesize(self, text):
            calls.append(text)
            async def pcm():
                yield b"\1\0" * 320
            return pcm()
    monkeypatch.setattr("sbd.core.config.load_config", lambda **kw: NS(action=NS(tts=NS(driver="sherpa_matcha"))))
    monkeypatch.setattr("sbd.action.speak.make_tts_adapter", lambda cfg: TTS())
    destination = tmp_path / "fixed-pcm"
    asyncio.run(prepare_fixtures(tmp_path / "config.yaml", destination))
    mapping_path = destination / "fixtures.json"
    mapping = json.loads(mapping_path.read_text())
    assert set(mapping) == set(FIXTURE_TEXT)
    assert len(calls) == len(set(FIXTURE_TEXT.values()))
    assert mapping["FX-SHORT-A"] == mapping["FX-SHORT-B"]
    assert mapping["FX-SHORT-B"] != mapping["FX-Q02"]
    assert mapping["FX-NORMAL-END"] != mapping["FX-Q06-T2"]
    resolved = resolve_fixtures(mapping_path, set(FIXTURE_TEXT))
    assert resolved["FX-SHORT-A"] == b"\0" * 16000 + b"\1\0" * 320 + b"\0" * 32000
    assert mapping_path.stat().st_mode & 0o777 == 0o600
    assert quality_revision(mapping_path) == "Q-20261011"
    metadata_path = destination / "fixture-metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["quality_bindings"]["FX-Q02"]["text"] = "一個星期有幾天？"
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(InvalidObservation, match="QUALITY_FIXTURE_REVISION_INVALID"):
        quality_revision(mapping_path)


@pytest.mark.parametrize("run,completed_before_observation", [
    ("lifecycle", False), ("lifecycle", True), ("quality", False), ("pn", False),
])
def test_probe_drives_actual_listen_reasoner_streaming_and_cleanup(run, completed_before_observation):
    """Actual controller/worker integration, with explicit portable backend doubles."""
    from sbd.action.rest import Rest
    from sbd.action.speak import Speak
    from sbd.action.speak.tts import MockTTSAdapter
    from sbd.cognition.observability import CognitionObserver
    from sbd.cognition.prompt_builder import ListenProjector
    from sbd.cognition.reasoner import Reasoner
    from sbd.core.display import DisplayArbiter
    from sbd.core.display.status_bar import StatusBar
    from sbd.core.display.session import SessionDisplay
    from sbd.core.resource_manager.catalog import WorkerCatalog
    from sbd.core.state_manager import StateManager
    from sbd.perception.listen.listener import Listen
    from sbd.perception.listen.asr import MockASRAdapter, ASRResult
    from tests.test_m4c_s02_tryrun import _ProductLLM, _Display, _Renderer, MockAudioOutput
    from tests.test_m2_wrk_003 import _validator

    async def scenario():
        plan = session_plan(run)
        probe = ProductProbe(run, {fixture: b"\1\0" * 320 for session in plan
                                  for _, fixture, _ in session}, 1)
        if run == "pn":
            probe.pcm_pacing = "realtime"
        bus = EventBus()
        observer = CognitionObserver()

        class LLM(_ProductLLM):
            def __init__(self):
                super().__init__()
                self._ledger = NS(claim=None)
            async def open_conversation(self, sid, generation):
                self._ledger.claim = (sid, generation)
                self.conversation_revision = 0
                observer.conversation_ready(generation)
                return await super().open_conversation(sid, generation)
            async def close_conversation(self, sid, generation, reason):
                result = await super().close_conversation(sid, generation, reason)
                self._ledger.claim = None
                probe.close_counts[sid] = probe.close_counts.get(sid, 0) + 1
                return result

        llm = LLM()
        tts = MockTTSAdapter()
        synthesize = tts.synthesize
        def observed_synthesize(text):
            probe.current["delivered"].append(text)
            return synthesize(text)
        tts.synthesize = observed_synthesize
        async def completion(status):
            observer.finish("NOT_OBSERVED" if status == "ok" else "FAILED")
        speak = Speak(tts=tts, audio_output=MockAudioOutput(), bus=bus,
                      observe=observer.mark, on_completion=completion)
        reasoner = Reasoner(llm, ListenProjector(), bus, {"listen", "speak"}.__contains__,
                            _validator(), observer=observer, streaming_speak=speak)
        asr = MockASRAdapter(tuple(ASRResult("請結束對話。" if route == "END_SESSION" else "天空為什麼是藍色的？")
                                  for session in plan for _, _, route in session))
        listen = Listen(audio_input=NS(frames=probe.frames), asr=asr, bus=bus, observe=observer.mark)
        catalog = WorkerCatalog()
        catalog.register_perception("listen", listen)
        catalog.set_reasoner(reasoner)
        catalog.register_action("speak", speak)
        catalog.register_action("rest", Rest(bus=bus))
        catalog.seal()
        sm = StateManager(bus=bus, workers=catalog, wake_ack_seconds=0.001)
        display = DisplayArbiter(_Display(), _Renderer())
        status = StatusBar(display, bus)
        session_display = SessionDisplay(display, bus, sm)
        button_config = NS(conversation_pin="conversation", short_press_min_ms=50, long_press_min_ms=1500)
        button = ButtonInputSource(gpio=None, bus=bus, config=button_config,
                                  pin_config=NS(pin=23, active_low=True))
        button._started = button._armed = True
        composition = NS(button=button, _cognition_observer=observer,
                         _speak_worker=speak, action_validator=_validator())
        records = {key: NS(instance=value, started=True, using_null=False, spec=NS(required=True, key=key))
                   for key, value in {"core.display.arbiter": display,
                                      "backend.cognition.reasoner.llm": llm}.items()}
        rm = NS(_state_manager=sm, _records=records)
        config = NS(core=NS(audio=NS(driver="alsa"), gpio=NS(driver="gpiod"),
                            display=NS(driver="ssd1351", show_session_content=True)),
                    perception=NS(listen=NS(adapter=NS(driver="whispercpp"))),
                    cognition=NS(llm=NS(driver="litert_lm")),
                    action=NS(tts=NS(driver="sherpa_matcha")),
                    input_sources=NS(button=NS(policy=NS(enabled=True))))
        probe.attach(composition, rm, bus, config)
        probe.initial_pids = set()
        if completed_before_observation:
            send_button = probe.button
            async def settled_button(*, shutdown=False):
                first_row = len(probe.rows)
                await send_button(shutdown=shutdown)
                if not shutdown:
                    # Execute the real two-turn controller path before allowing
                    # normal_session's start observer to inspect the live state.
                    await probe.until(lambda: len(probe.rows) > first_row
                                      and sm.state == "IDLE" and sm._session is None)
            probe.button = settled_button
        await display.start()
        await sm.start()
        sm.set_conversation_lifecycle(llm)
        await status.start()
        await session_display.start()
        try:
            for session in probe.plan:
                await asyncio.wait_for(probe.normal_session(session), 2)
            probe.finish_turns()
            assert probe.buttons == (3 if run == "lifecycle" else 2 if run == "pn" else 7)
            assert len(probe.sessions) == len(plan)
            assert len(probe.rows) == sum(len(session) for session in plan)
            assert len({row["session_id"] for row in probe.rows}) == len(plan)
            assert all(row["llm_terminal"] and row["audio_complete"] and row["speech_equal"]
                       for row in probe.rows)
            assert all(row["conversation_absent"] and row["inflight"] == 0
                       and row["streaming_controls"] == 0 and row["close_count"] == 1
                       for row in probe.sessions)
            assert not probe.errors and not probe.pending
        finally:
            await probe.button(shutdown=True)
            await sm.wait_stopped()
            await session_display.stop()
            await status.stop()
            await sm.stop()
            await display.stop()
    asyncio.run(scenario())
