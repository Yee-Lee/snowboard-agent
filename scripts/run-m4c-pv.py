#!/usr/bin/env python3
"""M4C Raspberry Pi product-verification coordinator."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

CATALOG = (
    ("M4C-PI-S01", "START_IDLE"),
    ("M4C-PI-S02", "NORMAL_END_B2"),
    ("M4C-PI-S03", "TWO_TIMEOUTS"),
    ("M4C-PI-S04", "PERCEPTION"),
    ("M4C-PI-S04", "THINK"),
    ("M4C-PI-S04", "ACTION"),
    ("M4C-PI-S05", "APP_EXIT"),
)
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,95}")
SUB_RUN_ID = RUN_ID
RESULT_FIELDS = {
    "schema_version", "test_id", "variant", "sub_run_id",
    "started_monotonic_ns", "ended_monotonic_ns", "script_status",
    "public_evidence",
}
FORBIDDEN_PUBLIC_KEYS = {
    "transcript", "prompt", "raw_model_output", "pcm", "session_id",
    "credential", "private_path", "text", "fragments",
}


class RunnerError(RuntimeError):
    pass


def _safe_regular(path: Path) -> None:
    metadata = os.lstat(path)
    if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise RunnerError("M4C_PATH_UNSAFE")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        _safe_regular(path)
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RunnerError("M4C_JSON_INVALID") from error
    if type(value) is not dict:
        raise RunnerError("M4C_JSON_INVALID")
    return value


def _write_json(path: Path, value: object, *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700 if private else 0o755)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600 if private else 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as sink:
        json.dump(value, sink, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        sink.write("\n")


def _replace_json(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    _write_json(temporary, value)
    os.replace(temporary, path)


def _empty_root(path: Path, *, mode: int) -> Path:
    resolved = path.resolve()
    if resolved == ROOT or resolved.is_relative_to(ROOT):
        raise RunnerError("M4C_EVIDENCE_ROOT_INSIDE_REPOSITORY")
    if resolved.exists():
        if not resolved.is_dir() or resolved.is_symlink() or any(resolved.iterdir()):
            raise RunnerError("M4C_EVIDENCE_ROOT_NOT_NEW_EMPTY")
    else:
        resolved.mkdir(parents=True, mode=mode)
    os.chmod(resolved, mode)
    return resolved


def _run_roots(public_root: Path, private_root: Path, run_id: str):
    return public_root.resolve() / run_id, private_root.resolve() / run_id


def _init(args: argparse.Namespace) -> int:
    if RUN_ID.fullmatch(args.pv_run_id) is None:
        raise RunnerError("M4C_RUN_ID_INVALID")
    public_root = _empty_root(args.public_root, mode=0o755)
    private_root = _empty_root(args.private_root, mode=0o700)
    public_run, private_run = _run_roots(public_root, private_root, args.pv_run_id)
    public_run.mkdir(mode=0o755)
    private_run.mkdir(mode=0o700)
    identity = {
        "schema_version": 1, "pv_run_id": args.pv_run_id,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _write_json(private_run / "run.json", identity, private=True)
    _write_json(public_run / "run.json", identity)
    return 0


def _load_run(args: argparse.Namespace):
    if RUN_ID.fullmatch(args.pv_run_id) is None:
        raise RunnerError("M4C_RUN_ID_INVALID")
    public_run, private_run = _run_roots(args.public_root, args.private_root, args.pv_run_id)
    private_identity = _read_json(private_run.resolve(strict=True) / "run.json")
    public_identity = _read_json(public_run.resolve(strict=True) / "run.json")
    if private_identity != public_identity:
        raise RunnerError("M4C_RUN_IDENTITY_MISMATCH")
    if private_identity.get("pv_run_id") != args.pv_run_id:
        raise RunnerError("M4C_RUN_IDENTITY_MISMATCH")
    return public_run, private_run


def _under(path: Path, parent: Path) -> bool:
    resolved = path.resolve()
    return resolved != parent and resolved.is_relative_to(parent)


def _validate_private_result(value: dict[str, Any], args) -> None:
    if "user_result" in value:
        raise RunnerError("M4C_USER_RESULT_FORBIDDEN")
    if set(value) != RESULT_FIELDS:
        raise RunnerError("M4C_RESULT_SCHEMA_INVALID")
    if (value["schema_version"] != 1 or value["test_id"] != args.test_id
            or value["variant"] != args.variant or value["sub_run_id"] != args.sub_run_id):
        raise RunnerError("M4C_RESULT_IDENTITY_INVALID")
    if value["script_status"] not in {"Pass", "Fail", "Incomplete", "Blocked"}:
        raise RunnerError("M4C_RESULT_STATUS_INVALID")
    if (type(value["started_monotonic_ns"]) is not int
            or type(value["ended_monotonic_ns"]) is not int
            or not 0 < value["started_monotonic_ns"] <= value["ended_monotonic_ns"]):
        raise RunnerError("M4C_RESULT_TIMING_INVALID")
    if type(value["public_evidence"]) is not dict:
        raise RunnerError("M4C_RESULT_EVIDENCE_INVALID")
    _privacy_scan(value["public_evidence"])


def _public_card(private: dict[str, Any], attempt_id: str) -> dict[str, Any]:
    card = {key: private[key] for key in RESULT_FIELDS}
    card.update(attempt_id=attempt_id, designated=True, superseded_by=None)
    return card


def _run(args: argparse.Namespace) -> int:
    if (args.test_id, args.variant) not in CATALOG:
        raise RunnerError("M4C_VARIANT_INVALID")
    if SUB_RUN_ID.fullmatch(args.sub_run_id) is None or not args.fresh_setup:
        raise RunnerError("M4C_FRESH_SETUP_REQUIRED")
    public_partition = args.public_partition.resolve()
    private_partition = args.private_partition.resolve()
    public_matches = [parent for parent in public_partition.parents
                      if parent.name == args.pv_run_id]
    private_matches = [parent for parent in private_partition.parents
                       if parent.name == args.pv_run_id]
    if len(public_matches) != 1 or len(private_matches) != 1:
        raise RunnerError("M4C_PARTITION_INVALID")
    args.public_root = public_matches[0].parent
    args.private_root = private_matches[0].parent
    public_run, private_run = _load_run(args)
    config_path = args.config.resolve(strict=True)
    _safe_regular(config_path)
    if (not _under(public_partition, public_run) or not _under(private_partition, private_run)
            or public_partition.exists() or private_partition.exists()):
        raise RunnerError("M4C_PARTITION_INVALID")
    public_partition.mkdir(parents=True, mode=0o755)
    private_partition.mkdir(parents=True, mode=0o700)
    started = datetime.now(UTC).isoformat()
    environment = {
        **os.environ,
        "PYTHONPATH": f"{SRC}:{ROOT}",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "SBD_M4C_TEST_ID": args.test_id,
        "SBD_M4C_VARIANT": args.variant,
        "SBD_M4C_SUB_RUN_ID": args.sub_run_id,
        "SBD_M4C_PRIVATE_PARTITION": str(private_partition),
        "SBD_M4C_CONFIG": str(config_path),
    }
    for option, name in (
        (args.utterance, "SBD_M4C_UTTERANCE"),
        (args.utterance_1, "SBD_M4C_UTTERANCE_1"),
        (args.utterance_2, "SBD_M4C_UTTERANCE_2"),
    ):
        if option is not None:
            if type(option) is not str or not option.strip() or "\x00" in option:
                raise RunnerError("M4C_UTTERANCE_INVALID")
            environment[name] = option
    command = [
        sys.executable, "-m", "pytest", "-p", "pytest_asyncio.plugin",
        "-p", "pytest_timeout", "-o", "addopts=", "--strict-markers",
        "--timeout=3300", "-m", "rpi", "-q",
        "tests/test_m4c_pv_rpi.py::test_m4c_product_scenario",
    ]
    completed = subprocess.run(
        command, cwd=ROOT, env=environment, stdin=None,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=3600)
    log = private_partition / "pytest.log"
    log.write_text(completed.stdout, encoding="utf-8")
    os.chmod(log, 0o600)
    result_path = private_partition / "result.json"
    if not result_path.is_file():
        raise RunnerError("M4C_PRIVATE_RESULT_MISSING")
    result = _read_json(result_path)
    _validate_private_result(result, args)
    if completed.returncode != 0 and result["script_status"] == "Pass":
        raise RunnerError("M4C_PYTEST_RESULT_CONTRADICTION")
    attempt_id = f"{args.test_id}-{args.variant}-{args.sub_run_id}"
    card = _public_card(result, attempt_id)
    card["started_at"] = started
    card["ended_at"] = datetime.now(UTC).isoformat()
    result_card = public_partition / "result.json"
    _write_json(result_card, card)

    registry_path = public_run / "designations.json"
    registry = _read_json(registry_path) if registry_path.exists() else {
        "schema_version": 1, "pv_run_id": args.pv_run_id, "attempts": []}
    if (set(registry) != {"schema_version", "pv_run_id", "attempts"}
            or registry["schema_version"] != 1
            or registry["pv_run_id"] != args.pv_run_id
            or type(registry["attempts"]) is not list):
        raise RunnerError("M4C_DESIGNATION_INVALID")
    for previous in registry["attempts"]:
        if (previous["test_id"], previous["variant"]) == (args.test_id, args.variant) and previous["designated"]:
            previous["designated"] = False
            previous["superseded_by"] = attempt_id
            old_card_path = public_run / previous["card"]
            old_card = _read_json(old_card_path)
            old_card["designated"] = False
            old_card["superseded_by"] = attempt_id
            _replace_json(old_card_path, old_card)
    registry["attempts"].append({
        "attempt_id": attempt_id, "test_id": args.test_id, "variant": args.variant,
        "sub_run_id": args.sub_run_id, "card": str(result_card.relative_to(public_run)),
        "designated": True, "superseded_by": None,
    })
    if registry_path.exists():
        _replace_json(registry_path, registry)
    else:
        _write_json(registry_path, registry)
    return 0 if card["script_status"] == "Pass" else 2


def _privacy_scan(value: object, path: str = "$") -> None:
    if type(value) is dict:
        for key, item in value.items():
            if key in FORBIDDEN_PUBLIC_KEYS:
                raise RunnerError("M4C_PUBLIC_PRIVACY_VIOLATION")
            _privacy_scan(item, f"{path}.{key}")
    elif type(value) is list:
        for index, item in enumerate(value):
            _privacy_scan(item, f"{path}[{index}]")
    elif type(value) is str and (str(Path.home()) in value or "\n" in value):
        raise RunnerError("M4C_PUBLIC_PRIVACY_VIOLATION")


def _finalize(args: argparse.Namespace) -> int:
    public_run, _ = _load_run(args)
    registry = _read_json(public_run / "designations.json")
    if (set(registry) != {"schema_version", "pv_run_id", "attempts"}
            or registry.get("schema_version") != 1
            or registry.get("pv_run_id") != args.pv_run_id):
        raise RunnerError("M4C_DESIGNATION_INVALID")
    attempts = registry.get("attempts")
    if type(attempts) is not list or not attempts:
        raise RunnerError("M4C_DESIGNATION_INVALID")
    active: dict[tuple[str, str], dict[str, Any]] = {}
    ids = set()
    for attempt in attempts:
        if (type(attempt) is not dict or set(attempt) != {
                "attempt_id", "test_id", "variant", "sub_run_id", "card",
                "designated", "superseded_by"}):
            raise RunnerError("M4C_DESIGNATION_INVALID")
        attempt_id = attempt["attempt_id"]
        if attempt_id in ids:
            raise RunnerError("M4C_DESIGNATION_INVALID")
        ids.add(attempt_id)
        key = (attempt["test_id"], attempt["variant"])
        if key not in CATALOG:
            raise RunnerError("M4C_EXTRA_VARIANT")
        card_path = (public_run / attempt["card"]).resolve()
        if not _under(card_path, public_run):
            raise RunnerError("M4C_DESIGNATION_INVALID")
        card = _read_json(card_path)
        _privacy_scan(card)
        if (card.get("attempt_id") != attempt_id
                or card.get("designated") != attempt["designated"]
                or card.get("superseded_by") != attempt["superseded_by"]):
            raise RunnerError("M4C_DESIGNATION_INVALID")
        if attempt["designated"]:
            if key in active:
                raise RunnerError("M4C_DUPLICATE_DESIGNATION")
            active[key] = card
        elif type(attempt["superseded_by"]) is not str:
            raise RunnerError("M4C_SUPERSESSION_INVALID")
    if set(active) != set(CATALOG):
        raise RunnerError("M4C_CATALOG_INCOMPLETE")
    by_id = {attempt["attempt_id"]: attempt for attempt in attempts}
    for attempt in attempts:
        seen: set[str] = set()
        current = attempt
        while not current["designated"]:
            current_id = current["attempt_id"]
            target_id = current["superseded_by"]
            if current_id in seen or target_id not in by_id:
                raise RunnerError("M4C_SUPERSESSION_INVALID")
            seen.add(current_id)
            target = by_id[target_id]
            if (target["test_id"], target["variant"]) != (
                attempt["test_id"], attempt["variant"]
            ):
                raise RunnerError("M4C_SUPERSESSION_INVALID")
            current = target
    for card in active.values():
        if card["script_status"] != "Pass":
            raise RunnerError("M4C_DESIGNATED_RESULT_NOT_PASS")
    final = {
        "schema_version": 1, "pv_run_id": args.pv_run_id, "pv_status": "Pass",
        "designated_count": len(active),
        "attempt_count": len(attempts),
        "finalized_at": datetime.now(UTC).isoformat(),
    }
    _write_json(public_run / "final.json", final)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--pv-run-id", required=True)
    init.add_argument("--public-root", required=True, type=Path)
    init.add_argument("--private-root", required=True, type=Path)
    run = commands.add_parser("run")
    run.add_argument("--test-id", required=True)
    run.add_argument("--variant", required=True)
    run.add_argument("--pv-run-id", required=True)
    run.add_argument("--sub-run-id", required=True)
    run.add_argument("--public-partition", required=True, type=Path)
    run.add_argument("--private-partition", required=True, type=Path)
    run.add_argument("--config", required=True, type=Path)
    run.add_argument("--fresh-setup", action="store_true")
    run.add_argument("--utterance")
    run.add_argument("--utterance-1")
    run.add_argument("--utterance-2")
    finalize = commands.add_parser("finalize")
    finalize.add_argument("--pv-run-id", required=True)
    finalize.add_argument("--public-root", required=True, type=Path)
    finalize.add_argument("--private-root", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return {"init": _init, "run": _run, "finalize": _finalize}[args.command](args)
    except (RunnerError, OSError, subprocess.SubprocessError) as error:
        sys.stderr.write(f"{type(error).__name__}: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
