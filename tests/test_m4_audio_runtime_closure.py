"""Regression tests for the M4a runtime closure verifier."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.m4_audio_runtime_closure import (
    ClosureError,
    SCHEMA,
    _manifest_packages,
    _verify_installed_packages,
    verify_wheel_directory,
)


def _package(path: Path) -> dict[str, object]:
    return {
        "distribution": "example-package",
        "version": "1.2.3",
        "filename": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size": path.stat().st_size,
        "source_locator": "controlled://audio/example-package-1.2.3.whl",
        "license_reference": "Example-License",
        "import_name": "example_package",
    }


def test_m4a_runtime_manifest_rejects_missing_provenance_fields(tmp_path: Path) -> None:
    wheel = tmp_path / "example_package-1.2.3-py3-none-any.whl"
    wheel.write_bytes(b"fixture-wheel")
    package = _package(wheel)
    del package["source_locator"]
    with pytest.raises(ClosureError, match="source_locator"):
        _manifest_packages({"schema": SCHEMA, "packages": [package]})


def test_m4a_runtime_wheel_inventory_is_exact_and_checksum_locked(tmp_path: Path) -> None:
    wheel = tmp_path / "example_package-1.2.3-py3-none-any.whl"
    wheel.write_bytes(b"fixture-wheel")
    packages = _manifest_packages({"schema": SCHEMA, "packages": [_package(wheel)]})
    verify_wheel_directory(tmp_path, packages)
    (tmp_path / "unexpected-1.0-py3-none-any.whl").write_bytes(b"unexpected")
    with pytest.raises(ClosureError, match="extra"):
        verify_wheel_directory(tmp_path, packages)


def test_m4a_runtime_installed_package_check_reports_only_real_mismatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packages = _manifest_packages({
        "schema": SCHEMA,
        "packages": [{
            "distribution": "example-package",
            "version": "1.2.3",
            "filename": "example.whl",
            "sha256": "a" * 64,
            "size": 1,
            "source_locator": "controlled://example",
            "license_reference": "Example-License",
            "import_name": "example_package",
        }],
    })
    monkeypatch.setattr(
        "scripts.m4_audio_runtime_closure._run_json",
        lambda command: [
            {"name": "example-package", "version": "1.2.3"},
            {"name": "pip", "version": "25.1"},
        ],
    )
    _verify_installed_packages(Path("/fixture/python"), packages)
