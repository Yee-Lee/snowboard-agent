from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts.candidate_gate import GateFailure, _network_attempt_count


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
        root / "tests" / "test_target.py",
        "import json,os,pathlib,pytest\n\n"
        "@pytest.mark.rpi\ndef test_target():\n"
        "    if 'SBD_M4A_CARD_ROOT' not in os.environ:\n"
        "        assert 'SBD_M4A_CANDIDATE_SHA' not in os.environ\n"
        "        return\n"
        "    root=pathlib.Path(os.environ['SBD_M4A_CARD_ROOT'])\n"
        "    sha=os.environ['SBD_M4A_CANDIDATE_SHA']\n"
        "    assert os.environ['SBD_M4A_ACCEPTANCE_RUN_ID']=='accept-002'\n"
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
        "trace.write_text('socket(AF_INET, SOCK_STREAM, 0) = 3\\n' "
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
    assert "network syscall" in failed_result.stderr
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


def test_m4a_network_trace_counts_only_inet_attempts(tmp_path: Path) -> None:
    trace = tmp_path / "network.trace.log"
    write(
        trace,
        "1 socket(AF_UNIX, SOCK_STREAM, 0) = 3\n"
        "2 socket(AF_INET, SOCK_STREAM, IPPROTO_TCP) = -1 ENETUNREACH\n"
        "3 socket(AF_INET6, SOCK_DGRAM, IPPROTO_UDP) = -1 ENETUNREACH\n",
    )
    assert _network_attempt_count(trace) == 2
    with pytest.raises(GateFailure, match="did not produce"):
        _network_attempt_count(tmp_path / "absent.log")
