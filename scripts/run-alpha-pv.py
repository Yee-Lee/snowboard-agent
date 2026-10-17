#!/usr/bin/env python3
"""Select one ALPHA Pi run, enforce a watchdog, and emit sanitized evidence.

Quality judgment is a replay of the same private observation, never another
product execution: --run quality --adjudicate DIR --judgments FILE.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.alpha_oracle import CLEANUP, RUNS, InvalidObservation, check_public, evaluate, experiment_block, require
from scripts.alpha_product import (FIXTURE_TEXT, private_json, process_identity, quality_revision,
                                   resolve_fixtures, session_plan)


def process_tree(root: int) -> dict[int, tuple[str, str]]:
    parents = {}
    identities = {}
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            fields = (proc / "stat").read_text().rsplit(")", 1)[1].split()
            parents[int(proc.name)] = int(fields[1])
            identities[int(proc.name)] = (fields[19], fields[0])
        except (OSError, ValueError, IndexError):
            continue
    found = {root}
    while True:
        children = {pid for pid, parent in parents.items() if parent in found}
        if children <= found:
            break
        found |= children
    return {pid: identities[pid] for pid in found if pid in identities}


def remains(pid: int, identity) -> bool:
    current = process_identity(pid)
    # A zombie child has not been reaped and remains an owner-cleanup failure.
    return current is not None and identity is not None and current[0] == identity[0]


def finish_process(process, identities: dict, seconds: float) -> bool:
    """Terminate only processes observed to belong to this invocation."""
    identities.update(process_tree(process.pid))
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for pid, identity in identities.items():
            if remains(pid, identity):
                try:
                    os.kill(pid, sig)
                except ProcessLookupError:
                    pass
        deadline = time.monotonic() + seconds / 2
        while time.monotonic() < deadline:
            process.poll()  # Reap our launcher promptly.
            if not any(remains(pid, identity) for pid, identity in identities.items()):
                return True
            time.sleep(0.02)
    return not any(remains(pid, identity) for pid, identity in identities.items())


def no_previous_app() -> bool:
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            command = (proc / "cmdline").read_bytes().split(b"\0")
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError:
            raise InvalidObservation("PROCESS_OBSERVATION_UNAVAILABLE") from None
        if any(arg.endswith((b"/alpha_product.py", b"/m4c_s05_app.py")) or arg == b"sbd.main"
               for arg in command):
            return False
    return True


def run_child(args, private: Path, run: str, suffix: str = "") -> dict:
    observation = private / f"observation{suffix}.json"
    log = private / f"application{suffix}.log"
    network = private / f"network{suffix}.log"
    start = time.monotonic_ns()
    deadline = getattr(args, "deadline", time.monotonic() + args.watchdog)
    if time.monotonic() >= deadline:
        return {"driver_complete": False, "failure_code": "RUNNER_WATCHDOG"}
    command = [str(args.python), str(ROOT / "scripts/alpha_product.py"), "--run", run,
               "--config", str(args.config.resolve()), "--fixtures", str(args.fixtures.resolve()),
               "--observation", str(observation), "--process-start-ns", str(start)]
    environment = None
    host_context = None
    if run in {"pn", "ph"}:
        host_context = {"boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                        "uptime_start_ns": time.monotonic_ns(), "wall_start_ns": time.time_ns()}
        timing = private / f"timings{suffix}"
        timing.mkdir(mode=0o700)
        experiment = private / f"experiment{suffix}.json"
        private_json(experiment, {"run": run, "fixtures": str(args.fixtures.resolve()),
            "observation": str(observation), "process_start_ns": start,
            "timing_directory": str(timing), "control": bool(args.cause_control_reason),
            "diagnostic_role": getattr(args, "diagnostic_role", None),
            "acoustic": bool(getattr(args, "acoustic", False)),
            "manual": bool(getattr(args, "manual", False))})
        environment = dict(os.environ, ALPHA_EXPERIMENT=str(experiment))
        command = [str(args.installed_entry.resolve()), "--config", str(args.config.resolve()),
                   "--python", str(args.python)]
    if args.run == "lifecycle":
        if args.network_launcher == "sudo-unshare":
            # Root creates only the namespace. Return to the caller for hardware access,
            # private evidence ownership, and the Python runtime itself.
            prefix = ["sudo", "-n", "unshare", "--net", "--", "setpriv",
                      f"--reuid={os.getuid()}", f"--regid={os.getgid()}", "--init-groups", "--"]
        else:
            prefix = ["unshare", "--net", "--"]
        command = prefix + ["strace", "-f", "-o", str(network), "-e", "trace=network", *command]
    identities = {}
    timed_out = False
    with log.open("xb") as sink:
        os.chmod(log, 0o600)
        process = subprocess.Popen(command, cwd=ROOT, stdout=sink, stderr=subprocess.STDOUT,
                                   start_new_session=True, env=environment)
        previous_interrupt = signal.getsignal(signal.SIGINT)
        if run == "ph" or getattr(args, "manual", False):
            def forward_interrupt(signum, frame):
                try:
                    process.send_signal(signal.SIGINT)
                except ProcessLookupError:
                    pass
            signal.signal(signal.SIGINT, forward_interrupt)
        guide_offset = 0
        try:
            while process.poll() is None:
                if run == "ph":
                    with log.open("r") as source:
                        source.seek(guide_offset)
                        while True:
                            line = source.readline()
                            if not line or not line.endswith("\n"):
                                break
                            guide_offset = source.tell()
                            if line.startswith("ALPHA_GUIDE "):
                                instruction = line.strip().split()[1:]
                                if instruction[0] == "SAY" and instruction[1] in FIXTURE_TEXT:
                                    print("請說：" + FIXTURE_TEXT[instruction[1]], flush=True)
                                elif instruction[0] == "START_SESSION":
                                    print("請短按按鈕開始新 Session，等候下一個指定問題。", flush=True)
                                elif instruction[0] == "STOP_APP":
                                    print("請長按按鈕或 Ctrl+C 正常停止 App。", flush=True)
                identities.update(process_tree(process.pid))
                if time.monotonic() >= deadline:
                    timed_out = True
                    break
                time.sleep(0.02)
        finally:
            if run == "ph" or getattr(args, "manual", False):
                signal.signal(signal.SIGINT, previous_interrupt)
            # This also captures detached native child groups, beyond the launcher PGID.
            if process.poll() is None:
                finish_process(process, identities, args.cleanup_timeout)
            try:
                process.wait(timeout=args.cleanup_timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
    observed = False
    try:
        value = json.loads(observation.read_text(encoding="utf-8"))
        observed = True
    except (OSError, ValueError):
        try:
            value = json.loads(observation.with_name(f"{observation.stem}-failure.json").read_text(encoding="utf-8"))
            observed = True
        except (OSError, ValueError):
            value = {"driver_complete": False, "failure_code": "OBSERVATION_MISSING"}
    for pid, identity in value.get("child_identities", {}).items():
        identities[int(pid)] = identity
    clean = not any(remains(pid, identity) for pid, identity in identities.items())
    if not clean:
        finish_process(process, identities, args.cleanup_timeout)
    cleanup = value.setdefault("cleanup", {})
    cleanup["app_absent"] = process.poll() is not None and not remains(value.get("app_pid", 0),
                                                    identities.get(value.get("app_pid", 0)))
    cleanup["children_absent"] = cleanup.get("children_absent") is True and clean
    if timed_out:
        value["driver_complete"] = False
        if not observed or value.get("failure_code") == "DRIVER_INCOMPLETE":
            value["failure_code"] = "RUNNER_WATCHDOG"
    elif process.returncode != 0:
        value.update(driver_complete=False, failure_code=value.get("failure_code", "LAUNCHER_FAILED"))
    value["launcher_exit_code"] = process.returncode
    value["process_start_ns"] = start
    value["process_end_ns"] = time.monotonic_ns()
    if run in {"pn", "ph"}:
        host_context.update(uptime_end_ns=time.monotonic_ns(), wall_end_ns=time.time_ns())
        value["host_context"] = host_context
        value["timing_events"] = [json.loads(line) for path in sorted(timing.glob("timing-*.jsonl"))
                                  for line in path.read_text().splitlines()]
        value["startup_timing_events"] = [json.loads(line) for path in sorted(timing.glob("startup-timing-*.jsonl"))
                                          for line in path.read_text().splitlines()]
    return value


def network_counts(private: Path) -> tuple[int, int]:
    logs = [private / "network.log", private / "network-restart.log"]
    require(all(path.is_file() for path in logs), "NETWORK_OBSERVATION_MISSING")
    attempts = 0
    for path in logs:
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.search(r"\b(connect|sendto|sendmsg)\(", line) and "AF_INET" in line:
                # UNIX sockets and loopback are local IPC; other endpoints are external attempts.
                if not ('inet_addr("127.' in line or 'inet_pton(AF_INET6, "::1"' in line):
                    attempts += 1
    # The namespace has no external interfaces; any network fallback also requires such an attempt.
    return attempts, attempts


def privacy_matches(public: dict, observations: dict) -> int:
    def strings(value):
        if isinstance(value, dict):
            return [s for item in value.values() for s in strings(item)]
        if isinstance(value, list):
            return [s for item in value for s in strings(item)]
        return [value] if isinstance(value, str) else []
    public_strings = strings(public)
    matches = observations.get("log_privacy_matches", 0)
    for turn in observations.get("turns", []):
        texts = [item.get("text") for item in turn.get("asr", [])]
        texts += [item.get("payload", {}).get("text") for item in turn.get("responses", [])]
        for text in texts:
            if type(text) is str and text and any(
                    text == item or (len(text) >= 4 and text in item) for item in public_strings):
                matches += 1
    # Structural privacy validation handles prompt/credential/audio fields, even without a sample value.
    try:
        check_public(public)
    except InvalidObservation:
        matches += 1
    return matches


def write_public(path: Path, report: dict) -> None:
    check_public(report)
    with path.open("x", encoding="utf-8") as sink:
        json.dump(report, sink, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        sink.write("\n")


def execute(args) -> int:
    if args.run in {"pn", "ph"}:
        return execute_experiment(args)
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,95}", args.run_id) is not None, "RUN_ID_INVALID")
    require(math.isfinite(args.watchdog) and args.watchdog > 0
            and math.isfinite(args.cleanup_timeout) and 0 < args.cleanup_timeout <= 60, "WATCHDOG_INVALID")
    root = args.output.resolve()
    require(not root.is_relative_to(ROOT), "EVIDENCE_INSIDE_REPOSITORY")
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    private = root / "private"
    private.mkdir(mode=0o700)
    os.chmod(root, 0o700)
    metadata = {"run_id": args.run_id, "target": {"architecture": platform.machine(),
                "python": platform.python_version()}, "watchdog_seconds": args.watchdog}
    value = {"driver_complete": False, "failure_code": "PRECONDITION_FAILED", "cleanup": {}}
    report = None
    try:
        require(platform.machine() == "aarch64", "PI_TARGET_REQUIRED")
        require(no_previous_app(), "PREVIOUS_APP_PRESENT")
        needed = {fixture for session in session_plan(args.run) for _, fixture, _ in session}
        resolve_fixtures(args.fixtures, needed)  # Resolve before any product stimulus; no digest.
        if args.run == "quality":
            metadata["fixture_revision"] = quality_revision(args.fixtures)
        args.deadline = time.monotonic() + args.watchdog
        value = run_child(args, private, args.run)
        if args.run == "lifecycle" and value.get("driver_complete"):
            # First owner-release result must be retained even if restart also succeeds.
            require(all(value.get("cleanup", {}).get(k) is True for k in CLEANUP), "OWNER_REMAINS")
            restart = run_child(args, private, "restart", "-restart")
            require(value.get("log_observed") is True and restart.get("log_observed") is True,
                    "PUBLIC_LOG_OBSERVATION_MISSING")
            value["log_privacy_matches"] = value.get("log_privacy_matches", 0) + restart.get("log_privacy_matches", 0)
            initial = restart.get("initial", {})
            value["restart"] = {key: initial.get(key) is True for key in
                                ("conversation_absent", "main_empty", "display_idle", "resources_ready")}
            value["restart"].update(new_process=value.get("app_pid") != restart.get("app_pid"),
                                    stopped_cleanly=restart.get("driver_complete") is True
                                    and restart.get("exit_code") == 0
                                    and all(restart.get("cleanup", {}).get(k) is True for k in CLEANUP))
            value["cleanup"] = {key: value["cleanup"].get(key) is True
                                and restart.get("cleanup", {}).get(key) is True for key in CLEANUP}
            value["network_attempts"], value["network_fallbacks"] = network_counts(private)
            value["privacy_matches"] = 0
        report = evaluate(args.run, value)
        report.update(**metadata, fixture_ids=sorted(needed), cleanup=value.get("cleanup", {}))
        if args.run == "lifecycle":
            value["privacy_matches"] = privacy_matches(report, value)
            if value["privacy_matches"]:
                report.update(disposition="FAIL", reason_code="PRIVACY_FAILED")
            report["privacy_matches"] = value["privacy_matches"]
    except (OSError, ValueError) as error:
        code = error.code if isinstance(error, InvalidObservation) else "RUNNER_PRECONDITION_FAILED"
        report = {**metadata, "test_id": RUNS[args.run], "disposition": "INVALID", "reason_code": code,
                  "cleanup": value.get("cleanup", {})}
    private_json(private / "run-observation.json", value)
    report["cleanup"] = {key: report.get("cleanup", {}).get(key) is True for key in CLEANUP}
    write_public(root / "result.json", report)
    print(json.dumps(report, separators=(",", ":")))
    return 0 if report["disposition"] in {"PASS", "VALID_BASELINE"} else 2


def execute_experiment(args) -> int:
    diagnostic = getattr(args, "diagnostic_first_use", False)
    single = getattr(args, "diagnostic_single_request", False)
    require(not single or diagnostic, "DIAGNOSTIC_MODE_INVALID")
    require(not diagnostic or (args.run == "pn" and args.cause_control_reason is None), "DIAGNOSTIC_MODE_INVALID")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,95}", args.run_id) is not None, "RUN_ID_INVALID")
    require(args.installed_entry is not None and args.installed_entry.is_file(), "INSTALLED_ENTRY_REQUIRED")
    require(args.cause_control_reason is None or bool(args.cause_control_reason.strip()), "CAUSE_CONTROL_REASON_REQUIRED")
    require(math.isfinite(args.watchdog) and args.watchdog > 0
            and math.isfinite(args.cleanup_timeout) and 0 < args.cleanup_timeout <= 60, "WATCHDOG_INVALID")
    root = args.output.resolve()
    require(not root.is_relative_to(ROOT), "EVIDENCE_INSIDE_REPOSITORY")
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    private = root / "private"
    private.mkdir(mode=0o700)
    report = {"test_id": RUNS[args.run], "run_id": args.run_id, "mode": args.run.upper(),
        "phase": args.phase, "control_enabled": bool(args.cause_control_reason),
        "target": {"architecture": platform.machine(), "python": platform.python_version()},
        "watchdog_seconds": args.watchdog, "clock_resolution_ns": time.get_clock_info("monotonic").resolution * 1e9,
        "timestamp_quantization_ns": 1, "capture_error_bound_ns": None,
        "improvement_claim_allowed": False,
        "limits": {"prefill": "NATIVE_NOT_EXPOSED", "native_render": "NATIVE_NOT_EXPOSED",
                   "admission_render": "EXPOSED", "asr_endpoint": "NOT_EXPOSED",
                   "human_speech_end": "NOT_MEASURED", "acoustic_onset": "NOT_MEASURED"},
        "blocks": [{"block": block, "disposition": "NOT_EXECUTED", "performance": [],
                    "turns": [], "unexecuted_cases": [args.run.upper() + "01"] + (
                        [args.run.upper() + "06"] * 4 if args.cause_control_reason else
                        [args.run.upper() + suffix for suffix in ("02", "04", "03", "05")])}
                   for block in (1, 2)],
        "fixture_revision": "PNPH-20261011", "ranges": [], "disposition": "INVALID", "reason_code": "PRECONDITION_FAILED"}
    observations = []
    if diagnostic:
        report.pop("test_id")  # Focused diagnosis earns no formal PN-case acceptance credit.
        for block in report["blocks"]:
            block["unexecuted_cases"] = ["NATIVE-APP-START"] + (
                ["NATIVE-FIRST", "NATIVE-REUSED"] if block["block"] == 1 else ["NATIVE-FRESH-APP"])
        if single:
            report["blocks"] = report["blocks"][:1]
            report["blocks"][0]["unexecuted_cases"] = ["NATIVE-APP-START", "NATIVE-FIRST"]
    try:
        require(platform.machine() == "aarch64", "PI_TARGET_REQUIRED")
        require(no_previous_app(), "PREVIOUS_APP_PRESENT")
        if args.run == "pn":
            needed = {"FX-SHORT-B"} if diagnostic else {
                fixture for session in session_plan("pn", control=bool(args.cause_control_reason))
                for _, fixture, _ in session}
            resolve_fixtures(args.fixtures, needed)
        for block in ((1,) if single else (1, 2)):
            args.diagnostic_role = ("single_request" if single else
                "first_app" if block == 1 else "fresh_app") if diagnostic else None
            args.deadline = time.monotonic() + args.watchdog
            observed = run_child(args, private, args.run, f"-block-{block}")
            observations.append(observed)
            view = experiment_block(args.run, observed, control=bool(args.cause_control_reason),
                                    diagnostic_role=args.diagnostic_role)
            view["block"] = block
            report["blocks"][block - 1] = view
            if view["disposition"] not in {"VALID_OBSERVATION", "PENDING"}:
                report.update(disposition=view["disposition"], reason_code=view["reason_code"])
                break
        else:
            report.update(disposition="PENDING" if args.run == "ph" else "VALID_OBSERVATION",
                          reason_code="HEARING_REPORT_PENDING" if args.run == "ph" else "BASELINE_CAPTURED")
            if diagnostic:
                report.update(disposition="DIAGNOSTIC_OBSERVATION", reason_code="FOCUSED_CAPTURED")
            else:
                add_experiment_ranges(report)
    except (OSError, ValueError, KeyError, TypeError) as error:
        report.update(disposition="INVALID", reason_code=error.code if isinstance(error, InvalidObservation)
                      else "DIAGNOSTIC_INCOMPLETE")
    private_json(private / "run-observation.json", {"blocks": observations,
        "cause_control_reason": args.cause_control_reason})
    write_public(root / "result.json", report)
    print(json.dumps(report, separators=(",", ":")))
    return 0 if report["disposition"] in {"VALID_OBSERVATION", "DIAGNOSTIC_OBSERVATION"} else 2


def add_experiment_ranges(report: dict) -> None:
    report["ranges"] = []
    if len(report["blocks"]) != 2:
        return
    first, second = (block["performance"] for block in report["blocks"])
    for left, right in zip(first, second, strict=True):
        require(left["case_id"] == right["case_id"], "EXPERIMENT_SEQUENCE_FAILED")
        report["ranges"].append({"case_id": left["case_id"],
            "turn_index": left.get("turn_index"), "durations_ns": {
                key: {"minimum_ns": min(value, right["durations_ns"][key]),
                      "maximum_ns": max(value, right["durations_ns"][key])}
                for key, value in left["durations_ns"].items()}})


def adjudicate(args) -> int:
    if args.run == "ph":
        return adjudicate_hearing(args)
    require(args.run == "quality" and args.judgments is not None, "QUALITY_JUDGMENTS_REQUIRED")
    root = args.adjudicate.resolve()
    old = json.loads((root / "result.json").read_text())
    require(old["test_id"] == RUNS["quality"] and old["disposition"] == "NEEDS_USER_DECISION",
            "QUALITY_NOT_PENDING")
    value = json.loads((root / "private/run-observation.json").read_text())
    judgments = json.loads(args.judgments.read_text())
    report = evaluate("quality", value, judgments=judgments)
    for key in ("run_id", "target", "watchdog_seconds", "fixture_ids", "cleanup", "fixture_revision"):
        if key == "fixture_revision" and key not in old:
            continue  # Retained historical pending observations have their original metadata.
        report[key] = old[key]
    # Preserve the initial objective observation and pending card; adjudication is not a retry.
    write_public(root / "adjudicated-result.json", report)
    private_json(root / "private/semantic-judgments.json", judgments)
    print(json.dumps(report, separators=(",", ":")))
    return 0 if report["disposition"] == "PASS" else 2


def adjudicate_hearing(args) -> int:
    require(args.judgments is not None, "HEARING_REPORT_REQUIRED")
    root = args.adjudicate.resolve()
    report = json.loads((root / "result.json").read_text())
    require(report["test_id"] == RUNS["ph"] and report["disposition"] == "PENDING", "HUMAN_NOT_PENDING")
    observations = json.loads((root / "private/run-observation.json").read_text())
    hearing = json.loads(args.judgments.read_text())
    require(type(hearing) is list and len(hearing) == 8
            and all(type(row) is dict and row.get("block") in {1, 2} for row in hearing), "HEARING_REPORT_INVALID")
    require(all(sorted(row.get("turn_index", -1) for row in hearing if row["block"] == block)
                == list(range(4)) for block in (1, 2)), "HEARING_REPORT_INVALID")
    report["blocks"] = []
    for block, observed in enumerate(observations["blocks"], 1):
        view = experiment_block("ph", observed, control=report["control_enabled"],
                                hearing=[row for row in hearing if row["block"] == block])
        view["block"] = block
        report["blocks"].append(view)
    failed = next((block for block in report["blocks"] if block["disposition"] != "VALID_OBSERVATION"), None)
    report.update(disposition=failed["disposition"] if failed else "VALID_OBSERVATION",
                  reason_code=failed["reason_code"] if failed else "BASELINE_CAPTURED")
    add_experiment_ranges(report)
    write_public(root / "adjudicated-result.json", report)
    private_json(root / "private/hearing-report.json", hearing)
    print(json.dumps(report, separators=(",", ":")))
    return 0 if report["disposition"] == "VALID_OBSERVATION" else 2


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", choices=tuple(RUNS), required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--watchdog", type=float)
    parser.add_argument("--cleanup-timeout", type=float, default=20)
    parser.add_argument("--network-launcher", choices=("unshare", "sudo-unshare"), default="unshare")
    parser.add_argument("--adjudicate", type=Path)
    parser.add_argument("--judgments", type=Path)
    parser.add_argument("--installed-entry", type=Path)
    parser.add_argument("--phase", choices=("before", "after"), default="before")
    parser.add_argument("--cause-control-reason")
    parser.add_argument("--diagnostic-first-use", action="store_true")
    parser.add_argument("--diagnostic-single-request", action="store_true")
    args = parser.parse_args(argv)
    if args.watchdog is None:
        args.watchdog = 1800 if args.run == "ph" else 900
    try:
        if args.adjudicate is not None:
            return adjudicate(args)
        require(all(getattr(args, key) is not None for key in ("run_id", "config", "fixtures", "output")),
                "DEPLOYMENT_ARGUMENTS_REQUIRED")
        return execute(args)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"disposition": "INVALID", "reason_code":
                         error.code if isinstance(error, InvalidObservation) else "RUNNER_FAILED"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
