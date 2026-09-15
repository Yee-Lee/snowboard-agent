"""Reusable private capture, lifecycle, measurement, and cleanup support for PV."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time
import traceback
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
        self.snapshot = None

    def memory(self, sample, *, generation, lifecycle_point):
        super().memory(sample, generation=generation, lifecycle_point=lifecycle_point)
        if self.harness is not None:
            point = "sample" if self.replacing and lifecycle_point == "post_session_close" else lifecycle_point
            self.harness.record_sample(sample, point, self.operation_index)

    def measured(self, snapshot):
        super().measured(snapshot)
        self.snapshot = snapshot
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


class _DiagnosticRecorder:
    """Incremental private trace plus content-free terminal synchronization."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve(strict=True)
        self._sequence = 0
        descriptor = os.open(self.root / "diagnostic-events.jsonl",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        self._stream = os.fdopen(descriptor, "w", buffering=1)
        self.record("run_created")

    def record(self, stage: str, **values) -> None:
        self._sequence += 1
        row = {
            "sequence": self._sequence,
            "wall_time": datetime.now(timezone.utc).isoformat(),
            "monotonic_ns": time.monotonic_ns(),
            "stage": stage,
            **values,
        }
        self._stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                      default=lambda item: sorted(item) if isinstance(item, frozenset) else None) + "\n")
        self._stream.flush()

    def announce(self, stage: str, **values) -> None:
        self.record(stage, **values)
        print(json.dumps({"status": "Running", "stage": stage, **values},
                         sort_keys=True), flush=True)
        if stage == "READY":
            print(f"========== READY：請現在說話（第 {values['turn']} 輪） ==========",
                  flush=True)

    def error(self, stage: str, error: BaseException) -> None:
        details = {"validation_reason": getattr(error, "reason", None)}
        for name in ("sample", "previous"):
            value = getattr(error, name, None)
            if value is not None:
                details[name] = asdict(value)
        self.record(stage, exception_type=type(error).__name__, exception=str(error),
                    traceback="".join(traceback.format_exception(error)), **details)
        print(json.dumps({"stage": stage, "exception": str(error),
                          "validation_reason": details["validation_reason"]}), flush=True)

    def close(self) -> None:
        if not self._stream.closed:
            self._stream.flush()
            os.fsync(self._stream.fileno())
            self._stream.close()


