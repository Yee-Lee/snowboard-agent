from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


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
    write(root / "pyproject.toml", "[project]\nname='gate-fixture'\nversion='0.0.0'\n")
    write(root / "pytest.ini", "[pytest]\nmarkers =\n    rpi: target-only test\n")
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
        root / "tests" / "test_target.py",
        "import pytest\n\n@pytest.mark.rpi\ndef test_target():\n    assert True\n",
    )
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


def version_result(sha: str, run_id: str, minor: str, branch: str = "candidate/test") -> dict[str, object]:
    return {
        "branch": branch,
        "candidate_sha": sha,
        "counts": {"passed": 1, "failed": 0, "skipped": 0, "xfailed": 0},
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
    before = (output / "result.json").read_bytes()
    second = command(root, *args)
    assert second.returncode != 0
    assert (output / "result.json").read_bytes() == before


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
        "3",
        "--output",
        str(output),
    )
    assert result.returncode == 0, result.stderr
    evidence = json.loads((output / "result.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "Diagnostic"
    assert "failed_acceptance" not in evidence
