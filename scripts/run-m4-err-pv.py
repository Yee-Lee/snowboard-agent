#!/usr/bin/env python3
"""Developer runner for one same-bytes M4-ERR Raspberry Pi Verify run.

The runner creates a digest/config-bound run, executes exactly one hardware
Test ID at a time, keeps pytest output private, and finalizes only when all five
cards pass on the unchanged binding.  It is not formal Tester evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sbd.core.candidate_identity import DEFAULT_SCOPES, tracked_content_digest  # noqa: E402
from sbd.core.config import load_config  # noqa: E402


TEST_NODES = {
    "M4-ERR-PV-001": "tests/test_m4_err_pv_rpi.py::test_m4_err_pv_001",
    "M4-ERR-PV-002": "tests/test_m4_err_pv_rpi.py::test_m4_err_pv_002",
    "M4-ERR-PV-003": "tests/test_m4_err_pv_rpi.py::test_m4_err_pv_003",
    "M4-ERR-PV-004": "tests/test_m4_err_pv_rpi.py::test_m4_err_pv_004",
    "M4-ERR-PV-005": "tests/test_m4_err_pv_rpi.py::test_m4_err_pv_005",
}
OBSERVATION_REQUIRED = frozenset({"M4-ERR-PV-001", "M4-ERR-PV-002"})
RUN_ID = re.compile(r"M4-ERR-[A-Za-z0-9][A-Za-z0-9._-]{2,95}")


class RunnerError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _artifact_identity(config_path: Path) -> dict[str, str]:
    config = load_config(
        local_path=config_path, dotenv_path=Path(os.devnull), environ={},
    )
    configured = {
        "asr_lock": config.perception.listen.adapter.artifact_lock_path,
        "llm_lock": config.cognition.llm.artifact_lock_path,
        "llm_profile": config.cognition.llm.product_profile_path,
        "tts_lock": config.action.tts.artifact_lock_path,
    }
    if any(path is None for path in configured.values()):
        raise RunnerError("M4_ERR_ARTIFACT_IDENTITY_MISSING")
    identity = {
        name: _sha256(path.resolve(strict=True))
        for name, path in configured.items()
        if path is not None
    }
    if set(identity) != set(configured) or any(
        re.fullmatch(r"[0-9a-f]{64}", digest) is None for digest in identity.values()
    ):
        raise RunnerError("M4_ERR_ARTIFACT_IDENTITY_INVALID")
    return identity


def _write_json(path: Path, value: object, *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700 if private else 0o755)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600 if private else 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as sink:
        json.dump(value, sink, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        sink.write("\n")


def _read_json(path: Path) -> dict[str, object]:
    try:
        metadata = os.lstat(path)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise RunnerError("M4_ERR_EVIDENCE_PATH_UNSAFE")
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RunnerError("M4_ERR_EVIDENCE_INVALID") from error
    if type(value) is not dict:
        raise RunnerError("M4_ERR_EVIDENCE_INVALID")
    return value


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    )
    return result.stdout.strip()


def _pending_paths(values: list[str]) -> tuple[str, ...]:
    pending = tuple(sorted(set(values)))
    for value in pending:
        path = Path(value)
        if not value or path.is_absolute() or ".." in path.parts:
            raise RunnerError("M4_ERR_PENDING_PATH_INVALID")
        if not (ROOT / path).is_file() or (ROOT / path).is_symlink():
            raise RunnerError("M4_ERR_PENDING_PATH_INVALID")
    actual = set(filter(None, _git(
        "ls-files", "--others", "--exclude-standard", "--", *DEFAULT_SCOPES
    ).splitlines()))
    if actual != set(pending):
        raise RunnerError("M4_ERR_PENDING_PATH_SET_MISMATCH")
    return pending


def _binding(root: Path) -> dict[str, object]:
    return _read_json(root / "private" / "binding.json")


def _verify_binding(root: Path, *, run_id: str) -> dict[str, object]:
    value = _binding(root)
    required = {
        "schema_version", "run_id", "base_sha", "content_sha256", "config_sha256",
        "artifact_identity", "pending_new_paths", "target", "python", "created_at",
    }
    if set(value) != required or value["schema_version"] != 1 or value["run_id"] != run_id:
        raise RunnerError("M4_ERR_BINDING_INVALID")
    pending = tuple(value["pending_new_paths"])
    if tracked_content_digest(ROOT, pending_new_paths=pending) != value["content_sha256"]:
        raise RunnerError("M4_ERR_CONTENT_CHANGED")
    return value


def _init(args: argparse.Namespace) -> int:
    if not RUN_ID.fullmatch(args.run_id):
        raise RunnerError("M4_ERR_RUN_ID_INVALID")
    root = args.output.resolve()
    if root == ROOT or root.is_relative_to(ROOT) or root.exists():
        raise RunnerError("M4_ERR_OUTPUT_MUST_BE_NEW_AND_OUTSIDE_REPOSITORY")
    if platform.system() != "Linux" or platform.machine() not in {"aarch64", "arm64"}:
        raise RunnerError("M4_ERR_TARGET_NOT_RASPBERRY_PI_AARCH64")
    if sys.version_info[:3] != (3, 13, 5):
        raise RunnerError("M4_ERR_TARGET_PYTHON_MISMATCH")
    config = args.config.resolve(strict=True)
    pending = _pending_paths(args.pending_path)
    value = {
        "schema_version": 1,
        "run_id": args.run_id,
        "base_sha": _git("rev-parse", "HEAD"),
        "content_sha256": tracked_content_digest(ROOT, pending_new_paths=pending),
        "config_sha256": _sha256(config),
        "artifact_identity": _artifact_identity(config),
        "pending_new_paths": list(pending),
        "target": "pi5-4gb-debian13-aarch64-cp3135",
        "python": platform.python_version(),
        "created_at": datetime.now(UTC).isoformat(),
    }
    (root / "private").mkdir(parents=True, mode=0o700)
    (root / "public").mkdir(mode=0o755)
    _write_json(root / "private" / "binding.json", value, private=True)
    _write_json(root / "public" / "binding.json", {
        key: value[key] for key in (
            "schema_version", "run_id", "base_sha", "content_sha256",
            "config_sha256", "artifact_identity", "target", "python", "created_at",
        )
    })
    return 0


def _junit_counts(path: Path) -> dict[str, int]:
    try:
        root = ElementTree.fromstring(path.read_bytes())
    except (OSError, ElementTree.ParseError) as error:
        raise RunnerError("M4_ERR_JUNIT_INVALID") from error
    cases = root.findall(".//testcase")
    if len(cases) != 1:
        raise RunnerError("M4_ERR_JUNIT_CASE_COUNT_INVALID")
    case = cases[0]
    failed = int(case.find("failure") is not None or case.find("error") is not None)
    skipped = int(case.find("skipped") is not None)
    return {"passed": int(not failed and not skipped), "failed": failed, "skipped": skipped}


def _observation_identity(root: Path, test_id: str) -> dict[str, str] | None:
    path = root / "private" / test_id / "product-observation.json"
    if test_id not in OBSERVATION_REQUIRED:
        return None
    if not path.is_file() or path.is_symlink():
        raise RunnerError("M4_ERR_PRODUCT_OBSERVATION_MISSING")
    return {
        "locator": f"private/{test_id}/product-observation.json",
        "sha256": _sha256(path),
    }


def _run_case(args: argparse.Namespace) -> int:
    if args.test_id not in TEST_NODES:
        raise RunnerError("M4_ERR_TEST_ID_INVALID")
    root = args.output.resolve(strict=True)
    binding = _verify_binding(root, run_id=args.run_id)
    config = args.config.resolve(strict=True)
    if _sha256(config) != binding["config_sha256"]:
        raise RunnerError("M4_ERR_CONFIG_CHANGED")
    if _artifact_identity(config) != binding["artifact_identity"]:
        raise RunnerError("M4_ERR_ARTIFACT_IDENTITY_CHANGED")
    private = root / "private" / args.test_id
    public = root / "public" / args.test_id
    private.mkdir(mode=0o700)
    public.mkdir(mode=0o755)
    junit = private / "junit.xml"
    log_path = private / "pytest.log"
    environment = {
        **os.environ,
        "PYTHONPATH": str(SRC),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "SBD_M4_ERR_CONFIG": str(config),
        "SBD_M4_ERR_RUN_ROOT": str(root),
        "SBD_M4_ERR_RUN_ID": args.run_id,
        "SBD_M4_ERR_TEST_ID": args.test_id,
    }
    if args.asr_wav is not None:
        environment["SBD_M4_ERR_ASR_WAV"] = str(args.asr_wav.resolve(strict=True))
    command = [
        sys.executable, "-B", "-m", "pytest", "-p", "pytest_asyncio.plugin",
        "-p", "pytest_timeout", "-o", "addopts=", "--strict-markers", "--timeout=1800",
        "-q", "-m", "rpi", f"--junit-xml={junit}", TEST_NODES[args.test_id],
    ]
    started = datetime.now(UTC).isoformat()
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=1900,
    )
    descriptor = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as sink:
        sink.write(result.stdout)
    counts = _junit_counts(junit)
    status = "Pass" if result.returncode == 0 and counts == {
        "passed": 1, "failed": 0, "skipped": 0,
    } else "Fail"
    card = {
        "schema_version": 1,
        "run_id": args.run_id,
        "test_id": args.test_id,
        "status": status,
        "content_sha256": binding["content_sha256"],
        "config_sha256": binding["config_sha256"],
        "artifact_identity": binding["artifact_identity"],
        "target": binding["target"],
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "exit_code": result.returncode,
        "counts": counts,
        "private_log_sha256": _sha256(log_path),
        "junit_sha256": _sha256(junit),
    }
    observation = _observation_identity(root, args.test_id)
    if observation is not None:
        card["product_observation"] = observation
    _write_json(public / "result.json", card)
    return 0 if status == "Pass" else 1


def _finalize(args: argparse.Namespace) -> int:
    root = args.output.resolve(strict=True)
    binding = _verify_binding(root, run_id=args.run_id)
    cards = []
    for test_id in TEST_NODES:
        card = _read_json(root / "public" / test_id / "result.json")
        observation = _observation_identity(root, test_id)
        if (
            card.get("run_id") != args.run_id
            or card.get("test_id") != test_id
            or card.get("status") != "Pass"
            or card.get("content_sha256") != binding["content_sha256"]
            or card.get("config_sha256") != binding["config_sha256"]
            or card.get("artifact_identity") != binding["artifact_identity"]
            or (
                observation is not None
                and card.get("product_observation") != observation
            )
        ):
            raise RunnerError("M4_ERR_FINALIZE_CARD_INVALID")
        cards.append(card)
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "status": "Pass",
        "content_sha256": binding["content_sha256"],
        "config_sha256": binding["config_sha256"],
        "artifact_identity": binding["artifact_identity"],
        "test_ids": list(TEST_NODES),
        "card_sha256": {
            test_id: _sha256(root / "public" / test_id / "result.json")
            for test_id in TEST_NODES
        },
        "finished_at": datetime.now(UTC).isoformat(),
    }
    _write_json(root / "public" / "final.json", manifest)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--run-id", required=True)
    common.add_argument("--output", type=Path, required=True)
    initialize = subparsers.add_parser("init", parents=[common])
    initialize.add_argument("--config", type=Path, required=True)
    initialize.add_argument("--pending-path", action="append", default=[])
    case = subparsers.add_parser("case", parents=[common])
    case.add_argument("--config", type=Path, required=True)
    case.add_argument("--test-id", choices=tuple(TEST_NODES), required=True)
    case.add_argument("--asr-wav", type=Path)
    subparsers.add_parser("finalize", parents=[common])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return {"init": _init, "case": _run_case, "finalize": _finalize}[args.command](args)
    except (RunnerError, subprocess.SubprocessError, OSError, ValueError) as error:
        sys.stderr.write(f"{type(error).__name__}: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
