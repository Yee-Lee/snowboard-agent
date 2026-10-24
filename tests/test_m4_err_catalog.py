"""Executable row-to-node gate for the required M4-ERR portable matrix."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.candidate_gate import GateFailure, m4b_junit_audit


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "tests/m4_err_required_rows.json"
REQUIRED_ROWS = frozenset({
    *(f"M4-ERR-PU-007:{row}" for row in (
        "AUDIO", "ASR", "LLM", "TTS", "INPUT", "INTERNAL", "UNKNOWN",
        "SHARED-REFERENCE",
    )),
    *(f"M4-ERR-PU-008:{row}" for row in (
        "CONFIG-EXIT-2", "STARTUP-EXIT-3", "RECOVERY-EXIT-4", "BUS-EXIT-4",
        "NORMAL-STOP-CONTINUES", "SHUTDOWN-PROOF-NONZERO",
        "FATAL-NO-DOUBLE-CYCLE", "STARTUP-ROLLBACK-SINGLE-ROOT",
    )),
    *(f"M4-ERR-PU-009:{row}" for row in (
        "TRANSCRIPT", "PROMPT", "PCM", "PAYLOAD", "FILESYSTEM", "NEWLINE",
    )),
    "M4-ERR-PI-004:RECOVERY-SUCCESS",
    "M4-ERR-PI-004:RECOVERY-FAILURE",
    *(f"M4-ERR-PI-005:ASR-{number}" for number in range(1, 12)),
    *(f"M4-ERR-PI-006:LLM-{number}" for number in range(1, 8)),
    "M4-ERR-PI-006:R1-R2-PROOF",
    "M4-ERR-PI-006:BROAD-CATCH-CAUSE",
    "M4-ERR-PI-006:PLANNED-RECYCLE-AUTH",
    *(f"M4-ERR-PI-008:BTN-{number}" for number in range(1, 6)),
    *(f"M4-ERR-PI-009:{row}" for row in (
        "INJECT-RUNTIME-FAILURE", "SINGLE-DIAGNOSTIC", "ATOMIC-DISABLE",
        "NO-SELF-RENDER", "STATIC-CAPABILITY", "VOICE-INDEPENDENT",
        "CALLER-HINT-WARNING-DROP",
    )),
})


class CatalogError(RuntimeError):
    pass


def _load_catalog(path: Path = CATALOG) -> dict[str, str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CatalogError("M4_ERR_CATALOG_INVALID") from error
    if type(value) is not dict or not value:
        raise CatalogError("M4_ERR_CATALOG_INVALID")
    if any(
        type(row) is not str or not row.startswith("M4-ERR-")
        or type(node) is not str or not node.startswith("tests/") or "::" not in node
        for row, node in value.items()
    ):
        raise CatalogError("M4_ERR_CATALOG_INVALID")
    nodes = list(value.values())
    if len(nodes) != len(set(nodes)):
        raise CatalogError("M4_ERR_CATALOG_DUPLICATE_NODE")
    rows = set(value)
    if rows != REQUIRED_ROWS:
        missing = sorted(REQUIRED_ROWS - rows)
        unexpected = sorted(rows - REQUIRED_ROWS)
        raise CatalogError(
            f"M4_ERR_CATALOG_ROW_SET_MISMATCH:missing={missing}:unexpected={unexpected}"
        )
    return value


def _audit_collection(selected: list[str], collected: list[str]) -> None:
    if (
        len(collected) != len(set(collected))
        or set(collected) != set(selected)
        or len(collected) != len(selected)
    ):
        raise CatalogError("M4_ERR_CATALOG_DESELECTED_OR_DUPLICATE")


def _audit_execution(junit: bytes, nodes: list[str], stdout: str) -> None:
    try:
        m4b_junit_audit(junit, nodes)
    except GateFailure as error:
        raise CatalogError("M4_ERR_CATALOG_EXECUTION_NOT_PASS") from error
    lowered = stdout.lower()
    if any(token in lowered for token in (" xfailed", " xpassed", " deselected")):
        raise CatalogError("M4_ERR_CATALOG_EXECUTION_NOT_PASS")


def test_m4_err_required_row_catalog_executes_exactly_once(tmp_path: Path) -> None:
    catalog = _load_catalog()
    selected = list(catalog.values())
    environment = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "src"),
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    base = [
        sys.executable, "-m", "pytest", "-p", "pytest_asyncio.plugin",
        "-o", "addopts=", "--strict-markers", "-q",
    ]
    collection = subprocess.run(
        [*base, "--collect-only", *selected], cwd=ROOT, env=environment,
        capture_output=True, text=True, timeout=120,
    )
    assert collection.returncode == 0, collection.stdout + collection.stderr
    nodes = [
        line.strip() for line in collection.stdout.splitlines()
        if line.startswith("tests/") and "::" in line
    ]
    _audit_collection(selected, nodes)
    junit = tmp_path / "m4-err-required-rows.xml"
    execution = subprocess.run(
        [*base, f"--junit-xml={junit}", *selected], cwd=ROOT, env=environment,
        capture_output=True, text=True, timeout=180,
    )
    assert execution.returncode == 0, execution.stdout + execution.stderr
    _audit_execution(junit.read_bytes(), nodes, execution.stdout)


def test_m4_err_catalog_negative_missing_and_duplicate(tmp_path: Path) -> None:
    original = _load_catalog()
    missing = dict(original)
    missing.pop("M4-ERR-PI-005:ASR-11")
    path = tmp_path / "missing.json"
    path.write_text(json.dumps(missing), encoding="utf-8")
    with pytest.raises(CatalogError, match="ROW_SET_MISMATCH"):
        _load_catalog(path)

    substituted = dict(original)
    substituted["M4-ERR-PI-005:ASR-12"] = substituted.pop("M4-ERR-PI-005:ASR-11")
    path.write_text(json.dumps(substituted), encoding="utf-8")
    with pytest.raises(CatalogError, match="ROW_SET_MISMATCH"):
        _load_catalog(path)

    duplicate = dict(original)
    duplicate["M4-ERR-PI-005:ASR-11"] = duplicate["M4-ERR-PI-005:ASR-10"]
    path.write_text(json.dumps(duplicate), encoding="utf-8")
    with pytest.raises(CatalogError, match="DUPLICATE_NODE"):
        _load_catalog(path)


def test_m4_err_catalog_negative_deselected_skip_xfail_xpass() -> None:
    with pytest.raises(CatalogError, match="DESELECTED"):
        _audit_collection(["tests/a.py::test_a", "tests/b.py::test_b"], ["tests/a.py::test_a"])
    skipped = (
        b'<testsuites><testsuite><testcase classname="tests.a" name="test_a">'
        b'<skipped/></testcase></testsuite></testsuites>'
    )
    with pytest.raises(CatalogError, match="NOT_PASS"):
        _audit_execution(skipped, ["tests/a.py::test_a"], "1 skipped")
    passed = b'<testsuites><testsuite><testcase classname="tests.a" name="test_a"/></testsuite></testsuites>'
    for outcome in ("1 xfailed", "1 xpassed", "1 deselected"):
        with pytest.raises(CatalogError, match="NOT_PASS"):
            _audit_execution(passed, ["tests/a.py::test_a"], outcome)
