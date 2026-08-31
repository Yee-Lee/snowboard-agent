"""M4B-LOCK-001 — exact product identity and runtime closure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from sbd.cognition.litert_lm.lock import (
    EXPECTED_PRODUCT_CONFIG,
    LLMArtifactLock,
    LLMLockError,
    RuntimeClosure,
    RuntimeFile,
    validate_product_config,
)


ROOT = Path(__file__).parent.parent
LOCK = ROOT / "requirements/m4b/llm-artifacts.json"
MANIFEST = ROOT / "requirements/m4b/llm-runtime-rpi-cp313.json"


def _mutated(tmp_path: Path, mutate) -> Path:
    value = json.loads(LOCK.read_text(encoding="utf-8"))
    mutate(value)
    path = tmp_path / "lock.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_m4b_lock_001_tracked_lock_and_closure_are_exact() -> None:
    lock = LLMArtifactLock.load(LOCK, repo_root=ROOT)
    assert lock.identity.candidate_id == "CAND-LRT-G4E2B-MOBILE-R1"
    assert lock.runtime_closure is not None
    assert len(lock.runtime_closure.files) == 14
    assert lock.runtime_closure.digest == hashlib.sha256(MANIFEST.read_bytes()).hexdigest()


@pytest.mark.parametrize("section", [
    "lock", "poc_reference", "candidate", "runtime", "model",
    "product_profile", "runtime_closure", "licenses",
])
@pytest.mark.parametrize("change", ["missing", "extra", "wrong"])
def test_m4b_lock_001_rejects_every_nested_shape_and_identity_mutation(
    tmp_path: Path, section: str, change: str,
) -> None:
    def mutate(value):
        target = value[section]
        key = next(iter(target))
        if change == "missing":
            target.pop(key)
        elif change == "extra":
            target["unexpected"] = 1
        else:
            target[key] = "drift" if not isinstance(target[key], str) else target[key] + "x"

    with pytest.raises(LLMLockError):
        LLMArtifactLock.load(_mutated(tmp_path, mutate))


def test_m4b_lock_001_rejects_top_level_extra_and_absolute_path(tmp_path: Path) -> None:
    for mutate in (
        lambda value: value.update(extra={}),
        lambda value: value["licenses"].update(notice_locator="/tmp/private"),
    ):
        with pytest.raises(LLMLockError):
            LLMArtifactLock.load(_mutated(tmp_path, mutate))


def test_m4b_lock_001_manifest_digest_and_entry_shape_fail_closed(tmp_path: Path) -> None:
    digest = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    with pytest.raises(LLMLockError, match="checksum"):
        RuntimeClosure.load(MANIFEST, expected_digest="0" * 64)
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    value["files"][0]["extra"] = True
    changed = tmp_path / "manifest.json"
    changed.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(LLMLockError, match="file entry"):
        RuntimeClosure.load(changed, expected_digest=hashlib.sha256(changed.read_bytes()).hexdigest())
    assert len(digest) == 64


def test_m4b_lock_001_install_inventory_rejects_missing_extra_and_symlink(tmp_path: Path) -> None:
    payload = b"runtime"
    path = tmp_path / "manifest.json"
    closure = RuntimeClosure(path, "a" * 64, (
        RuntimeFile("payload", len(payload), hashlib.sha256(payload).hexdigest()),
    ))
    root = tmp_path / "runtime"
    root.mkdir()
    with pytest.raises(LLMLockError, match="missing"):
        closure.verify_install(root)
    (root / "extra").write_bytes(payload)
    with pytest.raises(LLMLockError, match="extra"):
        closure.verify_install(root)
    (root / "extra").unlink()
    (root / "unsafe").symlink_to(path)
    with pytest.raises(LLMLockError, match="unsafe"):
        closure.verify_install(root)


def test_m4b_lock_001_manifest_cannot_add_interpreter_to_product_payload(tmp_path: Path) -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    value["files"].append({
        "relative_path": "bin/python3.13",
        "size_bytes": 1,
        "sha256": hashlib.sha256(b"x").hexdigest(),
    })
    changed = tmp_path / "manifest.json"
    changed.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(LLMLockError, match="product payload"):
        RuntimeClosure.load(
            changed,
            expected_digest=hashlib.sha256(changed.read_bytes()).hexdigest(),
        )


def _product_config() -> dict[str, object]:
    return {
        **EXPECTED_PRODUCT_CONFIG,
        "runtime_path": "/tmp/llm-poc-provenance/runtime",
        "model_path": "/tmp/llm-poc-provenance/model",
    }


def test_m4b_lock_001_product_config_cross_checks_every_frozen_field_without_opening_poc_paths() -> None:
    value = _product_config()
    assert validate_product_config(value) == value
    for key, original in EXPECTED_PRODUCT_CONFIG.items():
        changed = _product_config()
        if original is None:
            changed[key] = "fallback"
        elif type(original) is bool:
            changed[key] = not original
        elif type(original) in (int, float):
            changed[key] = original + 1
        else:
            changed[key] = str(original) + "-drift"
        with pytest.raises(LLMLockError, match="identity"):
            validate_product_config(changed)


@pytest.mark.parametrize("path", ["relative", "", "bad\x00path"])
def test_m4b_lock_001_product_config_rejects_non_absolute_provenance_path(path: str) -> None:
    value = _product_config()
    value["runtime_path"] = path
    with pytest.raises(LLMLockError, match="provenance"):
        validate_product_config(value)


def test_m4b_lock_001_product_config_rejects_missing_or_extra_field() -> None:
    for value in (
        {key: item for key, item in _product_config().items() if key != "threads"},
        {**_product_config(), "unexpected": True},
    ):
        with pytest.raises(LLMLockError, match="missing or extra"):
            validate_product_config(value)
