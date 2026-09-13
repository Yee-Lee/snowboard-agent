"""MEM/tooling regressions for real action windows and bounded lab cleanup."""
import asyncio
from dataclasses import replace
import json
import traceback

import pytest

from scripts.m4b_target_metrics import (MeasurementHarness, MeasurementPoint,
    MetricsError, MIB, derive_thresholds, freeze_release_profile_automatic)
from tests.test_m4b_mem_001 import sample
from tests.test_m4b_res_001 import authorization


def observations(*, early_primary=False, notice=False):
    labels = ["engine_ready", "conversation_preparation", "conversation_ready",
              "pre_generate", "post_generate", "pre_speak", "audio_completion",
              "primary_completion", "pre_replacement", "post_replacement",
              "post_session_close"]
    if early_primary:
        labels.remove("primary_completion")
        labels.insert(labels.index("pre_speak"), "primary_completion")
    rows = []
    for index, label in enumerate(labels):
        # The peak occurs in Audio, after the model terminal. Generation's
        # minimum must include it, not stop at the LLM terminal or PCM readiness.
        available = 900 * MIB if label == "audio_completion" else 1000 * MIB
        rows.append(MeasurementPoint(label, 0, replace(sample(stamp=index + 1),
            mem_total_bytes=2000 * MIB, mem_available_bytes=available)))
    if notice:
        last = rows.pop()
        for label in ("pre_speak", "audio_completion", "primary_completion"):
            rows.append(MeasurementPoint(label, 1, replace(sample(stamp=len(rows) + 1),
                mem_total_bytes=2000 * MIB, mem_available_bytes=1000 * MIB)))
        rows.append(replace(last, operation_index=1,
            sample=replace(last.sample, monotonic_ns=len(rows) + 1)))
    return rows


def test_generate_window_includes_actual_audio_peak():
    result = derive_thresholds(observations(), completed=True, cleanup_proven=True)
    assert result["generate_drop_bytes"] == result["speak_drop_bytes"] == 100 * MIB
    assert result["min_mem_available_generate_bytes"] == 612 * MIB


def test_release_freeze_is_automatic_under_current_authority():
    from pathlib import Path
    from sbd.cognition.litert_lm.lock import load_product_profile, validate_product_profile
    profile = load_product_profile(Path("requirements/m4b/product-profile.json"),
                                   allow_measurement=True)
    release = freeze_release_profile_automatic(profile, observations(),
        evidence_sha256="d" * 64, completed=True, cleanup_proven=True)
    assert release["profile_stage"] == "release"
    assert release["measurement_evidence_locator"] == "sha256/" + "d" * 64
    assert validate_product_profile(release) == release


def test_early_primary_completion_cannot_hide_audio_peak():
    with pytest.raises(MetricsError, match="INCOMPLETE"):
        derive_thresholds(observations(early_primary=True), completed=True, cleanup_proven=True)


def test_context_notice_primary_does_not_require_a_fake_generation():
    result = derive_thresholds(observations(notice=True), completed=True, cleanup_proven=True)
    assert result["generate_drop_bytes"] == 100 * MIB
    assert result["speak_drop_bytes"] == 100 * MIB


@pytest.mark.asyncio
async def test_native_scenario_failure_is_sanitized_and_cleanup_still_runs():
    expected, auth = authorization()
    closed = asyncio.Event()
    async def cleanup():
        closed.set()
        return True
    async def scenario(harness):
        raise RuntimeError("PRIVATE_NATIVE_INPUT_AND_PATH")
    harness = MeasurementHarness(authorization=auth, expected_tuple=expected,
        sample=sample, cleanup=cleanup)
    with pytest.raises(MetricsError, match="STOPPED") as caught:
        await harness.run(scenario)
    assert closed.is_set() and harness.stopped and not harness.completed
    assert harness.cleanup_proven
    rendered = "".join(traceback.format_exception(caught.value))
    assert "PRIVATE_NATIVE_INPUT_AND_PATH" not in rendered


@pytest.mark.asyncio
async def test_cleanup_watchdog_requires_proof_and_joins_cancelled_cleanup():
    expected, auth = authorization()
    entered, joined = asyncio.Event(), asyncio.Event()
    async def cleanup():
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            joined.set()
    async def scenario(harness):
        pass
    harness = MeasurementHarness(authorization=auth, expected_tuple=expected,
        sample=sample, cleanup=cleanup, cleanup_timeout_seconds=0.01)
    with pytest.raises(MetricsError, match="STOPPED"):
        await asyncio.wait_for(harness.run(scenario), timeout=1)
    assert entered.is_set() and joined.is_set()
    assert harness.stopped and not harness.cleanup_proven and not harness.completed


