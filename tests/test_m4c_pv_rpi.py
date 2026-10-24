"""Exact-product M4C Raspberry Pi scenario entry."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import time
from typing import Any

import pytest

from sbd.core.config import load_config
from sbd.core.event_bus import EventBus
from sbd.core.events import (
    ActionCompleted, ButtonPressed, ErrorOccurred, LLMResponse, PerceptionResult,
    ShutdownRequested, StateChanged,
)
from sbd.core.faults import safe_category_for_code
from sbd.core.m3_composition import M3Composition
from sbd.core.resource_manager import ResourceManager
from sbd.core.state_manager import StateManager
from sbd.core.state_manager.convergence import CancelTimeoutPolicy, DefaultSessionConverger


pytestmark = pytest.mark.rpi
ROOT = Path(__file__).resolve().parents[1]
ORACLE_SPEC = importlib.util.spec_from_file_location(
    "m4c_s02_oracle", ROOT / "scripts/m4c_s02_oracle.py"
)
assert ORACLE_SPEC is not None and ORACLE_SPEC.loader is not None
ORACLE = importlib.util.module_from_spec(ORACLE_SPEC)
ORACLE_SPEC.loader.exec_module(ORACLE)
S03_ORACLE_SPEC = importlib.util.spec_from_file_location(
    "m4c_s03_oracle", ROOT / "scripts/m4c_s03_oracle.py"
)
assert S03_ORACLE_SPEC is not None and S03_ORACLE_SPEC.loader is not None
S03_ORACLE = importlib.util.module_from_spec(S03_ORACLE_SPEC)
S03_ORACLE_SPEC.loader.exec_module(S03_ORACLE)
S04_ORACLE_SPEC = importlib.util.spec_from_file_location(
    "m4c_s04_oracle", ROOT / "scripts/m4c_s04_oracle.py"
)
assert S04_ORACLE_SPEC is not None and S04_ORACLE_SPEC.loader is not None
S04_ORACLE = importlib.util.module_from_spec(S04_ORACLE_SPEC)
S04_ORACLE_SPEC.loader.exec_module(S04_ORACLE)
S05_ORACLE_SPEC = importlib.util.spec_from_file_location(
    "m4c_s05_oracle", ROOT / "scripts/m4c_s05_oracle.py"
)
assert S05_ORACLE_SPEC is not None and S05_ORACLE_SPEC.loader is not None
S05_ORACLE = importlib.util.module_from_spec(S05_ORACLE_SPEC)
S05_ORACLE_SPEC.loader.exec_module(S05_ORACLE)


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def _write_stage(path: Path, stage: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(stage + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def _validate_product_config(config: Any) -> None:
    assert config.core.audio.driver == "alsa"
    assert config.core.audio.output.volume_percent == 25
    assert config.core.audio.input.device and config.core.audio.output.device
    assert config.core.gpio.driver == "gpiod"
    assert config.perception.listen.adapter.driver == "whispercpp"
    assert config.cognition.llm.driver == "litert_lm"
    assert config.action.tts.driver == "sherpa_matcha"
    assert config.input_sources.button.policy.enabled is True


def _main_text(arbiter: Any) -> str | None:
    hint = arbiter.snapshot().main
    if hint is None:
        return None
    value = hint.data.get("text")
    return value if type(value) is str else None


def _status_state(arbiter: Any) -> str | None:
    hint = dict(arbiter.snapshot().status_slots).get("state")
    if hint is None:
        return None
    value = hint.data.get("state")
    return value if type(value) is str else None


def _display_is_open(rm: ResourceManager) -> bool:
    record = rm._records["core.display"]
    display = record.instance
    return bool(
        record.started
        and (
            getattr(display, "_started", False) is True
            or (
                getattr(display, "_handle", 0) != 0
                and getattr(display, "_lib", None) is not None
            )
        )
    )


async def _run_s01(config: Any, stage_path: Path) -> dict[str, Any]:
    bus = EventBus()
    composition = M3Composition()
    rm = ResourceManager(config, bus)
    sm = StateManager(
        config, bus, rm.catalog, recovery=rm,
        action_validator=composition.action_validator,
    )
    rm.set_state_manager(sm)
    composition(rm, bus, config)

    states: list[str] = []
    perceptions: list[PerceptionResult] = []
    errors: list[ErrorOccurred] = []

    async def on_state(event: StateChanged) -> None:
        states.append(event.new)

    async def on_perception(event: PerceptionResult) -> None:
        perceptions.append(event)

    async def on_error(event: ErrorOccurred) -> None:
        errors.append(event)

    bus.subscribe(StateChanged, on_state, name="m4c.s01.state")
    bus.subscribe(PerceptionResult, on_perception, name="m4c.s01.perception")
    bus.subscribe(ErrorOccurred, on_error, name="m4c.s01.error")

    started = False
    try:
        _write_stage(stage_path, "STARTING")
        await sm.start()
        await rm.start()
        started = True
        await asyncio.sleep(0.25)
        await asyncio.wait_for(sm._inbox.join(), timeout=10)

        arbiter = rm._records["core.display.arbiter"].instance
        audio_input = rm._records["core.audio.input"].instance
        private = {
            "schema_version": 1,
            "state": sm.state,
            "state_changes": states,
            "session_created": sm._session is not None,
            "perception_count": len(perceptions),
            "audio_capture_active": getattr(audio_input, "_active", None) is not None,
            "status_state": _status_state(arbiter),
            "main_empty": _main_text(arbiter) is None,
            "display_open": _display_is_open(rm),
            "error_count": len(errors),
        }
        _write_json(stage_path.with_name("raw-observation.json"), private)
        assert private == {
            "schema_version": 1,
            "state": "IDLE",
            "state_changes": [],
            "session_created": False,
            "perception_count": 0,
            "audio_capture_active": False,
            "status_state": "IDLE",
            "main_empty": True,
            "display_open": True,
            "error_count": 0,
        }
        _write_stage(stage_path, "COMPLETE")
        return private
    finally:
        if started:
            await bus.publish(ShutdownRequested())
            await sm.wait_stopped()
            await rm.prepare_shutdown()
        await sm.stop()
        report = await rm.stop_all()
        assert report.failures == ()


async def _run_s02(config: Any, stage_path: Path) -> dict[str, Any]:
    bus = EventBus()
    composition = M3Composition()
    rm = ResourceManager(config, bus)
    converger = DefaultSessionConverger(timeouts=CancelTimeoutPolicy(
        abort_default_seconds=config.cancel.abort_timeout_seconds.default,
        force_abort_default_seconds=config.cancel.force_abort_timeout_seconds.default,
        abort_by_kind=config.cancel.abort_timeout_seconds.by_kind,
        force_abort_by_kind=config.cancel.force_abort_timeout_seconds.by_kind,
    ))
    sm = StateManager(
        config, bus, rm.catalog, converger=converger, recovery=rm,
        action_validator=composition.action_validator,
    )
    rm.set_state_manager(sm)
    composition(rm, bus, config)

    timestamps: dict[str, int] = {}
    states: list[str] = []
    perceptions: list[PerceptionResult] = []
    responses: list[LLMResponse] = []
    actions: list[ActionCompleted] = []
    action_timestamps: list[int] = []
    errors: list[ErrorOccurred] = []
    answer_displays: list[str | None] = []
    completed_play_counts: list[int] = []
    display_publications: list[tuple[str, str | None]] = []
    timing_rows: list[dict[str, Any]] = []
    idle = asyncio.Event()

    async def on_button(event: ButtonPressed) -> None:
        timestamps.setdefault("button_acceptance", time.monotonic_ns())

    async def on_perception(event: PerceptionResult) -> None:
        perceptions.append(event)

    async def on_response(event: LLMResponse) -> None:
        responses.append(event)

    async def on_action(event: ActionCompleted) -> None:
        actions.append(event)
        action_timestamps.append(time.monotonic_ns())
        if event.kind == "speak" and event.status == "ok":
            arbiter = rm._records["core.display.arbiter"].instance
            answer_displays.append(_main_text(arbiter))
            output = rm._records["core.audio.output"].instance
            completed_play_counts.append(output.raw_output.completed_play_count)

    async def on_state(event: StateChanged) -> None:
        states.append(event.new)
        if event.new == "PERCEPTION":
            perception_index = states.count("PERCEPTION")
            if perception_index == 1:
                _write_stage(stage_path, "SPEAK_TURN_1")
            elif perception_index == 2:
                _write_stage(stage_path, "SPEAK_TURN_2")
        elif event.new == "THINK":
            _write_stage(stage_path, f"THINK_TURN_{states.count('THINK')}")
        elif event.new == "ACTION":
            _write_stage(stage_path, f"ACTION_TURN_{states.count('ACTION')}")
        if event.new == "IDLE" and responses:
            timestamps["idle"] = time.monotonic_ns()
            _write_stage(stage_path, "COMPLETE")
            idle.set()

    async def on_error(event: ErrorOccurred) -> None:
        errors.append(event)
        category = safe_category_for_code(event.code)
        _write_json(stage_path.with_name("operator-error.json"), {
            "where": event.where,
            "code": event.code,
            "category": category,
            "backend_disposition": event.backend_disposition,
            "recovery_keys": list(event.recovery_keys),
        })
        _write_stage(stage_path, f"ERROR_{category.upper()}")
        idle.set()

    bus.subscribe(ButtonPressed, on_button, name="m4c.s02.button")
    bus.subscribe(PerceptionResult, on_perception, name="m4c.s02.perception")
    bus.subscribe(LLMResponse, on_response, name="m4c.s02.response")
    bus.subscribe(ActionCompleted, on_action, name="m4c.s02.action")
    bus.subscribe(StateChanged, on_state, name="m4c.s02.state")
    bus.subscribe(ErrorOccurred, on_error, name="m4c.s02.error")

    started = False
    try:
        await sm.start()
        composition._cognition_observer._sink = timing_rows.append
        await rm.start()
        started = True
        _write_stage(stage_path, "PRESS_BUTTON")
        arbiter = rm._records["core.display.arbiter"].instance
        original_write_main = arbiter.write_main

        def observed_write_main(hint) -> None:
            text = None if hint is None else hint.data.get("text")
            display_publications.append((sm.state, text))
            original_write_main(hint)

        arbiter.write_main = observed_write_main
        await asyncio.wait_for(idle.wait(), timeout=300)
        await asyncio.wait_for(sm._inbox.join(), timeout=10)

        # Persist the complete private observation ledger before adjudication.
        # A harness-only assertion defect can then be corrected and replayed
        # offline without asking the operator to repeat physical interaction.
        speak = composition._speak_worker
        _write_json(stage_path.with_name("raw-observation.json"), {
            "schema_version": 1,
            "timestamps": timestamps,
            "states": states,
            "perceptions": [asdict(item) for item in perceptions],
            "responses": [asdict(item) for item in responses],
            "actions": [asdict(item) for item in actions],
            "action_timestamps": action_timestamps,
            "answer_displays": answer_displays,
            "completed_play_counts": completed_play_counts,
            "display_publications": display_publications,
            "timing_rows": timing_rows,
            "streaming_history": [
                {"proof": asdict(proof), "fragments": list(fragments)}
                for proof, fragments in speak._streaming_history
            ],
            "streaming_completion_history": speak._streaming_completion_history,
            "final": {
                "state": sm.state,
                "main_text": _main_text(arbiter),
            },
        })

        assert not errors, repr(errors)
        assert len(perceptions) == 2
        assert all(type(item.text) is str and item.text.strip() for item in perceptions)
        assert len(responses) == 2
        assert [item.post_action_route for item in responses] == ["KEEP_NEXT", "END_SESSION"]
        assert actions and all(item.status == "ok" for item in actions)
        assert actions[0].kind == "speak"
        assert states == [
            "WAKE", "PERCEPTION", "THINK", "ACTION",
            "PERCEPTION", "THINK", "ACTION", "IDLE",
        ]

        assert len(speak._streaming_history) in {1, 2}
        assert len(speak._streaming_completion_history) == len(speak._streaming_history)
        first_proof, first_fragments = speak._streaming_history[0]
        first_terminal = responses[0].action_payload["text"]
        second_terminal = responses[1].action_payload.get("text", "")
        assert first_fragments and "".join(first_fragments) == first_terminal
        if second_terminal:
            assert [item.kind for item in actions] == ["speak", "speak", "rest"]
            _, second_fragments = speak._streaming_history[1]
            assert "".join(second_fragments) == second_terminal
            assert answer_displays == [first_terminal, second_terminal]
            assert display_publications == ORACLE.expected_display_publications(
                perceptions[0].text, first_terminal,
                perceptions[1].text, second_terminal,
            )
            turn2_branch = "nonempty_play_then_rest"
            turn2_completion = speak._streaming_completion_history[1]
        else:
            assert [item.kind for item in actions] == ["speak", "rest"]
            assert len(speak._streaming_history) == 1
            assert answer_displays == [first_terminal]
            assert display_publications == ORACLE.expected_display_publications(
                perceptions[0].text, first_terminal, perceptions[1].text, ""
            )
            turn2_branch = "empty_direct_rest"
            turn2_completion = action_timestamps[1]

        rows = [row for row in timing_rows if row.get("dashboard") == "timing"]
        assert len(rows) == 2
        first_timing = {
            key: node["monotonic_ns"] for key, node in rows[0]["values"]["events"].items()
        }
        second_timing = {
            key: node["monotonic_ns"] for key, node in rows[1]["values"]["events"].items()
        }
        assert all(value is not None for value in first_timing.values())
        assert first_timing["audio_first_write"] < first_timing["llm_terminal"]

        output = rm._records["core.audio.output"].instance
        play_count = output.raw_output.completed_play_count
        assert completed_play_counts and completed_play_counts[0] > 0
        if second_terminal:
            assert len(completed_play_counts) == 2
            assert completed_play_counts[0] < completed_play_counts[1] == play_count
        else:
            assert completed_play_counts == [play_count]
        assert _main_text(arbiter) is None

        timeline = {
            "button_acceptance": timestamps["button_acceptance"],
            "conversation_ready": first_timing["conversation_ready"],
            "asr_final": first_timing["asr_final"],
            "llm_send": first_timing["llm_send"],
            "first_safe_text": first_timing["first_safe_text"],
            "tts_first_pcm": first_timing["tts_pcm_ready"],
            "audio_first_write": first_timing["audio_first_write"],
            "llm_terminal": first_timing["llm_terminal"],
            "playback_complete": speak._streaming_completion_history[0],
            "drain_complete": speak._streaming_completion_history[0],
            "turn2_asr_final": second_timing["asr_final"],
            "turn2_llm_terminal": second_timing["llm_terminal"],
            "turn2_playback_complete": turn2_completion,
            "turn2_drain_complete": turn2_completion,
            "idle": timestamps["idle"],
        }
        return {
            "schema_version": 1,
            "streaming_path": "B2-ONE-LOOKAHEAD-COALESCE",
            "fragments": list(first_fragments),
            "terminal_text": first_terminal,
            "spoken_text": "".join(first_fragments),
            "display_text": answer_displays[0],
            "provisional_display_publications": 0,
            "timeline": timeline,
            "playback": {
                "admitted_fragment_count": len(first_fragments),
                "played_fragment_count": first_proof.fragment_count,
                "play_call_count": completed_play_counts[0],
                "drain_call_count": completed_play_counts[0],
                "complete": True,
            },
            "turn2": {
                "end": True,
                "branch": turn2_branch,
                "answer_length": len(second_terminal),
            },
            "cleanup": {
                "state": sm.state,
                "status": "待命",
                "main_empty": True,
            },
        }
    finally:
        if started:
            await bus.publish(ShutdownRequested())
            await sm.wait_stopped()
            await rm.prepare_shutdown()
        await sm.stop()
        report = await rm.stop_all()
        assert report.failures == ()


async def _run_s03(config: Any, stage_path: Path) -> dict[str, Any]:
    bus = EventBus()
    composition = M3Composition()
    rm = ResourceManager(config, bus)
    converger = DefaultSessionConverger(timeouts=CancelTimeoutPolicy(
        abort_default_seconds=config.cancel.abort_timeout_seconds.default,
        force_abort_default_seconds=config.cancel.force_abort_timeout_seconds.default,
        abort_by_kind=config.cancel.abort_timeout_seconds.by_kind,
        force_abort_by_kind=config.cancel.force_abort_timeout_seconds.by_kind,
    ))
    sm = StateManager(
        config, bus, rm.catalog, converger=converger, recovery=rm,
        action_validator=composition.action_validator,
    )
    rm.set_state_manager(sm)
    composition(rm, bus, config)

    states: list[str] = []
    perceptions: list[PerceptionResult] = []
    responses: list[dict[str, Any]] = []
    actions: list[ActionCompleted] = []
    streaks: list[int] = []
    errors: list[ErrorOccurred] = []
    order: list[str] = []
    display_publications: list[tuple[str, str | None]] = []
    completed_play_counts: list[int] = []
    reasoner_call_count = 0
    idle = asyncio.Event()

    async def on_perception(event: PerceptionResult) -> None:
        perceptions.append(event)
        order.append(f"timeout_{len(perceptions)}")

    async def on_action(event: ActionCompleted) -> None:
        actions.append(event)
        if event.kind == "speak":
            output = rm._records["core.audio.output"].instance
            completed_play_counts.append(output.raw_output.completed_play_count)
            order.append("retry_speak_complete")
        elif event.kind == "rest":
            order.append("rest_complete")

    async def on_state(event: StateChanged) -> None:
        states.append(event.new)
        if event.new == "PERCEPTION":
            index = states.count("PERCEPTION")
            _write_stage(stage_path, f"SILENT_WINDOW_{index}")
            if index == 2:
                order.append("listen_2_started")
        elif event.new == "ACTION":
            assert sm._session is not None and sm._session.llm_response is not None
            responses.append(asdict(sm._session.llm_response))
            streaks.append(sm._session.no_input_streak)
            _write_stage(
                stage_path,
                "RETRY_PLAYBACK" if states.count("ACTION") == 1 else "ENDING_SESSION",
            )
        elif event.new == "IDLE" and actions:
            order.append("idle")
            _write_stage(stage_path, "COMPLETE")
            idle.set()

    async def on_error(event: ErrorOccurred) -> None:
        errors.append(event)
        category = safe_category_for_code(event.code)
        _write_json(stage_path.with_name("operator-error.json"), {
            "where": event.where,
            "code": event.code,
            "category": category,
            "backend_disposition": event.backend_disposition,
            "recovery_keys": list(event.recovery_keys),
        })
        _write_stage(stage_path, f"ERROR_{category.upper()}")
        idle.set()

    bus.subscribe(PerceptionResult, on_perception, name="m4c.s03.perception")
    bus.subscribe(ActionCompleted, on_action, name="m4c.s03.action")
    bus.subscribe(StateChanged, on_state, name="m4c.s03.state")
    bus.subscribe(ErrorOccurred, on_error, name="m4c.s03.error")

    started = False
    try:
        await sm.start()
        await rm.start()
        started = True
        arbiter = rm._records["core.display.arbiter"].instance
        original_write_main = arbiter.write_main

        def observed_write_main(hint) -> None:
            text = None if hint is None else hint.data.get("text")
            display_publications.append((sm.state, text))
            original_write_main(hint)

        arbiter.write_main = observed_write_main
        reasoner = rm._records["worker.cognition.reasoner"].instance

        async def forbidden_reason(*args, **kwargs) -> None:
            nonlocal reasoner_call_count
            reasoner_call_count += 1
            raise AssertionError("S03 timeout path called Reasoner")

        reasoner.reason = forbidden_reason
        _write_stage(stage_path, "PRESS_BUTTON")
        await asyncio.wait_for(idle.wait(), timeout=180)
        await asyncio.wait_for(sm._inbox.join(), timeout=10)

        output = rm._records["core.audio.output"].instance
        raw = {
            "schema_version": 1,
            "states": states,
            "perceptions": [asdict(item) for item in perceptions],
            "responses": responses,
            "actions": [asdict(item) for item in actions],
            "no_input_streaks": streaks,
            "reasoner_call_count": reasoner_call_count,
            "order": order,
            "display_publications": display_publications,
            "completed_play_counts": completed_play_counts,
            "errors": [asdict(item) for item in errors],
            "final": {
                "state": sm.state,
                "status_state": _status_state(arbiter),
                "main_text": _main_text(arbiter),
                "completed_play_count": output.raw_output.completed_play_count,
            },
        }
        _write_json(stage_path.with_name("raw-observation.json"), raw)

        assert not errors, repr(errors)
        assert states == [
            "WAKE", "PERCEPTION", "ACTION", "PERCEPTION", "ACTION", "IDLE",
        ]
        assert _status_state(arbiter) == "IDLE"
        assert _main_text(arbiter) is None
        return {
            "schema_version": 1,
            "perceptions": raw["perceptions"],
            "responses": responses,
            "actions": raw["actions"],
            "no_input_streaks": streaks,
            "reasoner_call_count": reasoner_call_count,
            "order": order,
            "playback": {
                "retry_play_count": output.raw_output.completed_play_count,
                "complete": completed_play_counts == [1],
            },
            "cleanup": {
                "state": sm.state,
                "status": "待命",
                "main_empty": _main_text(arbiter) is None,
            },
        }
    finally:
        if started:
            await bus.publish(ShutdownRequested())
            await sm.wait_stopped()
            await rm.prepare_shutdown()
        await sm.stop()
        await rm.stop_all()


async def _run_s04(config: Any, variant: str, stage_path: Path) -> dict[str, Any]:
    bus = EventBus()
    composition = M3Composition()
    rm = ResourceManager(config, bus)
    converger = DefaultSessionConverger(timeouts=CancelTimeoutPolicy(
        abort_default_seconds=config.cancel.abort_timeout_seconds.default,
        force_abort_default_seconds=config.cancel.force_abort_timeout_seconds.default,
        abort_by_kind=config.cancel.abort_timeout_seconds.by_kind,
        force_abort_by_kind=config.cancel.force_abort_timeout_seconds.by_kind,
    ))
    sm = StateManager(
        config, bus, rm.catalog, converger=converger, recovery=rm,
        action_validator=composition.action_validator,
    )
    rm.set_state_manager(sm)
    composition(rm, bus, config)

    states: list[str] = []
    perceptions: list[PerceptionResult] = []
    responses: list[LLMResponse] = []
    actions: list[ActionCompleted] = []
    errors: list[ErrorOccurred] = []
    phase_active = {name: False for name in S04_ORACLE.VARIANTS}
    phase_starts = {name: 0 for name in S04_ORACLE.VARIANTS}
    interrupt: dict[str, Any] | None = None
    starts_at_interrupt: int | None = None
    action_prompted = False
    idle = asyncio.Event()

    async def on_perception(event: PerceptionResult) -> None:
        perceptions.append(event)

    async def on_response(event: LLMResponse) -> None:
        responses.append(event)

    async def on_action(event: ActionCompleted) -> None:
        actions.append(event)

    async def on_state(event: StateChanged) -> None:
        states.append(event.new)
        if event.new == "IDLE":
            _write_stage(
                stage_path,
                "COMPLETE" if interrupt is not None else "TARGET_NOT_REACHED",
            )
            idle.set()

    async def on_error(event: ErrorOccurred) -> None:
        errors.append(event)
        category = safe_category_for_code(event.code)
        _write_json(stage_path.with_name("operator-error.json"), {
            "where": event.where,
            "code": event.code,
            "category": category,
            "backend_disposition": event.backend_disposition,
            "recovery_keys": list(event.recovery_keys),
        })
        _write_stage(stage_path, f"ERROR_{category.upper()}")
        idle.set()

    bus.subscribe(PerceptionResult, on_perception, name="m4c.s04.perception")
    bus.subscribe(LLMResponse, on_response, name="m4c.s04.response")
    bus.subscribe(ActionCompleted, on_action, name="m4c.s04.action")
    bus.subscribe(StateChanged, on_state, name="m4c.s04.state")
    bus.subscribe(ErrorOccurred, on_error, name="m4c.s04.error")

    started = False
    try:
        await sm.start()
        await rm.start()
        started = True
        arbiter = rm._records["core.display.arbiter"].instance
        listen = rm._records["worker.perception.listen"].instance
        reasoner = rm._records["worker.cognition.reasoner"].instance
        llm = reasoner._llm
        output = rm._records["core.audio.output"].instance
        raw_output = output.raw_output

        original_perceive = listen.perceive

        async def observed_perceive(*args, **kwargs):
            phase_starts["PERCEPTION"] += 1
            phase_active["PERCEPTION"] = True
            _write_stage(
                stage_path,
                "PRESS_INTERRUPT" if variant == "PERCEPTION"
                else f"SPEAK_{phase_starts['PERCEPTION']}",
            )
            try:
                return await original_perceive(*args, **kwargs)
            finally:
                phase_active["PERCEPTION"] = False

        listen.perceive = observed_perceive
        original_generate = llm.generate

        async def observed_generate(*args, **kwargs):
            phase_starts["THINK"] += 1
            phase_active["THINK"] = True
            if variant == "THINK":
                _write_stage(stage_path, "PRESS_INTERRUPT")
            try:
                return await original_generate(*args, **kwargs)
            finally:
                phase_active["THINK"] = False

        llm.generate = observed_generate
        original_audio_observe = raw_output._observe

        def observed_audio(name: str) -> None:
            nonlocal action_prompted
            if original_audio_observe is not None:
                original_audio_observe(name)
            if (
                variant == "ACTION"
                and name == "audio_first_write"
                and phase_active["ACTION"]
                and not action_prompted
            ):
                action_prompted = True
                _write_stage(stage_path, "PRESS_INTERRUPT")

        raw_output._observe = observed_audio
        original_play = output.play

        async def observed_play(pcm):
            phase_starts["ACTION"] += 1
            phase_active["ACTION"] = True
            try:
                return await original_play(pcm)
            finally:
                phase_active["ACTION"] = False

        output.play = observed_play

        async def on_button(event: ButtonPressed) -> None:
            nonlocal interrupt, starts_at_interrupt
            del event
            state_matches = (
                sm.state == variant if variant != "ACTION"
                else sm.state in {"THINK", "ACTION"}
            )
            if state_matches and phase_active[variant] and interrupt is None:
                interrupt = {
                    "operation": variant,
                    "state": sm.state,
                    "operation_active": phase_active[variant],
                    "main_text": _main_text(arbiter),
                }
                starts_at_interrupt = phase_starts[variant]

        bus.subscribe(ButtonPressed, on_button, name="m4c.s04.button")
        _write_stage(stage_path, "PRESS_START")
        await asyncio.wait_for(idle.wait(), timeout=300)
        await asyncio.wait_for(sm._inbox.join(), timeout=10)
        await asyncio.sleep(0.2)
        await asyncio.wait_for(sm._inbox.join(), timeout=10)

        affected = {
            "PERCEPTION": len(perceptions),
            "THINK": len(responses),
            "ACTION": sum(item.status == "ok" for item in actions),
        }[variant]
        private = {
            "schema_version": 1,
            "variant": variant,
            "interrupt": interrupt,
            "affected_success_count": affected,
            "post_interrupt_start_count": (
                phase_starts[variant] - starts_at_interrupt
                if starts_at_interrupt is not None else -1
            ),
            "unexpected_error_count": len(errors),
            "cleanup": {
                "state": sm.state,
                "main_empty": _main_text(arbiter) is None,
                "affected_owner_idle": not phase_active[variant],
            },
        }
        _write_json(stage_path.with_name("raw-observation.json"), {
            **private,
            "states": states,
            "perception_count": len(perceptions),
            "response_count": len(responses),
            "action_count": len(actions),
        })
        assert interrupt is not None
        return private
    finally:
        if started:
            await bus.publish(ShutdownRequested())
            await sm.wait_stopped()
            await rm.prepare_shutdown()
        await sm.stop()
        await rm.stop_all()


def _process_identity(pid: int) -> tuple[str, str] | None:
    """Return Linux process state/start-time without retaining private argv."""
    try:
        value = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None
    close = value.rfind(")")
    fields = value[close + 2:].split()
    if close < 0 or len(fields) < 20:
        return None
    return fields[0], fields[19]


def _descendant_identities(root_pid: int) -> dict[int, tuple[str, str]]:
    pending = [root_pid]
    seen = {root_pid}
    descendants: dict[int, tuple[str, str]] = {}
    while pending:
        parent = pending.pop()
        try:
            children = Path(
                f"/proc/{parent}/task/{parent}/children"
            ).read_text(encoding="ascii").split()
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        for raw_pid in children:
            pid = int(raw_pid)
            if pid in seen:
                continue
            seen.add(pid)
            identity = _process_identity(pid)
            if identity is None:
                continue
            descendants[pid] = identity
            pending.append(pid)
    return descendants


def _surviving_identities(
    identities: dict[int, tuple[str, str]],
) -> list[int]:
    survivors = []
    for pid, (_, start_time) in identities.items():
        current = _process_identity(pid)
        if current is not None and current[0] != "Z" and current[1] == start_time:
            survivors.append(pid)
    return survivors


async def _run_s05(config_path: Path, stage_path: Path) -> dict[str, Any]:
    observation_path = stage_path.with_name("application-observation.json")
    ready_path = stage_path.with_name("application-ready")
    application_log = stage_path.with_name("application.log")
    with application_log.open("wb") as log_sink:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(ROOT / "scripts/m4c_s05_app.py"),
            "--config", str(config_path),
            "--observation", str(observation_path),
            "--ready", str(ready_path),
            cwd=ROOT,
            stdout=log_sink,
            stderr=asyncio.subprocess.STDOUT,
            start_new_session=True,
        )
    os.chmod(application_log, 0o600)

    async def wait_ready() -> None:
        while not ready_path.is_file():
            if process.returncode is not None:
                return
            await asyncio.sleep(0.1)

    waiter = asyncio.create_task(process.wait())
    ready_waiter = asyncio.create_task(wait_ready())
    descendants: dict[int, tuple[str, str]] = {}
    try:
        _write_stage(stage_path, "STARTING")
        done, _ = await asyncio.wait(
            {ready_waiter, waiter}, timeout=180,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if ready_waiter not in done or not ready_path.is_file():
            raise AssertionError("M4C_S05_APPLICATION_NOT_READY")
        descendants = _descendant_identities(process.pid)
        assert descendants, "M4C_S05_NATIVE_CHILD_OBSERVATION_EMPTY"
        _write_stage(stage_path, "LONG_PRESS")
        exit_code = await asyncio.wait_for(asyncio.shield(waiter), timeout=120)

        deadline = asyncio.get_running_loop().time() + 5.0
        while (survivors := _surviving_identities(descendants)):
            if asyncio.get_running_loop().time() >= deadline:
                break
            await asyncio.sleep(0.1)

        try:
            child = json.loads(observation_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, UnicodeError, json.JSONDecodeError):
            child = {}
        private = {
            "schema_version": 1,
            "variant": "APP_EXIT",
            "application_exit_code": exit_code,
            "shutdown_signal_count": child.get("shutdown_signal_count"),
            "wake_entry_count": child.get("wake_entry_count"),
            "shutdown_blank_seen": child.get("shutdown_blank_seen"),
            "blank_before_display_close": child.get("blank_before_display_close"),
            "stop_failure_count": child.get("stop_failure_count"),
            "native_child_count": len(descendants),
            "surviving_native_child_count": len(survivors),
        }
        _write_json(stage_path.with_name("raw-observation.json"), {
            **private,
            "application_observation_written": bool(child),
        })
        assert child, "M4C_S05_APPLICATION_OBSERVATION_MISSING"
        _write_stage(stage_path, "COMPLETE")
        return private
    finally:
        ready_waiter.cancel()
        if process.returncode is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.wait()
        await asyncio.gather(waiter, ready_waiter, return_exceptions=True)


def test_m4c_product_scenario() -> None:
    test_id = os.environ.get("SBD_M4C_TEST_ID")
    variant = os.environ.get("SBD_M4C_VARIANT")
    scenario = (test_id, variant)
    assert scenario in {
        ("M4C-PI-S01", "START_IDLE"),
        ("M4C-PI-S02", "NORMAL_END_B2"),
        ("M4C-PI-S03", "TWO_TIMEOUTS"),
        ("M4C-PI-S04", "PERCEPTION"),
        ("M4C-PI-S04", "THINK"),
        ("M4C-PI-S04", "ACTION"),
        ("M4C-PI-S05", "APP_EXIT"),
    }
    partition = Path(os.environ["SBD_M4C_PRIVATE_PARTITION"])
    config_path = Path(os.environ["SBD_M4C_CONFIG"])
    started = time.monotonic_ns()

    config = load_config(local_path=config_path, dotenv_path=Path(os.devnull), environ={})
    _validate_product_config(config)
    try:
        if scenario == ("M4C-PI-S01", "START_IDLE"):
            private = asyncio.run(_run_s01(config, partition / "operator-stage"))
            public = {
                "schema_version": 1,
                "scenario_code": "M4C-PI-S01/START_IDLE",
                "status_code": "IDLE_READY",
                "terminal_state_code": "IDLE",
                "conversation_created": private["session_created"],
                "audio_capture_started": private["audio_capture_active"],
                "main_empty": private["main_empty"],
                "display_open": private["display_open"],
            }
        elif scenario == ("M4C-PI-S02", "NORMAL_END_B2"):
            private = asyncio.run(_run_s02(config, partition / "operator-stage"))
            public = ORACLE.validate_s02_private_evidence(private)
        elif scenario == ("M4C-PI-S03", "TWO_TIMEOUTS"):
            private = asyncio.run(_run_s03(config, partition / "operator-stage"))
            public = S03_ORACLE.validate_s03_private_evidence(private)
        elif test_id == "M4C-PI-S04":
            assert variant is not None
            private = asyncio.run(_run_s04(
                config, variant, partition / "operator-stage"
            ))
            public = S04_ORACLE.validate_s04_private_evidence(private)
        else:
            private = asyncio.run(_run_s05(
                config_path, partition / "operator-stage"
            ))
            public = S05_ORACLE.validate_s05_private_evidence(private)
        evidence_path = partition / "evidence.json"
        _write_json(evidence_path, {"private": private, "public_projection": public})
        _write_json(partition / "result.json", {
            "schema_version": 1, "test_id": test_id, "variant": variant,
            "sub_run_id": os.environ["SBD_M4C_SUB_RUN_ID"],
            "started_monotonic_ns": started,
            "ended_monotonic_ns": time.monotonic_ns(),
            "script_status": "Pass", "public_evidence": public,
        })
    except BaseException as error:
        failure_path = partition / "evidence.json"
        _write_json(failure_path, {
            "schema_version": 1, "failure_type": type(error).__name__,
            "failure_code": str(error)[:160],
        })
        _write_json(partition / "result.json", {
            "schema_version": 1, "test_id": test_id, "variant": variant,
            "sub_run_id": os.environ["SBD_M4C_SUB_RUN_ID"],
            "started_monotonic_ns": started,
            "ended_monotonic_ns": time.monotonic_ns(),
            "script_status": "Fail",
            "public_evidence": {"failure_code": type(error).__name__},
        })
        raise
