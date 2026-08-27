#!/usr/bin/env python3
"""Run one reboot-isolated P6.1 or P7.1 replacement observation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, TextIO

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
from poc_llm.tools.run_gate1_pi_compat_v7 import (
    catalog_input,
    close_child,
    generate,
    group_resource_sample,
    observe_generation_threads,
    start_child,
)
PACKET_ID = "G1-P6.1-P7.1-001"
BASE_PACKET_ID = "G1-PI-COMPAT-007"
CANDIDATES = {
    "CAND-LRT-G4E2B-MOBILE-R1": 1024,
    "CAND-LRT-Q25-15B-Q8-R1": 512,
}
PLATFORM = "pi-debian13-aarch64"


def repo_artifact(item: dict[str, str]) -> Path:
    path = (ROOT / item["path"]).resolve()
    if not path.is_file() or streaming_digest(path) != item["sha256"]:
        raise PiPacketFailure(f"locked repository artifact mismatch: {item['path']}")
    return path


def isolation_state(
    proc_root: Path = Path("/proc"), *, max_uptime_s: float = 900.0
) -> dict[str, Any]:
    uptime_s = float((proc_root / "uptime").read_text(encoding="ascii").split()[0])
    if uptime_s > max_uptime_s:
        raise PiPacketFailure("P6.1/P7.1 reboot-age isolation bound exceeded")
    boot_id = (proc_root / "sys/kernel/random/boot_id").read_text(
        encoding="ascii"
    ).strip()
    if not boot_id:
        raise PiPacketFailure("P6.1/P7.1 boot identity unavailable")
    adapter_names = (
        b"litert_lm_pi_child_adapter",
        b"litert_lm_pi_async_child_adapter",
    )
    adapter_processes = 0
    for command_path in proc_root.glob("[0-9]*/cmdline"):
        try:
            command = command_path.read_bytes().replace(b"\0", b" ")
        except OSError:
            continue
        if any(name in command for name in adapter_names):
            adapter_processes += 1
    if adapter_processes:
        raise PiPacketFailure("pre-existing LiteRT-LM adapter process detected")
    return {
        "boot_id_sha256": hashlib.sha256(boot_id.encode("ascii")).hexdigest(),
        "prelaunch_uptime_s": round(uptime_s, 3),
        "preexisting_adapter_processes": 0,
        "prior_candidate_workloads_in_run": 0,
    }


def enforce_suite_isolation(
    evidence_root: Path,
    current: dict[str, Any],
    *,
    candidate_id: str,
    test_id: str,
    execution_sha: str,
    execution_surface_sha256: str,
) -> int:
    receipts = sorted(evidence_root.glob("*/p6-1-p7-1-sanitized.json"))
    for path in receipts:
        prior = load(path)
        if (
            prior.get("packet_id") != PACKET_ID
            or prior.get("execution_sha") != execution_sha
            or prior.get("execution_surface_sha256") != execution_surface_sha256
        ):
            raise PiPacketFailure("P6.1/P7.1 evidence root identity contamination")
        prior_isolation = prior.get("isolation", {})
        if prior_isolation.get("boot_id_sha256") == current["boot_id_sha256"]:
            raise PiPacketFailure("P6.1/P7.1 boot ID was already consumed")
        if (
            prior.get("candidate_id") == candidate_id
            and prior.get("test_id") == test_id
        ):
            raise PiPacketFailure("P6.1/P7.1 candidate/test already has a receipt")
    return len(receipts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-lock", type=Path, required=True)
    parser.add_argument("--candidate-set", type=Path, required=True)
    parser.add_argument("--candidate-id", choices=tuple(CANDIDATES), required=True)
    parser.add_argument("--test-id", choices=("P6.1", "P7.1"), required=True)
    parser.add_argument("--execution-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--max-prelaunch-uptime-s", type=float, default=900.0)
    return parser.parse_args()


def async_launch(
    *,
    config: Path,
    config_sha256: str,
    config_schema: Path,
    protocol_schema: Path,
    prompt_schema: Path,
    response_schema: Path,
    artifact_receipt: Path,
    artifact_receipt_schema: Path,
    install_root: Path,
    stderr: TextIO,
) -> subprocess.Popen[str]:
    argv = [
        "env", f"PYTHONPATH={install_root}", "python3",
        "poc_llm/harness/litert_lm_pi_async_child_adapter_v1.py",
        "--config", str(config), "--config-sha256", config_sha256,
        "--config-schema", str(config_schema),
        "--config-schema-sha256", streaming_digest(config_schema),
        "--protocol-schema", str(protocol_schema),
        "--protocol-schema-sha256", streaming_digest(protocol_schema),
        "--prompt-schema", str(prompt_schema),
        "--prompt-schema-sha256", streaming_digest(prompt_schema),
        "--response-schema", str(response_schema),
        "--response-schema-sha256", streaming_digest(response_schema),
        "--artifact-receipt", str(artifact_receipt),
        "--artifact-receipt-sha256", streaming_digest(artifact_receipt),
        "--artifact-receipt-schema", str(artifact_receipt_schema),
        "--artifact-receipt-schema-sha256", streaming_digest(artifact_receipt_schema),
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


def start_async_child(**kwargs: Any) -> tuple[subprocess.Popen[str], float]:
    started = time.monotonic()
    process = async_launch(
        config=kwargs["config"],
        config_sha256=kwargs["config_sha256"],
        config_schema=kwargs["config_schema"],
        protocol_schema=kwargs["protocol_schema"],
        prompt_schema=kwargs["prompt_schema"],
        response_schema=kwargs["response_schema"],
        artifact_receipt=kwargs["receipt"],
        artifact_receipt_schema=kwargs["receipt_schema"],
        install_root=kwargs["install_root"],
        stderr=kwargs["stderr"],
    )
    try:
        require_ready_v2(
            process, kwargs["validator"], kwargs["config_value"], kwargs["config_sha256"]
        )
    except Exception:
        stop(process)
        raise
    return process, round((time.monotonic() - started) * 1000, 3)


def wait_marker(path: Path, marker: str, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            if marker in path.read_text(encoding="utf-8"):
                return True
        except FileNotFoundError:
            pass
        time.sleep(0.01)
    return False


def marker_count(path: Path, marker: str) -> int:
    return path.read_text(encoding="utf-8").count(marker)


def marker_elapsed_ms(
    path: Path, marker: str, started: float, timeout_s: float
) -> float | None:
    if not wait_marker(path, marker, timeout_s):
        return None
    match = re.search(
        re.escape(marker) + r" monotonic_ns=([0-9]+)",
        path.read_text(encoding="utf-8"),
    )
    if match is None:
        return None
    return round((int(match.group(1)) / 1_000_000_000 - started) * 1000, 3)


def expected_ready_identity(config: dict[str, Any], config_sha256: str) -> dict[str, Any]:
    return {
        "candidate_id": config["candidate_id"],
        "pairing_revision": config["pairing_revision"],
        "platform": config["platform"],
        "runtime_sha256": config["runtime_sha256"],
        "model_sha256": config["model_sha256"],
        "config_sha256": config_sha256,
    }


def child_launch_args(common: dict[str, Any]) -> dict[str, Any]:
    """Return only the immutable launch inputs accepted by the v7 child helper."""
    return {
        "config": common["config"],
        "config_sha256": common["config_sha256"],
        "config_value": common["config_value"],
        "config_schema": common["config_schema"],
        "protocol_schema": common["protocol_schema"],
        "prompt_schema": common["prompt_schema"],
        "response_schema": common["response_schema"],
        "receipt": common["receipt"],
        "receipt_schema": common["receipt_schema"],
        "install_root": common["install_root"],
        "validator": common["validator"],
    }


def observed_rebuild(
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
    diagnostic_timeout_s: float,
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
        if process.stdout is None:
            raise PiPacketFailure("P7.1 rebuild stdout unavailable")
        ready = read_frame(process.stdout, diagnostic_timeout_s, validator)
        elapsed_ms = round((time.monotonic() - started) * 1000, 3)
        if (
            ready.get("type") != "READY"
            or ready.get("identity") != expected_ready_identity(config_value, config_sha256)
        ):
            raise PiPacketFailure("P7.1 rebuild READY identity mismatch")
        return process, elapsed_ms
    except Exception:
        stop(process)
        raise


def run_p6_1(
    *,
    common: dict[str, Any],
    result: dict[str, Any],
    stderr_path: Path,
) -> None:
    process: subprocess.Popen[str] | None = None
    try:
        with stderr_path.open("w", encoding="utf-8") as stderr:
            process, ready_ms = start_async_child(**common, stderr=stderr)
            result["prerequisite_ready_ms"] = ready_ms
            send(process, {"type": "PING", "protocol_version": "snowboard.llm/1"})
            if process.stdout is None or read_frame(
                process.stdout, 2.0, common["validator"]
            ).get("type") != "PONG":
                raise PiPacketFailure("P6.1 prerequisite PING/PONG failed")
            send(
                process,
                {
                    "type": "GENERATE",
                    "protocol_version": "snowboard.llm/1",
                    "request_id": "p6-1-cancel",
                    "input": common["abort_fixture"]["input"],
                },
            )
            if not wait_marker(stderr_path, "ADAPTER_P6_1_EVENT first_chunk", 15.0):
                raise PiPacketFailure("P6.1 async stream activity not observed")
            cancel_started = time.monotonic()
            send(
                process,
                {
                    "type": "CANCEL",
                    "protocol_version": "snowboard.llm/1",
                    "request_id": "p6-1-cancel",
                },
            )
            terminal: dict[str, Any] | None = None
            try:
                terminal = read_frame(process.stdout, 0.5, common["validator"])
            except PiPacketFailure as exc:
                if str(exc) != "protocol frame deadline exceeded":
                    raise
            cancel_ms = round((time.monotonic() - cancel_started) * 1000, 3)
            native_cancel_ms = marker_elapsed_ms(
                stderr_path,
                "ADAPTER_P6_1_EVENT native_cancel_once",
                cancel_started,
                1.0,
            )
            native_terminal_ms = marker_elapsed_ms(
                stderr_path,
                "ADAPTER_P6_1_EVENT stream_terminal_cancelled",
                cancel_started,
                1.0,
            )
            result["cancel"] = {
                "async_activity_observed": True,
                "terminal": terminal.get("type") if terminal else "NONE",
                "elapsed_ms": cancel_ms,
                "cancel_request_ms": 0,
                "native_cancel_invoked_ms": native_cancel_ms,
                "native_stream_terminal_ms": native_terminal_ms,
                "native_cancel_count": marker_count(
                    stderr_path, "ADAPTER_P6_1_EVENT native_cancel_once"
                ),
                "cancelled_conversation_discarded": wait_marker(
                    stderr_path, "ADAPTER_P6_1_EVENT conversation_discarded", 1.0
                ),
            }
            if (
                terminal is None
                or terminal.get("type") != "CANCELLED"
                or terminal.get("request_id") != "p6-1-cancel"
                or cancel_ms > 500.0
                or native_cancel_ms is None
                or native_cancel_ms > 500.0
                or native_terminal_ms is None
                or native_terminal_ms > 500.0
                or result["cancel"]["native_cancel_count"] != 1
                or not result["cancel"]["cancelled_conversation_discarded"]
            ):
                result["p_result"] = "FAIL"
                raise PiPacketFailure("P6.1 official async cancellation failed")
            health, health_ms = generate(
                process,
                common["validator"],
                "p6-1-health",
                catalog_input(common["catalog"]["valid_cases"][0]),
            )
            result["cancel"]["same_engine_health_terminal"] = health.get("type")
            result["cancel"]["same_engine_health_ms"] = health_ms
            result["cancel"]["conversation_discard_count"] = marker_count(
                stderr_path, "ADAPTER_P6_1_EVENT conversation_discarded"
            )
            if health.get("type") != "RESULT" or result["cancel"][
                "conversation_discard_count"
            ] != 2:
                result["p_result"] = "FAIL"
                raise PiPacketFailure("P6.1 same-Engine new-Conversation health failed")
            result["final_cleanup"] = close_child(process, common["validator"])
            process = None
            result["p_result"] = "PASS"
    finally:
        if process is not None:
            result["final_cleanup"] = stop(process)


def run_p7_1(
    *,
    common: dict[str, Any],
    result: dict[str, Any],
    fault_stderr_path: Path,
    rebuild_stderr_path: Path,
) -> None:
    process: subprocess.Popen[str] | None = None
    try:
        with fault_stderr_path.open("w", encoding="utf-8") as stderr:
            process, ready_ms = start_child(
                **child_launch_args(common), stderr=stderr
            )
            result["prerequisite_ready_ms"] = ready_ms
            baseline_threads = group_resource_sample(process.pid)["threads"]
            send(
                process,
                {
                    "type": "GENERATE",
                    "protocol_version": "snowboard.llm/1",
                    "request_id": "p7-1-force",
                    "input": common["abort_fixture"]["input"],
                },
            )
            active_threads = observe_generation_threads(process, baseline_threads)
            if active_threads is None:
                raise PiPacketFailure("P7.1 active generation not observed")
            abort_started = time.monotonic()
            force_cleanup = stop(process)
            abort_to_absence_ms = round((time.monotonic() - abort_started) * 1000, 3)
            process = None
            result["recovery"] = {
                "native_cancel_invoked": False,
                "baseline_threads": baseline_threads,
                "active_threads": active_threads,
                "abort_to_absence_ms": abort_to_absence_ms,
                "force_abort": force_cleanup,
                "rebuild_ready_ms": None,
                "ready_sla_ms": 10_000,
                "diagnostic_timeout_ms": 30_000,
                "diagnostic_disposition": "PENDING",
            }
            if (
                not force_cleanup.get("term_sent")
                or not force_cleanup.get("waited")
                or not force_cleanup.get("process_group_absent")
            ):
                result["p_result"] = "FAIL"
                raise PiPacketFailure("P7.1 force-abort cleanup failed")

        with rebuild_stderr_path.open("w", encoding="utf-8") as stderr:
            try:
                process, rebuild_ready_ms = observed_rebuild(
                    **child_launch_args(common),
                    stderr=stderr,
                    diagnostic_timeout_s=30.0,
                )
            except PiPacketFailure as exc:
                if str(exc) == "protocol frame deadline exceeded":
                    result["recovery"]["diagnostic_disposition"] = (
                        "WEDGED_OR_UNBOUNDED"
                    )
                    result["p_result"] = "FAIL"
                    raise PiPacketFailure("P7.1 rebuild exceeded diagnostic bound") from exc
                raise
            result["recovery"]["rebuild_ready_ms"] = rebuild_ready_ms
            result["recovery"]["diagnostic_disposition"] = (
                "WITHIN_SLA" if rebuild_ready_ms <= 10_000 else "SLOW_RECOVERY"
            )
            send(process, {"type": "PING", "protocol_version": "snowboard.llm/1"})
            if process.stdout is None or read_frame(
                process.stdout, 2.0, common["validator"]
            ).get("type") != "PONG":
                raise PiPacketFailure("P7.1 rebuild PING/PONG failed")
            health, health_ms = generate(
                process,
                common["validator"],
                "p7-1-health",
                catalog_input(common["catalog"]["valid_cases"][0]),
            )
            result["recovery"]["health_terminal"] = health.get("type")
            result["recovery"]["health_ms"] = health_ms
            result["final_cleanup"] = close_child(process, common["validator"])
            process = None
            if rebuild_ready_ms > 10_000 or health.get("type") != "RESULT":
                result["p_result"] = "FAIL"
                raise PiPacketFailure("P7.1 product recovery SLA failed")
        fatal = subprocess.run(
            [
                sys.executable,
                str(ROOT / "poc_llm/tools/run_gate1_pi_compat_v7.py"),
                "--fatal-outcome-self-test",
            ],
            cwd=ROOT,
            check=False,
        )
        result["recovery"]["fatal_outcome_exit_code"] = fatal.returncode
        if fatal.returncode != 4:
            raise PiPacketFailure("P7.1 fatal outcome mapping failed")
        result["p_result"] = "PASS"
    finally:
        if process is not None:
            result["final_cleanup"] = stop(process)


def main() -> int:
    args = parse_args()
    started = time.monotonic()
    raw_dir = args.evidence_root / args.run_id
    install_root = Path(f"/tmp/llm-poc-g1-p6-1-p7-1/install-{args.run_id}")
    result: dict[str, Any] = {
        "packet_id": PACKET_ID,
        "base_packet_id": BASE_PACKET_ID,
        "run_id": args.run_id,
        "test_id": args.test_id,
        "candidate_id": args.candidate_id,
        "execution_sha": args.execution_sha,
        "execution_surface_sha256": "",
        "core_acceptance": "PENDING",
        "isolation": {},
        "environment": {},
        "environment_post": {},
        "runtime": {},
        "artifact_authentication": {},
        "prerequisite_ready_ms": None,
        "cancel": {},
        "recovery": {},
        "final_cleanup": {},
        "p_result": "INCONCLUSIVE",
        "violations": [],
        "result": "INCONCLUSIVE",
    }
    result_schema: Path | None = None
    config_value: dict[str, Any] | None = None
    receipt: dict[str, Any] | None = None
    try:
        if raw_dir.exists() or install_root.exists():
            raise PiPacketFailure("P6.1/P7.1 evidence or install path is dirty")
        lock = load(args.packet_lock)
        if (
            lock.get("packet_id") != PACKET_ID
            or lock.get("base_packet_id") != BASE_PACKET_ID
            or lock.get("candidate_order") != list(CANDIDATES)
            or lock.get("thresholds")
            != {
                "cancel_ms": 500,
                "rebuild_ready_ms": 10_000,
                "rebuild_diagnostic_ms": 30_000,
            }
        ):
            raise PiPacketFailure("P6.1/P7.1 lock identity mismatch")
        result["execution_surface_sha256"] = streaming_digest(args.packet_lock)
        for item in lock["artifacts"].values():
            repo_artifact(item)
        if streaming_digest(args.candidate_set) != lock["candidate_set_sha256"]:
            raise PiPacketFailure("P6.1/P7.1 candidate set checksum mismatch")
        candidate_set = load(args.candidate_set)
        if candidate_set.get("packet_id") != BASE_PACKET_ID:
            raise PiPacketFailure("P6.1/P7.1 candidate set packet mismatch")
        entries = {
            item.get("candidate_id"): item for item in candidate_set.get("candidates", [])
        }
        if list(entries) != list(CANDIDATES) or args.candidate_id not in entries:
            raise PiPacketFailure("P6.1/P7.1 frozen candidate identity mismatch")
        entry = entries[args.candidate_id]
        result["isolation"] = isolation_state(
            max_uptime_s=args.max_prelaunch_uptime_s
        )
        result["isolation"]["candidate_id"] = args.candidate_id
        result["isolation"]["test_id"] = args.test_id
        result["isolation"]["prior_receipts_checked"] = enforce_suite_isolation(
            args.evidence_root,
            result["isolation"],
            candidate_id=args.candidate_id,
            test_id=args.test_id,
            execution_sha=args.execution_sha,
            execution_surface_sha256=result["execution_surface_sha256"],
        )
        result["environment"] = target_preflight(args.execution_sha)
        raw_dir.mkdir(parents=True, exist_ok=False)

        runtime = lock["runtime"]
        install = subprocess.run(
            [
                "python3",
                "poc_llm/tools/install_gate1_arm64_wheel_v2.py",
                "--wheel",
                runtime["wheel_path"],
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
            raise PiPacketFailure("P6.1/P7.1 installer result invalid") from exc
        if install.returncode != 0 or install_result.get("result") != "PASS":
            raise PiPacketFailure("P6.1/P7.1 offline installation failed")
        result["runtime"] = native_library_preflight_v2(
            install_root / "litert_lm/liblitert-lm.so",
            runtime["native_library_sha256"],
        )
        runtime_import = subprocess.run(
            [sys.executable, "-c", "import litert_lm"],
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
        if runtime_import.returncode != 0:
            raise PiPacketFailure("P6.1/P7.1 runtime import failed")
        result["runtime"]["python_import"] = "PASS"

        protocol = repo_artifact(lock["artifacts"]["protocol_schema"])
        config_schema = repo_artifact(lock["artifacts"]["config_schema"])
        prompt_schema = repo_artifact(lock["artifacts"]["prompt_schema"])
        response_schema = repo_artifact(lock["artifacts"]["response_schema"])
        receipt_schema = repo_artifact(lock["artifacts"]["artifact_receipt_schema"])
        result_schema = repo_artifact(lock["artifacts"]["result_schema"])
        abort_fixture = load(repo_artifact(lock["artifacts"]["abort_fixture"]))
        catalog = load(repo_artifact(lock["artifacts"]["catalog"]))
        license_metadata = load(repo_artifact(lock["artifacts"]["license_metadata"]))
        provenance = license_metadata.get("candidates", {}).get(args.candidate_id, {})
        if (
            provenance.get("license") not in {"apache-2.0", "gemma"}
            or not re.fullmatch(r"[0-9a-f]{40}", str(provenance.get("revision", "")))
        ):
            raise PiPacketFailure("P6.1/P7.1 provenance mismatch")
        config = repo_artifact(entry["standard_config"])
        config_value = load(config)
        if (
            config_value.get("candidate_id") != args.candidate_id
            or config_value.get("platform") != PLATFORM
            or config_value.get("engine_max_num_tokens") != CANDIDATES[args.candidate_id]
            or config_value.get("ready_timeout_ms") != 10_000
            or config_value.get("rebuild_timeout_ms") != 10_000
        ):
            raise PiPacketFailure("P6.1/P7.1 candidate config drift")
        validator = protocol_validator(protocol, prompt_schema, response_schema)

        model_record = authenticate_model(
            Path(config_value["model_path"]),
            entry["model_sha256"],
            entry["model_size_bytes"],
            timeout_s=120.0,
        )
        receipt = {
            "receipt_version": "pi-artifact-auth/2",
            "packet_id": BASE_PACKET_ID,
            "run_id": args.run_id,
            "execution_sha": args.execution_sha,
            "execution_surface_sha256": result["execution_surface_sha256"],
            "candidate_id": args.candidate_id,
            "runtime_sha256": runtime["wheel_sha256"],
            "model": model_record,
        }
        if not Draft202012Validator(load(receipt_schema)).is_valid(receipt):
            raise PiPacketFailure("P6.1/P7.1 artifact receipt schema mismatch")
        receipt_path = raw_dir / f"{args.candidate_id}.artifact-receipt.json"
        receipt_path.write_text(
            json.dumps(receipt, sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )
        result["artifact_authentication"] = {
            "model_sha256": model_record["sha256"],
            "model_size_bytes": model_record["size_bytes"],
            "duration_ms": model_record["authentication_duration_ms"],
            "receipt_sha256": streaming_digest(receipt_path),
            "full_model_hash_count": 1,
            "metadata_unchanged": False,
        }
        common = {
            "config": config,
            "config_sha256": entry["standard_config"]["sha256"],
            "config_value": config_value,
            "config_schema": config_schema,
            "protocol_schema": protocol,
            "prompt_schema": prompt_schema,
            "response_schema": response_schema,
            "receipt": receipt_path,
            "receipt_schema": receipt_schema,
            "install_root": install_root,
            "validator": validator,
            "abort_fixture": abort_fixture,
            "catalog": catalog,
        }
        if args.test_id == "P6.1":
            run_p6_1(
                common=common,
                result=result,
                stderr_path=raw_dir / f"{args.candidate_id}.p6-1.stderr",
            )
        else:
            run_p7_1(
                common=common,
                result=result,
                fault_stderr_path=raw_dir / f"{args.candidate_id}.p7-1.stderr",
                rebuild_stderr_path=raw_dir / f"{args.candidate_id}.p7-1-rebuild.stderr",
            )
        verify_model_receipt(
            receipt["model"], Path(config_value["model_path"]), config_value["model_sha256"]
        )
        result["artifact_authentication"]["metadata_unchanged"] = True
        result["environment_post"] = target_preflight(args.execution_sha)
        result["result"] = result["p_result"]
    except (PiPacketFailure, OSError, subprocess.SubprocessError, KeyError, ValueError) as exc:
        result["violations"].append(str(exc))
        if result["p_result"] == "INCONCLUSIVE" and result["prerequisite_ready_ms"] is not None:
            result["p_result"] = "FAIL"
        result["result"] = result["p_result"]
    finally:
        result["elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)
        if install_root.exists():
            shutil.rmtree(install_root)
        if raw_dir.exists():
            if result_schema is not None:
                errors = list(Draft202012Validator(load(result_schema)).iter_errors(result))
                if errors:
                    result["violations"].append("P6.1/P7.1 result schema validation failed")
                    result["result"] = "INCONCLUSIVE"
            (raw_dir / "p6-1-p7-1-sanitized.json").write_text(
                json.dumps(result, sort_keys=True), encoding="utf-8"
            )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["result"] == "PASS" else 1 if result["result"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