@pytest.mark.parametrize("timeout", [True, 0, -1, float("nan"), float("inf")])
def test_invalid_cleanup_watchdog_is_rejected(timeout):
    expected, auth = authorization()
    with pytest.raises(MetricsError, match="INVALID"):
        MeasurementHarness(authorization=auth, expected_tuple=expected,
            sample=sample, cleanup=lambda: None, cleanup_timeout_seconds=timeout)


def _live_worker_session(*, max_turns=20, cleanup_ok=True, available=1000 * MIB, measurement=None):
    """Actual adapter/ledger/worker/Listen/Reasoner/Speak; deterministic peripherals.

    The existing synthetic release adapter fixture isolates session orchestration.
    Signed null-threshold grant/admission tests separately exercise measurement
    policy. Neither fixture claims native model, hardware or measured thresholds.
    """
    from scripts.m4b_measurement import NativeMeasurementSession, _Components, _MeasurementObserver
    from tests.fakes.m4b_llm_child import adapter_fixture
    from sbd.perception.listen.asr import ASRResult, MockASRAdapter
    from sbd.perception.listen.listener import Listen
    from sbd.action.speak.speaker import Speak
    from sbd.cognition.reasoner import Reasoner
    from sbd.cognition.prompt_builder import ListenProjector
    from sbd.core.event_bus import EventBus
    from tests.test_m2_wrk_003 import _validator
    adapter, children, _, original_sampler = adapter_fixture()
    class Sampler:
        def sample(self, **kwargs):
            result = original_sampler.sample(**kwargs)
            return replace(result, mem_total_bytes=2000 * MIB, mem_available_bytes=available)
    adapter._sampler = sampler = Sampler()
    if measurement is not None:
        profile, expected, auth, grant = measurement
        original = adapter
        def factory(cfg, lock, epoch, *, measurement_grant):
            assert measurement_grant is grant
            return original._child_factory(cfg, lock, epoch)
        adapter = type(original)(original._cfg,
            lock=replace(original._lock, product_profile=profile,
                         identity=original._lock.ready_identity(profile)),
            schedule_recovery=original._schedule_recovery, wait_recovery=original._wait_recovery,
            resource_sampler=sampler, child_factory=factory, measurement_grant=grant)
    observer, bus, calls = _MeasurementObserver(), EventBus(), []
    adapter._observer = observer
    class Input:
        async def start(self):
            calls.append("input_start")
        async def stop(self):
            calls.append("input_stop")
        async def frames(self):
            yield b"pcm"
    class Output:
        async def start(self):
            calls.append("output_start")
        async def stop(self):
            calls.append("output_stop")
        async def play(self, pcm):
            async for chunk in pcm:
                calls.append("played_pcm")
    class TTS:
        async def start(self):
            pass
        async def stop(self):
            calls.append("tts_stop")
        async def abort(self):
            pass
        async def synthesize(self, text):
            yield b"12"
    asr, tts, audio_input, audio_output = (MockASRAdapter((ASRResult("你好"),) * 25),
                                        TTS(), Input(), Output())
    listener = Listen(audio_input=audio_input, asr=asr, bus=bus, observe=observer.mark)
    speaker = Speak(tts=tts, audio_output=audio_output, bus=bus, observe=observer.mark)
    reasoner = Reasoner(adapter, ListenProjector(), bus, lambda name: True, _validator(), observer=observer)
    components = _Components(adapter, listener, reasoner, speaker, audio_input, audio_output,
                              asr, tts, bus, sampler, observer)
    if measurement is None:
        expected, auth = authorization()
    def cleanup_proof(c, handles):
        return cleanup_ok and children[0].runtime.history is None and adapter._child is None
    session = NativeMeasurementSession(components, authorization=auth, expected_tuple=expected,
        max_turns=max_turns, cleanup_proof=cleanup_proof)
    return session, children, calls


