#!/usr/bin/env python3
"""Run one reboot-isolated Gate 2A P2/P3/P4/P5/P8 candidate on Pi 5."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time
from typing import Any, TextIO

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.m1_contract_boundary import normalize_response
from poc_llm.harness.gate2_errors_v1 import (
    CandidateViolation,
    EvidenceInvalid,
    sanitized_error,
    write_json_evidence,
)
from poc_llm.harness.pi_artifact_auth import streaming_digest, verify_model_receipt
from poc_llm.harness.pi_runtime import (
    PiPacketFailure,
    load,
    protocol_validator,
    read_frame,
    send,
    stop,
    target_preflight,
)
from poc_llm.harness.pi_runtime_v2 import native_library_preflight_v2, require_ready_v2
from poc_llm.tools.run_gate1_pi_compat_v7 import (
    catalog_input,
    close_child,
    generate,
    group_resource_sample,
    start_child,
    thermal_sample,
)


PACKET_ID = "G2A-PI-LLM-002"
GATE1_ENTRY_ID = "G1-M4B-CLOSURE-001"
CANDIDATES = (
    "CAND-LRT-G4E2B-MOBILE-R1",
    "CAND-LRT-Q25-15B-Q8-R1",
)
RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
EXECUTED_ITEMS = ("P2", "P3", "P4", "P5", "P8")
FORBIDDEN_LOG = (
    "raw model output:",
    "BEGIN PRIVATE PROMPT",
    "SECRET_PAYLOAD",
    "credential=",
    "api_key=",
    "hidden context:",
    "LEAK_MARKER",
)
STANDARD_INPUT = {
    "perceptions": [
        {"kind": "read", "status": "ok", "text": "Choose the rest action."}
    ],
    "pending_message_count": 0,
    "capabilities": {
        "perceptions": ["listen", "read", "look"],
        "actions": ["speak", "tool", "rest"],
        "tools": [],
    },
}
OBSERVATION_ERRORS = (
    PiPacketFailure,
    OSError,
    subprocess.SubprocessError,
    KeyError,
    TypeError,
    ValueError,
)
SCORED_PIPE_ERRORS = (PiPacketFailure, BrokenPipeError, ConnectionResetError, UnicodeError)
SCORED_CLOSE_ERRORS = SCORED_PIPE_ERRORS + (subprocess.TimeoutExpired,)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fatal-outcome-self-test", action="store_true")
    parser.add_argument("--packet-lock", type=Path, required=True)
    parser.add_argument("--gate1-entry", type=Path, required=True)
    parser.add_argument("--artifact-receipt", type=Path, required=True)
    parser.add_argument("--candidate-id", choices=CANDIDATES, required=True)
    parser.add_argument("--execution-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--max-prelaunch-uptime-s", type=float, default=1800.0)
    return parser.parse_args()


def valid_run_id(value: str) -> bool:
    return RUN_ID_RE.fullmatch(value) is not None


def ready_observation_config(
    config: dict[str, Any],
    candidate_id: str,
    policy: dict[str, int],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply a controller-only READY window without changing the frozen config identity."""

    contract_ms = config.get("ready_timeout_ms")
    default_ms = policy.get("default")
    operational_ms = policy.get(candidate_id, default_ms)
    if (
        not isinstance(contract_ms, int)
        or not isinstance(default_ms, int)
        or not isinstance(operational_ms, int)
        or contract_ms != default_ms
        or operational_ms < contract_ms
    ):
        raise PiPacketFailure("Gate 2A READY observation policy mismatch")
    observed = {**config, "ready_timeout_ms": operational_ms}
    metadata = {
        "contract_ms": contract_ms,
        "operational_ms": operational_ms,
        "workaround": (
            "P1.2_COLD_READY_OBSERVATION"
            if operational_ms != contract_ms
            else "NONE"
        ),
        "gate_credit": "FORBIDDEN",
    }
    return observed, metadata


def terminal_observation_timeout_s(config: dict[str, Any]) -> float:
    """Wait beyond the child timer only long enough to observe its terminal frame."""

    generate_ms = config.get("generate_timeout_ms")
    cancel_ms = config.get("cancel_timeout_ms")
    if (
        not isinstance(generate_ms, int)
        or not isinstance(cancel_ms, int)
        or generate_ms <= 0
        or cancel_ms < 0
    ):
        raise PiPacketFailure("Gate 2A terminal observation timeout config invalid")
    return (generate_ms + cancel_ms + 2000) / 1000


def repo_artifact(item: dict[str, str]) -> Path:
    path = (ROOT / item["path"]).resolve()
    if not path.is_file() or streaming_digest(path) != item["sha256"]:
        raise PiPacketFailure(f"locked repository artifact mismatch: {item['path']}")
    return path


