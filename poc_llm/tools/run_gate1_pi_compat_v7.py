#!/usr/bin/env python3
"""Run cumulative Gate 1 P1/P6/P7/P10A/P11/P12 on an authorized Pi 5."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.pi_artifact_auth import (
    authenticate_model,
    streaming_digest,
    verify_model_receipt,
)
from poc_llm.harness.pi_runtime import (
    PiPacketFailure,
    load,
    meminfo,
    protocol_validator,
    read_frame,
    send,
    stop,
    target_preflight,
)
from poc_llm.harness.pi_runtime_v2 import (
    launch_authenticated,
    native_library_preflight_v2,
    require_ready_v2,
)


PACKET_ID = "G1-PI-COMPAT-007"
PLATFORM = "pi-debian13-aarch64"
FORBIDDEN_LOG = (
    "raw model output:",
    "BEGIN PRIVATE PROMPT",
    "SECRET_PAYLOAD",
    "credential=",
    "api_key=",
    "hidden context:",
    "LEAK_MARKER",
)


class CandidateEvidenceInconclusive(RuntimeError):
    """The candidate was not disproven because required evidence was unavailable."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fatal-outcome-self-test", action="store_true")
    parser.add_argument("--packet-lock", type=Path, required=True)
    parser.add_argument("--candidate-set", type=Path, required=True)
    parser.add_argument("--execution-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    return parser.parse_args()


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


def ols_slope(values: list[float]) -> float:
    if len(values) < 2:
        raise PiPacketFailure("insufficient slope samples")
    mean_x = (len(values) - 1) / 2
    mean_y = sum(values) / len(values)
    denominator = sum((index - mean_x) ** 2 for index in range(len(values)))
    return sum(
        (index - mean_x) * (value - mean_y)
        for index, value in enumerate(values)
    ) / denominator


def evaluate_p10a(sessions: list[dict[str, Any]]) -> tuple[bool, dict[str, float]]:
    if len(sessions) != 20:
        raise PiPacketFailure("P10A requires exactly 20 sessions")
    pss = [item["resources"]["pss_mib"] for item in sessions]
    used = [item["resources"]["system_used_mib"] for item in sessions]
    calculations = {
        "pss_slope_mib_per_session": round(ols_slope(pss[5:]), 6),
        "system_used_slope_mib_per_session": round(ols_slope(used[5:]), 6),
        "pss_late_early_median_delta_mib": round(
            statistics.median(pss[15:]) - statistics.median(pss[:5]), 3
        ),
        "system_used_late_early_median_delta_mib": round(
            statistics.median(used[15:]) - statistics.median(used[:5]), 3
        ),
    }
    resources_valid = all(
        item["resources"]["process_count"] >= 1
        and item["resources"]["rss_mib"] > 0
        and item["resources"]["pss_mib"] > 0
        and item["resources"]["threads"] > 0
        and item["resources"]["cpu_ticks"] > 0
        and item["resources"]["mem_available_mib"] > 0
        for item in sessions
    )
    thermal_valid = all(
        item["thermal"]["temperature_c"] < 80
        and item["thermal"]["throttled"] == "0x0"
        for item in sessions
    )
    passed = (
        calculations["pss_slope_mib_per_session"] <= 4.0
        and calculations["system_used_slope_mib_per_session"] <= 4.0
        and calculations["pss_late_early_median_delta_mib"] <= 64.0
        and calculations["system_used_late_early_median_delta_mib"] <= 64.0
        and resources_valid
        and thermal_valid
    )
    return passed, calculations


def session_metrics_valid(metrics: dict[str, Any], engine_capacity: int) -> bool:
    """Validate native metrics without confusing serialized input with rendered KV use."""
    prefill = metrics.get("prefill_tokens")
    decode = metrics.get("decode_tokens")
    kv_tokens = metrics.get("kv_tokens")
    return bool(
        isinstance(prefill, int)
        and not isinstance(prefill, bool)
        and prefill > 0
        and isinstance(decode, int)
        and not isinstance(decode, bool)
        and 0 <= decode <= 16
        and isinstance(kv_tokens, int)
        and not isinstance(kv_tokens, bool)
        and 0 < kv_tokens <= engine_capacity
    )


def _process_group_pids(group_id: int) -> list[int]:
    members: list[int] = []
    for stat_path in Path("/proc").glob("[0-9]*/stat"):
        try:
            value = stat_path.read_text(encoding="utf-8")
            tail = value[value.rfind(")") + 2 :].split()
            if int(tail[2]) == group_id:
                members.append(int(stat_path.parent.name))
        except (OSError, ValueError, IndexError):
            continue
    return sorted(members)


def _process_values(pid: int) -> dict[str, float]:
    status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    fields = {
        line.split(":", 1)[0]: line.split()[1]
        for line in status.splitlines()
        if ":" in line and len(line.split()) >= 2
    }
    pss_kib = 0
    rollup = Path(f"/proc/{pid}/smaps_rollup")
    if rollup.is_file():
        for line in rollup.read_text(encoding="utf-8").splitlines():
            if line.startswith("Pss:"):
                pss_kib = int(line.split()[1])
                break
    value = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    tail = value[value.rfind(")") + 2 :].split()
    return {
        "rss_mib": int(fields.get("VmRSS", "0")) / 1024,
        "pss_mib": pss_kib / 1024,
        "threads": float(fields.get("Threads", "0")),
        "cpu_ticks": float(int(tail[11]) + int(tail[12])),
    }


def group_resource_sample(group_id: int) -> dict[str, float]:
    rss = pss = threads = cpu_ticks = 0.0
    pids = _process_group_pids(group_id)
    for pid in pids:
        try:
            values = _process_values(pid)
        except (OSError, ValueError, IndexError):
            continue
        rss += values["rss_mib"]
        pss += values["pss_mib"]
        threads += values["threads"]
        cpu_ticks += values["cpu_ticks"]
    memory = meminfo()
    return {
        "process_count": float(len(pids)),
        "rss_mib": round(rss, 3),
        "pss_mib": round(pss, 3),
        "threads": threads,
        "cpu_ticks": cpu_ticks,
        "mem_total_mib": round(memory["MemTotal"] / (1024 * 1024), 3),
        "mem_available_mib": round(memory["MemAvailable"] / (1024 * 1024), 3),
        "system_used_mib": round(
            (memory["MemTotal"] - memory["MemAvailable"]) / (1024 * 1024), 3
        ),
    }


def thermal_sample() -> dict[str, Any]:
    temperature = subprocess.run(
        ["vcgencmd", "measure_temp"], text=True, capture_output=True, check=False,
    )
    throttled = subprocess.run(
        ["vcgencmd", "get_throttled"], text=True, capture_output=True, check=False,
    )
    match = re.fullmatch(r"temp=([0-9]+(?:\.[0-9]+)?)'C\s*", temperature.stdout)
    if (
        temperature.returncode != 0
        or throttled.returncode != 0
        or match is None
        or not throttled.stdout.startswith("throttled=0x")
    ):
        raise PiPacketFailure("Pi thermal/throttling probe failed")
    return {
        "temperature_c": float(match.group(1)),
        "throttled": throttled.stdout.strip().split("=", 1)[1],
    }


def catalog_input(entry: dict[str, Any]) -> dict[str, Any]:
    tools = [
        {
            "name": name,
            "description": "Approved public integration tool.",
            "input_schema": {"type": "object"},
        }
        for name in entry["tools"]
    ]
    return {
        "perceptions": [{"kind": "read", "status": "ok", "text": entry["text"]}],
        "pending_message_count": 0,
        "capabilities": {
            "perceptions": ["listen", "read", "look"],
            "actions": entry["actions"],
            "tools": tools,
        },
    }


def start_child(
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
    stderr: Any,
) -> tuple[subprocess.Popen[str], float]:
    started = time.monotonic()
    process = launch_authenticated(
        config=config,
        config_sha256=config_sha256,
        config_schema=config_schema,
        protocol_schema=protocol_schema,
        prompt_schema=prompt_schema,
        response_schema=response_schema,
        artifact_receipt=receipt,
        artifact_receipt_schema=receipt_schema,
        install_root=install_root,
        stderr=stderr,
    )
    try:
        require_ready_v2(process, validator, config_value, config_sha256)
    except Exception:
        stop(process)
        raise
    return process, round((time.monotonic() - started) * 1000, 3)


def close_child(
    process: subprocess.Popen[str], validator: Draft202012Validator
) -> dict[str, Any]:
    if process.stdout is None:
        raise PiPacketFailure("candidate stdout unavailable")
    send(process, {"type": "SHUTDOWN", "protocol_version": "snowboard.llm/1"})
    if read_frame(process.stdout, 2.0, validator).get("type") != "SHUTDOWN_ACK":
        raise PiPacketFailure("SHUTDOWN acknowledgement missing")
    process.wait(timeout=2.0)
    cleanup = stop(process)
    expected = {
        "exit_code": 0,
        "waited": True,
        "term_sent": False,
        "kill_sent": False,
        "process_group_absent": True,
    }
    if cleanup != expected:
        raise PiPacketFailure("clean child shutdown proof failed")
    return cleanup


def generate(
    process: subprocess.Popen[str],
    validator: Draft202012Validator,
    request_id: str,
    value: dict[str, Any],
    timeout_s: float = 15.0,
) -> tuple[dict[str, Any], float]:
    if process.stdout is None:
        raise PiPacketFailure("candidate stdout unavailable")
    started = time.monotonic()
    send(
        process,
        {
            "type": "GENERATE",
            "protocol_version": "snowboard.llm/1",
            "request_id": request_id,
            "input": value,
        },
    )
    terminal = read_frame(process.stdout, timeout_s, validator)
    return terminal, round((time.monotonic() - started) * 1000, 3)


def observe_generation_threads(
    process: subprocess.Popen[str], baseline: float
) -> float | None:
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        threads = group_resource_sample(process.pid)["threads"]
        if threads > baseline:
            return threads
        time.sleep(0.01)
    return None


def wait_generation_threads_settle(
    process: subprocess.Popen[str]
) -> float:
    deadline = time.monotonic() + 1.0
    latest: float | None = None
    stable_reads = 0
    while time.monotonic() < deadline:
        current = group_resource_sample(process.pid)["threads"]
        if current == latest:
            stable_reads += 1
        else:
            latest = current
            stable_reads = 1
        if stable_reads >= 5:
            return current
        time.sleep(0.01)
    raise PiPacketFailure("generation threads did not settle before P7 probe")


def empty_candidate(candidate_id: str) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "p_results": {
            name: "Blocked" for name in ("P1", "P6", "P7", "P10A", "P11", "P12")
        },
        "artifact_authentication": {},
        "normal_lifecycle": {},
        "stability": {},
        "cancel": {},
        "recovery": {},
        "violations": [],
        "result": "INCONCLUSIVE",
    }


