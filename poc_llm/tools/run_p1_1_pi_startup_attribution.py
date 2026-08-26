#!/usr/bin/env python3
"""Run non-scoring P1.1 startup attribution on an authorized physical Pi."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.pi_artifact_auth import authenticate_model, streaming_digest
from poc_llm.harness.pi_runtime import (
    load,
    protocol_validator,
    read_frame,
    send,
    stop,
    target_preflight,
)
from poc_llm.tools.run_gate1_pi_compat_v7 import catalog_input


PACKET_ID = "P1.1-PI-STARTUP-ATTRIBUTION-001"
STAGE = re.compile(r"^P1_1_STAGE ([^ ]+) ([0-9]+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--p1-1-lock", type=Path, required=True)
    parser.add_argument("--gate1-lock", type=Path, required=True)
    parser.add_argument("--candidate-set", type=Path, required=True)
    parser.add_argument("--profile-set", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    return parser.parse_args()


def locked_artifact(item: dict[str, str]) -> Path:
    path = (ROOT / item["path"]).resolve()
    if not path.is_file() or streaming_digest(path) != item["sha256"]:
        raise RuntimeError(f"P1.1 locked artifact mismatch: {item['path']}")
    return path


def drop_model_cache(path: Path) -> float:
    started = time.monotonic()
    with path.open("rb", buffering=0) as stream:
        if hasattr(os, "posix_fadvise") and hasattr(os, "POSIX_FADV_DONTNEED"):
            os.posix_fadvise(stream.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
    return round((time.monotonic() - started) * 1000, 3)


def fresh_install_paths() -> tuple[Path, Path]:
    parent = Path(tempfile.mkdtemp(prefix="p1-1-install-", dir="/tmp"))
    return parent, parent / "runtime"


def stage_durations(stderr_path: Path, process_started_ns: int) -> dict[str, float]:
    values: dict[str, int] = {}
    for line in stderr_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = STAGE.fullmatch(line)
        if match:
            values[match.group(1)] = int(match.group(2))
    pairs = {
        "spawn_to_adapter_main": (None, "adapter_main_start"),
        "config_receipt": ("config_receipt_start", "config_receipt_end"),
        "litert_import": ("litert_import_start", "litert_import_end"),
        "engine": ("engine_start", "engine_end"),
        "sampler": ("sampler_start", "sampler_end"),
        "protocol_validator": ("protocol_validator_start", "protocol_validator_end"),
        "ready_emit": ("ready_emit_start", "ready_emit_end"),
    }
    result: dict[str, float] = {}
    for name, (start, end) in pairs.items():
        if end not in values or (start is not None and start not in values):
            continue
        beginning = process_started_ns if start is None else values[start]
        result[name] = round((values[end] - beginning) / 1_000_000, 3)
    return result


def observation_viable(observation: dict[str, Any]) -> bool:
    return bool(
        observation.get("eventual_ready_ms") is not None
        and observation["eventual_ready_ms"] <= 10_000
        and observation.get("ping_pong")
        and observation.get("generation_terminal") == "RESULT"
        and observation.get("shutdown_ack")
        and observation.get("cleanup", {}).get("process_group_absent")
    )


def diagnostic_stop(process: subprocess.Popen[str]) -> dict[str, Any]:
    try:
        return stop(process, kill_s=10.0)
    except subprocess.TimeoutExpired:
        return {
            "exit_code": process.poll(),
            "waited": False,
            "term_sent": True,
            "kill_sent": True,
            "process_group_absent": False,
            "cleanup_timeout": True,
        }


def main() -> int:
    args = parse_args()
    started = time.monotonic()
    result: dict[str, Any] = {
        "packet_id": PACKET_ID,
        "run_id": args.run_id,
        "diagnostic_only": True,
        "gate_credit": "FORBIDDEN",
        "execution_sha": args.execution_sha,
        "environment": {},
        "environment_post": {},
        "profiles": [],
        "candidates": [],
        "result": "INCONCLUSIVE",
        "violations": [],
    }
    run_root = args.evidence_root / args.run_id
    raw_root = run_root / "raw"
    install_parent, install_root = fresh_install_paths()
    try:
        run_root.mkdir(parents=True, exist_ok=False)
        raw_root.mkdir()
        result["environment"] = target_preflight(args.execution_sha)
        p1_1_lock = load(args.p1_1_lock)
        if (
            p1_1_lock.get("packet_id") != PACKET_ID
            or p1_1_lock.get("diagnostic_only") is not True
            or p1_1_lock.get("gate_credit") != "FORBIDDEN"
        ):
            raise RuntimeError("P1.1 lock identity mismatch")
        locked = {
            name: locked_artifact(item)
            for name, item in p1_1_lock.get("artifacts", {}).items()
        }
        for supplied, name in (
            (args.gate1_lock, "gate1_lock"),
            (args.candidate_set, "candidate_set"),
            (args.profile_set, "profiles"),
        ):
            if supplied.resolve() != locked[name]:
                raise RuntimeError(f"P1.1 supplied {name} path is not locked")
        lock = load(locked["gate1_lock"])
        for item in lock["artifacts"].values():
            locked_artifact(item)
        candidates = load(locked["candidate_set"])["candidates"]
        profiles = load(locked["profiles"])
        profile_definitions = profiles.get("profiles", [])
        profile_ids = [item.get("profile_id") for item in profile_definitions]
        if (
            profiles.get("packet_id") != PACKET_ID
            or profiles.get("gate_credit") != "FORBIDDEN"
            or profiles.get("candidate_order") != [item["candidate_id"] for item in candidates]
            or len(profile_ids) != 1
            or profile_ids[0] not in {"baseline", "bounded_context"}
        ):
            raise RuntimeError("P1.1 frozen profile set mismatch")
        result["profiles"] = profile_ids

        runtime = lock["runtime"]
        install = subprocess.run(
            [
                "python3",
                "poc_llm/tools/install_gate1_arm64_wheel_v2.py",
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
        if install.returncode != 0:
            raise RuntimeError("P1.1 offline runtime installation failed")

        artifacts = lock["artifacts"]
        protocol_path = ROOT / artifacts["protocol_schema"]["path"]
        prompt_path = ROOT / artifacts["prompt_schema"]["path"]
        response_path = ROOT / artifacts["response_schema"]["path"]
        config_schema = ROOT / artifacts["config_schema"]["path"]
        receipt_schema = ROOT / artifacts["artifact_receipt_schema"]["path"]
        receipt_validator = Draft202012Validator(load(receipt_schema))
        catalog = load(ROOT / artifacts["catalog"]["path"])
        validator = protocol_validator(protocol_path, prompt_path, response_path)
        probe = locked["probe"]

        for entry in candidates:
            candidate_id = entry["candidate_id"]
            config = ROOT / entry["standard_config"]["path"]
            config_value = load(config)
            model = Path(config_value["model_path"])
            cache_drop_advice_ms = drop_model_cache(model)
            model_record = authenticate_model(
                model,
                entry["model_sha256"],
                entry["model_size_bytes"],
                timeout_s=120.0,
            )
            receipt_value = {
                "receipt_version": "pi-artifact-auth/2",
                "packet_id": "G1-PI-COMPAT-007",
                "run_id": args.run_id,
                "execution_sha": args.execution_sha,
                "execution_surface_sha256": streaming_digest(args.gate1_lock),
                "candidate_id": candidate_id,
                "runtime_sha256": runtime["wheel_sha256"],
                "model": model_record,
            }
            if not receipt_validator.is_valid(receipt_value):
                raise RuntimeError("P1.1 fresh artifact receipt schema mismatch")
            receipt = raw_root / f"{candidate_id}.artifact-receipt.json"
            receipt.write_text(
                json.dumps(receipt_value, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            candidate_result = {"candidate_id": candidate_id, "observations": []}
            result["candidates"].append(candidate_result)
            for profile_definition in profile_definitions:
                profile = profile_definition["profile_id"]
                expected_max_num_tokens = (
                    None
                    if profile == "baseline"
                    else config_value["max_input_tokens"]
                    + config_value["max_output_tokens"]
                )
                if profile_definition.get("max_num_tokens") != expected_max_num_tokens:
                    raise RuntimeError("P1.1 profile/context envelope mismatch")
                observation: dict[str, Any] = {
                    "profile_id": profile,
                    "engine_max_num_tokens": expected_max_num_tokens,
                    "cache_drop_advice_ms": cache_drop_advice_ms,
                    "artifact_authentication_ms": model_record[
                        "authentication_duration_ms"
                    ],
                    "eventual_ready_ms": None,
                    "stage_ms": {},
                    "ping_pong": False,
                    "generation_terminal": "NONE",
                    "shutdown_ack": False,
                    "cleanup": {},
                    "p1_contract_fit": False,
                    "diagnostic_result": "INCONCLUSIVE",
                }
                stderr_path = raw_root / f"{candidate_id}.{profile}.stderr"
                argv = [
                    "env", f"PYTHONPATH={install_root}", "python3", str(probe),
                    "--p1-1-profile", profile,
                    "--config", str(config),
                    "--config-sha256", entry["standard_config"]["sha256"],
                    "--config-schema", str(config_schema),
                    "--config-schema-sha256", streaming_digest(config_schema),
                    "--protocol-schema", str(protocol_path),
                    "--protocol-schema-sha256", streaming_digest(protocol_path),
                    "--prompt-schema", str(prompt_path),
                    "--prompt-schema-sha256", streaming_digest(prompt_path),
                    "--response-schema", str(response_path),
                    "--response-schema-sha256", streaming_digest(response_path),
                    "--artifact-receipt", str(receipt),
                    "--artifact-receipt-sha256", streaming_digest(receipt),
                    "--artifact-receipt-schema", str(receipt_schema),
                    "--artifact-receipt-schema-sha256", streaming_digest(receipt_schema),
                ]
                process: subprocess.Popen[str] | None = None
                process_started_ns = time.monotonic_ns()
                try:
                    with stderr_path.open("w", encoding="utf-8") as stderr:
                        process = subprocess.Popen(
                            argv,
                            cwd=ROOT,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=stderr,
                            text=True,
                            start_new_session=True,
                            env={
                                **os.environ,
                                "HF_HUB_OFFLINE": "1",
                                "TRANSFORMERS_OFFLINE": "1",
                            },
                        )
                        if process.stdout is None:
                            raise RuntimeError("P1.1 child stdout unavailable")
                        ready = read_frame(process.stdout, 120.0, validator)
                        observation["eventual_ready_ms"] = round(
                            (time.monotonic_ns() - process_started_ns) / 1_000_000, 3
                        )
                        expected = {
                            "candidate_id": config_value["candidate_id"],
                            "pairing_revision": config_value["pairing_revision"],
                            "platform": config_value["platform"],
                            "runtime_sha256": config_value["runtime_sha256"],
                            "model_sha256": config_value["model_sha256"],
                            "config_sha256": entry["standard_config"]["sha256"],
                        }
                        if ready.get("type") != "READY" or ready.get("identity") != expected:
                            raise RuntimeError("P1.1 READY identity mismatch")
                        send(process, {"type": "PING", "protocol_version": "snowboard.llm/1"})
                        observation["ping_pong"] = (
                            read_frame(process.stdout, 2.0, validator).get("type") == "PONG"
                        )
                        send(
                            process,
                            {
                                "type": "GENERATE",
                                "protocol_version": "snowboard.llm/1",
                                "request_id": f"p1-1-{profile}",
                                "input": catalog_input(catalog["valid_cases"][0]),
                            },
                        )
                        terminal = read_frame(process.stdout, 15.0, validator)
                        observation["generation_terminal"] = terminal.get("type", "NONE")
                        send(process, {"type": "SHUTDOWN", "protocol_version": "snowboard.llm/1"})
                        observation["shutdown_ack"] = (
                            read_frame(process.stdout, 2.0, validator).get("type")
                            == "SHUTDOWN_ACK"
                        )
                        process.wait(timeout=2.0)
                        observation["cleanup"] = diagnostic_stop(process)
                        process = None
                except Exception:
                    if process is not None:
                        observation["cleanup"] = diagnostic_stop(process)
                        process = None
                observation["stage_ms"] = stage_durations(stderr_path, process_started_ns)
                observation["p1_contract_fit"] = observation_viable(observation)
                observation["diagnostic_result"] = (
                    "VIABLE"
                    if observation["p1_contract_fit"]
                    else "NOT_VIABLE"
                    if observation["eventual_ready_ms"] is not None
                    else "INCONCLUSIVE"
                )
                candidate_result["observations"].append(observation)

        result["environment_post"] = target_preflight(args.execution_sha)
        result["result"] = "COMPLETE"
        schema = load(locked["result_schema"])
        errors = list(Draft202012Validator(schema).iter_errors(result))
        if errors:
            raise RuntimeError("P1.1 result schema mismatch")
    except Exception as exc:
        result["violations"].append(f"{type(exc).__name__}: {exc}")
        result["result"] = "INCONCLUSIVE"
    finally:
        shutil.rmtree(install_parent)
        run_root.mkdir(parents=True, exist_ok=True)
        (run_root / "p1-1-sanitized.json").write_text(
            json.dumps(result, sort_keys=True, indent=2), encoding="utf-8"
        )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["result"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
