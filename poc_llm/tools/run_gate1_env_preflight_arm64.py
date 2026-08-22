#!/usr/bin/env python3
"""ARM64-only, no-model environment preflight runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import zipfile


EXPECTED_WHEEL_SHA256 = "5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00"
PACKET_ID = "GATE1-ENV-PREFLIGHT-ARM64-001"
ENVIRONMENT_ID = "ENV-UTM-ARM64-001"
ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def run(argv: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=ROOT, env=env, text=True, capture_output=True, check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--install-dir", type=Path, required=True)
    parser.add_argument("--host-netns", required=True)
    args = parser.parse_args()

    report: dict[str, object] = {
        "packet_id": PACKET_ID,
        "environment_id": ENVIRONMENT_ID,
        "scope": "ARM64_ONLY",
        "candidate_evidence": False,
        "result": "INCONCLUSIVE",
        "checks": {},
        "repetitions": [],
        "cleanup": {"isolated_install_removed": False, "owned_processes_absent": False},
        "violations": [],
    }
    checks = report["checks"]
    violations = report["violations"]
    assert isinstance(checks, dict) and isinstance(violations, list)

    if args.raw_dir.exists() or args.install_dir.exists():
        violations.append("raw or isolated install path is dirty/reused")
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
        return 2

    args.raw_dir.mkdir(parents=True)
    raw_log = args.raw_dir / "arm64-preflight.log"
    log_lines: list[str] = []

    try:
        interfaces = sorted(item.name for item in Path("/sys/class/net").iterdir())
        self_netns = os.readlink("/proc/self/ns/net")
        route_lines = Path("/proc/net/route").read_text(encoding="utf-8").splitlines()
        checks["network_interfaces"] = interfaces
        checks["network_namespace_isolated"] = self_netns != args.host_netns
        checks["ipv4_route_table_empty"] = len(route_lines) <= 1
        checks["network_disabled"] = (
            checks["network_namespace_isolated"] and checks["ipv4_route_table_empty"]
        )
        checks["machine_aarch64"] = platform.machine() == "aarch64"
        checks["wheel_present"] = args.wheel.is_file()
        wheel_sha = digest(args.wheel) if args.wheel.is_file() else "unavailable"
        checks["wheel_sha256"] = wheel_sha
        checks["wheel_authenticated"] = wheel_sha == EXPECTED_WHEEL_SHA256
        if not all((checks["network_disabled"], checks["machine_aarch64"], checks["wheel_authenticated"])):
            raise RuntimeError("environment or wheel admission failed")

        args.install_dir.mkdir(parents=True)
        with zipfile.ZipFile(args.wheel) as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise RuntimeError("wheel archive integrity failed")
            archive.extractall(args.install_dir)

        native = args.install_dir / "litert_lm/liblitert-lm.so"
        native_file = run(["file", str(native)])
        link = run(["ldd", str(native)])
        log_lines.extend((native_file.stdout, native_file.stderr, link.stdout, link.stderr))
        checks["native_aarch64"] = native_file.returncode == 0 and "ARM aarch64" in native_file.stdout
        checks["native_link_complete"] = link.returncode == 0 and "not found" not in link.stdout + link.stderr
        checks["native_sha256"] = digest(native)
        if not checks["native_aarch64"] or not checks["native_link_complete"]:
            raise RuntimeError("native architecture or linkage failed")

        child_env = os.environ.copy()
        child_env["PYTHONPATH"] = str(args.install_dir)
        child_env["PYTHONPYCACHEPREFIX"] = str(args.install_dir / "pycache")
        for repetition in range(1, 4):
            imported = run(
                [sys.executable, "-c", "import litert_lm; from litert_lm._ffi import _get_lib; _get_lib(); print('NATIVE_IMPORT_OK')"],
                env=child_env,
            )
            lifecycle = run(
                [
                    sys.executable,
                    "-m",
                    "unittest",
                    "poc_llm.tests.gate1.test_m1_contract.M1ContractTest.test_complete_contract_self_test_passes",
                    "poc_llm.tests.gate1.test_m1_contract.M1ContractTest.test_timeout_and_cancel_cleanup_restore_terminal_readiness",
                ],
                env=child_env,
            )
            log_lines.extend((imported.stdout, imported.stderr, lifecycle.stdout, lifecycle.stderr))
            passed = (
                imported.returncode == 0
                and imported.stdout.strip() == "NATIVE_IMPORT_OK"
                and lifecycle.returncode == 0
            )
            repetitions = report["repetitions"]
            assert isinstance(repetitions, list)
            repetitions.append(
                {
                    "repetition": repetition,
                    "native_import_exit": imported.returncode,
                    "lifecycle_exit": lifecycle.returncode,
                    "passed": passed,
                }
            )
            if not passed:
                raise RuntimeError(f"repetition {repetition} failed")

        checks["bundle_unchanged"] = digest(args.wheel) == EXPECTED_WHEEL_SHA256
        report["result"] = "PASS" if checks["bundle_unchanged"] else "FAIL"
    except Exception as error:  # fail closed and retain sanitized reason
        violations.append(str(error))
    finally:
        raw_log.write_text("".join(log_lines), encoding="utf-8")
        shutil.rmtree(args.install_dir, ignore_errors=True)
        cleanup = report["cleanup"]
        assert isinstance(cleanup, dict)
        cleanup["isolated_install_removed"] = not args.install_dir.exists()
        owned = run(["pgrep", "-f", "poc_llm/tests/gate1/fake_candidate.py"])
        cleanup["owned_processes_absent"] = owned.returncode == 1
        report["raw_log_sha256"] = digest(raw_log)
        report["completed_unix_seconds"] = int(time.time())
        if not cleanup["isolated_install_removed"] or not cleanup["owned_processes_absent"]:
            report["result"] = "FAIL"
            violations.append("run-owned cleanup proof failed")

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