def p12_disposition(report: dict[str, Any]) -> str:
    """Credit offline inference only after the normal inference lifecycle completed."""
    return "PASS" if report["p_results"]["P1"] == "PASS" else "Blocked"


def main() -> int:
    if sys.argv[1:] == ["--fatal-outcome-self-test"]:
        return 4
    args = parse_args()
    if args.fatal_outcome_self_test:
        return 4
    started = time.monotonic()
    raw_dir = args.evidence_root / args.run_id
    install_root = Path(f"/tmp/llm-poc-g1-pi-007/install-{args.run_id}")
    aggregate: dict[str, Any] = {
        "packet_id": PACKET_ID,
        "run_id": args.run_id,
        "execution_sha": args.execution_sha,
        "execution_surface_sha256": "",
        "core_acceptance": "PENDING",
        "gate2_credit_scope": ["P1", "P6", "P7", "P10A", "P11", "P12"],
        "environment": {},
        "environment_post": {},
        "runtime": {},
        "candidates": [],
        "proposed_finalists": [],
        "violations": [],
        "result": "INCONCLUSIVE",
    }
    active_process: subprocess.Popen[str] | None = None
    try:
        if raw_dir.exists() or install_root.exists():
            raise PiPacketFailure("run-owned evidence or install path is dirty")
        lock = load(args.packet_lock)
        if lock.get("packet_id") != PACKET_ID:
            raise PiPacketFailure("packet lock ID mismatch")
        aggregate["execution_surface_sha256"] = streaming_digest(args.packet_lock)
        for item in lock["artifacts"].values():
            repo_artifact(item)
        if streaming_digest(args.candidate_set) != lock["candidate_set_sha256"]:
            raise PiPacketFailure("candidate set checksum mismatch")
        candidate_set = load(args.candidate_set)
        candidates = candidate_set.get("candidates")
        if (
            candidate_set.get("packet_id") != PACKET_ID
            or not isinstance(candidates, list)
            or [entry["candidate_id"] for entry in candidates] != lock["candidate_order"]
        ):
            raise PiPacketFailure("candidate set/order mismatch")
        aggregate["environment"] = target_preflight(args.execution_sha)
        raw_dir.mkdir(parents=True, exist_ok=False)

        runtime = lock["runtime"]
        wheel = Path(runtime["wheel_path"])
        if not wheel.is_file():
            raise PiPacketFailure("staged runtime wheel missing")
        install = subprocess.run(
            [
                "python3",
                "poc_llm/tools/install_gate1_arm64_wheel_v2.py",
                "--wheel",
                str(wheel),
                "--wheel-sha256",
                runtime["wheel_sha256"],
                "--target",
                str(install_root),
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
            install_result = json.loads(install.stdout)
        except json.JSONDecodeError as exc:
            raise PiPacketFailure("offline installer emitted invalid result") from exc
        if (
            install.returncode != 0
            or install_result.get("result") != "PASS"
            or install_result.get("wheel_sha256") != runtime["wheel_sha256"]
        ):
            raise PiPacketFailure("offline runtime installation failed")
        aggregate["runtime"] = native_library_preflight_v2(
            install_root / "litert_lm/liblitert-lm.so",
            runtime["native_library_sha256"],
        )
        runtime_import = subprocess.run(
            [
                sys.executable,
                "-c",
                "import litert_lm; print(getattr(litert_lm, '__version__', '0.16.0'))",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
            env={
                **os.environ,
                "PYTHONPATH": str(install_root),
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
            },
        )
        (raw_dir / "runtime-import.stdout").write_text(
            runtime_import.stdout, encoding="utf-8"
        )
        (raw_dir / "runtime-import.stderr").write_text(
            runtime_import.stderr, encoding="utf-8"
        )
        if runtime_import.returncode != 0:
            raise PiPacketFailure("installed runtime import failed")
        aggregate["runtime"]["python_import"] = "PASS"

        protocol = repo_artifact(lock["artifacts"]["protocol_schema"])
        config_schema = repo_artifact(lock["artifacts"]["config_schema"])
        prompt_schema = repo_artifact(lock["artifacts"]["prompt_schema"])
        response_schema = repo_artifact(lock["artifacts"]["response_schema"])
        receipt_schema = repo_artifact(lock["artifacts"]["artifact_receipt_schema"])
        result_schema = repo_artifact(lock["artifacts"]["result_schema"])
        abort_fixture = load(repo_artifact(lock["artifacts"]["abort_fixture"]))
        catalog = load(repo_artifact(lock["artifacts"]["catalog"]))
        license_metadata = load(repo_artifact(lock["artifacts"]["license_metadata"]))
        validator = protocol_validator(protocol, prompt_schema, response_schema)

        prepared: dict[str, dict[str, Any]] = {}
        receipt_validator = Draft202012Validator(load(receipt_schema))
        for entry in candidates:
            provenance = license_metadata.get("candidates", {}).get(entry["candidate_id"])
            if (
                not isinstance(provenance, dict)
                or provenance.get("license") != "apache-2.0"
                or not re.fullmatch(r"[0-9a-f]{40}", str(provenance.get("revision", "")))
                or not re.fullmatch(
                    r"[0-9a-f]{64}", str(provenance.get("metadata_sha256", ""))
                )
            ):
                raise PiPacketFailure("candidate license/provenance metadata mismatch")
            config = repo_artifact(entry["standard_config"])
            config_value = load(config)
            if (
                config_value.get("candidate_id") != entry["candidate_id"]
                or config_value.get("platform") != PLATFORM
                or config_value.get("model_sha256") != entry["model_sha256"]
            ):
                raise PiPacketFailure("candidate/config identity mismatch")
            prepared[entry["candidate_id"]] = {
                "entry": entry,
                "config": config,
                "config_value": config_value,
            }

        for entry in candidates:
            candidate_id = entry["candidate_id"]
            report = empty_candidate(candidate_id)
            aggregate["candidates"].append(report)
            record = prepared[candidate_id]
            config = record["config"]
            config_value = record["config_value"]
            stderr_paths = [
                raw_dir / f"{candidate_id}.normal.stderr",
                raw_dir / f"{candidate_id}.fault.stderr",
                raw_dir / f"{candidate_id}.rebuild.stderr",
            ]
            try:
                # Authenticate just in time so each P1 begins from the same receipt-conditioned cache state.
                model_record = authenticate_model(
                    Path(config_value["model_path"]),
                    entry["model_sha256"],
                    entry["model_size_bytes"],
                    timeout_s=120.0,
                )
                receipt = {
                    "receipt_version": "pi-artifact-auth/2",
                    "packet_id": PACKET_ID,
                    "run_id": args.run_id,
                    "execution_sha": args.execution_sha,
                    "execution_surface_sha256": aggregate["execution_surface_sha256"],
                    "candidate_id": candidate_id,
                    "runtime_sha256": runtime["wheel_sha256"],
                    "model": model_record,
                }
                if not receipt_validator.is_valid(receipt):
                    raise PiPacketFailure("artifact receipt schema mismatch")
                receipt_path = raw_dir / f"{candidate_id}.artifact-receipt.json"
                receipt_path.write_text(
                    json.dumps(receipt, sort_keys=True, separators=(",", ":")),
                    encoding="utf-8",
                )
                report["artifact_authentication"] = {
                    "model_sha256": model_record["sha256"],
                    "model_size_bytes": model_record["size_bytes"],
                    "duration_ms": model_record["authentication_duration_ms"],
                    "receipt_sha256": streaming_digest(receipt_path),
                    "full_model_hash_count": 1,
                    "metadata_unchanged": False,
                }
                report["p_results"]["P11"] = "PASS"

                # P1 + P10A share one persistent Engine and one set of 20 sessions.
                with stderr_paths[0].open("w", encoding="utf-8") as stderr:
                    active_process, ready_ms = start_child(
                        config=config,
                        config_sha256=entry["standard_config"]["sha256"],
                        config_value=config_value,
                        config_schema=config_schema,
                        protocol_schema=protocol,
                        prompt_schema=prompt_schema,
                        response_schema=response_schema,
                        receipt=receipt_path,
                        receipt_schema=receipt_schema,
                        install_root=install_root,
                        validator=validator,
                        stderr=stderr,
                    )
                    send(active_process, {"type": "PING", "protocol_version": "snowboard.llm/1"})
                    if (
                        active_process.stdout is None
                        or read_frame(active_process.stdout, 2.0, validator).get("type") != "PONG"
                    ):
                        raise PiPacketFailure("P1 PING/PONG failed")
                    sessions: list[dict[str, Any]] = []
                    for sequence in range(20):
                        catalog_entry = catalog["valid_cases"][
                            sequence % len(catalog["valid_cases"])
                        ]
                        terminal, wall_ms = generate(
                            active_process,
                            validator,
                            f"p10a-{sequence:02d}",
                            catalog_input(catalog_entry),
                        )
                        if terminal.get("type") != "RESULT":
                            raise PiPacketFailure("P10A session did not return RESULT")
                        metrics = terminal.get("metrics", {})
                        if not session_metrics_valid(
                            metrics, config_value["engine_max_num_tokens"]
                        ):
                            raise PiPacketFailure("P10A native token metrics violate the frozen envelope")
                        time.sleep(5.0)
                        resources = group_resource_sample(active_process.pid)
                        thermal = thermal_sample()
                        sessions.append(
                            {
                                "sequence": sequence + 1,
                                "fixture_id": catalog_entry["id"],
                                "terminal": "RESULT",
                                "action_kind": terminal["response"]["action_kind"],
                                "wall_ms": wall_ms,
                                "metrics": metrics,
                                "resources": resources,
                                "thermal": thermal,
                            }
                        )
                    normal_cleanup = close_child(active_process, validator)
                    active_process = None
                p10a_pass, p10a_calculations = evaluate_p10a(sessions)
                report["normal_lifecycle"] = {
                    "ready_ms": ready_ms,
                    "ping_pong": "PASS",
                    "shutdown_cleanup": normal_cleanup,
                }
                report["stability"] = {
                    "sessions_completed": len(sessions),
                    "sessions": sessions,
                    **p10a_calculations,
                    "wall_p50_ms": percentile([item["wall_ms"] for item in sessions], 50),
                    "wall_p95_ms": percentile([item["wall_ms"] for item in sessions], 95),
                }
                report["p_results"]["P1"] = "PASS"
                report["p_results"]["P10A"] = "PASS" if p10a_pass else "FAIL"
                if not p10a_pass:
                    raise PiPacketFailure("P10A stability decision rule failed")

                # P6 observation and P7 force-abort share one fault child.
                with stderr_paths[1].open("w", encoding="utf-8") as stderr:
                    active_process, fault_ready_ms = start_child(
                        config=config,
                        config_sha256=entry["standard_config"]["sha256"],
                        config_value=config_value,
                        config_schema=config_schema,
                        protocol_schema=protocol,
                        prompt_schema=prompt_schema,
                        response_schema=response_schema,
                        receipt=receipt_path,
                        receipt_schema=receipt_schema,
                        install_root=install_root,
                        validator=validator,
                        stderr=stderr,
                    )
                    baseline_threads = group_resource_sample(active_process.pid)["threads"]
                    send(
                        active_process,
                        {
                            "type": "GENERATE",
                            "protocol_version": "snowboard.llm/1",
                            "request_id": "p6-cancel",
                            "input": abort_fixture["input"],
                        },
                    )
                    active_threads = observe_generation_threads(active_process, baseline_threads)
                    cancel_terminal: dict[str, Any] | None = None
                    if active_process.stdout is None:
                        raise CandidateEvidenceInconclusive("P6 stdout unavailable")
                    if active_threads is None:
                        try:
                            cancel_terminal = read_frame(active_process.stdout, 0.1, validator)
                        except PiPacketFailure as exc:
                            if str(exc) != "protocol frame deadline exceeded":
                                raise
                        cancel_ms = 0.0
                    else:
                        cancel_started = time.monotonic()
                        send(
                            active_process,
                            {
                                "type": "CANCEL",
                                "protocol_version": "snowboard.llm/1",
                                "request_id": "p6-cancel",
                            },
                        )
                        try:
                            cancel_terminal = read_frame(active_process.stdout, 0.5, validator)
                        except PiPacketFailure as exc:
                            if str(exc) != "protocol frame deadline exceeded":
                                raise
                        cancel_ms = round((time.monotonic() - cancel_started) * 1000, 3)
                    native_cancel = (
                        active_threads is not None
                        and cancel_terminal is not None
                        and cancel_terminal.get("type") == "CANCELLED"
                        and cancel_terminal.get("request_id") == "p6-cancel"
                        and cancel_ms <= 500.0
                    )
                    report["p_results"]["P6"] = (
                        "PASS" if native_cancel else "Conditional escalation"
                    )
                    report["cancel"] = {
                        "generation_active_observed": active_threads is not None,
                        "baseline_threads": baseline_threads,
                        "active_threads": active_threads,
                        "terminal": (
                            cancel_terminal.get("type") if cancel_terminal is not None else "NONE"
                        ),
                        "elapsed_ms": cancel_ms,
                        "disposition": report["p_results"]["P6"],
                    }
                    if native_cancel:
                        baseline_threads = wait_generation_threads_settle(active_process)
                        send(
                            active_process,
                            {
                                "type": "GENERATE",
                                "protocol_version": "snowboard.llm/1",
                                "request_id": "p7-force",
                                "input": abort_fixture["input"],
                            },
                        )
                        if observe_generation_threads(active_process, baseline_threads) is None:
                            raise CandidateEvidenceInconclusive(
                                "P7 active generation could not be observed"
                            )
                    elif cancel_terminal is not None:
                        baseline_threads = wait_generation_threads_settle(active_process)
                        send(
                            active_process,
                            {
                                "type": "GENERATE",
                                "protocol_version": "snowboard.llm/1",
                                "request_id": "p7-force",
                                "input": abort_fixture["input"],
                            },
                        )
                        if observe_generation_threads(active_process, baseline_threads) is None:
                            raise CandidateEvidenceInconclusive(
                                "P7 active generation could not be observed"
                            )
                    elif active_threads is None:
                        raise CandidateEvidenceInconclusive(
                            "P6 neither active generation nor terminal was observed"
                        )
                    force_cleanup = stop(active_process)
                    active_process = None
                    if (
                        not force_cleanup.get("term_sent")
                        or not force_cleanup.get("waited")
                        or not force_cleanup.get("process_group_absent")
                    ):
                        raise PiPacketFailure("P7 Level 2 cleanup failed")

                with stderr_paths[2].open("w", encoding="utf-8") as stderr:
                    active_process, rebuild_ready_ms = start_child(
                        config=config,
                        config_sha256=entry["standard_config"]["sha256"],
                        config_value=config_value,
                        config_schema=config_schema,
                        protocol_schema=protocol,
                        prompt_schema=prompt_schema,
                        response_schema=response_schema,
                        receipt=receipt_path,
                        receipt_schema=receipt_schema,
                        install_root=install_root,
                        validator=validator,
                        stderr=stderr,
                    )
                    send(active_process, {"type": "PING", "protocol_version": "snowboard.llm/1"})
                    if (
                        active_process.stdout is None
                        or read_frame(active_process.stdout, 2.0, validator).get("type") != "PONG"
                    ):
                        raise PiPacketFailure("P7 rebuild PING/PONG failed")
                    recovery_terminal, recovery_ms = generate(
                        active_process,
                        validator,
                        "p7-recovery",
                        catalog_input(catalog["valid_cases"][0]),
                    )
                    if recovery_terminal.get("type") != "RESULT":
                        raise PiPacketFailure("P7 recovery generation failed")
                    rebuild_cleanup = close_child(active_process, validator)
                    active_process = None
                fatal = subprocess.run(
                    [sys.executable, str(Path(__file__)), "--fatal-outcome-self-test"],
                    cwd=ROOT,
                    check=False,
                )
                if fatal.returncode != 4:
                    raise PiPacketFailure("P7 fatal outcome mapping failed")
                report["recovery"] = {
                    "fault_ready_ms": fault_ready_ms,
                    "force_abort": force_cleanup,
                    "rebuild_ready_ms": rebuild_ready_ms,
                    "recovery_generation_ms": recovery_ms,
                    "recovery_terminal": "RESULT",
                    "rebuild_cleanup": rebuild_cleanup,
                    "fatal_outcome_exit_code": fatal.returncode,
                }
                report["p_results"]["P7"] = "PASS"

                verify_model_receipt(
                    receipt["model"],
                    Path(config_value["model_path"]),
                    config_value["model_sha256"],
                )
                report["artifact_authentication"]["metadata_unchanged"] = True
                log_text = "".join(
                    path.read_text(encoding="utf-8", errors="replace")
                    for path in stderr_paths
                )
                if any(pattern in log_text for pattern in FORBIDDEN_LOG):
                    raise PiPacketFailure("runner-owned stderr failed log-hygiene scan")
                report["result"] = "PASS"
            except CandidateEvidenceInconclusive as exc:
                report["violations"].append(str(exc))
                report["result"] = "INCONCLUSIVE"
                if active_process is not None:
                    report.setdefault("recovery", {})["exception_cleanup"] = stop(active_process)
                    active_process = None
            except PiPacketFailure as exc:
                report["violations"].append(str(exc))
                report["result"] = "FAIL"
                if (
                    report["p_results"]["P11"] == "PASS"
                    and report["p_results"]["P1"] == "Blocked"
                ):
                    report["p_results"]["P1"] = "FAIL"
                if active_process is not None:
                    report.setdefault("recovery", {})["exception_cleanup"] = stop(active_process)
                    active_process = None
            except (
                OSError,
                subprocess.SubprocessError,
                KeyError,
                ValueError,
            ) as exc:
                report["violations"].append(str(exc))
                report["result"] = "INCONCLUSIVE"
                if active_process is not None:
                    report.setdefault("recovery", {})["exception_cleanup"] = stop(active_process)
                    active_process = None

        aggregate["environment_post"] = target_preflight(args.execution_sha)
        for report in aggregate["candidates"]:
            report["p_results"]["P12"] = p12_disposition(report)
            if report["result"] == "PASS":
                aggregate["proposed_finalists"].append(report["candidate_id"])
        if any(report["result"] == "INCONCLUSIVE" for report in aggregate["candidates"]):
            aggregate["result"] = "INCONCLUSIVE"
        else:
            aggregate["result"] = "PASS" if aggregate["proposed_finalists"] else "FAIL"
        if not Draft202012Validator(load(result_schema)).is_valid(aggregate):
            raise PiPacketFailure("Gate 1 v7 aggregate result schema mismatch")
    except (
        PiPacketFailure,
        OSError,
        subprocess.SubprocessError,
        KeyError,
        ValueError,
    ) as exc:
        aggregate["violations"].append(str(exc))
        aggregate["result"] = "INCONCLUSIVE"
        if active_process is not None:
            stop(active_process)
    finally:
        aggregate["elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)
        if install_root.exists():
            shutil.rmtree(install_root)
        if raw_dir.exists():
            (raw_dir / "gate1-pi-v7-sanitized.json").write_text(
                json.dumps(aggregate, sort_keys=True), encoding="utf-8"
            )
        print(json.dumps(aggregate, sort_keys=True, separators=(",", ":")))
    return 0 if aggregate["result"] == "PASS" else 1 if aggregate["result"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
