"""ALPHA path/timing oracles. Public projections contain no private speech."""
from __future__ import annotations

import re

RUNS = {
    "lifecycle": "ALPHA-L01-LIFECYCLE",
    "performance": "ALPHA-P01-PERFORMANCE",
    "recovery": "ALPHA-R01-LLM-RECOVERY",
    "quality": "ALPHA-Q-RUN-01-QUALITY",
    "pn": "ALPHA.P.PN",
    "ph": "ALPHA.P.PH",
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
    "quality", "objective", "semantic", "fixture_revision",
    "blocks", "block", "mode", "phase", "control_enabled", "unexecuted_cases",
    "clock_resolution_ns", "timestamp_quantization_ns", "capture_error_bound_ns",
    "improvement_claim_allowed", "limits", "prefill", "native_render", "asr_endpoint",
    "human_speech_end", "acoustic_onset", "admission_render", "startup_prework",
    "prior_inference", "first_frame", "last_frame", "parent_request_send", "child_request_receive",
    "native_generation_start", "first_generated_output", "child_safe_text_emit",
    "parent_safe_text_receive", "child_terminal_emit", "parent_terminal_receive",
    "conversation_create", "render_begin", "render_end", "output_tokens", "rendered_input_tokens",
    "idle_to_request_ns", "input_mode", "pacing", "frame_count", "max_lateness_ns",
    "delivery_span_error_ns", "batch_index", "turn_index", "report_status", "unclear_speech",
    "stutter", "perceived_waiting", "playback_agreement", "ranges", "minimum_ns", "maximum_ns",
    "native_runtime_begin", "native_runtime_ready", "engine_init_begin", "engine_init_end",
    "response_format_begin", "response_format_end", "optional_args_begin", "optional_args_end",
    "native_submit_begin", "native_submit_end", "native_work", "cpu_time_ns", "major_fault_count",
    "input_block_count", "callback_before_return", "return_to_callback_ns",
    "host_uptime_start_ns", "host_uptime_end_ns", "cache_prefetch", "read_bytes",
    "duration_ns", "completed_before_generation"))


