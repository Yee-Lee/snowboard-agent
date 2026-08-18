#!/usr/bin/env python3
"""Fail-closed portable-candidate and hardware-acceptance gate.

This runner intentionally accepts a candidate identity from its caller.  It
never treats the checked-out HEAD as authorization to test or accept itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import secrets
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PORTABLE_MINORS = ("3.11", "3.12", "3.13")
PROTECTED_PATHS = (
    "src",
    "tests",
    "scripts",
    "pyproject.toml",
    "pytest.ini",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements.lock",
    "poetry.lock",
    "uv.lock",
    "Pipfile.lock",
    ".github/workflows",
    "config.example.yaml",
    "config",
    "artifacts",
)


class GateFailure(RuntimeError):
    """A contract failure which must leave a machine-readable FAIL record."""


class RunReuseFailure(GateFailure):
    """A reused run must be rejected without modifying its existing bundle."""


@dataclass(frozen=True)
class Repository:
    root: Path
    candidate_sha: str
    head_sha: str
    branch: str
    dirty_paths: list[str]


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GateFailure(f"{label} is unreadable: {path}: {error}") from error
    if not isinstance(value, dict):
        raise GateFailure(f"{label} must be a JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


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
    if completed.returncode != 0:
        reason = completed.stderr.strip() or completed.stdout.strip()
        raise GateFailure(f"git {' '.join(args)} failed: {reason}")
    return completed.stdout.strip()


def inspect_repository(root: Path, candidate_sha: str) -> Repository:
    if not SHA_RE.fullmatch(candidate_sha):
        raise GateFailure("candidate SHA must be exactly 40 lowercase hexadecimal characters")
    head_sha = run_git(root, "rev-parse", "HEAD")
    if candidate_sha != head_sha:
        raise GateFailure(f"candidate SHA does not match checked-out HEAD: expected {candidate_sha}, got {head_sha}")
    branch = run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    dirty = run_git(root, "status", "--porcelain=v1", "--untracked-files=all", "--", *PROTECTED_PATHS)
    dirty_paths = sorted({line[2:].lstrip() for line in dirty.splitlines() if line})
    if dirty_paths:
        raise GateFailure("protected candidate input is dirty: " + ", ".join(dirty_paths))
    return Repository(root, candidate_sha, head_sha, branch, dirty_paths)


def identity(repo: Repository, mode: str, run_id: str, argv: list[str]) -> dict[str, Any]:
    return {
        "candidate_sha": repo.candidate_sha,
        "branch": repo.branch,
        "command": argv,
        "dirty_paths": repo.dirty_paths,
        "protected_paths_clean": not repo.dirty_paths,
        "mode": mode,
        "platform": platform.platform(),
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "run_id": run_id,
        "started_at_utc": utc_now(),
    }


def prepare_output(output: Path, mode: str, run_id: str) -> None:
    if output.exists():
        raise RunReuseFailure(f"run ID/output is already in use and will not be overwritten: {output}")
    normalized = output.as_posix()
    if mode == "portable":
        if f"/portable/{run_id}/" not in normalized or not output.name.startswith("python-"):
            raise GateFailure(f"portable output must be isolated under portable/<run-id>/python-<minor>: {output}")
    elif f"/{mode}/" not in normalized or output.name != run_id:
        raise GateFailure(f"output must be isolated under {mode}/<run-id>: {output}")
    output.mkdir(parents=True)
    (output / "logs").mkdir()


def write_failure(output: Path | None, command: str, reason: str, started: str) -> None:
    if output is None or not output.exists():
        return
    evidence_root = output.parent if output.is_file() else output
    logs = evidence_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{command}.stderr.log").write_text(reason + "\n", encoding="utf-8")
    write_json(
        evidence_root / f"{command}-failure.json",
        {
            "command": command,
            "ended_at_utc": utc_now(),
            "exit_code": 1,
            "raw_log_path": f"logs/{command}.stderr.log",
            "reason": reason,
            "started_at_utc": started,
            "status": "Fail",
        },
    )


def require_run_id(run_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}", run_id):
        raise GateFailure("run ID must be 3-128 safe characters ([A-Za-z0-9._-])")


def execute_suite(
    output: Path,
    suite: str,
    timeout_seconds: float,
    marker: str | None = None,
) -> tuple[int, dict[str, int], list[str]]:
    if timeout_seconds <= 0:
        raise GateFailure("timeout seconds must be greater than zero")
    junit = output / "junit.xml"
    argv = [sys.executable, "-m", "pytest", "-v"]
    if marker:
        argv.extend(["-m", marker])
    argv.extend([suite, f"--junitxml={junit}"])
    started = utc_now()
    stdout_path = output / "logs" / "suite.stdout.log"
    stderr_path = output / "logs" / "suite.stderr.log"
    try:
        completed = subprocess.run(argv, text=True, capture_output=True, timeout=timeout_seconds, check=False)
        stdout_path.write_text(completed.stdout, encoding="utf-8")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as error:
        timed_out_stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else (error.stdout or "")
        timed_out_stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else (error.stderr or "")
        stdout_path.write_text(timed_out_stdout, encoding="utf-8")
        stderr_path.write_text(timed_out_stderr + f"\nTIMEOUT after {timeout_seconds} seconds\n", encoding="utf-8")
        raise GateFailure(f"suite timeout after {timeout_seconds} seconds; raw logs: {stdout_path}, {stderr_path}") from error
    counts = read_suite_counts(junit, completed.stdout)
    return exit_code, counts, argv


def read_suite_counts(junit: Path, stdout: str) -> dict[str, int]:
    counts = {"passed": 0, "failed": 0, "blocked": 0, "skipped": 0, "xfailed": 0}
    if junit.exists():
        try:
            root = ET.parse(junit).getroot()
            suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
            for item in suites:
                counts["failed"] += int(item.attrib.get("failures", "0")) + int(item.attrib.get("errors", "0"))
                counts["skipped"] += int(item.attrib.get("skipped", "0"))
                counts["passed"] += int(item.attrib.get("tests", "0")) - int(item.attrib.get("failures", "0")) - int(item.attrib.get("errors", "0")) - int(item.attrib.get("skipped", "0"))
        except (ET.ParseError, ValueError) as error:
            raise GateFailure(f"suite did not produce a valid JUnit report: {error}") from error
    if " xfailed" in stdout.lower() or " xfail" in stdout.lower():
        counts["xfailed"] = 1
    return counts


def all_zero(counts: dict[str, int]) -> bool:
    return all(counts.get(name) == 0 for name in ("failed", "blocked", "skipped", "xfailed"))


def check_checksum_inputs(args: argparse.Namespace) -> dict[str, dict[str, str]]:
    return {
        "artifact_manifest": checksum_reference(Path(args.artifact_manifest), "artifact manifest"),
        "config": checksum_reference(Path(args.config), "config"),
        "hardware": checksum_reference(Path(args.hardware), "hardware description"),
    }


def checksum_reference(path: Path, label: str) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": sha256(path, label)}


def validate_counts(value: object, label: str) -> dict[str, int]:
    names = {"passed", "failed", "blocked", "skipped", "xfailed"}
    if not isinstance(value, dict) or set(value) != names:
        raise GateFailure(f"{label} counts must contain exactly {', '.join(sorted(names))}")
    if any(not isinstance(value[name], int) or value[name] < 0 for name in names):
        raise GateFailure(f"{label} counts must be non-negative integers")
    return value


def validate_version_result(
    result: dict[str, Any],
    minor: str,
    candidate_sha: str,
    run_id: str,
) -> dict[str, Any]:
    label = f"Python {minor} result"
    if result.get("status") != "Pass" or result.get("candidate_sha") != candidate_sha:
        raise GateFailure(f"{label} is failed or has a mixed candidate SHA")
    if result.get("run_id") != run_id:
        raise GateFailure(f"{label} does not belong to portable run {run_id}")
    if result.get("python_minor") != minor:
        raise GateFailure(f"{label} python_minor is missing or does not match its matrix key")
    python_identity = result.get("python")
    if not isinstance(python_identity, dict) or python_identity.get("implementation") != "CPython":
        raise GateFailure(f"{label} must identify CPython")
    version = python_identity.get("version")
    if not isinstance(version, str) or not version.startswith(minor + "."):
        raise GateFailure(f"{label} Python version does not match {minor}")
    if not isinstance(result.get("platform"), str) or not result["platform"]:
        raise GateFailure(f"{label} platform identity is missing")
    if not isinstance(result.get("branch"), str) or not result["branch"]:
        raise GateFailure(f"{label} branch identity is missing")
    if result.get("dirty_paths") != [] or result.get("protected_paths_clean") is not True:
        raise GateFailure(f"{label} protected-path dirty identity is missing or not clean")
    command = result.get("command")
    if not isinstance(command, list) or not command or any(not isinstance(item, str) for item in command):
        raise GateFailure(f"{label} command argv is missing or invalid")
    timeout = result.get("timeout_seconds")
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise GateFailure(f"{label} bounded timeout is missing or invalid")
    dependency = result.get("dependency_lock_checksum")
    if not isinstance(dependency, str) or not re.fullmatch(r"[0-9a-f]{64}", dependency):
        raise GateFailure(f"{label} dependency checksum is missing or invalid")
    raw_logs = result.get("raw_logs")
    if not isinstance(raw_logs, list) or not raw_logs or any(not isinstance(item, str) for item in raw_logs):
        raise GateFailure(f"{label} raw log identity is missing")
    counts = validate_counts(result.get("counts"), label)
    if not all_zero(counts):
        raise GateFailure(f"{label} has non-zero Fail/Blocked/Skip/XFail counts")
    if result.get("exit_code") != 0:
        raise GateFailure(f"{label} exit code is missing or non-zero")
    started = parse_timestamp(result.get("started_at_utc"), f"{label} started_at_utc")
    ended = parse_timestamp(result.get("ended_at_utc"), f"{label} ended_at_utc")
    if ended < started:
        raise GateFailure(f"{label} end time predates its start time")
    if not isinstance(result.get("suite"), str) or not result["suite"]:
        raise GateFailure(f"{label} suite identity is missing")
    test_ids = result.get("suite_test_ids")
    if not isinstance(test_ids, list) or not test_ids or any(not isinstance(item, str) or not item for item in test_ids):
        raise GateFailure(f"{label} suite/Test-ID mapping is missing")
    return {
        "branch": result["branch"],
        "command": command,
        "counts": counts,
        "dependency_lock_checksum": dependency,
        "dirty_paths": [],
        "ended_at_utc": result["ended_at_utc"],
        "exit_code": 0,
        "platform": result["platform"],
        "protected_paths_clean": True,
        "python": python_identity,
        "python_minor": minor,
        "raw_logs": raw_logs,
        "started_at_utc": result["started_at_utc"],
        "suite": result["suite"],
        "suite_test_ids": test_ids,
        "timeout_seconds": timeout,
    }


def verify_matrix(index_path: Path, candidate_sha: str) -> tuple[dict[str, Any], dict[str, str]]:
    index = load_json(index_path, "portable matrix index")
    if index.get("status") != "Pass":
        raise GateFailure("portable matrix index is not Pass")
    if index.get("candidate_sha") != candidate_sha:
        raise GateFailure("portable matrix candidate SHA does not match the requested candidate")
    results = index.get("results")
    if not isinstance(results, dict) or set(results) != set(PORTABLE_MINORS):
        raise GateFailure("portable matrix must contain exactly Python 3.11, 3.12, and 3.13 results")
    run_id = index.get("run_id")
    if not isinstance(run_id, str):
        raise GateFailure("portable matrix run ID is missing")
    require_run_id(run_id)
    expected_identities = index.get("version_identities")
    if not isinstance(expected_identities, dict) or set(expected_identities) != set(PORTABLE_MINORS):
        raise GateFailure("portable matrix version identity index is incomplete")
    result_checksums: dict[str, str] = {}
    dependency_checksums: set[str] = set()
    branches: set[str] = set()
    test_id_sets: set[tuple[str, ...]] = set()
    platforms: set[str] = set()
    for minor, result_ref in results.items():
        result_path = index_path.parent / str(result_ref)
        result = load_json(result_path, f"Python {minor} result")
        version_identity = validate_version_result(result, minor, candidate_sha, run_id)
        if expected_identities.get(minor) != version_identity:
            raise GateFailure(f"Python {minor} result identity does not match the matrix index")
        dependency_checksums.add(version_identity["dependency_lock_checksum"])
        branches.add(version_identity["branch"])
        test_id_sets.add(tuple(version_identity["suite_test_ids"]))
        platforms.add(version_identity["platform"])
        result_checksums[minor] = sha256(result_path, f"Python {minor} result")
    if len(dependency_checksums) != 1 or index.get("dependency_lock_checksum") not in dependency_checksums:
        raise GateFailure("portable matrix dependency identity is missing or mixed")
    if len(branches) != 1 or index.get("branch") not in branches:
        raise GateFailure("portable matrix branch identity is missing or mixed")
    if len(test_id_sets) != 1 or index.get("suite_test_ids") != list(next(iter(test_id_sets))):
        raise GateFailure("portable matrix suite/Test-ID identity is missing or mixed")
    if index.get("dirty_paths") != [] or index.get("protected_paths_clean") is not True:
        raise GateFailure("portable matrix protected-path identity is missing or not clean")
    matrix_command = index.get("command")
    if (
        index.get("exit_code") != 0
        or not isinstance(matrix_command, list)
        or not matrix_command
        or any(not isinstance(item, str) or not item for item in matrix_command)
    ):
        raise GateFailure("portable matrix command/exit identity is missing or failed")
    if index.get("platforms") != sorted(platforms):
        raise GateFailure("portable matrix aggregate platform identity is missing or mixed")
    matrix_started = parse_timestamp(index.get("started_at_utc"), "portable matrix started_at_utc")
    matrix_ended = parse_timestamp(index.get("ended_at_utc"), "portable matrix ended_at_utc")
    if matrix_ended < matrix_started:
        raise GateFailure("portable matrix end time predates its start time")
    return index, result_checksums


def build_matrix(args: argparse.Namespace, repo: Repository) -> None:
    matrix_started_at = utc_now()
    input_root = Path(args.input_root)
    output = Path(args.output)
    if output.exists():
        raise RunReuseFailure(f"matrix index already exists and will not be overwritten: {output}")
    if output.parent.resolve() != input_root.resolve() or output.name != "matrix-index.json":
        raise GateFailure("matrix index must be written as <input-root>/matrix-index.json")
    results: dict[str, str] = {}
    version_identities: dict[str, dict[str, Any]] = {}
    dependency_checksums: set[str] = set()
    branches: set[str] = set()
    suite_test_ids: set[tuple[str, ...]] = set()
    failure: str | None = None
    for minor in PORTABLE_MINORS:
        result_path = input_root / f"python-{minor}" / "result.json"
        try:
            result = load_json(result_path, f"Python {minor} result")
            version_identity = validate_version_result(result, minor, repo.candidate_sha, args.run_id)
            dependency_checksums.add(version_identity["dependency_lock_checksum"])
            branches.add(version_identity["branch"])
            suite_test_ids.add(tuple(version_identity["suite_test_ids"]))
            version_identities[minor] = version_identity
            results[minor] = str(result_path.relative_to(input_root))
        except GateFailure as error:
            failure = str(error)
            break
    if failure is None and len(dependency_checksums) != 1:
        failure = "portable matrix dependency checksum is mixed across Python versions"
    if failure is None and len(branches) != 1:
        failure = "portable matrix branch identity is mixed across Python versions"
    if failure is None and len(suite_test_ids) != 1:
        failure = "portable matrix suite/Test-ID mapping is mixed across Python versions"
    index: dict[str, Any] = {
        "candidate_sha": repo.candidate_sha,
        "command": sys.argv,
        "ended_at_utc": utc_now(),
        "exit_code": 0 if failure is None else 1,
        "dirty_paths": [],
        "platforms": sorted({identity["platform"] for identity in version_identities.values()}),
        "protected_paths_clean": True,
        "results": results,
        "run_id": args.run_id,
        "started_at_utc": matrix_started_at,
        "status": "Pass" if failure is None else "Fail",
        "version_identities": version_identities,
    }
    if len(dependency_checksums) == 1:
        index["dependency_lock_checksum"] = next(iter(dependency_checksums))
    if len(branches) == 1:
        index["branch"] = next(iter(branches))
    if len(suite_test_ids) == 1:
        index["suite_test_ids"] = list(next(iter(suite_test_ids)))
    if failure is not None:
        index["reason"] = failure
    write_json(output, index)
    if failure is not None:
        raise GateFailure(failure)


def verify_freeze_manifest(path: Path, candidate_sha: str) -> dict[str, Any]:
    manifest = load_json(path, "freeze manifest")
    if manifest.get("status") != "Frozen" or manifest.get("candidate_sha") != candidate_sha:
        raise GateFailure("freeze manifest is absent, not Frozen, or belongs to a different candidate")
    return manifest


def parse_timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise GateFailure(f"{label} timestamp is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise GateFailure(f"{label} timestamp is invalid: {value}") from error
    if parsed.tzinfo is None:
        raise GateFailure(f"{label} timestamp must include a UTC offset")
    return parsed


def verify_manual_observation(
    ready_path: Path,
    observation_path: Path,
    run_id: str,
    candidate_sha: str,
    card_started_at: datetime,
) -> dict[str, Any]:
    ready = load_json(ready_path, "READY record")
    observation = load_json(observation_path, "manual observation")
    for record, label in ((ready, "READY record"), (observation, "manual observation")):
        if record.get("candidate_sha") != candidate_sha or record.get("mode") != "acceptance":
            raise GateFailure(f"{label} candidate SHA or acceptance mode does not match")
        if record.get("run_id") != run_id:
            raise GateFailure(f"{label} run ID does not match acceptance run")
        if not isinstance(record.get("test_id"), str) or not record["test_id"]:
            raise GateFailure(f"{label} test ID is missing")
        if not isinstance(record.get("nonce"), str) or not record["nonce"]:
            raise GateFailure(f"{label} nonce is missing")
    if ready["test_id"] != observation["test_id"] or ready["nonce"] != observation["nonce"]:
        raise GateFailure("manual observation test ID or nonce does not match READY record")
    ready_at = parse_timestamp(ready.get("ready_at_utc"), "READY record")
    observed_at = parse_timestamp(observation.get("observed_at_utc"), "manual observation")
    if ready_at < card_started_at:
        raise GateFailure("READY record predates the active formal card")
    if observed_at <= ready_at or observed_at <= card_started_at:
        raise GateFailure("manual observation is not later than READY")
    if observation_path.stat().st_mtime_ns < ready_path.stat().st_mtime_ns:
        raise GateFailure("manual observation file predates the active READY record")
    if not isinstance(observation.get("operator"), str) or not observation["operator"]:
        raise GateFailure("manual observation operator is missing")
    if not isinstance(observation.get("checklist_version"), str) or not observation["checklist_version"]:
        raise GateFailure("manual observation checklist version is missing")
    checklist = observation.get("checklist")
    if not isinstance(checklist, dict) or not checklist or any(value is not True for value in checklist.values()):
        raise GateFailure("manual observation checklist is missing or contains a non-pass item")
    if observation.get("record_command_exit_code") != 0:
        raise GateFailure("manual observation record command did not exit zero")
    return observation


def portable(args: argparse.Namespace, repo: Repository, output: Path) -> None:
    if args.python not in PORTABLE_MINORS:
        raise GateFailure("portable Python minor must be one of 3.11, 3.12, 3.13")
    if platform.python_version_tuple()[:2] != tuple(args.python.split(".")):
        raise GateFailure(f"runner Python is {platform.python_version()}, not requested Python {args.python}")
    exit_code, counts, suite_argv = execute_suite(output, args.suite, args.timeout_seconds)
    status = "Pass" if exit_code == 0 and all_zero(counts) else "Fail"
    result = identity(repo, "portable", args.run_id, sys.argv)
    result.update(
        {
            "counts": counts,
            "dependency_lock_checksum": sha256(repo.root / "pyproject.toml", "pyproject.toml"),
            "ended_at_utc": utc_now(),
            "exit_code": exit_code,
            "python_minor": args.python,
            "raw_logs": ["logs/suite.stdout.log", "logs/suite.stderr.log"],
            "status": status,
            "suite": args.suite,
            "suite_command": suite_argv,
            "suite_test_ids": args.test_id,
            "timeout_seconds": args.timeout_seconds,
        }
    )
    write_json(output / "result.json", result)
    if status != "Pass":
        raise GateFailure("portable suite has a non-zero exit or Fail/Blocked/Skip/XFail count")


def preflight(args: argparse.Namespace, repo: Repository, output: Path) -> None:
    if args.runtime != "3.13":
        raise GateFailure("target runtime must be the fixed Pi CPython 3.13 runtime")
    freeze_path = Path(args.freeze_manifest).resolve()
    matrix_path = Path(args.portable_index).resolve()
    verify_freeze_manifest(freeze_path, repo.candidate_sha)
    matrix, matrix_result_checksums = verify_matrix(matrix_path, repo.candidate_sha)
    frozen_inputs = check_checksum_inputs(args)
    frozen_inputs["freeze_manifest"] = checksum_reference(freeze_path, "freeze manifest")
    frozen_inputs["portable_index"] = checksum_reference(matrix_path, "portable matrix index")
    result = identity(repo, "acceptance", args.run_id, sys.argv)
    result.update(
        {
            "ended_at_utc": utc_now(),
            "exit_code": 0,
            "frozen_inputs": frozen_inputs,
            "portable_result_checksums": matrix_result_checksums,
            "portable_run_id": matrix.get("run_id"),
            "runtime": args.runtime,
            "status": "Pass",
        }
    )
    write_json(output / "identity.json", result)
    write_json(output / "preflight.json", result)


def verify_checksum_reference(reference: object, label: str) -> None:
    if not isinstance(reference, dict):
        raise GateFailure(f"preflight {label} checksum reference is missing")
    path = reference.get("path")
    expected = reference.get("sha256")
    if not isinstance(path, str) or not isinstance(expected, str):
        raise GateFailure(f"preflight {label} checksum reference is invalid")
    if sha256(Path(path), label) != expected:
        raise GateFailure(f"{label} changed after preflight")


def verify_preflight_chain(preflight_path: Path, preflight_result: dict[str, Any]) -> dict[str, Any]:
    identity_path = preflight_path.parent / "identity.json"
    identity_checksum = sha256(identity_path, "preflight identity")
    preflight_checksum = sha256(preflight_path, "preflight")
    if load_json(identity_path, "preflight identity") != preflight_result or identity_checksum != preflight_checksum:
        raise GateFailure("identity.json does not match preflight.json")
    frozen_inputs = preflight_result.get("frozen_inputs")
    if not isinstance(frozen_inputs, dict):
        raise GateFailure("preflight frozen input identity is missing")
    for name in ("artifact_manifest", "config", "hardware", "freeze_manifest", "portable_index"):
        verify_checksum_reference(frozen_inputs.get(name), name)
    portable_reference = frozen_inputs["portable_index"]
    matrix_path = Path(portable_reference["path"])
    index = load_json(matrix_path, "portable matrix index")
    result_refs = index.get("results")
    expected_checksums = preflight_result.get("portable_result_checksums")
    if not isinstance(result_refs, dict) or not isinstance(expected_checksums, dict):
        raise GateFailure("preflight portable result identity is missing")
    for minor in PORTABLE_MINORS:
        result_ref = result_refs.get(minor)
        expected = expected_checksums.get(minor)
        if not isinstance(result_ref, str) or not isinstance(expected, str):
            raise GateFailure(f"preflight Python {minor} result checksum is missing")
        if sha256(matrix_path.parent / result_ref, f"Python {minor} result") != expected:
            raise GateFailure(f"Python {minor} result changed after preflight")
    return {
        "frozen_inputs": frozen_inputs,
        "identity": {"path": str(identity_path.resolve()), "sha256": identity_checksum},
        "portable_result_checksums": expected_checksums,
        "preflight": {"path": str(preflight_path.resolve()), "sha256": preflight_checksum},
        "portable_run_id": preflight_result.get("portable_run_id"),
    }


def reserve_acceptance_attempt(output: Path, run_id: str, candidate_sha: str) -> Path:
    marker = output / "accept-attempt.json"
    payload = {
        "candidate_sha": candidate_sha,
        "mode": "acceptance",
        "reserved_at_utc": utc_now(),
        "run_id": run_id,
        "status": "Started",
    }
    try:
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise RunReuseFailure("acceptance run ID already has an attempt and cannot be resumed") from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as target:
        target.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return marker


def wait_for_observation(
    ready_path: Path,
    observation_path: Path,
    run_id: str,
    candidate_sha: str,
    card_started_at: datetime,
    timeout_seconds: float,
    process: subprocess.Popen[Any],
) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise GateFailure("manual observation timeout must be greater than zero")
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if observation_path.exists():
            return verify_manual_observation(ready_path, observation_path, run_id, candidate_sha, card_started_at)
        if process.poll() is not None:
            raise GateFailure("acceptance suite exited before manual observation was recorded")
        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
    raise GateFailure(f"manual observation timeout after {timeout_seconds} seconds")


def stop_process(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def wait_for_producer_ready(
    process: subprocess.Popen[Any],
    suite_started_path: Path,
    ready_path: Path,
    repo: Repository,
    run_id: str,
    test_id: str,
    nonce: str,
    card_started_at: datetime,
    timeout_seconds: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if timeout_seconds <= 0:
        raise GateFailure("producer readiness timeout must be greater than zero")
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if ready_path.exists():
            started = load_json(suite_started_path, "suite-start record")
            ready = load_json(ready_path, "READY record")
            for record, label, timestamp_name in (
                (started, "suite-start record", "started_at_utc"),
                (ready, "READY record", "ready_at_utc"),
            ):
                if any(
                    record.get(name) != value
                    for name, value in (
                        ("candidate_sha", repo.candidate_sha),
                        ("mode", "acceptance"),
                        ("run_id", run_id),
                        ("test_id", test_id),
                        ("nonce", nonce),
                        ("producer_pid", process.pid),
                    )
                ):
                    raise GateFailure(f"{label} does not belong to the active suite producer")
                if parse_timestamp(record.get(timestamp_name), label) < card_started_at:
                    raise GateFailure(f"{label} predates the active suite process")
            if parse_timestamp(ready["ready_at_utc"], "READY record") < parse_timestamp(started["started_at_utc"], "suite-start record"):
                raise GateFailure("READY record predates suite start")
            return started, ready
        if process.poll() is not None:
            raise GateFailure("acceptance suite exited before emitting READY")
        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
    raise GateFailure(f"producer readiness timeout after {timeout_seconds} seconds")


def execute_acceptance_suite(
    args: argparse.Namespace,
    repo: Repository,
    output: Path,
    suite_started_path: Path,
    ready_path: Path,
    observation_path: Path,
) -> tuple[int, dict[str, int], list[str], dict[str, Any], dict[str, Any]]:
    if args.timeout_seconds <= 0:
        raise GateFailure("suite timeout must be greater than zero")
    junit = output / "junit.xml"
    argv = [sys.executable, "-m", "pytest", "-v", "-m", "rpi", args.suite, f"--junitxml={junit}"]
    nonce = secrets.token_hex(16)
    environment = os.environ.copy()
    environment.update(
        {
            "CANDIDATE_GATE_CANDIDATE_SHA": repo.candidate_sha,
            "CANDIDATE_GATE_MANUAL_OBSERVATION": str(observation_path),
            "CANDIDATE_GATE_MODE": "acceptance",
            "CANDIDATE_GATE_NONCE": nonce,
            "CANDIDATE_GATE_READY_RECORD": str(ready_path),
            "CANDIDATE_GATE_RUN_ID": args.run_id,
            "CANDIDATE_GATE_SUITE_STARTED": str(suite_started_path),
            "CANDIDATE_GATE_TEST_ID": args.test_id,
        }
    )
    stdout_path = output / "logs" / "suite.stdout.log"
    stderr_path = output / "logs" / "suite.stderr.log"
    card_started_at = datetime.now(UTC)
    deadline = time.monotonic() + args.timeout_seconds
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(argv, stdout=stdout, stderr=stderr, text=True, env=environment)
        try:
            started, _ = wait_for_producer_ready(
                process,
                suite_started_path,
                ready_path,
                repo,
                args.run_id,
                args.test_id,
                nonce,
                card_started_at,
                min(args.readiness_timeout_seconds, max(0.0, deadline - time.monotonic())),
            )
            observation = wait_for_observation(
                ready_path,
                observation_path,
                args.run_id,
                repo.candidate_sha,
                card_started_at,
                min(args.manual_timeout_seconds, max(0.0, deadline - time.monotonic())),
                process,
            )
            try:
                exit_code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired as error:
                raise GateFailure(f"suite timeout after {args.timeout_seconds} seconds") from error
        except GateFailure:
            stop_process(process)
            raise
    stdout_text = stdout_path.read_text(encoding="utf-8")
    counts = read_suite_counts(junit, stdout_text)
    return exit_code, counts, argv, started, observation


def write_full_acceptance_failure(
    repo: Repository,
    args: argparse.Namespace,
    output: Path,
    evidence_chain: dict[str, Any],
    attempt_reference: dict[str, str],
    reason: str,
    evidence_paths: dict[str, Path],
) -> None:
    raw_logs = ["logs/accept.stderr.log"]
    for relative in ("logs/suite.stdout.log", "logs/suite.stderr.log"):
        if (output / relative).is_file():
            raw_logs.append(relative)
    failure_result = identity(repo, "acceptance", args.run_id, sys.argv)
    failure_result.update(evidence_chain)
    failure_result.update(
        {
            "acceptance_attempt": attempt_reference,
            "ended_at_utc": utc_now(),
            "exit_code": 1,
            "raw_logs": raw_logs,
            "reason": reason,
            "status": "Fail",
            "suite": args.suite,
            "timeout_seconds": args.timeout_seconds,
        }
    )
    for name, path in evidence_paths.items():
        if path.is_file():
            failure_result[name] = checksum_reference(path, name)
    write_json(output / "results" / "result.json", failure_result)


def accept(args: argparse.Namespace, repo: Repository, output: Path) -> None:
    preflight_path = Path(args.preflight)
    if not output.exists():
        raise GateFailure("acceptance output does not contain a preflight-created run directory")
    if preflight_path.resolve() != (output / "preflight.json").resolve():
        raise GateFailure("acceptance must consume preflight.json from its own run directory")
    preflight_result = load_json(preflight_path, "preflight result")
    if any(preflight_result.get(name) != value for name, value in (("status", "Pass"), ("mode", "acceptance"), ("run_id", args.run_id), ("candidate_sha", repo.candidate_sha))):
        raise GateFailure("preflight is not a PASS for this acceptance run and candidate")
    evidence_chain = verify_preflight_chain(preflight_path, preflight_result)
    attempt_path = reserve_acceptance_attempt(output, args.run_id, repo.candidate_sha)
    attempt_reference = checksum_reference(attempt_path, "acceptance attempt")
    ready_path = Path(args.ready_record).resolve()
    observation_path = Path(args.manual_observation).resolve()
    cards_root = (output / "cards").resolve()
    manual_root = (output / "manual").resolve()
    suite_started_path = cards_root / f"{args.test_id}-suite-started.json"
    evidence_paths = {
        "suite_started": suite_started_path,
        "ready_record": ready_path,
        "manual_observation": observation_path,
    }
    try:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}", args.test_id):
            raise GateFailure("test ID must use 3-128 safe characters ([A-Za-z0-9._-])")
        if ready_path.parent != cards_root or observation_path.parent != manual_root:
            raise GateFailure("READY and manual observation must use this run's cards/ and manual/ directories")
        if ready_path.exists() or observation_path.exists() or cards_root.exists() or manual_root.exists():
            raise GateFailure("prefilled READY or manual observation is forbidden")
        cards_root.mkdir()
        manual_root.mkdir()
        exit_code, counts, suite_argv, suite_started, observation = execute_acceptance_suite(
            args,
            repo,
            output,
            suite_started_path,
            ready_path,
            observation_path,
        )
    except GateFailure as error:
        write_full_acceptance_failure(repo, args, output, evidence_chain, attempt_reference, str(error), evidence_paths)
        raise
    try:
        if load_json(suite_started_path, "suite-start record") != suite_started:
            raise GateFailure("suite-start record changed during acceptance execution")
        observation = verify_manual_observation(
            ready_path,
            observation_path,
            args.run_id,
            repo.candidate_sha,
            parse_timestamp(suite_started["started_at_utc"], "suite-start record"),
        )
        ready_checksum = sha256(ready_path, "READY record")
        observation_checksum = sha256(observation_path, "manual observation")
        suite_started_checksum = sha256(suite_started_path, "suite-start record")
    except GateFailure as error:
        write_full_acceptance_failure(repo, args, output, evidence_chain, attempt_reference, str(error), evidence_paths)
        raise
    status = "Pass" if exit_code == 0 and all_zero(counts) else "Fail"
    result = identity(repo, "acceptance", args.run_id, sys.argv)
    result.update(evidence_chain)
    result.update(
        {
            "acceptance_attempt": attempt_reference,
            "counts": counts,
            "ended_at_utc": utc_now(),
            "exit_code": exit_code,
            "manual_observation": {"path": str(observation_path), "sha256": observation_checksum},
            "raw_logs": ["logs/suite.stdout.log", "logs/suite.stderr.log"],
            "ready_record": {"path": str(ready_path), "sha256": ready_checksum},
            "status": status,
            "suite": args.suite,
            "suite_command": suite_argv,
            "suite_started": {"path": str(suite_started_path), "sha256": suite_started_checksum},
            "suite_started_identity": suite_started,
            "timeout_seconds": args.timeout_seconds,
        }
    )
    write_json(output / "results" / "result.json", result)
    if status != "Pass":
        raise GateFailure("acceptance suite has a non-zero exit or Fail/Blocked/Skip/XFail count")
    manifest = dict(result)
    manifest["manual_test_id"] = observation["test_id"]
    write_json(output / "manifest.json", manifest)


def verify_runner_acceptance_failure(
    failed_path: Path,
    failed: dict[str, Any],
    repo: Repository,
) -> None:
    run_root = failed_path.parent.parent
    attempt_path = run_root / "accept-attempt.json"
    attempt = load_json(attempt_path, "acceptance attempt")
    run_id = failed["run_id"]
    if any(
        attempt.get(name) != value
        for name, value in (
            ("candidate_sha", repo.candidate_sha),
            ("mode", "acceptance"),
            ("run_id", run_id),
            ("status", "Started"),
        )
    ):
        raise GateFailure("debug acceptance attempt identity is invalid")
    attempt_reference = failed.get("acceptance_attempt")
    verify_checksum_reference(attempt_reference, "acceptance attempt")
    if Path(attempt_reference["path"]).resolve() != attempt_path.resolve():
        raise GateFailure("debug acceptance attempt path does not match the failed bundle")
    if not isinstance(failed.get("branch"), str) or not failed["branch"]:
        raise GateFailure("debug acceptance failure branch identity is missing")
    if failed.get("dirty_paths") != [] or failed.get("protected_paths_clean") is not True:
        raise GateFailure("debug acceptance failure protected-path identity is invalid")
    if not isinstance(failed.get("platform"), str) or not isinstance(failed.get("python"), dict):
        raise GateFailure("debug acceptance failure platform/Python identity is missing")
    if not isinstance(failed.get("command"), list) or not failed["command"]:
        raise GateFailure("debug acceptance failure command identity is missing")
    if not isinstance(failed.get("exit_code"), int) or failed["exit_code"] == 0:
        raise GateFailure("debug acceptance failure exit code is invalid")
    started = parse_timestamp(failed.get("started_at_utc"), "acceptance failure started_at_utc")
    ended = parse_timestamp(failed.get("ended_at_utc"), "acceptance failure ended_at_utc")
    if ended < started:
        raise GateFailure("debug acceptance failure end time predates start")
    raw_logs = failed.get("raw_logs")
    if not isinstance(raw_logs, list) or not raw_logs:
        raise GateFailure("debug acceptance failure raw-log identity is missing")
    if any(not isinstance(relative, str) or not (run_root / relative).is_file() for relative in raw_logs):
        raise GateFailure("debug acceptance failure raw-log file is missing")
    preflight_reference = failed.get("preflight")
    verify_checksum_reference(preflight_reference, "preflight")
    preflight_path = Path(preflight_reference["path"])
    if preflight_path.resolve() != (run_root / "preflight.json").resolve():
        raise GateFailure("debug preflight path does not belong to the failed acceptance run")
    preflight_result = load_json(preflight_path, "preflight result")
    if any(
        preflight_result.get(name) != value
        for name, value in (
            ("candidate_sha", repo.candidate_sha),
            ("mode", "acceptance"),
            ("run_id", run_id),
            ("status", "Pass"),
        )
    ):
        raise GateFailure("debug preflight identity does not match the failed acceptance run")
    chain = verify_preflight_chain(preflight_path, preflight_result)
    for name, expected in chain.items():
        if failed.get(name) != expected:
            raise GateFailure(f"debug acceptance failure {name} chain is missing or inconsistent")


def debug(args: argparse.Namespace, repo: Repository, output: Path) -> None:
    failed_path = Path(args.failed_acceptance).resolve()
    failed_acceptance = load_json(failed_path, "failed acceptance evidence")
    if any(
        failed_acceptance.get(name) != value
        for name, value in (("status", "Fail"), ("mode", "acceptance"), ("candidate_sha", repo.candidate_sha))
    ):
        raise GateFailure("debug requires a formal FAIL acceptance result for the same candidate")
    failed_run_id = failed_acceptance.get("run_id")
    if not isinstance(failed_run_id, str) or failed_run_id == args.run_id:
        raise GateFailure("debug must reference a distinct valid failed acceptance run ID")
    require_run_id(failed_run_id)
    if failed_path.name != "result.json" or failed_path.parent.name != "results" or failed_path.parent.parent.name != failed_run_id or failed_path.parent.parent.parent.name != "acceptance":
        raise GateFailure("debug failure input must be the result of its acceptance/<run-id> bundle")
    verify_runner_acceptance_failure(failed_path, failed_acceptance, repo)
    try:
        exit_code, counts, suite_argv = execute_suite(output, args.node, args.timeout_seconds, marker="rpi")
        status = "Diagnostic" if exit_code == 0 and all_zero(counts) else "Fail"
    except GateFailure as error:
        exit_code = 1
        counts = {"passed": 0, "failed": 1, "blocked": 0, "skipped": 0, "xfailed": 0}
        suite_argv = [sys.executable, "-m", "pytest", "-v", "-m", "rpi", args.node]
        status = "Fail"
        failure_reason = str(error)
    result = identity(repo, "debug", args.run_id, sys.argv)
    result.update(
        {
            "counts": counts,
            "ended_at_utc": utc_now(),
            "exit_code": exit_code,
            "failed_acceptance": checksum_reference(failed_path, "failed acceptance evidence"),
            "node": args.node,
            "raw_logs": ["logs/suite.stdout.log", "logs/suite.stderr.log"],
            "status": status,
            "suite_command": suite_argv,
            "timeout_seconds": args.timeout_seconds,
        }
    )
    if "failure_reason" in locals():
        result["reason"] = failure_reason
    write_json(output / "result.json", result)
    if status != "Diagnostic":
        raise GateFailure("debug node failed, timed out, was skipped, or does not exist")
    write_json(output / "manifest.json", result)


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--repo", default=".", help="repository root (default: current directory)")
    commands = command.add_subparsers(dest="command", required=True)

    def common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--candidate-sha", required=True)
        subparser.add_argument("--run-id", required=True)
        subparser.add_argument("--output", required=True)

    portable_parser = commands.add_parser("portable")
    common(portable_parser)
    portable_parser.add_argument("--python", required=True, choices=PORTABLE_MINORS)
    portable_parser.add_argument("--suite", required=True)
    portable_parser.add_argument("--test-id", action="append", required=True)
    portable_parser.add_argument("--timeout-seconds", required=True, type=float)

    preflight_parser = commands.add_parser("preflight")
    common(preflight_parser)
    preflight_parser.add_argument("--portable-index", required=True)
    preflight_parser.add_argument("--freeze-manifest", required=True)
    preflight_parser.add_argument("--runtime", required=True)
    preflight_parser.add_argument("--hardware", required=True)
    preflight_parser.add_argument("--config", required=True)
    preflight_parser.add_argument("--artifact-manifest", required=True)

    accept_parser = commands.add_parser("accept")
    common(accept_parser)
    accept_parser.add_argument("--preflight", required=True)
    accept_parser.add_argument("--suite", required=True)
    accept_parser.add_argument("--timeout-seconds", required=True, type=float)
    accept_parser.add_argument("--manual-timeout-seconds", required=True, type=float)
    accept_parser.add_argument("--readiness-timeout-seconds", required=True, type=float)
    accept_parser.add_argument("--test-id", required=True)
    accept_parser.add_argument("--ready-record", required=True)
    accept_parser.add_argument("--manual-observation", required=True)

    debug_parser = commands.add_parser("debug")
    common(debug_parser)
    debug_parser.add_argument("--node", required=True)
    debug_parser.add_argument("--failed-acceptance", required=True)
    debug_parser.add_argument("--timeout-seconds", required=True, type=float)

    matrix_parser = commands.add_parser("matrix")
    matrix_parser.add_argument("--candidate-sha", required=True)
    matrix_parser.add_argument("--run-id", required=True)
    matrix_parser.add_argument("--input-root", required=True)
    matrix_parser.add_argument("--output", required=True)
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    output = Path(args.output).resolve()
    started = utc_now()
    acceptance_was_reserved = args.command == "accept" and (output / "accept-attempt.json").exists()
    try:
        require_run_id(args.run_id)
        if args.command == "accept":
            # Acceptance consumes an existing preflight directory and must never recreate it.
            repo = inspect_repository(Path(args.repo).resolve(), args.candidate_sha)
            accept(args, repo, output)
        elif args.command == "matrix":
            repo = inspect_repository(Path(args.repo).resolve(), args.candidate_sha)
            build_matrix(args, repo)
        else:
            mode = "portable" if args.command == "portable" else ("acceptance" if args.command == "preflight" else args.command)
            prepare_output(output, mode, args.run_id)
            repo = inspect_repository(Path(args.repo).resolve(), args.candidate_sha)
            if args.command == "portable":
                portable(args, repo, output)
            elif args.command == "preflight":
                preflight(args, repo, output)
            else:
                debug(args, repo, output)
    except GateFailure as error:
        if not isinstance(error, RunReuseFailure) and not acceptance_was_reserved:
            write_failure(output if output.exists() else None, args.command, str(error), started)
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
