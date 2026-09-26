"""Portable fail-closed checks for the M4C Pi coordinator."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_m4c_pv", ROOT / "scripts/run-m4c-pv.py"
)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_fixed_catalog_is_exact_and_has_no_human_variants() -> None:
    assert RUNNER.CATALOG == (
        ("M4C-PI-S01", "START_IDLE"),
        ("M4C-PI-S02", "NORMAL_END_B2"),
        ("M4C-PI-S03", "TWO_TIMEOUTS"),
        ("M4C-PI-S04", "PERCEPTION"),
        ("M4C-PI-S04", "THINK"),
        ("M4C-PI-S04", "ACTION"),
        ("M4C-PI-S05", "APP_EXIT"),
    )
    assert not hasattr(RUNNER, "HUMAN_VARIANTS")


def test_run_parser_accepts_utterance_inputs_without_binding_manifest() -> None:
    args = RUNNER._parser().parse_args([
        "run", "--test-id", "M4C-PI-S02", "--variant", "NORMAL_END_B2",
        "--pv-run-id", "pv-run-001", "--sub-run-id", "sub-run-001",
        "--public-partition", "/tmp/public/pv-run-001/M4C-PI-S02/sub-run-001",
        "--private-partition", "/tmp/private/pv-run-001/M4C-PI-S02/sub-run-001",
        "--fresh-setup", "--config", "/tmp/config.local.yaml",
        "--utterance-1", "天空為什麼是藍色的？", "--utterance-2", "請結束對話。",
    ])
    assert args.utterance_1 == "天空為什麼是藍色的？"
    assert args.utterance_2 == "請結束對話。"
    assert args.fresh_setup is True


@pytest.mark.parametrize("value", [
    {"transcript": "private"},
    {"nested": [{"prompt": "private"}]},
    {"value": "line one\nline two"},
])
def test_public_privacy_scan_rejects_private_content(value: object) -> None:
    with pytest.raises(RUNNER.RunnerError, match="M4C_PUBLIC_PRIVACY_VIOLATION"):
        RUNNER._privacy_scan(value)


def test_private_result_forbids_human_verdict() -> None:
    value = {
        "schema_version": 1,
        "test_id": "M4C-PI-S02",
        "variant": "NORMAL_END_B2",
        "sub_run_id": "sub-run-001",
        "started_monotonic_ns": 1,
        "ended_monotonic_ns": 2,
        "script_status": "Pass",
        "public_evidence": {"understandable": True},
    }
    args = argparse.Namespace(
        test_id="M4C-PI-S02", variant="NORMAL_END_B2", sub_run_id="sub-run-001"
    )
    value["user_result"] = "Pass"
    with pytest.raises(RUNNER.RunnerError, match="M4C_USER_RESULT_FORBIDDEN"):
        RUNNER._validate_private_result(value, args)


def test_pi_invocation_explicitly_selects_rpi_marker() -> None:
    source = (ROOT / "scripts/run-m4c-pv.py").read_text(encoding="utf-8")
    command = source[source.index("command = ["):source.index("completed = subprocess.run")]
    assert '"-m", "rpi"' in command


def _run_args(tmp_path: Path) -> argparse.Namespace:
    run_id = "pv-run-001"
    return argparse.Namespace(
        test_id="M4C-PI-S02", variant="NORMAL_END_B2", sub_run_id="sub-run-001",
        pv_run_id=run_id, fresh_setup=True,
        public_partition=tmp_path / "public" / run_id / "M4C-PI-S02" / "sub-run-001",
        private_partition=tmp_path / "private" / run_id / "M4C-PI-S02" / "sub-run-001",
        config=tmp_path / "config.local.yaml",
        utterance=None, utterance_1="天空為什麼是藍色的？", utterance_2="請結束對話。",
    )


def _write_config(args: argparse.Namespace) -> None:
    args.config.write_text("test config", encoding="utf-8")


def test_s02_runner_smoke_writes_one_automatic_atomic_result(tmp_path, monkeypatch) -> None:
    args = _run_args(tmp_path)
    _write_config(args)
    public_run = tmp_path / "public" / args.pv_run_id
    private_run = tmp_path / "private" / args.pv_run_id
    public_run.mkdir(parents=True)
    private_run.mkdir(parents=True)
    monkeypatch.setattr(RUNNER, "_load_run", lambda value: (public_run, private_run))

    def execute(command, **kwargs):
        assert "tests/test_m4c_pv_rpi.py::test_m4c_product_scenario" in command
        environment = kwargs["env"]
        assert environment["SBD_M4C_UTTERANCE_1"] == "天空為什麼是藍色的？"
        assert environment["SBD_M4C_CONFIG"] == str(args.config.resolve())
        private = Path(environment["SBD_M4C_PRIVATE_PARTITION"])
        value = {
            "schema_version": 1, "test_id": args.test_id, "variant": args.variant,
            "sub_run_id": args.sub_run_id,
            "started_monotonic_ns": 1, "ended_monotonic_ns": 2,
            "script_status": "Pass",
            "public_evidence": {"product_behavior_passed": True},
        }
        (private / "result.json").write_text(json.dumps(value), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="1 passed")

    monkeypatch.setattr(RUNNER.subprocess, "run", execute)
    assert RUNNER._run(args) == 0
    card = json.loads((args.public_partition / "result.json").read_text())
    assert card["script_status"] == "Pass"
    assert card["public_evidence"] == {"product_behavior_passed": True}
    assert "user_result" not in card
    assert not any("sha" in key or "digest" in key for key in card)
    assert len(json.loads((public_run / "designations.json").read_text())["attempts"]) == 1


def test_s02_runner_fails_closed_when_private_result_is_missing(tmp_path, monkeypatch) -> None:
    args = _run_args(tmp_path)
    _write_config(args)
    public_run = tmp_path / "public" / args.pv_run_id
    private_run = tmp_path / "private" / args.pv_run_id
    public_run.mkdir(parents=True)
    private_run.mkdir(parents=True)
    monkeypatch.setattr(RUNNER, "_load_run", lambda value: (public_run, private_run))
    monkeypatch.setattr(
        RUNNER.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout="failed")
    )
    with pytest.raises(RUNNER.RunnerError, match="M4C_PRIVATE_RESULT_MISSING"):
        RUNNER._run(args)


def test_private_result_rejects_public_evidence_privacy_leak() -> None:
    value = {
        "schema_version": 1,
        "test_id": "M4C-PI-S02",
        "variant": "NORMAL_END_B2",
        "sub_run_id": "sub-run-001",
        "started_monotonic_ns": 1,
        "ended_monotonic_ns": 2,
        "script_status": "Pass",
        "public_evidence": {"text": "private"},
    }
    args = argparse.Namespace(
        test_id="M4C-PI-S02", variant="NORMAL_END_B2", sub_run_id="sub-run-001"
    )
    with pytest.raises(RUNNER.RunnerError, match="M4C_PUBLIC_PRIVACY_VIOLATION"):
        RUNNER._validate_private_result(value, args)


def test_finalizer_requires_and_accepts_exact_seven_entry_catalog(
    tmp_path: Path, monkeypatch,
) -> None:
    public_run = tmp_path / "public" / "pv-run-001"
    public_run.mkdir(parents=True)
    attempts = []
    for index, (test_id, variant) in enumerate(RUNNER.CATALOG, start=1):
        sub_run_id = f"sub-run-{index:03d}"
        attempt_id = f"{test_id}-{variant}-{sub_run_id}"
        card_path = public_run / test_id / sub_run_id / "result.json"
        card_path.parent.mkdir(parents=True)
        card = {
            "schema_version": 1,
            "test_id": test_id,
            "variant": variant,
            "sub_run_id": sub_run_id,
            "started_monotonic_ns": index,
            "ended_monotonic_ns": index + 1,
            "script_status": "Pass",
            "public_evidence": {"passed": True},
            "attempt_id": attempt_id,
            "designated": True,
            "superseded_by": None,
        }
        card_path.write_text(json.dumps(card), encoding="utf-8")
        attempts.append({
            "attempt_id": attempt_id,
            "test_id": test_id,
            "variant": variant,
            "sub_run_id": sub_run_id,
            "card": str(card_path.relative_to(public_run)),
            "designated": True,
            "superseded_by": None,
        })
    (public_run / "designations.json").write_text(json.dumps({
        "schema_version": 1,
        "pv_run_id": "pv-run-001",
        "attempts": attempts,
    }), encoding="utf-8")
    monkeypatch.setattr(RUNNER, "_load_run", lambda args: (public_run, tmp_path / "private"))

    args = argparse.Namespace(pv_run_id="pv-run-001")
    assert RUNNER._finalize(args) == 0
    final = json.loads((public_run / "final.json").read_text(encoding="utf-8"))
    assert final["pv_status"] == "Pass"
    assert final["designated_count"] == 7