@pytest.mark.asyncio
async def test_live_workers_run_single_session_to_context_replacement_then_repeat():
    session, children, calls = _live_worker_session()
    result = await session.run()
    child = children[0]
    assert result["status"] == "Measured" and "PASS" not in repr(result)
    assert len(children) == 1 and child.runtime.opens == child.runtime.closes == 2
    assert session.replacement_completed and session.repeat_succeeded and session.generated_turns >= 3
    opens = [frame for frame in child.commands if frame["op"] == "OPEN"]
    assert len({frame["session_id"] for frame in opens}) == 1
    assert [frame["generation"] for frame in opens] == [1, 2]
    labels = [point.lifecycle_point for point in session.harness.points]
    assert labels[0] == "engine_ready" and labels[-1] == "post_session_close"
    assert labels.count("post_session_close") == 1 and labels.count("pre_replacement") == 1
    assert calls.count("played_pcm") == session.generated_turns + 1
    assert session.harness.cleanup_proven and session._events == [] and session._session == ""


@pytest.mark.asyncio
async def test_signed_null_threshold_profile_drives_complete_actual_worker_session(tmp_path, monkeypatch):
    from tests.test_m4b_off_001 import _measurement_authorization
    from sbd.cognition.litert_lm.measurement import MeasurementGrant
    profile, expected, auth, path, context_checks = _measurement_authorization(tmp_path, monkeypatch)
    grant = MeasurementGrant.load(path, expected_tuple=expected, profile=profile)
    session, children, calls = _live_worker_session(measurement=(profile, expected, auth, grant))
    result = await session.run()
    assert result["status"] == "Measured" and result["authorized_tuple"] == expected
    assert session.repeat_succeeded and session.replacement_completed
    assert profile["min_mem_available_generate_bytes"] is None
    assert profile["min_mem_available_speak_bytes"] is None
    assert not session._c.adapter.recovery_pending and len(context_checks) >= 2
    assert len(children) == 1 and children[0].runtime.opens == 2
    # Peripheral/native/context attestation are explicitly simulated; this is
    # execution of the orchestration and real null-threshold policy, not Pi PASS.


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["no_context", "floor", "cleanup"])
async def test_live_session_cannot_measure_without_context_floor_or_cleanup(failure):
    session, children, calls = _live_worker_session(max_turns=3 if failure == "no_context" else 20,
        cleanup_ok=failure != "cleanup", available=511 * MIB if failure == "floor" else 1000 * MIB)
    with pytest.raises(MetricsError):
        await session.run()
    assert not session.harness.completed and session.harness.stopped
    assert session._events == [] and session._session == ""
    assert "input_stop" in calls and "output_stop" in calls
    if failure == "floor":
        assert children[0].runtime.sends == 0


@pytest.mark.asyncio
async def test_native_session_cleanup_honors_outer_watchdog_cancellation():
    session, children, calls = _live_worker_session()
    entered, joined = asyncio.Event(), asyncio.Event()
    async def held_stop():
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            joined.set()
    session._c.speaker.stop = held_stop
    session.harness._cleanup_timeout = 0.01
    with pytest.raises(MetricsError, match="STOPPED"):
        await asyncio.wait_for(session.run(), timeout=1)
    assert entered.is_set() and joined.is_set()
    assert not session.harness.completed and not session.harness.cleanup_proven
    assert session._events == [] and session._session == ""


def test_cli_missing_inputs_is_blocked_not_a_fake_native_pass(capsys):
    from scripts.m4b_measurement import main
    assert main([]) == 2
    assert json.loads(capsys.readouterr().out) == {
        "status": "Blocked", "code": "M4B_MEASUREMENT_NOT_COMPLETE",
        "stage": "input_validation",
    }


def test_user_diagnostic_harness_is_explicitly_not_formal_evidence():
    expected, _auth = authorization()
    harness = MeasurementHarness(authorization=None, expected_tuple=expected,
        user_authorized_diagnostic=True, sample=sample, cleanup=lambda: None)
    assert harness.authorized_tuple == expected
    assert harness.user_authorized_diagnostic is True


