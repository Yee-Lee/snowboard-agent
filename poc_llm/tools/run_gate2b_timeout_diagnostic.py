#!/usr/bin/env python3
"""Diagnose one Gate 2B LLM deadline without changing formal evidence or credit."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.gate2b_combined_v1 import canonical_sha256
from poc_llm.harness.litert_lm_child_adapter import LiteRtBackend
from poc_llm.harness.litert_lm_gate2b_child_adapter_v1 import gate2b_product_prompt
from poc_llm.harness.litert_lm_pi_child_adapter_v2 import load_pi_config_v2
from poc_llm.harness.m1_contract_boundary import normalize_response
from poc_llm.harness.pi_artifact_auth import streaming_digest
from poc_llm.harness.pi_runtime import group_absent, load, target_preflight
from poc_llm.tools.run_gate2b_pi_v1 import (
    TranscriptAsrDomain,
    audio_device_owner_count,
    load_audio_bindings,
    repo_artifact,
)


DIAGNOSTIC_ID = "G2B-P10B-TIMEOUT-DIAGNOSTIC-001"
SESSION_ID = "M4-SESSION-01"
NONCE = "G2BN0001"
TRAP = "G2BT0001"
FORMAL_TIMEOUT_SECONDS = 15.0


def request_value(transcript: str) -> dict[str, Any]:
    """Reproduce the immutable Attempt 003 first-session input exactly."""

    return {
        "perceptions": [{
            "kind": "listen",
            "status": "ok",
            "text": (
                transcript
                + f"\nReply briefly in spoken form and include current session marker {NONCE} "
                + f"exactly once. Never mention trap {TRAP} or an earlier session marker."
            ),
        }],
        "pending_message_count": 0,
        "capabilities": {
            "perceptions": ["listen"],
            "actions": ["speak"],
            "tools": [],
        },
    }


def sanitized_generation(
    backend: LiteRtBackend,
    config: dict[str, Any],
    value: dict[str, Any],
) -> dict[str, Any]:
    """Run to completion and retain metrics and digests, never private text."""

    prompt = gate2b_product_prompt(value)
    started = time.monotonic()
    generation = backend.generate(
        prompt,
        max_output_tokens=config["max_output_tokens"],
    )
    wall_ms = round((time.monotonic() - started) * 1000, 3)
    response, diagnostics = normalize_response(generation.text, value)
    speech = response.get("action_payload", {}).get("text")
    speech_value = speech if isinstance(speech, str) else ""
    metrics = dict(generation.metrics)
    return {
        "terminal": "RESULT",
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_chars": len(prompt),
        "prompt_bytes": len(prompt.encode("utf-8")),
        "input_sha256": canonical_sha256(value),
        "input_chars": len(json.dumps(
            value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )),
        "raw_output_sha256": hashlib.sha256(
            generation.text.encode("utf-8")
        ).hexdigest(),
        "raw_output_chars": len(generation.text),
        "response_sha256": canonical_sha256(response),
        "response_action_kind": response.get("action_kind"),
        "boundary_diagnostics": list(diagnostics),
        "current_marker_present_once": speech_value.count(NONCE) == 1,
        "current_trap_absent": TRAP not in speech_value,
        "metrics": metrics,
        "declared_max_input_tokens": config["max_input_tokens"],
        "declared_max_output_tokens": config["max_output_tokens"],
        "runtime_prefill_within_declared_input_limit": (
            metrics.get("prefill_tokens", 0) <= config["max_input_tokens"]
        ),
        "wall_ms": wall_ms,
        "formal_timeout_ms": FORMAL_TIMEOUT_SECONDS * 1000,
        "formal_deadline_overrun_ms": round(
            wall_ms - FORMAL_TIMEOUT_SECONDS * 1000, 3
        ),
        "completed_within_formal_deadline": (
            wall_ms <= FORMAL_TIMEOUT_SECONDS * 1000
        ),
    }


def worker_main(args: argparse.Namespace) -> int:
    try:
        payload = json.loads(sys.stdin.read())
        value = payload["value"]
        config, _receipt = load_pi_config_v2(
            args.config,
            args.config_sha256,
            args.config_schema,
            args.artifact_receipt,
            args.artifact_receipt_sha256,
            args.artifact_receipt_schema,
        )
        backend = LiteRtBackend(config)
        try:
            result = sanitized_generation(backend, config, value)
        finally:
            backend.close()
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except Exception as error:
        print(json.dumps({
            "terminal": "DIAGNOSTIC_ERROR",
            "error_type": type(error).__name__,
        }, sort_keys=True, separators=(",", ":")))
        return 2


async def acquire_transcript(
    *,
    bindings: dict[str, Any],
    audio_root: Path,
    record: dict[str, Any],
    vad_runtime_python: Path,
    vad_model: Path,
    asr_binary: Path,
    asr_model: Path,
    work_root: Path,
) -> tuple[dict[str, Any], dict[str, int], dict[str, bool]]:
    vad = bindings["PersistentVadDomain"](
        audio_root,
        vad_runtime_python,
        vad_model,
        work_root / "vad-bounded",
        120.0,
    )
    asr = TranscriptAsrDomain(bindings["PersistentAsrDomain"](
        asr_binary,
        asr_model,
        work_root / "asr",
        120.0,
    ))
    roots: dict[str, int] = {}
    stop_errors: list[str] = []
    try:
        await vad.start()
        vad_identity = vad.residency_identity()
        roots["vad"] = int(vad_identity["pid"])
        await asr.start()
        asr_identity = asr.residency_identity()
        roots["asr"] = int(asr_identity["pid"])

        vad_started = time.monotonic()
        vad_result = await vad.run(record)
        vad_wall_ms = round((time.monotonic() - vad_started) * 1000, 3)
        asr_started = time.monotonic()
        asr_result = await asr.run({
            **record,
            "bounded_wav": vad_result["bounded_wav"],
        })
        asr_wall_ms = round((time.monotonic() - asr_started) * 1000, 3)
        return {
            "transcript": asr_result["transcript"],
            "transcript_sha256": asr_result["transcript_sha256"],
            "transcript_chars": len(asr_result["transcript"]),
            "transcript_bytes": len(asr_result["transcript"].encode("utf-8")),
            "bounded_sha256": vad_result["bounded_sha256"],
            "vad_wall_ms": vad_wall_ms,
            "asr_wall_ms": asr_wall_ms,
            "asr_reported_latency_ms": asr_result["latency_ms"],
        }, roots, {}
    finally:
        for name, domain in (("asr", asr), ("vad", vad)):
            try:
                await domain.stop()
            except Exception:
                stop_errors.append(name)
        absence = {name: group_absent(pid) for name, pid in roots.items()}
        if stop_errors or not all(absence.values()):
            raise RuntimeError("Audio diagnostic cleanup failed")


def terminate_worker(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=2.0)
    except ProcessLookupError:
        pass


def run_worker(
    *,
    args: argparse.Namespace,
    install_root: Path,
    config: Path,
    config_sha256: str,
    config_schema: Path,
    receipt_schema: Path,
    value: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    argv = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--config", str(config),
        "--config-sha256", config_sha256,
        "--config-schema", str(config_schema),
        "--artifact-receipt", str(args.artifact_receipt),
        "--artifact-receipt-sha256", streaming_digest(args.artifact_receipt),
        "--artifact-receipt-schema", str(receipt_schema),
    ]
    process = subprocess.Popen(
        argv,
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        env={
            **os.environ,
            "PYTHONPATH": str(install_root),
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "NO_PROXY": "*",
        },
    )
    try:
        stdout, stderr = process.communicate(
            json.dumps({"value": value}, sort_keys=True, separators=(",", ":")),
            timeout=args.observation_timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        terminate_worker(process)
        return {
            "terminal": "OBSERVATION_TIMEOUT",
            "observation_timeout_seconds": args.observation_timeout_seconds,
        }, {
            "worker_exit_code": process.returncode,
            "process_group_absent": group_absent(process.pid),
        }
    finally:
        if process.poll() is None:
            terminate_worker(process)

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Diagnostic worker emitted invalid sanitized JSON") from error
    runtime_log = {
        "stderr_sha256": hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
        "prefill_profile_warning": "Failed to get prefill profile summary" in stderr,
        "native_cancel_observed": "Task cancelled" in stderr,
    }
    cleanup = {
        "worker_exit_code": process.returncode,
        "process_group_absent": group_absent(process.pid),
    }
    if process.returncode != 0 or cleanup["process_group_absent"] is not True:
        raise RuntimeError("Diagnostic worker failed or remained resident")
    result["runtime_log"] = runtime_log
    return result, cleanup


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--worker", action="store_true")
    value.add_argument("--config", type=Path)
    value.add_argument("--config-sha256")
    value.add_argument("--config-schema", type=Path)
    value.add_argument("--artifact-receipt", type=Path)
    value.add_argument("--artifact-receipt-sha256")
    value.add_argument("--artifact-receipt-schema", type=Path)
    value.add_argument("--packet-lock", type=Path)
    value.add_argument("--packet-lock-sha256")
    value.add_argument("--accepted-audio-entry", type=Path)
    value.add_argument("--execution-sha")
    value.add_argument("--audio-root", type=Path)
    value.add_argument("--audio-fixture-dir", type=Path)
    value.add_argument("--audio-fixture-lock", type=Path)
    value.add_argument("--audio-asr-binary", type=Path)
    value.add_argument("--audio-asr-model", type=Path)
    value.add_argument("--audio-vad-runtime-python", type=Path)
    value.add_argument("--audio-vad-model", type=Path)
    value.add_argument("--observation-timeout-seconds", type=float, default=60.0)
    return value


def require_parent_args(args: argparse.Namespace) -> None:
    required = (
        "packet_lock", "packet_lock_sha256", "accepted_audio_entry",
        "execution_sha", "artifact_receipt", "audio_root", "audio_fixture_dir",
        "audio_fixture_lock", "audio_asr_binary", "audio_asr_model",
        "audio_vad_runtime_python", "audio_vad_model",
    )
    if any(getattr(args, name) in {None, ""} for name in required):
        raise ValueError("Missing required diagnostic argument")
    if args.observation_timeout_seconds != 60.0:
        raise ValueError("The diagnostic observation watchdog is frozen at 60 seconds")


def main() -> int:
    args = parser().parse_args()
    if args.worker:
        return worker_main(args)
    report: dict[str, Any] = {
        "diagnostic_id": DIAGNOSTIC_ID,
        "formal_credit": False,
        "formal_attempt_mutated": False,
        "formal_attempt_id": "G2B-PI-COMBINED-003",
        "session_id": SESSION_ID,
        "result": "INCONCLUSIVE",
    }
    try:
        require_parent_args(args)
        if streaming_digest(args.packet_lock) != args.packet_lock_sha256:
            raise ValueError("Formal Gate 2B packet lock mismatch")
        lock = load(args.packet_lock)
        if lock.get("packet_id") != "G2B-PI-COMBINED-001":
            raise ValueError("Formal Gate 2B packet identity mismatch")
        artifacts = {name: repo_artifact(item) for name, item in lock["artifacts"].items()}
        accepted_path = artifacts["accepted_audio_entry"]
        if args.accepted_audio_entry.resolve() != accepted_path:
            raise ValueError("Accepted Audio entry path mismatch")
        accepted = load(accepted_path)
        if not Draft202012Validator(load(
            artifacts["accepted_audio_entry_schema"]
        )).is_valid(accepted):
            raise ValueError("Accepted Audio entry schema mismatch")
        environment = target_preflight(args.execution_sha)
        if audio_device_owner_count() != 0:
            raise ValueError("Pre-existing Audio device owner detected")

        candidate = lock["candidates"]["CAND-LRT-G4E2B-MOBILE-R1"]
        config = repo_artifact(candidate["product_config"])
        runtime = lock["runtime"]
        installer = artifacts["installer"]
        with tempfile.TemporaryDirectory(
            prefix="llm-poc-g2b-timeout-debug-", dir="/tmp"
        ) as directory:
            work_root = Path(directory)
            install_root = work_root / "install"
            install = subprocess.run(
                [
                    sys.executable, str(installer),
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
            if install.returncode != 0 or json.loads(install.stdout).get("result") != "PASS":
                raise RuntimeError("Offline diagnostic runtime install failed")

            bindings = load_audio_bindings(args.audio_root)
            fixture_lock = bindings["load_fixture_lock"](
                args.audio_fixture_lock,
                accepted["p9_combined_execution_sha"],
            )
            bindings["verify_fixture_files"](fixture_lock, args.audio_fixture_dir)
            record = fixture_lock["records"][0]
            if record.get("session_id") != SESSION_ID:
                raise ValueError("First Accepted Audio session identity mismatch")
            record = {
                **record,
                "wav_path": args.audio_fixture_dir / record["filename"],
            }
            audio, roots, _absence = asyncio.run(acquire_transcript(
                bindings=bindings,
                audio_root=args.audio_root,
                record=record,
                vad_runtime_python=args.audio_vad_runtime_python,
                vad_model=args.audio_vad_model,
                asr_binary=args.audio_asr_binary,
                asr_model=args.audio_asr_model,
                work_root=work_root,
            ))
            transcript = audio.pop("transcript")
            value = request_value(transcript)
            generation, worker_cleanup = run_worker(
                args=args,
                install_root=install_root,
                config=config,
                config_sha256=candidate["product_config"]["sha256"],
                config_schema=artifacts["product_config_schema"],
                receipt_schema=artifacts["artifact_receipt_schema"],
                value=value,
            )
            del transcript, value

        report.update({
            "execution_sha": args.execution_sha,
            "formal_packet_lock_sha256": args.packet_lock_sha256,
            "environment": {
                "machine": environment.get("machine"),
                "swap_total_bytes": environment.get("swap_total_bytes"),
                "routes_offline": environment.get("network", {}).get(
                    "routes_offline"
                ),
                "throttled_prelaunch": environment.get("throttled_prelaunch"),
            },
            "audio_input": {
                "fixture_id": record["fixture_id"],
                "fixture_sha256": record["sha256"],
                **audio,
            },
            "generation": generation,
            "cleanup": {
                "audio_process_groups_absent": {
                    name: group_absent(pid) for name, pid in roots.items()
                },
                "llm": worker_cleanup,
                "audio_device_owner_count": audio_device_owner_count(),
            },
        })
        report["result"] = "COMPLETE" if generation.get("terminal") == "RESULT" else "INCONCLUSIVE"
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
        return 0 if report["result"] == "COMPLETE" else 2
    except Exception as error:
        report["error_type"] = type(error).__name__
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
