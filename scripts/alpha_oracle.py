"""ALPHA path/timing oracles. Public projections contain no private speech."""
from __future__ import annotations

import re

RUNS = {
    "lifecycle": "ALPHA-L01-LIFECYCLE",
    "performance": "ALPHA-P01-PERFORMANCE",
    "recovery": "ALPHA-R01-LLM-RECOVERY",
    "quality": "ALPHA-Q-RUN-01-QUALITY",
}
QUALITY = tuple(f"ALPHA-Q{i:02d}-{name}" for i, name in enumerate(
    ("IDENTITY", "FACTUAL", "CAPABILITY", "INSTRUCTION", "CONTEXT", "END"), 1))
FIXTURES = (
    "FX-SHORT-A", "FX-SHORT-B", "FX-FOLLOW-UP", "FX-MULTI-FRAGMENT", "FX-NORMAL-END",
    "FX-Q01", "FX-Q02", "FX-Q03", "FX-Q04", "FX-Q05-T1", "FX-Q05-T2",
    "FX-Q06-T1", "FX-Q06-T2",
)
BARRIER_COUNTS = ("session_tasks", "streaming_controls", "queue_depth", "inflight",
                  "late_audio", "stale_facts", "late_fragments")
BARRIER_BOOLS = ("conversation_absent", "main_empty", "display_idle", "backend_reused")
TURN_BOOLS = ("asr_terminal", "llm_terminal", "schema_valid", "route_valid",
              "response_nonempty", "speech_equal", "protocol_clear", "audio_complete")
CLEANUP = ("app_absent", "children_absent", "alsa_absent", "display_owner_absent",
           "hardware_owners_absent")
PUBLIC_KEYS = set((*BARRIER_COUNTS, *BARRIER_BOOLS, *TURN_BOOLS, *CLEANUP,
    "close_count", "test_id", "run_id", "target", "architecture", "python", "watchdog_seconds",
    "disposition", "reason_code", "turns", "sessions", "case_id", "fixture_id", "fixture_ids",
    "network_attempts", "network_fallbacks", "privacy_matches", "restart", "new_process",
    "resources_ready", "stopped_cleanly", "performance", "invalid_observations", "nodes",
    "durations_ns", "end_to_end_ns", "largest_stage_code", "token_counts", "input_tokens", "context_tokens",
    "fragments", "reuse", "engine_reused", "child_reused", "queue_entry_depth", "queue_wait_ns",
    "admission", "tts_start", "tts_first_pcm", "audio_start", "audio_complete", "sequence", "dequeued",
    "process_start", "config_complete", "idle", "conversation_ready", "speech_end", "asr_final",
    "llm_send", "first_safe_text", "llm_terminal", "audio_first_write", "previous_action_complete",
    "next_perception_start", "final_drain", "cleanup", "recovery", "killed_sole_llm",
    "after_safe_admission", "fault_locator", "old_reaped", "barrier_rejected", "ready_before_admission",
    "new_child", "sole_replacement", "new_conversation", "error_display_clear", "failed_work_empty",
    "old_context_absent", "replacement_count", "future_fragments", "failed_normal_terminals",
    "quality", "objective", "semantic"))


