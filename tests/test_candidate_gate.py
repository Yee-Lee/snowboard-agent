from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.candidate_gate import (
    GateFailure,
    M4B_CARD_REQUIRED,
    M4B_CANONICAL_SUITE,
    M4B_PORTABLE_IDS,
    Repository,
    _network_attempt_count,
    _m4b_foundation_evidence,
    _m4b_profile_identity,
    _m4b_source_audit,
    _m4b_test_id_evidence,
    _validate_m4b_card,
    m4b_catalog_paths,
    m4b_collection_audit,
    portable,
    prepare_new_output,
    validate_m4b_product_preflight,
)


REPOSITORY = Path(__file__).resolve().parents[1]
RUNNER = REPOSITORY / "scripts" / "candidate_gate.py"
CURRENT_MINOR = f"{sys.version_info.major}.{sys.version_info.minor}"
SUPPORTED_MINORS = ("3.11", "3.12", "3.13")


def command(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--repo", str(root), *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def candidate_repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "candidate"
    root.mkdir()
    write(root / ".gitignore", "__pycache__/\n*.py[cod]\n")
    write(
        root / "pyproject.toml",
        "[project]\nname='gate-fixture'\nversion='0.0.0'\n\n"
        "[tool.pytest.ini_options]\naddopts='-q'\nmarkers=['rpi: target-only test']\n",
    )
    write(root / "src" / "fixture.py", "VALUE = 1\n")
    write(
        root / "tests" / "test_scope.py",
        "import pytest\n\ndef test_portable():\n    assert True\n\n"
        "@pytest.mark.rpi\ndef test_rpi_must_not_run_portably():\n    raise AssertionError('rpi collected')\n",
    )
    write(
        root / "tests" / "test_timeout.py",
        "import time\n\ndef test_hang():\n    time.sleep(10)\n",
    )
    write(
        root / "tests" / "test_timeout_descendant.py",
        "import pathlib,subprocess,sys,time\n\n"
        "def test_hang_with_independent_process_group():\n"
        "    target=pathlib.Path('local-inputs/descendant.pid')\n"
        "    target.parent.mkdir(parents=True,exist_ok=True)\n"
        "    child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)\n"
        "    target.write_text(str(child.pid))\n"
        "    time.sleep(30)\n",
    )
    write(
        root / "tests" / "test_xpass.py",
        "import pytest\n\n@pytest.mark.xfail\ndef test_unexpected_pass():\n    assert object() is not None\n",
    )
    write(
        root / "tests" / "test_target.py",
        "import json,os,pathlib,pytest\n\n"
        "@pytest.mark.rpi\ndef test_target():\n"
        "    if 'SBD_M4A_CARD_ROOT' not in os.environ:\n"
        "        assert 'SBD_M4A_CANDIDATE_SHA' not in os.environ\n"
        "        return\n"
        "    root=pathlib.Path(os.environ['SBD_M4A_CARD_ROOT'])\n"
        "    sha=os.environ['SBD_M4A_CANDIDATE_SHA']\n"
        "    assert os.environ['SBD_M4A_ACCEPTANCE_RUN_ID']=='accept-002'\n"
        "    assert os.environ['OPENBLAS_NUM_THREADS']=='1'\n"
        "    (root/'M4A-TARGET-001.json').write_text(json.dumps({"
        "'candidate_sha':sha,'test_id':'M4A-TARGET-001','metric':1}))\n",
    )
    write(
        root / "tests" / "milestones" / "test_m4_local_voice.py",
        "import json,os,pathlib,pytest,socket\n\n"
        "@pytest.mark.rpi\ndef test_target():\n"
        "    if os.environ.get('SBD_TEST_NETWORK_ATTEMPT'):\n"
        "        socket.socket(socket.AF_INET,socket.SOCK_STREAM).close()\n"
        "    root=pathlib.Path(os.environ['SBD_M4A_CARD_ROOT'])\n"
        "    sha=os.environ['SBD_M4A_CANDIDATE_SHA']\n"
        "    (root/'M4A-OFF-001.json').write_text(json.dumps({"
        "'candidate_sha':sha,'test_id':'M4A-OFF-001','network_attempts':0}))\n",
    )
    write(root / "tests" / "portable-suite.txt", "tests/test_scope.py\n")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "gate@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Gate Fixture"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
    return root, sha


def portable_args(sha: str, run_id: str, output: Path, suite: str = "tests/test_scope.py") -> tuple[str, ...]:
    return (
        "portable",
        "--candidate-sha",
        sha,
        "--run-id",
        run_id,
        "--python",
        CURRENT_MINOR,
        "--suite",
        suite,
        "--timeout-seconds",
        "3",
        "--output",
        str(output),
    )


def enable_m4b_candidate(root: Path) -> str:
    profile = {"profile_id": "core-m4b-cognition-001"}
    encoded = json.dumps(profile, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode()
    profile["profile_sha256"] = hashlib.sha256(encoded).hexdigest()
    write(root / "requirements" / "m4b" / "product-profile.json",
          json.dumps(profile, sort_keys=True))
    selectors = list(M4B_PORTABLE_IDS.values())
    write(root / M4B_CANONICAL_SUITE, "\n".join(selectors) + "\n")
    write(root / "tests" / "test_foundation_stub.py", "VALUE = 1\n")
    baseline = [f"tests/test_foundation_stub.py::test_{number:03}" for number in range(99)]
    baseline_path = root / "docs" / "test_spec" / "baselines" / "m4b_foundation_node_ids.txt"
    write(baseline_path, "\n".join(baseline) + "\n")
    baseline_evidence = m4b_collection_audit(baseline_path.read_bytes(), baseline)
    for path in selectors:
        name = ("test_G02_exact_99_nodes_fixture" if path.endswith("test_m4b_reg_001.py")
                else "test_contract")
        if path.endswith("test_m4b_reg_001.py"):
            write(root / path,
                  "VALUE = 1\n\n"
                  f"def {name}(record_property):\n"
                  f"    evidence = {baseline_evidence!r}\n"
                  "    for key, value in evidence.items():\n"
                  "        record_property(key, value)\n"
                  "    assert VALUE == 1\n")
        else:
            write(root / path, f"VALUE = 1\n\ndef {name}():\n    assert VALUE == 1\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "enable m4b fixture"], cwd=root, check=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True,
                          capture_output=True, check=True).stdout.strip()


def write_m4b_matrix_inputs(root: Path, sha: str, run_id: str) -> Path:
    profile_id, profile_sha256 = _m4b_profile_identity(root)
    targets = m4b_catalog_paths(root)
    catalog_sha256 = hashlib.sha256((root / M4B_CANONICAL_SUITE).read_bytes()).hexdigest()
    nodes = []
    for path in targets:
        name = ("test_G02_exact_99_nodes_fixture" if path.endswith("test_m4b_reg_001.py")
                else "test_contract")
        nodes.append(f"{path}::{name}")
    baseline = (root / "docs/test_spec/baselines/m4b_foundation_node_ids.txt").read_bytes()
    baseline_evidence = m4b_collection_audit(baseline, baseline.decode().splitlines())
    matrix_root = root / "evidence" / "portable" / run_id
    for minor in SUPPORTED_MINORS:
        directory = matrix_root / f"python-{minor}"
        directory.mkdir(parents=True)
        collection = directory / "collection-node-ids.txt"
        collection.write_text("\n".join(nodes) + "\n", encoding="utf-8")
        suite = ET.Element("testsuite", tests=str(len(nodes)), failures="0", errors="0", skipped="0")
        for node in nodes:
            path, name = node.split("::")
            case = ET.SubElement(suite, "testcase", classname=path.removesuffix(".py").replace("/", "."), name=name)
            if name.startswith("test_G02_exact_99_nodes"):
                properties = ET.SubElement(case, "properties")
                for key, value in baseline_evidence.items():
                    ET.SubElement(properties, "property", name=key, value=str(value))
        junit = directory / "junit.xml"
        ET.ElementTree(suite).write(junit, encoding="utf-8", xml_declaration=True)
        for relative in ("logs/collection.stdout.log", "logs/collection.stderr.log",
                         "logs/suite.stdout.log", "logs/suite.stderr.log"):
            write(directory / relative, "fixture\n")
        junit_sha256 = hashlib.sha256(junit.read_bytes()).hexdigest()
        result = {
            "branch": "candidate/test", "candidate_sha": sha,
            "case_id": f"PY{minor.replace('.', '')}",
            "catalog_paths": targets, "catalog_sha256": catalog_sha256,
            "collection_count": len(nodes), "collection_locator": "collection-node-ids.txt",
            "collection_sha256": hashlib.sha256(collection.read_bytes()).hexdigest(),
            "counts": {"passed": len(nodes), "failed": 0, "errors": 0, "skipped": 0,
                       "xfailed": 0, "xpassed": 0},
            "end_monotonic_ns": 2, "evidence_sha256": junit_sha256, "exit_code": 0,
            "junit_locator": "junit.xml", "junit_sha256": junit_sha256,
            "matrix": "portable", "mode": "portable",
            "platform": "Linux-fixture", "platform_identity": {"system": "Linux", "machine": "x86_64"},
            "profile_id": profile_id, "profile_sha256": profile_sha256,
            "python": {"implementation": "CPython", "version": f"{minor}.9"},
            "python_minor": minor,
            "raw_logs": ["logs/collection.stdout.log", "logs/collection.stderr.log",
                         "logs/suite.stdout.log", "logs/suite.stderr.log"],
            "run_id": run_id, "schema_version": 1,
            "source_audit_sha256": _m4b_source_audit(root, targets),
            "start_monotonic_ns": 1, "status": "Pass", "suite": M4B_CANONICAL_SUITE,
            "suite_command": [sys.executable, "-m", "pytest", "-v", "-m", "not rpi",
                              *targets, f"--junitxml={junit}"],
            "test_id": "M4B-PORTABLE-CATALOG", "test_id_evidence": _m4b_test_id_evidence(nodes),
            "timeout_seconds": 60, "baseline_evidence": baseline_evidence,
        }
        write(directory / "result.json", json.dumps(result))
        assert _m4b_foundation_evidence(root, junit) == baseline_evidence
    return matrix_root


def version_result(sha: str, run_id: str, minor: str, branch: str = "candidate/test") -> dict[str, object]:
    return {
        "branch": branch,
        "candidate_sha": sha,
        "counts": {"passed": 1, "failed": 0, "errors": 0, "skipped": 0,
                   "xfailed": 0, "xpassed": 0},
        "exit_code": 0,
        "python_minor": minor,
        "raw_logs": ["logs/suite.stdout.log", "logs/suite.stderr.log"],
        "run_id": run_id,
        "status": "Pass",
        "timeout_seconds": 60,
    }


def write_matrix_inputs(root: Path, sha: str, run_id: str, branches: tuple[str, str, str] | None = None) -> Path:
    matrix_root = root / "evidence" / "portable" / run_id
    branches = branches or ("candidate/test",) * 3
    for minor, branch in zip(SUPPORTED_MINORS, branches, strict=True):
        path = matrix_root / f"python-{minor}" / "result.json"
        write(path, json.dumps(version_result(sha, run_id, minor, branch)))
    return matrix_root


def build_matrix(root: Path, sha: str, run_id: str, matrix_root: Path) -> subprocess.CompletedProcess[str]:
    return command(
        root,
        "matrix",
        "--candidate-sha",
        sha,
        "--run-id",
        run_id,
        "--input-root",
        str(matrix_root),
        "--output",
        str(matrix_root / "matrix-index.json"),
    )


def write_preflight_inputs(root: Path) -> tuple[Path, Path, Path]:
    paths = (root / "local-inputs" / "hardware.json", root / "local-inputs" / "config.yaml", root / "local-inputs" / "artifacts.json")
    for path, content in zip(paths, ("{}\n", "mode: test\n", "{}\n"), strict=True):
        write(path, content)
    return paths


def run_preflight(root: Path, sha: str, run_id: str, matrix_root: Path, output: Path) -> subprocess.CompletedProcess[str]:
    hardware, config, artifacts = write_preflight_inputs(root)
    return command(
        root,
        "preflight",
        "--candidate-sha",
        sha,
        "--run-id",
        run_id,
        "--portable-index",
        str(matrix_root / "matrix-index.json"),
        "--runtime",
        "3.13",
        "--hardware",
        str(hardware),
        "--config",
        str(config),
        "--artifact-manifest",
        str(artifacts),
        "--output",
        str(output),
    )


def test_portable_excludes_rpi_and_records_result(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    output = root / "evidence" / "portable" / "scope-run" / f"python-{CURRENT_MINOR}"
    result = command(root, *portable_args(sha, "scope-run", output))
    assert result.returncode == 0, result.stderr
    evidence = json.loads((output / "result.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "Pass"
    assert evidence["counts"]["passed"] == 1
    assert evidence["counts"]["skipped"] == 0
    assert evidence["suite_command"][4:6] == ["-m", "not rpi"]


def test_portable_suite_manifest_expands_only_tracked_test_paths(
    candidate_repo: tuple[Path, str],
) -> None:
    root, sha = candidate_repo
    output = root / "evidence" / "portable" / "manifest-run" / f"python-{CURRENT_MINOR}"
    result = command(
        root, *portable_args(sha, "manifest-run", output, "tests/portable-suite.txt"),
    )
    assert result.returncode == 0, result.stderr
    evidence = json.loads((output / "result.json").read_text(encoding="utf-8"))
    assert "tests/test_scope.py" in evidence["suite_command"]
    assert "tests/portable-suite.txt" not in evidence["suite_command"]


def test_portable_xpass_is_fail_and_never_writes_pass_result(
    candidate_repo: tuple[Path, str],
) -> None:
    root, sha = candidate_repo
    output = root / "evidence" / "portable" / "xpass-run" / f"python-{CURRENT_MINOR}"
    result = command(root, *portable_args(sha, "xpass-run", output, "tests/test_xpass.py"))
    assert result.returncode != 0
    assert "xpassed" in result.stderr.lower()
    evidence = json.loads((output / "result.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "Fail"
    assert evidence["counts"]["xpassed"] == 1


def test_m4b_portable_rejects_external_absolute_and_arbitrary_suites(
    candidate_repo: tuple[Path, str], tmp_path: Path,
) -> None:
    root, _ = candidate_repo
    sha = enable_m4b_candidate(root)
    external = tmp_path / "trivial_probe.py"
    write(external, "def test_trivial():\n    assert object() is not None\n")
    for index, suite in enumerate((str(external), "tests", "tests/test_scope.py")):
        output = root / "evidence" / "portable" / f"bad-suite-{index}" / f"python-{CURRENT_MINOR}"
        result = command(root, *portable_args(sha, f"bad-suite-{index}", output, suite))
        assert result.returncode != 0
        assert M4B_CANONICAL_SUITE in result.stderr
        assert not (output / "junit.xml").exists()


def test_m4b_portable_executes_canonical_suite_and_writes_bound_evidence(
    candidate_repo: tuple[Path, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _ = candidate_repo
    sha = enable_m4b_candidate(root)
    output = root / "evidence" / "portable" / "canonical-run" / f"python-{CURRENT_MINOR}"
    prepare_new_output(output)
    monkeypatch.setattr("scripts.candidate_gate.platform.system", lambda: "Linux")
    monkeypatch.setattr("scripts.candidate_gate.platform.machine", lambda: "x86_64")
    portable(
        SimpleNamespace(run_id="canonical-run", suite=M4B_CANONICAL_SUITE,
                        timeout_seconds=30, python=CURRENT_MINOR),
        Repository(root=root, candidate_sha=sha, branch="candidate/test"),
        output,
    )
    evidence = json.loads((output / "result.json").read_text(encoding="utf-8"))
    assert "addopts='-q'" in (root / "pyproject.toml").read_text(encoding="utf-8")
    assert evidence["status"] == "Pass"
    assert evidence["catalog_paths"] == list(M4B_PORTABLE_IDS.values())
    assert set(evidence["test_id_evidence"]) == set(M4B_PORTABLE_IDS)
    assert evidence["baseline_evidence"]["retained_count"] == 99
    assert evidence["counts"] == {"passed": 13, "failed": 0, "errors": 0,
                                  "skipped": 0, "xfailed": 0, "xpassed": 0}
    collected = (output / "collection-node-ids.txt").read_text(encoding="utf-8").splitlines()
    assert len(collected) == 13
    assert all(node.startswith("tests/") and "::" in node for node in collected)


def test_exact_sha_rejects_before_suite(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    output = root / "evidence" / "portable" / "wrong-sha" / f"python-{CURRENT_MINOR}"
    result = command(root, *portable_args("0" * 40, "wrong-sha", output))
    assert result.returncode != 0
    assert "does not match" in result.stderr
    assert not (output / "junit.xml").exists()
    assert (output / "logs" / "portable.stderr.log").is_file()
    assert sha != "0" * 40


def test_dirty_protected_path_rejects_but_local_config_does_not(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    write(root / "config.m4.local.yaml", "local: true\n")
    clean_output = root / "evidence" / "portable" / "local-config" / f"python-{CURRENT_MINOR}"
    clean = command(root, *portable_args(sha, "local-config", clean_output))
    assert clean.returncode == 0, clean.stderr

    write(root / "src" / "fixture.py", "VALUE = 2\n")
    dirty_output = root / "evidence" / "portable" / "dirty-src" / f"python-{CURRENT_MINOR}"
    dirty = command(root, *portable_args(sha, "dirty-src", dirty_output))
    assert dirty.returncode != 0
    assert "protected candidate input is dirty" in dirty.stderr
    assert not (dirty_output / "junit.xml").exists()


def test_timeout_is_bounded_and_keeps_raw_log(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    output = root / "evidence" / "portable" / "timeout-run" / f"python-{CURRENT_MINOR}"
    args = list(portable_args(sha, "timeout-run", output, "tests/test_timeout.py"))
    args[args.index("3")] = "0.1"
    result = command(root, *args)
    assert result.returncode != 0
    assert "suite timeout" in result.stderr
    assert "TIMEOUT" in (output / "logs" / "suite.stderr.log").read_text(encoding="utf-8")


def test_timeout_terminates_independent_descendant_process_group(
    candidate_repo: tuple[Path, str],
) -> None:
    root, sha = candidate_repo
    output = root / "evidence" / "portable" / "timeout-tree" / f"python-{CURRENT_MINOR}"
    args = list(portable_args(sha, "timeout-tree", output, "tests/test_timeout_descendant.py"))
    # Leave enough time for pytest/plugin startup on loaded workstations while
    # still proving the runner's bounded process-tree timeout.
    args[args.index("3")] = "5.0"
    result = command(root, *args)
    assert result.returncode != 0
    pid = int((root / "local-inputs" / "descendant.pid").read_text())
    for _ in range(100):
        stat = Path(f"/proc/{pid}/stat")
        if not stat.exists() or stat.read_text().rsplit(")", 1)[1].split()[0] == "Z":
            break
        time.sleep(0.01)
    else:
        raise AssertionError("timed-out independent descendant remained alive")


def test_existing_run_output_is_not_overwritten(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    output = root / "evidence" / "portable" / "used-run" / f"python-{CURRENT_MINOR}"
    write(output / "sentinel.txt", "keep\n")
    result = command(root, *portable_args(sha, "used-run", output))
    assert result.returncode != 0
    assert (output / "sentinel.txt").read_text(encoding="utf-8") == "keep\n"
    assert list(output.iterdir()) == [output / "sentinel.txt"]


def test_matrix_requires_all_three_versions_and_same_sha(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    matrix_root = write_matrix_inputs(root, sha, "matrix-ok")
    passed_result = build_matrix(root, sha, "matrix-ok", matrix_root)
    assert passed_result.returncode == 0, passed_result.stderr
    index = json.loads((matrix_root / "matrix-index.json").read_text(encoding="utf-8"))
    assert set(index["results"]) == set(SUPPORTED_MINORS)

    incomplete_root = write_matrix_inputs(root, sha, "matrix-missing")
    (incomplete_root / "python-3.12" / "result.json").unlink()
    missing = build_matrix(root, sha, "matrix-missing", incomplete_root)
    assert missing.returncode != 0
    assert "3.12" in missing.stderr

    mixed_root = write_matrix_inputs(root, sha, "matrix-mixed")
    mixed_path = mixed_root / "python-3.13" / "result.json"
    mixed = json.loads(mixed_path.read_text(encoding="utf-8"))
    mixed["candidate_sha"] = "f" * 40
    mixed_path.write_text(json.dumps(mixed), encoding="utf-8")
    mixed_result = build_matrix(root, sha, "matrix-mixed", mixed_root)
    assert mixed_result.returncode != 0
    assert "mixed candidate SHA" in mixed_result.stderr


def test_m4b_matrix_requires_linux_canonical_catalog_profile_and_evidence_identity(
    candidate_repo: tuple[Path, str],
) -> None:
    root, _ = candidate_repo
    sha = enable_m4b_candidate(root)
    valid_root = write_m4b_matrix_inputs(root, sha, "m4b-valid")
    valid = build_matrix(root, sha, "m4b-valid", valid_root)
    assert valid.returncode == 0, valid.stderr

    mutations = (
        ("platform", lambda row: row["platform_identity"].update(system="Darwin")),
        ("suite", lambda row: row.update(suite="tests/test_scope.py")),
        ("catalog", lambda row: row.update(catalog_sha256="0" * 64)),
        ("profile", lambda row: row.update(profile_sha256="0" * 64)),
        ("test-id", lambda row: row["test_id_evidence"].pop("M4B-REG-001")),
        ("junit", lambda row: row.update(evidence_sha256="0" * 64)),
    )
    for name, mutate in mutations:
        run_id = f"m4b-bad-{name}"
        matrix_root = write_m4b_matrix_inputs(root, sha, run_id)
        path = matrix_root / "python-3.12" / "result.json"
        row = json.loads(path.read_text(encoding="utf-8"))
        mutate(row)
        path.write_text(json.dumps(row), encoding="utf-8")
        rejected = build_matrix(root, sha, run_id, matrix_root)
        assert rejected.returncode != 0, name
        assert not (matrix_root / "matrix-index.json").exists(), name


def test_m4b_matrix_rejects_xpass_even_when_record_claims_pass(
    candidate_repo: tuple[Path, str],
) -> None:
    root, _ = candidate_repo
    sha = enable_m4b_candidate(root)
    matrix_root = write_m4b_matrix_inputs(root, sha, "m4b-xpass")
    path = matrix_root / "python-3.11" / "result.json"
    row = json.loads(path.read_text(encoding="utf-8"))
    row["counts"]["xpassed"] = 1
    path.write_text(json.dumps(row), encoding="utf-8")
    rejected = build_matrix(root, sha, "m4b-xpass", matrix_root)
    assert rejected.returncode != 0
    assert "XPASS" in rejected.stderr


def test_branch_name_is_diagnostic_only(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    matrix_root = write_matrix_inputs(root, sha, "branch-info", ("candidate/a", "detached", "candidate/b"))
    result = build_matrix(root, sha, "branch-info", matrix_root)
    assert result.returncode == 0, result.stderr


def test_preflight_records_minimal_checksums(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    matrix_root = write_matrix_inputs(root, sha, "matrix-preflight")
    assert build_matrix(root, sha, "matrix-preflight", matrix_root).returncode == 0
    output = root / "evidence" / "acceptance" / "accept-001"
    result = run_preflight(root, sha, "accept-001", matrix_root, output)
    assert result.returncode == 0, result.stderr
    preflight = json.loads((output / "preflight.json").read_text(encoding="utf-8"))
    assert preflight["status"] == "Pass"
    assert set(preflight["checksums"]) == {"artifact_manifest", "config", "hardware"}
    for reference in preflight["checksums"].values():
        data = Path(reference["path"]).read_bytes()
        assert reference["sha256"] == hashlib.sha256(data).hexdigest()
    assert "freeze_manifest" not in preflight
    assert "portable_result_checksums" not in preflight


def test_acceptance_uses_preflight_and_cannot_be_reused(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    matrix_root = write_matrix_inputs(root, sha, "matrix-accept")
    assert build_matrix(root, sha, "matrix-accept", matrix_root).returncode == 0
    output = root / "evidence" / "acceptance" / "accept-002"
    assert run_preflight(root, sha, "accept-002", matrix_root, output).returncode == 0
    args = (
        "accept",
        "--candidate-sha",
        sha,
        "--run-id",
        "accept-002",
        "--preflight",
        str(output / "preflight.json"),
        "--suite",
        "tests/test_target.py",
        "--timeout-seconds",
        "3",
        "--output",
        str(output),
    )
    first = command(root, *args)
    assert first.returncode == 0, first.stderr
    evidence = json.loads((output / "result.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "Pass"
    assert evidence["suite_command"][4:6] == ["-m", "rpi"]
    card = json.loads((output / "cards" / "M4A-TARGET-001.json").read_text(encoding="utf-8"))
    assert card["candidate_sha"] == sha and card["run_id"] == "accept-002"
    assert card["test_id"] == "M4A-TARGET-001" and card["metric"] == 1
    assert card["status"] == "Pass" and card["counts"]["skipped"] == 0
    assert card["command"] == evidence["command"]
    before = (output / "result.json").read_bytes()
    second = command(root, *args)
    assert second.returncode != 0
    assert (output / "result.json").read_bytes() == before


def test_m4a_acceptance_strace_proves_zero_network_and_rejects_attempt(
    candidate_repo: tuple[Path, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, sha = candidate_repo
    fake_bin = root / "local-inputs" / "bin"
    fake_strace = fake_bin / "strace"
    write(
        fake_strace,
        "#!/usr/bin/env python3\n"
        "import os,pathlib,subprocess,sys\n"
        "trace=pathlib.Path(sys.argv[sys.argv.index('-o')+1])\n"
        "trace.write_text('connect(3, {sa_family=AF_INET, sin_port=htons(443)}, 16) = -1 ENETUNREACH\\n' "
        "if os.environ.get('SBD_TEST_NETWORK_ATTEMPT') else '')\n"
        "command=sys.argv[sys.argv.index('--')+1:]\n"
        "raise SystemExit(subprocess.run(command).returncode)\n",
    )
    fake_strace.chmod(0o755)
    monkeypatch.setenv("PATH", str(fake_bin) + os.pathsep + os.environ["PATH"])

    def acceptance(run_id: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        matrix_root = write_matrix_inputs(root, sha, f"matrix-{run_id}")
        assert build_matrix(root, sha, f"matrix-{run_id}", matrix_root).returncode == 0
        output = root / "evidence" / "acceptance" / run_id
        assert run_preflight(root, sha, run_id, matrix_root, output).returncode == 0
        result = command(
            root,
            "accept", "--candidate-sha", sha, "--run-id", run_id,
            "--preflight", str(output / "preflight.json"),
            "--suite", "tests/milestones/test_m4_local_voice.py",
            "--timeout-seconds", "10", "--output", str(output),
        )
        return result, output

    passed_result, passed_output = acceptance("m4a-net-zero")
    assert passed_result.returncode == 0, passed_result.stderr
    result = json.loads((passed_output / "result.json").read_text())
    assert result["network_attempt_count"] == 0
    assert (passed_output / "logs" / "network.trace.log").is_file()

    monkeypatch.setenv("SBD_TEST_NETWORK_ATTEMPT", "1")
    failed_result, failed_output = acceptance("m4a-net-attempt")
    assert failed_result.returncode != 0
    assert "network I/O" in failed_result.stderr
    assert "AF_INET" in (
        failed_output / "logs" / "network.trace.log"
    ).read_text(encoding="utf-8")


def test_debug_needs_no_acceptance_failure_bundle(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    output = root / "evidence" / "debug" / "debug-001"
    result = command(
        root,
        "debug",
        "--candidate-sha",
        sha,
        "--run-id",
        "debug-001",
        "--node",
        "tests/test_target.py::test_target",
        "--timeout-seconds",
        "10",
        "--output",
        str(output),
    )
    assert result.returncode == 0, result.stderr
    evidence = json.loads((output / "result.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "Diagnostic"
    assert "failed_acceptance" not in evidence


def test_m4a_network_trace_counts_only_destination_bearing_inet_attempts(
    tmp_path: Path,
) -> None:
    trace = tmp_path / "network.trace.log"
    write(
        trace,
        "1 socket(AF_UNIX, SOCK_STREAM, 0) = 3\n"
        "2 socket(AF_INET, SOCK_STREAM, IPPROTO_TCP) = 3\n"
        "3 socket(AF_INET6, SOCK_DGRAM, IPPROTO_UDP) = 4\n"
        "4 connect(3, {sa_family=AF_INET, sin_port=htons(443)}, 16) = -1 ENETUNREACH\n"
        "5 sendto(4, \"dns\", 3, 0, {sa_family=AF_INET6, sin6_port=htons(53)}, 28) = -1 ENETUNREACH\n",
    )
    assert _network_attempt_count(trace) == 2
    with pytest.raises(GateFailure, match="did not produce"):
        _network_attempt_count(tmp_path / "absent.log")


def test_m4b_acceptance_cards_require_every_test_spec_evidence_field() -> None:
    assert set(M4B_CARD_REQUIRED) == {f"M4B-PI-{name}-001" for name in
                                    ("ATT", "SEM", "CONV", "MEM", "WAKE", "TIME", "RES")}
    for test_id, fields in M4B_CARD_REQUIRED.items():
        with pytest.raises(GateFailure, match="METADATA_INVALID"):
            _validate_m4b_card({"candidate_sha": "a" * 40, "test_id": test_id})
        assert {"profile_sha256", "evidence_sha256", "case_id"}.issubset(fields)


@pytest.mark.parametrize("test_id", [
    "M4B-RDY-001", "M4B-GEN-001", "M4B-OUT-001", "M4B-P5-001",
    "M4B-CAN-001", "M4B-REC-001", "M4B-HIST-001", "M4B-PRIV-001",
    "M4B-OFF-001", "M4B-RES-001", "M4B-PKG-001",
])
def test_m4b_retired_card_ids_cannot_satisfy_current_acceptance(test_id):
    with pytest.raises(GateFailure, match="RETIRED_OR_UNKNOWN"):
        _validate_m4b_card({"test_id": test_id, "candidate_sha": "a" * 40, "status": "Pass"})


def _current_m4b_record():
    return dict(schema_version=1, test_id="M4B-PI-MEM-001", case_id="M01",
        candidate_sha="a" * 40, profile_id="core-m4b-cognition-001", profile_sha256="b" * 64,
        matrix="PR", platform="pi5-4gb-debian13-aarch64", python="3.13.5",
        start_monotonic_ns=1, end_monotonic_ns=2, status="Pass", evidence_sha256="c" * 64)


def test_m4b_well_formed_metadata_does_not_fabricate_native_acceptance():
    with pytest.raises(GateFailure, match="PRIVATE_PROOF_INCOMPLETE"):
        _validate_m4b_card(_current_m4b_record())


@pytest.mark.parametrize("changes", [
    {"private_path": "/tmp/canary"}, {"text": "private"}, {"matrix": "PU"},
    {"python": "3.13.15"}, {"profile_sha256": "invalid"}, {"prewarm_latency_ms": 1},
    {"r14_formula_version": "retired"}, {"status": "Waived"}, {"end_monotonic_ns": 0},
])
def test_m4b_card_rejects_private_extra_fields_and_wrong_scope(changes):
    with pytest.raises(GateFailure, match="METADATA_INVALID"):
        _validate_m4b_card({**_current_m4b_record(), **changes})


def _m4b_product_preflight():
    raw = (REPOSITORY / "requirements/m4b/llm-artifacts.json").read_bytes()
    lock = json.loads(raw)
    return {
        "status": "PreflightReady", "operation": "preflight", "candidate_sha": "a" * 40,
        "candidate_id": "CAND-LRT-G4E2B-MOBILE-R1",
        "pairing_revision": "litert-lm-v0.16.0-pi-g2b-r5",
        "platform": "pi-debian13-aarch64", "python": "CPython 3.13.5",
        "artifact_lock_sha256": hashlib.sha256(raw).hexdigest(),
        "runtime_manifest_sha256": lock["runtime_closure"]["manifest_sha256"],
        "model_sha256": lock["model"]["sha256"],
        "profile_id": "core-m4b-cognition-001", "profile_stage": "release",
        "profile_sha256": "d" * 64, "network_isolated": True,
        "runtime_file_count": 14, "install_file_count": 20,
        "python_abi_attestation_sha256": "b" * 64, "install_inventory_sha256": "c" * 64,
    }


def test_m4b_runner_preflight_binds_sanitized_python_abi_and_inventory():
    value = _m4b_product_preflight()
    assert validate_m4b_product_preflight(value, "a" * 40) == ("b" * 64, "c" * 64)


@pytest.mark.parametrize("changes", [
    {"candidate_sha": "d" * 40}, {"python": "CPython 3.13"}, {"status": "Pass"},
    {"runtime_manifest_sha256": "d" * 64}, {"model_sha256": "e" * 64},
    {"runtime_file_count": 15}, {"runtime_file_count": True}, {"install_file_count": 0},
    {"python_abi_attestation_sha256": "bad"}, {"profile_sha256": "bad"},
    {"profile_stage": "measurement"}, {"network_isolated": False}, {"network_isolated": 1},
    {"private_path": "/tmp/private-runtime"}, {"product_config_sha256": "f" * 64},
])
def test_m4b_runner_preflight_rejects_retired_or_mismatched_identity(changes):
    with pytest.raises(GateFailure, match="M4B_PREFLIGHT_"):
        validate_m4b_product_preflight({**_m4b_product_preflight(), **changes}, "a" * 40)


def _release_profile():
    from sbd.cognition.litert_lm.lock import load_product_profile, profile_digest
    result = dict(load_product_profile(REPOSITORY / "requirements/m4b/product-profile.json", allow_measurement=True))
    result.update(profile_stage="release", min_mem_available_speak_bytes=515 * 1024**2,
        min_mem_available_generate_bytes=523 * 1024**2,
        measurement_evidence_locator="sha256/" + hashlib.sha256(b"synthetic-raw-d").hexdigest())
    result["profile_sha256"] = profile_digest(result)
    return result


def _target_proof(kind):
    from dataclasses import asdict, replace
    from sbd.cognition.litert_lm.lock import LLMArtifactLock, EXPECTED_RUNTIME, EXPECTED_MODEL, load_product_profile
    from scripts.m4b_target_metrics import derive_thresholds
    from tests.test_m4b_res_001 import series, authorization
    from tests.test_m4b_mem_001 import sample
    from sbd.cognition.observability import TIMING_NODES
    profile = _release_profile()
    if kind == "ATT":
        lock = LLMArtifactLock.load(REPOSITORY / "requirements/m4b/llm-artifacts.json")
        lock_data = json.loads((REPOSITORY / "requirements/m4b/llm-artifacts.json").read_bytes())
        artifacts = {name: EXPECTED_RUNTIME[name] for name in
            ("wheel_filename", "wheel_size_bytes", "wheel_sha256", "native_relative_path", "native_size_bytes", "native_sha256")}
        artifacts.update(model_filename=EXPECTED_MODEL["filename"], model_size_bytes=EXPECTED_MODEL["size_bytes"],
            model_sha256=EXPECTED_MODEL["sha256"], lock_sha256=lock.digest,
            runtime_manifest_sha256=lock_data["runtime_closure"]["manifest_sha256"], runtime_file_count=14,
            notice_sha256=lock_data["licenses"]["notice_sha256"])
        data = dict(profile=profile, ready_identity=dict(lock.ready_identity(profile).fields),
            artifacts=artifacts,
            target=dict(clean_worktree=True, candidate_sha="a" * 40, platform="pi5-4gb-debian13-aarch64",
                python="3.13.5", soabi="cpython-313-aarch64-linux-gnu", multiarch="aarch64-linux-gnu",
                pid=4, pgid=4, prewarm_count=0, conversation_count=0, kernel_sha256="e" * 64,
                deployment_files_verified=True, system_site_packages=False, extra_artifact_count=0, alternate_endpoint_count=0),
            capture=dict(before_native_import=True, through_child_exit=True, network_attempts=0,
                downloader_calls=0, telemetry_calls=0, dns_calls=0, fallback_calls=0))
    elif kind == "SEM":
        cases = [dict(case_id=f"H{i:02}", answer_sha256="e" * 64, end=i == 5, spoken_length=10,
            structural_pass=True, conversation_generation=1, turn_index=i, farewell_before_rest=True if i == 5 else None,
            rubric=dict(reviewer="synthetic-reviewer", correct_relevant=True, capability_honest=True,
                end_polarity=True, traditional_chinese=True, concise=True,
                personality_applicable=i == 7, personality_present=True if i == 7 else None)) for i in range(1, 10)]
        data = dict(cases=cases)
    elif kind == "CONV":
        names = ["context_rejected", "primary_terminal", "close_proven", "open_ready", "human_repeat", "repeat_success", "following_success"]
        data = dict(events=[dict(event=name, monotonic_ns=i, generation=1 if i < 3 else 2,
            turn_index=1 if i < 4 else 2 if i < 6 else 3,
            proofs=dict(closed=True, history_clear=True, kv_released=True) if i == 2 else None)
            for i, name in enumerate(names)], same_product_session=True, rejected_send_count=0,
            rejected_mutation_count=0, automatic_replay_count=0, old_context_absent=True, new_context_works=True)
    elif kind == "MEM":
        measured = load_product_profile(REPOSITORY / "requirements/m4b/product-profile.json", allow_measurement=True)
        identity, _ = authorization()
        identity.update(candidate_sha="a" * 40, profile_sha256=measured["profile_sha256"],
            harness_sha256=hashlib.sha256((REPOSITORY / "scripts/m4b_measurement.py").read_bytes()).hexdigest())
        rows = []
        for available, decision in ((523 * 1024**2, "GENERATE"), (523 * 1024**2 - 1, "NOTICE"),
                                   (515 * 1024**2, "NOTICE"), (515 * 1024**2 - 1, "SILENT")):
            observation = asdict(replace(sample(), mem_total_bytes=2000 * 1024**2, mem_available_bytes=available))
            rows.append(dict(sample=observation, decision=decision, generate_calls=int(decision == "GENERATE"),
                tts_calls=int(decision != "SILENT"), recycle_pending=decision != "GENERATE"))
        data = dict(measurement_profile=dict(measured), measurement_attestation=identity,
            points=[asdict(p) for p in series()], release_profile=profile,
            completed=True, cleanup_proven=True, measurement_run_sha256="d" * 64, release_run_sha256="e" * 64,
            release_rows=rows, recovery_ready=True, new_turn_success=True)
    elif kind == "WAKE":
        data = dict(cases=[])
        for name in ("open_first", "ack_first", "slow_open", "interrupt_open"):
            interrupted = name == "interrupt_open"
            data["cases"].append(dict(case=name, wake_ack_ns=2 if name == "open_first" else 1,
                open_ready_ns=None if interrupted else 1 if name == "open_first" else 2,
                open_join_ns=None if interrupted else 3,
                activity=[] if interrupted else [dict(kind=k, monotonic_ns=4) for k in
                    ("audio_pull", "listen", "asr", "perception", "reasoner")],
                display_blocked=False, display_fact_count=0, display_turn_count=0, cleanup_proven=True))
    elif kind == "TIME":
        data = dict(rows=[dict(clock_domain="controller_monotonic", events=dict(zip(TIMING_NODES, range(7))), null_reasons={})],
                    clock_mapping_sha256="d" * 64, mapping_verified=True)
    else:
        data = dict(runs=[dict(stage=stage, run_sha256=digest * 64, network_attempts=0, swap_growth_bytes=0,
            oom_delta=0, kernel_faults=0, throttled_bits=0, temperature_stop_violations=0, orphans=0,
            duplicate_pids=0, owner_leaks=0) for stage, digest in (("measurement", "d"), ("release", "e"))],
            cleanup=[dict(kind=k, start_ns=1, exit_ns=2, deadline_ns=3, remaining_owners=0,
                remaining_descendants=0, recovery_success=True) for k in
                ("normal_close", "planned_recovery", "forced_pgid", "shutdown")],
            scan=dict(domains=["logs", "public_evidence", "temp_workdirs", "process_arguments", "process_environment", "persisted_files"],
                post_session_close=True, post_shutdown=True, reversible_encodings=True, hits=0, manifest_sha256="f" * 64))
    def resolve_synthetic_digests(value):
        if isinstance(value, dict):
            return {k: resolve_synthetic_digests(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [resolve_synthetic_digests(v) for v in value]
        if isinstance(value, str) and value in {letter * 64 for letter in "def"}:
            return hashlib.sha256(f"synthetic-raw-{value[0]}".encode()).hexdigest()
        return value
    data = resolve_synthetic_digests(data)
    if kind == "MEM":
        from sbd.cognition.litert_lm.lock import profile_digest
        raw = json.dumps(data["points"], sort_keys=True).encode()
        data["measurement_run_sha256"] = hashlib.sha256(raw).hexdigest()
        profile["measurement_evidence_locator"] = "sha256/" + data["measurement_run_sha256"]
        profile["profile_sha256"] = profile_digest(profile)
        data["release_profile"] = profile
        raw = json.dumps({"rows": data["release_rows"], "profile_sha256": profile["profile_sha256"]}, sort_keys=True).encode()
        data["release_run_sha256"] = hashlib.sha256(raw).hexdigest()
    record = {**_current_m4b_record(), "test_id": f"M4B-PI-{kind}-001", "profile_sha256": profile["profile_sha256"]}
    proof = dict(schema_version=1, test_id=record["test_id"], candidate_sha=record["candidate_sha"],
                 profile_sha256=record["profile_sha256"], data=data)
    return record, proof


def _validate_fixture(record, proof):
    payload = json.dumps(proof).encode()
    record = {**record, "evidence_sha256": hashlib.sha256(payload).hexdigest()}
    blobs = {hashlib.sha256(f"synthetic-raw-{letter}".encode()).hexdigest(): f"synthetic-raw-{letter}".encode()
             for letter in "def"}
    if record["test_id"] == "M4B-PI-MEM-001":
        data = proof["data"]
        for value in (data["points"],
                      {"rows": data["release_rows"], "profile_sha256": data["release_profile"]["profile_sha256"]}):
            raw = json.dumps(value, sort_keys=True).encode()
            blobs[hashlib.sha256(raw).hexdigest()] = raw
    blobs[record["evidence_sha256"]] = payload
    _validate_m4b_card(record, evidence_resolver=blobs.__getitem__)


@pytest.mark.parametrize("kind", ["ATT", "SEM", "CONV", "MEM", "WAKE", "TIME", "RES"])
def test_m4b_private_proof_reconciliation_executes_current_structural_rules(kind):
    record, proof = _target_proof(kind)
    _validate_fixture(record, proof)
    with pytest.raises(GateFailure, match="PRIVATE_PROOF_INVALID"):
        _validate_m4b_card(record, evidence_resolver=lambda _: b"corrupt")
    proof["candidate_sha"] = "f" * 40
    with pytest.raises(GateFailure, match="PRIVATE_PROOF_INVALID"):
        _validate_fixture(record, proof)


@pytest.mark.parametrize("kind,mutate", [
    ("ATT", lambda d: d["capture"].update(network_attempts=1)),
    ("ATT", lambda d: d["target"].update(prewarm_count=1)),
    ("SEM", lambda d: d["cases"][8].update(conversation_generation=2)),
    ("SEM", lambda d: d["cases"][6]["rubric"].update(personality_present=False)),
    ("CONV", lambda d: d["events"][2]["proofs"].update(kv_released=False)),
    ("CONV", lambda d: d.update(automatic_replay_count=1)),
    ("MEM", lambda d: d["release_rows"][1].update(generate_calls=1)),
    ("MEM", lambda d: d["measurement_attestation"].update(candidate_sha="f" * 40)),
    ("WAKE", lambda d: d["cases"][0]["activity"][0].update(monotonic_ns=1)),
    ("WAKE", lambda d: d["cases"][3].update(cleanup_proven=False)),
    ("TIME", lambda d: d["rows"][0]["events"].update(audio_first_write=0)),
    ("TIME", lambda d: d.update(mapping_verified=False)),
    ("RES", lambda d: d["scan"].update(hits=1)),
    ("RES", lambda d: d["cleanup"][2].update(exit_ns=4)),
])
def test_m4b_private_proof_rejects_false_pass_values(kind, mutate):
    record, proof = _target_proof(kind)
    mutate(proof["data"])
    with pytest.raises(GateFailure, match="PRIVATE_PROOF_INVALID"):
        _validate_fixture(record, proof)
