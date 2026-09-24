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


def test_fixed_catalog_and_human_variants_are_exact() -> None:
    assert len(RUNNER.CATALOG) == 16
    assert len(set(RUNNER.CATALOG)) == 16
    assert {test_id for test_id, _ in RUNNER.CATALOG} == {
        f"M4C-PI-S{index:02d}" for index in range(1, 10)
    }
    assert RUNNER.HUMAN_VARIANTS == {
        ("M4C-PI-S09", "QUALITY_T02"),
    }


def test_run_parser_accepts_bound_utterance_inputs() -> None:
    args = RUNNER._parser().parse_args([
        "run", "--test-id", "M4C-PI-S02", "--variant", "NORMAL_END",
        "--pv-run-id", "pv-run-001", "--sub-run-id", "sub-run-001",
        "--public-partition", "/tmp/public/pv-run-001/M4C-PI-S02/sub-run-001",
        "--private-partition", "/tmp/private/pv-run-001/M4C-PI-S02/sub-run-001",
        "--binding-manifest", "/tmp/binding.json", "--fresh-setup",
        "--config", "/tmp/config.local.yaml",
        "--utterance-1", "你是誰？", "--utterance-2", "請結束對話。",
    ])
    assert args.utterance_1 == "你是誰？"
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


def test_private_result_requires_human_verdict_only_for_declared_variants() -> None:
    binding = {
        "base_sha": "base",
        "tracked_content_sha256": "a" * 64,
        "pending_paths": [],
        "harness_sha256": "b" * 64,
        "config_sha256": "c" * 64,
        "artifact_digests": {"lock": "d" * 64},
        "target_facts": {
            "target": "pi5-4gb-debian13-aarch64-cp3135",
            "python": "3.13.5", "volume_percent": 25, "network": "disabled",
        },
    }
    value = {
        "schema_version": 1,
        "test_id": "M4C-PI-S09",
        "variant": "QUALITY_T02",
        "sub_run_id": "sub-run-001",
        **RUNNER._tuple(binding),
        "started_monotonic_ns": 1,
        "ended_monotonic_ns": 2,
        "script_status": "Pass",
        "evidence_sha256": "e" * 64,
    }
    args = argparse.Namespace(
        test_id="M4C-PI-S09", variant="QUALITY_T02", sub_run_id="sub-run-001"
    )
    with pytest.raises(RUNNER.RunnerError, match="M4C_USER_RESULT_INVALID"):
        RUNNER._validate_private_result(value, args, binding)
    value["user_result"] = "Pass"
    RUNNER._validate_private_result(value, args, binding)

    value["test_id"], value["variant"] = "M4C-PI-S02", "NORMAL_END"
    args.test_id, args.variant = value["test_id"], value["variant"]
    with pytest.raises(RUNNER.RunnerError, match="M4C_USER_RESULT_FORBIDDEN"):
        RUNNER._validate_private_result(value, args, binding)


def test_pi_invocation_explicitly_selects_rpi_marker() -> None:
    source = (ROOT / "scripts/run-m4c-pv.py").read_text(encoding="utf-8")
    command = source[source.index("command = ["):source.index("completed = subprocess.run")]
    assert '"-m", "rpi"' in command


def test_harness_digest_is_derived_from_declared_bytes(monkeypatch) -> None:
    monkeypatch.setattr(RUNNER, "HARNESS_PATHS", ("scripts/run-m4c-pv.py",))
    first = RUNNER._harness_digest()
    second = RUNNER._canonical_digest([
        ("scripts/run-m4c-pv.py", RUNNER._sha256(ROOT / "scripts/run-m4c-pv.py"))
    ])
    assert first == second


def _binding() -> dict:
    return {
        "base_sha": "base",
        "tracked_content_sha256": "a" * 64,
        "pending_paths": [],
        "harness_sha256": "b" * 64,
        "config_sha256": "c" * 64,
        "artifact_digests": {"lock": "d" * 64},
        "target_facts": {
            "target": "pi5-4gb-debian13-aarch64-cp3135",
            "python": "3.13.5", "volume_percent": 25, "network": "disabled",
        },
    }


def _run_args(tmp_path: Path) -> argparse.Namespace:
    run_id = "pv-run-001"
    (tmp_path / "binding.json").write_text("{}", encoding="utf-8")
    return argparse.Namespace(
        test_id="M4C-PI-S02", variant="NORMAL_END", sub_run_id="sub-run-001",
        pv_run_id=run_id, fresh_setup=True,
        public_partition=tmp_path / "public" / run_id / "M4C-PI-S02" / "sub-run-001",
        private_partition=tmp_path / "private" / run_id / "M4C-PI-S02" / "sub-run-001",
        binding_manifest=tmp_path / "binding.json",
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
    binding = _binding()
    binding["config_sha256"] = RUNNER._sha256(args.config)
    monkeypatch.setattr(RUNNER, "_load_run", lambda value: (binding, public_run, private_run))

    def execute(command, **kwargs):
        assert "tests/test_m4c_pv_rpi.py::test_m4c_product_scenario" in command
        environment = kwargs["env"]
        assert environment["SBD_M4C_UTTERANCE_1"] == "天空為什麼是藍色的？"
        assert environment["SBD_M4C_CONFIG"] == str(args.config.resolve())
        private = Path(environment["SBD_M4C_PRIVATE_PARTITION"])
        value = {
            "schema_version": 1, "test_id": args.test_id, "variant": args.variant,
            "sub_run_id": args.sub_run_id, **RUNNER._tuple(binding),
            "started_monotonic_ns": 1, "ended_monotonic_ns": 2,
            "script_status": "Pass", "evidence_sha256": "e" * 64,
        }
        (private / "result.json").write_text(json.dumps(value), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="1 passed")

    monkeypatch.setattr(RUNNER.subprocess, "run", execute)
    assert RUNNER._run(args) == 0
    card = json.loads((args.public_partition / "result.json").read_text())
    assert card["script_status"] == "Pass"
    assert "user_result" not in card
    assert len(json.loads((public_run / "designations.json").read_text())["attempts"]) == 1


def test_s02_runner_fails_closed_when_private_result_is_missing(tmp_path, monkeypatch) -> None:
    args = _run_args(tmp_path)
    _write_config(args)
    public_run = tmp_path / "public" / args.pv_run_id
    private_run = tmp_path / "private" / args.pv_run_id
    public_run.mkdir(parents=True)
    private_run.mkdir(parents=True)
    monkeypatch.setattr(
        RUNNER, "_load_run", lambda value: (
            {**_binding(), "config_sha256": RUNNER._sha256(args.config)},
            public_run,
            private_run,
        )
    )
    monkeypatch.setattr(
        RUNNER.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout="failed")
    )
    with pytest.raises(RUNNER.RunnerError, match="M4C_PRIVATE_RESULT_MISSING"):
        RUNNER._run(args)


def test_s02_runner_rejects_config_not_bound_to_manifest(tmp_path, monkeypatch) -> None:
    args = _run_args(tmp_path)
    _write_config(args)
    public_run = tmp_path / "public" / args.pv_run_id
    private_run = tmp_path / "private" / args.pv_run_id
    public_run.mkdir(parents=True)
    private_run.mkdir(parents=True)
    monkeypatch.setattr(
        RUNNER, "_load_run", lambda value: (_binding(), public_run, private_run)
    )
    with pytest.raises(RUNNER.RunnerError, match="M4C_CONFIG_CHANGED"):
        RUNNER._run(args)
