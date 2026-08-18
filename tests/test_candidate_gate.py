"""Black-box regressions for the M4 candidate hardware gate."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

import pytest


REPOSITORY = Path(__file__).resolve().parents[1]
RUNNER = REPOSITORY / "scripts" / "candidate_gate.py"
PYTHON_MINOR = f"{sys.version_info.major}.{sys.version_info.minor}"
MINORS = ("3.11", "3.12", "3.13")


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


@pytest.fixture()
def candidate_repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "candidate"
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "scripts").mkdir()
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "src" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    producer = '''import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest


def write_record(path, value):
    target = Path(path)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(value), encoding="utf-8")
    temporary.replace(target)


def producer_handshake():
    common = {
        "candidate_sha": os.environ["CANDIDATE_GATE_CANDIDATE_SHA"],
        "mode": os.environ["CANDIDATE_GATE_MODE"],
        "nonce": os.environ["CANDIDATE_GATE_NONCE"],
        "producer_pid": os.getpid(),
        "run_id": os.environ["CANDIDATE_GATE_RUN_ID"],
        "test_id": os.environ["CANDIDATE_GATE_TEST_ID"],
    }
    write_record(os.environ["CANDIDATE_GATE_SUITE_STARTED"], {**common, "started_at_utc": datetime.now(UTC).isoformat()})
    write_record(os.environ["CANDIDATE_GATE_READY_RECORD"], {**common, "ready_at_utc": datetime.now(UTC).isoformat()})
    observation = Path(os.environ["CANDIDATE_GATE_MANUAL_OBSERVATION"])
    deadline = time.monotonic() + 5
    while not observation.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert observation.exists(), "operator observation did not arrive"


@pytest.mark.rpi
def test_rpi():
    producer_handshake()
'''
    (root / "tests" / "test_rpi.py").write_text(producer, encoding="utf-8")
    (root / "tests" / "test_rpi_fail.py").write_text(
        producer.replace("def test_rpi():\n    producer_handshake()", "def test_rpi_fail():\n    producer_handshake()\n    assert False, 'injected formal acceptance failure'"),
        encoding="utf-8",
    )
    (root / "tests" / "test_debug.py").write_text(
        "import time\nimport pytest\n\n@pytest.mark.rpi\ndef test_ok():\n    assert True\n\n@pytest.mark.rpi\ndef test_hang():\n    time.sleep(30)\n",
        encoding="utf-8",
    )
    (root / "scripts" / "existing_runner.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / ".github" / "workflows" / "existing.yml").write_text("name: fixture\n", encoding="utf-8")
    (root / ".gitignore").write_text("__pycache__/\n*.pyc\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        "[project]\nname = 'candidate-fixture'\nversion = '0'\nrequires-python = '>=3.11,<3.14'\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    git(root, "config", "user.email", "candidate@example.test")
    git(root, "config", "user.name", "Candidate Test")
    git(root, "add", ".")
    git(root, "commit", "-qm", "fixture")
    return root, git(root, "rev-parse", "HEAD")


def gate_command(root: Path, *args: str) -> list[str]:
    return [sys.executable, str(RUNNER), "--repo", str(root), *args]


def gate(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        gate_command(root, *args),
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def portable_output(root: Path, run_id: str) -> Path:
    return root / "evidence" / "portable" / run_id / f"python-{PYTHON_MINOR}"


def version_result(sha: str, run_id: str, minor: str) -> dict[str, object]:
    started = datetime.now(UTC)
    return {
        "branch": "fixture-branch",
        "candidate_sha": sha,
        "command": [f"python{minor}", "-m", "pytest", "tests"],
        "counts": {"passed": 10, "failed": 0, "blocked": 0, "skipped": 0, "xfailed": 0},
        "dependency_lock_checksum": "a" * 64,
        "dirty_paths": [],
        "ended_at_utc": (started + timedelta(seconds=1)).isoformat(),
        "exit_code": 0,
        "platform": "fixture-linux",
        "python": {"implementation": "CPython", "version": f"{minor}.9"},
        "python_minor": minor,
        "protected_paths_clean": True,
        "raw_logs": ["logs/suite.stdout.log", "logs/suite.stderr.log"],
        "run_id": run_id,
        "status": "Pass",
        "started_at_utc": started.isoformat(),
        "suite": "tests",
        "suite_test_ids": ["OUT-PROCESS-2026-001"],
        "timeout_seconds": 60,
    }


def version_identity(result: dict[str, object]) -> dict[str, object]:
    return {
        name: result[name]
        for name in (
            "command",
            "branch",
            "counts",
            "dependency_lock_checksum",
            "dirty_paths",
            "ended_at_utc",
            "exit_code",
            "platform",
            "protected_paths_clean",
            "python",
            "python_minor",
            "raw_logs",
            "started_at_utc",
            "suite",
            "suite_test_ids",
            "timeout_seconds",
        )
    }


def make_preflight_inputs(root: Path, sha: str, run_id: str = "matrix") -> tuple[Path, Path, Path, Path, Path]:
    matrix_started = datetime.now(UTC)
    matrix_root = root / "evidence" / "portable" / run_id
    results: dict[str, str] = {}
    identities: dict[str, dict[str, object]] = {}
    for minor in MINORS:
        result_path = matrix_root / f"python-{minor}" / "result.json"
        result = version_result(sha, run_id, minor)
        write_json(result_path, result)
        results[minor] = str(result_path.relative_to(matrix_root))
        identities[minor] = version_identity(result)
    matrix = matrix_root / "matrix-index.json"
    write_json(
        matrix,
        {
            "branch": "fixture-branch",
            "candidate_sha": sha,
            "command": ["candidate_gate.py", "matrix"],
            "dependency_lock_checksum": "a" * 64,
            "dirty_paths": [],
            "ended_at_utc": (matrix_started + timedelta(seconds=1)).isoformat(),
            "exit_code": 0,
            "platforms": ["fixture-linux"],
            "protected_paths_clean": True,
            "results": results,
            "run_id": run_id,
            "status": "Pass",
            "started_at_utc": matrix_started.isoformat(),
            "suite_test_ids": ["OUT-PROCESS-2026-001"],
            "version_identities": identities,
        },
    )
    freeze = root / "freeze-manifest.json"
    write_json(freeze, {"candidate_sha": sha, "status": "Frozen"})
    hardware = root / "hardware.json"
    config = root / "config.yaml"
    artifact = root / "artifacts.json"
    for path in (hardware, config, artifact):
        path.write_text("{}\n", encoding="utf-8")
    return matrix, freeze, hardware, config, artifact


def preflight(root: Path, sha: str, run_id: str) -> tuple[subprocess.CompletedProcess[str], tuple[Path, Path, Path, Path, Path]]:
    inputs = make_preflight_inputs(root, sha)
    matrix, freeze, hardware, config, artifact = inputs
    output = root / "evidence" / "acceptance" / run_id
    result = gate(
        root,
        "preflight",
        "--candidate-sha",
        sha,
        "--run-id",
        run_id,
        "--portable-index",
        str(matrix),
        "--freeze-manifest",
        str(freeze),
        "--runtime",
        "3.13",
        "--hardware",
        str(hardware),
        "--config",
        str(config),
        "--artifact-manifest",
        str(artifact),
        "--output",
        str(output),
    )
    return result, inputs


def accept_args(root: Path, sha: str, run_id: str, manual_timeout: str = "2") -> list[str]:
    output = root / "evidence" / "acceptance" / run_id
    return [
        "accept",
        "--candidate-sha",
        sha,
        "--run-id",
        run_id,
        "--preflight",
        str(output / "preflight.json"),
        "--suite",
        "tests/test_rpi.py",
        "--timeout-seconds",
        "5",
        "--manual-timeout-seconds",
        manual_timeout,
        "--readiness-timeout-seconds",
        "2",
        "--test-id",
        "M4-REG-001",
        "--ready-record",
        str(output / "cards" / "M4-REG-001-ready.json"),
        "--manual-observation",
        str(output / "manual" / "M4-REG-001.json"),
        "--output",
        str(output),
    ]


def run_accept_with_observation(
    root: Path,
    args: list[str],
    observation_factory: Callable[[dict[str, object]], dict[str, object] | None],
) -> subprocess.CompletedProcess[str]:
    ready_path = Path(args[args.index("--ready-record") + 1])
    observation_path = Path(args[args.index("--manual-observation") + 1])
    output = Path(args[args.index("--output") + 1])
    test_id = args[args.index("--test-id") + 1]
    suite_started_path = output / "cards" / f"{test_id}-suite-started.json"
    process = subprocess.Popen(
        gate_command(root, *args),
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 3
    while not ready_path.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    if ready_path.exists():
        assert suite_started_path.exists(), "READY was not emitted by an active suite producer"
        ready = json.loads(ready_path.read_text(encoding="utf-8"))
        observation = observation_factory(ready)
        if observation is not None:
            write_json(observation_path, observation)
    stdout, stderr = process.communicate(timeout=10)
    return subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)


def valid_observation(ready: dict[str, object]) -> dict[str, object]:
    ready_at = datetime.fromisoformat(str(ready["ready_at_utc"]).replace("Z", "+00:00"))
    return {
        "checklist": {"heard": True},
        "checklist_version": "1",
        "candidate_sha": ready["candidate_sha"],
        "mode": "acceptance",
        "nonce": ready["nonce"],
        "observed_at_utc": (ready_at + timedelta(milliseconds=1)).isoformat(),
        "operator": "tester",
        "record_command_exit_code": 0,
        "run_id": ready["run_id"],
        "test_id": ready["test_id"],
    }


def test_dry_sha_rejects_mismatched_external_candidate_before_suite(candidate_repo: tuple[Path, str]) -> None:
    root, _ = candidate_repo
    output = portable_output(root, "dry-sha")
    result = gate(root, "portable", "--candidate-sha", "0" * 40, "--run-id", "dry-sha", "--python", PYTHON_MINOR, "--suite", "tests", "--test-id", "OUT-PROCESS-2026-001", "--timeout-seconds", "5", "--output", str(output))

    assert result.returncode != 0
    assert "does not match checked-out HEAD" in result.stderr
    assert (output / "portable-failure.json").is_file()
    assert not (output / "result.json").exists()


@pytest.mark.parametrize(
    ("relative_path", "content"),
    [
        ("src/module.py", "VALUE = 2\n"),
        ("scripts/run_m4_acceptance.py", "VALUE = 1\n"),
        ("scripts/existing_runner.py", "VALUE = 2\n"),
        (".github/workflows/new-candidate.yml", "name: new\n"),
        (".github/workflows/existing.yml", "name: changed\n"),
    ],
)
def test_dry_dirty_protects_complete_runner_surface(candidate_repo: tuple[Path, str], relative_path: str, content: str) -> None:
    root, sha = candidate_repo
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    output = portable_output(root, "dry-dirty")
    result = gate(root, "portable", "--candidate-sha", sha, "--run-id", "dry-dirty", "--python", PYTHON_MINOR, "--suite", "tests", "--test-id", "OUT-PROCESS-2026-001", "--timeout-seconds", "5", "--output", str(output))

    assert result.returncode != 0
    assert "protected candidate input is dirty" in result.stderr
    assert relative_path in (output / "logs" / "portable.stderr.log").read_text(encoding="utf-8")
    assert not (output / "result.json").exists()


def test_dry_matrix_rejects_missing_python_minor(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    matrix, freeze, hardware, config, artifact = make_preflight_inputs(root, sha)
    index = json.loads(matrix.read_text(encoding="utf-8"))
    del index["results"]["3.12"]
    matrix.write_text(json.dumps(index), encoding="utf-8")
    output = root / "evidence" / "acceptance" / "dry-matrix"
    result = gate(root, "preflight", "--candidate-sha", sha, "--run-id", "dry-matrix", "--portable-index", str(matrix), "--freeze-manifest", str(freeze), "--runtime", "3.13", "--hardware", str(hardware), "--config", str(config), "--artifact-manifest", str(artifact), "--output", str(output))

    assert result.returncode != 0
    assert "exactly Python 3.11, 3.12, and 3.13" in result.stderr
    assert (output / "preflight-failure.json").is_file()
    assert not (output / "preflight.json").exists()


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("run_id", None, "portable run"),
        ("python_minor", "3.12", "python_minor"),
        ("platform", None, "platform identity"),
        ("dependency_lock_checksum", None, "dependency checksum"),
        ("branch", None, "branch identity"),
        ("dirty_paths", None, "dirty identity"),
        ("protected_paths_clean", False, "dirty identity"),
        ("started_at_utc", None, "started_at_utc"),
        ("ended_at_utc", None, "ended_at_utc"),
        ("exit_code", 1, "exit code"),
        ("suite_test_ids", None, "suite/Test-ID"),
    ],
)
def test_matrix_identity_is_fail_closed(candidate_repo: tuple[Path, str], field: str, value: object, reason: str) -> None:
    root, sha = candidate_repo
    matrix, freeze, hardware, config, artifact = make_preflight_inputs(root, sha)
    result_path = matrix.parent / "python-3.11" / "result.json"
    def mutate() -> None:
        result_data = json.loads(result_path.read_text(encoding="utf-8"))
        if value is None:
            result_data.pop(field)
        else:
            result_data[field] = value
        result_path.write_text(json.dumps(result_data), encoding="utf-8")

    mutate()
    matrix.unlink()
    matrix_build = gate(root, "matrix", "--candidate-sha", sha, "--run-id", "matrix", "--input-root", str(matrix.parent), "--output", str(matrix))
    assert matrix_build.returncode != 0
    assert matrix.exists(), matrix_build.stderr
    assert json.loads(matrix.read_text(encoding="utf-8"))["status"] == "Fail"

    matrix, freeze, hardware, config, artifact = make_preflight_inputs(root, sha)
    result_path = matrix.parent / "python-3.11" / "result.json"
    mutate()
    output = root / "evidence" / "acceptance" / f"identity-{field}"
    completed = gate(root, "preflight", "--candidate-sha", sha, "--run-id", f"identity-{field}", "--portable-index", str(matrix), "--freeze-manifest", str(freeze), "--runtime", "3.13", "--hardware", str(hardware), "--config", str(config), "--artifact-manifest", str(artifact), "--output", str(output))

    assert completed.returncode != 0
    assert reason in completed.stderr
    assert (output / "preflight-failure.json").is_file()
    assert not (output / "preflight.json").exists()


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("branch", None),
        ("dirty_paths", None),
        ("started_at_utc", None),
        ("exit_code", None),
        ("suite_test_ids", None),
        ("platforms", None),
        ("command", []),
    ],
)
def test_preflight_rejects_incomplete_matrix_aggregate_identity(candidate_repo: tuple[Path, str], field: str, replacement: object) -> None:
    root, sha = candidate_repo
    matrix, freeze, hardware, config, artifact = make_preflight_inputs(root, sha)
    index = json.loads(matrix.read_text(encoding="utf-8"))
    if replacement is None:
        index.pop(field)
    else:
        index[field] = replacement
    matrix.write_text(json.dumps(index), encoding="utf-8")
    output = root / "evidence" / "acceptance" / f"aggregate-{field}"
    completed = gate(root, "preflight", "--candidate-sha", sha, "--run-id", f"aggregate-{field}", "--portable-index", str(matrix), "--freeze-manifest", str(freeze), "--runtime", "3.13", "--hardware", str(hardware), "--config", str(config), "--artifact-manifest", str(artifact), "--output", str(output))

    assert completed.returncode != 0
    assert (output / "preflight-failure.json").is_file()
    assert not (output / "preflight.json").exists()


def test_matrix_builder_failure_has_machine_readable_bundle(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    matrix_root = root / "evidence" / "portable" / "matrix-fail"
    result = gate(root, "matrix", "--candidate-sha", sha, "--run-id", "matrix-fail", "--input-root", str(matrix_root), "--output", str(matrix_root / "matrix-index.json"))

    assert result.returncode != 0
    assert "traceback" not in result.stderr.lower()
    assert json.loads((matrix_root / "matrix-index.json").read_text(encoding="utf-8"))["status"] == "Fail"
    assert (matrix_root / "matrix-failure.json").is_file()
    assert (matrix_root / "logs" / "matrix.stderr.log").is_file()


def test_dry_timeout_records_bounded_failure(candidate_repo: tuple[Path, str]) -> None:
    root, _ = candidate_repo
    hanging = root / "tests" / "test_hang.py"
    hanging.write_text("import time\n\ndef test_hang():\n    time.sleep(30)\n", encoding="utf-8")
    git(root, "add", "tests/test_hang.py")
    git(root, "commit", "-qm", "add hanging suite")
    sha = git(root, "rev-parse", "HEAD")
    output = portable_output(root, "dry-timeout")
    result = gate(root, "portable", "--candidate-sha", sha, "--run-id", "dry-timeout", "--python", PYTHON_MINOR, "--suite", "tests/test_hang.py", "--test-id", "OUT-PROCESS-2026-001", "--timeout-seconds", "0.1", "--output", str(output))

    assert result.returncode != 0
    assert "suite timeout" in result.stderr
    assert "TIMEOUT" in (output / "logs" / "suite.stderr.log").read_text(encoding="utf-8")
    assert (output / "portable-failure.json").is_file()


@pytest.mark.parametrize("case", ["prefilled", "stale", "wrong-nonce", "missing", "record-failure", "missing-identity"])
def test_dry_manual_requires_current_card_handshake(candidate_repo: tuple[Path, str], case: str) -> None:
    root, sha = candidate_repo
    run_id = f"manual-{case}"
    preflight_result, _ = preflight(root, sha, run_id)
    assert preflight_result.returncode == 0, preflight_result.stderr
    args = accept_args(root, sha, run_id, manual_timeout="0.15" if case == "missing" else "2")
    observation_path = Path(args[args.index("--manual-observation") + 1])
    if case == "prefilled":
        write_json(observation_path, {"prefilled": True})
        completed = gate(root, *args)
    else:
        def factory(ready: dict[str, object]) -> dict[str, object] | None:
            if case == "missing":
                return None
            observation = valid_observation(ready)
            if case == "stale":
                observation["observed_at_utc"] = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
            elif case == "wrong-nonce":
                observation["nonce"] = "wrong"
            elif case == "record-failure":
                observation["record_command_exit_code"] = 1
            elif case == "missing-identity":
                observation.pop("candidate_sha")
                observation.pop("mode")
            return observation

        completed = run_accept_with_observation(root, args, factory)

    assert completed.returncode != 0
    output = root / "evidence" / "acceptance" / run_id
    assert not (output / "manifest.json").exists()
    failure = json.loads((output / "results" / "result.json").read_text(encoding="utf-8"))
    assert failure["candidate_sha"] == sha
    assert failure["run_id"] == run_id
    assert failure["mode"] == "acceptance"
    assert failure["branch"]
    assert failure["dirty_paths"] == []
    assert failure["protected_paths_clean"] is True
    assert failure["platform"] and failure["python"]
    assert failure["command"] and failure["frozen_inputs"]
    assert failure["preflight"]["sha256"]
    assert failure["started_at_utc"] and failure["ended_at_utc"]
    assert failure["exit_code"] != 0
    assert "logs/accept.stderr.log" in failure["raw_logs"]


def test_acceptance_attempt_cannot_be_resumed_or_overwritten(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    run_id = "accept-once"
    result, _ = preflight(root, sha, run_id)
    assert result.returncode == 0, result.stderr
    args = accept_args(root, sha, run_id)
    first = run_accept_with_observation(root, args, valid_observation)
    assert first.returncode == 0, first.stderr
    output = root / "evidence" / "acceptance" / run_id
    protected = [output / "accept-attempt.json", output / "results" / "result.json", output / "manifest.json", output / "logs" / "suite.stdout.log"]
    before = {path: file_sha256(path) for path in protected}

    second = gate(root, *args)

    assert second.returncode != 0
    assert "cannot be resumed" in second.stderr
    assert before == {path: file_sha256(path) for path in protected}


def test_acceptance_binds_preflight_and_manual_evidence_checksums(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    run_id = "evidence-chain"
    result, _ = preflight(root, sha, run_id)
    assert result.returncode == 0, result.stderr
    completed = run_accept_with_observation(root, accept_args(root, sha, run_id), valid_observation)
    assert completed.returncode == 0, completed.stderr
    manifest = json.loads((root / "evidence" / "acceptance" / run_id / "manifest.json").read_text(encoding="utf-8"))

    assert set(manifest["frozen_inputs"]) == {"artifact_manifest", "config", "freeze_manifest", "hardware", "portable_index"}
    assert set(manifest["portable_result_checksums"]) == set(MINORS)
    assert len(manifest["preflight"]["sha256"]) == 64
    assert len(manifest["ready_record"]["sha256"]) == 64
    assert len(manifest["manual_observation"]["sha256"]) == 64


def test_manual_observation_follows_active_suite_producer_ready(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    run_id = "producer-barrier"
    result, _ = preflight(root, sha, run_id)
    assert result.returncode == 0, result.stderr
    observed_after_producer = False

    def observe(ready: dict[str, object]) -> dict[str, object]:
        nonlocal observed_after_producer
        output = root / "evidence" / "acceptance" / run_id
        started = json.loads((output / "cards" / "M4-REG-001-suite-started.json").read_text(encoding="utf-8"))
        assert started["producer_pid"] == ready["producer_pid"]
        assert datetime.fromisoformat(ready["ready_at_utc"]) >= datetime.fromisoformat(started["started_at_utc"])
        observed_after_producer = True
        return valid_observation(ready)

    completed = run_accept_with_observation(root, accept_args(root, sha, run_id), observe)

    assert completed.returncode == 0, completed.stderr
    assert observed_after_producer


def test_post_preflight_consumed_input_mutation_prevents_acceptance(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    for target in ("hardware", "freeze", "matrix", "version-result", "identity"):
        run_id = f"mutated-{target}"
        result, inputs = preflight(root, sha, run_id)
        assert result.returncode == 0, result.stderr
        matrix, freeze, hardware, _, _ = inputs
        paths = {
            "freeze": freeze,
            "hardware": hardware,
            "identity": root / "evidence" / "acceptance" / run_id / "identity.json",
            "matrix": matrix,
            "version-result": matrix.parent / "python-3.11" / "result.json",
        }
        paths[target].write_bytes(paths[target].read_bytes() + b"\n")
        completed = gate(root, *accept_args(root, sha, run_id))

        assert completed.returncode != 0
        assert "changed after preflight" in completed.stderr or "does not match preflight" in completed.stderr
        assert not (root / "evidence" / "acceptance" / run_id / "manifest.json").exists()


def failed_acceptance(root: Path, sha: str, run_id: str = "failed-accept") -> Path:
    path = root / "evidence" / "acceptance" / run_id / "results" / "result.json"
    write_json(path, {"candidate_sha": sha, "mode": "acceptance", "run_id": run_id, "status": "Fail"})
    return path


def test_debug_rejects_path_shaped_fabricated_acceptance_failure(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    failed = failed_acceptance(root, sha)
    output = root / "evidence" / "debug" / "debug-fabricated"
    result = gate(root, "debug", "--candidate-sha", sha, "--run-id", "debug-fabricated", "--node", "tests/test_debug.py::test_ok", "--failed-acceptance", str(failed), "--timeout-seconds", "2", "--output", str(output))

    assert result.returncode != 0
    assert "attempt" in result.stderr or "chain" in result.stderr
    assert not (output / "manifest.json").exists()


def test_debug_uses_runner_generated_fail_bundle_and_executes_bounded_nodes(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    failed_run = "runner-failed"
    preflight_result, _ = preflight(root, sha, failed_run)
    assert preflight_result.returncode == 0, preflight_result.stderr
    failure_args = accept_args(root, sha, failed_run)
    failure_args[failure_args.index("--suite") + 1] = "tests/test_rpi_fail.py"
    acceptance = run_accept_with_observation(root, failure_args, valid_observation)
    assert acceptance.returncode != 0
    failed = root / "evidence" / "acceptance" / failed_run / "results" / "result.json"

    success_output = root / "evidence" / "debug" / "debug-success"
    success = gate(root, "debug", "--candidate-sha", sha, "--run-id", "debug-success", "--node", "tests/test_debug.py::test_ok", "--failed-acceptance", str(failed), "--timeout-seconds", "2", "--output", str(success_output))
    assert success.returncode == 0, success.stderr
    assert json.loads((success_output / "manifest.json").read_text(encoding="utf-8"))["status"] == "Diagnostic"

    missing_output = root / "evidence" / "debug" / "debug-missing"
    missing = gate(root, "debug", "--candidate-sha", sha, "--run-id", "debug-missing", "--node", "tests/DOES_NOT_EXIST.py::bad", "--failed-acceptance", str(failed), "--timeout-seconds", "2", "--output", str(missing_output))
    assert missing.returncode != 0
    assert not (missing_output / "manifest.json").exists()

    output = root / "evidence" / "debug" / "debug-timeout"
    result = gate(root, "debug", "--candidate-sha", sha, "--run-id", "debug-timeout", "--node", "tests/test_debug.py::test_hang", "--failed-acceptance", str(failed), "--timeout-seconds", "0.1", "--output", str(output))

    assert result.returncode != 0
    assert "TIMEOUT" in (output / "logs" / "suite.stderr.log").read_text(encoding="utf-8")
    assert json.loads((output / "result.json").read_text(encoding="utf-8"))["status"] == "Fail"
    assert not (output / "manifest.json").exists()


def test_portable_matrix_index_requires_complete_same_candidate_identity(candidate_repo: tuple[Path, str]) -> None:
    root, sha = candidate_repo
    run_id = "matrix-pass"
    matrix_root = root / "evidence" / "portable" / run_id
    for minor in MINORS:
        write_json(matrix_root / f"python-{minor}" / "result.json", version_result(sha, run_id, minor))
    result = gate(root, "matrix", "--candidate-sha", sha, "--run-id", run_id, "--input-root", str(matrix_root), "--output", str(matrix_root / "matrix-index.json"))

    assert result.returncode == 0, result.stderr
    index = json.loads((matrix_root / "matrix-index.json").read_text(encoding="utf-8"))
    assert index["status"] == "Pass"
    assert set(index["version_identities"]) == set(MINORS)