def experiment_block(run: str, observed: dict, *, control: bool = False,
                     hearing: list | None = None, diagnostic_role: str | None = None) -> dict:
    """Validate observable request boundaries before projecting an experimental block."""
    prefix = run.upper()
    expected = [prefix + "06"] * 4 if control else [prefix + "02", prefix + "04", prefix + "03", prefix + "05"]
    if diagnostic_role is not None:
        expected = (["NATIVE-FIRST", "NATIVE-REUSED"] if diagnostic_role == "first_app" else
                    ["NATIVE-FIRST"] if diagnostic_role == "single_request" else ["NATIVE-FRESH-APP"])
    report = {"disposition": "INVALID", "reason_code": "DIAGNOSTIC_INCOMPLETE",
              "turns": [public_turn(row) for row in observed.get("turns", [])],
              "performance": [], "unexecuted_cases": list(expected), "stopped_cleanly": False}
    for row in observed.get("turns", []):
        if report["unexecuted_cases"] and row.get("case_id") == report["unexecuted_cases"][0]:
            report["unexecuted_cases"].pop(0)
    try:
        require(observed.get("driver_complete") is True,
                observed.get("failure_code", "DRIVER_INCOMPLETE"))
        require(observed.get("exit_code") == 0 and observed.get("launcher_exit_code") == 0,
                "APP_EXIT_FAILED")
        require(all_true(observed.get("initial", {}),
                         ("conversation_absent", "main_empty", "display_idle", "resources_ready")),
                "INITIAL_IDLE_FAILED")
        require(len(observed.get("sessions", [])) == (len(expected) if diagnostic_role else 2) and all(
            barrier_pass(row, backend_reuse_required=False) for row in observed["sessions"]),
            "SESSION_CLEANUP_FAILED")
        all_turns = observed.get("turns", [])
        require(len(all_turns) == (len(expected) if diagnostic_role else 6)
                and all(all_true(row, TURN_BOOLS) for row in all_turns), "TURN_FAILED")
        measured = [row for row in all_turns if row["case_id"] != "CLOSE"]
        require([row["case_id"] for row in measured] == expected, "EXPERIMENT_SEQUENCE_FAILED")
        require(len({row["session_id"] for row in measured}) == (len(expected) if diagnostic_role else 2),
                "CONVERSATION_REUSE_INVALID")
        events = observed.get("timing_events", [])
        cache_starts = [event for event in events if event["stage"] == "cache_prefetch_start"]
        cache_terminals = [event for event in events if event["stage"] in {
            "cache_prefetch_complete", "cache_prefetch_cancelled", "cache_prefetch_failed"}]
        unavailable = [event for event in events if event["stage"] == "cache_prefetch_unavailable"]
        if observed.get("prefetch_expected"):
            require((len(cache_starts) == 1 and len(cache_terminals) == 1)
                    or (not cache_starts and (len(unavailable) == 1 or len(cache_terminals) == 1)),
                    "DIAGNOSTIC_INCOMPLETE")
        startup = timing_view("P01-STARTUP", observed["startup"])
        startup["case_id"] = "NATIVE-APP-START" if diagnostic_role else prefix + "01"
        startup_events = observed.get("startup_timing_events", [])
        native_startup = ("native_runtime_begin", "engine_init_begin", "engine_init_end", "native_runtime_ready")
        for stage in native_startup:
            matches = [event for event in startup_events if event["stage"] == stage]
            require(len(matches) == 1 and type(matches[0]["monotonic_ns"]) is int,
                    "DIAGNOSTIC_INCOMPLETE")
            startup["nodes"][stage] = matches[0]["monotonic_ns"]
        sequence = ("config_complete", *native_startup, "idle")
        require(all(startup["nodes"][left] <= startup["nodes"][right]
                    for left, right in zip(sequence, sequence[1:])), "TIMING_NODE_ORDER")
        for left, right in (("engine_init_begin", "engine_init_end"),
                            ("native_runtime_begin", "native_runtime_ready")):
            startup["durations_ns"][f"{left}_to_{right}"] = startup["nodes"][right] - startup["nodes"][left]
        startup.update(prior_inference=any(event["stage"] == "native_generation_start"
            and event["monotonic_ns"] < observed["startup"]["idle"] for event in events),
            startup_prework=True)  # Engine construction and prompt token attestation; no new pre-inference.
        require(not startup["prior_inference"], "PRETEST_INFERENCE")
        host = observed.get("host_context", {})
        require(type(host.get("boot_id")) is str and bool(host["boot_id"])
                and type(host.get("uptime_start_ns")) is int and type(host.get("uptime_end_ns")) is int
                and host["uptime_start_ns"] <= host["uptime_end_ns"], "DIAGNOSTIC_INCOMPLETE")
        startup.update(host_uptime_start_ns=host["uptime_start_ns"], host_uptime_end_ns=host["uptime_end_ns"])
        report["performance"].append(startup)
        for index, row in enumerate(measured):
            nodes = dict(row["nodes"])
            starts = [event for event in events if event["stage"] == "native_generation_start"
                      and event["session_id"] == row["session_id"]
                      and event["monotonic_ns"] == nodes.get("llm_send")]
            require(len(starts) == 1, "DIAGNOSTIC_INCOMPLETE")
            request = starts[0]
            same = [event for event in events if all(event.get(key) == request[key]
                    for key in ("request_id", "session_id", "generation"))]
            stages = ("parent_request_send", "child_request_receive", "native_generation_start",
                      "first_generated_output", "child_safe_text_emit", "parent_safe_text_receive",
                      "child_terminal_emit", "parent_terminal_receive")
            for stage in stages:
                candidates = [event for event in same if event["stage"] == stage]
                require(bool(candidates) and (len(candidates) == 1 or "safe_text" in stage),
                        "DIAGNOSTIC_INCOMPLETE")
                if "safe_text" in stage:
                    require([event.get("sequence") for event in candidates] == list(range(len(candidates))),
                            "DIAGNOSTIC_INCOMPLETE")
                nodes[stage] = candidates[0]["monotonic_ns"]
            require(nodes["native_generation_start"] == nodes["llm_send"], "DIAGNOSTIC_INCOMPLETE")
            preparation = ("response_format_begin", "response_format_end", "optional_args_begin",
                           "optional_args_end", "native_submit_begin", "native_submit_end")
            preparation_rows = {}
            for stage in preparation:
                candidates = [event for event in same if event["stage"] == stage]
                require(len(candidates) == 1, "DIAGNOSTIC_INCOMPLETE")
                preparation_rows[stage] = candidates[0]
                nodes[stage] = candidates[0]["monotonic_ns"]
            callback = next(event for event in same if event["stage"] == "first_generated_output")
            counters = {}
            for field in ("cpu_time_ns", "major_fault_count", "input_block_count"):
                before = preparation_rows["native_submit_begin"].get(field)
                after = callback.get(field)
                require(type(before) is int and type(after) is int and 0 <= before <= after,
                        "DIAGNOSTIC_INCOMPLETE")
                counters[field] = after - before
            render = [event for event in events if event["session_id"] == request["session_id"]
                      and event["generation"] == request["generation"]
                      and event["request_id"] == request["request_id"] - 1]
            for stage in ("render_begin", "render_end"):
                candidates = [event for event in render if event["stage"] == stage]
                require(len(candidates) == 1, "DIAGNOSTIC_INCOMPLETE")
                nodes[stage] = candidates[0]["monotonic_ns"]
            for stage in ("conversation_create", "conversation_ready"):
                candidates = [event for event in events if event["stage"] == stage
                              and event["session_id"] == row["session_id"]]
                require(len(candidates) == 1, "DIAGNOSTIC_INCOMPLETE")
                nodes[stage] = candidates[0]["monotonic_ns"]
            require(nodes["conversation_create"] <= nodes["conversation_ready"] <= nodes["parent_request_send"],
                    "TIMING_NODE_ORDER")
            required = ("asr_final", "first_safe_text", "llm_terminal", "first_frame", "last_frame",
                        "tts_first_pcm", "audio_first_write", "audio_complete")
            require(all(type(nodes.get(key)) is int and nodes[key] > 0 for key in required),
                    "DIAGNOSTIC_INCOMPLETE")
            edges = list(zip(stages[:6], stages[1:6])) + [
                ("render_begin", "render_end"), ("render_end", "parent_request_send"),
                ("first_frame", "last_frame"), ("last_frame", "asr_final"),
                ("child_safe_text_emit", "child_terminal_emit"),
                ("child_terminal_emit", "parent_terminal_receive"),
                ("asr_final", "parent_request_send"),
                ("parent_safe_text_receive", "tts_first_pcm"),
                ("tts_first_pcm", "audio_first_write"), ("audio_first_write", "audio_complete"),
                ("parent_terminal_receive", "audio_complete"),
                ("asr_final", "audio_first_write"), ("native_generation_start", "first_safe_text")]
            prepare_sequence = ("native_generation_start", *preparation[:-1])
            edges.extend(zip(prepare_sequence, prepare_sequence[1:]))
            edges.extend([("native_submit_begin", "native_submit_end"),
                          ("native_submit_begin", "first_generated_output")])
            if index in (1, 3):
                require(all(type(nodes.get(key)) is int for key in
                            ("previous_action_complete", "next_perception_start")), "DIAGNOSTIC_INCOMPLETE")
                edges.extend([("previous_action_complete", "next_perception_start"),
                              ("next_perception_start", "first_frame")])
            require(all(nodes[left] <= nodes[right] for left, right in edges), "TIMING_NODE_ORDER")
            counts = {"input_tokens": request.get("user_tokens"),
                      "context_tokens": request.get("current_kv_tokens"),
                      "rendered_input_tokens": request.get("rendered_incremental_tokens")}
            terminals = [event for event in same if event["stage"] == "child_terminal_emit"]
            counts["output_tokens"] = terminals[0].get("decode_tokens")
            require(all(type(value) is int and value >= 0 for value in counts.values()), "TOKEN_COUNT_MISSING")
            fragments = row["fragments"]
            require(bool(fragments) and all(all(type(fragment.get(key)) is int for key in
                ("admission", "queue_wait_ns", "queue_entry_depth", "batch_index", "tts_start",
                 "tts_first_pcm", "audio_start", "audio_first_write", "audio_complete")) for fragment in fragments),
                "FRAGMENT_NODE_MISSING")
            require(all(fragment["admission"] <= fragment["tts_start"] <= fragment["tts_first_pcm"]
                <= fragment["audio_first_write"] <= fragment["audio_complete"] <= nodes["audio_complete"]
                and fragment["queue_wait_ns"] >= 0 and fragment["queue_entry_depth"] >= 1
                for fragment in fragments), "FRAGMENT_NODE_ORDER")
            if row["case_id"] == prefix + "05":
                require(len(fragments) >= 2, "MULTIPLE_FRAGMENTS_MISSING")
            durations = {f"{left}_to_{right}": nodes[right] - nodes[left] for left, right in edges}
            view = {"case_id": row["case_id"], "turn_index": index,
                    "nodes": {key: nodes[key] for key in (*stages, *required, "conversation_create", "conversation_ready", "render_begin", "render_end")},
                    "durations_ns": durations, "token_counts": counts,
                    "fragments": fragments,
                    "idle_to_request_ns": nodes["parent_request_send"] - observed["startup"]["idle"],
                    "input_mode": "REALTIME_PCM" if run == "pn" else "MICROPHONE",
                    "reuse": {"engine_reused": observed.get("engine_reused") is True,
                              "child_reused": observed.get("child_reused") is True}}
            if index in (1, 3):
                view["nodes"].update({key: nodes[key] for key in
                                     ("previous_action_complete", "next_perception_start")})
            view["nodes"]["final_drain"] = nodes["audio_complete"]
            view["nodes"].update({key: nodes[key] for key in preparation})
            view["native_work"] = {**counters,
                "callback_before_return": nodes["first_generated_output"] < nodes["native_submit_end"],
                "return_to_callback_ns": (nodes["first_generated_output"] - nodes["native_submit_end"]
                    if nodes["first_generated_output"] >= nodes["native_submit_end"] else None)}
            if cache_starts and cache_terminals:
                begin, end = cache_starts[0], cache_terminals[0]
                require(all(begin[key] == end[key] for key in ("request_id", "session_id", "generation")),
                        "DIAGNOSTIC_INCOMPLETE")
                view["cache_prefetch"] = {"reason_code": end["stage"].upper(),
                    "read_bytes": end["cache_read_bytes"],
                    "duration_ns": end["monotonic_ns"] - begin["monotonic_ns"],
                    "completed_before_generation": end["stage"] == "cache_prefetch_complete"
                        and end["monotonic_ns"] <= nodes["native_generation_start"]}
            elif observed.get("prefetch_expected"):
                view["cache_prefetch"] = {"reason_code": "CACHE_UNAVAILABLE_OR_FAILED",
                                         "completed_before_generation": False}
            stage_intervals = list(zip(stages[:6], stages[1:6])) + [
                ("last_frame", "asr_final"), ("asr_final", "parent_request_send"),
                ("parent_safe_text_receive", "tts_first_pcm"), ("tts_first_pcm", "audio_first_write")]
            view["largest_stage_code"] = max((f"{left}_to_{right}" for left, right in stage_intervals),
                                               key=durations.get)
            if run == "pn":
                pacing = row.get("pacing", {})
                frames = pacing.get("frames", [])
                require(bool(frames) and all(0 <= frame["lateness_ns"] <= 20_000_000 for frame in frames),
                        "PACING_DISTORTED")
                deviation = frames[-1]["delivered_ns"] - frames[0]["delivered_ns"] - (len(frames) - 1) * 20_000_000
                require(abs(deviation) <= 20_000_000 and type(nodes.get("speech_end")) is int,
                        "PACING_DISTORTED")
                require(nodes["last_frame"] + 20_000_000 >= nodes["speech_end"]
                        and nodes["speech_end"] <= nodes["asr_final"], "PACING_DISTORTED")
                view["nodes"]["speech_end"] = nodes["speech_end"]
                view["pacing"] = {"frame_count": len(frames), "max_lateness_ns": max(frame["lateness_ns"] for frame in frames),
                                  "delivery_span_error_ns": deviation}
            else:
                matches = [item for item in (hearing or []) if item.get("turn_index") == index
                           and item.get("case_id") == row["case_id"]]
                human = matches[0] if len(matches) == 1 else {"report_status": "PENDING"}
                require(human.get("report_status") in {"CONFIRMED", "FAIL", "PENDING"}, "HEARING_REPORT_INVALID")
                view["report_status"] = human["report_status"]
                for key in ("unclear_speech", "stutter", "perceived_waiting", "playback_agreement"):
                    require(human["report_status"] == "PENDING" or type(human.get(key)) is bool,
                            "HEARING_REPORT_INVALID")
                    view[key] = human.get(key)
            report["performance"].append(view)
        report["stopped_cleanly"] = all_true(observed.get("cleanup", {}), CLEANUP)
        require(report["stopped_cleanly"], "OWNER_REMAINS")
        report.update(disposition="VALID_OBSERVATION", reason_code="BASELINE_CAPTURED")
        if run == "ph":
            human = report["performance"][1:]
            if any(row["report_status"] == "FAIL" or row.get("unclear_speech") is True
                   or row.get("stutter") is True or row.get("playback_agreement") is False for row in human):
                report.update(disposition="FAIL", reason_code="HEARING_FAILED")
            elif any(row["report_status"] != "CONFIRMED" for row in human):
                report.update(disposition="PENDING", reason_code="HEARING_REPORT_PENDING")
    except (InvalidObservation, KeyError, TypeError, ValueError) as error:
        code = error.code if isinstance(error, InvalidObservation) else "DIAGNOSTIC_INCOMPLETE"
        report.update(reason_code=code, disposition="FAIL" if code in {
            "TURN_FAILED", "APP_EXIT_FAILED", "SESSION_CLEANUP_FAILED", "UNEXPECTED_PRODUCT_ERROR",
            "SESSION_ENDED_BEFORE_FIXTURES", "APP_STOPPED_EARLY", "OWNER_REMAINS", "INITIAL_IDLE_FAILED"} else "INVALID")
    return report


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
