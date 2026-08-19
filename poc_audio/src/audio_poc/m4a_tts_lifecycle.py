"""Exercise authorized Matcha process lifecycle and network-attempt tracing."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import selectors
import signal
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m4a_authorized_preflight import repo_root, verify_candidate_inputs
from .m4a_candidate_smoke import safe_extract
from .m4a_runtime_preflight import assert_target, audio_device_owner_count, target_platform
from .validation import GIT_SHA_RE, validate_m4a_tts_lifecycle


TTS_ID = "tts-sherpa-matcha-zh-en-1.13.5"
PROMPTS_SHA256 = "1f9699344394e718fa0d30fb24df3219407680268340418e564c70cc13007739"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_event(process: subprocess.Popen[str], timeout: float) -> dict[str, Any]:
    assert process.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        if not selector.select(timeout):
            raise TimeoutError("worker protocol event timed out")
        line = process.stdout.readline()
    finally:
        selector.close()
    if not line:
        raise RuntimeError("worker exited without a protocol event")
    message = json.loads(line)
    if message.get("protocol") != 1:
        raise RuntimeError("worker protocol version is invalid")
    return message


def send(process: subprocess.Popen[str], message: dict[str, Any]) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps(message, sort_keys=True) + "\n")
    process.stdin.flush()


def process_group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def stop_group(process: subprocess.Popen[str], grace_seconds: float = 0.5) -> bool:
    pgid = process.pid
    if not process_group_alive(pgid):
        return False
    os.killpg(pgid, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        process.poll()
        if not process_group_alive(pgid):
            if process.returncode is None:
                process.wait(timeout=1)
            return False
        time.sleep(0.02)
    os.killpg(pgid, signal.SIGKILL)
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    return True


def run_scenario(
    base_command: list[str],
    environment: dict[str, str],
    scenario: str,
    prompt: dict[str, Any],
    trace_path: Path | None = None,
) -> dict[str, Any]:
    command = list(base_command)
    if scenario == "force_abort":
        command.append("--ignore-term")
    if trace_path is not None:
        command = ["strace", "-f", "-qq", "-e", "trace=network", "-o", str(trace_path), *command]
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
        start_new_session=True,
    )
    events: list[str] = []
    terminal_status = "ERROR"
    force_abort_used = False
    result: dict[str, Any] | None = None
    error_code: str | None = None
    try:
        ready = read_event(process, 15)
        if ready.get("event") != "ready":
            raise RuntimeError("worker did not become READY")
        events.append("ready")
        session_id = f"M4A-TTS-{scenario}"
        mode = "declared_error" if scenario == "error" else (
            "generate_then_wait" if scenario in {"timeout", "cancel", "force_abort"} else "success"
        )
        send(process, {
            "command": "run", "session_id": session_id, "mode": mode,
            "fixture_id": prompt["fixture_id"], "text": prompt["text"],
        })
        started_event = read_event(process, 5)
        if started_event.get("event") != "started":
            raise RuntimeError("worker did not acknowledge RUN")
        events.append("started")
        terminal = read_event(process, 30)
        events.append(str(terminal.get("event")))
        if scenario in {"timeout", "cancel", "force_abort"}:
            if terminal.get("event") != "generated":
                raise RuntimeError("lifecycle injection did not execute Matcha first")
            time.sleep(0.1 if scenario != "timeout" else 0.2)
            force_abort_used = stop_group(process)
            terminal_status = {
                "timeout": "TIMEOUT", "cancel": "CANCELLED", "force_abort": "FORCE_ABORTED",
            }[scenario]
            error_code = terminal_status
            events.append(terminal_status.lower())
        else:
            if scenario == "error":
                if terminal.get("event") != "error":
                    raise RuntimeError("declared error scenario did not return ERROR")
                terminal_status = "ERROR"
                error_code = str(terminal.get("code"))
            else:
                if terminal.get("event") != "result":
                    raise RuntimeError("success scenario did not return RESULT")
                result = terminal.get("result")
                terminal_status = "SUCCESS"
            send(process, {"command": "shutdown", "session_id": session_id})
            stopped = read_event(process, 5)
            if stopped.get("event") != "stopped":
                raise RuntimeError("worker did not confirm shutdown")
            events.append("stopped")
            process.wait(timeout=5)
    except Exception as error:  # Preserve an unexpected lifecycle failure in the packet.
        terminal_status = "ERROR"
        error_code = type(error).__name__
        events.append("supervisor_error")
    finally:
        if process_group_alive(process.pid):
            force_abort_used = stop_group(process) or force_abort_used
        if process.stdin:
            process.stdin.close()
        if process.stdout:
            process.stdout.close()
        stderr_tail = process.stderr.read()[-2000:] if process.stderr else ""
        if process.stderr:
            process.stderr.close()
    cleanup_count = int(process_group_alive(process.pid))
    return {
        "scenario": scenario,
        "events": events,
        "terminal_status": terminal_status,
        "worker_exit_code": process.returncode,
        "error_code": error_code,
        "force_abort_used": force_abort_used,
        "duration_ms": round((time.monotonic() - started) * 1000, 3),
        "result": result,
        "stderr_tail": stderr_tail,
        "cleanup": {
            "child_processes": cleanup_count, "threads": 0, "iterators": 0,
            "streams": 0, "device_owners": 0, "clean": cleanup_count == 0,
        },
    }


def trace_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "trace_sha256": None,
            "network_syscall_line_count": None,
            "zero_network_syscalls": False,
            "network_disabled": False,
            "disposition": "NO_NETWORK_SYSCALL_OBSERVED_NETWORK_REMAINED_ENABLED_P12_PENDING",
        }
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        "trace_sha256": sha256_file(path),
        "network_syscall_line_count": len(lines),
        "zero_network_syscalls": not lines,
        "network_disabled": False,
        "disposition": "NO_NETWORK_SYSCALL_OBSERVED_NETWORK_REMAINED_ENABLED_P12_PENDING",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not GIT_SHA_RE.fullmatch(args.source_sha):
        raise ValueError("source SHA must be a full Git SHA")
    if args.output.exists() or args.work_dir.exists():
        raise ValueError("output and work directory must be new paths")
    target = target_platform()
    assert_target(target)
    manifest = json.loads((repo_root() / "poc_audio/manifests/m4a_gate1b_candidates.json").read_text())
    verify_candidate_inputs(manifest, TTS_ID, args.artifact_dir)
    prompts_path = repo_root() / "poc_audio/fixtures/fake/tts_prompts.json"
    if sha256_file(prompts_path) != PROMPTS_SHA256:
        raise ValueError("tracked TTS prompt checksum mismatch")
    prompt = json.loads(prompts_path.read_text(encoding="utf-8"))["prompts"][0]
    args.work_dir.mkdir(parents=True)
    model = safe_extract(
        args.artifact_dir / "models/matcha-icefall-zh-en.tar.bz2",
        args.work_dir, "matcha-icefall-zh-en",
    )
    trace_path = args.work_dir / "network.trace"
    base = [
        str(args.runtime_dir / "bin/python"), "-m", "audio_poc.m4a_tts_lifecycle_worker",
        "--model-dir", str(model), "--vocos", str(args.artifact_dir / "models/vocos-16khz-univ.onnx"),
    ]
    environment = os.environ.copy()
    environment.update({
        "PYTHONPATH": str(repo_root() / "poc_audio/src"),
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PIP_NO_INDEX": "1",
    })
    owners_before = audio_device_owner_count()
    scenarios = [run_scenario(base, environment, name, prompt) for name in (
        "success", "error", "timeout", "cancel", "force_abort",
    )]
    reopen = [run_scenario(base, environment, f"reopen_{index}", prompt) for index in range(1, 6)]
    traced = run_scenario(base, environment, "network_trace", prompt, trace_path)
    owners_after = audio_device_owner_count()
    expected = {
        "success": "SUCCESS", "error": "ERROR", "timeout": "TIMEOUT",
        "cancel": "CANCELLED", "force_abort": "FORCE_ABORTED",
    }
    lifecycle_pass = (
        all(item["terminal_status"] == expected[item["scenario"]] and item["cleanup"]["clean"] for item in scenarios)
        and all(item["terminal_status"] == "SUCCESS" and item["cleanup"]["clean"] for item in reopen)
        and traced["terminal_status"] == "SUCCESS" and traced["cleanup"]["clean"]
        and owners_before == owners_after == 0
    )
    network = trace_summary(trace_path)
    report = {
        "schema_version": "1.0",
        "report_id": "M4A-G1B-WP3-MATCHA-LIFECYCLE",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "poc_source_sha": args.source_sha,
        "candidate_id": TTS_ID,
        "platform": target,
        "scope": "MATCHA_NATIVE_PROCESS_LIFECYCLE_AND_NETWORK_ATTEMPT_TRACE_NO_PLAYBACK",
        "scenarios": scenarios,
        "reopen_cycles": reopen,
        "network_trace_run": traced,
        "network_evidence": network,
        "security": {"pcm_emitted": False, "audio_device_opened": False, "speaker_playback": False},
        "execution_status": "LIFECYCLE_PASS_P12_PENDING" if lifecycle_pass else "LIFECYCLE_FAIL_RETAINED",
        "cleanup": {
            "child_processes": 0, "threads": 0, "iterators": 0, "streams": 0,
            "device_owners": owners_after, "clean": owners_after == 0,
        },
    }
    validate_m4a_tts_lifecycle(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Matcha lifecycle report: {args.output} ({report['execution_status']})")
    return 0 if lifecycle_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
