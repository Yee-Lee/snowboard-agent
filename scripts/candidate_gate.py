#!/usr/bin/env python3
"""Minimal candidate and target test runner for M4 and later milestones."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
PORTABLE_MINORS = ("3.11", "3.12", "3.13")
PROTECTED_PATHS = (
    "src",
    "tests",
    "scripts/candidate_gate.py",
    ".github/workflows/candidate-portable.yml",
    "pyproject.toml",
    "pytest.ini",
    "requirements",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements.lock",
    "poetry.lock",
    "uv.lock",
    "Pipfile.lock",
    "config.example.yaml",
)


class GateFailure(RuntimeError):
    """A candidate gate check failed."""


class RunReuseFailure(GateFailure):
    """An existing output must remain untouched."""


@dataclass(frozen=True)
class Repository:
    root: Path
    candidate_sha: str
    branch: str


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GateFailure(f"{label} is unreadable: {path}: {error}") from error
    if not isinstance(value, dict):
        raise GateFailure(f"{label} must be a JSON object: {path}")
    return value


def sha256(path: Path, label: str) -> str:
    if not path.is_file():
        raise GateFailure(f"{label} is missing or is not a file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        reason = completed.stderr.strip() or completed.stdout.strip()
        raise GateFailure(f"git {' '.join(args)} failed: {reason}")
    return completed.stdout.strip()


def inspect_repository(root: Path, candidate_sha: str) -> Repository:
    if not SHA_RE.fullmatch(candidate_sha):
        raise GateFailure("candidate SHA must be exactly 40 lowercase hexadecimal characters")
    head_sha = run_git(root, "rev-parse", "HEAD")
    if candidate_sha != head_sha:
        raise GateFailure(f"candidate SHA does not match checked-out HEAD: expected {candidate_sha}, got {head_sha}")
    dirty = run_git(root, "status", "--porcelain=v1", "--untracked-files=all", "--", *PROTECTED_PATHS)
    dirty_paths = sorted({line[2:].lstrip() for line in dirty.splitlines() if line})
    if dirty_paths:
        raise GateFailure("protected candidate input is dirty: " + ", ".join(dirty_paths))
    # Branch is diagnostic only. Detached HEAD and branch renames do not reject a candidate.
    branch = run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return Repository(root=root, candidate_sha=candidate_sha, branch=branch)


def require_run_id(run_id: str) -> None:
    if not RUN_ID_RE.fullmatch(run_id):
        raise GateFailure("run ID must be 3-128 safe characters ([A-Za-z0-9._-])")


def prepare_new_output(output: Path) -> None:
    if output.exists():
        raise RunReuseFailure(f"run output already exists and will not be overwritten: {output}")
    output.mkdir(parents=True)
    (output / "logs").mkdir()


def base_result(repo: Repository, mode: str, run_id: str) -> dict[str, Any]:
    return {
        "branch": repo.branch,
        "candidate_sha": repo.candidate_sha,
        "command": sys.argv,
        "mode": mode,
        "platform": platform.platform(),
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "run_id": run_id,
        "started_at_utc": utc_now(),
    }


def suite_counts(junit: Path, stdout: str) -> dict[str, int]:
    counts = {"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0}
    if not junit.is_file():
        raise GateFailure("suite did not produce a JUnit result")
    try:
        root = ET.parse(junit).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
        for suite in suites:
            tests = int(suite.attrib.get("tests", "0"))
            failures = int(suite.attrib.get("failures", "0")) + int(suite.attrib.get("errors", "0"))
            skipped = int(suite.attrib.get("skipped", "0"))
            counts["failed"] += failures
            counts["skipped"] += skipped
            counts["passed"] += tests - failures - skipped
    except (ET.ParseError, ValueError) as error:
        raise GateFailure(f"suite produced invalid JUnit: {error}") from error
    if " xfailed" in stdout.lower() or " xfail" in stdout.lower():
        counts["xfailed"] = 1
    return counts


def execute_pytest(
    repo: Repository,
    output: Path,
    target: str,
    marker: str,
    timeout_seconds: float,
) -> tuple[int, dict[str, int], list[str]]:
    if timeout_seconds <= 0:
        raise GateFailure("timeout seconds must be greater than zero")
    junit = output / "junit.xml"
    argv = [sys.executable, "-m", "pytest", "-v", "-m", marker, target, f"--junitxml={junit}"]
    stdout_path = output / "logs" / "suite.stdout.log"
    stderr_path = output / "logs" / "suite.stderr.log"
    try:
        completed = subprocess.run(
            argv,
            cwd=repo.root,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        stdout_path.write_text(completed.stdout, encoding="utf-8")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else (error.stdout or "")
        stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else (error.stderr or "")
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr + f"\nTIMEOUT after {timeout_seconds} seconds\n", encoding="utf-8")
        raise GateFailure(f"suite timeout after {timeout_seconds} seconds") from error
    return completed.returncode, suite_counts(junit, completed.stdout), argv


def passed(exit_code: int, counts: dict[str, int]) -> bool:
    return exit_code == 0 and all(counts[name] == 0 for name in ("failed", "skipped", "xfailed"))


def run_suite(args: argparse.Namespace, repo: Repository, output: Path, mode: str, marker: str) -> None:
    result = base_result(repo, mode, args.run_id)
    exit_code, counts, suite_command = execute_pytest(
        repo, output, args.suite if hasattr(args, "suite") else args.node, marker, args.timeout_seconds
    )
    status = "Pass" if passed(exit_code, counts) else "Fail"
    result.update(
        {
            "counts": counts,
            "ended_at_utc": utc_now(),
            "exit_code": exit_code,
            "raw_logs": ["logs/suite.stdout.log", "logs/suite.stderr.log"],
            "status": status,
            "suite_command": suite_command,
            "timeout_seconds": args.timeout_seconds,
        }
    )
    if mode == "portable":
        result["python_minor"] = args.python
        result["suite"] = args.suite
    elif mode == "acceptance":
        result["suite"] = args.suite
    else:
        result["node"] = args.node
        if status == "Pass":
            result["status"] = "Diagnostic"
    write_json(output / "result.json", result)
    if not passed(exit_code, counts):
        raise GateFailure(f"{mode} suite failed, timed out, was skipped, or was xfailed")


def portable(args: argparse.Namespace, repo: Repository, output: Path) -> None:
    if platform.python_version_tuple()[:2] != tuple(args.python.split(".")):
        raise GateFailure(f"runner Python is {platform.python_version()}, not requested Python {args.python}")
    run_suite(args, repo, output, "portable", "not rpi")


def validate_version_result(result: dict[str, Any], minor: str, candidate_sha: str, run_id: str) -> None:
    if result.get("status") != "Pass" or result.get("exit_code") != 0:
        raise GateFailure(f"Python {minor} portable result is not Pass")
    if result.get("candidate_sha") != candidate_sha or result.get("run_id") != run_id:
        raise GateFailure(f"Python {minor} portable result has a mixed candidate SHA or run ID")
    if result.get("python_minor") != minor:
        raise GateFailure(f"Python {minor} portable result has the wrong minor identity")
    counts = result.get("counts")
    if not isinstance(counts, dict) or any(counts.get(name) != 0 for name in ("failed", "skipped", "xfailed")):
        raise GateFailure(f"Python {minor} portable result contains Fail, Skip, or XFail")
    if not isinstance(result.get("timeout_seconds"), (int, float)) or result["timeout_seconds"] <= 0:
        raise GateFailure(f"Python {minor} portable result has no bounded timeout")
    if not isinstance(result.get("raw_logs"), list) or not result["raw_logs"]:
        raise GateFailure(f"Python {minor} portable result has no raw log locator")


def validate_matrix(index: dict[str, Any], index_path: Path, candidate_sha: str) -> None:
    if index.get("status") != "Pass" or index.get("candidate_sha") != candidate_sha:
        raise GateFailure("portable matrix is not Pass for this candidate SHA")
    results = index.get("results")
    if not isinstance(results, dict) or set(results) != set(PORTABLE_MINORS):
        raise GateFailure("portable matrix must contain Python 3.11, 3.12, and 3.13")
    run_id = index.get("run_id")
    if not isinstance(run_id, str):
        raise GateFailure("portable matrix run ID is missing")
    for minor, relative in results.items():
        if not isinstance(relative, str):
            raise GateFailure(f"Python {minor} portable result locator is invalid")
        result = load_json(index_path.parent / relative, f"Python {minor} portable result")
        validate_version_result(result, minor, candidate_sha, run_id)


def matrix(args: argparse.Namespace, repo: Repository) -> None:
    input_root = Path(args.input_root).resolve()
    output = Path(args.output).resolve()
    if output.exists():
        raise RunReuseFailure(f"matrix output already exists and will not be overwritten: {output}")
    if output.parent != input_root or output.name != "matrix-index.json":
        raise GateFailure("matrix output must be <input-root>/matrix-index.json")
    results: dict[str, str] = {}
    for minor in PORTABLE_MINORS:
        path = input_root / f"python-{minor}" / "result.json"
        result = load_json(path, f"Python {minor} portable result")
        validate_version_result(result, minor, repo.candidate_sha, args.run_id)
        results[minor] = str(path.relative_to(input_root))
    write_json(
        output,
        {
            "branch": repo.branch,
            "candidate_sha": repo.candidate_sha,
            "command": sys.argv,
            "created_at_utc": utc_now(),
            "results": results,
            "run_id": args.run_id,
            "status": "Pass",
        },
    )


def checksum_reference(path: Path, label: str) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": sha256(path, label)}


def preflight(args: argparse.Namespace, repo: Repository, output: Path) -> None:
    if args.runtime != "3.13":
        raise GateFailure("target runtime must be the M4 deployment runtime, CPython 3.13")
    matrix_path = Path(args.portable_index).resolve()
    matrix_index = load_json(matrix_path, "portable matrix index")
    validate_matrix(matrix_index, matrix_path, repo.candidate_sha)
    result = base_result(repo, "preflight", args.run_id)
    result.update(
        {
            "checksums": {
                "artifact_manifest": checksum_reference(Path(args.artifact_manifest), "artifact manifest"),
                "config": checksum_reference(Path(args.config), "config"),
                "hardware": checksum_reference(Path(args.hardware), "hardware description"),
            },
            "ended_at_utc": utc_now(),
            "exit_code": 0,
            "portable_index": str(matrix_path),
            "portable_run_id": matrix_index.get("run_id"),
            "runtime": args.runtime,
            "status": "Pass",
        }
    )
    write_json(output / "preflight.json", result)


def accept(args: argparse.Namespace, repo: Repository, output: Path) -> None:
    preflight_path = Path(args.preflight).resolve()
    if not output.is_dir() or preflight_path != (output / "preflight.json").resolve():
        raise GateFailure("acceptance must use its preflight-created output directory")
    if (output / "result.json").exists():
        raise RunReuseFailure("acceptance run already has a result and will not be rerun")
    preflight_result = load_json(preflight_path, "preflight result")
    expected = {
        "candidate_sha": repo.candidate_sha,
        "run_id": args.run_id,
        "status": "Pass",
    }
    if any(preflight_result.get(key) != value for key, value in expected.items()):
        raise GateFailure("preflight does not belong to this candidate and acceptance run")
    run_suite(args, repo, output, "acceptance", "rpi")


def write_failure(output: Path | None, command: str, reason: str, started_at: str) -> None:
    if output is None or not output.exists() or not output.is_dir():
        return
    logs = output / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    raw_log = logs / f"{command}.stderr.log"
    raw_log.write_text(reason + "\n", encoding="utf-8")
    failure_path = output / f"{command}-failure.json"
    if not failure_path.exists():
        write_json(
            failure_path,
            {
                "command": command,
                "ended_at_utc": utc_now(),
                "exit_code": 1,
                "raw_log": str(raw_log.relative_to(output)),
                "reason": reason,
                "started_at_utc": started_at,
                "status": "Fail",
            },
        )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--repo", default=".")
    commands = root.add_subparsers(dest="command", required=True)

    def common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--candidate-sha", required=True)
        subparser.add_argument("--run-id", required=True)
        subparser.add_argument("--output", required=True)

    portable_parser = commands.add_parser("portable")
    common(portable_parser)
    portable_parser.add_argument("--python", choices=PORTABLE_MINORS, required=True)
    portable_parser.add_argument("--suite", required=True)
    portable_parser.add_argument("--timeout-seconds", type=float, required=True)

    matrix_parser = commands.add_parser("matrix")
    matrix_parser.add_argument("--candidate-sha", required=True)
    matrix_parser.add_argument("--run-id", required=True)
    matrix_parser.add_argument("--input-root", required=True)
    matrix_parser.add_argument("--output", required=True)

    preflight_parser = commands.add_parser("preflight")
    common(preflight_parser)
    preflight_parser.add_argument("--portable-index", required=True)
    preflight_parser.add_argument("--runtime", required=True)
    preflight_parser.add_argument("--hardware", required=True)
    preflight_parser.add_argument("--config", required=True)
    preflight_parser.add_argument("--artifact-manifest", required=True)

    accept_parser = commands.add_parser("accept")
    common(accept_parser)
    accept_parser.add_argument("--preflight", required=True)
    accept_parser.add_argument("--suite", required=True)
    accept_parser.add_argument("--timeout-seconds", type=float, required=True)

    debug_parser = commands.add_parser("debug")
    common(debug_parser)
    debug_parser.add_argument("--node", required=True)
    debug_parser.add_argument("--timeout-seconds", type=float, required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    output = Path(args.output).resolve()
    started_at = utc_now()
    try:
        require_run_id(args.run_id)
        if args.command == "matrix":
            repo = inspect_repository(Path(args.repo).resolve(), args.candidate_sha)
            matrix(args, repo)
        elif args.command == "accept":
            repo = inspect_repository(Path(args.repo).resolve(), args.candidate_sha)
            accept(args, repo, output)
        else:
            prepare_new_output(output)
            repo = inspect_repository(Path(args.repo).resolve(), args.candidate_sha)
            if args.command == "portable":
                portable(args, repo, output)
            elif args.command == "preflight":
                preflight(args, repo, output)
            else:
                run_suite(args, repo, output, "debug", "rpi")
    except GateFailure as error:
        if not isinstance(error, RunReuseFailure):
            write_failure(output.parent if args.command == "matrix" else output, args.command, str(error), started_at)
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
