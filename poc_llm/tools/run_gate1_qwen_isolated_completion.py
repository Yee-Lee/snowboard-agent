#!/usr/bin/env python3
"""Run the frozen Gate 1 Qwen workload first after a bounded Pi reboot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.pi_artifact_auth import streaming_digest
from poc_llm.harness.pi_runtime import load


PACKET_ID = "G1-QWEN-ISOLATED-COMPLETION-001"
BASE_PACKET_ID = "G1-PI-COMPAT-007"
QWEN_ID = "CAND-LRT-Q25-15B-Q8-R1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-lock", type=Path, required=True)
    parser.add_argument("--candidate-set", type=Path, required=True)
    parser.add_argument("--execution-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--max-prelaunch-uptime-s", type=float, default=900.0)
    return parser.parse_args()


def isolation_state(
    proc_root: Path = Path("/proc"), *, max_uptime_s: float = 900.0
) -> dict[str, Any]:
    uptime_s = float((proc_root / "uptime").read_text(encoding="ascii").split()[0])
    if uptime_s > max_uptime_s:
        raise RuntimeError("Pi reboot-age isolation bound exceeded")
    boot_id = (proc_root / "sys/kernel/random/boot_id").read_text(
        encoding="ascii"
    ).strip()
    if not boot_id:
        raise RuntimeError("Pi boot identity unavailable")
    adapter_processes = 0
    for command_path in proc_root.glob("[0-9]*/cmdline"):
        try:
            command = command_path.read_bytes().replace(b"\0", b" ")
        except OSError:
            continue
        if b"litert_lm_pi_child_adapter" in command:
            adapter_processes += 1
    if adapter_processes:
        raise RuntimeError("pre-existing LiteRT-LM adapter process detected")
    return {
        "boot_id_sha256": hashlib.sha256(boot_id.encode("ascii")).hexdigest(),
        "prelaunch_uptime_s": round(uptime_s, 3),
        "preexisting_adapter_processes": 0,
        "prior_candidate_workloads_in_run": 0,
        "candidate_id": QWEN_ID,
    }


def main() -> int:
    args = parse_args()
    result: dict[str, Any] = {
        "packet_id": PACKET_ID,
        "base_packet_id": BASE_PACKET_ID,
        "run_id": args.run_id,
        "execution_sha": args.execution_sha,
        "execution_surface_sha256": "",
        "isolation": {},
        "inner_result_sha256": "",
        "candidate_run": {},
        "violations": [],
        "result": "INCONCLUSIVE",
    }
    output_root = args.evidence_root / args.run_id
    inner_root = args.evidence_root / "candidate-run"
    try:
        if output_root.exists() or (inner_root / args.run_id).exists():
            raise RuntimeError("isolated completion evidence path already exists")
        lock = load(args.packet_lock)
        if lock.get("packet_id") != BASE_PACKET_ID:
            raise RuntimeError("isolated completion lock base packet mismatch")
        result["execution_surface_sha256"] = streaming_digest(args.packet_lock)
        wrapper = lock.get("artifacts", {}).get("isolation_wrapper", {})
        if (
            wrapper.get("path") != "poc_llm/tools/run_gate1_qwen_isolated_completion.py"
            or streaming_digest(ROOT / wrapper["path"]) != wrapper.get("sha256")
        ):
            raise RuntimeError("isolated completion wrapper identity mismatch")
        candidates = load(args.candidate_set)
        if (
            candidates.get("packet_id") != BASE_PACKET_ID
            or [item.get("candidate_id") for item in candidates.get("candidates", [])]
            != [QWEN_ID]
        ):
            raise RuntimeError("isolated completion candidate set mismatch")
        result["isolation"] = isolation_state(
            max_uptime_s=args.max_prelaunch_uptime_s
        )

        runner = ROOT / lock["artifacts"]["runner"]["path"]
        command = [
            sys.executable,
            str(runner),
            "--packet-lock",
            str(args.packet_lock),
            "--candidate-set",
            str(args.candidate_set),
            "--execution-sha",
            args.execution_sha,
            "--run-id",
            args.run_id,
            "--evidence-root",
            str(inner_root),
        ]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=900,
            env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
        )
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("isolated candidate runner emitted no result")
        candidate_run = json.loads(lines[-1])
        result["candidate_run"] = candidate_run
        inner_result = inner_root / args.run_id / "gate1-pi-v7-sanitized.json"
        if not inner_result.is_file():
            raise RuntimeError("isolated candidate sanitized result missing")
        result["inner_result_sha256"] = streaming_digest(inner_result)
        if (
            candidate_run.get("execution_surface_sha256")
            != result["execution_surface_sha256"]
            or [item.get("candidate_id") for item in candidate_run.get("candidates", [])]
            != [QWEN_ID]
        ):
            raise RuntimeError("isolated candidate result identity mismatch")
        result["result"] = candidate_run.get("result", "INCONCLUSIVE")
        if completed.returncode not in {0, 1, 2}:
            raise RuntimeError("isolated candidate runner exited unexpectedly")
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.SubprocessError, RuntimeError) as exc:
        result["violations"].append(f"{type(exc).__name__}: {exc}")
        result["result"] = "INCONCLUSIVE"
    finally:
        output_root.mkdir(parents=True, exist_ok=True)
        schema_item: dict[str, str] | None = None
        try:
            schema_item = load(args.packet_lock)["artifacts"]["completion_result_schema"]
            schema_path = ROOT / schema_item["path"]
            if streaming_digest(schema_path) != schema_item["sha256"]:
                raise RuntimeError("completion result schema identity mismatch")
            errors = list(Draft202012Validator(load(schema_path)).iter_errors(result))
            if errors:
                result["violations"].append("completion result schema validation failed")
                result["result"] = "INCONCLUSIVE"
        except (OSError, ValueError, KeyError, RuntimeError):
            result["violations"].append("completion result schema unavailable")
            result["result"] = "INCONCLUSIVE"
        (output_root / "qwen-isolated-sanitized.json").write_text(
            json.dumps(result, sort_keys=True), encoding="utf-8"
        )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["result"] == "PASS" else 1 if result["result"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