def percentile(values: list[float], percent: int) -> float:
    if not values:
        raise PiPacketFailure("empty percentile sample")
    ordered = sorted(values)
    return ordered[max(0, (len(ordered) * percent + 99) // 100 - 1)]


def ancestor_check(gate1_sha: str, execution_sha: str) -> None:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", gate1_sha, execution_sha],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise PiPacketFailure("Gate 1 execution SHA is not an ancestor")


def isolation_state(max_uptime_s: float) -> dict[str, Any]:
    uptime_s = float(Path("/proc/uptime").read_text(encoding="ascii").split()[0])
    if uptime_s > max_uptime_s:
        raise PiPacketFailure("Gate 2A reboot-age isolation bound exceeded")
    boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    if not boot_id:
        raise PiPacketFailure("Gate 2A boot identity unavailable")
    process_count = 0
    for command_path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            command = command_path.read_bytes().replace(b"\0", b" ")
        except OSError:
            continue
        if b"litert_lm_pi_" in command and b"child_adapter" in command:
            process_count += 1
    if process_count:
        raise PiPacketFailure("pre-existing LiteRT-LM adapter process detected")
    return {
        "boot_id_sha256": hashlib.sha256(boot_id.encode("ascii")).hexdigest(),
        "prelaunch_uptime_s": round(uptime_s, 3),
        "preexisting_adapter_processes": 0,
    }


def enforce_isolation(
    evidence_root: Path,
    isolation: dict[str, Any],
    candidate_id: str,
) -> int:
    prior = sorted(evidence_root.glob("*/gate2a-sanitized.json"))
    for path in prior:
        value = load(path)
        if value.get("packet_id") != PACKET_ID:
            raise PiPacketFailure("Gate 2A evidence root identity contamination")
        if value.get("isolation", {}).get("boot_id_sha256") == isolation["boot_id_sha256"]:
            raise PiPacketFailure("Gate 2A boot ID was already consumed")
        if value.get("candidate_id") == candidate_id:
            raise PiPacketFailure("Gate 2A candidate already has an observation")
    return len(prior)


def launch_p5(
    *,
    config: Path,
    config_sha256: str,
    config_schema: Path,
    protocol_schema: Path,
    prompt_schema: Path,
    response_schema: Path,
    receipt: Path,
    receipt_schema: Path,
    install_root: Path,
    stderr: TextIO,
) -> subprocess.Popen[str]:
    argv = [
        "env", f"PYTHONPATH={install_root}", "python3",
        "poc_llm/harness/litert_lm_pi_p5_child_adapter_v1.py",
        "--config", str(config), "--config-sha256", config_sha256,
        "--config-schema", str(config_schema),
        "--config-schema-sha256", streaming_digest(config_schema),
        "--protocol-schema", str(protocol_schema),
        "--protocol-schema-sha256", streaming_digest(protocol_schema),
        "--prompt-schema", str(prompt_schema),
        "--prompt-schema-sha256", streaming_digest(prompt_schema),
        "--response-schema", str(response_schema),
        "--response-schema-sha256", streaming_digest(response_schema),
        "--artifact-receipt", str(receipt),
        "--artifact-receipt-sha256", streaming_digest(receipt),
        "--artifact-receipt-schema", str(receipt_schema),
        "--artifact-receipt-schema-sha256", streaming_digest(receipt_schema),
    ]
    return subprocess.Popen(
        argv,
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=stderr,
        text=True,
        start_new_session=True,
        env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
    )


def start_p5(
    *,
    config: Path,
    config_sha256: str,
    config_value: dict[str, Any],
    config_schema: Path,
    protocol_schema: Path,
    prompt_schema: Path,
    response_schema: Path,
    receipt: Path,
    receipt_schema: Path,
    install_root: Path,
    validator: Draft202012Validator,
    stderr: TextIO,
) -> tuple[subprocess.Popen[str], float]:
    started = time.monotonic()
    process = launch_p5(
        config=config,
        config_sha256=config_sha256,
        config_schema=config_schema,
        protocol_schema=protocol_schema,
        prompt_schema=prompt_schema,
        response_schema=response_schema,
        receipt=receipt,
        receipt_schema=receipt_schema,
        install_root=install_root,
        stderr=stderr,
    )
    try:
        require_ready_v2(process, validator, config_value, config_sha256)
    except Exception:
        stop(process)
        raise
    return process, round((time.monotonic() - started) * 1000, 3)


def scored_generate(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], float]:
    """Classify a READY child's scored protocol timeout/EOF/frame defect as candidate behavior."""

    try:
        return generate(*args, **kwargs)
    except SCORED_PIPE_ERRORS as error:
        raise CandidateViolation("post-READY scored protocol failure") from error


def scored_pong(
    process: subprocess.Popen[str], validator: Draft202012Validator
) -> dict[str, Any]:
    """Run the scored same-child liveness exchange after READY."""

    try:
        send(process, {"type": "PING", "protocol_version": "snowboard.llm/1"})
        if process.stdout is None:
            raise PiPacketFailure("P5 child stdout unavailable")
        return read_frame(process.stdout, 2.0, validator)
    except SCORED_PIPE_ERRORS as error:
        raise CandidateViolation("post-READY same-child protocol failure") from error


def scored_close_child(
    process: subprocess.Popen[str], validator: Draft202012Validator
) -> dict[str, Any]:
    """Treat a READY candidate's failed protocol shutdown as a scored violation."""

    try:
        return close_child(process, validator)
    except SCORED_CLOSE_ERRORS as error:
        raise CandidateViolation("post-READY candidate cleanup failure") from error


def p2_valid(
    terminal: dict[str, Any],
    entry: dict[str, Any],
    expected_fallback: dict[str, Any],
    *,
    engine_capacity: int,
    max_output_tokens: int,
) -> bool:
    response = terminal.get("response", {})
    metrics = terminal.get("metrics", {})
    metrics_valid = all(
        isinstance(metrics.get(name), int) and not isinstance(metrics.get(name), bool)
        for name in ("prefill_tokens", "decode_tokens", "kv_tokens")
    )
    return bool(
        terminal.get("type") == "RESULT"
        and response != expected_fallback
        and response.get("action_kind") == entry["expected_kind"]
        and (
            entry["expected_kind"] != "tool"
            or response.get("action_payload", {}).get("name") == entry["tool"]
        )
        and metrics_valid
        and metrics["prefill_tokens"] > 0
        and 0 < metrics["decode_tokens"] <= max_output_tokens
        and 0 < metrics["kv_tokens"] <= engine_capacity
        and metrics["kv_tokens"]
        <= metrics["prefill_tokens"] + metrics["decode_tokens"] + 16
    )


def p8_input(template: str, entry: dict[str, str]) -> dict[str, Any]:
    return {
        "perceptions": [{
            "kind": "read",
            "status": "ok",
            "text": template.format(nonce=entry["nonce"], trap=entry["trap"]),
        }],
        "pending_message_count": 0,
        "capabilities": {
            "perceptions": ["listen"],
            "actions": ["speak"],
            "tools": [],
        },
    }


def p4_summary(cold: list[dict[str, Any]], hot: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "cold_wall_p50_ms": round(statistics.median(item["wall_ms"] for item in cold), 3),
        "hot_wall_p50_ms": round(statistics.median(item["wall_ms"] for item in hot), 3),
        "hot_wall_p95_ms": round(percentile([item["wall_ms"] for item in hot], 95), 3),
        "ttft_p50_ms": round(statistics.median(item["metrics"]["ttft_ms"] for item in hot), 3),
        "ttft_p95_ms": round(percentile([item["metrics"]["ttft_ms"] for item in hot], 95), 3),
        "decode_p50_tokens_per_second": round(statistics.median(item["metrics"]["decode_tokens_per_second"] for item in hot), 3),
        "decode_p95_tokens_per_second": round(percentile([item["metrics"]["decode_tokens_per_second"] for item in hot], 95), 3),
    }


def scan_owned_logs(raw_dir: Path, runtime_markers: set[str]) -> dict[str, Any]:
    files: list[dict[str, str]] = []
    leaked = False
    markers = tuple(FORBIDDEN_LOG) + tuple(
        marker for marker in sorted(runtime_markers) if marker
    )
    for path in sorted(raw_dir.iterdir()):
        if not path.is_file() or path.name == "gate2a-sanitized.json":
            continue
        try:
            content = path.read_bytes()
            text = content.decode("utf-8", errors="replace")
        except OSError as error:
            raise EvidenceInvalid("Gate 2A owned-log scan failed") from error
        files.append({"name": path.name, "sha256": hashlib.sha256(content).hexdigest()})
        if any(marker in text for marker in FORBIDDEN_LOG):
            leaked = True
        if any(marker in text for marker in markers[len(FORBIDDEN_LOG):]):
            leaked = True
    return {
        "passed": not leaked,
        "scanned_files": files,
        "static_marker_count": len(FORBIDDEN_LOG),
        "runtime_marker_count": len(markers) - len(FORBIDDEN_LOG),
    }


def p5_result_disposition(
    terminal: dict[str, Any],
    elapsed_ms: float,
    *,
    markers_ok: bool,
    health_ok: bool,
    rebuild_ok: bool,
) -> str:
    terminal_ok = (
        terminal.get("type") == "ERROR"
        and terminal.get("code") == "TIMEOUT"
        and terminal.get("request_id") == "p5-continuous"
        and 15000 <= elapsed_ms <= 17000
    )
    if terminal_ok and markers_ok and health_ok and rebuild_ok:
        return "PASS"
    if terminal.get("type") == "RESULT" and elapsed_ms < 15000:
        return "INCONCLUSIVE"
    return "FAIL"


def p5_runner_disposition(
    terminal: dict[str, Any],
    elapsed_ms: float,
    *,
    markers_ok: bool,
    health_ok: bool,
    rebuild_ok: bool,
    candidate_error: str | None,
    observation_error: str | None,
    rebuild_candidate_error: str | None,
    rebuild_observation_error: str | None,
) -> str:
    """Apply the typed matrix used by the real P5 runner path."""

    primary = p5_primary_disposition(
        terminal,
        elapsed_ms,
        markers_ok=markers_ok,
        health_ok=health_ok,
        candidate_error=candidate_error,
        observation_error=observation_error,
    )
    if primary != "PASS":
        return primary
    if rebuild_candidate_error is not None:
        return "FAIL"
    if rebuild_observation_error is not None:
        return "INCONCLUSIVE"
    return "PASS" if rebuild_ok else "FAIL"


def p5_primary_disposition(
    terminal: dict[str, Any],
    elapsed_ms: float,
    *,
    markers_ok: bool,
    health_ok: bool,
    candidate_error: str | None,
    observation_error: str | None,
) -> str:
    if candidate_error is not None:
        return "FAIL"
    if observation_error is not None:
        return "INCONCLUSIVE"
    return p5_result_disposition(
        terminal, elapsed_ms, markers_ok=markers_ok,
        health_ok=health_ok, rebuild_ok=True,
    )


def cleanup_pass(value: object) -> bool:
    return isinstance(value, dict) and value == {
        "exit_code": 0, "waited": True, "term_sent": False,
        "kill_sent": False, "process_group_absent": True,
    }


def verify_gate2a_result(
    result: dict[str, Any],
    catalog: dict[str, Any],
    p8_fixture: dict[str, Any],
    *,
    engine_capacity: int,
    max_output_tokens: int,
) -> dict[str, str]:
    """Independently recompute Gate 2A dispositions from sanitized evidence."""

    samples = result.get("samples", {})
    computed: dict[str, str] = {}
    p2 = samples.get("p2", {})
    p2_cases = p2.get("cases", []) if isinstance(p2, dict) else []
    expected_p2 = {
        (entry["id"], repetition)
        for entry in catalog["valid_cases"]
        for repetition in range(catalog["repetitions"])
    }
    observed_p2 = {
        (item.get("id"), item.get("repetition"))
        for item in p2_cases if isinstance(item, dict)
    }
    if isinstance(p2, dict) and p2.get("error_type") is not None:
        computed["P2"] = "INCONCLUSIVE"
    else:
        valid_p2 = (
            len(p2_cases) == len(expected_p2)
            and observed_p2 == expected_p2
            and all(
                item.get("valid") is True
                and isinstance(item.get("prefill_tokens"), int)
                and item["prefill_tokens"] > 0
                and isinstance(item.get("decode_tokens"), int)
                and 0 < item["decode_tokens"] <= max_output_tokens
                and isinstance(item.get("kv_tokens"), int)
                and 0 < item["kv_tokens"] <= engine_capacity
                and item["kv_tokens"]
                <= item["prefill_tokens"] + item["decode_tokens"] + 16
                for item in p2_cases
            )
        )
        computed["P2"] = "PASS" if valid_p2 else "FAIL"

    p3 = samples.get("p3", [])
    expected_p3 = {entry["id"] for entry in catalog["failure_raw_outputs"]}
    observed_p3 = {item.get("id") for item in p3 if isinstance(item, dict)}
    computed["P3"] = "PASS" if (
        len(p3) == len(expected_p3)
        and observed_p3 == expected_p3
        and all(
            item.get("repetitions") == catalog["repetitions"]
            and item.get("deterministic") is True
            and item.get("fallback") is True
            for item in p3
        )
    ) else "FAIL"

    p4 = samples.get("p4", {})
    failures = p4.get("failures", []) if isinstance(p4, dict) else []
    if any(item.get("category") != "CandidateViolation" for item in failures):
        computed["P4"] = "INCONCLUSIVE"
    elif failures:
        computed["P4"] = "FAIL"
    else:
        cold, warmups, hot = p4.get("cold", []), p4.get("warmups", []), p4.get("hot", [])
        complete = len(cold) == 3 and len(warmups) == 3 and len(hot) == 20
        try:
            summary = p4_summary(cold, hot) if complete else {}
            environment_ok = complete and all(
                item["thermal"]["temperature_c"] < 80
                and item["thermal"]["throttled"] == "0x0"
                and item["resources"]["pss_mib"] > 0
                for item in cold + hot
            )
            metrics_complete = complete and all(
                isinstance(item.get("wall_ms"), (int, float))
                and isinstance(item.get("metrics", {}).get("ttft_ms"), (int, float))
                and isinstance(item.get("metrics", {}).get("decode_tokens_per_second"), (int, float))
                for item in warmups + hot
            )
        except (KeyError, TypeError, ValueError, statistics.StatisticsError):
            environment_ok = metrics_complete = False
            summary = {}
        if not complete or not metrics_complete:
            computed["P4"] = "INCONCLUSIVE"
        elif not environment_ok:
            computed["P4"] = "INCONCLUSIVE"
        elif p4.get("summary") != summary:
            computed["P4"] = "INCONCLUSIVE"
        elif summary["ttft_p95_ms"] <= 2500 and summary["decode_p50_tokens_per_second"] >= 4:
            computed["P4"] = "PASS"
        else:
            computed["P4"] = "Core threshold decision required"

    p5 = samples.get("p5", {})
    counts = p5.get("marker_counts", {}) if isinstance(p5, dict) else {}
    mode = p5.get("timeout_mode") if isinstance(p5, dict) else None
    active_markers = (
        counts.get("chunk_started", 0) >= 1
        and counts.get("chunk_started", 0) > counts.get("chunk_completed", 0)
        and counts.get("native_cancel_once") == 1
        and counts.get("native_cancel_failed") == 0
        and counts.get("timeout_between_chunks") == 0
    )
    boundary_markers = (
        counts.get("chunk_completed", 0) >= 1
        and counts.get("chunk_started") == counts.get("chunk_completed")
        and counts.get("native_cancel_once") == 0
        and counts.get("native_cancel_failed") == 0
        and counts.get("timeout_between_chunks") == 1
    )
    marker_mode_ok = (
        (mode == "ACTIVE_CHUNK_CANCEL" and active_markers)
        or (mode == "BETWEEN_CHUNKS_STOP" and boundary_markers)
    ) and counts.get("continuous_terminal_cancelled") == 1
    marker_mode_ok = marker_mode_ok and counts.get("conversation_discarded", 0) >= counts.get("chunk_started", 0)
    computed["P5"] = p5_runner_disposition(
        {"type":p5.get("terminal"), "code":p5.get("code"),
         "request_id":"p5-continuous"},
        p5.get("elapsed_ms", -1), markers_ok=marker_mode_ok,
        health_ok=(p5.get("same_child_pong") == "PONG"
                   and p5.get("same_child_health_terminal") == "RESULT"),
        rebuild_ok=p5.get("rebuild_health_terminal") == "RESULT",
        candidate_error=p5.get("candidate_error_type"),
        observation_error=p5.get("observation_error_type"),
        rebuild_candidate_error=p5.get("rebuild_candidate_error_type"),
        rebuild_observation_error=p5.get("rebuild_error_type"),
    )

    p8 = samples.get("p8", {})
    p8_cases = p8.get("cases", []) if isinstance(p8, dict) else []
    expected_p8 = {entry["id"] for entry in p8_fixture["cases"]}
    if isinstance(p8, dict) and p8.get("error_type") is not None:
        computed["P8"] = "INCONCLUSIVE"
    else:
        computed["P8"] = "PASS" if (
            len(p8_cases) == len(expected_p8)
            and {item.get("id") for item in p8_cases} == expected_p8
            and all(
                item.get("terminal") == "RESULT"
                and item.get("prior_marker_leaked") is False
                and item.get("current_marker_present_once") is True
                and item.get("current_trap_absent") is True
                and item.get("kv_is_single_turn") is True
                for item in p8_cases
            )
        ) else "FAIL"

    hygiene = samples.get("log_hygiene", {})
    if hygiene.get("passed") is not True:
        computed["P3"] = "FAIL"
    cleanup = result.get("cleanup", {})
    cleanup_items = {
        "P2": ("p2",), "P4": ("standard",), "P5": ("p5_same_child", "p5_rebuild"),
        "P8": ("p8",),
    }
    for item, names in cleanup_items.items():
        if computed[item] in {"PASS", "Core threshold decision required"} and not all(
            cleanup_pass(cleanup.get(name)) for name in names
        ):
            computed[item] = "FAIL"
    if computed["P4"] in {"PASS", "Core threshold decision required"} and not (
        isinstance(cleanup.get("p4_cold"), list)
        and len(cleanup["p4_cold"]) == 3
        and all(cleanup_pass(item) for item in cleanup["p4_cold"])
    ):
        computed["P4"] = "FAIL"
    if result.get("executed_results") != computed:
        raise EvidenceInvalid("Gate 2A claimed dispositions do not match sanitized evidence")
    if any(value == "FAIL" for value in computed.values()):
        scope = "FAIL"
    elif any(value in {"INCONCLUSIVE", "Blocked"} for value in computed.values()):
        scope = "INCONCLUSIVE"
    elif computed["P4"] == "Core threshold decision required":
        scope = "Core threshold decision required"
    else:
        scope = "PASS"
    if "gate2a_scope_result" in result and (
        result.get("gate2a_scope_result") != scope or result.get("result") != scope
    ):
        raise EvidenceInvalid("Gate 2A scope result does not match P dispositions")
    if "provisional_eligibility" in result:
        expected_eligibility = (
            "ELIGIBLE_FOR_USER_REVIEW" if scope == "PASS" and result.get("candidate_id") == CANDIDATES[0]
            else "WORKAROUND_DISPOSITION_REQUIRED" if scope == "PASS"
            else "PENDING" if scope == "Core threshold decision required"
            else "NOT_ELIGIBLE"
        )
        if result["provisional_eligibility"] != expected_eligibility:
            raise EvidenceInvalid("Gate 2A eligibility does not match evidence")
    return computed


def initial_result(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "packet_id": PACKET_ID,
        "run_id": args.run_id,
        "candidate_id": args.candidate_id,
        "execution_sha": args.execution_sha,
        "execution_surface_sha256": "",
        "gate1_entry": {},
        "isolation": {},
        "environment": {},
        "environment_post": {},
        "runtime": {},
        "artifact_authentication": {},
        "carried_results": {},
        "executed_results": {item: "Blocked" for item in EXECUTED_ITEMS},
        "samples": {},
        "cleanup": {},
        "violations": [],
        "gate2a_scope_result": "INCONCLUSIVE",
        "provisional_eligibility": "PENDING",
        "result": "INCONCLUSIVE",
    }


def main() -> int:
    if sys.argv[1:] == ["--fatal-outcome-self-test"]:
        return 4
    args = parse_args()
    if args.fatal_outcome_self_test:
        return 4
    result = initial_result(args)
    if not valid_run_id(args.run_id):
        result["violations"].append("Gate 2A run ID is not a safe slug")
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 2
    raw_dir = args.evidence_root / args.run_id
    install_root = Path(f"/tmp/llm-poc-g2a-002/install-{args.run_id}")
    active: subprocess.Popen[str] | None = None
    result_schema: Path | None = None
    receipt: dict[str, Any] | None = None
    config_value: dict[str, Any] | None = None
    owns_raw_dir = False
    owns_install_root = False
    try:
        if raw_dir.exists() or install_root.exists():
            raise PiPacketFailure("Gate 2A run-owned path is dirty")
        if raw_dir.resolve().is_relative_to(ROOT):
            raise PiPacketFailure("Gate 2A controlled evidence must remain outside Git")
        lock = load(args.packet_lock)
        if (
            lock.get("packet_id") != PACKET_ID
            or lock.get("executed_items") != list(EXECUTED_ITEMS)
            or lock.get("carried_items") != ["P1", "P6.1", "P7.1", "P10A", "P11", "P12"]
            or lock.get("ready_observation_ms") != {
                "default": 10000,
                "CAND-LRT-Q25-15B-Q8-R1": 30000,
            }
            or lock.get("thresholds") != {
                "p4_ttft_p95_ms": 2500,
                "p4_decode_p50_tokens_per_second": 4,
                "p5_timeout_window_ms": [15000, 17000],
            }
        ):
            raise PiPacketFailure("Gate 2A lock identity mismatch")
        result["execution_surface_sha256"] = streaming_digest(args.packet_lock)
        artifacts = {name: repo_artifact(item) for name, item in lock["artifacts"].items()}
        result_schema = artifacts["result_schema"]
        for lock_name in ("gate1_base_lock", "gate1_replacement_lock"):
            carried_lock = load(artifacts[lock_name])
            for item in carried_lock.get("artifacts", {}).values():
                repo_artifact(item)
        candidate_set = artifacts["gate1_candidate_set"]
        if any(
            load(artifacts[name]).get("candidate_set_sha256")
            != streaming_digest(candidate_set)
            for name in ("gate1_base_lock", "gate1_replacement_lock")
        ):
            raise PiPacketFailure("Gate 1 candidate-set carry identity mismatch")
        expected_entry = artifacts["gate1_entry"]
        if args.gate1_entry.resolve() != expected_entry:
            raise PiPacketFailure("Gate 1 closure entry path mismatch")
        gate1_entry = load(expected_entry)
        if not Draft202012Validator(load(artifacts["gate1_entry_schema"])).is_valid(gate1_entry):
            raise PiPacketFailure("Gate 1 closure entry schema mismatch")
        if gate1_entry.get("entry_id") != GATE1_ENTRY_ID:
            raise PiPacketFailure("Gate 1 closure entry identity mismatch")
        ancestor_check(gate1_entry["gate1_execution_sha"], args.execution_sha)
        carried = gate1_entry["candidates"][args.candidate_id]
        result["gate1_entry"] = {
            "entry_id": gate1_entry["entry_id"],
            "core_ack_id": gate1_entry["core_ack_id"],
            "gate1_execution_sha": gate1_entry["gate1_execution_sha"],
            "gate1_execution_surface_sha256": gate1_entry["gate1_execution_surface_sha256"],
            "entry_disposition": carried["entry_disposition"],
        }
        result["carried_results"] = {
            item: carried[item] for item in ("P1", "P6.1", "P7.1", "P10A", "P11", "P12")
        }
        raw_dir.mkdir(parents=True, exist_ok=False)
        owns_raw_dir = True
        result["isolation"] = isolation_state(args.max_prelaunch_uptime_s)
        result["isolation"]["prior_receipts_checked"] = enforce_isolation(
            args.evidence_root, result["isolation"], args.candidate_id
        )
        result["environment"] = target_preflight(args.execution_sha)

        runtime = lock["runtime"]
        owns_install_root = True
        install = subprocess.run(
            [
                "python3", str(artifacts["installer"]),
                "--wheel", runtime["wheel_path"],
                "--wheel-sha256", runtime["wheel_sha256"],
                "--target", str(install_root),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=300,
        )
        (raw_dir / "offline-install.stdout").write_text(install.stdout, encoding="utf-8")
        (raw_dir / "offline-install.stderr").write_text(install.stderr, encoding="utf-8")
        try:
            install_value = json.loads(install.stdout)
        except json.JSONDecodeError as error:
            raise PiPacketFailure("Gate 2A installer result invalid") from error
        if install.returncode != 0 or install_value.get("result") != "PASS":
            raise PiPacketFailure("Gate 2A offline installation failed")
        result["runtime"] = native_library_preflight_v2(
            install_root / "litert_lm/liblitert-lm.so",
            runtime["native_library_sha256"],
        )

        candidate = lock["candidates"][args.candidate_id]
        standard = repo_artifact(candidate["standard_config"])
        product_config = repo_artifact(candidate["product_config"])
        p5_config = repo_artifact(candidate["p5_config"])
        config_value = load(standard)
        product_value = load(product_config)
        p5_value = load(p5_config)
        if (
            config_value["candidate_id"] != args.candidate_id
            or product_value["candidate_id"] != args.candidate_id
            or p5_value["candidate_id"] != args.candidate_id
            or product_value["model_sha256"] != config_value["model_sha256"]
            or product_value["runtime_sha256"] != config_value["runtime_sha256"]
            or product_value["max_output_tokens"] != 64
            or product_value["engine_max_num_tokens"] != config_value["engine_max_num_tokens"]
            or p5_value["engine_max_num_tokens"] != config_value["engine_max_num_tokens"]
            or p5_value["max_output_tokens"] > 512
        ):
            raise PiPacketFailure("Gate 2A candidate config drift")
        observed_standard_value, ready_observation = ready_observation_config(
            config_value, args.candidate_id, lock["ready_observation_ms"]
        )
        observed_product_value, product_ready_observation = ready_observation_config(
            product_value, args.candidate_id, lock["ready_observation_ms"]
        )
        observed_p5_value, p5_ready_observation = ready_observation_config(
            p5_value, args.candidate_id, lock["ready_observation_ms"]
        )
        if not ready_observation == product_ready_observation == p5_ready_observation:
            raise PiPacketFailure("Gate 2A candidate READY observation profiles differ")
        result["isolation"]["ready_observation"] = ready_observation
        product_terminal_timeout_s = terminal_observation_timeout_s(product_value)

        receipt_schema = artifacts["artifact_receipt_schema"]
        receipt = load(args.artifact_receipt)
        if not Draft202012Validator(load(receipt_schema)).is_valid(receipt):
            raise PiPacketFailure("Gate 1 artifact receipt schema mismatch")
        if (
            receipt["packet_id"] != "G1-PI-COMPAT-007"
            or receipt["execution_sha"] != gate1_entry["gate1_execution_sha"]
            or receipt["candidate_id"] != args.candidate_id
            or receipt["runtime_sha256"] != runtime["wheel_sha256"]
            or receipt["model"]["sha256"] != config_value["model_sha256"]
        ):
            raise PiPacketFailure("Gate 1 artifact receipt does not authorize candidate")
        verify_model_receipt(
            receipt["model"], Path(config_value["model_path"]), config_value["model_sha256"]
        )
        result["artifact_authentication"] = {
            "reused_receipt_sha256": streaming_digest(args.artifact_receipt),
            "model_sha256": receipt["model"]["sha256"],
            "model_size_bytes": receipt["model"]["size_bytes"],
            "full_model_hash_count": 0,
            "metadata_unchanged": False,
        }

        protocol = artifacts["protocol_schema"]
        prompt_schema = artifacts["prompt_schema"]
        response_schema = artifacts["response_schema"]
        standard_schema = artifacts["standard_config_schema"]
        product_schema = artifacts["product_config_schema"]
        p5_schema = artifacts["p5_config_schema"]
        validator = protocol_validator(protocol, prompt_schema, response_schema)
        catalog = load(artifacts["catalog"])
        p5_fixture = load(artifacts["p5_fixture"])
        p8_fixture = load(artifacts["p8_fixture"])
        runtime_log_markers = {
            entry["text"] for entry in catalog["valid_cases"]
        } | {
            entry["raw"] for entry in catalog["failure_raw_outputs"] if entry["raw"]
        } | {
            value for entry in p8_fixture["cases"]
            for value in (entry["nonce"], entry["trap"])
        } | {
            perception["text"] for perception in p5_fixture["input"]["perceptions"]
        }
        if (
            p5_fixture["timeout_ms"] != 15000
            or p5_fixture["timeout_pass_window_ms"] != [15000, 17000]
            or p5_fixture["chunk_max_output_tokens"] != 512
            or p5_fixture["candidate_chunk_max_output_tokens"].get(args.candidate_id)
            != p5_value["max_output_tokens"]
            or p5_fixture["completed_chunk_disposition"] != "CONTINUE"
            or not p5_fixture["result_before_timeout_forbidden"]
            or not p5_fixture["adaptive_fixture_forbidden"]
        ):
            raise PiPacketFailure("P5 continuous fixture drift")

        common = {
            "config": standard,
            "config_sha256": candidate["standard_config"]["sha256"],
            "config_value": observed_standard_value,
            "config_schema": standard_schema,
            "protocol_schema": protocol,
            "prompt_schema": prompt_schema,
            "response_schema": response_schema,
            "receipt": args.artifact_receipt,
            "receipt_schema": receipt_schema,
            "install_root": install_root,
            "validator": validator,
        }
        product_common = {
            **common,
            "config": product_config,
            "config_sha256": candidate["product_config"]["sha256"],
            "config_value": observed_product_value,
            "config_schema": product_schema,
        }

        standard_stderr = raw_dir / "standard.stderr"
        with standard_stderr.open("w", encoding="utf-8") as stderr:
            cold: list[dict[str, Any]] = []
            cold_cleanup: list[dict[str, Any]] = []
            p4_failures: list[dict[str, Any]] = []
            for index in range(3):
                active, ready_ms = start_child(**common, stderr=stderr)
                try:
                    terminal, wall_ms = generate(
                        active, validator, f"p4-cold-{index}", STANDARD_INPUT
                    )
                    if terminal.get("type") == "RESULT":
                        cold.append({
                            "ready_ms": ready_ms,
                            "wall_ms": wall_ms,
                            "metrics": terminal["metrics"],
                            "resources": group_resource_sample(active.pid),
                            "thermal": thermal_sample(),
                        })
                    else:
                        p4_failures.append({
                            "phase": "cold", "index": index,
                            "category": "CandidateViolation",
                            "terminal": terminal.get("type"),
                            "code": terminal.get("code"),
                        })
                    cold_cleanup.append(close_child(active, validator))
                    active = None
                except OBSERVATION_ERRORS as error:
                    p4_failures.append({
                        "phase": "cold", "index": index,
                        "category": "EnvironmentInvalid",
                        "error_type": type(error).__name__,
                    })
                    result["cleanup"][f"p4_cold_forced_{index}"] = stop(active)
                    active = None

            active, p2_ready_ms = start_child(**product_common, stderr=stderr)
            p2: list[dict[str, Any]] = []
            p2_error: str | None = None
            try:
                for entry in catalog["valid_cases"]:
                    for repetition in range(catalog["repetitions"]):
                        terminal, wall_ms = generate(
                            active,
                            validator,
                            f"{entry['id']}-{repetition}",
                            catalog_input(entry),
                            timeout_s=product_terminal_timeout_s,
                        )
                        p2.append({
                            "id": entry["id"],
                            "repetition": repetition,
                            "wall_ms": wall_ms,
                            "valid": p2_valid(
                                terminal,
                                entry,
                                catalog["expected_fallback"],
                                engine_capacity=product_value["engine_max_num_tokens"],
                                max_output_tokens=product_value["max_output_tokens"],
                            ),
                            "prefill_tokens": terminal.get("metrics", {}).get("prefill_tokens"),
                            "decode_tokens": terminal.get("metrics", {}).get("decode_tokens"),
                            "kv_tokens": terminal.get("metrics", {}).get("kv_tokens"),
                            "response_sha256": hashlib.sha256(
                                json.dumps(terminal.get("response", {}), sort_keys=True).encode()
                            ).hexdigest(),
                        })
                result["cleanup"]["p2"] = close_child(active, validator)
                active = None
            except OBSERVATION_ERRORS as error:
                p2_error = type(error).__name__
                result["cleanup"]["p2_forced"] = stop(active)
                active = None
            result["executed_results"]["P2"] = (
                "INCONCLUSIVE" if p2_error is not None else
                "PASS" if len(p2) == 30 and all(item["valid"] for item in p2)
                else "FAIL"
            )

            p3: list[dict[str, Any]] = []
            for entry in catalog["failure_raw_outputs"]:
                observed: list[tuple[dict[str, Any], tuple[str, ...]]] = []
                for _ in range(catalog["repetitions"]):
                    observed.append(normalize_response(
                        entry["raw"], STANDARD_INPUT, refused=entry["refused"]
                    ))
                deterministic = all(item == observed[0] for item in observed)
                fallback = all(item[0] == catalog["expected_fallback"] for item in observed)
                p3.append({
                    "id": entry["id"],
                    "repetitions": len(observed),
                    "deterministic": deterministic,
                    "fallback": fallback,
                    "diagnostic_sha256": hashlib.sha256(
                        "\n".join(observed[0][1]).encode()
                    ).hexdigest(),
                })
            result["executed_results"]["P3"] = (
                "PASS" if len(p3) == 10 and all(item["deterministic"] and item["fallback"] for item in p3) else "FAIL"
            )

            active, resident_ready_ms = start_child(**common, stderr=stderr)

            warmups: list[dict[str, Any]] = []
            hot: list[dict[str, Any]] = []
            try:
                for index in range(3):
                    terminal, wall_ms = generate(
                        active, validator, f"p4-warmup-{index}", STANDARD_INPUT
                    )
                    if terminal.get("type") == "RESULT":
                        warmups.append({"wall_ms": wall_ms, "metrics": terminal["metrics"]})
                    else:
                        p4_failures.append({
                            "phase": "warmup", "index": index,
                            "category": "CandidateViolation",
                            "terminal": terminal.get("type"),
                            "code": terminal.get("code"),
                        })
                for index in range(20):
                    terminal, wall_ms = generate(
                        active, validator, f"p4-hot-{index}", STANDARD_INPUT
                    )
                    if terminal.get("type") == "RESULT":
                        hot.append({
                            "wall_ms": wall_ms,
                            "metrics": terminal["metrics"],
                            "resources": group_resource_sample(active.pid),
                            "thermal": thermal_sample(),
                        })
                    else:
                        p4_failures.append({
                            "phase": "hot", "index": index,
                            "category": "CandidateViolation",
                            "terminal": terminal.get("type"),
                            "code": terminal.get("code"),
                        })
                result["cleanup"]["standard"] = close_child(active, validator)
                active = None
            except OBSERVATION_ERRORS as error:
                p4_failures.append({
                    "phase": "resident", "category": "EnvironmentInvalid",
                    "error_type": type(error).__name__,
                })
                result["cleanup"]["standard_forced"] = stop(active)
                active = None
            method_complete = (
                len(cold) == 3 and len(warmups) == 3 and len(hot) == 20
                and not p4_failures
            )
            summary = p4_summary(cold, hot) if method_complete else {}
            p4_environment_ok = method_complete and all(
                item["thermal"]["temperature_c"] < 80
                and item["thermal"]["throttled"] == "0x0"
                and item["resources"]["pss_mib"] > 0
                for item in cold + hot
            )
            if any(item["category"] == "EnvironmentInvalid" for item in p4_failures):
                result["executed_results"]["P4"] = "INCONCLUSIVE"
            elif not method_complete:
                result["executed_results"]["P4"] = "FAIL"
            elif not p4_environment_ok:
                result["executed_results"]["P4"] = "INCONCLUSIVE"
            elif (
                summary["ttft_p95_ms"] <= 2500
                and summary["decode_p50_tokens_per_second"] >= 4
            ):
                result["executed_results"]["P4"] = "PASS"
            else:
                result["executed_results"]["P4"] = "Core threshold decision required"

            result["samples"].update({
                "p2": {"ready_ms": p2_ready_ms, "cases": p2, "error_type": p2_error},
                "p3": p3,
                "p4": {
                    "resident_ready_ms": resident_ready_ms,
                    "cold": cold,
                    "warmups": warmups,
                    "hot": hot,
                    "summary": summary,
                    "failures": p4_failures,
                },
            })
            result["cleanup"]["p4_cold"] = cold_cleanup

            active, p8_ready_ms = start_child(**product_common, stderr=stderr)
            p8: list[dict[str, Any]] = []
            prior_markers: list[str] = []
            p8_error: str | None = None
            try:
                for entry in p8_fixture["cases"]:
                    terminal, wall_ms = generate(
                        active,
                        validator,
                        entry["id"].lower(),
                        p8_input(p8_fixture["prompt_template"], entry),
                        timeout_s=product_terminal_timeout_s,
                    )
                    encoded = json.dumps(
                        terminal.get("response", {}), sort_keys=True, ensure_ascii=True
                    )
                    leaked = any(marker in encoded for marker in prior_markers)
                    current_marker_present = encoded.count(entry["nonce"]) == 1
                    current_trap_absent = entry["trap"] not in encoded
                    metrics = terminal.get("metrics", {})
                    metric_values_valid = (
                        isinstance(metrics.get("kv_tokens"), int)
                        and not isinstance(metrics.get("kv_tokens"), bool)
                        and isinstance(metrics.get("prefill_tokens"), int)
                        and not isinstance(metrics.get("prefill_tokens"), bool)
                        and isinstance(metrics.get("decode_tokens"), int)
                        and not isinstance(metrics.get("decode_tokens"), bool)
                    )
                    kv_valid = (
                        metric_values_valid
                        and metrics["prefill_tokens"] > 0
                        and 0 < metrics["decode_tokens"] <= product_value["max_output_tokens"]
                        and 0 < metrics["kv_tokens"] <= product_value["engine_max_num_tokens"]
                        and metrics["kv_tokens"]
                        <= metrics["prefill_tokens"] + metrics["decode_tokens"] + 16
                    )
                    p8.append({
                        "id": entry["id"],
                        "wall_ms": wall_ms,
                        "terminal": terminal.get("type"),
                        "response_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
                        "prior_marker_leaked": leaked,
                        "current_marker_present_once": current_marker_present,
                        "current_trap_absent": current_trap_absent,
                        "prefill_tokens": metrics.get("prefill_tokens"),
                        "decode_tokens": metrics.get("decode_tokens"),
                        "kv_tokens": metrics.get("kv_tokens"),
                        "kv_is_single_turn": kv_valid,
                    })
                    prior_markers.extend([entry["nonce"], entry["trap"]])
                result["cleanup"]["p8"] = close_child(active, validator)
                active = None
            except OBSERVATION_ERRORS as error:
                p8_error = type(error).__name__
                result["cleanup"]["p8_forced"] = stop(active)
                active = None
            result["executed_results"]["P8"] = (
                "INCONCLUSIVE" if p8_error is not None else
                "PASS" if len(p8) == 5
                and all(
                    item["terminal"] == "RESULT"
                    and not item["prior_marker_leaked"]
                    and item["current_marker_present_once"]
                    and item["current_trap_absent"]
                    and item["kv_is_single_turn"]
                    for item in p8
                )
                else "FAIL"
            )
            result["samples"]["p8"] = {
                "ready_ms": p8_ready_ms, "cases": p8, "error_type": p8_error,
            }

        p5_stderr = raw_dir / "p5.stderr"
        terminal: dict[str, Any] = {"type": "NO_TERMINAL", "code": "PROTOCOL_FAILURE"}
        pong: dict[str, Any] = {}
        health: dict[str, Any] = {}
        health_ms: float | None = None
        p5_observation_error: str | None = None
        p5_candidate_error: str | None = None
        p5_same_cleanup: dict[str, Any] = {}
        with p5_stderr.open("w", encoding="utf-8") as stderr:
            active, p5_ready_ms = start_p5(
                config=p5_config,
                config_sha256=candidate["p5_config"]["sha256"],
                config_value=observed_p5_value,
                config_schema=p5_schema,
                protocol_schema=protocol,
                prompt_schema=prompt_schema,
                response_schema=response_schema,
                receipt=args.artifact_receipt,
                receipt_schema=receipt_schema,
                install_root=install_root,
                validator=validator,
                stderr=stderr,
            )
            operation_started = time.monotonic()
            try:
                terminal, elapsed_ms = scored_generate(
                    active,
                    validator,
                    "p5-continuous",
                    p5_fixture["input"],
                    timeout_s=17.5,
                )
                pong = scored_pong(active, validator)
                health, health_ms = scored_generate(
                    active, validator, "p5-same-child-health", STANDARD_INPUT
                )
                p5_same_cleanup = scored_close_child(active, validator)
                active = None
            except CandidateViolation as error:
                elapsed_ms = round((time.monotonic() - operation_started) * 1000, 3)
                p5_candidate_error = type(error.__cause__).__name__
                p5_same_cleanup = stop(active)
                active = None
            except (
                OSError,
                subprocess.SubprocessError,
                KeyError,
                TypeError,
                ValueError,
            ) as error:
                elapsed_ms = round((time.monotonic() - operation_started) * 1000, 3)
                p5_observation_error = type(error).__name__
                p5_same_cleanup = stop(active)
                active = None
        marker_text = p5_stderr.read_text(encoding="utf-8")
        marker_counts = {
            "chunk_started": marker_text.count("P5_EVENT chunk_started"),
            "chunk_completed": marker_text.count("P5_EVENT chunk_completed"),
            "native_cancel_once": marker_text.count("P5_EVENT native_cancel_once"),
            "native_cancel_failed": marker_text.count("P5_EVENT native_cancel_failed"),
            "timeout_between_chunks": marker_text.count("P5_EVENT timeout_between_chunks"),
            "continuous_terminal_cancelled": marker_text.count("P5_EVENT continuous_terminal_cancelled"),
            "conversation_discarded": marker_text.count("P5_EVENT conversation_discarded"),
        }
        active_markers_ok = (
            marker_counts["chunk_started"] >= 1
            and marker_counts["chunk_started"] > marker_counts["chunk_completed"]
            and marker_counts["native_cancel_once"] == 1
            and marker_counts["native_cancel_failed"] == 0
            and marker_counts["timeout_between_chunks"] == 0
        )
        boundary_markers_ok = (
            marker_counts["chunk_completed"] >= 1
            and marker_counts["chunk_started"] == marker_counts["chunk_completed"]
            and marker_counts["native_cancel_once"] == 0
            and marker_counts["native_cancel_failed"] == 0
            and marker_counts["timeout_between_chunks"] == 1
        )
        timeout_mode = (
            "ACTIVE_CHUNK_CANCEL" if active_markers_ok else
            "BETWEEN_CHUNKS_STOP" if boundary_markers_ok else "INVALID"
        )
        markers_ok = (
            (active_markers_ok or boundary_markers_ok)
            and marker_counts["continuous_terminal_cancelled"] == 1
            and marker_counts["conversation_discarded"] >= marker_counts["chunk_started"]
        )
        health_ok = pong.get("type") == "PONG" and health.get("type") == "RESULT"

        rebuild_stderr = raw_dir / "p5-rebuild.stderr"
        rebuild_terminal: dict[str, Any] = {"type": "NO_TERMINAL"}
        rebuild_ready_ms: float | None = None
        rebuild_health_ms: float | None = None
        rebuild_error: str | None = None
        rebuild_candidate_error: str | None = None
        rebuild_cleanup: dict[str, Any] = {}
        with rebuild_stderr.open("w", encoding="utf-8") as stderr:
            try:
                active, rebuild_ready_ms = start_child(**common, stderr=stderr)
                rebuild_terminal, rebuild_health_ms = scored_generate(
                    active, validator, "p5-rebuild-health", STANDARD_INPUT
                )
                rebuild_cleanup = scored_close_child(active, validator)
                active = None
            except CandidateViolation as error:
                rebuild_candidate_error = type(error.__cause__).__name__
                rebuild_cleanup = stop(active)
                active = None
            except (
                PiPacketFailure,
                OSError,
                subprocess.SubprocessError,
                KeyError,
                TypeError,
                ValueError,
            ) as error:
                rebuild_error = type(error).__name__
                rebuild_cleanup = stop(active)
                active = None
        rebuild_ok = rebuild_terminal.get("type") == "RESULT"
        result["executed_results"]["P5"] = p5_runner_disposition(
            terminal,
            elapsed_ms,
            markers_ok=markers_ok,
            health_ok=health_ok,
            rebuild_ok=rebuild_ok,
            candidate_error=p5_candidate_error,
            observation_error=p5_observation_error,
            rebuild_candidate_error=rebuild_candidate_error,
            rebuild_observation_error=rebuild_error,
        )
        result["samples"]["p5"] = {
            "ready_ms": p5_ready_ms,
            "terminal": terminal.get("type"),
            "code": terminal.get("code"),
            "elapsed_ms": elapsed_ms,
            "observation_error_type": p5_observation_error,
            "candidate_error_type": p5_candidate_error,
            "timeout_mode": timeout_mode,
            "marker_counts": marker_counts,
            "same_child_pong": pong.get("type"),
            "same_child_health_terminal": health.get("type"),
            "same_child_health_ms": health_ms,
            "rebuild_ready_ms": rebuild_ready_ms,
            "rebuild_health_terminal": rebuild_terminal.get("type"),
            "rebuild_health_ms": rebuild_health_ms,
            "rebuild_error_type": rebuild_error,
            "rebuild_candidate_error_type": rebuild_candidate_error,
        }
        result["cleanup"]["p5_same_child"] = p5_same_cleanup
        result["cleanup"]["p5_rebuild"] = rebuild_cleanup

        hygiene = scan_owned_logs(raw_dir, runtime_log_markers)
        result["samples"]["log_hygiene"] = hygiene
        if not hygiene["passed"]:
            result["violations"].append("CandidateViolation: owned log hygiene")
            result["executed_results"]["P3"] = "FAIL"
        verify_model_receipt(
            receipt["model"], Path(config_value["model_path"]), config_value["model_sha256"]
        )
        result["artifact_authentication"]["metadata_unchanged"] = True
        result["environment_post"] = target_preflight(args.execution_sha)

        values = result["executed_results"]
        if any(values[item] == "FAIL" for item in EXECUTED_ITEMS):
            result["gate2a_scope_result"] = "FAIL"
        elif any(values[item] in {"INCONCLUSIVE", "Blocked"} for item in EXECUTED_ITEMS):
            result["gate2a_scope_result"] = "INCONCLUSIVE"
        elif values["P4"] == "Core threshold decision required":
            result["gate2a_scope_result"] = "Core threshold decision required"
        else:
            result["gate2a_scope_result"] = "PASS"
        if result["gate2a_scope_result"] == "PASS":
            result["provisional_eligibility"] = (
                "ELIGIBLE_FOR_USER_REVIEW"
                if args.candidate_id == CANDIDATES[0]
                else "WORKAROUND_DISPOSITION_REQUIRED"
            )
        elif result["gate2a_scope_result"] == "Core threshold decision required":
            result["provisional_eligibility"] = "PENDING"
        else:
            result["provisional_eligibility"] = "NOT_ELIGIBLE"
        result["result"] = result["gate2a_scope_result"]
        verify_gate2a_result(
            result, catalog, p8_fixture,
            engine_capacity=product_value["engine_max_num_tokens"],
            max_output_tokens=product_value["max_output_tokens"],
        )
    except (
        PiPacketFailure,
        OSError,
        subprocess.SubprocessError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        evidence = sanitized_error(error)
        result["violations"].append(f"{evidence['category']}: {evidence['error_type']}")
        result["gate2a_scope_result"] = "INCONCLUSIVE"
        result["provisional_eligibility"] = "PENDING"
        result["result"] = "INCONCLUSIVE"
    finally:
        forced_cleanup = stop(active)
        if active is not None:
            result["cleanup"]["forced"] = forced_cleanup
        if owns_install_root and install_root.exists():
            shutil.rmtree(install_root)
        if owns_raw_dir and raw_dir.exists():
            if result_schema is not None:
                errors = list(Draft202012Validator(load(result_schema)).iter_errors(result))
                if errors:
                    result["violations"].append("Gate 2A result schema validation failed")
                    result["gate2a_scope_result"] = "INCONCLUSIVE"
                    result["provisional_eligibility"] = "PENDING"
                    result["result"] = "INCONCLUSIVE"
            try:
                write_json_evidence(raw_dir / "gate2a-sanitized.json", result)
            except EvidenceInvalid as error:
                evidence = sanitized_error(error)
                result["violations"].append(
                    f"{evidence['category']}: {evidence['error_type']}"
                )
                result["gate2a_scope_result"] = "INCONCLUSIVE"
                result["provisional_eligibility"] = "PENDING"
                result["result"] = "INCONCLUSIVE"
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if result["result"] == "PASS":
        return 0
    if result["result"] == "FAIL":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
