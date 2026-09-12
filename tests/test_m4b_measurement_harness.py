"""MEM/tooling regressions for real action windows and bounded lab cleanup."""
import asyncio
from dataclasses import replace
import traceback

import pytest

from scripts.m4b_target_metrics import (MeasurementHarness, MeasurementPoint,
    MetricsError, MIB, derive_thresholds)
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
    assert capsys.readouterr().out == '{"status":"Blocked","code":"M4B_MEASUREMENT_NOT_COMPLETE"}\n'


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