@pytest.mark.parametrize("failure_type", [RuntimeError, KeyboardInterrupt])
def test_user_diagnostic_startup_failure_is_fully_persisted(tmp_path, monkeypatch, capsys, failure_type):
    from scripts import m4b_measurement

    output = tmp_path / "private"
    output.mkdir(mode=0o700)
    existing = tmp_path / "input"
    existing.write_text("fixture")
    monkeypatch.setattr(m4b_measurement, "build_native",
        lambda args, recorder=None: (_ for _ in ()).throw(failure_type("startup detail")))
    args = []
    for name in ("audio-config", "runtime-python", "model", "product-profile", "artifact-lock"):
        args.extend((f"--{name}", str(existing)))
    args.extend(("--private-output", str(output), "--candidate-sha", "a" * 40,
                 "--user-authorized-diagnostic"))
    assert m4b_measurement.main(args) == 2
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["stage"] == "input_validation"
    failure = json.loads((output / "failure.json").read_text())
    assert failure["exception_type"] == failure_type.__name__
    assert failure["interrupted"] is (failure_type is KeyboardInterrupt)
    assert failure["exception"] == "startup detail"
    events = [json.loads(line) for line in (output / "diagnostic-events.jsonl").read_text().splitlines()]
    assert [row["stage"] for row in events] == [
        "run_created", "STARTING", "diagnostic_inputs", "run_failed",
    ]
    assert f"{failure_type.__name__}: startup detail" in events[-1]["traceback"]
    assert (output / "partial-series.json").is_file()
    assert (output / "partial-observations.json").is_file()
    assert (output / "partial-turns.json").is_file()


@pytest.mark.asyncio
async def test_diagnostic_audio_emits_ready_then_persists_exact_pcm(tmp_path, capsys):
    from scripts.m4b_measurement import _DiagnosticAudioInput, _DiagnosticRecorder

    class Frames:
        def __init__(self):
            self.values = iter((b"\x01\x02" * 320, b"\x03\x04" * 320))
        def __aiter__(self):
            return self
        async def __anext__(self):
            try:
                return next(self.values)
            except StopIteration:
                raise StopAsyncIteration
        async def aclose(self):
            return None

    class Input:
        _executor = None
        async def start(self):
            return None
        async def stop(self):
            return None
        def frames(self):
            return Frames()

    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    recorder = _DiagnosticRecorder(root)
    audio = _DiagnosticAudioInput(Input(), recorder)
    stream = audio.frames()
    assert capsys.readouterr().out == ""  # No false READY before first real frame.
    assert await anext(stream) == b"\x01\x02" * 320
    assert await anext(stream) == b"\x03\x04" * 320
    await stream.aclose()
    recorder.close()
    announced = capsys.readouterr().out.splitlines()
    assert json.loads(announced[0]) == {
        "status": "Running", "stage": "READY", "turn": 1,
        "audio_format": "s16le-16000-mono",
    }
    assert announced[1] == "========== READY：請現在說話（第 1 輪） =========="
    assert (root / "input-turn-0001.pcm").read_bytes() == b"\x01\x02" * 320 + b"\x03\x04" * 320
    events = [json.loads(line) for line in (root / "diagnostic-events.jsonl").read_text().splitlines()]
    assert [row["stage"] for row in events] == ["run_created", "READY", "audio_input_closed"]
    assert events[-1]["pcm_bytes"] == 1280


def test_target_binding_requires_real_argument_list(monkeypatch):
    from tests.m4b_target_cases import require_native_scenario_binding
    from scripts.m4b_llm_product import ProductFailure
    monkeypatch.delenv("M4B_MEASUREMENT_ARGS", raising=False)
    with pytest.raises(ProductFailure, match="INPUTS_MISSING"):
        require_native_scenario_binding()
    monkeypatch.setenv("M4B_MEASUREMENT_ARGS", '["--candidate-sha", "abc"]')
    assert require_native_scenario_binding() == ["--candidate-sha", "abc"]


def test_private_output_is_exclusive_and_rejects_public_directory(tmp_path):
    from scripts.m4b_measurement import _write_private
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    _write_private(root, "measurement.json", {"status": "Measured"})
    with pytest.raises(FileExistsError):
        _write_private(root, "measurement.json", {"status": "Measured"})
    root.chmod(0o755)
    with pytest.raises(MetricsError, match="PRIVATE_OUTPUT_INVALID"):
        _write_private(root, "other.json", {})