class InvalidObservation(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def require(value: bool, code: str) -> None:
    if not value:
        raise InvalidObservation(code)


def all_true(row: dict, names: tuple[str, ...]) -> bool:
    return all(row.get(key) is True for key in names)


def barrier_pass(row: dict, *, backend_reuse_required: bool) -> bool:
    booleans = BARRIER_BOOLS if backend_reuse_required else tuple(k for k in BARRIER_BOOLS if k != "backend_reused")
    return (all_true(row, booleans) and row.get("close_count") == 1
            and all(type(row.get(key)) is int and row[key] == 0 for key in BARRIER_COUNTS))


def public_turn(row: dict) -> dict:
    return {"case_id": row["case_id"], "fixture_id": row["fixture_id"],
            **{key: row.get(key) is True for key in TURN_BOOLS},
            "disposition": "PASS" if all_true(row, TURN_BOOLS) else "FAIL"}


def public_barrier(row: dict) -> dict:
    return {key: row.get(key) for key in (*BARRIER_BOOLS, *BARRIER_COUNTS, "close_count")}


def timing_view(case_id: str, nodes: dict, *, token_counts: dict | None = None,
                fragments: list | None = None, reuse: dict | None = None) -> dict:
    """Validate causal branches; streaming audio may precede the LLM terminal."""
    common = ("conversation_ready", "speech_end", "asr_final", "llm_send", "first_safe_text",
              "llm_terminal", "tts_first_pcm", "audio_first_write", "audio_complete")
    if case_id == "P01-STARTUP":
        required = ("process_start", "config_complete", "idle")
        edges = [("process_start", "config_complete"), ("config_complete", "idle")]
        ready = nodes.get("resources_ready")
        require(type(ready) is dict and bool(ready), "STARTUP_READY_MISSING")
        for value in ready.values():
            require(type(value) is int and nodes["config_complete"] <= value <= nodes["idle"],
                    "STARTUP_READY_ORDER")
    elif case_id == "P04-FOLLOW-UP":
        required = ("previous_action_complete", "next_perception_start", "asr_final", "llm_send",
                    "first_safe_text", "llm_terminal", "audio_complete")
        edges = [("previous_action_complete", "next_perception_start"),
                 ("next_perception_start", "asr_final"), ("asr_final", "llm_send"),
                 ("llm_send", "first_safe_text"), ("first_safe_text", "llm_terminal"),
                 ("llm_terminal", "audio_complete")]
        require(type(token_counts) is dict and set(token_counts) == {"input_tokens", "context_tokens"}
                and all(type(v) is int and v >= 0 for v in token_counts.values()), "TOKEN_COUNT_MISSING")
    elif case_id in {"P02-FIRST-TURN", "P03-WARM-SESSION"}:
        required = common
        edges = list(zip(common[:5], common[1:5])) + [
            ("first_safe_text", "llm_terminal"), ("first_safe_text", "tts_first_pcm"),
            ("tts_first_pcm", "audio_first_write"), ("audio_first_write", "audio_complete"),
            ("llm_terminal", "audio_complete")]
        if case_id == "P03-WARM-SESSION":
            require(type(reuse) is dict and set(reuse) == {"engine_reused", "child_reused"}
                    and all(type(v) is bool for v in reuse.values()), "REUSE_MISSING")
    elif case_id == "P05-STREAMING":
        required = ("llm_send", "llm_terminal", "final_drain")
        edges = [("llm_send", "llm_terminal"), ("llm_terminal", "final_drain")]
        require(type(fragments) is list and len(fragments) >= 2, "MULTIPLE_FRAGMENTS_MISSING")
        for fragment in fragments:
            fields = ("admission", "tts_start", "tts_first_pcm", "audio_start", "audio_complete")
            require(all(type(fragment.get(k)) is int and fragment[k] > 0 for k in fields),
                    "FRAGMENT_NODE_MISSING")
            require(fragment["admission"] <= fragment["tts_start"] <= fragment["tts_first_pcm"]
                    <= fragment["audio_complete"] <= nodes["final_drain"]
                    and fragment["tts_start"] <= fragment["audio_start"] <= fragment["audio_complete"],
                    "FRAGMENT_NODE_ORDER")
            require(type(fragment.get("queue_entry_depth")) is int
                    and fragment["queue_entry_depth"] >= 1, "FRAGMENT_QUEUE_MISSING")
            fragment["queue_wait_ns"] = fragment["tts_start"] - fragment["admission"]
    else:
        raise InvalidObservation("PERFORMANCE_CASE_UNKNOWN")
    require(all(type(nodes.get(k)) is int and nodes[k] > 0 for k in required), "TIMING_NODE_MISSING")
    require(all(nodes[left] <= nodes[right] for left, right in edges), "TIMING_NODE_ORDER")
    durations = {f"{left}_to_{right}": nodes[right] - nodes[left] for left, right in edges}
    largest = max(durations, key=durations.get)
    return {"case_id": case_id, "nodes": {k: nodes[k] for k in required}
            | ({"resources_ready": nodes["resources_ready"]} if case_id == "P01-STARTUP" else {}),
            "durations_ns": durations, "end_to_end_ns": nodes[required[-1]] - nodes[required[0]],
            "largest_stage_code": largest, **({"token_counts": token_counts} if token_counts else {}),
            **({"fragments": fragments} if fragments is not None else {}),
            **({"reuse": reuse} if reuse is not None else {})}


def evaluate(run: str, observations: dict, *, judgments: dict | None = None) -> dict:
    """Project complete observations; a driver error is never overridden by judgment."""
    report = {"test_id": RUNS[run], "disposition": "FAIL", "reason_code": "PATH_FAILED",
              "turns": [public_turn(row) for row in observations.get("turns", [])],
              "sessions": [public_barrier(row) for row in observations.get("sessions", [])]}
    try:
        require(observations.get("driver_complete") is True, observations.get("failure_code", "DRIVER_INCOMPLETE"))
        require(observations.get("exit_code") == 0, "APP_EXIT_FAILED")
        require(all_true(observations.get("cleanup", {}), CLEANUP), "OWNER_REMAINS")
        require(all_true(observations.get("initial", {}),
                         ("conversation_absent", "main_empty", "display_idle", "resources_ready")),
                "INITIAL_IDLE_FAILED")
        sessions = observations["sessions"]
        turns = observations["turns"]
        require(all(barrier_pass(row, backend_reuse_required=run == "lifecycle") for row in sessions),
                "SESSION_CLEANUP_FAILED")
        if run == "lifecycle":
            require(len(sessions) == 3 and len(turns) == 6 and observations.get("buttons") == 3,
                    "LIFECYCLE_SEQUENCE_FAILED")
            require([t["fixture_id"] for t in turns] == ["FX-SHORT-A", "FX-NORMAL-END"] * 3,
                    "FIXTURE_SEQUENCE_FAILED")
            require(all(all_true(row, TURN_BOOLS) for row in turns), "TURN_FAILED")
            require(all_true(observations.get("restart", {}),
                             ("new_process", "conversation_absent", "main_empty", "display_idle",
                              "resources_ready", "stopped_cleanly")), "RESTART_FAILED")
            require(observations.get("network_attempts") == 0
                    and observations.get("network_fallbacks") == 0
                    and observations.get("privacy_matches") == 0, "OFFLINE_PRIVACY_FAILED")
            report.update(network_attempts=0, network_fallbacks=0, privacy_matches=0,
                          restart=observations["restart"])
        elif run == "performance":
            # Close turns are functional requirements and remain visible, outside numeric views.
            require(len(sessions) == 2 and len(turns) == 6
                    and all(all_true(row, TURN_BOOLS) for row in turns), "PERFORMANCE_PATH_FAILED")
            require([t["fixture_id"] for t in turns] == ["FX-SHORT-B", "FX-FOLLOW-UP", "FX-NORMAL-END",
                    "FX-SHORT-B", "FX-MULTI-FRAGMENT", "FX-NORMAL-END"], "FIXTURE_SEQUENCE_FAILED")
            cases = observations.get("performance", [])
            report["performance"] = []
            require([row.get("case_id") for row in cases] == ["P01-STARTUP", "P02-FIRST-TURN",
                    "P04-FOLLOW-UP", "P03-WARM-SESSION", "P05-STREAMING"], "PERFORMANCE_CASE_MISSING")
            for row in cases:
                # Keep preceding valid views and the failing sample on invalidation.
                report["performance"].append(timing_view(**row))
        elif run == "recovery":
            require(len(sessions) == 1 and len(turns) == 3, "RECOVERY_SEQUENCE_FAILED")
            proof = observations.get("recovery", {})
            required = ("killed_sole_llm", "after_safe_admission", "fault_locator", "old_reaped",
                        "barrier_rejected", "ready_before_admission", "new_child", "sole_replacement",
                        "new_conversation", "error_display_clear", "failed_work_empty",
                        "old_context_absent")
            require(all_true(proof, required) and proof.get("replacement_count") == 1
                    and proof.get("future_fragments") == 0 and proof.get("failed_normal_terminals") == 0,
                    "RECOVERY_CONVERGENCE_FAILED")
            require(all(all_true(row, TURN_BOOLS) for row in turns[1:])
                    and [t["fixture_id"] for t in turns] == ["FX-MULTI-FRAGMENT", "FX-SHORT-A", "FX-NORMAL-END"],
                    "POST_RECOVERY_SESSION_FAILED")
            report["recovery"] = {key: proof.get(key) for key in (*required, "replacement_count",
                                                      "future_fragments", "failed_normal_terminals")}
        else:
            require(len(sessions) == 6, "QUALITY_SESSION_MISSING")
            rows = []
            judgments = judgments or {}
            require(set(judgments) <= set(QUALITY), "QUALITY_CASE_UNKNOWN")
            for identity in QUALITY:
                case_turns = [t for t in turns if t["case_id"] == identity]
                expected = 2 if identity in QUALITY[4:] else 1
                require(len(case_turns) == expected, "QUALITY_CASE_MISSING")
                objective = all(all_true(row, TURN_BOOLS) for row in case_turns)
                judgment = judgments.get(identity, {"disposition": "NEEDS_USER_DECISION",
                                                    "reason_code": "SEMANTIC_OBSERVATION_PENDING"})
                require(set(judgment) == {"disposition", "reason_code"}
                        and judgment["disposition"] in {"PASS", "FAIL", "NEEDS_USER_DECISION"}
                        and type(judgment["reason_code"]) is str
                        and re.fullmatch(r"[A-Z][A-Z0-9_]{2,79}", judgment["reason_code"]) is not None,
                        "SEMANTIC_RESULT_INVALID")
                rows.append({"case_id": identity, "objective": "PASS" if objective else "FAIL",
                             "semantic": judgment["disposition"], "reason_code": judgment["reason_code"]})
            # Cleanup turns are not quality cases, but failures still invalidate the run.
            report["quality"] = rows
            require(all(all_true(row, TURN_BOOLS) for row in turns), "QUALITY_PATH_FAILED")
            if any(r["semantic"] == "FAIL" for r in rows):
                raise InvalidObservation("SEMANTIC_FAILED")
            if any(r["semantic"] == "NEEDS_USER_DECISION" for r in rows):
                report.update(disposition="NEEDS_USER_DECISION", reason_code="SEMANTIC_OBSERVATION_PENDING")
                return report
        report.update(disposition="VALID_BASELINE" if run == "performance" else "PASS", reason_code="COMPLETE")
    except (InvalidObservation, KeyError, TypeError, ValueError) as error:
        report.update(disposition="INVALID" if run == "performance" else "FAIL",
                      reason_code=error.code if isinstance(error, InvalidObservation) else "OBSERVATION_MISSING")
        if run == "performance":
            report["invalid_observations"] = observations.get("performance", [])
    return report


def check_public(value: object) -> None:
    """Reject arbitrary text/payload types even beneath apparently harmless field names."""
    if type(value) is dict:
        forbidden = {"text", "transcript", "prompt", "raw_model_output", "pcm", "audio", "credential",
                     "session_id", "private_path", "answer", "spoken", "output"}
        for key, child in value.items():
            require(type(key) is str and key not in forbidden and
                    (key in PUBLIC_KEYS
                     or re.fullmatch(r"(?:core|backend|worker|input|observer)\.[a-z.]+", key) is not None
                     or ("_to_" in key and all(part in PUBLIC_KEYS for part in key.split("_to_")))),
                    "PUBLIC_FIELD_FORBIDDEN")
            check_public(child)
    elif type(value) is list:
        for child in value:
            check_public(child)
    elif type(value) is str:
        require(re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", value) is not None, "PUBLIC_TEXT_FORBIDDEN")
    else:
        require(value is None or type(value) in {bool, int, float}, "PUBLIC_VALUE_FORBIDDEN")
