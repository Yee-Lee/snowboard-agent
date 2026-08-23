#!/usr/bin/env python3
"""Execute the bounded, no-Gate-2-credit Pi compatibility packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.pi_runtime import (
    PiPacketFailure, digest, launch, load, protocol_validator, read_frame,
    require_ready, send, stop, target_preflight,
)


PACKET_ID = "G1-PI-COMPAT-006"
PLATFORM = "pi-debian13-aarch64"
MINIMAL_INPUT = {
    "perceptions": [{"kind": "read", "status": "ok", "text": "Choose the rest action."}],
    "pending_message_count": 0,
    "capabilities": {"perceptions": ["read"], "actions": ["rest"], "tools": []},
}


def _repo_file(relative: str, expected: str) -> Path:
    path = (ROOT / relative).resolve()
    if not path.is_file() or digest(path) != expected:
        raise PiPacketFailure(f"locked repository artifact mismatch: {relative}")
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-lock", type=Path, required=True)
    parser.add_argument("--candidate-set", type=Path, required=True)
    parser.add_argument("--execution-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    return parser.parse_args()


def _empty_candidate(candidate_id: str) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "result": "INCONCLUSIVE",
        "checks": {name: "Pending" for name in (
            "artifacts", "offline_install", "runtime_import", "ready", "ping",
            "minimal_generation", "shutdown", "exit", "orphan_zero", "cleanup",
        )},
        "timing_ms": {}, "cleanup": {}, "violations": [],
    }


def _validate_result(value: dict[str, Any], result_schema: Path) -> None:
    if list(Draft202012Validator(load(result_schema)).iter_errors(value)):
        raise PiPacketFailure("Gate 1 Pi result schema mismatch")


def main() -> int:
    args = _parse_args()
    started = time.monotonic()
    aggregate: dict[str, Any] = {
        "packet_id": PACKET_ID, "run_id": args.run_id, "execution_sha": args.execution_sha,
        "platform": "pi5-4gb-debian13-aarch64", "gate2_credit": False,
        "result": "INCONCLUSIVE", "environment": {}, "candidates": [], "violations": [],
    }
    raw_dir = args.evidence_root / args.run_id
    install_root = Path(f"/tmp/llm-poc-g1-pi-006/install-{args.run_id}")
    try:
        if raw_dir.exists() or install_root.exists():
            raise PiPacketFailure("run-owned evidence or install path is dirty")
        lock = load(args.packet_lock)
        if lock.get("packet_id") != PACKET_ID:
            raise PiPacketFailure("packet lock ID mismatch")
        for item in lock["artifacts"].values():
            _repo_file(item["path"], item["sha256"])
        candidate_set = load(args.candidate_set)
        if candidate_set.get("packet_id") != PACKET_ID:
            raise PiPacketFailure("candidate set packet ID mismatch")
        if digest(args.candidate_set) != lock["candidate_set_sha256"]:
            raise PiPacketFailure("candidate set checksum mismatch")
        candidates = candidate_set.get("candidates")
        if not isinstance(candidates, list) or [item["candidate_id"] for item in candidates] != lock["candidate_order"]:
            raise PiPacketFailure("candidate set/order mismatch or backfill attempt")
        aggregate["environment"] = target_preflight(args.execution_sha)
        raw_dir.mkdir(parents=True, exist_ok=False)
        runtime = lock["runtime"]
        wheel = Path(runtime["wheel_path"])
        if not wheel.is_file() or digest(wheel) != runtime["wheel_sha256"]:
            raise PiPacketFailure("staged runtime wheel identity mismatch")
        install = subprocess.run(
            ["python3", "poc_llm/tools/install_gate1_arm64_wheel.py", "--wheel", str(wheel),
             "--wheel-sha256", runtime["wheel_sha256"], "--target", str(install_root)],
            cwd=ROOT, text=True, capture_output=True, check=False, timeout=300,
        )
        (raw_dir / "offline-install.stdout").write_text(install.stdout, encoding="utf-8")
        (raw_dir / "offline-install.stderr").write_text(install.stderr, encoding="utf-8")
        if install.returncode != 0:
            raise PiPacketFailure("offline runtime installation failed")
        native = install_root / "litert_lm/liblitert-lm.so"
        if not native.is_file() or digest(native) != runtime["native_library_sha256"]:
            raise PiPacketFailure("installed native library identity mismatch")
        protocol = _repo_file(lock["artifacts"]["protocol_schema"]["path"], lock["artifacts"]["protocol_schema"]["sha256"])
        config_schema = _repo_file(lock["artifacts"]["config_schema"]["path"], lock["artifacts"]["config_schema"]["sha256"])
        prompt_schema = _repo_file(lock["artifacts"]["prompt_schema"]["path"], lock["artifacts"]["prompt_schema"]["sha256"])
        response_schema = _repo_file(lock["artifacts"]["response_schema"]["path"], lock["artifacts"]["response_schema"]["sha256"])
        validator = protocol_validator(protocol, prompt_schema, response_schema)
        for entry in candidates:
            report = _empty_candidate(entry["candidate_id"])
            aggregate["candidates"].append(report)
            process: subprocess.Popen[str] | None = None
            try:
                config = _repo_file(entry["standard_config"]["path"], entry["standard_config"]["sha256"])
                config_value = load(config)
                if config_value["candidate_id"] != entry["candidate_id"] or config_value["platform"] != PLATFORM:
                    raise PiPacketFailure("candidate/config identity mismatch")
                report["checks"]["artifacts"] = report["checks"]["offline_install"] = report["checks"]["runtime_import"] = "PASS"
                stderr_path = raw_dir / f"{entry['candidate_id']}.stderr"
                with stderr_path.open("w", encoding="utf-8") as stderr:
                    launch_started = time.monotonic()
                    process = launch(config=config, config_sha256=entry["standard_config"]["sha256"], config_schema=config_schema, protocol_schema=protocol, install_root=install_root, stderr=stderr)
                    require_ready(process, validator, config_value, entry["standard_config"]["sha256"])
                    report["timing_ms"]["ready"] = round((time.monotonic() - launch_started) * 1000, 3)
                    report["checks"]["ready"] = "PASS"
                    send(process, {"type": "PING", "protocol_version": "snowboard.llm/1"})
                    if process.stdout is None or read_frame(process.stdout, 2.0, validator).get("type") != "PONG":
                        raise PiPacketFailure("PING/PONG failed")
                    report["checks"]["ping"] = "PASS"
                    send(process, {"type": "GENERATE", "protocol_version": "snowboard.llm/1", "request_id": "g1-minimal", "input": MINIMAL_INPUT})
                    generation_started = time.monotonic()
                    terminal = read_frame(process.stdout, 15.0, validator)
                    report["timing_ms"]["minimal_generation"] = round((time.monotonic() - generation_started) * 1000, 3)
                    if terminal.get("type") != "RESULT" or terminal.get("request_id") != "g1-minimal":
                        raise PiPacketFailure("minimal deterministic generation failed")
                    report["checks"]["minimal_generation"] = "PASS"
                    send(process, {"type": "SHUTDOWN", "protocol_version": "snowboard.llm/1"})
                    if read_frame(process.stdout, 2.0, validator).get("type") != "SHUTDOWN_ACK":
                        raise PiPacketFailure("SHUTDOWN acknowledgement missing")
                    report["checks"]["shutdown"] = "PASS"
                    process.wait(timeout=2.0)
                report["cleanup"] = stop(process)
                if report["cleanup"] != {"exit_code": 0, "waited": True, "term_sent": False, "kill_sent": False, "process_group_absent": True}:
                    raise PiPacketFailure("candidate cleanup failed")
                for name in ("exit", "orphan_zero", "cleanup"):
                    report["checks"][name] = "PASS"
                report["result"] = "PASS"
            except (PiPacketFailure, OSError, subprocess.SubprocessError, KeyError, ValueError) as exc:
                report["violations"].append(str(exc))
                report["result"] = "FAIL"
                if process is not None:
                    report["cleanup"] = stop(process)
            _validate_result(report, _repo_file(lock["artifacts"]["result_schema"]["path"], lock["artifacts"]["result_schema"]["sha256"]))
        aggregate["result"] = "PASS" if all(item["result"] == "PASS" for item in aggregate["candidates"]) else "FAIL"
    except (PiPacketFailure, OSError, subprocess.SubprocessError, KeyError, ValueError) as exc:
        aggregate["violations"].append(str(exc))
        aggregate["result"] = "INCONCLUSIVE"
    finally:
        aggregate["elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)
        if install_root.exists():
            shutil.rmtree(install_root)
        if raw_dir.exists():
            (raw_dir / "gate1-pi-sanitized.json").write_text(json.dumps(aggregate, sort_keys=True), encoding="utf-8")
        print(json.dumps(aggregate, sort_keys=True, separators=(",", ":")))
    return 0 if aggregate["result"] == "PASS" else 1 if aggregate["result"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