@pytest.mark.asyncio
async def test_complete_pm_accepts_free_input_and_prints_actual_input_output(tmp_path, capsys):
    from collections import deque
    from scripts.m4b_measurement import _DiagnosticRecorder
    from sbd.perception.listen.asr import ASRResult
    session, children, calls = _live_worker_session()
    recorder = _DiagnosticRecorder(tmp_path)
    session._recorder = recorder
    session._complete_pm = True
    session._c.sampler._sample = session._c.sampler.sample
    # Ten generations reach 900 KV. Free questions and ASR typos must reach
    # Reasoner, including different wording after replacement; meaning is reviewed.
    session._c.asr._outcomes = deque(ASRResult(text) for text in
        ["你是誰?", "台灣最高的三四省樓。", ""] + ["你好"] * 8 +
        ["你是誰？", "錯的問題", "你是誰", "下一題"])
    try:
        result = await session.run()
    finally:
        recorder.close()
    assert result["repeat_verified"] is None
    assert result["new_conversation_answered"] is True
    assert result["post_replacement_generated_turns"] == 2
    assert result["pr_complete"] is result["ph_complete"] is False
    import hashlib
    digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
    generated = [frame["input_sha256"] for frame in children[0].commands if frame["op"] == "GENERATE"]
    assert digest("錯的問題") in generated
    assert digest("台灣最高的三四省樓。") in generated
    assert generated[-2:] == [digest("錯的問題"), digest("你是誰")]
    terminal = capsys.readouterr().out
    assert '[第 1 輪｜ASR ok] "你是誰?"' in terminal
    assert '[第 1 輪｜回覆 KEEP_NEXT] "你好"' in terminal
    events = [json.loads(line) for line in (tmp_path / "diagnostic-events.jsonl").read_text().splitlines()]
    assert not any(row["stage"] == "input_retry" for row in events)
    assert "請說：" not in terminal
    assert any(row["stage"] == "waiting_for_input" for row in events)
    assert any(row["stage"] == "context_rejection_proof" for row in events)
    # The export/import contract is exercised using this explicitly synthetic
    # runtime session; these fixture artifacts are never native acceptance.
    from dataclasses import asdict
    from pathlib import Path
    from scripts.m4b_measurement import _write_private, _seal_pm_bundle, validate_pm_bundle
    from sbd.cognition.litert_lm.lock import load_product_profile
    profile = load_product_profile(Path("requirements/m4b/product-profile.json"), allow_measurement=True)
    _write_private(tmp_path, "series.json", [asdict(p) for p in session.harness.points])
    series_digest = hashlib.sha256((tmp_path / "series.json").read_bytes()).hexdigest()
    release = freeze_release_profile_automatic(profile, session.harness.points,
        evidence_sha256=series_digest, completed=True, cleanup_proven=True)
    result.update(pm_complete=True, measurement_series_sha256=series_digest,
                  release_profile_sha256=release["profile_sha256"])
    for name, value in (("measurement.json", result), ("measurement-profile.json", profile),
            ("release-profile.json", release), ("artifact-verification.json", {"verified": True}),
            ("content-verification.json", {"verified": True}),
            ("observations.json", session._c.observer.rows), ("turns.json", session._diagnostic_turns)):
        _write_private(tmp_path, name, value)
    for turn in session._diagnostic_turns:
        (tmp_path / f"input-turn-{turn['turn']:04d}.pcm").write_bytes(b"fixture PCM")
    assert _seal_pm_bundle(tmp_path)["status"] == "PM_INPUT_VALID"
    (tmp_path / "input-turn-0001.pcm").unlink()
    with pytest.raises(MetricsError, match="PM_BUNDLE_INVALID"):
        validate_pm_bundle(tmp_path)


def test_changed_artifact_cannot_freeze_measurement(monkeypatch):
    from scripts import m4b_measurement
    monkeypatch.setattr(m4b_measurement, "_artifact_snapshot", lambda args: {"model": "changed"})
    with pytest.raises(MetricsError, match="ARTIFACT_CHANGED_DURING_RUN"):
        m4b_measurement._verify_measured_artifacts(None, {"model": "original"})


