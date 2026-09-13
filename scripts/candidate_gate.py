#!/usr/bin/env python3
"""Minimal candidate and target test runner for M4 and later milestones."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import signal
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
PORTABLE_MINORS = ("3.11", "3.12", "3.13")
M4B_CANONICAL_SUITE = "tests/m4b_portable_suite.txt"
M4B_PROFILE_PATH = "requirements/m4b/product-profile.json"
M4B_BASELINE_PATH = "docs/test_spec/baselines/m4b_foundation_node_ids.txt"
M4B_PORTABLE_IDS = {
    "M4B-NORM-001": "tests/test_m4b_norm_001.py",
    "M4B-PROMPT-001": "tests/test_m4b_prompt_001.py",
    "M4B-SEM-001": "tests/test_m4b_sem_001.py",
    "M4B-S2-001": "tests/test_m4b_s2_001.py",
    "M4B-ADM-001": "tests/test_m4b_adm_001.py",
    "M4B-PREFILL-001": "tests/test_m4b_prefill_001.py",
    "M4B-OUTCOME-001": "tests/test_m4b_outcome_001.py",
    "M4B-CONV-001": "tests/test_m4b_conv_001.py",
    "M4B-MEM-001": "tests/test_m4b_mem_001.py",
    "M4B-REC-001": "tests/test_m4b_rec_001.py",
    "M4B-WIRE-001": "tests/test_m4b_wire_001.py",
    "M4B-PRIV-001": "tests/test_m4b_priv_001.py",
    "M4B-REG-001": "tests/test_m4b_reg_001.py",
}
PROTECTED_PATHS = (
    "src",
    "tests",
    "scripts",
    "native",
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
        "schema_version": 1,
        "start_monotonic_ns": time.monotonic_ns(),
        "started_at_utc": utc_now(),
    }


def _pytest_outcome_count(stdout: str, outcome: str) -> int:
    matches = re.findall(rf"(?<![A-Za-z0-9_])(\d+)\s+{re.escape(outcome)}\b", stdout.lower())
    return int(matches[-1]) if matches else 0


def suite_counts(junit: Path, stdout: str) -> dict[str, int]:
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0,
              "xfailed": 0, "xpassed": 0}
    if not junit.is_file():
        raise GateFailure("suite did not produce a JUnit result")
    try:
        root = ET.parse(junit).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
        for suite in suites:
            tests = int(suite.attrib.get("tests", "0"))
            failures = int(suite.attrib.get("failures", "0"))
            errors = int(suite.attrib.get("errors", "0"))
            skipped = int(suite.attrib.get("skipped", "0"))
            counts["failed"] += failures
            counts["errors"] += errors
            counts["skipped"] += skipped
            counts["passed"] += tests - failures - errors - skipped
    except (ET.ParseError, ValueError) as error:
        raise GateFailure(f"suite produced invalid JUnit: {error}") from error
    counts["xfailed"] = _pytest_outcome_count(stdout, "xfailed")
    counts["xpassed"] = _pytest_outcome_count(stdout, "xpassed")
    return counts


def _process_tree(root_pid: int) -> dict[int, int]:
    """Return the live Linux descendant PID -> PGID map, including root."""
    parents: dict[int, int] = {}
    proc = Path("/proc")
    if proc.is_dir():
        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                tail = (entry / "stat").read_text(encoding="ascii").rsplit(")", 1)[1].split()
                parents[int(entry.name)] = int(tail[1])
            except (OSError, ValueError, IndexError):
                continue
    owned = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if pid not in owned and parent in owned:
                owned.add(pid)
                changed = True
    result: dict[int, int] = {}
    for pid in owned:
        try:
            result[pid] = os.getpgid(pid)
        except ProcessLookupError:
            continue
    return result


def _live_group(tree: dict[int, int], pgid: int) -> bool:
    for pid, expected_group in tree.items():
        if expected_group != pgid:
            continue
        try:
            if os.getpgid(pid) != pgid:
                continue
            stat = Path("/proc") / str(pid) / "stat"
            if not stat.is_file() or stat.read_text(encoding="ascii").rsplit(")", 1)[1].split()[0] != "Z":
                return True
        except (OSError, ProcessLookupError, IndexError):
            continue
    return False


def _signal_process_tree(tree: dict[int, int], sig: signal.Signals, *, live_only: bool) -> None:
    own_group = os.getpgrp()
    for pgid in sorted(set(tree.values()), reverse=True):
        if pgid == own_group or (live_only and not _live_group(tree, pgid)):
            continue
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            continue


def _terminate_timed_out_suite(
    process: subprocess.Popen[str],
) -> tuple[str, str]:
    """Terminate pytest and any independently sessionized product descendants."""
    tree = _process_tree(process.pid)
    _signal_process_tree(tree, signal.SIGTERM, live_only=False)
    try:
        stdout, stderr = process.communicate(timeout=2.0)
    except subprocess.TimeoutExpired:
        _signal_process_tree(tree, signal.SIGKILL, live_only=True)
        try:
            stdout, stderr = process.communicate(timeout=2.0)
        except subprocess.TimeoutExpired as error:
            raise GateFailure("timed-out suite process tree could not be reaped") from error
    else:
        # A top-level pytest can exit while a child-created process group is
        # still alive and no longer holds the pytest stdout/stderr pipes.
        _signal_process_tree(tree, signal.SIGKILL, live_only=True)
    return stdout, stderr


def _network_attempt_count(trace: Path) -> int:
    if not trace.is_file():
        raise GateFailure("M4a network audit did not produce a trace")
    destination_attempt = re.compile(
        r"\b(?:connect|sendto|sendmsg|sendmmsg)\([^\n]*\bAF_INET6?\b"
    )
    return sum(
        1
        for line in trace.read_text(encoding="utf-8", errors="replace").splitlines()
        if destination_attempt.search(line)
    )


def execute_pytest(
    repo: Repository,
    output: Path,
    target: str,
    marker: str,
    timeout_seconds: float,
    *,
    mode: str,
    run_id: str,
) -> tuple[int, dict[str, int], list[str], list[str], int | None]:
    if timeout_seconds <= 0:
        raise GateFailure("timeout seconds must be greater than zero")
    junit = output / "junit.xml"
    targets = [target]
    manifest = (repo.root / target).resolve() if not Path(target).is_absolute() else Path(target).resolve()
    if target.endswith(".txt"):
        if not manifest.is_file() or not manifest.is_relative_to(repo.root):
            raise GateFailure("suite manifest must be a tracked repository file")
        targets = [line.strip() for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not targets:
            raise GateFailure("suite manifest must contain at least one test path")
        for item in targets:
            item_path = (repo.root / item).resolve()
            if item.startswith("-") or not item_path.is_file() or not item_path.is_relative_to(repo.root / "tests"):
                raise GateFailure("suite manifest contains an invalid test path")
    argv = [sys.executable, "-m", "pytest", "-v", "-m", marker, *targets, f"--junitxml={junit}"]
    stdout_path = output / "logs" / "suite.stdout.log"
    stderr_path = output / "logs" / "suite.stderr.log"
    raw_logs = ["logs/suite.stdout.log", "logs/suite.stderr.log"]
    target_path = (repo.root / target).resolve() if not Path(target).is_absolute() else Path(target).resolve()
    m4_target_audit = (
        mode == "acceptance"
        and target_path == (repo.root / "tests" / "milestones" / "test_m4_local_voice.py").resolve()
    )
    network_trace = output / "logs" / "network.trace.log"
    launch_argv = argv
    if m4_target_audit:
        strace = shutil.which("strace")
        if strace is None:
            raise GateFailure("M4a target acceptance requires strace network auditing")
        launch_argv = [
            strace, "-f", "-qq", "-e", "trace=network",
            "-o", str(network_trace), "--", *argv,
        ]
        raw_logs.append("logs/network.trace.log")
    try:
        environment = os.environ.copy()
        # The formal runner is itself a production launch boundary.  Set the
        # native thread policy before pytest imports controller audio modules.
        environment["OPENBLAS_NUM_THREADS"] = "1"
        source_root = str(repo.root / "src")
        environment["PYTHONPATH"] = source_root
        for name in (
            "SBD_M4A_CANDIDATE_SHA", "SBD_M4A_ACCEPTANCE_RUN_ID",
            "SBD_M4A_CARD_ROOT", "SBD_M4A_RUNNER_PREFLIGHT",
            "SBD_M4B_CANDIDATE_SHA", "SBD_M4B_ACCEPTANCE_RUN_ID",
            "SBD_M4B_CARD_ROOT", "SBD_M4B_RUNNER_PREFLIGHT",
            "SBD_M4B_PRODUCT_PREFLIGHT",
            "SBD_M4A_TARGET_CONFIG",
        ):
            environment.pop(name, None)
        if mode == "acceptance":
            card_root = output / "cards"
            if card_root.exists():
                raise GateFailure("acceptance card output already exists")
            card_root.mkdir()
            environment.update({
                "SBD_M4A_CANDIDATE_SHA": repo.candidate_sha,
                "SBD_M4A_ACCEPTANCE_RUN_ID": run_id,
                "SBD_M4A_CARD_ROOT": str(card_root),
                "SBD_M4A_RUNNER_PREFLIGHT": str((output / "preflight.json").resolve()),
                "SBD_M4B_CANDIDATE_SHA": repo.candidate_sha,
                "SBD_M4B_ACCEPTANCE_RUN_ID": run_id,
                "SBD_M4B_CARD_ROOT": str(card_root),
                "SBD_M4B_RUNNER_PREFLIGHT": str((output / "preflight.json").resolve()),
            })
            runner_preflight = load_json(output / "preflight.json", "runner preflight")
            config_reference = runner_preflight.get("checksums", {}).get("config")
            if not isinstance(config_reference, dict) or not isinstance(config_reference.get("path"), str):
                raise GateFailure("runner preflight config reference is invalid")
            environment["SBD_M4A_TARGET_CONFIG"] = config_reference["path"]
            m4b_product = runner_preflight.get("checksums", {}).get("m4b_artifact_manifest")
            if isinstance(m4b_product, dict) and isinstance(m4b_product.get("path"), str):
                environment["SBD_M4B_PRODUCT_PREFLIGHT"] = m4b_product["path"]
        process = subprocess.Popen(
            launch_argv,
            cwd=repo.root,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as error:
            stdout, stderr = _terminate_timed_out_suite(process)
            stdout_path.write_text(stdout, encoding="utf-8")
            stderr_path.write_text(stderr + f"\nTIMEOUT after {timeout_seconds} seconds\n", encoding="utf-8")
            raise GateFailure(f"suite timeout after {timeout_seconds} seconds") from error
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
    except subprocess.TimeoutExpired as error:
        # Defensive fallback for a platform-specific Popen implementation.
        stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else (error.stdout or "")
        stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else (error.stderr or "")
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr + f"\nTIMEOUT after {timeout_seconds} seconds\n", encoding="utf-8")
        raise GateFailure(f"suite timeout after {timeout_seconds} seconds") from error
    network_attempt_count: int | None = None
    if m4_target_audit:
        network_attempt_count = _network_attempt_count(network_trace)
        if network_attempt_count:
            raise GateFailure("M4 target suite attempted IPv4/IPv6 network I/O")
    return process.returncode, suite_counts(junit, stdout), argv, raw_logs, network_attempt_count


def passed(exit_code: int, counts: dict[str, int]) -> bool:
    return exit_code == 0 and all(
        counts.get(name) == 0
        for name in ("failed", "errors", "skipped", "xfailed", "xpassed")
    )


M4B_TARGET_IDS = frozenset(f"M4B-PI-{name}-001" for name in
    ("ATT", "SEM", "CONV", "MEM", "WAKE", "TIME", "RES"))
M4B_CARD_FIELDS = frozenset({"schema_version", "test_id", "case_id", "candidate_sha", "profile_id",
    "profile_sha256", "matrix", "platform", "python", "start_monotonic_ns", "end_monotonic_ns",
    "status", "evidence_sha256"})
M4B_CARD_REQUIRED = {test_id: M4B_CARD_FIELDS for test_id in M4B_TARGET_IDS}


def m4b_collection_audit(baseline: bytes, collected: list[str]) -> dict[str, Any]:
    """Exact immutable Foundation comparison; no set coercion hides duplicates."""
    try:
        expected = baseline.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        raise GateFailure("M4B_BASELINE_INVALID") from None
    if (len(expected) != 99 or expected != sorted(set(expected))
            or any("::" not in node for node in expected)
            or len(collected) != len(set(collected)) or any("::" not in node for node in collected)):
        raise GateFailure("M4B_COLLECTION_INVALID")
    missing = sorted(set(expected) - set(collected))
    if missing:
        raise GateFailure("M4B_FOUNDATION_NODES_MISSING")
    normalized = ("\n".join(sorted(collected)) + "\n").encode("utf-8")
    return {"baseline_count": 99, "retained_count": 99, "missing_count": 0,
        "baseline_sha256": hashlib.sha256(baseline).hexdigest(),
        "collected_sha256": hashlib.sha256(normalized).hexdigest(),
        "missing_sha256": hashlib.sha256(b"").hexdigest()}


def m4b_source_violations(source: str) -> list[tuple[int, str]]:
    """Resolve pytest aliases and constant-only assertions in affected sources."""
    import ast
    tree = ast.parse(source)
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    def resolve(node):
        if isinstance(node, ast.Name):
            return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return f"{resolve(node.value)}.{node.attr}"
        return ""
    for _ in range(len(tuple(ast.walk(tree)))):
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                name = resolve(node.value)
                for target in node.targets:
                    if isinstance(target, ast.Name) and name and aliases.get(target.id) != name:
                        aliases[target.id] = name
                        changed = True
        if not changed:
            break
    forbidden = {"pytest.skip", "pytest.xfail", "pytest.importorskip", "pytest.mark.skip",
                 "pytest.mark.skipif", "pytest.mark.xfail", "pytest.mark.rpi"}
    violations = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Call, ast.Attribute, ast.Name)):
            name = resolve(node.func if isinstance(node, ast.Call) else node)
            if name in forbidden:
                violations.add((node.lineno, "FORBIDDEN_TEST_CONTROL"))
        if isinstance(node, ast.Assert) and not any(isinstance(n, (ast.Name, ast.Call, ast.Attribute,
                ast.Subscript, ast.Await, ast.NamedExpr)) for n in ast.walk(node.test)):
            violations.add((node.lineno, "CONSTANT_ASSERTION"))
    return sorted(violations)


def m4b_junit_audit(payload: bytes, expected_nodes: list[str]) -> dict[str, int]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        raise GateFailure("M4B_JUNIT_INVALID") from None
    cases = root.findall(".//testcase")
    expected_identities = {}
    for node in expected_nodes:
        parts = node.split("::")
        classname = parts[0].removesuffix(".py").replace("/", ".")
        if len(parts) > 2:
            classname += "." + ".".join(parts[1:-1])
        identity = (classname, parts[-1])
        if identity in expected_identities:
            raise GateFailure("M4B_JUNIT_NODE_MISMATCH")
        expected_identities[identity] = node
    actual = []
    for case in cases:
        if (case.find("failure") is not None or case.find("error") is not None
                or case.find("skipped") is not None or "wasxfail" in case.attrib
                or any("xfail" in str(p.attrib).lower() for p in case.findall("./properties/property"))):
            raise GateFailure("M4B_JUNIT_NOT_PASS")
        identity = (case.get("classname", ""), case.get("name", ""))
        if identity not in expected_identities:
            raise GateFailure("M4B_JUNIT_NODE_MISMATCH")
        actual.append(expected_identities[identity])
    if not actual or len(actual) != len(set(actual)) or set(actual) != set(expected_nodes):
        raise GateFailure("M4B_JUNIT_NODE_MISMATCH")
    return {"passed": len(actual), "failed": 0, "errors": 0, "skipped": 0, "xfailed": 0, "xpassed": 0}


def m4b_catalog_paths(root: Path) -> list[str]:
    path = root / "tests/m4b_portable_suite.txt"
    try:
        selectors = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        raise GateFailure("M4B_CATALOG_UNAVAILABLE") from None
    if (not selectors or len(selectors) != len(set(selectors))
            or any(not s.startswith("tests/") or ".." in PurePosixPath(s.split("::")[0]).parts
                   or not root.joinpath(s.split("::")[0]).is_file() for s in selectors)):
        raise GateFailure("M4B_CATALOG_INCOMPLETE")
    return selectors


def _m4b_candidate(root: Path) -> bool:
    return root.joinpath(M4B_PROFILE_PATH).is_file()


def _m4b_profile_identity(root: Path) -> tuple[str, str]:
    profile = load_json(root / M4B_PROFILE_PATH, "M4B product profile")
    profile_id = profile.get("profile_id")
    profile_sha256 = profile.get("profile_sha256")
    content = {key: value for key, value in profile.items() if key != "profile_sha256"}
    try:
        encoded = json.dumps(content, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise GateFailure("M4B_PROFILE_IDENTITY_INVALID") from None
    if (profile_id != "core-m4b-cognition-001"
            or not isinstance(profile_sha256, str)
            or hashlib.sha256(encoded).hexdigest() != profile_sha256):
        raise GateFailure("M4B_PROFILE_IDENTITY_INVALID")
    return profile_id, profile_sha256


def _m4b_canonical_targets(repo: Repository, suite: str) -> tuple[list[str], str]:
    if suite != M4B_CANONICAL_SUITE or Path(suite).is_absolute():
        raise GateFailure(f"M4B portable suite must be exactly {M4B_CANONICAL_SUITE}")
    manifest = repo.root / M4B_CANONICAL_SUITE
    baseline = repo.root / M4B_BASELINE_PATH
    tracked = set(run_git(repo.root, "ls-files", "--", M4B_CANONICAL_SUITE,
                          M4B_PROFILE_PATH, M4B_BASELINE_PATH).splitlines())
    if tracked != {M4B_CANONICAL_SUITE, M4B_PROFILE_PATH, M4B_BASELINE_PATH}:
        raise GateFailure("M4B canonical suite/profile/baseline must be tracked candidate inputs")
    selectors = m4b_catalog_paths(repo.root)
    selected_paths = {selector.split("::", 1)[0] for selector in selectors}
    if not set(M4B_PORTABLE_IDS.values()) <= selected_paths:
        raise GateFailure("M4B_CATALOG_INCOMPLETE")
    tracked_selectors = set(run_git(repo.root, "ls-files", "--", *sorted(selected_paths)).splitlines())
    if tracked_selectors != selected_paths:
        raise GateFailure("M4B catalog contains an untracked test path")
    return selectors, sha256(manifest, "M4B canonical suite")


def _m4b_collect_nodes(
    repo: Repository, output: Path, targets: list[str], timeout_seconds: float,
) -> tuple[list[str], list[str]]:
    stdout_path = output / "logs" / "collection.stdout.log"
    stderr_path = output / "logs" / "collection.stderr.log"
    nodes_path = output / "collection-node-ids.txt"
    argv = [sys.executable, "-m", "pytest", "-o", "addopts=", "--collect-only", "-q",
            "-m", "not rpi", *targets]
    environment = os.environ.copy()
    environment["OPENBLAS_NUM_THREADS"] = "1"
    environment["PYTHONPATH"] = str(repo.root / "src")
    process = subprocess.Popen(
        argv, cwd=repo.root, env=environment, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as error:
        stdout, stderr = _terminate_timed_out_suite(process)
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr + "\nCOLLECTION TIMEOUT\n", encoding="utf-8")
        raise GateFailure("M4B canonical collection timed out") from error
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    if process.returncode:
        raise GateFailure("M4B canonical collection failed")
    nodes = [line.strip() for line in stdout.splitlines()
             if line.startswith("tests/") and "::" in line]
    if not nodes or len(nodes) != len(set(nodes)):
        raise GateFailure("M4B_COLLECTION_INVALID")
    nodes_path.write_text("\n".join(nodes) + "\n", encoding="utf-8")
    return nodes, ["logs/collection.stdout.log", "logs/collection.stderr.log"]


def _m4b_foundation_evidence(root: Path, junit: Path) -> dict[str, Any]:
    baseline = root.joinpath(M4B_BASELINE_PATH).read_bytes()
    baseline_nodes = baseline.decode("utf-8").splitlines()
    expected = m4b_collection_audit(baseline, baseline_nodes)
    try:
        document = ET.parse(junit).getroot()
    except ET.ParseError:
        raise GateFailure("M4B_JUNIT_INVALID") from None
    cases = [case for case in document.findall(".//testcase")
             if case.get("classname") == "tests.test_m4b_reg_001"
             and case.get("name", "").startswith("test_G02_exact_99_nodes")]
    if len(cases) != 1:
        raise GateFailure("M4B_FOUNDATION_EVIDENCE_MISSING")
    properties = {item.get("name"): item.get("value")
                  for item in cases[0].findall("./properties/property")}
    if any(properties.get(name) != str(value) for name, value in expected.items()):
        raise GateFailure("M4B_FOUNDATION_EVIDENCE_MISMATCH")
    return expected


def _m4b_test_id_evidence(nodes: list[str]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for test_id, path in M4B_PORTABLE_IDS.items():
        selected = [node for node in nodes if node.startswith(path + "::")]
        if not selected:
            raise GateFailure(f"M4B_TEST_ID_EVIDENCE_MISSING:{test_id}")
        payload = ("\n".join(selected) + "\n").encode("utf-8")
        evidence[test_id] = {
            "collected_count": len(selected),
            "passed_count": len(selected),
            "node_ids_sha256": hashlib.sha256(payload).hexdigest(),
            "status": "Pass",
        }
    return evidence


def _m4b_source_audit(root: Path, targets: list[str]) -> str:
    baseline = root.joinpath(M4B_BASELINE_PATH).read_text(encoding="utf-8").splitlines()
    paths = {node.split("::", 1)[0] for node in baseline}
    paths.update(selector.split("::", 1)[0] for selector in targets
                 if Path(selector.split("::", 1)[0]).name.startswith("test_m4b"))
    digest = hashlib.sha256()
    violations: list[str] = []
    for relative in sorted(paths):
        payload = root.joinpath(relative).read_bytes()
        digest.update(relative.encode("utf-8") + b"\0" + payload)
        source = payload.decode("utf-8")
        violations.extend(f"{relative}:{line}:{reason}"
                          for line, reason in m4b_source_violations(source))
    if violations:
        raise GateFailure("M4B_SOURCE_AUDIT_FAILED:" + ",".join(violations[:10]))
    return digest.hexdigest()


def _m4b_portable_precheck(
    repo: Repository, output: Path, suite: str, timeout_seconds: float,
) -> dict[str, Any]:
    profile_id, profile_sha256 = _m4b_profile_identity(repo.root)
    targets, catalog_sha256 = _m4b_canonical_targets(repo, suite)
    system = platform.system()
    machine = platform.machine().lower()
    if system != "Linux" or machine not in {"x86_64", "aarch64"}:
        raise GateFailure("M4B formal portable execution requires Linux x86_64/aarch64")
    source_sha256 = _m4b_source_audit(repo.root, targets)
    nodes, logs = _m4b_collect_nodes(repo, output, targets, timeout_seconds)
    collection_path = output / "collection-node-ids.txt"
    return {
        "catalog_paths": targets,
        "catalog_sha256": catalog_sha256,
        "collection_count": len(nodes),
        "collection_locator": "collection-node-ids.txt",
        "collection_sha256": sha256(collection_path, "M4B collection node list"),
        "collection_nodes": nodes,
        "platform_identity": {"system": system, "machine": machine},
        "profile_id": profile_id,
        "profile_sha256": profile_sha256,
        "source_audit_sha256": source_sha256,
        "precheck_logs": logs,
    }


def _draft_contains_absolute(value: object) -> bool:
    if type(value) is dict:
        return any(_draft_contains_absolute(item) for item in value.values())
    if type(value) is list:
        return any(_draft_contains_absolute(item) for item in value)
    return type(value) is str and value.startswith("/")


def _relative_locator(value: object) -> bool:
    if type(value) is not str or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def _validate_m4b_card(draft: dict[str, Any], *, evidence_resolver=None) -> None:
    """Reconcile private digest-bound proofs without putting their content in cards."""
    for directory in (Path(__file__).resolve().parents[1], Path(__file__).resolve().parents[1] / "src"):
        if str(directory) not in sys.path:
            sys.path.insert(0, str(directory))
    from scripts.m4b_inheritance import InheritanceError, validate_result_record
    if draft.get("test_id") not in M4B_TARGET_IDS:
        raise GateFailure("M4B_RETIRED_OR_UNKNOWN_TARGET_ID")
    try:
        validate_result_record(draft, candidate_sha=draft.get("candidate_sha", ""),
                               profile_sha256=draft.get("profile_sha256", ""))
    except (InheritanceError, TypeError, ValueError):
        raise GateFailure("M4B_TARGET_METADATA_INVALID") from None
    if evidence_resolver is None:
        raise GateFailure("M4B_PRIVATE_PROOF_INCOMPLETE")
    try:
        raw = evidence_resolver(draft["evidence_sha256"])
        if type(raw) is not bytes or hashlib.sha256(raw).hexdigest() != draft["evidence_sha256"]:
            raise ValueError
        proof = json.loads(raw)
        if (type(proof) is not dict or set(proof) != {
                "schema_version", "test_id", "candidate_sha", "profile_sha256", "data"}
                or proof["schema_version"] != 1 or type(proof["schema_version"]) is not int
                or any(proof[k] != draft[k] for k in ("test_id", "candidate_sha", "profile_sha256"))
                or draft["status"] != "Pass" or type(proof["data"]) is not dict):
            raise ValueError
        _m4b_validate_proof(draft, proof["data"], evidence_resolver)
    except Exception:
        raise GateFailure("M4B_PRIVATE_PROOF_INVALID") from None


def _m4b_exact(value, fields):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError


def _m4b_digest(value):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError


def _m4b_raw_artifact(digest, resolver):
    _m4b_digest(digest)
    payload = resolver(digest)
    if type(payload) is not bytes or not payload or hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError
    return payload


def _m4b_true(value):
    if value is not True:
        raise ValueError


def _m4b_int(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError


def _m4b_sample(value):
    from sbd.cognition.litert_lm.resource import ProcessResource, SystemResourceSample
    _m4b_exact(value, {"monotonic_ns", "processes", "mem_total_bytes", "mem_available_bytes",
        "swap_used_bytes", "oom_kill", "temperature_c", "throttled_bits"})
    if type(value["processes"]) is not list:
        raise ValueError
    processes = []
    for row in value["processes"]:
        _m4b_exact(row, {"pid", "owner", "start_time_ticks", "pss_bytes", "rss_bytes", "cpu_seconds", "threads"})
        owner = row["owner"]
        if type(owner) is list:
            if len(owner) != len(set(owner)):
                raise ValueError
            owner = frozenset(owner)
        processes.append(ProcessResource(**{**row, "owner": owner}))
    sample = SystemResourceSample(**{**value, "processes": tuple(processes)})
    sample.validate()
    return sample


def _m4b_validate_proof(record, data, resolver):
    from sbd.cognition.litert_lm.lock import (LLMArtifactLock, load_product_profile,
        validate_product_profile, EXPECTED_MODEL, EXPECTED_RUNTIME)
    from sbd.cognition.observability import timing_row
    test_id = record["test_id"]
    if test_id == "M4B-PI-ATT-001":
        _m4b_exact(data, {"profile", "ready_identity", "artifacts", "target", "capture"})
        profile = validate_product_profile(data["profile"])
        if profile["profile_sha256"] != record["profile_sha256"]:
            raise ValueError
        lock_path = Path(__file__).resolve().parents[1] / "requirements/m4b/llm-artifacts.json"
        lock = LLMArtifactLock.load(lock_path)
        if data["ready_identity"] != lock.ready_identity(profile).fields:
            raise ValueError
        lock_data = json.loads(lock_path.read_bytes())
        expected_artifacts = {name: EXPECTED_RUNTIME[name] for name in
            ("wheel_filename", "wheel_size_bytes", "wheel_sha256", "native_relative_path", "native_size_bytes", "native_sha256")}
        expected_artifacts.update(model_filename=EXPECTED_MODEL["filename"], model_size_bytes=EXPECTED_MODEL["size_bytes"],
            model_sha256=EXPECTED_MODEL["sha256"], lock_sha256=lock.digest,
            runtime_manifest_sha256=lock_data["runtime_closure"]["manifest_sha256"], runtime_file_count=14,
            notice_sha256=lock_data["licenses"]["notice_sha256"])
        _m4b_exact(data["artifacts"], expected_artifacts)
        if any(type(data["artifacts"][k]) is not type(v) or data["artifacts"][k] != v for k, v in expected_artifacts.items()):
            raise ValueError
        target = data["target"]
        _m4b_exact(target, {"clean_worktree", "candidate_sha", "platform", "python", "soabi", "multiarch",
                            "pid", "pgid", "prewarm_count", "conversation_count", "kernel_sha256",
                            "deployment_files_verified", "system_site_packages", "extra_artifact_count", "alternate_endpoint_count"})
        _m4b_true(target["clean_worktree"])
        _m4b_true(target["deployment_files_verified"])
        if target["system_site_packages"] is not False:
            raise ValueError
        _m4b_digest(target["kernel_sha256"])
        if (target["candidate_sha"] != record["candidate_sha"] or target["platform"] != record["platform"]
                or target["python"] != "3.13.5" or target["soabi"] != "cpython-313-aarch64-linux-gnu"
                or target["multiarch"] != "aarch64-linux-gnu" or target["pid"] != target["pgid"]):
            raise ValueError
        _m4b_int(target["pid"], 1)
        _m4b_int(target["pgid"], 1)
        for name in ("prewarm_count", "conversation_count", "extra_artifact_count", "alternate_endpoint_count"):
            _m4b_int(target[name])
            if target[name] != 0:
                raise ValueError
        _m4b_exact(data["capture"], {"before_native_import", "through_child_exit", "network_attempts",
                                    "downloader_calls", "telemetry_calls", "dns_calls", "fallback_calls"})
        for name, value in data["capture"].items():
            if name in {"before_native_import", "through_child_exit"}:
                _m4b_true(value)
            else:
                _m4b_int(value)
                if value:
                    raise ValueError
    elif test_id == "M4B-PI-SEM-001":
        _m4b_exact(data, {"cases"})
        cases = data["cases"]
        if type(cases) is not list or len(cases) != 9 or {c["case_id"] for c in cases} != {f"H{i:02}" for i in range(1, 10)}:
            raise ValueError
        by_id = {}
        for case in cases:
            _m4b_exact(case, {"case_id", "answer_sha256", "end", "spoken_length", "structural_pass",
                "conversation_generation", "turn_index", "farewell_before_rest", "rubric"})
            _m4b_raw_artifact(case["answer_sha256"], resolver)
            _m4b_true(case["structural_pass"])
            _m4b_int(case["spoken_length"], 1)
            _m4b_int(case["conversation_generation"], 1)
            _m4b_int(case["turn_index"], 1)
            if case["spoken_length"] > 30 or type(case["end"]) is not bool or case["end"] != (case["case_id"] == "H05"):
                raise ValueError
            if case["case_id"] == "H05":
                _m4b_true(case["farewell_before_rest"])
            elif case["farewell_before_rest"] is not None:
                raise ValueError
            rubric = case["rubric"]
            _m4b_exact(rubric, {"reviewer", "correct_relevant", "capability_honest", "end_polarity",
                "traditional_chinese", "personality_applicable", "personality_present", "concise"})
            if type(rubric["reviewer"]) is not str or not rubric["reviewer"].strip():
                raise ValueError
            for name in ("correct_relevant", "capability_honest", "end_polarity", "traditional_chinese", "concise"):
                _m4b_true(rubric[name])
            if type(rubric["personality_applicable"]) is not bool:
                raise ValueError
            if case["case_id"] == "H07" or rubric["personality_applicable"]:
                _m4b_true(rubric["personality_applicable"])
                _m4b_true(rubric["personality_present"])
            elif rubric["personality_present"] is not None:
                raise ValueError
            by_id[case["case_id"]] = case
        if (by_id["H08"]["conversation_generation"] != by_id["H09"]["conversation_generation"]
                or by_id["H09"]["turn_index"] != by_id["H08"]["turn_index"] + 1):
            raise ValueError
    elif test_id == "M4B-PI-CONV-001":
        _m4b_exact(data, {"events", "same_product_session", "rejected_send_count", "rejected_mutation_count",
            "automatic_replay_count", "old_context_absent", "new_context_works"})
        for key in ("same_product_session", "old_context_absent", "new_context_works"):
            _m4b_true(data[key])
        for key in ("rejected_send_count", "rejected_mutation_count", "automatic_replay_count"):
            _m4b_int(data[key])
            if data[key]:
                raise ValueError
        events = data["events"]
        names = ["context_rejected", "primary_terminal", "close_proven", "open_ready", "human_repeat",
                 "repeat_success", "following_success"]
        if type(events) is not list or [e["event"] for e in events] != names:
            raise ValueError
        previous_ns = -1
        for index, event in enumerate(events):
            _m4b_exact(event, {"event", "monotonic_ns", "generation", "turn_index", "proofs"})
            _m4b_int(event["monotonic_ns"])
            _m4b_int(event["generation"], 1)
            _m4b_int(event["turn_index"], 1)
            if event["monotonic_ns"] < previous_ns:
                raise ValueError
            previous_ns = event["monotonic_ns"]
            if event["generation"] != events[0]["generation"] + (1 if index >= 3 else 0):
                raise ValueError
            if event["event"] == "close_proven":
                _m4b_exact(event["proofs"], {"closed", "history_clear", "kv_released"})
                for value in event["proofs"].values():
                    _m4b_true(value)
            elif event["proofs"] is not None:
                raise ValueError
        if not events[0]["turn_index"] < events[4]["turn_index"] == events[5]["turn_index"] < events[6]["turn_index"]:
            raise ValueError
    elif test_id == "M4B-PI-MEM-001":
        from scripts.m4b_target_metrics import (MeasurementPoint, freeze_release_profile_automatic)
        from sbd.cognition.litert_lm.resource import memory_decision
        _m4b_exact(data, {"measurement_profile", "measurement_attestation", "points", "release_profile",
            "completed", "cleanup_proven", "measurement_run_sha256", "release_run_sha256", "release_rows",
            "recovery_ready", "new_turn_success"})
        measured = validate_product_profile(data["measurement_profile"], allow_measurement=True)
        expected = {"schema_version": 1, "candidate_sha": record["candidate_sha"],
            "profile_sha256": measured["profile_sha256"], "target_identity": "pi5-4gb-debian13-aarch64-cp3135",
            "harness_sha256": hashlib.sha256(Path(__file__).with_name("m4b_measurement.py").read_bytes()).hexdigest()}
        _m4b_exact(data["measurement_attestation"], set(expected))
        if data["measurement_attestation"] != expected:
            raise ValueError
        for name in ("measurement_run_sha256", "release_run_sha256"):
            _m4b_raw_artifact(data[name], resolver)
        if data["measurement_run_sha256"] == data["release_run_sha256"]:
            raise ValueError
        measurement_raw = json.loads(_m4b_raw_artifact(data["measurement_run_sha256"], resolver))
        if measurement_raw != data["points"]:
            raise ValueError
        points = []
        for row in data["points"]:
            _m4b_exact(row, {"lifecycle_point", "operation_index", "sample"})
            points.append(MeasurementPoint(row["lifecycle_point"], row["operation_index"], _m4b_sample(row["sample"])))
        release = freeze_release_profile_automatic(measured, points, evidence_sha256=data["measurement_run_sha256"],
            completed=data["completed"], cleanup_proven=data["cleanup_proven"])
        if release != data["release_profile"] or release["profile_sha256"] != record["profile_sha256"]:
            raise ValueError
        release_raw = json.loads(_m4b_raw_artifact(data["release_run_sha256"], resolver))
        if release_raw != {"rows": data["release_rows"], "profile_sha256": release["profile_sha256"]}:
            raise ValueError
        observed = set()
        for row in data["release_rows"]:
            _m4b_exact(row, {"sample", "decision", "generate_calls", "tts_calls", "recycle_pending"})
            sample = _m4b_sample(row["sample"])
            decision = memory_decision(sample,
                min_mem_available_speak_bytes=release["min_mem_available_speak_bytes"],
                min_mem_available_generate_bytes=release["min_mem_available_generate_bytes"])
            if row["decision"] != decision.value or row["generate_calls"] != (1 if decision.value == "GENERATE" else 0):
                raise ValueError
            _m4b_int(row["generate_calls"])
            _m4b_int(row["tts_calls"])
            if decision.value == "SILENT" and row["tts_calls"] != 0:
                raise ValueError
            if decision.value == "NOTICE" and row["tts_calls"] != 1:
                raise ValueError
            if type(row["recycle_pending"]) is not bool or row["recycle_pending"] != (decision.value != "GENERATE"):
                raise ValueError
            observed.add(sample.mem_available_bytes)
        speak, generate = release["min_mem_available_speak_bytes"], release["min_mem_available_generate_bytes"]
        if not {speak, speak - 1, generate, generate - 1}.issubset(observed):
            raise ValueError
        _m4b_true(data["recovery_ready"])
        _m4b_true(data["new_turn_success"])
    elif test_id == "M4B-PI-WAKE-001":
        _m4b_exact(data, {"cases"})
        cases = data["cases"]
        if type(cases) is not list or {r["case"] for r in cases} != {"open_first", "ack_first", "slow_open", "interrupt_open"} or len(cases) != 4:
            raise ValueError
        for row in cases:
            _m4b_exact(row, {"case", "wake_ack_ns", "open_ready_ns", "open_join_ns", "activity",
                "display_blocked", "display_fact_count", "display_turn_count", "cleanup_proven"})
            if row["display_blocked"] is not False or row["display_fact_count"] != 0 or row["display_turn_count"] != 0:
                raise ValueError
            _m4b_int(row["display_fact_count"])
            _m4b_int(row["display_turn_count"])
            if row["case"] == "interrupt_open":
                if row["activity"] != [] or row["open_ready_ns"] is not None or row["open_join_ns"] is not None:
                    raise ValueError
                _m4b_true(row["cleanup_proven"])
                continue
            for name in ("wake_ack_ns", "open_ready_ns", "open_join_ns"):
                _m4b_int(row[name])
            if row["open_join_ns"] < row["open_ready_ns"]:
                raise ValueError
            if row["case"] == "open_first" and row["open_ready_ns"] > row["wake_ack_ns"]:
                raise ValueError
            if row["case"] in {"ack_first", "slow_open"} and row["wake_ack_ns"] > row["open_ready_ns"]:
                raise ValueError
            if {e["kind"] for e in row["activity"]} != {"audio_pull", "listen", "asr", "perception", "reasoner"}:
                raise ValueError
            for event in row["activity"]:
                _m4b_exact(event, {"kind", "monotonic_ns"})
                _m4b_int(event["monotonic_ns"])
                if event["monotonic_ns"] < max(row["wake_ack_ns"], row["open_join_ns"]):
                    raise ValueError
    elif test_id == "M4B-PI-TIME-001":
        _m4b_exact(data, {"rows", "clock_mapping_sha256", "mapping_verified"})
        _m4b_raw_artifact(data["clock_mapping_sha256"], resolver)
        _m4b_true(data["mapping_verified"])
        if type(data["rows"]) is not list or not data["rows"]:
            raise ValueError
        for row in data["rows"]:
            _m4b_exact(row, {"clock_domain", "events", "null_reasons"})
            timing_row(**row)
    elif test_id == "M4B-PI-RES-001":
        _m4b_exact(data, {"runs", "cleanup", "scan"})
        if type(data["runs"]) is not list or {r["stage"] for r in data["runs"]} != {"measurement", "release"} or len(data["runs"]) != 2:
            raise ValueError
        for run in data["runs"]:
            counters = {"network_attempts", "swap_growth_bytes", "oom_delta", "kernel_faults", "throttled_bits",
                        "temperature_stop_violations", "orphans", "duplicate_pids", "owner_leaks"}
            _m4b_exact(run, counters | {"stage", "run_sha256"})
            _m4b_raw_artifact(run["run_sha256"], resolver)
            for name in counters:
                _m4b_int(run[name])
                if run[name]:
                    raise ValueError
        if data["runs"][0]["run_sha256"] == data["runs"][1]["run_sha256"]:
            raise ValueError
        cleanup = data["cleanup"]
        if type(cleanup) is not list or {r["kind"] for r in cleanup} != {"normal_close", "planned_recovery", "forced_pgid", "shutdown"} or len(cleanup) != 4:
            raise ValueError
        for row in cleanup:
            _m4b_exact(row, {"kind", "start_ns", "exit_ns", "deadline_ns", "remaining_owners", "remaining_descendants", "recovery_success"})
            for name in ("start_ns", "exit_ns", "deadline_ns", "remaining_owners", "remaining_descendants"):
                _m4b_int(row[name])
            if not row["start_ns"] <= row["exit_ns"] <= row["deadline_ns"] or row["remaining_owners"] or row["remaining_descendants"]:
                raise ValueError
            if row["kind"] in {"planned_recovery", "forced_pgid"}:
                _m4b_true(row["recovery_success"])
        scan = data["scan"]
        _m4b_exact(scan, {"domains", "post_session_close", "post_shutdown", "reversible_encodings", "hits", "manifest_sha256"})
        if type(scan["domains"]) is not list or set(scan["domains"]) != {"logs", "public_evidence", "temp_workdirs", "process_arguments", "process_environment", "persisted_files"}:
            raise ValueError
        for name in ("post_session_close", "post_shutdown", "reversible_encodings"):
            _m4b_true(scan[name])
        _m4b_int(scan["hits"])
        if scan["hits"]:
            raise ValueError
        _m4b_raw_artifact(scan["manifest_sha256"], resolver)
    else:
        raise ValueError


def _finalize_acceptance_cards(output: Path, result: dict[str, Any], *, m4b_evidence_resolver=None) -> None:
    card_root = output / "cards"
    if not card_root.is_dir() or card_root.is_symlink():
        raise GateFailure("acceptance card output is absent or unsafe")
    reserved = set(result) - {"candidate_sha"}
    m4b_ids: set[str] = set()
    m4b_profiles: set[str] = set()
    for path in sorted(card_root.iterdir()):
        if not path.is_file() or path.is_symlink() or path.suffix != ".json":
            raise GateFailure("acceptance card output contains an unsafe entry")
        draft = load_json(path, "test-specific acceptance card")
        test_id = draft.get("test_id")
        if (
            not isinstance(test_id, str)
            or not re.fullmatch(r"M4[A-Z0-9-]{3,63}", test_id)
            or draft.get("candidate_sha") != result["candidate_sha"]
        ):
            raise GateFailure("test-specific acceptance card identity mismatch")
        if test_id.startswith("M4B-"):
            if test_id in m4b_ids:
                raise GateFailure("duplicate M4b acceptance card")
            _validate_m4b_card(draft, evidence_resolver=m4b_evidence_resolver)
            m4b_ids.add(test_id)
            m4b_profiles.add(draft["profile_sha256"])
            # Current M4B cards already have their complete public schema. Do not
            # merge runner paths or private diagnostics into them.
            continue
        if set(draft) & reserved:
            raise GateFailure("test-specific acceptance card overrides runner fields")
        finalized = dict(result)
        finalized.update(draft)
        write_json(path, finalized)
    expected_m4b = M4B_TARGET_IDS
    if (m4b_ids or "m4b_python_abi_attestation_sha256" in result) and (
            m4b_ids != expected_m4b or len(m4b_profiles) != 1):
        raise GateFailure("M4b acceptance card set is missing or contains unknown IDs")


def run_suite(args: argparse.Namespace, repo: Repository, output: Path, mode: str, marker: str) -> None:
    result = base_result(repo, mode, args.run_id)
    m4b_precheck: dict[str, Any] | None = None
    if mode == "portable" and _m4b_candidate(repo.root):
        m4b_precheck = _m4b_portable_precheck(
            repo, output, args.suite, args.timeout_seconds,
        )
    exit_code, counts, suite_command, raw_logs, network_attempt_count = execute_pytest(
        repo,
        output,
        args.suite if hasattr(args, "suite") else args.node,
        marker,
        args.timeout_seconds,
        mode=mode,
        run_id=args.run_id,
    )
    status = "Pass" if passed(exit_code, counts) else "Fail"
    result.update(
        {
            "counts": counts,
            "ended_at_utc": utc_now(),
            "end_monotonic_ns": time.monotonic_ns(),
            "exit_code": exit_code,
            "raw_logs": raw_logs,
            "status": status,
            "suite_command": suite_command,
            "timeout_seconds": args.timeout_seconds,
        }
    )
    if mode == "portable":
        result["python_minor"] = args.python
        result["suite"] = args.suite
        if m4b_precheck is not None:
            nodes = m4b_precheck.pop("collection_nodes")
            result["raw_logs"] = [*m4b_precheck.pop("precheck_logs"), *raw_logs]
            junit = output / "junit.xml"
            junit_counts = m4b_junit_audit(junit.read_bytes(), nodes)
            if any(junit_counts[name] != counts[name]
                   for name in ("passed", "failed", "errors", "skipped", "xfailed", "xpassed")):
                raise GateFailure("M4B_JUNIT_COUNT_MISMATCH")
            junit_sha256 = sha256(junit, "M4B portable JUnit")
            result.update(m4b_precheck)
            result.update({
                "baseline_evidence": _m4b_foundation_evidence(repo.root, junit),
                "case_id": f"PY{args.python.replace('.', '')}",
                "evidence_sha256": junit_sha256,
                "junit_locator": "junit.xml",
                "junit_sha256": junit_sha256,
                "matrix": "portable",
                "test_id": "M4B-PORTABLE-CATALOG",
                "test_id_evidence": _m4b_test_id_evidence(nodes),
            })
    elif mode == "acceptance":
        result["suite"] = args.suite
        if network_attempt_count is not None:
            result["network_attempt_count"] = network_attempt_count
        preflight_result = load_json(output / "preflight.json", "runner preflight")
        for name in (
            "m4b_python_abi_attestation_sha256", "m4b_install_inventory_sha256",
        ):
            if name in preflight_result:
                if not re.fullmatch(r"[0-9a-f]{64}", str(preflight_result[name])):
                    raise GateFailure("M4b preflight identity is invalid at acceptance start")
                result[name] = preflight_result[name]
    else:
        result["node"] = args.node
        if status == "Pass":
            result["status"] = "Diagnostic"
    if mode == "acceptance" and passed(exit_code, counts):
        _finalize_acceptance_cards(output, result)
    write_json(output / "result.json", result)
    if not passed(exit_code, counts):
        raise GateFailure(
            f"{mode} suite failed, timed out, was skipped, xfailed, or xpassed"
        )


def portable(args: argparse.Namespace, repo: Repository, output: Path) -> None:
    if platform.python_version_tuple()[:2] != tuple(args.python.split(".")):
        raise GateFailure(f"runner Python is {platform.python_version()}, not requested Python {args.python}")
    run_suite(args, repo, output, "portable", "not rpi")


def _m4b_validate_result_evidence(
    result: dict[str, Any], minor: str, repo: Repository, result_path: Path,
) -> None:
    profile_id, profile_sha256 = _m4b_profile_identity(repo.root)
    targets, catalog_sha256 = _m4b_canonical_targets(repo, str(result.get("suite", "")))
    platform_identity = result.get("platform_identity")
    python_identity = result.get("python")
    if platform_identity is None or set(platform_identity) != {"system", "machine"}:
        raise GateFailure(f"Python {minor} portable result has incomplete platform identity")
    if (platform_identity["system"] != "Linux"
            or platform_identity["machine"] not in {"x86_64", "aarch64"}):
        raise GateFailure(f"Python {minor} portable result is not from supported Linux")
    if (not isinstance(python_identity, dict)
            or python_identity.get("implementation") != "CPython"
            or not isinstance(python_identity.get("version"), str)
            or not re.fullmatch(rf"{re.escape(minor)}\.\d+", python_identity["version"])):
        raise GateFailure(f"Python {minor} portable result has incomplete Python identity")
    if (result.get("schema_version") != 1
            or result.get("test_id") != "M4B-PORTABLE-CATALOG"
            or result.get("case_id") != f"PY{minor.replace('.', '')}"
            or result.get("mode") != "portable"
            or result.get("matrix") != "portable"
            or result.get("profile_id") != profile_id
            or result.get("profile_sha256") != profile_sha256
            or result.get("catalog_sha256") != catalog_sha256
            or result.get("catalog_paths") != targets):
        raise GateFailure(f"Python {minor} portable result has mixed suite/catalog/profile identity")
    start_ns = result.get("start_monotonic_ns")
    end_ns = result.get("end_monotonic_ns")
    if (type(start_ns) is not int or type(end_ns) is not int
            or start_ns < 0 or end_ns < start_ns):
        raise GateFailure(f"Python {minor} portable result has invalid monotonic identity")

    result_dir = result_path.parent.resolve()

    def evidence_path(field: str) -> Path:
        relative = result.get(field)
        if not _relative_locator(relative):
            raise GateFailure(f"Python {minor} portable result has unsafe {field}")
        path = (result_dir / str(relative)).resolve()
        if not path.is_relative_to(result_dir) or not path.is_file() or path.is_symlink():
            raise GateFailure(f"Python {minor} portable result has missing {field}")
        return path

    collection = evidence_path("collection_locator")
    junit = evidence_path("junit_locator")
    suite_command = result.get("suite_command")
    if (not isinstance(suite_command, list)
            or suite_command[1:6] != ["-m", "pytest", "-v", "-m", "not rpi"]
            or suite_command[6:-1] != targets
            or len(suite_command) < 8
            or not isinstance(suite_command[-1], str)
            or not suite_command[-1].startswith("--junitxml=")
            or Path(suite_command[-1].split("=", 1)[1]).resolve() != junit):
        raise GateFailure(f"Python {minor} portable result has non-canonical suite command")
    if result.get("collection_sha256") != sha256(collection, "M4B collection evidence"):
        raise GateFailure(f"Python {minor} portable result has mismatched collection digest")
    if (result.get("junit_sha256") != sha256(junit, "M4B JUnit evidence")
            or result.get("evidence_sha256") != result.get("junit_sha256")):
        raise GateFailure(f"Python {minor} portable result has mismatched JUnit digest")
    nodes = collection.read_text(encoding="utf-8").splitlines()
    if (not nodes or len(nodes) != len(set(nodes))
            or result.get("collection_count") != len(nodes)):
        raise GateFailure(f"Python {minor} portable result has invalid collection identity")
    expected_test_ids = _m4b_test_id_evidence(nodes)
    if result.get("test_id_evidence") != expected_test_ids:
        raise GateFailure(f"Python {minor} portable result has incomplete Test ID evidence")
    junit_counts = m4b_junit_audit(junit.read_bytes(), nodes)
    if result.get("counts") != junit_counts:
        raise GateFailure(f"Python {minor} portable result has mismatched JUnit counts")
    if result.get("baseline_evidence") != _m4b_foundation_evidence(repo.root, junit):
        raise GateFailure(f"Python {minor} portable result has mismatched Foundation evidence")
    if result.get("source_audit_sha256") != _m4b_source_audit(repo.root, targets):
        raise GateFailure(f"Python {minor} portable result has mismatched source audit")
    raw_logs = result.get("raw_logs")
    required_logs = {"logs/collection.stdout.log", "logs/collection.stderr.log",
                     "logs/suite.stdout.log", "logs/suite.stderr.log"}
    if (not isinstance(raw_logs, list) or len(raw_logs) != len(set(raw_logs))
            or not required_logs <= set(raw_logs)):
        raise GateFailure(f"Python {minor} portable result has no raw log locator")
    for relative in raw_logs:
        if not _relative_locator(relative):
            raise GateFailure(f"Python {minor} portable result has unsafe raw log locator")
        path = (result_dir / relative).resolve()
        if not path.is_relative_to(result_dir) or not path.is_file() or path.is_symlink():
            raise GateFailure(f"Python {minor} portable result has missing raw log evidence")


def validate_version_result(
    result: dict[str, Any], minor: str, candidate_sha: str, run_id: str,
    *, repo: Repository | None = None, result_path: Path | None = None,
) -> None:
    if result.get("status") != "Pass" or result.get("exit_code") != 0:
        raise GateFailure(f"Python {minor} portable result is not Pass")
    if result.get("candidate_sha") != candidate_sha or result.get("run_id") != run_id:
        raise GateFailure(f"Python {minor} portable result has a mixed candidate SHA or run ID")
    if result.get("python_minor") != minor:
        raise GateFailure(f"Python {minor} portable result has the wrong minor identity")
    counts = result.get("counts")
    forbidden = ("failed", "errors", "skipped", "xfailed", "xpassed")
    if not isinstance(counts, dict) or any(counts.get(name) != 0 for name in forbidden):
        raise GateFailure(f"Python {minor} portable result contains Fail, Error, Skip, XFail, or XPASS")
    if not isinstance(result.get("timeout_seconds"), (int, float)) or result["timeout_seconds"] <= 0:
        raise GateFailure(f"Python {minor} portable result has no bounded timeout")
    if not isinstance(result.get("raw_logs"), list) or not result["raw_logs"]:
        raise GateFailure(f"Python {minor} portable result has no raw log locator")
    if repo is not None and _m4b_candidate(repo.root):
        if result_path is None:
            raise GateFailure(f"Python {minor} portable result has no evidence location")
        _m4b_validate_result_evidence(result, minor, repo, result_path)


def validate_matrix(index: dict[str, Any], index_path: Path, repo: Repository) -> None:
    if index.get("status") != "Pass" or index.get("candidate_sha") != repo.candidate_sha:
        raise GateFailure("portable matrix is not Pass for this candidate SHA")
    results = index.get("results")
    if not isinstance(results, dict) or set(results) != set(PORTABLE_MINORS):
        raise GateFailure("portable matrix must contain Python 3.11, 3.12, and 3.13")
    run_id = index.get("run_id")
    if not isinstance(run_id, str):
        raise GateFailure("portable matrix run ID is missing")
    result_sha256 = index.get("result_sha256")
    if not isinstance(result_sha256, dict) or set(result_sha256) != set(PORTABLE_MINORS):
        raise GateFailure("portable matrix result digest index is incomplete")
    for minor, relative in results.items():
        if not isinstance(relative, str):
            raise GateFailure(f"Python {minor} portable result locator is invalid")
        result_path = (index_path.parent / relative).resolve()
        if (not result_path.is_relative_to(index_path.parent.resolve())
                or result_sha256.get(minor) != sha256(result_path, f"Python {minor} result")):
            raise GateFailure(f"Python {minor} portable result digest mismatch")
        result = load_json(result_path, f"Python {minor} portable result")
        validate_version_result(result, minor, repo.candidate_sha, run_id,
                                repo=repo, result_path=result_path)
    if _m4b_candidate(repo.root):
        profile_id, profile_sha256 = _m4b_profile_identity(repo.root)
        _, catalog_sha256 = _m4b_canonical_targets(repo, M4B_CANONICAL_SUITE)
        if (index.get("schema_version") != 1
                or index.get("profile_id") != profile_id
                or index.get("profile_sha256") != profile_sha256
                or index.get("catalog_sha256") != catalog_sha256):
            raise GateFailure("portable matrix has mixed catalog/profile identity")


def matrix(args: argparse.Namespace, repo: Repository) -> None:
    input_root = Path(args.input_root).resolve()
    output = Path(args.output).resolve()
    if output.exists():
        raise RunReuseFailure(f"matrix output already exists and will not be overwritten: {output}")
    if output.parent != input_root or output.name != "matrix-index.json":
        raise GateFailure("matrix output must be <input-root>/matrix-index.json")
    results: dict[str, str] = {}
    result_digests: dict[str, str] = {}
    for minor in PORTABLE_MINORS:
        path = input_root / f"python-{minor}" / "result.json"
        result = load_json(path, f"Python {minor} portable result")
        validate_version_result(result, minor, repo.candidate_sha, args.run_id,
                                repo=repo, result_path=path)
        results[minor] = str(path.relative_to(input_root))
        result_digests[minor] = sha256(path, f"Python {minor} result")
    identity: dict[str, Any] = {}
    if _m4b_candidate(repo.root):
        profile_id, profile_sha256 = _m4b_profile_identity(repo.root)
        _, catalog_sha256 = _m4b_canonical_targets(repo, M4B_CANONICAL_SUITE)
        identity = {
            "catalog_sha256": catalog_sha256,
            "profile_id": profile_id,
            "profile_sha256": profile_sha256,
            "schema_version": 1,
        }
    write_json(
        output,
        {
            "branch": repo.branch,
            "candidate_sha": repo.candidate_sha,
            "command": sys.argv,
            "created_at_utc": utc_now(),
            "results": results,
            "result_sha256": result_digests,
            "run_id": args.run_id,
            "status": "Pass",
            **identity,
        },
    )


def checksum_reference(path: Path, label: str) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": sha256(path, label)}


def validate_m4b_product_preflight(
    value: dict[str, Any], candidate_sha: str,
) -> tuple[str, str]:
    required = {
        "status", "operation", "candidate_sha", "candidate_id", "pairing_revision",
        "artifact_lock_sha256", "runtime_manifest_sha256", "runtime_file_count",
        "install_file_count", "install_inventory_sha256", "model_sha256",
        "profile_id", "profile_sha256", "profile_stage", "network_isolated",
        "platform", "python", "python_abi_attestation_sha256",
    }
    # This file comes from the candidate checkout, never a caller-selected lock.
    lock_path = Path(__file__).resolve().parents[1] / "requirements/m4b/llm-artifacts.json"
    try:
        raw = lock_path.read_bytes()
        lock = json.loads(raw)
        fixed = {
            "status": "PreflightReady", "operation": "preflight",
            "candidate_sha": candidate_sha,
            "candidate_id": "CAND-LRT-G4E2B-MOBILE-R1",
            "pairing_revision": "litert-lm-v0.16.0-pi-g2b-r5",
            "platform": "pi-debian13-aarch64", "python": "CPython 3.13.5",
            "artifact_lock_sha256": hashlib.sha256(raw).hexdigest(),
            "runtime_manifest_sha256": lock["runtime_closure"]["manifest_sha256"],
            "model_sha256": lock["model"]["sha256"], "runtime_file_count": 14,
            "profile_id": "core-m4b-cognition-001", "profile_stage": "release",
            "network_isolated": True,
        }
    except (OSError, KeyError, TypeError, ValueError):
        raise GateFailure("M4B_PREFLIGHT_AUTHORITY_UNAVAILABLE") from None
    if (type(value) is not dict or set(value) != required
            or not SHA_RE.fullmatch(candidate_sha) or _draft_contains_absolute(value)
            or any(type(value.get(k)) is not type(v) or value[k] != v for k, v in fixed.items())):
        raise GateFailure("M4B_PREFLIGHT_IDENTITY_INVALID")
    for name in ("profile_sha256", "python_abi_attestation_sha256", "install_inventory_sha256"):
        if type(value[name]) is not str or re.fullmatch(r"[0-9a-f]{64}", value[name]) is None:
            raise GateFailure("M4B_PREFLIGHT_DIGEST_INVALID")
    if type(value["install_file_count"]) is not int or value["install_file_count"] <= 0:
        raise GateFailure("M4B_PREFLIGHT_INVENTORY_INVALID")
    return value["python_abi_attestation_sha256"], value["install_inventory_sha256"]


def preflight(args: argparse.Namespace, repo: Repository, output: Path) -> None:
    if args.runtime != "3.13":
        raise GateFailure("target runtime must be the M4 deployment runtime, CPython 3.13")
    matrix_path = Path(args.portable_index).resolve()
    matrix_index = load_json(matrix_path, "portable matrix index")
    validate_matrix(matrix_index, matrix_path, repo)
    result = base_result(repo, "preflight", args.run_id)
    checksums = {
        "artifact_manifest": checksum_reference(Path(args.artifact_manifest), "artifact manifest"),
        "config": checksum_reference(Path(args.config), "config"),
        "hardware": checksum_reference(Path(args.hardware), "hardware description"),
    }
    m4b_abi: str | None = None
    m4b_inventory: str | None = None
    if args.m4b_artifact_manifest is not None:
        m4b_path = Path(args.m4b_artifact_manifest)
        m4b_product = load_json(m4b_path, "M4b product preflight")
        m4b_abi, m4b_inventory = validate_m4b_product_preflight(
            m4b_product, repo.candidate_sha,
        )
        checksums["m4b_artifact_manifest"] = checksum_reference(
            m4b_path, "M4b artifact manifest"
        )
    result.update(
        {
            "checksums": checksums,
            "ended_at_utc": utc_now(),
            "exit_code": 0,
            "portable_index": str(matrix_path),
            "portable_run_id": matrix_index.get("run_id"),
            "runtime": args.runtime,
            "status": "Pass",
        }
    )
    if m4b_abi is not None and m4b_inventory is not None:
        result["m4b_python_abi_attestation_sha256"] = m4b_abi
        result["m4b_install_inventory_sha256"] = m4b_inventory
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
    preflight_parser.add_argument("--m4b-artifact-manifest")

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