class _DiagnosticFrameStream:
    def __init__(self, source, recorder: _DiagnosticRecorder, turn: int) -> None:
        self._source = source
        self._recorder = recorder
        self._turn = turn
        self._bytes = 0
        self._ready = False
        self._digest = hashlib.sha256()
        descriptor = os.open(recorder.root / f"input-turn-{turn:04d}.pcm",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        self._stream = os.fdopen(descriptor, "wb", buffering=0)

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        frame = await anext(self._source)
        if not self._ready:
            self._recorder.announce("READY", turn=self._turn, audio_format="s16le-16000-mono")
            self._ready = True
        self._stream.write(frame)
        self._digest.update(frame)
        self._bytes += len(frame)
        return frame

    async def aclose(self) -> None:
        try:
            await self._source.aclose()
        finally:
            if not self._stream.closed:
                self._stream.close()
                self._recorder.record("audio_input_closed", turn=self._turn,
                    pcm_bytes=self._bytes, pcm_sha256=self._digest.hexdigest())


class _DiagnosticAudioInput:
    def __init__(self, source, recorder: _DiagnosticRecorder) -> None:
        self._source = source
        self._recorder = recorder
        self._turn = 0

    @property
    def _executor(self):
        return self._source._executor

    async def start(self) -> None:
        await self._source.start()

    async def stop(self) -> None:
        await self._source.stop()

    def frames(self):
        self._turn += 1
        return _DiagnosticFrameStream(self._source.frames(), self._recorder, self._turn)


class NativeMeasurementSession:
    """Execute actual workers; injectable components are portable test seams only."""

    def __init__(self, components: _Components, *, authorization, expected_tuple,
                 user_authorized_diagnostic: bool = False,
                 auto_fill: bool = False, diagnostic_windows: int | None = None,
                 max_turns: int = 128, listen_timeout_seconds: float = 30,
                 startup_health=None, cleanup_proof=None, recorder: _DiagnosticRecorder | None = None):
        if type(max_turns) is not int or not 3 <= max_turns <= 256:
            raise MetricsError("M4B_MEASUREMENT_INPUT_INVALID")
        self._c = components
        self._max_turns = max_turns
        self._listen_timeout = listen_timeout_seconds
        self._recorder = recorder
        if diagnostic_windows is not None and (diagnostic_windows not in (1, 2)
                or recorder is None):
            raise MetricsError("M4B_MEASUREMENT_INPUT_INVALID")
        self._diagnostic_windows = diagnostic_windows
        if diagnostic_windows is not None:
            self._max_turns = diagnostic_windows
        self._auto_fill = auto_fill
        if type(auto_fill) is not bool:
            raise MetricsError("M4B_MEASUREMENT_INPUT_INVALID")
        self.human_turns = 0
        self.automatic_turns = 0
        self._diagnostic_stage = "constructed"
        self._diagnostic_turns = []
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
        self.post_replacement_generated_turns = 0
        self.generated_turns = 0
        self._rejected_text = None
        self._repeat_verified = False
        self.harness = MeasurementHarness(authorization=authorization, expected_tuple=expected_tuple,
            user_authorized_diagnostic=user_authorized_diagnostic,
            sample=self._sample, cleanup=self._cleanup,
            point_sink=(None if recorder is None else
                        lambda point: recorder.record("resource_sample", point=asdict(point))),
            error_sink=None if recorder is None else recorder.error)
        components.observer.harness = self.harness
        for kind in (PerceptionResult, LLMResponse, ActionCompleted, ErrorOccurred):
            self._subscriptions.append(components.bus.subscribe(kind, self._collect,
                name="m4b.measurement.collect"))

    async def _collect(self, event):
        if self._recorder is not None:
            self._recorder.record("bus_event", event_type=type(event).__name__, event=asdict(event))
        self._events.append(event)

    def _mark(self, stage: str, **values) -> None:
        self._diagnostic_stage = stage
        if self._recorder is not None:
            self._recorder.announce(stage, **values)

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
        # Diagnostic mode retains the original private traceback instead of the
        # sampler's public fail-closed redaction. It is written only to 0600 output.
        sample = self._c.sampler._sample if self._recorder is not None else self._c.sampler.sample
        return sample(child_pid=child.pid, child_pgid=child.pgid)

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
        if self._recorder is not None:
            self._recorder.record("open_proof", ready=asdict(ready),
                revision=self._c.adapter.conversation_revision)

    async def _close(self, reason):
        proof = await self._c.adapter.control.close_conversation(self._session, self._generation, reason)
        self._proof(proof, self._session, self._generation)
        self._conversation_open = False
        if self._recorder is not None:
            self._recorder.record("close_proof", reason=reason, proof=asdict(proof))

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
            owners = (("audio_input", c.audio_input), ("audio_output", c.audio_output),
                      ("asr", c.listener), ("tts", c.speaker), ("llm", c.reasoner))
            for name, owner in owners:
                started_ns = time.monotonic_ns()
                self._mark("owner_starting", owner=name)
                if self._startup_health is not None:
                    self._startup_health_previous = self._startup_health(self._startup_health_previous)
                self._started.append(owner)
                if self._recorder is None:
                    await owner.start()
                else:
                    task = asyncio.create_task(owner.start())
                    try:
                        while not task.done():
                            await asyncio.wait({task}, timeout=5.0)
                            if not task.done():
                                elapsed_seconds = (time.monotonic_ns() - started_ns) // 1_000_000_000
                                self._mark("owner_loading", owner=name,
                                           elapsed_seconds=elapsed_seconds)
                        await task
                    except BaseException:
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
                        raise
                self._mark("owner_ready", owner=name,
                           startup_duration_ns=time.monotonic_ns() - started_ns)
            self._mark("conversation_opening", generation=self._generation)
            await self._operation(self._open)
            self._mark("conversation_ready", generation=self._generation)
            for turn in range(1, self._max_turns + 1):
                c.observer.operation_index = turn
                c.observer.context_rejected = False
                c.observer.generated_this_turn = False
                c.observer.snapshot = None
                automatic = (self._auto_fill and self.human_turns >= 2
                             and not self.replacement_completed)
                if not automatic:
                    if self._auto_fill and self.human_turns >= 5:
                        self._mark("HUMAN_CAPTURE_FINISHED", human_windows=5,
                                   agent_review_required=True)
                        break
                    self.human_turns += 1
                label = f"自動填充 {self.automatic_turns + 1}" if automatic else f"第 {self.human_turns} 輪"
                if automatic:
                    questions = ("一公斤有幾公克？", "雪是什麼顏色？", "滑雪前要熱身嗎？", "你是誰？")
                    text = questions[self.automatic_turns % len(questions)]
                    self.automatic_turns += 1
                    self._mark("AUTO_FILL", turn=turn, automatic_turn=self.automatic_turns)
                    print("自動累積 context，現在不需說話。", flush=True)
                    perception = PerceptionResult("listen", "ok", text,
                        session_id=self._session, turn_id=turn, correlation_id=turn)
                else:
                    await self._operation(lambda: c.listener.perceive(
                        self._session, turn, turn, self._listen_timeout))
                    perception = self._take(PerceptionResult)
                self._diagnostic_turns.append({"turn": turn, "generation": self._generation,
                    "input_source": "automatic_fill" if automatic else "microphone",
                    "audio_turn": None if automatic else self.human_turns,
                    "perception": asdict(perception)})
                if self._recorder is not None:
                    self._recorder.record("perception_result", turn=turn,
                                          perception=asdict(perception))
                self._mark("automatic_input" if automatic else "asr_complete", turn=turn, status=perception.status,
                           text_codepoints=len(perception.text or ""))
                if self._recorder is not None:
                    print(f"[{label}｜{'文字輸入' if automatic else 'ASR'} {perception.status}] "
                          + json.dumps(perception.text, ensure_ascii=False), flush=True)
                if self._diagnostic_windows and perception.status == "timeout":
                    self._mark("waiting_for_input", turn=turn, reason="NO_TRANSCRIPT")
                    print("本輪沒有辨識文字，已保留錄音供 agent 審查。", flush=True)
                    with c.observer._lock:
                        c.observer._events["asr_final"] = None
                    perception = None
                    continue
                self._mark("reasoning", turn=turn, generation=self._generation)
                operation = c.reasoner.reason(self._session, turn, turn, (perception,), (),
                                               conversation_generation=self._generation)
                perception = None
                await self._operation(lambda: operation)
                response = self._take(LLMResponse)
                self._diagnostic_turns[-1]["response"] = asdict(response)
                if self._recorder is not None:
                    self._recorder.record("llm_response", turn=turn,
                                          response=asdict(response))
                self._mark("response_ready", turn=turn, route=response.post_action_route,
                           action=response.action_kind)
                if self._recorder is not None:
                    print(f"[{label}｜回覆 {response.post_action_route}] "
                          + json.dumps(response.action_payload.get("text"), ensure_ascii=False),
                          flush=True)
                if response.action_kind != "speak":
                    raise MetricsError("M4B_MEASUREMENT_UNEXPECTED_OUTCOME")
                self._mark("speaking", turn=turn)
                await harness.operation(before="pre_speak", after="audio_completion", index=turn,
                    execute=lambda: c.speaker.execute(self._session, turn, turn, response.action_payload))
                terminal = self._take(ActionCompleted)
                if terminal.status != "ok":
                    raise MetricsError("M4B_MEASUREMENT_ACTION_FAILED")
                self._mark("turn_complete", turn=turn, generated=c.observer.generated_this_turn)
                harness.capture("primary_completion", turn)
                c.observer.finish()
                if self._recorder is not None:
                    self._recorder.record("turn_observations", turn=turn,
                        rows=c.observer.rows[-2:])
                route = response.post_action_route
                response = None
                if self._diagnostic_windows and self.human_turns >= self._diagnostic_windows:
                    if c.observer.generated_this_turn:
                        self.generated_turns += 1
                    break
                if c.observer.generated_this_turn:
                    self.generated_turns += 1
                    if self._auto_fill:
                        runtime_row = next((row for row in reversed(c.observer.rows)
                            if row.get("dashboard") == "runtime"
                            and row.get("values", {}).get("terminal_conversation_kv_tokens")
                            is not None), None)
                        if runtime_row is not None:
                            kv_tokens = runtime_row["values"]["terminal_conversation_kv_tokens"]
                            self._mark("context_progress", turn=turn,
                                conversation_kv_tokens=kv_tokens,
                                context_admission_limit_tokens=896,
                                progress_percent=min(100, kv_tokens * 100 // 896))
                    if (self._recorder is not None and not self._auto_fill
                            and self.generated_turns >= 3):
                        break
                    if self.replacement_completed:
                        if (not self._repeat_verified and
                                (c.observer.snapshot is None or c.observer.snapshot.current_kv_tokens != 0)):
                            raise MetricsError("M4B_REPLACEMENT_CONTEXT_NOT_EMPTY")
                        self._repeat_verified = True
                        self.post_replacement_generated_turns += 1
                        self.repeat_succeeded = self.post_replacement_generated_turns >= 2
                        if self.repeat_succeeded and (not self._auto_fill or self.human_turns >= 5):
                            break
                if route == "REPLACE_NEXT":
                    if not c.observer.context_rejected or self.generated_turns < 2:
                        raise MetricsError("M4B_MEASUREMENT_CONTEXT_NOT_PROVEN")
                    self._rejected_text = self._diagnostic_turns[-1]["perception"]["text"]
                    if self._recorder is not None:
                        self._recorder.record("context_rejection_proof", turn=turn,
                            snapshot=asdict(c.observer.snapshot), generated=False)
                    self._mark("replacement_starting", turn=turn, generation=self._generation)
                    await harness.operation(before="pre_replacement", after="post_replacement",
                                            index=turn, execute=self._replace)
                    self.replacement_completed = True
                    self._mark("replacement_ready", turn=turn, generation=self._generation)
                    if self._recorder is not None:
                        self._recorder.announce("NEW_CONVERSATION_READY", turn=turn,
                                                generation=self._generation)
                        print("========== 新對話已建立：接下來可自由提問，等 READY 再說。 ==========",
                              flush=True)
                elif route == "END_SESSION":
                    if self._diagnostic_windows:
                        break
                    raise MetricsError("M4B_MEASUREMENT_SESSION_ENDED_EARLY")
            if self._recorder is None and not self.repeat_succeeded and not self._auto_fill:
                raise MetricsError("M4B_MEASUREMENT_REPEAT_NOT_PROVEN")
            if (self._recorder is not None and not self._auto_fill
                    and not self._diagnostic_windows and self.generated_turns < 3):
                raise MetricsError("M4B_DIAGNOSTIC_TURNS_NOT_COMPLETE")
            # CLOSE's own callback is the final row; do not append a synthetic
            # operation-after sample after the actual post-session-close point.
            harness.capture("sample", c.observer.operation_index, before_operation=True)
            self._mark("session_closing", generation=self._generation)
            await self._close("session_end")
        finally:
            response = perception = None
            self._events.clear()

    async def _cleanup(self):
        c = self._c
        if self._recorder is not None:
            self._recorder.record("cleanup_starting", started_owner_count=len(self._started))
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
            if self._recorder is not None:
                for child in handles:
                    process = getattr(child, "_process", None)
                    self._recorder.record("cleanup_owner_proof",
                        child_type=type(child).__name__,
                        pid=getattr(child, "pid", None),
                        process_pid=getattr(process, "pid", None),
                        returncode=getattr(process, "returncode", None),
                        workdir=str(getattr(child, "_workdir", None)))
        finally:
            self._started.clear()
            for subscription in self._subscriptions:
                c.bus.unsubscribe(subscription)
            self._subscriptions.clear()
            self._events.clear()
            self._session = ""
            self._rejected_text = None
        proven = clean and self._cleanup_proof(c, handles)
        if self._recorder is not None:
            self._recorder.record("cleanup_complete", cleanup_proven=proven)
        return proven

    async def run(self):
        result = await self.harness.run(self._scenario,
            derive_profile=self._diagnostic_windows is None)
        result.update(replacement_completed=self.replacement_completed,
            human_capture_windows=self.human_turns, automatic_fill_turns=self.automatic_turns,
            input_mode="five_human_with_automatic_fill" if self._auto_fill else "human_only",
            new_conversation_answered=self._repeat_verified,
            repeat_verified=None, semantic_review="agent_required",
            post_replacement_generated_turns=self.post_replacement_generated_turns,
            successful_turns=self.generated_turns,
            cleanup_proven=self.harness.cleanup_proven)
        if self._recorder is not None and not self._auto_fill:
            result.update(status="DiagnosticComplete",
                          successful_turns=self.generated_turns,
                          replacement_completed=self.replacement_completed)
        return result


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
            or health["oom_kill"] != 0
            or health["thermal_celsius"] >= 80 or health["throttled_bits"] != 0):
        raise MetricsError("M4B_MEASUREMENT_STARTUP_UNSAFE")
    return health


def build_native(args, recorder: _DiagnosticRecorder | None = None):
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
    if args.user_authorized_diagnostic:
        if recorder is None:
            raise MetricsError("M4B_MEASUREMENT_DIAGNOSTIC_MISSING")
        grant = MeasurementGrant.user_diagnostic(expected_tuple=expected, profile=profile,
            diagnostic_directory=recorder.root)
    else:
        grant = MeasurementGrant.load(args.authorization, expected_tuple=expected, profile=profile)
    cfg = LLMConfig(driver="litert_lm", runtime_python=args.runtime_python,
        model_path=args.model, product_profile_path=args.product_profile,
        artifact_lock_path=args.artifact_lock, profile_id=profile["profile_id"])
    _validate_shape(cfg)
    lock = LLMArtifactLock.load(args.artifact_lock, repo_root=ROOT)
    # The uncommitted user diagnostic is not formal evidence. Its isolated
    # child performs the complete runtime/model/profile verification once,
    # immediately before native import; avoid two redundant parent-side hashes
    # of the 2.6 GB model. Formal measurement retains the parent checks.
    if not args.user_authorized_diagnostic:
        profile = lock.verify_config_paths(cfg, allow_measurement=True)
    lock = replace(lock, identity=lock.ready_identity(profile), product_profile=profile)
    audio_input, audio_output = make_audio_input(config.core.audio), make_audio_output(config.core.audio)
    if recorder is not None:
        audio_input = _DiagnosticAudioInput(audio_input, recorder)
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
    authorization = None if args.user_authorized_diagnostic else json.loads(args.authorization.read_text())
    return NativeMeasurementSession(components, authorization=authorization, expected_tuple=expected,
        user_authorized_diagnostic=args.user_authorized_diagnostic,
        auto_fill=False,
        diagnostic_windows=getattr(args, "diagnostic_windows", None),
        max_turns=args.max_turns, listen_timeout_seconds=(10.0
            if getattr(args, "diagnostic_windows", None)
            else config.perception.timeout_seconds.listen),
        startup_health=_startup_health, recorder=recorder)


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