@pytest.mark.asyncio
@pytest.mark.parametrize("valid", [True, False, "reported"])
async def test_auto_fill_uses_real_worker_path_and_never_requests_sixth_human_window(tmp_path, valid):
    from collections import deque
    from scripts.m4b_measurement import _DiagnosticRecorder
    from sbd.perception.listen.asr import ASRResult
    session, children, _ = _live_worker_session()
    recorder = _DiagnosticRecorder(tmp_path)
    session._recorder = recorder
    session._complete_pm = session._auto_fill = True
    session._c.sampler._sample = session._c.sampler.sample
    words = (["你是誰?", "台灣最高的三四省樓。", "自由問句", "下一題", "最後一題"]
             if valid else [""] * 5)
    if valid == "reported":
        words = ["你是誰?", "", "", "台灣最高的三四審文。", "台灣最高的三四省樓。"]
    session._c.asr._outcomes = deque(ASRResult(word) for word in words + ["不可收第六輪"])
    try:
        if valid:
            result = await session.run()
            assert result["human_capture_windows"] == 5
            assert result["automatic_fill_turns"] == (10 if valid == "reported" else 9)
            assert result["post_replacement_generated_turns"] == (2 if valid == "reported" else 3)
            assert result["repeat_verified"] is None
            assert result["new_conversation_answered"] is True
            assert children[0].runtime.opens == 2
            assert children[0].runtime.sends == (12 if valid == "reported" else 13)
            automatic = [r for r in session._diagnostic_turns if r["input_source"] == "automatic_fill"]
            assert len(automatic) == result["automatic_fill_turns"]
            assert all(r["audio_turn"] is None for r in automatic)
            assert automatic[-1]["response"]["post_action_route"] == "REPLACE_NEXT"
        else:
            result = await session.run()
            assert session.human_turns == 5
            assert result["new_conversation_answered"] is False
            assert result["post_replacement_generated_turns"] == 0
            assert result["cleanup_proven"] is True
            assert session.generated_turns == session.automatic_turns - 1
        assert [value.text for value in session._c.asr._outcomes] == ["不可收第六輪"]
    finally:
        recorder.close()


def test_completed_capture_survives_postprocess_error(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace
    from scripts import m4b_measurement as module
    output = tmp_path / "private"
    output.mkdir(mode=0o700)
    profile = tmp_path / "profile.json"
    profile.write_text("{}")
    async def run():
        return {"status": "Measured"}
    session = SimpleNamespace(run=run, harness=SimpleNamespace(points=[], completed=True, cleanup_proven=True),
        _c=SimpleNamespace(observer=SimpleNamespace(rows=[])), _diagnostic_turns=[],
        _diagnostic_stage="session_closing", replacement_completed=True,
        _repeat_verified=True, post_replacement_generated_turns=2)
    monkeypatch.setattr(module, "build_native", lambda *args, **kwargs: session)
    monkeypatch.setattr(module, "_artifact_snapshot", lambda args: {})
    monkeypatch.setattr(module, "_content_snapshot", lambda args: {})
    def fail(*args):
        raise RuntimeError("postprocess failure")
    monkeypatch.setattr(module, "_verify_measured_artifacts", fail)
    argv = []
    for name in ("audio-config", "runtime-python", "model", "product-profile", "artifact-lock"):
        argv.extend(("--" + name, str(profile)))
    argv.extend(("--private-output", str(output), "--candidate-sha", "a" * 40,
                 "--user-authorized-diagnostic", "--complete-pm"))
    assert module.main(argv) == 0
    report = json.loads((output / "review-needed.json").read_text())
    assert report["capture_complete"] is True and report["status"] == "NeedsReview"
    assert not (output / "failure.json").exists()
    assert (output / "series.json").exists() and (output / "partial-turns.json").exists()
    assert "M4B_POSTPROCESS_REVIEW_REQUIRED" in capsys.readouterr().out


@pytest.mark.asyncio
@pytest.mark.parametrize("windows", [1, 2])
@pytest.mark.parametrize("text", ["自由問句", ""])
async def test_bounded_voice_windows_do_not_require_pm_profile(tmp_path, windows, text):
    from collections import deque
    from scripts.m4b_measurement import _DiagnosticRecorder
    from sbd.perception.listen.asr import ASRResult
    session, children, _ = _live_worker_session()
    recorder = _DiagnosticRecorder(tmp_path)
    session._recorder = recorder
    session._diagnostic_windows = session._max_turns = windows
    session.harness.user_authorized_diagnostic = True
    session._c.sampler._sample = session._c.sampler.sample
    session._c.asr._outcomes = deque(ASRResult(word) for word in [text] * windows + ["unused"])
    try:
        result = await session.run()
    finally:
        recorder.close()
    assert result["status"] == "DiagnosticComplete"
    assert result["human_capture_windows"] == windows
    assert result["automatic_fill_turns"] == 0
    assert result["derived"] is None
    assert result["cleanup_proven"] is True
    assert [v.text for v in session._c.asr._outcomes] == ["unused"]
