"""Strict M3 Raspberry Pi acceptance-card and evidence helpers."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any, Iterable

from sbd.core.config import load_config


_ROOT = Path(__file__).resolve().parents[1]
_CARD_STARTED: dict[str, str] = {}
_TESTED_PATHS = (
    "src", "tests", "scripts/record_m3_observation.py",
    "pyproject.toml", "requirements",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=_ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()


def candidate_identity() -> dict[str, str]:
    revision = _git("rev-parse", "HEAD")
    expected = os.environ.get("SBD_M3_CANDIDATE_SHA")
    assert expected and len(expected) == 40, (
        "SBD_M3_CANDIDATE_SHA must be the approved full candidate SHA"
    )
    assert revision == expected, (
        f"checked-out HEAD {revision} does not match candidate {expected}"
    )
    dirty = _git(
        "status", "--porcelain", "--untracked-files=all", "--", *_TESTED_PATHS,
    )
    assert not dirty, "candidate source/test worktree is dirty:\n" + dirty
    return {
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "implementation_sha": revision,
    }


def rpi_config(test_id: str):
    candidate_identity()
    _CARD_STARTED[test_id] = _utc_now()
    raw = os.environ.get("SBD_M3_RPI_CONFIG")
    if not raw:
        raise AssertionError("SBD_M3_RPI_CONFIG must name the sanitized Pi-local config")
    path = Path(raw)
    if not path.is_file():
        raise AssertionError("SBD_M3_RPI_CONFIG does not name a readable local config")
    return load_config(local_path=path, environ={})


def interaction_timeout() -> float:
    value = float(os.environ.get("SBD_M3_INTERACTION_TIMEOUT_SECONDS", "30"))
    if value <= 0 or value > 300:
        raise AssertionError("SBD_M3_INTERACTION_TIMEOUT_SECONDS must be in 0..300")
    return value


def require_manual(test_id: str, required_checks: Iterable[str]) -> dict[str, Any]:
    raw = os.environ.get("SBD_M3_MANUAL_DIR")
    assert raw, "SBD_M3_MANUAL_DIR must point to current-run observation JSON files"
    path = Path(raw) / f"{test_id}.json"
    deadline = monotonic() + interaction_timeout()
    result: dict[str, Any] | None = None
    while monotonic() < deadline:
        if path.is_file():
            try:
                candidate = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                candidate = None
            if (
                isinstance(candidate, dict)
                and isinstance(candidate.get("observed_at_utc"), str)
                and candidate["observed_at_utc"] >= _CARD_STARTED[test_id]
            ):
                result = candidate
                break
        time.sleep(0.2)
    assert result is not None, f"current-run manual observation is missing or stale: {path}"
    assert result.get("test_id") == test_id
    assert result.get("operator"), "manual observation must identify the operator"
    observed_at = result.get("observed_at_utc")
    assert isinstance(observed_at, str) and observed_at >= _CARD_STARTED[test_id]
    checks = result.get("checks")
    assert isinstance(checks, dict)
    missing = set(required_checks) - checks.keys()
    assert not missing, "manual checklist is missing: " + ", ".join(sorted(missing))
    failed = [name for name in required_checks if checks[name] is not True]
    assert not failed, "manual checks failed: " + ", ".join(failed)
    assert isinstance(result.get("media_metadata"), list), (
        "manual observation must include a media_metadata list (empty is allowed)"
    )
    return result


def _hardware_manifest() -> dict[str, Any]:
    raw = os.environ.get("SBD_M3_HARDWARE_MANIFEST")
    assert raw, "SBD_M3_HARDWARE_MANIFEST must identify hardware and wiring JSON"
    path = Path(raw)
    assert path.is_file(), f"hardware manifest is missing: {path}"
    value = json.loads(path.read_text())
    for field in ("pi", "peripherals", "wiring", "operator"):
        assert value.get(field), f"hardware manifest field is required: {field}"
    return value


def _package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in ("pyalsaaudio", "samplerate", "numpy", "picamera2", "gpiod", "Pillow"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def _artifact_identity(config) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = [
        {"package": name, "version": version}
        for name, version in _package_versions().items()
    ]
    path = config.core.display.native_library_path
    if path is not None and path.is_file():
        artifacts.append({
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "abi": config.core.display.native_abi_version,
            "license": "delivery notice / accepted Display POC",
        })
    return artifacts


def _evidence_root() -> Path:
    raw = os.environ.get("SBD_M3_EVIDENCE_DIR")
    if not raw:
        raise AssertionError("SBD_M3_EVIDENCE_DIR must point to the delivery bundle root")
    root = Path(raw)
    if not root.is_dir():
        raise AssertionError("SBD_M3_EVIDENCE_DIR must already exist")
    for name in ("cards", "checksums", "environment", "logs", "media-metadata", "results"):
        (root / name).mkdir(exist_ok=True)
    return root


def record_result(
    test_id: str, *, expected: str, actual: str,
    fixture: dict[str, Any] | None = None, manual: dict[str, Any] | None = None,
    **metrics: Any,
) -> None:
    identity = candidate_identity()
    config_path = Path(os.environ["SBD_M3_RPI_CONFIG"])
    config = load_config(local_path=config_path, environ={})
    hardware = _hardware_manifest()
    root = _evidence_root()
    finished = _utc_now()
    command = shlex.join([sys.executable, "-m", "pytest", *sys.argv[1:]])
    relative_result = f"results/{test_id}.json"
    relative_card = f"cards/{test_id}.md"
    fixture_identity = dict(fixture or {"name": "none", "sha256": "not-applicable"})
    fixture_sha = fixture_identity.get("sha256")
    if fixture_sha != "not-applicable" and (
        not isinstance(fixture_sha, str)
        or len(fixture_sha) != 64
        or any(character not in "0123456789abcdef" for character in fixture_sha.lower())
    ):
        fixture_identity["source_identity"] = fixture_sha
        fixture_identity["sha256"] = hashlib.sha256(
            json.dumps(fixture_identity, sort_keys=True).encode()
        ).hexdigest()
    payload = {
        "test_id": test_id,
        "status": "Pass",
        "product_revision": identity,
        "hardware_and_wiring": hardware,
        "artifacts": _artifact_identity(config),
        "config": {
            "path": str(config_path),
            "sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        },
        "fixture": fixture_identity,
        "reproduction": {"command": command, "operation": metrics.pop("operation", "automated")},
        "expected": expected,
        "actual": actual,
        "started_utc": _CARD_STARTED[test_id],
        "finished_utc": finished,
        "exit_code": 0,
        "artifacts_index": {
            "result": relative_result,
            "card": relative_card,
            "logs": "logs/",
            "media_metadata": "media-metadata/",
        },
        "manual_observation": manual,
        "metrics": metrics,
        "system": {
            "machine": platform.machine(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
    }
    (root / relative_result).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    (root / relative_card).write_text(
        "\n".join((
            f"# {test_id} Hardware Test Card",
            "",
            f"- Status: Pass",
            f"- Product revision: {identity['branch']} / {identity['implementation_sha']}",
            f"- Hardware and wiring: hardware_and_wiring in `{relative_result}`",
            f"- Artifact / config / fixture identity: `{relative_result}`",
            f"- Command: `{command}`",
            f"- Expected: {expected}",
            f"- Actual: {actual}",
            f"- Started / finished (UTC): {_CARD_STARTED[test_id]} / {finished}",
            "- Exit code: 0 (written only after all card assertions pass)",
            f"- Result / log / media index: `{relative_result}`, `logs/`, `media-metadata/`",
            "",
        ))
    )
    system = {**payload["system"], **identity}
    (root / "environment/system.json").write_text(json.dumps(system, indent=2, sort_keys=True) + "\n")
    (root / "environment/hardware.json").write_text(json.dumps(hardware, indent=2, sort_keys=True) + "\n")
    (root / "environment/packages.json").write_text(json.dumps(_package_versions(), indent=2, sort_keys=True) + "\n")
    (root / "environment/devices.txt").write_text(json.dumps(hardware, indent=2, sort_keys=True) + "\n")
    (root / "environment/packages.txt").write_text(
        "\n".join(f"{name}=={version}" for name, version in sorted(_package_versions().items())) + "\n"
    )
    results = []
    checksum_lines = [f"{payload['config']['sha256']}  {config_path}"]
    for result_path in sorted((root / "results").glob("M3-*.json")):
        item = json.loads(result_path.read_text())
        if item.get("product_revision") != identity or item.get("status") != "Pass":
            continue
        results.append({"test_id": item["test_id"], "status": item["status"], "path": str(result_path.relative_to(root))})
        fixture_value = item.get("fixture", {})
        if fixture_value.get("sha256"):
            checksum_lines.append(f"{fixture_value['sha256']}  fixture:{item['test_id']}:{fixture_value.get('name', '')}")
        for artifact in item.get("artifacts", []):
            if artifact.get("sha256") and artifact.get("path"):
                checksum_lines.append(f"{artifact['sha256']}  {artifact['path']}")
    (root / "manifest.json").write_text(json.dumps({
        "candidate": identity,
        "generated_at_utc": finished,
        "cards": results,
    }, indent=2, sort_keys=True) + "\n")
    (root / "checksums/SHA256SUMS").write_text("\n".join(dict.fromkeys(checksum_lines)) + "\n")
    (root / "logs/README.md").write_text(
        "# Logs\n\nPytest log and JUnit paths are supplied by the M3 runbook. "
        "Every result card records the exact command.\n"
    )
    media = [
        {"test_id": item["test_id"], "media_metadata": item["manual_observation"]["media_metadata"]}
        for item in (
            json.loads(path.read_text()) for path in sorted((root / "results").glob("M3-*.json"))
        )
        if item.get("product_revision") == identity and item.get("manual_observation")
    ]
    (root / "media-metadata/index.json").write_text(json.dumps(media, indent=2, sort_keys=True) + "\n")


def validate_evidence_bundle(expected_ids: Iterable[str]) -> None:
    root = _evidence_root()
    identity = candidate_identity()
    for test_id in expected_ids:
        result_path = root / "results" / f"{test_id}.json"
        card_path = root / "cards" / f"{test_id}.md"
        assert result_path.is_file(), f"missing evidence result: {test_id}"
        assert card_path.is_file(), f"missing evidence card: {test_id}"
        result = json.loads(result_path.read_text())
        assert result["test_id"] == test_id and result["status"] == "Pass"
        assert result["product_revision"] == identity
        for field in (
            "hardware_and_wiring", "artifacts", "config", "fixture", "reproduction",
            "expected", "actual", "started_utc", "finished_utc", "exit_code",
            "artifacts_index", "system",
        ):
            assert result.get(field) is not None, f"{test_id} missing {field}"


def elapsed_samples(callback, count: int) -> list[float]:
    samples: list[float] = []
    for _ in range(count):
        started = monotonic()
        callback()
        samples.append(monotonic() - started)
    return samples
