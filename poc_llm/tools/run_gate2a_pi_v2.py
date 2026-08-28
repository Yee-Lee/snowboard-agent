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


def scan_owned_logs(raw_dir: Path) -> list[str]:
    violations: list[str] = []
    for path in sorted(raw_dir.iterdir()):
        if not path.is_file() or path.name == "gate2a-sanitized.json":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(marker in text for marker in FORBIDDEN_LOG):
            violations.append(f"owned log hygiene failure: {path.name}")
    return violations


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
        result["isolation"] = isolation_state(args.max_prelaunch_uptime_s)
        result["isolation"]["prior_receipts_checked"] = enforce_isolation(
            args.evidence_root, result["isolation"], args.candidate_id
        )
        result["environment"] = target_preflight(args.execution_sha)
        raw_dir.mkdir(parents=True, exist_ok=False)
        owns_raw_dir = True

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
            "config_value": config_value,
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
            "config_value": product_value,
            "config_schema": product_schema,
        }

        standard_stderr = raw_dir / "standard.stderr"
        with standard_stderr.open("w", encoding="utf-8") as stderr:
            cold: list[dict[str, Any]] = []
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
                            "terminal": terminal.get("type"),
                            "code": terminal.get("code"),
                        })
                    close_child(active, validator)
                    active = None
                except OBSERVATION_ERRORS as error:
                    p4_failures.append({
                        "phase": "cold", "index": index,
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
                "PASS"
                if p2_error is None and len(p2) == 30 and all(item["valid"] for item in p2)
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
                            "terminal": terminal.get("type"),
                            "code": terminal.get("code"),
                        })
                result["cleanup"]["standard"] = close_child(active, validator)
                active = None
            except OBSERVATION_ERRORS as error:
                p4_failures.append({
                    "phase": "resident", "error_type": type(error).__name__,
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
            if not method_complete or not p4_environment_ok:
                result["executed_results"]["P4"] = "FAIL"
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
                "PASS"
                if p8_error is None and len(p8) == 5
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
        p5_same_cleanup: dict[str, Any] = {}
        with p5_stderr.open("w", encoding="utf-8") as stderr:
            active, p5_ready_ms = start_p5(
                config=p5_config,
                config_sha256=candidate["p5_config"]["sha256"],
                config_value=p5_value,
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
                terminal, elapsed_ms = generate(
                    active,
                    validator,
                    "p5-continuous",
                    p5_fixture["input"],
                    timeout_s=17.5,
                )
                send(active, {"type": "PING", "protocol_version": "snowboard.llm/1"})
                if active.stdout is None:
                    raise PiPacketFailure("P5 child stdout unavailable")
                pong = read_frame(active.stdout, 2.0, validator)
                health, health_ms = generate(
                    active, validator, "p5-same-child-health", STANDARD_INPUT
                )
                p5_same_cleanup = close_child(active, validator)
                active = None
            except (
                PiPacketFailure,
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
            "continuous_terminal_cancelled": marker_text.count("P5_EVENT continuous_terminal_cancelled"),
            "conversation_discarded": marker_text.count("P5_EVENT conversation_discarded"),
        }
        markers_ok = (
            marker_counts["chunk_started"] >= 1
            and marker_counts["chunk_started"] > marker_counts["chunk_completed"]
            and marker_counts["native_cancel_once"] == 1
            and marker_counts["continuous_terminal_cancelled"] == 1
            and marker_counts["conversation_discarded"] >= marker_counts["chunk_started"]
        )
        health_ok = pong.get("type") == "PONG" and health.get("type") == "RESULT"

        rebuild_stderr = raw_dir / "p5-rebuild.stderr"
        rebuild_terminal: dict[str, Any] = {"type": "NO_TERMINAL"}
        rebuild_ready_ms: float | None = None
        rebuild_health_ms: float | None = None
        rebuild_error: str | None = None
        rebuild_cleanup: dict[str, Any] = {}
        with rebuild_stderr.open("w", encoding="utf-8") as stderr:
            try:
                active, rebuild_ready_ms = start_child(**common, stderr=stderr)
                rebuild_terminal, rebuild_health_ms = generate(
                    active, validator, "p5-rebuild-health", STANDARD_INPUT
                )
                rebuild_cleanup = close_child(active, validator)
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
        result["executed_results"]["P5"] = p5_result_disposition(
            terminal,
            elapsed_ms,
            markers_ok=markers_ok,
            health_ok=health_ok,
            rebuild_ok=rebuild_ok,
        )
        result["samples"]["p5"] = {
            "ready_ms": p5_ready_ms,
            "terminal": terminal.get("type"),
            "code": terminal.get("code"),
            "elapsed_ms": elapsed_ms,
            "observation_error_type": p5_observation_error,
            "marker_counts": marker_counts,
            "same_child_pong": pong.get("type"),
            "same_child_health_terminal": health.get("type"),
            "same_child_health_ms": health_ms,
            "rebuild_ready_ms": rebuild_ready_ms,
            "rebuild_health_terminal": rebuild_terminal.get("type"),
            "rebuild_health_ms": rebuild_health_ms,
            "rebuild_error_type": rebuild_error,
        }
        result["cleanup"]["p5_same_child"] = p5_same_cleanup
        result["cleanup"]["p5_rebuild"] = rebuild_cleanup

        hygiene = scan_owned_logs(raw_dir)
        result["violations"].extend(hygiene)
        if hygiene:
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
    except (
        PiPacketFailure,
        OSError,
        subprocess.SubprocessError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        result["violations"].append(str(error))
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
            (raw_dir / "gate2a-sanitized.json").write_text(
                json.dumps(result, sort_keys=True), encoding="utf-8"
            )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if result["result"] == "PASS":
        return 0
    if result["result"] == "FAIL":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
