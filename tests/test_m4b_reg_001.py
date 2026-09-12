"""M4B-REG-001: actual retained regression execution and anti-weakening audits."""
from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.candidate_gate import (GateFailure, m4b_catalog_paths, m4b_collection_audit,
    m4b_junit_audit, m4b_source_violations)
from tests.test_m4b_foundation import _invalid_llm_response_constructor_lines

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs/test_spec/baselines/m4b_foundation_node_ids.txt"
STARTING_SHA = "54c506713082b1ea95cfa331f08b7124dcfa0316"
BASELINE_FILES = sorted({node.split("::")[0] for node in BASELINE.read_text().splitlines()})
SHARED_FILES = ("tests/test_config.py", "tests/test_resource_manager.py", "tests/test_m3_composition.py",
    "tests/test_m3_audo_001_002_003_004_005_006_007.py", "tests/test_m3_aud_001_002_003_004.py")
M4A_FILES = ("tests/test_m4a_ipc_001.py", "tests/test_m4a_asr_003.py",
             "tests/test_m4a_tts_002.py", "tests/test_m4a_priv_001.py")


def _pytest(tmp_path, files, name):
    command = [sys.executable, "-m", "pytest", "-p", "pytest_asyncio.plugin", "-p", "pytest_timeout",
        "-o", "addopts=", "--strict-markers", "--timeout=60", "-q"]
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src"),
                   "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    collection = subprocess.run([*command, "--collect-only", *files], cwd=ROOT,
        env=environment, capture_output=True, text=True, timeout=90)
    assert collection.returncode == 0, collection.stdout + collection.stderr
    nodes = [line.strip() for line in collection.stdout.splitlines() if line.startswith("tests/") and "::" in line]
    assert nodes and len(nodes) == len(set(nodes))
    result = subprocess.run([*command, f"--junit-xml={tmp_path / (name + '.xml')}", *files],
        cwd=ROOT, env=environment, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "xfailed" not in result.stdout and "xpassed" not in result.stdout
    counts = m4b_junit_audit((tmp_path / (name + ".xml")).read_bytes(), nodes)
    return nodes, counts


def test_G01_all_constructor_forms_and_affected_test_controls_are_audited(request):
    violations = []
    for path in sorted((*ROOT.joinpath("src").rglob("*.py"), *ROOT.joinpath("tests").rglob("*.py"))):
        source = path.read_text(encoding="utf-8")
        violations.extend((str(path.relative_to(ROOT)), line, "CONSTRUCTOR")
                          for line in _invalid_llm_response_constructor_lines(source))
    affected = {ROOT / path for path in BASELINE_FILES} | set(ROOT.joinpath("tests").glob("test_m4b*.py"))
    for path in sorted(affected):
        violations.extend((str(path.relative_to(ROOT)), line, reason)
                          for line, reason in m4b_source_violations(path.read_text(encoding="utf-8")))
    assert violations == []
    for item in request.session.items:
        if Path(item.path) in affected:
            assert not {"skip", "skipif", "xfail", "rpi"} & {mark.name for mark in item.iter_markers()}


@pytest.mark.parametrize("source", [
    "import pytest as p\np.skip('x')", "from pytest import xfail as x\nx('x')",
    "import pytest\ns = pytest.mark.skipif\ns(True)",
    "from pytest import mark as m\na=m.xfail\nb=a\nb(reason='x')",
    "def test_fake():\n    assert 1 == 1", "def test_fake():\n    assert False",
])
def test_G01_guard_rejects_aliases_and_constant_only_assertions(source):
    assert m4b_source_violations(source)


def test_G02_exact_99_nodes_execute_with_strict_zero_skip_junit(tmp_path, record_property):
    nodes, counts = _pytest(tmp_path, BASELINE_FILES, "foundation99")
    audit = m4b_collection_audit(BASELINE.read_bytes(), nodes)
    assert counts["passed"] == 99
    for name, value in audit.items():
        record_property(name, value)


def test_G02_audit_rejects_missing_duplicates_unsorted_and_skipped_evidence():
    nodes = BASELINE.read_text().splitlines()
    for baseline, collected in ((BASELINE.read_bytes(), nodes[:-1]),
            (BASELINE.read_bytes(), nodes + nodes[:1]),
            (("\n".join(reversed(nodes)) + "\n").encode(), nodes)):
        with pytest.raises(GateFailure):
            m4b_collection_audit(baseline, collected)
    with pytest.raises(GateFailure, match="NOT_PASS"):
        m4b_junit_audit(b'<testsuites><testsuite><testcase classname="tests.x" name="y"><skipped/></testcase></testsuite></testsuites>',
                       ["tests/x.py::y"])


def test_G03_focused_foundation_implementation_executes_separately(tmp_path):
    nodes, counts = _pytest(tmp_path, ["tests/test_m4b_foundation.py"], "focused")
    assert counts["passed"] == len(nodes) and counts["passed"] > 0
    assert all(node.startswith("tests/test_m4b_foundation.py::") for node in nodes)


def test_G04_changed_shared_config_composition_and_rm_regression(tmp_path, record_property):
    nodes, counts = _pytest(tmp_path, SHARED_FILES, "shared")
    assert counts["passed"] == len(nodes)
    record_property("selected_files", ",".join(SHARED_FILES))
    record_property("selection_reason", "Changed config/composition and shared RM lifecycle dependencies")


def test_G05_affected_m4a_portable_boundaries(tmp_path, record_property):
    nodes, counts = _pytest(tmp_path, M4A_FILES, "m4a")
    assert counts["passed"] == len(nodes)
    record_property("selected_files", ",".join(M4A_FILES))
    record_property("selection_reason", "Shared IPC/process cleanup, ASR/TTS terminal and privacy boundaries")


def _retained_definition_inventory(source):
    tree = ast.parse(source)
    # Protect stimuli, fixtures, helper classes and decorators as well as asserts.
    # A weaker input fixture with an unchanged assert is still a weakened test.
    return {node.name: ast.dump(node, include_attributes=False)
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def test_G06_immutable_test_names_and_assertions_match_predevelopment_sha():
    retained = sorted(set(BASELINE_FILES) | set(SHARED_FILES) | set(M4A_FILES)
                      | {"tests/test_m4b_foundation.py"})
    for relative in retained:
        before = subprocess.run(["git", "show", f"{STARTING_SHA}:{relative}"], cwd=ROOT,
            capture_output=True, text=True, timeout=10)
        assert before.returncode == 0, "Exact pre-development source is unavailable"
        old = _retained_definition_inventory(before.stdout)
        current = _retained_definition_inventory((ROOT / relative).read_text(encoding="utf-8"))
        assert old.keys() <= current.keys(), relative
        assert all(current[name] == assertions for name, assertions in old.items()), relative


def test_G06_guard_detects_weakened_stimulus_with_unchanged_assertion():
    original = "def test_example():\n    actual = product('boundary')\n    assert actual\n"
    weakened = "def test_example():\n    actual = product('trivial')\n    assert actual\n"
    assert _retained_definition_inventory(original) != _retained_definition_inventory(weakened)


def test_G06_complete_catalog_never_silently_drops_unimplemented_paths():
    selectors = m4b_catalog_paths(ROOT)
    required = {f"tests/test_m4b_{name}_001.py" for name in
        ("norm", "prompt", "sem", "s2", "adm", "prefill", "outcome", "conv", "mem", "rec", "wire", "priv", "reg")}
    assert required <= set(selectors)


def test_G06_missing_catalog_path_is_incomplete(tmp_path):
    directory = tmp_path / "tests"
    directory.mkdir()
    (directory / "m4b_portable_suite.txt").write_text("tests/not_implemented.py\n")
    with pytest.raises(GateFailure, match="INCOMPLETE"):
        m4b_catalog_paths(tmp_path)
