"""Exact-product M4C Raspberry Pi scenario entry."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
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


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


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


def _binding_result_fields(binding: dict[str, Any]) -> dict[str, Any]:
    return {key: binding[key] for key in (
        "base_sha", "tracked_content_sha256", "pending_paths", "harness_sha256",
        "config_sha256", "artifact_digests", "target_facts",
    )}


def _validate_product_config(config: Any, config_path: Path,
                             binding: dict[str, Any]) -> None:
    assert _sha256(config_path) == binding["config_sha256"]
    assert config.core.audio.driver == "alsa"
    assert config.core.audio.output.volume_percent == 25
    assert config.core.audio.input.device and config.core.audio.output.device
    assert config.core.gpio.driver == "gpiod"
    assert config.perception.listen.adapter.driver == "whispercpp"
    assert config.cognition.llm.driver == "litert_lm"
    assert config.action.tts.driver == "sherpa_matcha"
    assert config.input_sources.button.policy.enabled is True
    paths = {
        "asr_artifact_lock": config.perception.listen.adapter.artifact_lock_path,
        "llm_artifact_lock": config.cognition.llm.artifact_lock_path,
        "llm_product_profile": config.cognition.llm.product_profile_path,
        "tts_artifact_lock": config.action.tts.artifact_lock_path,
    }
    actual = {
        name: _sha256(path) for name, path in paths.items()
        if isinstance(path, Path) and path.is_file() and not path.is_symlink()
    }
    assert actual == binding["artifact_digests"]


def _main_text(arbiter: Any) -> str | None:
    hint = arbiter.snapshot().main
    if hint is None:
        return None
    value = hint.data.get("text")
    return value if type(value) is str else None


async def _run_s02(config: Any, utterance_1: str, utterance_2: str,
                   stage_path: Path) -> dict[str, Any]:
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
                "session_present": sm._session is not None,
                "in_flight_count": len(sm._in_flight),
                "streaming_active": speak._streaming is not None,
                "main_text": _main_text(arbiter),
            },
        })

        assert not errors, repr(errors)
        assert len(perceptions) == 2
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
        assert first_proof.normalized_text_sha256 == _sha256_bytes(first_terminal.encode())
        if second_terminal:
            assert [item.kind for item in actions] == ["speak", "speak", "rest"]
            second_proof, second_fragments = speak._streaming_history[1]
            assert "".join(second_fragments) == second_terminal
            assert second_proof.normalized_text_sha256 == _sha256_bytes(second_terminal.encode())
            assert answer_displays == [first_terminal, second_terminal]
            assert display_publications == ORACLE.expected_display_publications(
                utterance_1, first_terminal, utterance_2, second_terminal
            )
            turn2_branch = "nonempty_play_then_rest"
            turn2_completion = speak._streaming_completion_history[1]
        else:
            assert [item.kind for item in actions] == ["speak", "rest"]
            assert len(speak._streaming_history) == 1
            assert answer_displays == [first_terminal]
            assert display_publications == ORACLE.expected_display_publications(
                utterance_1, first_terminal, utterance_2, ""
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
        assert sm._session is None and sm._in_flight == {}
        assert speak._streaming is None
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
                "conversation_close": True,
                "request_terminal": True,
                "stream_closed": True,
                "owner_count": 0,
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


def test_m4c_product_scenario() -> None:
    test_id = os.environ.get("SBD_M4C_TEST_ID")
    variant = os.environ.get("SBD_M4C_VARIANT")
    assert (test_id, variant) == ("M4C-PI-S02", "NORMAL_END")
    partition = Path(os.environ["SBD_M4C_PRIVATE_PARTITION"])
    binding = _read_json(Path(os.environ["SBD_M4C_BINDING_MANIFEST"]))
    config_path = Path(os.environ["SBD_M4C_CONFIG"])
    utterance_1 = os.environ.get("SBD_M4C_UTTERANCE_1", "天空為什麼是藍色的？")
    utterance_2 = os.environ.get("SBD_M4C_UTTERANCE_2", "請結束對話。")
    started = time.monotonic_ns()

    config = load_config(local_path=config_path, dotenv_path=Path(os.devnull), environ={})
    _validate_product_config(config, config_path, binding)
    try:
        private = asyncio.run(_run_s02(
            config, utterance_1, utterance_2, partition / "operator-stage"
        ))
        public = ORACLE.validate_s02_private_evidence(private)
        evidence_path = partition / "evidence.json"
        _write_json(evidence_path, {"private": private, "public_projection": public})
        _write_json(partition / "result.json", {
            "schema_version": 1, "test_id": test_id, "variant": variant,
            "sub_run_id": os.environ["SBD_M4C_SUB_RUN_ID"],
            **_binding_result_fields(binding),
            "started_monotonic_ns": started,
            "ended_monotonic_ns": time.monotonic_ns(),
            "script_status": "Pass", "evidence_sha256": _sha256(evidence_path),
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
            **_binding_result_fields(binding),
            "started_monotonic_ns": started,
            "ended_monotonic_ns": time.monotonic_ns(),
            "script_status": "Fail", "evidence_sha256": _sha256(failure_path),
        })
        raise
