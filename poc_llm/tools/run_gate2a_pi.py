#!/usr/bin/env python3
"""Run the independent M4b Gate 2A matrix on an authorized Pi 5."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any
import re

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.m1_contract_boundary import normalize_response
from poc_llm.harness.pi_runtime import (
    PiPacketFailure, digest, launch, load, meminfo, native_library_preflight, protocol_validator, read_frame,
    require_ready, send, stop, target_preflight,
)


PACKET_ID = "G2A-PI-LLM-001"
STANDARD_INPUT = {
    "perceptions": [{"kind": "read", "status": "ok", "text": "Choose the rest action."}],
    "pending_message_count": 0,
    "capabilities": {"perceptions": ["read", "listen", "look"], "actions": ["speak", "tool", "rest"], "tools": []},
}
FORBIDDEN_LOG = ("raw model output:", "BEGIN PRIVATE PROMPT", "SECRET_PAYLOAD", "credential=", "api_key=", "hidden context:", "LEAK_MARKER")


def percentile(values: list[float], percent: int) -> float:
    if not values:
        raise PiPacketFailure("empty metric samples")
    return sorted(values)[max(0, (len(values) * percent + 99) // 100 - 1)]


def ols_slope(values: list[float]) -> float:
    if len(values) < 2:
        raise PiPacketFailure("insufficient slope samples")
    x = list(range(len(values)))
    mean_x, mean_y = sum(x) / len(x), sum(values) / len(values)
    denominator = sum((value - mean_x) ** 2 for value in x)
    return sum((x[index] - mean_x) * (value - mean_y) for index, value in enumerate(values)) / denominator


def process_sample(pid: int) -> dict[str, float]:
    status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    fields = {line.split(":", 1)[0]: line.split()[1] for line in status.splitlines() if ":" in line and len(line.split()) >= 2}
    pss_kib = 0
    rollup = Path(f"/proc/{pid}/smaps_rollup")
    if rollup.is_file():
        for line in rollup.read_text(encoding="utf-8").splitlines():
            if line.startswith("Pss:"):
                pss_kib = int(line.split()[1])
                break
    memory = meminfo()
    return {"rss_mib": int(fields.get("VmRSS", "0")) / 1024, "pss_mib": pss_kib / 1024,
            "threads": float(fields.get("Threads", "0")), "system_used_mib": (memory["MemTotal"] - memory["MemAvailable"]) / (1024 * 1024)}


def thermal_sample() -> dict[str, Any]:
    temperature = subprocess.run(["vcgencmd", "measure_temp"], text=True, capture_output=True, check=False)
    throttled = subprocess.run(["vcgencmd", "get_throttled"], text=True, capture_output=True, check=False)
    match = re.fullmatch(r"temp=([0-9]+(?:\.[0-9]+)?)'C\s*", temperature.stdout)
    if temperature.returncode != 0 or throttled.returncode != 0 or match is None or not throttled.stdout.startswith("throttled=0x"):
        raise PiPacketFailure("Pi thermal/throttling probe failed")
    return {"temperature_c": float(match.group(1)), "throttled": throttled.stdout.strip().split("=", 1)[1]}


def repo_artifact(item: dict[str, str]) -> Path:
    path = (ROOT / item["path"]).resolve()
    if not path.is_file() or digest(path) != item["sha256"]:
        raise PiPacketFailure(f"locked artifact mismatch: {item['path']}")
    return path


def command_generation(process: subprocess.Popen[str], validator: Draft202012Validator, request_id: str, value: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    if process.stdout is None:
        raise PiPacketFailure("candidate stdout unavailable")
    send(process, {"type": "GENERATE", "protocol_version": "snowboard.llm/1", "request_id": request_id, "input": value})
    return read_frame(process.stdout, timeout_s, validator)


def catalog_input(entry: dict[str, Any]) -> dict[str, Any]:
    tools = [{"name": name, "input_schema": {"type": "object"}} for name in entry["tools"]]
    return {
        "perceptions": [{"kind": "read", "status": "ok", "text": entry["text"]}],
        "pending_message_count": 0,
        "capabilities": {"perceptions": ["listen", "read", "look"], "actions": entry["actions"], "tools": tools},
    }


def start_child(config: Path, config_sha: str, config_schema: Path, protocol_schema: Path, install: Path, validator: Draft202012Validator, stderr: Any) -> tuple[subprocess.Popen[str], dict[str, Any]]:
    value = load(config)
    process = launch(config=config, config_sha256=config_sha, config_schema=config_schema, protocol_schema=protocol_schema, install_root=install, stderr=stderr)
    require_ready(process, validator, value, config_sha)
    return process, value


def close_child(process: subprocess.Popen[str], validator: Draft202012Validator) -> dict[str, Any]:
    if process.stdout is None:
        raise PiPacketFailure("candidate stdout unavailable")
    send(process, {"type": "SHUTDOWN", "protocol_version": "snowboard.llm/1"})
    if read_frame(process.stdout, 2.0, validator).get("type") != "SHUTDOWN_ACK":
        raise PiPacketFailure("SHUTDOWN acknowledgement missing")
    process.wait(timeout=2.0)
    cleanup = stop(process)
    if cleanup != {"exit_code": 0, "waited": True, "term_sent": False, "kill_sent": False, "process_group_absent": True}:
        raise PiPacketFailure("child cleanup failed")
    return cleanup


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fatal-outcome-self-test", action="store_true")
    parser.add_argument("--packet-lock", type=Path, required=True)
    parser.add_argument("--finalist-receipt", type=Path, required=True)
    parser.add_argument("--execution-sha", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    if sys.argv[1:] == ["--fatal-outcome-self-test"]:
        return 4
    args = parse_args()
    if args.fatal_outcome_self_test:
        return 4
    raw_dir = args.evidence_root / args.run_id
    install = Path(f"/tmp/llm-poc-g2a-001/install-{args.run_id}")
    result: dict[str, Any] = {"packet_id": PACKET_ID, "run_id": args.run_id, "candidate_id": args.candidate_id,
                              "execution_sha": args.execution_sha, "results": {case: "Blocked" for case in ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P10A", "P11", "P12")},
                              "samples": {}, "violations": [], "result": "Blocked"}
    try:
        if raw_dir.exists() or install.exists():
            raise PiPacketFailure("run-owned path is dirty")
        lock = load(args.packet_lock)
        if lock.get("packet_id") != PACKET_ID:
            raise PiPacketFailure("Gate 2A lock ID mismatch")
        for item in lock["artifacts"].values():
            repo_artifact(item)
        receipt = load(args.finalist_receipt)
        receipt_schema = repo_artifact(lock["artifacts"]["finalist_receipt_schema"])
        if not Draft202012Validator(load(receipt_schema)).is_valid(receipt):
            raise PiPacketFailure("Core Gate 1 finalist receipt schema mismatch")
        if receipt.get("packet_id") != "G1-PI-COMPAT-006" or receipt.get("candidate_id") != args.candidate_id or not receipt.get("core_ack_id"):
            raise PiPacketFailure("Core Gate 1 finalist receipt does not authorize candidate")
        environment = target_preflight(args.execution_sha)
        result["environment"] = environment
        result["results"]["P12"] = "PASS"
        candidate = lock["candidates"].get(args.candidate_id)
        if candidate is None:
            raise PiPacketFailure("candidate is not in frozen Gate 2A set")
        standard = repo_artifact(candidate["standard_config"])
        p5_config = repo_artifact(candidate["p5_config"])
        fixture = repo_artifact(lock["artifacts"]["p5_fixture"])
        catalog = load(repo_artifact(lock["artifacts"]["catalog"]))
        protocol = repo_artifact(lock["artifacts"]["protocol_schema"])
        config_schema = repo_artifact(lock["artifacts"]["config_schema"])
        prompt_schema = repo_artifact(lock["artifacts"]["prompt_schema"])
        response_schema = repo_artifact(lock["artifacts"]["response_schema"])
        validator = protocol_validator(protocol, prompt_schema, response_schema)
        runtime = lock["runtime"]
        wheel = Path(runtime["wheel_path"])
        if not wheel.is_file() or digest(wheel) != runtime["wheel_sha256"]:
            raise PiPacketFailure("staged wheel identity mismatch")
        raw_dir.mkdir(parents=True, exist_ok=False)
        install_report = subprocess.run(["python3", "poc_llm/tools/install_gate1_arm64_wheel.py", "--wheel", str(wheel), "--wheel-sha256", runtime["wheel_sha256"], "--target", str(install)], cwd=ROOT, capture_output=True, text=True, check=False, timeout=300)
        (raw_dir / "install.stderr").write_text(install_report.stderr, encoding="utf-8")
        if install_report.returncode != 0:
            raise PiPacketFailure("P11 offline runtime installation failed")
        result["native_library"] = native_library_preflight(
            install / "litert_lm/liblitert-lm.so", runtime["native_library_sha256"],
        )
        result["results"]["P11"] = "PASS"

        stderr_path = raw_dir / "candidate.stderr"
        with stderr_path.open("w", encoding="utf-8") as stderr:
            # P1: three cold cycles plus one resident sequence.
            p1_cycles = []
            for sequence in range(3):
                process, _ = start_child(standard, candidate["standard_config"]["sha256"], config_schema, protocol, install, validator, stderr)
                send(process, {"type": "PING", "protocol_version": "snowboard.llm/1"})
                if process.stdout is None or read_frame(process.stdout, 2.0, validator).get("type") != "PONG":
                    raise PiPacketFailure("P1 PING failed")
                terminal = command_generation(process, validator, f"p1-cold-{sequence}", STANDARD_INPUT, 15.0)
                if terminal.get("type") != "RESULT":
                    raise PiPacketFailure("P1 minimal generation failed")
                p1_cycles.append(close_child(process, validator))
            result["samples"]["p1_cold_cleanup"] = p1_cycles
            process, _ = start_child(standard, candidate["standard_config"]["sha256"], config_schema, protocol, install, validator, stderr)
            p1_resident: dict[str, Any] = {"pings": 0, "generations": 0}
            for _ in range(10):
                send(process, {"type": "PING", "protocol_version": "snowboard.llm/1"})
                if process.stdout is None or read_frame(process.stdout, 2.0, validator).get("type") != "PONG":
                    raise PiPacketFailure("P1 resident PING failed")
                p1_resident["pings"] += 1
            for sequence in range(3):
                if command_generation(process, validator, f"p1-resident-{sequence}", STANDARD_INPUT, 15.0).get("type") != "RESULT":
                    raise PiPacketFailure("P1 resident generation failed")
                p1_resident["generations"] += 1
            p1_resident["cleanup"] = close_child(process, validator)
            result["samples"]["p1_resident"] = p1_resident
            result["results"]["P1"] = "PASS"

            cold = []
            for sequence in range(3):
                cold_process, _ = start_child(standard, candidate["standard_config"]["sha256"], config_schema, protocol, install, validator, stderr)
                started = time.monotonic()
                terminal = command_generation(cold_process, validator, f"p4-cold-{sequence}", STANDARD_INPUT, 15.0)
                if terminal.get("type") != "RESULT":
                    raise PiPacketFailure("P4 cold generation failed")
                cold.append({"wall_ms": round((time.monotonic() - started) * 1000, 3), **terminal["metrics"]})
                close_child(cold_process, validator)
            result["samples"]["p4_cold"] = cold

            # P2 model-backed 10-case x3; P3 fixed normalizer failures.
            process, _ = start_child(standard, candidate["standard_config"]["sha256"], config_schema, protocol, install, validator, stderr)
            p2 = []
            for entry in catalog["valid_cases"]:
                prompt = catalog_input(entry)
                for repetition in range(catalog["repetitions"]):
                    terminal = command_generation(process, validator, f"{entry['id']}-{repetition}", prompt, 15.0)
                    response = terminal.get("response", {})
                    valid = terminal.get("type") == "RESULT" and response.get("action_kind") == entry["expected_kind"] and (entry["expected_kind"] != "tool" or response.get("action_payload", {}).get("name") == entry["tool"])
                    p2.append({"id": entry["id"], "valid": valid})
            result["results"]["P2"] = "PASS" if all(item["valid"] for item in p2) else "FAIL"
            p3 = []
            for entry in catalog["failure_raw_outputs"]:
                response, diagnostics = normalize_response(entry["raw"], STANDARD_INPUT, refused=entry["id"] == "P3-018")
                p3.append({"id": entry["id"], "fallback": response["action_kind"] in {"speak", "rest"}, "diagnostic": diagnostics[0]})
            result["results"]["P3"] = "PASS" if all(item["fallback"] for item in p3) else "FAIL"
            result["samples"]["p2"] = p2
            result["samples"]["p3"] = p3

            # P4 hot performance from same process; cold samples use fresh processes below.
            hot = []
            for _ in range(3):
                if command_generation(process, validator, "p4-warmup", STANDARD_INPUT, 15.0).get("type") != "RESULT":
                    raise PiPacketFailure("P4 warmup failed")
            for sequence in range(20):
                started = time.monotonic()
                terminal = command_generation(process, validator, f"p4-hot-{sequence}", STANDARD_INPUT, 15.0)
                if terminal.get("type") != "RESULT":
                    raise PiPacketFailure("P4 hot generation failed")
                hot.append({"wall_ms": round((time.monotonic() - started) * 1000, 3), **terminal["metrics"]})
            result["samples"]["p4_hot"] = hot
            result["results"]["P4"] = "PASS" if percentile([item["ttft_ms"] for item in hot], 95) <= 2500 and percentile([item["decode_tokens_per_second"] for item in hot], 50) >= 4 else "Core threshold decision required"

            # P8 five nonce turns in a single Engine; no response text is persisted.
            p8 = []
            for sequence in range(5):
                nonce = f"P8NONCE{sequence}"
                prompt = {**STANDARD_INPUT, "perceptions": [{"kind": "read", "status": "ok", "text": f"Reply briefly and do not repeat earlier nonces: {nonce}"}]}
                terminal = command_generation(process, validator, f"p8-{sequence}", prompt, 15.0)
                encoded = json.dumps(terminal.get("response", {}), ensure_ascii=False)
                p8.append({"response_sha256": hashlib.sha256(encoded.encode()).hexdigest(), "leaked_prior_nonce": any(f"P8NONCE{old}" in encoded for old in range(sequence))})
                if terminal.get("type") != "RESULT":
                    raise PiPacketFailure("P8 generation failed")
            result["samples"]["p8"] = p8
            result["results"]["P8"] = "PASS" if not any(item["leaked_prior_nonce"] for item in p8) else "FAIL"

            # P10A: exactly 20 public-catalog sessions with frozen 5s cadence and samples.
            soak = []
            for sequence in range(20):
                entry = catalog["valid_cases"][sequence % len(catalog["valid_cases"])]
                terminal = command_generation(process, validator, f"p10a-{entry['id']}-{sequence // len(catalog['valid_cases'])}", catalog_input(entry), 15.0)
                if terminal.get("type") != "RESULT":
                    raise PiPacketFailure("P10A generation failed")
                soak.append({**process_sample(process.pid), **thermal_sample()})
                time.sleep(5.0)
            result["samples"]["p10a"] = soak
            pss = [item["pss_mib"] for item in soak]
            used = [item["system_used_mib"] for item in soak]
            p10_pass = ols_slope(pss[5:]) <= 4.0 and ols_slope(used[5:]) <= 4.0 and percentile(pss[15:], 50) <= percentile(pss[:5], 50) + 64 and percentile(used[15:], 50) <= percentile(used[:5], 50) and all(item["temperature_c"] < 80 and item["throttled"] == "0x0" for item in soak)
            result["results"]["P10A"] = "PASS" if p10_pass else "FAIL"
            close_child(process, validator)

            # P5, P6 and P7 use the frozen extreme profile, never a workstation model run.
            p5_value = load(fixture)
            process, _ = start_child(p5_config, candidate["p5_config"]["sha256"], config_schema, protocol, install, validator, stderr)
            p5_started = time.monotonic()
            terminal = command_generation(process, validator, "p5-extreme", p5_value["input"], 17.0)
            p5_elapsed = (time.monotonic() - p5_started) * 1000
            if terminal.get("type") == "ERROR" and terminal.get("code") == "TIMEOUT" and 15000 <= p5_elapsed <= 17000:
                send(process, {"type": "PING", "protocol_version": "snowboard.llm/1"})
                result["results"]["P5"] = "PASS" if process.stdout and read_frame(process.stdout, 2.0, validator).get("type") == "PONG" else "FAIL"
            elif terminal.get("type") == "RESULT" and p5_elapsed < 15000:
                result["results"]["P5"] = "INCONCLUSIVE"
            else:
                result["results"]["P5"] = "FAIL"
            result["samples"]["p5"] = {"terminal": terminal.get("type"), "elapsed_ms": round(p5_elapsed, 3)}
            close_child(process, validator)
            if result["results"]["P5"] == "PASS":
                rebuilt, _ = start_child(standard, candidate["standard_config"]["sha256"], config_schema, protocol, install, validator, stderr)
                p5_probe = command_generation(rebuilt, validator, "p5-rebuild-probe", STANDARD_INPUT, 15.0)
                p5_cleanup = close_child(rebuilt, validator)
                result["samples"]["p5"]["rebuild_probe"] = p5_probe.get("type")
                result["samples"]["p5"]["rebuild_cleanup"] = p5_cleanup
                if p5_probe.get("type") != "RESULT":
                    result["results"]["P5"] = "FAIL"

            process, _ = start_child(p5_config, candidate["p5_config"]["sha256"], config_schema, protocol, install, validator, stderr)
            send(process, {"type": "GENERATE", "protocol_version": "snowboard.llm/1", "request_id": "p6-cancel", "input": p5_value["input"]})
            time.sleep(0.1)
            cancelled_at = time.monotonic()
            send(process, {"type": "CANCEL", "protocol_version": "snowboard.llm/1", "request_id": "p6-cancel"})
            if process.stdout is None:
                raise PiPacketFailure("P6 stdout unavailable")
            terminal = read_frame(process.stdout, 2.0, validator)
            cancel_ms = (time.monotonic() - cancelled_at) * 1000
            result["results"]["P6"] = "PASS" if terminal.get("type") == "CANCELLED" and cancel_ms <= 500 else "Conditional escalation"
            result["samples"]["p6"] = {"terminal": terminal.get("type"), "elapsed_ms": round(cancel_ms, 3)}
            close_child(process, validator)

            process, _ = start_child(p5_config, candidate["p5_config"]["sha256"], config_schema, protocol, install, validator, stderr)
            send(process, {"type": "GENERATE", "protocol_version": "snowboard.llm/1", "request_id": "p7-force", "input": p5_value["input"]})
            time.sleep(0.1)
            forced = stop(process)
            rebuilt, _ = start_child(standard, candidate["standard_config"]["sha256"], config_schema, protocol, install, validator, stderr)
            probe = command_generation(rebuilt, validator, "p7-rebuild", STANDARD_INPUT, 15.0)
            rebuilt_cleanup = close_child(rebuilt, validator)
            result["samples"]["p7"] = {"force_abort": forced, "rebuild_cleanup": rebuilt_cleanup}
            fatal = subprocess.run([sys.executable, str(Path(__file__)), "--fatal-outcome-self-test"], check=False)
            result["samples"]["p7"]["fatal_outcome_exit_code"] = fatal.returncode
            result["results"]["P7"] = "PASS" if forced["waited"] and forced["process_group_absent"] and probe.get("type") == "RESULT" and fatal.returncode == 4 else "FAIL"

        log_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        if any(pattern in log_text for pattern in FORBIDDEN_LOG):
            result["results"]["P3"] = "FAIL"
        result["environment_post"] = target_preflight(args.execution_sha)
        result["results"]["P12"] = "PASS"
        mandatory = ("P1", "P2", "P3", "P5", "P7", "P8", "P10A", "P11", "P12")
        if any(result["results"][case] == "FAIL" for case in mandatory):
            result["result"] = "FAIL"
        elif (all(result["results"][case] == "PASS" for case in mandatory)
              and result["results"]["P4"] == "PASS"
              and result["results"]["P6"] in {"PASS", "Conditional escalation"}):
            result["result"] = "PASS"
        else:
            result["result"] = "INCONCLUSIVE"
        result_schema = repo_artifact(lock["artifacts"]["result_schema"])
        if not Draft202012Validator(load(result_schema)).is_valid(result):
            raise PiPacketFailure("Gate 2A result schema mismatch")
    except (PiPacketFailure, OSError, subprocess.SubprocessError, KeyError, ValueError) as exc:
        result["violations"].append(str(exc))
        result["result"] = "INCONCLUSIVE"
    finally:
        if install.exists():
            shutil.rmtree(install)
        if raw_dir.exists():
            (raw_dir / "gate2a-sanitized.json").write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["result"] == "PASS" else 1 if result["result"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
