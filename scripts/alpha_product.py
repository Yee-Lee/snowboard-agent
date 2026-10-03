#!/usr/bin/env python3
"""Instrument the delivered App entrypoint without replacing its composition or supervisor.

The only input substitution is fixed local PCM at AudioInput.frames. GPIO callback
stimuli use the real ButtonInputSource; all backend execution remains production.
Observations and raw answers are private, mode 0600, and never printed.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import deque
from contextlib import ExitStack
import json
import logging
import os
import re
from pathlib import Path
import signal
import sys
import time
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts.alpha_oracle import FIXTURES, QUALITY, InvalidObservation, require

FIXTURE_TEXT = dict(zip(FIXTURES, (
    "一個星期有幾天？", "一個星期有幾天？", "請再簡短回答一次。",
    "請列出三個滑雪安全重點。", "現在請結束對話。", "請問你是誰？",
    "一個星期有幾天？", "你現在可以看到我前面的東西嗎？",
    "用一句話說初學滑雪為何要戴安全帽。", "請簡短介紹台灣。",
    "再簡單一點，並且只說它的位置。", "請不要結束對話，先告訴我一加一等於多少。",
    "現在請結束對話。"), strict=True))


async def prepare_fixtures(config_path: Path, output: Path) -> None:
    """Bind fixtures once before the four runs, using the offline production TTS."""
    import sbd.main  # Native thread policy, before backend imports.
    from sbd.core.config import load_config
    from sbd.action.speak import make_tts_adapter
    config = load_config(local_path=config_path)
    require(config.action.tts.driver == "sherpa_matcha", "PRODUCTION_TTS_REQUIRED")
    output = output.resolve()
    require(not output.is_relative_to(ROOT), "FIXTURES_INSIDE_REPOSITORY")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    tts = make_tts_adapter(config.action.tts)
    mapping, already_bound = {}, {}
    try:
        await tts.start()
        for identity, text in FIXTURE_TEXT.items():
            if text in already_bound:
                mapping[identity] = already_bound[text]
                continue
            path = output / f"{identity}.wav"
            pcm = tts.synthesize(text)
            try:
                with wave.open(str(path), "wb") as wav:
                    os.chmod(path, 0o600)
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(16000)
                    # Fixed leading/trailing silence supports the accepted ASR endpoint.
                    wav.writeframes(b"\0" * 16000)
                    count = 0
                    async for chunk in pcm:
                        require(type(chunk) is bytes and len(chunk) % 2 == 0, "FIXTURE_PCM_INVALID")
                        wav.writeframes(chunk)
                        count += len(chunk)
                    require(count > 0, "FIXTURE_PCM_EMPTY")
                    wav.writeframes(b"\0" * 32000)
            finally:
                await pcm.aclose()
            mapping[identity] = already_bound[text] = path.name
        private_json(output / "fixtures.json", mapping)
    finally:
        await tts.stop()


def private_json(path: Path, value: object) -> None:
    # Only fresh output paths are accepted by the coordinator.
    with path.open("x", encoding="utf-8") as sink:
        os.chmod(path, 0o600)
        json.dump(value, sink, ensure_ascii=False, separators=(",", ":"))
        sink.write("\n")


class PublicLogObservation:
    """Observe actual console/file emissions, including rotated file handlers."""
    def __init__(self):
        self.messages = []
        self.secrets = []  # Memory only; never written into private/public observations.
        self.original = logging.Handler.handle

    def handle(self, handler, record):
        emitted = self.original(handler, record)
        if emitted and isinstance(handler, logging.StreamHandler):
            rendered = handler.format(record)
            try:
                parsed = json.loads(rendered)
                rendered = json.dumps(parsed, ensure_ascii=False)
                message = parsed.get("message", "") if isinstance(parsed, dict) else (
                    record.getMessage() if not isinstance(parsed, list) else "")
            except ValueError:
                message = record.getMessage() if rendered == record.getMessage() or rendered.endswith(
                    " " + record.getMessage()) else ""
            self.messages.append((message, rendered))
        return emitted

    def matches(self, turns):
        from sbd.cognition.prompt_builder import SYSTEM_PROMPT
        samples = {SYSTEM_PROMPT}
        for turn in turns:
            samples.update(item.get("text", "") for item in turn.get("asr", []))
            samples.update(item.get("payload", {}).get("text", "")
                           for item in turn.get("responses", []))
        fields = re.compile(r'''(?:["'](?:text|transcript|prompt|raw_model_output|credential|password|pcm|audio_payload)["']\s*:|\b(?:transcript|prompt|credential|password|pcm|audio_payload)=)''')
        return sum(bool(fields.search(rendered)) or any(secret and secret in rendered for secret in self.secrets) or any(
            sample and (message == sample or (len(sample) >= 4 and sample in rendered))
            for sample in samples) for message, rendered in self.messages)


def resolve_fixtures(path: Path, needed: set[str]) -> dict[str, bytes]:
    mapping = json.loads(path.read_text(encoding="utf-8"))
    require(type(mapping) is dict and needed <= set(mapping) <= set(FIXTURES), "FIXTURE_MAPPING_INVALID")
    result = {}
    for identity in needed:
        source = Path(mapping[identity])
        if not source.is_absolute():
            source = path.parent / source
        with wave.open(str(source), "rb") as wav:
            require((wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getcomptype())
                    == (16000, 1, 2, "NONE"), "FIXTURE_FORMAT_INVALID")
            value = wav.readframes(wav.getnframes())
        require(bool(value) and len(value) % 2 == 0, "FIXTURE_PCM_INVALID")
        result[identity] = value  # One immutable binding, shared by P02 and P03.
    return result


def session_plan(run: str) -> list[list[tuple[str, str, str]]]:
    end = ("CLOSE", "FX-NORMAL-END", "END_SESSION")
    if run == "lifecycle":
        return [[(f"L{i}-T1", "FX-SHORT-A", "KEEP_NEXT"),
                 (f"L{i}-T2", "FX-NORMAL-END", "END_SESSION")] for i in range(1, 4)]
    if run == "performance":
        return [[("P02-FIRST-TURN", "FX-SHORT-B", "KEEP_NEXT"),
                 ("P04-FOLLOW-UP", "FX-FOLLOW-UP", "KEEP_NEXT"), end],
                [("P03-WARM-SESSION", "FX-SHORT-B", "KEEP_NEXT"),
                 ("P05-STREAMING", "FX-MULTI-FRAGMENT", "KEEP_NEXT"), end]]
    if run == "recovery":
        return [[("FAULT", "FX-MULTI-FRAGMENT", "KEEP_NEXT")],
                [("RECOVERED", "FX-SHORT-A", "KEEP_NEXT"), end]]
    return [[(QUALITY[i], f"FX-Q{i+1:02d}", "KEEP_NEXT"), end] for i in range(4)] + [
        [(QUALITY[4], "FX-Q05-T1", "KEEP_NEXT"), (QUALITY[4], "FX-Q05-T2", "KEEP_NEXT")],
        [(QUALITY[5], "FX-Q06-T1", "KEEP_NEXT"), (QUALITY[5], "FX-Q06-T2", "END_SESSION")]]


def process_identity(pid: int) -> tuple[str, str] | None:
    try:
        parts = (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
        return parts[19], parts[0]
    except (OSError, IndexError):
        return None


def hardware_fds() -> dict[str, int]:
    counts = {"alsa": 0, "display_owner": 0, "hardware_owners": 0}
    for fd in Path("/proc/self/fd").iterdir():
        try:
            target = os.readlink(fd)
        except FileNotFoundError:
            continue
        if target.startswith("/dev/snd/"):
            counts["alsa"] += 1
        if target.startswith(("/dev/spidev", "/dev/fb", "/dev/dri/")):
            counts["display_owner"] += 1
        if target.startswith(("/dev/snd/", "/dev/spidev", "/dev/fb", "/dev/dri/",
                              "/dev/gpiochip", "/dev/video", "/dev/media")):
            counts["hardware_owners"] += 1
    return counts


def process_reaped(process) -> bool:
    return (process is not None and process.returncode is not None
            and process_identity(process.pid) is None)


class ProductProbe:
    def __init__(self, run: str, fixtures: dict[str, bytes], process_start: int):
        self.run, self.fixtures = run, fixtures
        self.plan = session_plan(run)
        self.pending = deque()
        self.rows = []
        self.current = None
        self.sessions = []
        self.close_counts = {}
        self.children = {}
        self.llm_children = []
        self.resource_ready = {}
        self.errors = []
        self.late_audio = self.stale_facts = self.late_fragments = 0
        self.buttons = 0
        self.task = None
        self.sm = self.rm = self.bus = self.composition = None
        self.recovery = {}
        self.failed_control = None
        self.killed = None
        self.killed_process = None
        self.initial_pids = None
        self.first_child = None
        self.failed_session = None
        self.rejection_task = None
        self.closing_quality_context = False
        self.opened = []
        self.startup = {"process_start": process_start}
        self.result = {"driver_complete": False, "failure_code": "DRIVER_INCOMPLETE"}

    async def until(self, predicate) -> None:
        while not predicate():
            if self.sm._loop_task.done():
                self.sm._loop_task.result()
                raise InvalidObservation("APP_STOPPED_EARLY")
            await asyncio.sleep(0.005)

    def backend_pids(self) -> set[int]:
        pids = set()
        for record in self.rm._records.values():
            if not record.spec.key.startswith("backend."):
                continue
            child = getattr(record.instance, "_child", None)
            pid = getattr(child, "pid", 0)
            if type(pid) is int and pid > 0:
                pids.add(pid)
                self.children.setdefault(pid, process_identity(pid))
        return pids

    def idle_snapshot(self) -> dict:
        arbiter = self.rm._records["core.display.arbiter"].instance
        display = arbiter.snapshot()
        status = dict(display.status_slots).get("state")
        llm = self.rm._records["backend.cognition.reasoner.llm"].instance
        return {"conversation_absent": self.sm._session is None and llm._ledger.claim is None,
                "main_empty": display.main is None,
                "display_idle": self.sm.state == "IDLE" and status is not None
                                and status.data.get("state") == "IDLE",
                "resources_ready": all(r.started and not r.using_null for r in self.rm._records.values()
                                       if r.spec.required)}

    def barrier(self, session_id: str) -> dict:
        speak = self.composition._speak_worker
        control = speak._streaming
        snapshot = self.idle_snapshot()
        inflight = tuple(self.sm._in_flight.values())
        return {**{key: snapshot[key] for key in ("conversation_absent", "main_empty", "display_idle")},
                "close_count": self.close_counts.get(session_id, 0),
                "session_tasks": sum(not record.task.done() for record in inflight),
                "streaming_controls": int(control is not None),
                "queue_depth": 0 if control is None else control.queue_depth,
                "inflight": len(inflight), "late_audio": self.late_audio,
                "stale_facts": self.stale_facts, "late_fragments": self.late_fragments,
                "backend_reused": self.backend_pids() == self.initial_pids}

    def frames(self):
        async def stream():
            if not self.pending and self.closing_quality_context:
                # KEEP_NEXT may arm capture before the runner's close Button is dispatched.
                # Supply no third fixture/ASR result; normal product interruption cancels it.
                await asyncio.Event().wait()
            require(bool(self.pending), "UNPLANNED_TURN")
            case, identity, route = self.pending.popleft()
            session = self.sm._session
            require(session is not None, "PCM_WITHOUT_SESSION")
            row = {"case_id": case, "fixture_id": identity, "expected_route": route,
                   "session_id": session.session_id, "turn_id": session.turn_id,
                   "nodes": {"next_perception_start": time.monotonic_ns()}, "fragments": [],
                   "asr": [], "responses": [], "actions": [], "delivered": [], "runtime": []}
            if self.rows:
                row["nodes"]["previous_action_complete"] = self.rows[-1]["nodes"].get("audio_complete")
            self.rows.append(row)
            self.current = row
            payload = self.fixtures[identity]
            try:
                for offset in range(0, len(payload), 640):
                    frame = payload[offset:offset + 640].ljust(640, b"\0")
                    if any(frame):
                        # Controlled PCM speech end: last non-silent frame actually delivered.
                        row["nodes"]["speech_end"] = time.monotonic_ns()
                    yield frame
                    await asyncio.sleep(0)  # No artificial real-time playback pacing.
            finally:
                row["capture_closed"] = True
        return stream()

    def matching_row(self, event):
        for row in reversed(self.rows):
            if (row["session_id"], row["turn_id"]) == (event.session_id, event.turn_id):
                return row
        return None

    def observe(self, row: dict) -> None:
        current = self.current
        if current is None:
            return
        if row["dashboard"] == "timing":
            for name, node in row["values"]["events"].items():
                current["nodes"][{"tts_pcm_ready": "tts_first_pcm"}.get(name, name)] = node["monotonic_ns"]
        elif row["dashboard"] == "runtime":
            current["runtime"].append(row["values"])

    def attach(self, composition, rm, bus, config) -> None:
        require(config.core.audio.driver == "alsa" and config.core.gpio.driver == "gpiod"
                and config.core.display.driver == "ssd1351" and config.core.display.show_session_content
                and config.perception.listen.adapter.driver == "whispercpp"
                and config.cognition.llm.driver == "litert_lm"
                and config.action.tts.driver == "sherpa_matcha"
                and config.input_sources.button.policy.enabled, "PRODUCTION_CONFIG_REQUIRED")
        self.composition, self.rm, self.bus, self.sm = composition, rm, bus, rm._state_manager
        composition._cognition_observer._sink = self.observe
        from sbd.core.events import PerceptionResult, LLMResponse, ActionCompleted, ErrorOccurred

        async def terminal(event):
            row = self.matching_row(event)
            session = self.sm._session
            if row is None or session is None or (event.session_id, event.turn_id) != (
                    session.session_id, session.turn_id):
                self.stale_facts += 1
            if row is None:
                return
            if isinstance(event, PerceptionResult):
                row["asr"].append({"status": event.status, "text": event.text})
            elif isinstance(event, LLMResponse):
                row["responses"].append({"kind": event.action_kind, "payload": event.action_payload,
                                         "route": event.post_action_route})
            else:
                row["actions"].append({"kind": event.kind, "status": event.status})
                if event.kind == "speak":
                    row["nodes"]["audio_complete"] = time.monotonic_ns()

        async def fault(event):
            self.errors.append({"code": event.code, "disposition": event.backend_disposition,
                                "keys": list(event.recovery_keys)})

        for kind in (PerceptionResult, LLMResponse, ActionCompleted):
            bus.subscribe(kind, terminal, name=f"alpha.{kind.__name__}")
        bus.subscribe(ErrorOccurred, fault, name="alpha.error")

    async def button(self, *, shutdown=False) -> None:
        from sbd.core.gpio.base import GPIOEvent
        source = self.composition.button
        config = source._config
        pin = source._pin_config
        now = time.monotonic()
        duration = config.long_press_min_ms if shutdown else config.short_press_min_ms
        press = "falling" if pin.active_low else "rising"
        release = "rising" if pin.active_low else "falling"
        await source._on_gpio_event(GPIOEvent(pin.pin, press, now))
        await source._on_gpio_event(GPIOEvent(pin.pin, release, now + duration / 1000))
        if not shutdown:
            self.buttons += 1

    async def normal_session(self, plan) -> None:
        context_case = self.run == "quality" and plan[0][0] == QUALITY[4]
        self.closing_quality_context = context_case
        first_row = len(self.rows)
        self.pending.extend(plan)
        await self.button()
        # PCM admission records the actual Session identity durably. A short
        # Session can complete between polls of the live State Manager pointer.
        await self.until(lambda: len(self.rows) > first_row)
        session_id = self.rows[first_row]["session_id"]
        if context_case:
            await self.until(lambda: any(row["case_id"] == QUALITY[4] and row["fixture_id"] == "FX-Q05-T2"
                                        and any(a["kind"] == "speak" and a["status"] == "ok"
                                                for a in row["actions"]) and bool(row["runtime"])
                                        for row in self.rows)
                             or self.sm._session is None)
            if self.sm._session is not None:
                # Formal short press closes the two-turn case; no third voice stimulus is admitted.
                await self.button()
        await self.until(lambda: self.sm.state == "IDLE" and self.sm._session is None)
        await self.sm._inbox.join()
        require(not self.pending, "SESSION_ENDED_BEFORE_FIXTURES")
        self.sessions.append(self.barrier(session_id))
        self.closing_quality_context = False

    async def stimulate(self) -> None:
        try:
            self.startup["idle"] = time.monotonic_ns()
            self.startup["resources_ready"] = self.resource_ready
            self.result["initial"] = self.idle_snapshot()
            self.initial_pids = self.backend_pids()
            self.first_child = self.rm._records["backend.cognition.reasoner.llm"].instance._child
            if self.run == "restart":
                self.result["driver_complete"] = True
                return
            if self.run == "recovery":
                self.pending.extend(self.plan[0])
                await self.button()
                await self.until(lambda: self.killed is not None)
                await self.until(lambda: self.sm.state == "IDLE" and self.sm._session is None)
                await self.sm._inbox.join()
                llm = self.rm._records["backend.cognition.reasoner.llm"].instance
                replacement = llm._child
                old = self.killed
                self.recovery.update(
                    fault_locator=self.errors == [{"code": "LLM_BACKEND_FAILED",
                        "disposition": "rebuild_required", "keys": ["backend.cognition.reasoner.llm"]}],
                    old_reaped=process_reaped(self.killed_process),
                    new_child=replacement is not old and replacement.pid != old.pid,
                    sole_replacement=len(self.llm_children) == 2,
                    replacement_count=len(self.llm_children) - 1,
                    ready_before_admission=llm._ledger.claim is None and self.rm.recovery_ready(),
                    failed_work_empty=not self.sm._in_flight and self.composition._speak_worker._streaming is None
                                      and self.failed_control.queue_depth == 0 and not self.failed_control._inflight
                                      and self.failed_control._pcm is None,
                    failed_normal_terminals=len(self.rows[0]["responses"]) + sum(
                        a["status"] == "ok" for a in self.rows[0]["actions"]),
                    future_fragments=len(self.failed_control._admitted) - self.recovery["admitted_at_kill"])
                self.initial_pids = self.backend_pids()
                await self.normal_session(self.plan[1])
                self.recovery["new_conversation"] = self.rows[1]["session_id"] != self.failed_session
                self.recovery["old_context_absent"] = self.opened[-1]["empty_history"]
            else:
                for plan in self.plan:
                    await self.normal_session(plan)
                require(not self.errors, "UNEXPECTED_PRODUCT_ERROR")
            self.result["driver_complete"] = True
        except Exception as error:
            self.result["failure_code"] = error.code if isinstance(error, InvalidObservation) else "DRIVER_FAILED"
            if getattr(self, "failure_path", None) is not None:
                private_json(self.failure_path, {**self.result, "turns": self.rows, "sessions": self.sessions})
        finally:
            await self.button(shutdown=True)

    def finish_turns(self) -> None:
        for row in self.rows:
            responses, actions = row["responses"], row["actions"]
            response = responses[0] if len(responses) == 1 else None
            text = "" if response is None else response["payload"].get("text", "")
            generated = any(v.get("admission_result") == "GENERATE" for v in row["runtime"])
            legal = False
            if response is not None:
                try:
                    self.composition.action_validator.validate(response["kind"], response["payload"])
                    legal = response["kind"] in {"speak", "rest"}
                except Exception:
                    pass
            speech_required = bool(text)
            completed = [a for a in actions if a["kind"] == "speak"]
            row.update(asr_terminal=len(row["asr"]) == 1 and row["asr"][0]["status"] == "ok",
                       llm_terminal=response is not None and generated,
                       schema_valid=legal,
                       route_valid=response is not None and response["route"] == row["expected_route"],
                       response_nonempty=bool(text) or row["expected_route"] == "END_SESSION",
                       speech_equal="".join(row["delivered"]) == text,
                       protocol_clear=not any(marker in "".join(row["delivered"]) for marker in
                           ("<start_of_turn>", "<end_of_turn>", '"text":', '"end":', "SAFE_TEXT")),
                       audio_complete=(len(completed) == 1 and completed[0]["status"] == "ok"
                                       if speech_required else not completed)
                                      and all(a["status"] == "ok" for a in actions))

    def performance(self) -> list:
        cases = [{"case_id": "P01-STARTUP", "nodes": self.startup}]
        for row in self.rows:
            identity = row["case_id"]
            if identity == "CLOSE":
                continue
            item = {"case_id": identity, "nodes": row["nodes"]}
            if identity == "P04-FOLLOW-UP":
                values = row["runtime"][-1] if row["runtime"] else {}
                item["token_counts"] = {"input_tokens": values.get("user_tokens"),
                                        "context_tokens": values.get("current_kv_tokens")}
            elif identity == "P03-WARM-SESSION":
                item["reuse"] = {"engine_reused": len(self.llm_children) == 1,
                                  "child_reused": self.first_child is self.llm_children[-1]}
            elif identity == "P05-STREAMING":
                item["nodes"]["final_drain"] = row["nodes"].get("audio_complete")
                item["fragments"] = row["fragments"]
            cases.append(item)
        return cases


async def launch(args) -> int:
    # Import main first: it sets native thread policy before product imports.
    import sbd.main as app_main
    from sbd.core.m3_composition import M3Composition
    from sbd.core.resource_manager import ResourceManager
    from sbd.cognition.litert_lm.adapter import LiteRTLMAdapter, SubprocessLLMChild
    from sbd.action.speak.streaming import StreamingSpeakControl
    from sbd.core.state_manager import StateManager
    from sbd.core.events import ButtonPressed

    plan = session_plan(args.run) if args.run != "restart" else []
    needed = {fixture for session in plan for _, fixture, _ in session}
    fixtures = resolve_fixtures(args.fixtures, needed)
    probe = ProductProbe(args.run, fixtures, args.process_start_ns)
    probe.failure_path = args.observation.with_name(f"{args.observation.stem}-failure.json")
    originals = {"compose": M3Composition.__call__, "start_one": ResourceManager._start_one,
                 "ready": app_main.logger.info, "config": app_main.load_config,
                 "llm_start": SubprocessLLMChild.start, "open": LiteRTLMAdapter.open_conversation,
                 "close": LiteRTLMAdapter.close_conversation, "feed": StreamingSpeakControl.feed,
                 "dequeue": StreamingSpeakControl._dequeue,
                 "handle": StateManager._handle_item,
                 "recovery": ResourceManager.begin_recovery}

    def config(*a, **kw):
        value = originals["config"](*a, **kw)
        if args.run in {"lifecycle", "restart"} and value.adaptors.mqtt.password is not None:
            logs.secrets.append(value.adaptors.mqtt.password.reveal())
        probe.startup["config_complete"] = time.monotonic_ns()
        return value

    def compose(self, rm, bus, cfg):
        originals["compose"](self, rm, bus, cfg)
        probe.attach(self, rm, bus, cfg)

    async def start_one(self, spec):
        await originals["start_one"](self, spec)
        record = self._records[spec.key]
        if spec.required and record.started:
            probe.resource_ready[spec.key] = time.monotonic_ns()
        if spec.key == "core.audio.input":
            record.instance.frames = probe.frames
        if spec.key == "core.audio.output":
            output = record.instance
            play = output.play

            async def observed_play(pcm):
                row = probe.current
                if probe.sm._session is None:
                    probe.late_audio += 1
                fragments = [] if row is None else [f for f in row["fragments"] if "tts_start" in f
                                                    and "audio_start" not in f]
                started = time.monotonic_ns()
                for fragment in fragments:
                    fragment["audio_start"] = started
                await play(pcm)
                complete = time.monotonic_ns()
                for fragment in fragments:
                    fragment["audio_complete"] = complete
            output.play = observed_play
        if spec.key == "backend.action.speak.tts":
            tts = record.instance
            synthesize = tts.synthesize

            def observed_synthesize(text):
                row = probe.current
                stamp = time.monotonic_ns()
                batch = [] if row is None else [f for f in row["fragments"]
                                                if f.get("dequeued") and "tts_start" not in f]
                if row is not None:
                    row["delivered"].append(text)
                for fragment in batch:
                    fragment["tts_start"] = stamp

                async def pcm():
                    source = synthesize(text)
                    try:
                        async for chunk in source:
                            if chunk:
                                now = time.monotonic_ns()
                                for fragment in batch:
                                    fragment.setdefault("tts_first_pcm", now)
                            yield chunk
                    finally:
                        await source.aclose()
                return pcm()
            tts.synthesize = observed_synthesize

    def ready(message, *a, **kw):
        originals["ready"](message, *a, **kw)
        if message == "M2 runtime ready state=IDLE":
            probe.task = asyncio.create_task(probe.stimulate())

    async def llm_start(self):
        result = await originals["llm_start"](self)
        probe.llm_children.append(self)
        probe.children[self.pid] = process_identity(self.pid)
        return result

    async def opened(self, sid, generation):
        value = await originals["open"](self, sid, generation)
        probe.opened.append({"session_id": sid, "empty_history": self._ledger.revision == 0})
        return value

    async def closed(self, sid, generation, reason):
        value = await originals["close"](self, sid, generation, reason)
        probe.close_counts[sid] = probe.close_counts.get(sid, 0) + 1
        return value

    async def feed(self, sid, turn, sequence, text):
        await originals["feed"](self, sid, turn, sequence, text)
        row = probe.current
        if row is None or (row["session_id"], row["turn_id"]) != (sid, turn):
            probe.late_fragments += 1
            return
        row["fragments"].append({"admission": time.monotonic_ns(),
                                 "queue_entry_depth": self.queue_depth, "sequence": sequence})
        if probe.run == "recovery" and probe.killed is None:
            llm = probe.rm._records["backend.cognition.reasoner.llm"].instance
            child = llm._child
            require(child is not None and child._process.returncode is None
                    and len(probe.llm_children) == 1, "LLM_KILL_TARGET_INVALID")
            probe.killed, probe.failed_control = child, self
            probe.killed_process = child._process
            probe.failed_session = sid
            probe.recovery.update(killed_sole_llm=True, after_safe_admission=True,
                                  admitted_at_kill=self.admitted_count)
            os.kill(child.pid, signal.SIGKILL)  # Exactly one real-child termination request.

    async def dequeue(self):
        batch = await originals["dequeue"](self)
        if batch is not None and probe.current is not None:
            sequences = {fragment.sequence for fragment in batch}
            for row in probe.current["fragments"]:
                if row["sequence"] in sequences:
                    row["dequeued"] = True
        return batch

    def recovery(self, keys):
        ticket = originals["recovery"](self, keys)
        if probe.run == "recovery":
            snapshot = probe.rm._records["core.display.arbiter"].instance.snapshot()
            state = dict(snapshot.status_slots).get("state")
            main = None if snapshot.main is None else snapshot.main.data.get("text")
            provisional = "".join(probe.failed_control._admitted)
            probe.recovery["error_display_clear"] = (state is not None and state.data.get("state") == "ERROR"
                                                      and (main is None or main != provisional))

            async def reject_button():
                await probe.button()
                await probe.sm._inbox.join()
            probe.rejection_task = asyncio.create_task(reject_button())
        return ticket

    async def handle(self, item):
        barrier_button = (isinstance(item, ButtonPressed) and probe.run == "recovery"
                          and self.state == "ERROR" and self._pending is not None
                          and self._pending.recovery_generation is not None
                          and not probe.rm.recovery_ready())
        opened_before = len(probe.opened)
        await originals["handle"](self, item)
        if barrier_button:
            probe.recovery["barrier_rejected"] = len(probe.opened) == opened_before

    logs = PublicLogObservation()
    with ExitStack() as stack:
        if args.run in {"lifecycle", "restart"}:
            stack.enter_context(patch.object(logging.Handler, "handle",
                lambda handler, record: logs.handle(handler, record)))
        for target, replacement in (("sbd.main.load_config", config),
            ("sbd.main.logger.info", ready),
            ("sbd.core.m3_composition.M3Composition.__call__", compose),
            ("sbd.core.resource_manager.ResourceManager._start_one", start_one),
            ("sbd.core.resource_manager.ResourceManager.begin_recovery", recovery),
            ("sbd.core.state_manager.StateManager._handle_item", handle),
            ("sbd.cognition.litert_lm.adapter.SubprocessLLMChild.start", llm_start),
            ("sbd.cognition.litert_lm.adapter.LiteRTLMAdapter.open_conversation", opened),
            ("sbd.cognition.litert_lm.adapter.LiteRTLMAdapter.close_conversation", closed),
            ("sbd.action.speak.streaming.StreamingSpeakControl._dequeue", dequeue),
            ("sbd.action.speak.streaming.StreamingSpeakControl.feed", feed)):
            stack.enter_context(patch(target, replacement))
        exit_code = await app_main.run_app(str(args.config))
        if probe.task is not None:
            if not probe.task.done():
                probe.task.cancel()
            await asyncio.gather(probe.task, return_exceptions=True)
        if probe.rejection_task is not None:
            await asyncio.gather(probe.rejection_task, return_exceptions=True)
        probe.finish_turns()
        counts = hardware_fds()
        probe.result.update(exit_code=exit_code, turns=probe.rows, sessions=probe.sessions,
                            buttons=probe.buttons, recovery=probe.recovery,
                            child_identities={str(pid): identity for pid, identity in probe.children.items()},
                            app_pid=os.getpid(),
                            cleanup={"app_absent": False,
                                "children_absent": all(process_identity(pid) is None for pid in probe.children),
                                "alsa_absent": counts["alsa"] == 0,
                                "display_owner_absent": counts["display_owner"] == 0,
                                "hardware_owners_absent": counts["hardware_owners"] == 0})
        if args.run == "performance":
            probe.result["performance"] = probe.performance()
        if args.run in {"lifecycle", "restart"}:
            probe.result["log_privacy_matches"] = logs.matches(probe.rows)
            probe.result["log_observed"] = bool(logs.messages)
        private_json(args.observation, probe.result)
    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", choices=("lifecycle", "performance", "recovery", "quality", "restart"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--observation", type=Path)
    parser.add_argument("--process-start-ns", type=int)
    parser.add_argument("--prepare-fixtures", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.prepare_fixtures is not None:
            asyncio.run(prepare_fixtures(args.config, args.prepare_fixtures))
            print(json.dumps({"fixture_count": len(FIXTURE_TEXT)}))
            return
        require(args.run is not None and args.fixtures is not None and args.observation is not None
                and args.process_start_ns is not None, "DRIVER_ARGUMENTS_REQUIRED")
        raise SystemExit(asyncio.run(launch(args)))
    except Exception:
        # Startup/precondition exceptions must never expose paths, credentials or text.
        if args.observation is not None and not args.observation.exists():
            private_json(args.observation, {"driver_complete": False, "failure_code": "DRIVER_STARTUP_FAILED"})
        raise SystemExit(2)


if __name__ == "__main__":
    main()
