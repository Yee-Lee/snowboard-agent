"""Portable fail-closed checks for the M4C Pi coordinator."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_m4c_pv", ROOT / "scripts/run-m4c-pv.py"
)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_fixed_catalog_and_human_variants_are_exact() -> None:
    assert len(RUNNER.CATALOG) == 17
    assert len(set(RUNNER.CATALOG)) == 17
    assert {test_id for test_id, _ in RUNNER.CATALOG} == {
        f"M4C-PI-S{index:02d}" for index in range(1, 10)
    }
    assert RUNNER.HUMAN_VARIANTS == {
        ("M4C-PI-S02", "NORMAL_END"),
        ("M4C-PI-S09", "QUALITY_T02"),
    }


def test_run_parser_accepts_bound_utterance_inputs() -> None:
    args = RUNNER._parser().parse_args([
        "run", "--test-id", "M4C-PI-S02", "--variant", "NORMAL_END",
        "--pv-run-id", "pv-run-001", "--sub-run-id", "sub-run-001",
        "--public-partition", "/tmp/public/pv-run-001/M4C-PI-S02/sub-run-001",
        "--private-partition", "/tmp/private/pv-run-001/M4C-PI-S02/sub-run-001",
        "--binding-manifest", "/tmp/binding.json", "--fresh-setup",
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
        "test_id": "M4C-PI-S02",
        "variant": "NORMAL_END",
        "sub_run_id": "sub-run-001",
        **RUNNER._tuple(binding),
        "started_monotonic_ns": 1,
        "ended_monotonic_ns": 2,
        "script_status": "Pass",
        "evidence_sha256": "e" * 64,
    }
    args = argparse.Namespace(
        test_id="M4C-PI-S02", variant="NORMAL_END", sub_run_id="sub-run-001"
    )
    with pytest.raises(RUNNER.RunnerError, match="M4C_USER_RESULT_INVALID"):
        RUNNER._validate_private_result(value, args, binding)
    value["user_result"] = "Pass"
    RUNNER._validate_private_result(value, args, binding)

    value["test_id"], value["variant"] = "M4C-PI-S01", "START_IDLE"
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
