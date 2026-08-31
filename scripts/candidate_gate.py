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
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
PORTABLE_MINORS = ("3.11", "3.12", "3.13")
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
    return exit_code == 0 and all(counts[name] == 0 for name in ("failed", "skipped", "xfailed"))


M4B_CARD_REQUIRED = {
    "M4B-RDY-001": {
        "engine_load_latency_ms", "ready_latency_ms", "prewarm_latency_ms",
        "prewarm_prompt_sha256", "ready_identity",
    },
    "M4B-GEN-001": {
        "child_pid", "engine_load_count", "conversation_count", "init_ms",
        "ttft_ms", "prefill_tokens", "decode_tokens", "kv_tokens",
        "response_digests",
    },
    "M4B-OUT-001": {
        "catalog_case_count", "schema_pass_count", "current_marker_exactly_once",
        "prior_marker_hits", "forbidden_literal_hits", "tool_handler_calls",
    },
    "M4B-P5-001": {"case", "converged_to"},
    "M4B-CAN-001": {
        "case", "native_cancel_calls", "worker_joined", "term_sent", "kill_sent",
        "waitpid_exit_code", "orphan_count", "recovery_ready",
    },
    "M4B-REC-001": {
        "trigger_reason", "generation_count", "ticket_id",
        "resource_samples_locator", "prewarm_timings_locator",
    },
    "M4B-HIST-001": {
        "turn_count", "conversation_count", "child_pid_stable",
        "current_marker_pass_count", "prior_marker_hits",
    },
    "M4B-PRIV-001": {"scanned_locators", "paths_digest", "hits"},
    "M4B-OFF-001": {
        "network_attempts", "downloader_calls", "session_status",
        "session_result_sha256",
    },
    "M4B-RES-001": {
        "session_count", "generation_count", "r14_formula_version",
        "combined_pss_slope_mib_per_session", "system_used_slope_mib_per_session",
        "combined_pss_late_minus_early_median_delta_mib",
        "system_used_late_minus_early_median_delta_mib", "max_generation_delta_mib",
        "max_system_used_mib",
        "swap_used_zero", "oom_kill_delta", "throttled_zero",
        "thermal_max_celsius", "resource_samples_locator", "cleanup_locator",
        "poc_p9_p10b_status", "user_waiver",
    },
    "M4B-PKG-001": {
        "install_inventory_sha256", "python_abi_attestation_sha256",
        "abi_status", "file_count",
    },
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


def _validate_m4b_card(draft: dict[str, Any]) -> None:
    test_id = draft.get("test_id")
    required = M4B_CARD_REQUIRED.get(test_id)
    if required is None or not required.issubset(draft):
        raise GateFailure("M4b acceptance card is missing required evidence fields")
    if _draft_contains_absolute(draft):
        raise GateFailure("M4b acceptance card contains an absolute private path")
    zero_fields = {
        "M4B-OUT-001": ("prior_marker_hits", "forbidden_literal_hits", "tool_handler_calls"),
        "M4B-CAN-001": ("orphan_count",),
        "M4B-HIST-001": ("prior_marker_hits",),
        "M4B-PRIV-001": ("hits",),
        "M4B-OFF-001": ("network_attempts", "downloader_calls"),
        "M4B-RES-001": ("oom_kill_delta",),
    }
    if any(draft.get(name) != 0 for name in zero_fields.get(test_id, ())):
        raise GateFailure("M4b acceptance card contains a nonzero fail-closed metric")
    for locator in (
        "resource_samples_locator", "prewarm_timings_locator", "cleanup_locator",
    ):
        if locator in draft and not _relative_locator(draft[locator]):
            raise GateFailure("M4b acceptance card contains an invalid evidence locator")
    if test_id == "M4B-PKG-001" and set(draft) != {
        "candidate_sha", "test_id", *required,
    }:
        raise GateFailure("M4b package card contains unsanitized evidence fields")
    if test_id == "M4B-RDY-001":
        identity = draft["ready_identity"]
        timings = (
            draft["engine_load_latency_ms"], draft["ready_latency_ms"],
            draft["prewarm_latency_ms"],
        )
        if any(type(value) not in (int, float) or not math.isfinite(value) or value < 0 for value in timings) or identity != {
            "candidate_id": "CAND-LRT-G4E2B-MOBILE-R1",
            "pairing_revision": "litert-lm-v0.16.0-pi-g2b-r5",
            "platform": "pi-debian13-aarch64",
            "runtime_sha256": "5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00",
            "model_sha256": "181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c",
            "config_sha256": "c4557b018733ce8a2f4aa46b375cc7dafb31fbd8c363271deb1156c651e5171e",
        } or draft["prewarm_prompt_sha256"] != "4f3bc3e09b3b1693812c749765cfce5899dc11933de06623dbfc82a61a50472d":
            raise GateFailure("M4b READY card identity mismatch")
    elif test_id == "M4B-GEN-001":
        response_digests = draft["response_digests"]
        if (
            type(draft["child_pid"]) is not int or draft["child_pid"] <= 0
            or draft["engine_load_count"] != 3
            or draft["conversation_count"] != 20
            or any(type(draft[name]) not in (int, float) or not math.isfinite(draft[name]) or draft[name] < 0 for name in ("init_ms", "ttft_ms"))
            or type(draft["prefill_tokens"]) is not int or not 1 <= draft["prefill_tokens"] <= 128
            or type(draft["decode_tokens"]) is not int or not 1 <= draft["decode_tokens"] <= 128
            or type(draft["kv_tokens"]) is not int or not 1 <= draft["kv_tokens"] <= 1024
            or type(response_digests) is not list or len(response_digests) != 20
            or any(not re.fullmatch(r"[0-9a-f]{64}", str(value)) for value in response_digests)
        ):
            raise GateFailure("M4b generation card is not fully passing")
    elif test_id == "M4B-OUT-001":
        if (
            type(draft["catalog_case_count"]) is not int
            or draft["catalog_case_count"] != 23
            or draft["schema_pass_count"] != draft["catalog_case_count"]
            or draft["current_marker_exactly_once"] is not True
        ):
            raise GateFailure("M4b output catalog card is not fully passing")
    elif test_id == "M4B-P5-001":
        if draft["case"] != "ReasoningInputTooLarge" or draft["converged_to"] != "P5":
            raise GateFailure("M4b P5 card is not fully passing")
    elif test_id == "M4B-CAN-001":
        if (
            draft["case"] != "cooperative-cancel-and-level2"
            or draft["native_cancel_calls"] != 1
            or draft["worker_joined"] is not True
            or type(draft["term_sent"]) is not bool
            or type(draft["kill_sent"]) is not bool
            or type(draft["waitpid_exit_code"]) is not int
            or draft["recovery_ready"] is not True
        ):
            raise GateFailure("M4b cancellation card is not fully passing")
    elif test_id == "M4B-REC-001":
        if (
            draft["trigger_reason"] != "attempt-limit-8-and-16"
            or draft["generation_count"] != 3
            or draft["ticket_id"] != 2
        ):
            raise GateFailure("M4b recovery card is not fully passing")
    elif test_id == "M4B-HIST-001":
        if (
            draft["turn_count"] != 20
            or draft["conversation_count"] != 20
            or draft["child_pid_stable"] is not True
            or draft["current_marker_pass_count"] != 20
        ):
            raise GateFailure("M4b history card is not fully passing")
    elif test_id == "M4B-OFF-001":
        if draft["session_status"] != "Pass" or not re.fullmatch(
            r"[0-9a-f]{64}", str(draft["session_result_sha256"]),
        ):
            raise GateFailure("M4b offline card identity mismatch")
    elif test_id == "M4B-RES-001":
        if (
            draft["session_count"] != 20
            or draft["generation_count"] != 3
            or draft["r14_formula_version"] != "2026-08-29-r14-user-resource-adjustment"
            or draft["swap_used_zero"] is not True
            or draft["throttled_zero"] is not True
            or draft["poc_p9_p10b_status"] != "FAIL"
            or draft["user_waiver"] != "KNOWN_RUNTIME_DEFECT / ENGINE-SESSION RESIDENT RETENTION"
        ):
            raise GateFailure("M4b resource card fixed identity mismatch")
        for name, maximum in (
            ("combined_pss_slope_mib_per_session", 4),
            ("system_used_slope_mib_per_session", 4),
            ("combined_pss_late_minus_early_median_delta_mib", 64),
            ("system_used_late_minus_early_median_delta_mib", 64),
            ("max_generation_delta_mib", 64),
            ("max_system_used_mib", 3584),
            ("thermal_max_celsius", 80),
        ):
            value = draft[name]
            if type(value) not in (int, float) or not math.isfinite(value):
                raise GateFailure("M4b resource card exceeds a frozen gate")
            exceeded = value >= maximum if name == "thermal_max_celsius" else value > maximum
            if exceeded:
                raise GateFailure("M4b resource card exceeds a frozen gate")
    elif test_id in {"M4B-PRIV-001", "M4B-PKG-001"}:
        digest_name = "paths_digest" if test_id == "M4B-PRIV-001" else "install_inventory_sha256"
        if not re.fullmatch(r"[0-9a-f]{64}", str(draft[digest_name])):
            raise GateFailure("M4b acceptance card digest is invalid")
        if test_id == "M4B-PRIV-001":
            locators = draft["scanned_locators"]
            if (
                type(locators) is not list
                or len(locators) < 5
                or any(type(value) is not str or not value for value in locators)
                or hashlib.sha256("\n".join(locators).encode()).hexdigest() != draft["paths_digest"]
            ):
                raise GateFailure("M4b privacy card scan identity is invalid")
        if test_id == "M4B-PKG-001" and (
            draft["abi_status"] != "Pass"
            or not re.fullmatch(r"[0-9a-f]{64}", str(draft["python_abi_attestation_sha256"]))
            or type(draft["file_count"]) is not int
            or draft["file_count"] <= 0
        ):
            raise GateFailure("M4b package ABI evidence is invalid")


def _finalize_acceptance_cards(output: Path, result: dict[str, Any]) -> None:
    card_root = output / "cards"
    if not card_root.is_dir() or card_root.is_symlink():
        raise GateFailure("acceptance card output is absent or unsafe")
    reserved = set(result) - {"candidate_sha"}
    m4b_ids: set[str] = set()
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
        if set(draft) & reserved:
            raise GateFailure("test-specific acceptance card overrides runner fields")
        if test_id.startswith("M4B-"):
            if test_id in m4b_ids:
                raise GateFailure("duplicate M4b acceptance card")
            _validate_m4b_card(draft)
            m4b_ids.add(test_id)
        finalized = dict(result)
        finalized.update(draft)
        write_json(path, finalized)
    expected_m4b = {
        "M4B-RDY-001", "M4B-GEN-001", "M4B-OUT-001", "M4B-P5-001",
        "M4B-CAN-001", "M4B-REC-001", "M4B-HIST-001", "M4B-PRIV-001",
        "M4B-OFF-001", "M4B-RES-001", "M4B-PKG-001",
    }
    if m4b_ids and m4b_ids != expected_m4b:
        raise GateFailure("M4b acceptance card set is missing or contains unknown IDs")


def run_suite(args: argparse.Namespace, repo: Repository, output: Path, mode: str, marker: str) -> None:
    result = base_result(repo, mode, args.run_id)
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


def validate_m4b_product_preflight(
    value: dict[str, Any], candidate_sha: str,
) -> tuple[str, str]:
    required = {
        "status", "candidate_sha", "candidate_id", "pairing_revision",
        "artifact_lock_sha256", "runtime_manifest_sha256", "runtime_file_count",
        "install_file_count", "install_inventory_sha256", "model_sha256",
        "product_config_sha256", "platform", "python",
        "python_abi_attestation_sha256",
    }
    fixed = {
        "status": "Pass",
        "candidate_sha": candidate_sha,
        "candidate_id": "CAND-LRT-G4E2B-MOBILE-R1",
        "pairing_revision": "litert-lm-v0.16.0-pi-g2b-r5",
        "platform": "pi-debian13-aarch64",
        "python": "CPython 3.13.5",
        "artifact_lock_sha256": "92e78d0c85de5419a02d28a74db03fe28fa27197d34ef49cb44abfb2bb0aac99",
        "runtime_manifest_sha256": "6c11b8357021fb3bd7abaddeb8fdfdabc1b0fa85cd22bd49fcd7d9cd7d0871d2",
        "model_sha256": "181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c",
        "product_config_sha256": "c4557b018733ce8a2f4aa46b375cc7dafb31fbd8c363271deb1156c651e5171e",
        "runtime_file_count": 14,
    }
    if (
        type(value) is not dict
        or set(value) != required
        or _draft_contains_absolute(value)
        or any(value.get(key) != expected for key, expected in fixed.items())
    ):
        raise GateFailure("M4b product preflight identity mismatch")
    abi = value.get("python_abi_attestation_sha256")
    inventory = value.get("install_inventory_sha256")
    if (
        not re.fullmatch(r"[0-9a-f]{64}", str(abi))
        or not re.fullmatch(r"[0-9a-f]{64}", str(inventory))
        or type(value.get("install_file_count")) is not int
        or value["install_file_count"] <= 0
    ):
        raise GateFailure("M4b product preflight ABI evidence is invalid")
    return str(abi), str(inventory)


def preflight(args: argparse.Namespace, repo: Repository, output: Path) -> None:
    if args.runtime != "3.13":
        raise GateFailure("target runtime must be the M4 deployment runtime, CPython 3.13")
    matrix_path = Path(args.portable_index).resolve()
    matrix_index = load_json(matrix_path, "portable matrix index")
    validate_matrix(matrix_index, matrix_path, repo.candidate_sha)
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
