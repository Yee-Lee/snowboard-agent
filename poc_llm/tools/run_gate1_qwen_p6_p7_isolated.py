#!/usr/bin/env python3
"""Run only Qwen P6/P7 from a reboot-isolated, healthy persistent child."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
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
    protocol_validator,
    read_frame,
    send,
    stop,
    target_preflight,
)
from poc_llm.harness.pi_runtime_v2 import native_library_preflight_v2
from poc_llm.tools.run_gate1_pi_compat_v7 import (
    catalog_input,
    close_child,
    generate,
    group_resource_sample,
    observe_generation_threads,
    start_child,
    wait_generation_threads_settle,
)
from poc_llm.tools.run_gate1_qwen_isolated_completion import isolation_state


PACKET_ID = "G1-QWEN-P6P7-ISOLATED-001"
BASE_PACKET_ID = "G1-PI-COMPAT-007"
QWEN_ID = "CAND-LRT-Q25-15B-Q8-R1"
PLATFORM = "pi-debian13-aarch64"


class FocusedEvidenceInconclusive(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-lock", type=Path, required=True)
    parser.add_argument("--candidate-set", type=Path, required=True)
    parser.add_argument("--execution-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--max-prelaunch-uptime-s", type=float, default=900.0)
    return parser.parse_args()


def repo_artifact(item: dict[str, str]) -> Path:
    path = (ROOT / item["path"]).resolve()
    if not path.is_file() or streaming_digest(path) != item["sha256"]:
        raise PiPacketFailure(f"locked repository artifact mismatch: {item['path']}")
    return path


def main() -> int:
    args = parse_args()
    started = time.monotonic()
    raw_dir = args.evidence_root / args.run_id
    install_root = Path(f"/tmp/llm-poc-g1-qwen-p6p7/install-{args.run_id}")
    result: dict[str, Any] = {
        "packet_id": PACKET_ID,
        "base_packet_id": BASE_PACKET_ID,
        "run_id": args.run_id,
        "execution_sha": args.execution_sha,
        "execution_surface_sha256": "",
        "core_acceptance": "PENDING",
        "isolation": {},
        "environment": {},
        "environment_post": {},
        "runtime": {},
        "artifact_authentication": {},
        "prerequisite_ready_ms": None,
        "p_results": {"P6": "Blocked", "P7": "Blocked"},
        "cancel": {},
        "recovery": {},
        "violations": [],
        "result": "INCONCLUSIVE",
    }
    active_process: subprocess.Popen[str] | None = None
    p7_attempted = False
    result_schema: Path | None = None
    try:
        if raw_dir.exists() or install_root.exists():
            raise PiPacketFailure("focused evidence or install path is dirty")
        lock = load(args.packet_lock)
        if (
            lock.get("packet_id") != BASE_PACKET_ID
            or lock.get("candidate_order") != [QWEN_ID]
        ):
            raise PiPacketFailure("focused lock identity mismatch")
        result["execution_surface_sha256"] = streaming_digest(args.packet_lock)
        for item in lock["artifacts"].values():
            repo_artifact(item)
        if streaming_digest(args.candidate_set) != lock["candidate_set_sha256"]:
            raise PiPacketFailure("focused candidate set checksum mismatch")
        candidate_set = load(args.candidate_set)
        candidates = candidate_set.get("candidates", [])
        if (
            candidate_set.get("packet_id") != BASE_PACKET_ID
            or len(candidates) != 1
            or candidates[0].get("candidate_id") != QWEN_ID
        ):
            raise PiPacketFailure("focused candidate set identity mismatch")
        entry = candidates[0]
        result["isolation"] = isolation_state(
            max_uptime_s=args.max_prelaunch_uptime_s
        )
        result["environment"] = target_preflight(args.execution_sha)
        raw_dir.mkdir(parents=True, exist_ok=False)

        runtime = lock["runtime"]
        wheel = Path(runtime["wheel_path"])
        install = subprocess.run(
            [
                "python3", "poc_llm/tools/install_gate1_arm64_wheel_v2.py",
                "--wheel", str(wheel), "--wheel-sha256", runtime["wheel_sha256"],
                "--target", str(install_root),
            ],
            cwd=ROOT, text=True, capture_output=True, check=False, timeout=300,
        )
        (raw_dir / "offline-install.stdout").write_text(install.stdout, encoding="utf-8")
        (raw_dir / "offline-install.stderr").write_text(install.stderr, encoding="utf-8")
        try:
            install_result = json.loads(install.stdout)
        except json.JSONDecodeError as exc:
            raise PiPacketFailure("focused offline installer emitted invalid result") from exc
        if install.returncode != 0 or install_result.get("result") != "PASS":
            raise PiPacketFailure("focused offline runtime installation failed")
        result["runtime"] = native_library_preflight_v2(
            install_root / "litert_lm/liblitert-lm.so",
            runtime["native_library_sha256"],
        )
        runtime_import = subprocess.run(
            [sys.executable, "-c", "import litert_lm"],
            cwd=ROOT, text=True, capture_output=True, check=False, timeout=30,
            env={
                **os.environ, "PYTHONPATH": str(install_root),
                "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
            },
        )
        (raw_dir / "runtime-import.stdout").write_text(
            runtime_import.stdout, encoding="utf-8"
        )
        (raw_dir / "runtime-import.stderr").write_text(
            runtime_import.stderr, encoding="utf-8"
        )
        if runtime_import.returncode != 0:
            raise PiPacketFailure("focused installed runtime import failed")
        result["runtime"]["python_import"] = "PASS"

        protocol = repo_artifact(lock["artifacts"]["protocol_schema"])
        config_schema = repo_artifact(lock["artifacts"]["config_schema"])
        prompt_schema = repo_artifact(lock["artifacts"]["prompt_schema"])
        response_schema = repo_artifact(lock["artifacts"]["response_schema"])
        receipt_schema = repo_artifact(lock["artifacts"]["artifact_receipt_schema"])
        result_schema = repo_artifact(lock["artifacts"]["focused_result_schema"])
        abort_fixture = load(repo_artifact(lock["artifacts"]["abort_fixture"]))
        catalog = load(repo_artifact(lock["artifacts"]["catalog"]))
        license_metadata = load(repo_artifact(lock["artifacts"]["license_metadata"]))
        provenance = license_metadata.get("candidates", {}).get(QWEN_ID, {})
        if (
            provenance.get("license") != "apache-2.0"
            or not re.fullmatch(r"[0-9a-f]{40}", str(provenance.get("revision", "")))
        ):
            raise PiPacketFailure("focused Qwen provenance mismatch")
        config = repo_artifact(entry["standard_config"])
        config_value = load(config)
        if (
            config_value.get("candidate_id") != QWEN_ID
            or config_value.get("platform") != PLATFORM
            or config_value.get("engine_max_num_tokens") != 512
            or config_value.get("ready_timeout_ms") != 10_000
            or config_value.get("rebuild_timeout_ms") != 10_000
        ):
            raise PiPacketFailure("focused Qwen config drift")
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
            "candidate_id": QWEN_ID,
            "runtime_sha256": runtime["wheel_sha256"],
            "model": model_record,
        }
        receipt_validator = Draft202012Validator(load(receipt_schema))
        if not receipt_validator.is_valid(receipt):
            raise PiPacketFailure("focused artifact receipt schema mismatch")
        receipt_path = raw_dir / f"{QWEN_ID}.artifact-receipt.json"
        receipt_path.write_text(
            json.dumps(receipt, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        result["artifact_authentication"] = {
            "model_sha256": model_record["sha256"],
            "model_size_bytes": model_record["size_bytes"],
            "duration_ms": model_record["authentication_duration_ms"],
            "receipt_sha256": streaming_digest(receipt_path),
            "full_model_hash_count": 1,
            "metadata_unchanged": False,
        }

        fault_stderr = raw_dir / f"{QWEN_ID}.p6-p7.stderr"
        try:
            with fault_stderr.open("w", encoding="utf-8") as stderr:
                active_process, prerequisite_ready_ms = start_child(
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
                result["prerequisite_ready_ms"] = prerequisite_ready_ms
                send(active_process, {"type": "PING", "protocol_version": "snowboard.llm/1"})
                if (
                    active_process.stdout is None
                    or read_frame(active_process.stdout, 2.0, validator).get("type") != "PONG"
                ):
                    raise FocusedEvidenceInconclusive("focused prerequisite PING/PONG failed")
                baseline_threads = group_resource_sample(active_process.pid)["threads"]
                send(
                    active_process,
                    {
                        "type": "GENERATE", "protocol_version": "snowboard.llm/1",
                        "request_id": "p6-cancel", "input": abort_fixture["input"],
                    },
                )
                active_threads = observe_generation_threads(active_process, baseline_threads)
                if active_threads is None:
                    raise FocusedEvidenceInconclusive(
                        "focused P6 active generation could not be observed"
                    )
                cancel_started = time.monotonic()
                send(
                    active_process,
                    {
                        "type": "CANCEL", "protocol_version": "snowboard.llm/1",
                        "request_id": "p6-cancel",
                    },
                )
                cancel_terminal: dict[str, Any] | None = None
                try:
                    if active_process.stdout is None:
                        raise FocusedEvidenceInconclusive("focused P6 stdout unavailable")
                    cancel_terminal = read_frame(active_process.stdout, 0.5, validator)
                except PiPacketFailure as exc:
                    if str(exc) != "protocol frame deadline exceeded":
                        raise
                cancel_ms = round((time.monotonic() - cancel_started) * 1000, 3)
                native_cancel = (
                    cancel_terminal is not None
                    and cancel_terminal.get("type") == "CANCELLED"
                    and cancel_terminal.get("request_id") == "p6-cancel"
                    and cancel_ms <= 500.0
                )
                result["p_results"]["P6"] = (
                    "PASS" if native_cancel else "Conditional escalation"
                )
                result["cancel"] = {
                    "generation_active_observed": True,
                    "baseline_threads": baseline_threads,
                    "active_threads": active_threads,
                    "terminal": cancel_terminal.get("type") if cancel_terminal else "NONE",
                    "elapsed_ms": cancel_ms,
                    "disposition": result["p_results"]["P6"],
                }
                if cancel_terminal is not None:
                    baseline_threads = wait_generation_threads_settle(active_process)
                    send(
                        active_process,
                        {
                            "type": "GENERATE", "protocol_version": "snowboard.llm/1",
                            "request_id": "p7-force", "input": abort_fixture["input"],
                        },
                    )
                    if observe_generation_threads(active_process, baseline_threads) is None:
                        raise FocusedEvidenceInconclusive(
                            "focused P7 active generation could not be observed"
                        )
                force_cleanup = stop(active_process)
                active_process = None
                p7_attempted = True
                if (
                    not force_cleanup.get("term_sent")
                    or not force_cleanup.get("waited")
                    or not force_cleanup.get("process_group_absent")
                ):
                    raise PiPacketFailure("focused P7 Level 2 cleanup failed")
        except PiPacketFailure:
            raise

        rebuild_stderr = raw_dir / f"{QWEN_ID}.rebuild.stderr"
        with rebuild_stderr.open("w", encoding="utf-8") as stderr:
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
                raise PiPacketFailure("focused P7 rebuild PING/PONG failed")
            recovery_terminal, recovery_ms = generate(
                active_process,
                validator,
                "p7-recovery",
                catalog_input(catalog["valid_cases"][0]),
            )
            if recovery_terminal.get("type") != "RESULT":
                raise PiPacketFailure("focused P7 recovery generation failed")
            rebuild_cleanup = close_child(active_process, validator)
            active_process = None
        fatal = subprocess.run(
            [sys.executable, str(ROOT / "poc_llm/tools/run_gate1_pi_compat_v7.py"),
             "--fatal-outcome-self-test"],
            cwd=ROOT, check=False,
        )
        if fatal.returncode != 4:
            raise PiPacketFailure("focused P7 fatal outcome mapping failed")
        result["recovery"] = {
            "force_abort": force_cleanup,
            "rebuild_ready_ms": rebuild_ready_ms,
            "recovery_generation_ms": recovery_ms,
            "recovery_terminal": "RESULT",
            "rebuild_cleanup": rebuild_cleanup,
            "fatal_outcome_exit_code": fatal.returncode,
        }
        result["p_results"]["P7"] = "PASS"
        verify_model_receipt(
            receipt["model"], Path(config_value["model_path"]), config_value["model_sha256"]
        )
        result["artifact_authentication"]["metadata_unchanged"] = True
        result["environment_post"] = target_preflight(args.execution_sha)
        result["result"] = "PASS"
    except FocusedEvidenceInconclusive as exc:
        result["violations"].append(str(exc))
        result["result"] = "INCONCLUSIVE"
        if active_process is not None:
            result.setdefault("recovery", {})["exception_cleanup"] = stop(active_process)
            active_process = None
    except (PiPacketFailure, OSError, subprocess.SubprocessError, KeyError, ValueError) as exc:
        result["violations"].append(str(exc))
        result["result"] = "FAIL" if p7_attempted else "INCONCLUSIVE"
        if p7_attempted:
            result["p_results"]["P7"] = "FAIL"
        if active_process is not None:
            result.setdefault("recovery", {})["exception_cleanup"] = stop(active_process)
            active_process = None
    finally:
        result["elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)
        if install_root.exists():
            shutil.rmtree(install_root)
        if raw_dir.exists():
            if result_schema is None:
                try:
                    lock = load(args.packet_lock)
                    result_schema = repo_artifact(lock["artifacts"]["focused_result_schema"])
                except (OSError, KeyError, ValueError, PiPacketFailure):
                    result_schema = None
            if result_schema is not None:
                errors = list(Draft202012Validator(load(result_schema)).iter_errors(result))
                if errors:
                    result["violations"].append("focused result schema validation failed")
                    result["result"] = "INCONCLUSIVE"
            (raw_dir / "qwen-p6-p7-isolated-sanitized.json").write_text(
                json.dumps(result, sort_keys=True), encoding="utf-8"
            )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["result"] == "PASS" else 1 if result["result"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
