"""Strict syscall-level offline-closure audit for an M1 candidate command."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from .m1_baseline import (
    _output_digest,
    _repo_root,
    _resource_fields,
    _row,
    _verify_external,
    run_monitored,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _network_syscall_lines(trace: Path) -> list[str]:
    lines = trace.read_text(encoding="utf-8", errors="replace").splitlines()
    return [line for line in lines if line.strip()]


def run_offline_audit(
    candidate_id: str,
    trace_path: Path,
    command: list[str],
) -> dict[str, object]:
    """Trace every network syscall and fail closed on any observed call."""

    if not command:
        raise ValueError("audited command must not be empty")
    repo_root = _repo_root()
    trace = _verify_external(trace_path, repo_root, "offline trace")
    if trace.exists():
        raise FileExistsError("offline trace already exists")
    if not trace.parent.is_dir():
        raise FileNotFoundError("offline trace parent does not exist")
    strace = shutil.which("strace")
    if strace is None:
        raise RuntimeError("strace is required for syscall-level offline audit")

    method, selected = _row(candidate_id)
    run = run_monitored(
        [
            strace,
            "-f",
            "-qq",
            "-e",
            "trace=network",
            "-o",
            str(trace),
            "--",
            *command,
        ],
        selected["command"]["timeout_seconds"],
        repo_root,
    )
    if not trace.is_file():
        syscall_count = None
        trace_sha256 = None
    else:
        syscall_count = len(_network_syscall_lines(trace))
        trace_sha256 = _sha256(trace)
    offline_closed = run.status == "COMPLETED" and syscall_count == 0
    return {
        "schema_version": "1.0",
        "formal_result": False,
        "candidate_id": candidate_id,
        "offline_closed": offline_closed,
        "status": (
            "NON_FORMAL_OFFLINE_CLOSURE_COMPLETED"
            if offline_closed
            else "NON_FORMAL_OFFLINE_CLOSURE_FAILED"
        ),
        "command_status": run.status,
        "returncode": run.returncode,
        "network_syscall_count": syscall_count,
        "trace_sha256": trace_sha256,
        "stdout_sha256": _output_digest(run.stdout),
        "stderr_sha256": _output_digest(run.stderr),
        **_resource_fields(run, method["memory_reference_bytes"]),
        "interpretation": "NON_FORMAL_WORKSTATION_OFFLINE_CLOSURE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    result = run_offline_audit(args.candidate_id, args.trace, command)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["offline_closed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
