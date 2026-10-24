"""Portable guards for the M4-ERR Raspberry Pi Verify runner."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from sbd.core.candidate_identity import DEFAULT_SCOPES


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_m4_err_pv", ROOT / "scripts/run-m4-err-pv.py"
)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_m4_err_pv_runner_has_exact_full_test_id_namespace() -> None:
    assert tuple(RUNNER.TEST_NODES) == (
        "M4-ERR-PV-001",
        "M4-ERR-PV-002",
        "M4-ERR-PV-003",
        "M4-ERR-PV-004",
        "M4-ERR-PV-005",
    )
    assert len(set(RUNNER.TEST_NODES.values())) == 5
    assert all(node.startswith("tests/test_m4_err_pv_rpi.py::")
               for node in RUNNER.TEST_NODES.values())


def test_m4_err_candidate_identity_protects_runner_and_authority() -> None:
    assert "src" in DEFAULT_SCOPES
    assert not any(scope.startswith("src/") for scope in DEFAULT_SCOPES)
    assert "scripts" in DEFAULT_SCOPES
    assert "docs/implement/ch_m4_error_handling.md" in DEFAULT_SCOPES
    assert "docs/test_spec/test_spec_M4_ERR.md" in DEFAULT_SCOPES


def test_m4_err_artifact_identity_is_closed_and_nonempty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifacts = {}
    for name in ("asr_lock", "llm_lock", "llm_profile", "tts_lock"):
        path = tmp_path / name
        path.write_text(name, encoding="utf-8")
        artifacts[name] = path
    config = SimpleNamespace(
        perception=SimpleNamespace(listen=SimpleNamespace(adapter=SimpleNamespace(
            artifact_lock_path=artifacts["asr_lock"],
        ))),
        cognition=SimpleNamespace(llm=SimpleNamespace(
            artifact_lock_path=artifacts["llm_lock"],
            product_profile_path=artifacts["llm_profile"],
        )),
        action=SimpleNamespace(tts=SimpleNamespace(
            artifact_lock_path=artifacts["tts_lock"],
        )),
    )
    monkeypatch.setattr(RUNNER, "load_config", lambda **kwargs: config)
    identity = RUNNER._artifact_identity(tmp_path / "config.yaml")
    assert set(identity) == set(artifacts)
    assert all(len(digest) == 64 for digest in identity.values())


@pytest.mark.parametrize(
    ("body", "expected"),
    (
        ("<testsuite><testcase name='x'/></testsuite>", {"passed": 1, "failed": 0, "skipped": 0}),
        ("<testsuite><testcase name='x'><failure/></testcase></testsuite>", {"passed": 0, "failed": 1, "skipped": 0}),
        ("<testsuite><testcase name='x'><skipped/></testcase></testsuite>", {"passed": 0, "failed": 0, "skipped": 1}),
    ),
)
def test_m4_err_pv_runner_audits_one_junit_case(
    tmp_path: Path, body: str, expected: dict[str, int]
) -> None:
    junit = tmp_path / "junit.xml"
    junit.write_text(body, encoding="utf-8")
    assert RUNNER._junit_counts(junit) == expected
    junit.write_text("<testsuite/>", encoding="utf-8")
    with pytest.raises(RUNNER.RunnerError, match="CASE_COUNT"):
        RUNNER._junit_counts(junit)


def test_m4_err_pv_finalize_requires_all_five_same_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binding = {
        "content_sha256": "a" * 64,
        "config_sha256": "b" * 64,
        "artifact_identity": {"lock": "c" * 64},
    }
    monkeypatch.setattr(RUNNER, "_verify_binding", lambda root, run_id: binding)
    for test_id in RUNNER.TEST_NODES:
        if test_id in RUNNER.OBSERVATION_REQUIRED:
            _write(tmp_path / "private" / test_id / "product-observation.json", {
                "test_id": test_id,
            })
        card = {
            "run_id": "M4-ERR-run-1",
            "test_id": test_id,
            "status": "Pass",
            **binding,
        }
        observation = RUNNER._observation_identity(tmp_path, test_id)
        if observation is not None:
            card["product_observation"] = observation
        _write(tmp_path / "public" / test_id / "result.json", card)
    args = SimpleNamespace(output=tmp_path, run_id="M4-ERR-run-1")
    assert RUNNER._finalize(args) == 0
    final = json.loads((tmp_path / "public/final.json").read_text(encoding="utf-8"))
    assert final["status"] == "Pass" and final["test_ids"] == list(RUNNER.TEST_NODES)


def test_m4_err_pv_finalize_rejects_failed_or_mixed_card(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binding = {
        "content_sha256": "a" * 64,
        "config_sha256": "b" * 64,
        "artifact_identity": {"lock": "c" * 64},
    }
    monkeypatch.setattr(RUNNER, "_verify_binding", lambda root, run_id: binding)
    for index, test_id in enumerate(RUNNER.TEST_NODES):
        if test_id in RUNNER.OBSERVATION_REQUIRED:
            _write(tmp_path / "private" / test_id / "product-observation.json", {
                "test_id": test_id,
            })
        card = {
            "run_id": "M4-ERR-run-2",
            "test_id": test_id,
            "status": "Fail" if index == 3 else "Pass",
            **binding,
        }
        observation = RUNNER._observation_identity(tmp_path, test_id)
        if observation is not None:
            card["product_observation"] = observation
        _write(tmp_path / "public" / test_id / "result.json", card)
    with pytest.raises(RUNNER.RunnerError, match="CARD_INVALID"):
        RUNNER._finalize(SimpleNamespace(output=tmp_path, run_id="M4-ERR-run-2"))


def test_m4_err_pv_observation_is_required_and_content_bound(tmp_path: Path) -> None:
    with pytest.raises(RUNNER.RunnerError, match="OBSERVATION_MISSING"):
        RUNNER._observation_identity(tmp_path, "M4-ERR-PV-001")
    observation = tmp_path / "private/M4-ERR-PV-001/product-observation.json"
    _write(observation, {"structured_log": {"code": "AUDIO_CAPTURE_FAILED"}})
    identity = RUNNER._observation_identity(tmp_path, "M4-ERR-PV-001")
    assert identity is not None
    assert identity["locator"] == "private/M4-ERR-PV-001/product-observation.json"
    assert len(identity["sha256"]) == 64
    assert RUNNER._observation_identity(tmp_path, "M4-ERR-PV-003") is None
