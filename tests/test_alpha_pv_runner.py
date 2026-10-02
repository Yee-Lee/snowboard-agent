"""ALPHA failure-sensitive path/timing oracles and actual subprocess cleanup."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace as NS

import pytest

from scripts.alpha_oracle import (
    BARRIER_BOOLS, BARRIER_COUNTS, CLEANUP, QUALITY, TURN_BOOLS,
    InvalidObservation, check_public, evaluate, timing_view,
)
from scripts.alpha_product import session_plan

SPEC = importlib.util.spec_from_file_location("alpha_runner", Path(__file__).parents[1] / "scripts/run-alpha-pv.py")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_public_privacy_short_answer_is_not_a_case_id_substring():
    private = {"turns": [{"responses": [{"payload": {"text": "2"}}]}],
               "log_privacy_matches": 0}
    assert RUNNER.privacy_matches({"reason_code": "L2_T1"}, private) == 0
    private["log_privacy_matches"] = 1
    assert RUNNER.privacy_matches({"reason_code": "L2_T1"}, private) == 1


def observation(run):
    return {"driver_complete": True, "exit_code": 0, "buttons": 3,
            "cleanup": dict.fromkeys(CLEANUP, True),
            "initial": dict.fromkeys(("conversation_absent", "main_empty", "display_idle", "resources_ready"), True),
            "sessions": [{**dict.fromkeys(BARRIER_BOOLS, True), **dict.fromkeys(BARRIER_COUNTS, 0),
                          "close_count": 1} for _ in session_plan(run)],
            "turns": [{"case_id": case, "fixture_id": fixture, **dict.fromkeys(TURN_BOOLS, True)}
                      for session in session_plan(run) for case, fixture, _ in session],
            "restart": dict.fromkeys(("new_process", "conversation_absent", "main_empty", "display_idle",
                                      "resources_ready", "stopped_cleanly"), True),
            "network_attempts": 0, "network_fallbacks": 0, "privacy_matches": 0}


def semantic():
    return {identity: {"disposition": "PASS", "reason_code": "RUBRIC_MET"} for identity in QUALITY}


def test_lifecycle_projects_six_turns_and_three_barriers_without_private_text():
    value = observation("lifecycle")
    value["turns"][0]["transcript"] = "private input"
    result = evaluate("lifecycle", value)
    assert result["disposition"] == "PASS"
    assert len(result["turns"]) == 6 and len(result["sessions"]) == 3
    assert "private input" not in json.dumps(result)
    check_public(result)


@pytest.mark.parametrize("field", BARRIER_COUNTS + BARRIER_BOOLS + ("close_count",))
def test_each_session_cleanup_failure_cannot_be_averaged(field):
    value = observation("lifecycle")
    value["sessions"][1][field] = 1 if field in BARRIER_COUNTS else False
    assert evaluate("lifecycle", value)["disposition"] == "FAIL"


@pytest.mark.parametrize("field", TURN_BOOLS)
def test_each_required_turn_path_failure_is_fatal(field):
    value = observation("lifecycle")
    value["turns"][3][field] = False
    assert evaluate("lifecycle", value)["disposition"] == "FAIL"


@pytest.mark.parametrize("change", [
    {"network_attempts": 1}, {"network_fallbacks": 1}, {"privacy_matches": 1},
    {"buttons": 6}, {"exit_code": 4}, {"driver_complete": False},
])
def test_lifecycle_rejects_offline_privacy_sequence_and_runtime_failures(change):
    value = observation("lifecycle")
    value.update(change)
    assert evaluate("lifecycle", value)["disposition"] == "FAIL"


def test_quality_semantics_do_not_override_objective_failure_and_no_retry():
    value = observation("quality")
    assert evaluate("quality", value)["disposition"] == "NEEDS_USER_DECISION"
    assert evaluate("quality", value, judgments=semantic())["disposition"] == "PASS"
    value["turns"][0]["audio_complete"] = False
    result = evaluate("quality", value, judgments=semantic())
    assert result["disposition"] == "FAIL"
    assert result["quality"][0]["objective"] == "FAIL"
    value = observation("quality")
    value["turns"].append(copy.deepcopy(value["turns"][0]))
    assert evaluate("quality", value, judgments=semantic())["disposition"] == "FAIL"


def test_quality_failed_semantics_and_private_reason_cannot_pass():
    value = observation("quality")
    judgments = semantic()
    judgments[QUALITY[2]]["disposition"] = "FAIL"
    assert evaluate("quality", value, judgments=judgments)["disposition"] == "FAIL"
    judgments[QUALITY[2]]["reason_code"] = "actual private answer: 我看得到"
    assert evaluate("quality", value, judgments=judgments)["reason_code"] == "SEMANTIC_RESULT_INVALID"


def test_streaming_timing_accepts_overlap_and_rejects_missing_or_reversed_nodes():
    nodes = {"conversation_ready": 1, "speech_end": 2, "asr_final": 3, "llm_send": 4,
             "first_safe_text": 5, "tts_first_pcm": 6, "audio_first_write": 7,
             "llm_terminal": 9, "audio_complete": 10}
    view = timing_view("P02-FIRST-TURN", nodes)
    assert view["end_to_end_ns"] == 9
    assert all(v >= 0 for v in view["durations_ns"].values())
    for change in ({"tts_first_pcm": None}, {"audio_first_write": 5}, {"speech_end": 4}):
        with pytest.raises(InvalidObservation):
            timing_view("P02-FIRST-TURN", nodes | change)


def test_followup_requires_actual_token_counts_and_all_fragment_measurements():
    nodes = dict(previous_action_complete=1, next_perception_start=2, asr_final=3,
                 llm_send=4, first_safe_text=5, llm_terminal=6, audio_complete=7)
    with pytest.raises(InvalidObservation, match="TOKEN_COUNT_MISSING"):
        timing_view("P04-FOLLOW-UP", nodes)
    assert timing_view("P04-FOLLOW-UP", nodes, token_counts={"input_tokens": 3, "context_tokens": 50})
    fragments = [{"admission": 2, "queue_entry_depth": 1, "tts_start": 3,
                  "tts_first_pcm": 4, "audio_start": 3, "audio_complete": 5},
                 {"admission": 3, "queue_entry_depth": 2, "tts_start": 5,
                  "tts_first_pcm": 6, "audio_start": 5, "audio_complete": 8}]
    view = timing_view("P05-STREAMING", {"llm_send": 1, "llm_terminal": 7, "final_drain": 8}, fragments=fragments)
    assert [f["queue_wait_ns"] for f in view["fragments"]] == [1, 2]
    fragments[1].pop("tts_first_pcm")
    with pytest.raises(InvalidObservation, match="FRAGMENT_NODE_MISSING"):
        timing_view("P05-STREAMING", {"llm_send": 1, "llm_terminal": 7, "final_drain": 8}, fragments=fragments)


def test_incomplete_performance_retains_failed_observation():
    value = observation("performance")
    value["performance"] = [{"case_id": "P01-STARTUP", "nodes": {"process_start": 1}}]
    result = evaluate("performance", value)
    assert result["disposition"] == "INVALID"
    assert result["invalid_observations"] == value["performance"]


def test_replacement_alone_does_not_prove_recovery():
    value = observation("recovery")
    value["sessions"] = value["sessions"][1:]
    fields = ("killed_sole_llm", "after_safe_admission", "fault_locator", "old_reaped", "barrier_rejected",
              "ready_before_admission", "new_child", "sole_replacement", "new_conversation",
              "error_display_clear", "failed_work_empty", "old_context_absent")
    value["recovery"] = {**dict.fromkeys(fields, True), "replacement_count": 1,
                         "future_fragments": 0, "failed_normal_terminals": 0}
    assert evaluate("recovery", value)["disposition"] == "PASS"
    value["turns"][1]["llm_terminal"] = False
    assert evaluate("recovery", value)["disposition"] == "FAIL"
    value["turns"][1]["llm_terminal"] = True
    for field in fields:
        changed = copy.deepcopy(value)
        changed["recovery"][field] = False
        assert evaluate("recovery", changed)["disposition"] == "FAIL"


@pytest.mark.parametrize("payload", [
    {"transcript": "private"}, {"quality": [{"reason_code": "原文"}]},
    {"nodes": {"pcm": [1, 2]}}, {"prompt": "hidden"}, {"credential": "secret"},
])
def test_public_evidence_rejects_private_content(payload):
    with pytest.raises(InvalidObservation):
        check_public(payload)


def test_actual_subprocess_cleanup_reaps_launcher_and_kills_its_separate_child_group():
    # Exercises OS cleanup rather than substituting a fake completion boolean.
    process = subprocess.Popen([sys.executable, "-c",
        "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True); time.sleep(30)"],
        start_new_session=True)
    try:
        import time
        deadline = time.monotonic() + 2
        identities = RUNNER.process_tree(process.pid)
        while len(identities) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
            identities = RUNNER.process_tree(process.pid)
        assert len(identities) == 2
        # Some CI PID 1 implementations leave orphan zombies; that must be reported honestly.
        clean = RUNNER.finish_process(process, identities, 1)
        assert process.poll() is not None
        for pid, identity in identities.items():
            current = RUNNER.process_identity(pid)
            assert current is None or current[1] == "Z" or current[0] != identity[0]
        assert clean == (not any(RUNNER.remains(pid, identity) for pid, identity in identities.items()))
    finally:
        RUNNER.finish_process(process, RUNNER.process_tree(process.pid), 1)
        process.wait(timeout=1)


def test_network_trace_counts_external_attempts_once_across_restart(tmp_path):
    (tmp_path / "network.log").write_text('1 connect(3, {sa_family=AF_INET, sin_addr=inet_addr("8.8.8.8")}, 16) = -1 ENETUNREACH\n')
    (tmp_path / "network-restart.log").write_text('2 connect(3, {sa_family=AF_UNIX}, 16) = 0\n')
    assert RUNNER.network_counts(tmp_path) == (1, 1)
    (tmp_path / "network.log").unlink()
    with pytest.raises(InvalidObservation, match="NETWORK_OBSERVATION_MISSING"):
        RUNNER.network_counts(tmp_path)


def test_quality_adjudication_reuses_same_private_run_without_launch(tmp_path, monkeypatch):
    root = tmp_path / "quality"
    private = root / "private"
    private.mkdir(parents=True)
    value = observation("quality")
    (private / "run-observation.json").write_text(json.dumps(value))
    report = evaluate("quality", value)
    report.update(run_id="QUALITY-01", target={"architecture": "aarch64", "python": "3.13.5"},
                  watchdog_seconds=900, fixture_ids=[], cleanup=value["cleanup"])
    original = json.dumps(report)
    (root / "result.json").write_text(original)
    judgments = tmp_path / "judgments.json"
    judgments.write_text(json.dumps(semantic()))
    def unexpected_launch(*args):
        pytest.fail("Semantic observation must not launch another product run")
    monkeypatch.setattr(RUNNER, "run_child", unexpected_launch)
    args = NS(run="quality", adjudicate=root, judgments=judgments)
    assert RUNNER.adjudicate(args) == 0
    assert (root / "result.json").read_text() == original
    adjudicated = json.loads((root / "adjudicated-result.json").read_text())
    assert adjudicated["disposition"] == "PASS" and adjudicated["run_id"] == "QUALITY-01"
    assert len(adjudicated["quality"]) == 6


@pytest.mark.parametrize("earlier_failure", [False, True])
def test_actual_watchdog_records_failure_and_stops_owned_process(tmp_path, monkeypatch, earlier_failure):
    popen = subprocess.Popen
    def launch_harness(command, **kwargs):
        return popen([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
    monkeypatch.setattr(RUNNER.subprocess, "Popen", launch_harness)
    args = NS(run="performance", python=Path(sys.executable), config=tmp_path / "config",
              fixtures=tmp_path / "fixtures", watchdog=0.1, cleanup_timeout=1)
    if earlier_failure:
        (tmp_path / "observation-failure.json").write_text(json.dumps(
            {"driver_complete": False, "failure_code": "SESSION_ENDED_BEFORE_FIXTURES"}))
    value = RUNNER.run_child(args, tmp_path, "performance")
    assert value["driver_complete"] is False
    assert value["failure_code"] == ("SESSION_ENDED_BEFORE_FIXTURES" if earlier_failure else "RUNNER_WATCHDOG")
    assert value["cleanup"]["app_absent"] is True
    assert value["launcher_exit_code"] is not None


def test_complete_performance_is_valid_without_latency_threshold_and_keeps_invalid_sample():
    value = observation("performance")
    common = dict(conversation_ready=1, speech_end=2, asr_final=3, llm_send=4, first_safe_text=5,
                  tts_first_pcm=6, audio_first_write=7, llm_terminal=9, audio_complete=10)
    value["performance"] = [
        {"case_id": "P01-STARTUP", "nodes": {"process_start": 1, "config_complete": 2,
                                            "resources_ready": {"core.audio": 3}, "idle": 4}},
        {"case_id": "P02-FIRST-TURN", "nodes": common.copy()},
        {"case_id": "P04-FOLLOW-UP", "nodes": dict(previous_action_complete=1, next_perception_start=2,
            asr_final=3, llm_send=4, first_safe_text=5, llm_terminal=9, audio_complete=10),
            "token_counts": {"input_tokens": 2, "context_tokens": 50}},
        {"case_id": "P03-WARM-SESSION", "nodes": common.copy(),
            "reuse": {"engine_reused": True, "child_reused": True}},
        {"case_id": "P05-STREAMING", "nodes": {"llm_send": 1, "llm_terminal": 9, "final_drain": 10},
            "fragments": [{"admission": i, "queue_entry_depth": 1, "tts_start": i + 1,
                "tts_first_pcm": i + 2, "audio_start": i + 1, "audio_complete": i + 3} for i in (2, 5)]}]
    result = evaluate("performance", value)
    assert result["disposition"] == "VALID_BASELINE" and len(result["performance"]) == 5
    check_public(result)
    value["sessions"][0]["backend_reused"] = False
    value["performance"][3]["reuse"] = {"engine_reused": False, "child_reused": False}
    assert evaluate("performance", value)["disposition"] == "VALID_BASELINE"
    value["performance"][-1]["fragments"][-1]["tts_first_pcm"] = None
    result = evaluate("performance", value)
    assert result["disposition"] == "INVALID"
    assert len(result["performance"]) == 4
    assert result["invalid_observations"][-1]["fragments"][-1]["tts_first_pcm"] is None
