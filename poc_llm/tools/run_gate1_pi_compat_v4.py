#!/usr/bin/env python3
"""Bounded Gate 1 product-Pi compatibility runner; never emits Gate 2 credit."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time
from typing import Any

import jsonschema


PACKET_ID = "G1-X86-PI-COMPAT-004"
TEST_ID = "G1-PI-COMPAT-004"
PLATFORM_ID = "pi5-4gb-debian13-aarch64"
ROOT = Path(__file__).resolve().parents[2]
CORE_PATH = ROOT / "poc_llm/tools/run_gate1_prescreen.py"
INSTALL_TIMEOUT = 300.0
LOAD_TIMEOUT = 180.0
REQUEST_TIMEOUT = 30.0


class CompatibilityFailure(RuntimeError):
    pass


class EvidenceFailure(RuntimeError):
    pass


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_digest(argv: list[str]) -> str:
    value = json.dumps(argv, ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(value).hexdigest()


def resolve_artifact(item: dict[str, Any], label: str) -> Path:
    path = (ROOT / item["path"]).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file() or digest(path) != item["sha256"]:
        raise EvidenceFailure(f"{label} artifact identity mismatch")
    return path


def locked_paths(lock: dict[str, Any]) -> dict[str, Path]:
    return {key: resolve_artifact(item, f"locked {key}") for key, item in lock["artifacts"].items()}


def load_core() -> Any:
    spec = importlib.util.spec_from_file_location("gate1_pi_runner_core_v3", CORE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("process lifecycle core cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, raw = line.split(":", 1)
        if key in {"MemTotal", "MemAvailable", "SwapTotal"}:
            values[key] = int(raw.strip().split()[0]) * 1024
    return values


def os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')
    return values


def git_state() -> tuple[str, bool]:
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    return sha, not bool(dirty)


def expand(argv: list[str], isolated_dir: Path) -> list[str]:
    return [item.replace("{isolated_dir}", str(isolated_dir)) for item in argv]


def blank_report(args: argparse.Namespace) -> dict[str, Any]:
    checks = {key: "Pending" for key in (
        "preselected", "artifacts", "offline_install", "runtime_import", "runtime_version",
        "model_load", "ready", "ping", "minimal_generation", "shutdown", "exit",
        "orphan_zero", "isolated_cleanup",
    )}
    return {
        "packet_id":PACKET_ID, "test_id":TEST_ID, "selection_cycle_id":args.selection_cycle_id,
        "run_id":args.run_id, "candidate_id":"UNBOUND", "pairing_revision":"UNBOUND",
        "platform":PLATFORM_ID, "result":"INCONCLUSIVE",
        "identity":{key:"0" * 64 for key in (
            "lock_sha256", "manifest_sha256", "acquisition_manifest_sha256", "preselection_sha256",
            "command_sha256", "logical_runtime_source_sha256", "runtime_sha256",
            "dependency_bundle_sha256", "model_sha256", "config_sha256",
            "pi_result_schema_sha256", "runner_sha256",
        )},
        "environment":{
            "git_sha":"0" * 64, "git_clean":False, "os_id":"unknown", "os_version":"unknown",
            "machine":platform.machine(), "mem_total_bytes":0,
            "network_disabled_proof_sha256":"0" * 64, "raw_path_reused":args.raw_dir.exists(),
        },
        "checks":checks,
        "observations":{
            "swap_total_bytes":0, "mem_available_before_bytes":0, "mem_available_after_bytes":0,
            "disk_free_before_bytes":0, "disk_free_after_bytes":0, "elapsed_ms":0,
            "informational_only":True,
        },
        "cleanup":{
            "exit_code":None, "waited":False, "term_sent":False, "kill_sent":False,
            "process_group_absent":True, "isolated_environment_removed":False,
        },
        "violations":[],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection-cycle-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--preselection", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--network-disabled-proof", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--isolated-dir", type=Path, required=True)
    args = parser.parse_args()
    report = blank_report(args)
    core = load_core()
    process: subprocess.Popen[str] | None = None
    started = time.monotonic()
    exit_code = 2
    try:
        if args.raw_dir.exists() or args.isolated_dir.exists():
            raise EvidenceFailure("raw or isolated evidence path is dirty/reused")
        lock = load(args.lock)
        paths = locked_paths(lock)
        manifest = load(args.candidate_manifest)
        jsonschema.validate(manifest, load(paths["candidate_schema"]))
        preselection = load(args.preselection)
        jsonschema.validate(preselection, load(paths["selection_schema"]))
        if preselection["stage"] != "PRESELECTION" or preselection["selection_cycle_id"] != args.selection_cycle_id:
            raise EvidenceFailure("preselection stage/cycle mismatch")
        key = (manifest["candidate_id"], manifest["pairing_revision"])
        allowed = {(item["candidate_id"], item["pairing_revision"]) for item in preselection["preselected_candidates"]}
        if key not in allowed:
            raise EvidenceFailure("candidate was not preselected; third-candidate backfill forbidden")
        report["checks"]["preselected"] = "PASS"
        acquisition_path = resolve_artifact(manifest["acquisition_manifest"], "acquisition manifest")
        acquisition = load(acquisition_path)
        jsonschema.validate(acquisition, load(paths["acquisition_schema"]))
        if (
            acquisition["candidate_id"] != key[0]
            or acquisition["pairing_revision"] != key[1]
            or acquisition["logical_runtime"] != manifest["logical_runtime"]
        ):
            raise EvidenceFailure("candidate/acquisition logical identity mismatch")
        native = acquisition["platforms"]["pi-debian13-aarch64"]
        resolve_artifact(native["runtime_artifact"], "Pi runtime")
        resolve_artifact(native["dependency_bundle"], "Pi dependency bundle")
        resolve_artifact(manifest["model"], "model")
        resolve_artifact(manifest["config"], "config")
        if command_digest(native["install_argv"]) != native["install_argv_sha256"]:
            raise EvidenceFailure("Pi install command identity mismatch")
        command = manifest["commands"]["pi-debian13-aarch64"]
        if command_digest(command["argv"]) != command["sha256"]:
            raise EvidenceFailure("Pi runtime command identity mismatch")
        report["checks"]["artifacts"] = "PASS"

        release = os_release()
        memory = meminfo()
        git_sha, git_clean = git_state()
        proof = load(args.network_disabled_proof)
        if proof.get("network_disabled") is not True:
            raise EvidenceFailure("network-disabled proof is invalid")
        report["candidate_id"], report["pairing_revision"] = key
        report["identity"] = {
            "lock_sha256":digest(args.lock), "manifest_sha256":digest(args.candidate_manifest),
            "acquisition_manifest_sha256":digest(acquisition_path),
            "preselection_sha256":digest(args.preselection), "command_sha256":command["sha256"],
            "logical_runtime_source_sha256":manifest["logical_runtime"]["source_sha256"],
            "runtime_sha256":native["runtime_artifact"]["sha256"],
            "dependency_bundle_sha256":native["dependency_bundle"]["sha256"],
            "model_sha256":manifest["model"]["sha256"], "config_sha256":manifest["config"]["sha256"],
            "pi_result_schema_sha256":lock["artifacts"]["pi_result_schema"]["sha256"],
            "runner_sha256":lock["artifacts"]["pi_runner"]["sha256"],
        }
        report["environment"] = {
            "git_sha":git_sha, "git_clean":git_clean, "os_id":release.get("ID", "unknown"),
            "os_version":release.get("VERSION_ID", "unknown"), "machine":platform.machine(),
            "mem_total_bytes":memory.get("MemTotal", 0),
            "network_disabled_proof_sha256":digest(args.network_disabled_proof),
            "raw_path_reused":False,
        }
        report["observations"].update({
            "swap_total_bytes":memory.get("SwapTotal", 0),
            "mem_available_before_bytes":memory.get("MemAvailable", 0),
            "disk_free_before_bytes":shutil.disk_usage(ROOT).free,
        })
        if not git_clean or release.get("ID") != "debian" or release.get("VERSION_ID") != "13" or platform.machine() != "aarch64":
            raise EvidenceFailure("Pi environment identity is not approved")

        args.raw_dir.mkdir(parents=True, exist_ok=False)
        args.isolated_dir.mkdir(parents=True, exist_ok=False)
        install = subprocess.run(
            expand(native["install_argv"], args.isolated_dir), cwd=ROOT, check=False,
            capture_output=True, text=True, timeout=INSTALL_TIMEOUT,
            env={**os.environ, "PIP_NO_INDEX":"1", "HF_HUB_OFFLINE":"1", "TRANSFORMERS_OFFLINE":"1"},
        )
        (args.raw_dir / "install.stderr").write_text(install.stderr, encoding="utf-8")
        if install.returncode != 0:
            report["checks"]["offline_install"] = "FAIL"
            raise CompatibilityFailure("isolated offline installation failed")
        report["checks"]["offline_install"] = report["checks"]["runtime_import"] = "PASS"

        stderr_path = args.raw_dir / "candidate.stderr"
        with stderr_path.open("w", encoding="utf-8") as stderr_stream:
            process = subprocess.Popen(
                expand(command["argv"], args.isolated_dir), cwd=ROOT, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=stderr_stream, text=True, start_new_session=True,
                env={**os.environ, "HF_HUB_OFFLINE":"1", "TRANSFORMERS_OFFLINE":"1"},
            )
            ready = core.read_frame(process.stdout, LOAD_TIMEOUT) if process.stdout else {}
        expected = {
            "type":"READY", "candidate_id":key[0],
            "runtime_sha256":native["runtime_artifact"]["sha256"],
            "model_sha256":manifest["model"]["sha256"], "config_sha256":manifest["config"]["sha256"],
            "runtime_version":manifest["logical_runtime"]["version"],
        }
        if any(ready.get(item) != value for item, value in expected.items()):
            report["checks"]["ready"] = "FAIL"
            raise CompatibilityFailure("READY/runtime/model/config identity mismatch")
        for check in ("runtime_version", "model_load", "ready"):
            report["checks"][check] = "PASS"
        captured: list[str] = []
        if core.request(process, {"op":"PING"}, captured, REQUEST_TIMEOUT).get("type") != "PONG":
            report["checks"]["ping"] = "FAIL"
            raise CompatibilityFailure("PING compatibility probe failed")
        report["checks"]["ping"] = "PASS"
        generated = core.request(
            process,
            {"op":"MINIMAL_GENERATE","input_ref":"public.synthetic.compatibility.fixed-v1","max_output_tokens":1,"temperature":0},
            captured, REQUEST_TIMEOUT,
        )
        if generated.get("type") != "RESULT" or generated.get("status") != "OK":
            report["checks"]["minimal_generation"] = "FAIL"
            raise CompatibilityFailure("minimal deterministic generation failed")
        report["checks"]["minimal_generation"] = "PASS"
        shutdown = core.request(process, {"op":"SHUTDOWN"}, captured, REQUEST_TIMEOUT)
        if shutdown.get("type") != "SHUTDOWN_ACK":
            report["checks"]["shutdown"] = "FAIL"
            raise CompatibilityFailure("SHUTDOWN acknowledgement failed")
        report["checks"]["shutdown"] = "PASS"
        process.wait(timeout=core.TERM_GRACE)
        report["cleanup"].update(core.stop(process))
        if (
            report["cleanup"]["exit_code"] != 0 or report["cleanup"]["term_sent"]
            or report["cleanup"]["kill_sent"] or not report["cleanup"]["process_group_absent"]
        ):
            raise CompatibilityFailure("Pi exit/orphan cleanup failed")
        report["checks"]["exit"] = report["checks"]["orphan_zero"] = "PASS"
        report["result"] = "PASS"
        exit_code = 0
    except CompatibilityFailure as error:
        report["violations"].append(str(error))
        report["result"] = "FAIL"
        exit_code = 1
    except (
        EvidenceFailure, json.JSONDecodeError, jsonschema.ValidationError, OSError,
        subprocess.SubprocessError, KeyError, TypeError, ValueError,
    ) as error:
        report["violations"].append(str(error))
        report["result"] = "INCONCLUSIVE"
        exit_code = 2
    finally:
        if process is not None and not report["cleanup"]["waited"]:
            report["cleanup"].update(core.stop(process))
        if args.isolated_dir.exists():
            shutil.rmtree(args.isolated_dir)
        report["cleanup"]["isolated_environment_removed"] = not args.isolated_dir.exists()
        report["checks"]["isolated_cleanup"] = (
            "PASS" if report["cleanup"]["isolated_environment_removed"] else "FAIL"
        )
        after = meminfo()
        report["observations"].update({
            "mem_available_after_bytes":after.get("MemAvailable", 0),
            "disk_free_after_bytes":shutil.disk_usage(ROOT).free,
            "elapsed_ms":round((time.monotonic() - started) * 1000, 3),
        })
        try:
            if "paths" in locals():
                jsonschema.validate(report, load(paths["pi_result_schema"]))
        except jsonschema.ValidationError as error:
            report["result"] = "INCONCLUSIVE"
            report["violations"].append(f"Pi result schema failure: {error.message}")
            exit_code = 2
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
