"""Authorized, measurement-only Audio + LLM vertical slice (never product PASS).

Run from a clean, exact-SHA Pi checkout with the separately approved authorization
and private output directory. Speak short, genuine follow-ups into the microphone
until the application requests a repeat after context replacement. The next
successful generation closes this laboratory session. This is not SM/WAKE or
human semantic acceptance, and cannot freeze a release profile.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.m4b_target_metrics import MeasurementHarness, MetricsError
from sbd.cognition.observability import CognitionObserver
from sbd.core.events import ActionCompleted, ErrorOccurred, LLMResponse, PerceptionResult


class _MeasurementObserver(CognitionObserver):
    def __init__(self):
        self.rows = []
        super().__init__(sink=self.rows.append)
        self.harness = None
        self.operation_index = 0
        self.replacing = False
        self.context_rejected = False
        self.generated_this_turn = False

    def memory(self, sample, *, generation, lifecycle_point):
        super().memory(sample, generation=generation, lifecycle_point=lifecycle_point)
        if self.harness is not None:
            point = "sample" if self.replacing and lifecycle_point == "post_session_close" else lifecycle_point
            self.harness.record_sample(sample, point, self.operation_index)

    def measured(self, snapshot):
        super().measured(snapshot)
        self.context_rejected = (snapshot.current_kv_tokens + snapshot.rendered_incremental_tokens
                                 + snapshot.output_reserve_tokens > snapshot.engine_context_tokens)

    def generated(self, metrics, *, clock_mapped=False):
        super().generated(metrics, clock_mapped=clock_mapped)
        self.generated_this_turn = True


@dataclass
class _Components:
    adapter: object
    listener: object
    reasoner: object
    speaker: object
    audio_input: object
    audio_output: object
    asr: object
    tts: object
    bus: object
    sampler: object
    observer: _MeasurementObserver


class NativeMeasurementSession:
    """Execute actual workers; injectable components are portable test seams only."""

    def __init__(self, components: _Components, *, authorization, expected_tuple,
                 max_turns: int = 128, listen_timeout_seconds: float = 30,
                 startup_health=None, cleanup_proof=None):
        if type(max_turns) is not int or not 3 <= max_turns <= 256:
            raise MetricsError("M4B_MEASUREMENT_INPUT_INVALID")
        self._c = components
        self._max_turns = max_turns
        self._listen_timeout = listen_timeout_seconds
        self._startup_health = startup_health
        self._startup_health_previous = None
        self._cleanup_proof = cleanup_proof or _native_cleanup_proven
        self._events = []
        self._subscriptions = []
        self._started = []
        self._session = uuid.uuid4().hex
        self._generation = 1
        self._conversation_open = False
        self.replacement_completed = False
        self.repeat_succeeded = False
        self.generated_turns = 0
        self.harness = MeasurementHarness(authorization=authorization, expected_tuple=expected_tuple,
            sample=self._sample, cleanup=self._cleanup)
        components.observer.harness = self.harness
        for kind in (PerceptionResult, LLMResponse, ActionCompleted, ErrorOccurred):
            self._subscriptions.append(components.bus.subscribe(kind, self._collect,
                name="m4b.measurement.collect"))

    async def _collect(self, event):
        self._events.append(event)

    def _take(self, kind):
        events, self._events = self._events, []
        if (any(isinstance(event, ErrorOccurred) for event in events)
                or len(events) != 1 or not isinstance(events[0], kind)):
            events.clear()
            raise MetricsError("M4B_MEASUREMENT_WORKER_FAILED")
        return events.pop()

    def _sample(self):
        child = self._c.adapter._child
        if child is None:
            raise MetricsError("M4B_MEASUREMENT_OWNER_MISSING")
        return self._c.sampler.sample(child_pid=child.pid, child_pgid=child.pgid)

    async def _operation(self, execute):
        # Actual named boundary rows come from adapter/worker callbacks. This
        # wrapper adds pre-operation safety and samples during asynchronous work.
        return await self.harness.operation(before="sample", after="sample",
            index=self._c.observer.operation_index, execute=execute)

    @staticmethod
    def _proof(proof, session, generation):
        from sbd.core.state_manager.ports import ConversationCloseProof
        if (not isinstance(proof, ConversationCloseProof) or proof.session_id != session
                or proof.generation != generation or proof.request_terminal_proven is not True
                or proof.cleanup_proven is not True or proof.engine_usable is not True):
            raise MetricsError("M4B_MEASUREMENT_CLOSE_UNPROVEN")

    async def _open(self):
        from sbd.core.state_manager.ports import ConversationReady
        ready = await self._c.adapter.control.open_conversation(self._session, self._generation)
        if (not isinstance(ready, ConversationReady) or ready.session_id != self._session
                or ready.generation != self._generation):
            raise MetricsError("M4B_MEASUREMENT_OPEN_UNPROVEN")
        self._conversation_open = True

    async def _close(self, reason):
        proof = await self._c.adapter.control.close_conversation(self._session, self._generation, reason)
        self._proof(proof, self._session, self._generation)
        self._conversation_open = False

    async def _replace(self):
        observer = self._c.observer
        observer.replacing = True
        try:
            await self._close("replacement")
            self._generation += 1
            await self._open()
        finally:
            observer.replacing = False

    async def _scenario(self, harness):
        c, response, perception = self._c, None, None
        try:
            # Before Engine READY there cannot be a complete LLM owner sample.
            # Startup checks actual system health; the first complete owner row
            # is emitted by authenticated Engine READY, never a fake LLM PID.
            for owner in (c.audio_input, c.audio_output, c.listener, c.speaker, c.reasoner):
                if self._startup_health is not None:
                    self._startup_health_previous = self._startup_health(self._startup_health_previous)
                self._started.append(owner)
                await owner.start()
            await self._operation(self._open)
            for turn in range(1, self._max_turns + 1):
                c.observer.operation_index = turn
                c.observer.context_rejected = False
                c.observer.generated_this_turn = False
                await self._operation(lambda: c.listener.perceive(
                    self._session, turn, turn, self._listen_timeout))
                perception = self._take(PerceptionResult)
                operation = c.reasoner.reason(self._session, turn, turn, (perception,), (),
                                               conversation_generation=self._generation)
                perception = None
                await self._operation(lambda: operation)
                response = self._take(LLMResponse)
                if response.action_kind != "speak":
                    raise MetricsError("M4B_MEASUREMENT_UNEXPECTED_OUTCOME")
                await harness.operation(before="pre_speak", after="audio_completion", index=turn,
                    execute=lambda: c.speaker.execute(self._session, turn, turn, response.action_payload))
                terminal = self._take(ActionCompleted)
                if terminal.status != "ok":
                    raise MetricsError("M4B_MEASUREMENT_ACTION_FAILED")
                harness.capture("primary_completion", turn)
                c.observer.finish()
                route = response.post_action_route
                response = None
                if c.observer.generated_this_turn:
                    self.generated_turns += 1
                    if self.replacement_completed:
                        self.repeat_succeeded = True
                        break
                if route == "REPLACE_NEXT":
                    if not c.observer.context_rejected or self.generated_turns < 2:
                        raise MetricsError("M4B_MEASUREMENT_CONTEXT_NOT_PROVEN")
                    await harness.operation(before="pre_replacement", after="post_replacement",
                                            index=turn, execute=self._replace)
                    self.replacement_completed = True
                elif route == "END_SESSION":
                    raise MetricsError("M4B_MEASUREMENT_SESSION_ENDED_EARLY")
            if not self.repeat_succeeded:
                raise MetricsError("M4B_MEASUREMENT_REPEAT_NOT_PROVEN")
            # CLOSE's own callback is the final row; do not append a synthetic
            # operation-after sample after the actual post-session-close point.
            harness.capture("sample", c.observer.operation_index, before_operation=True)
            await self._close("session_end")
        finally:
            response = perception = None
            self._events.clear()

    async def _cleanup(self):
        c = self._c
        # Cleanup remains mandatory after a stopped run. Its teardown callbacks
        # must not try to append to an already-invalid measurement series.
        c.observer.harness = None
        handles = [getattr(owner, "_child", None) for owner in (c.asr, c.tts, c.adapter)]
        clean = True
        try:
            for owner in reversed(self._started):
                try:
                    await owner.stop()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    clean = False
                    force = getattr(owner, "force_abort", None)
                    if force is not None:
                        try:
                            await asyncio.wait_for(force(), timeout=1)
                        except asyncio.CancelledError:
                            raise
                        except Exception:
                            pass
        finally:
            self._started.clear()
            for subscription in self._subscriptions:
                c.bus.unsubscribe(subscription)
            self._subscriptions.clear()
            self._events.clear()
            self._session = ""
        return clean and self._cleanup_proof(c, handles)

    async def run(self):
        return await self.harness.run(self._scenario)


def _native_cleanup_proven(components, handles):
    from scripts.m4b_target_metrics import process_group_members
    for child in handles:
        if child is None:
            return False
        process = getattr(child, "_process", None)
        pid = getattr(child, "pid", None) or getattr(process, "pid", None)
        if not pid or (process is not None and process.returncode is None):
            return False
        if process_group_members(pid) or getattr(child, "_workdir", None) is not None:
            return False
    return all(getattr(audio, "_executor", None) is None
               for audio in (components.audio_input, components.audio_output))


def _startup_health(previous=None):
    from scripts.m4b_target_metrics import MEASUREMENT_SAFETY_FLOOR_BYTES, kernel_resource_sample
    from sbd.core._m4b_resource_binding import _pi_temperature, _pi_throttled
    health = kernel_resource_sample(Path("/proc/meminfo").read_text(), Path("/proc/vmstat").read_text(),
        str(round(_pi_temperature() * 1000)), f"throttled=0x{_pi_throttled():x}")
    if (health["mem_available_mib"] * 1024**2 < MEASUREMENT_SAFETY_FLOOR_BYTES
            or (previous is not None and health["swap_used_mib"] > previous["swap_used_mib"])
            or health["oom_kill"] != 0
            or health["thermal_celsius"] >= 80 or health["throttled_bits"] != 0):
        raise MetricsError("M4B_MEASUREMENT_STARTUP_UNSAFE")
    return health


def build_native(args):
    from sbd.action.payload_validator import ActionPayloadValidator
    from sbd.action.tool.registry import ToolRegistry
    from sbd.action.speak import make_tts_adapter
    from sbd.action.speak.speaker import Speak
    from sbd.cognition.factory import _validate_shape
    from sbd.cognition.litert_lm.adapter import LiteRTLMAdapter
    from sbd.cognition.litert_lm.lock import LLMArtifactLock, load_product_profile
    from sbd.cognition.litert_lm.measurement import MeasurementGrant
    from sbd.cognition.litert_lm.resource import ProcLLMResourceSampler
    from sbd.cognition.prompt_builder import ListenProjector
    from sbd.cognition.reasoner import Reasoner
    from sbd.core._m4b_resource_binding import _M4BResourceBinding, _pi_temperature, _pi_throttled
    from sbd.core.audio import make_audio_input, make_audio_output
    from sbd.core.config.loader import load_config
    from sbd.core.config.models import LLMConfig
    from sbd.core.event_bus import EventBus
    from sbd.perception.listen import make_asr_adapter
    from sbd.perception.listen.listener import Listen
    if not args.audio_config.is_file():
        raise MetricsError("M4B_MEASUREMENT_INPUTS_MISSING")
    config = load_config(local_path=args.audio_config, dotenv_path=Path("/dev/null"), environ={})
    if (config.cognition.llm.driver != "mock" or config.core.audio.driver != "alsa"
            or config.perception.default_perceptions != ("listen",)
            or not config.perception.listen.enabled or config.perception.read.enabled
            or config.perception.look.enabled
            or not config.action.speak.enabled or not config.action.rest.enabled
            or config.action.tool.enabled
            or config.perception.listen.adapter.driver != "whispercpp"
            or config.action.tts.driver != "sherpa_matcha"):
        raise MetricsError("M4B_MEASUREMENT_INPUT_UNSUPPORTED")
    profile = load_product_profile(args.product_profile, allow_measurement=True)
    expected = dict(schema_version=1, harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        candidate_sha=args.candidate_sha, profile_sha256=profile["profile_sha256"],
        target_identity="pi5-4gb-debian13-aarch64-cp3135")
    grant = MeasurementGrant.load(args.authorization, expected_tuple=expected, profile=profile)
    cfg = LLMConfig(driver="litert_lm", runtime_python=args.runtime_python,
        model_path=args.model, product_profile_path=args.product_profile,
        artifact_lock_path=args.artifact_lock, profile_id=profile["profile_id"])
    _validate_shape(cfg)
    lock = LLMArtifactLock.load(args.artifact_lock, repo_root=ROOT)
    profile = lock.verify_config_paths(cfg, allow_measurement=True)
    lock = replace(lock, identity=lock.ready_identity(profile), product_profile=profile)
    audio_input, audio_output = make_audio_input(config.core.audio), make_audio_output(config.core.audio)
    asr, tts = make_asr_adapter(config.perception.listen.adapter), make_tts_adapter(config.action.tts)
    binding = _M4BResourceBinding(asr=asr, tts=tts, native_asr=True, native_tts=True)
    sampler = ProcLLMResourceSampler(ownership_registry=binding,
        temperature=_pi_temperature, throttled=_pi_throttled)
    observer, bus = _MeasurementObserver(), EventBus()
    def forbidden_recovery(*args, **kwargs):
        raise MetricsError("M4B_MEASUREMENT_RECOVERY_FORBIDDEN")
    adapter = LiteRTLMAdapter(cfg, lock=lock, schedule_recovery=forbidden_recovery,
        wait_recovery=forbidden_recovery, resource_sampler=sampler,
        observer=observer, measurement_grant=grant)
    binding.bind_llm(adapter)
    audio_output._observe = observer.mark
    listener = Listen(audio_input=audio_input, asr=asr, bus=bus, observe=observer.mark)
    speaker = Speak(tts=tts, audio_output=audio_output, bus=bus, observe=observer.mark)
    tools = ToolRegistry()
    tools.seal()
    reasoner = Reasoner(adapter, ListenProjector(), bus, lambda name: name in {"listen", "speak"},
        ActionPayloadValidator(tools=tools), observer=observer)
    components = _Components(adapter, listener, reasoner, speaker, audio_input, audio_output,
                             asr, tts, bus, sampler, observer)
    authorization = json.loads(args.authorization.read_text())
    return NativeMeasurementSession(components, authorization=authorization, expected_tuple=expected,
        max_turns=args.max_turns, listen_timeout_seconds=config.perception.timeout_seconds.listen,
        startup_health=_startup_health)


def _write_private(directory: Path, name: str, value):
    root = directory.resolve(strict=True)
    if (not root.is_dir() or root.is_relative_to(ROOT)
            or stat.S_IMODE(root.stat().st_mode) & 0o077):
        raise MetricsError("M4B_MEASUREMENT_PRIVATE_OUTPUT_INVALID")
    descriptor = os.open(root / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(value, stream, sort_keys=True,
                      default=lambda item: sorted(item) if isinstance(item, frozenset) else None)
    except BaseException:
        raise MetricsError("M4B_MEASUREMENT_OUTPUT_FAILED") from None


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise MetricsError("M4B_MEASUREMENT_INPUTS_MISSING")


def main(argv=None):
    parser = _Parser(description=__doc__)
    for field in ("audio-config", "runtime-python", "model", "product-profile", "artifact-lock",
                  "authorization", "private-output"):
        parser.add_argument("--" + field, type=Path, required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--max-turns", type=int, default=128)
    try:
        args = parser.parse_args(argv)
        # Refuse output collisions before acquiring hardware/model resources.
        root = args.private_output.resolve(strict=True)
        if (not root.is_dir() or root.is_relative_to(ROOT) or stat.S_IMODE(root.stat().st_mode) & 0o077
                or any((root / name).exists() for name in (
                    "measurement.json", "series.json", "observations.json"))):
            raise MetricsError("M4B_MEASUREMENT_PRIVATE_OUTPUT_INVALID")
        session = build_native(args)
        result = asyncio.run(session.run())
        _write_private(root, "series.json", [asdict(point) for point in session.harness.points])
        _write_private(root, "observations.json", session._c.observer.rows)
        _write_private(root, "measurement.json", result)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print('{"status":"Blocked","code":"M4B_MEASUREMENT_NOT_COMPLETE"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
