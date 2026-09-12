"""M4B-LOCK-001 — exact product identity and runtime closure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from sbd.cognition.litert_lm.lock import (
    EXPECTED_PROFILE,
    LLMArtifactLock,
    LLMLockError,
    RuntimeClosure,
    RuntimeFile,
    validate_product_profile,
    load_product_profile,
    profile_digest,
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
    assert lock.product_profile["candidate_id"] == "CAND-LRT-G4E2B-MOBILE-R1"
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


def _release_profile():
    from tests.test_m4b_cfg_001 import release_profile
    return release_profile()


@pytest.mark.parametrize("key", list(EXPECTED_PROFILE), ids=lambda key: "P03-field-" + key)
def test_every_profile_field_is_authenticated_even_with_new_digest(key):
    value = _release_profile()
    original = value[key]
    value[key] = not original if type(original) is bool else "drift"
    value["profile_sha256"] = profile_digest(value)
    with pytest.raises(LLMLockError, match="identity"):
        validate_product_profile(value)


@pytest.mark.parametrize("key", list(EXPECTED_PROFILE), ids=lambda key: "P04-missing-" + key)
def test_missing_profile_field(key):
    value = _release_profile()
    del value[key]
    value["profile_sha256"] = profile_digest(value)
    with pytest.raises(LLMLockError, match="missing or extra"):
        validate_product_profile(value)


@pytest.mark.parametrize("key", ["endpoint", "prewarm_prompt", "system_site", "extra_artifact"], ids=lambda key: "P04-extra-" + key)
def test_extra_profile_field(key):
    value = _release_profile()
    value[key] = "untrusted"
    value["profile_sha256"] = profile_digest(value)
    with pytest.raises(LLMLockError, match="missing or extra"):
        validate_product_profile(value)


@pytest.mark.parametrize("speak,generate", [(None,None),(0,1),(2,1),(True,2),(1,float("inf"))], ids=["M03-null","M03-zero","M03-reversed","M03-bool","M03-infinite"])
def test_invalid_release_memory(speak,generate):
    value = _release_profile()
    value.update(min_mem_available_speak_bytes=speak,min_mem_available_generate_bytes=generate)
    with pytest.raises(LLMLockError):
        value["profile_sha256"] = profile_digest(value)
        validate_product_profile(value)


def test_measurement_is_explicit_only_M03():
    path = ROOT / "requirements/m4b/product-profile.json"
    with pytest.raises(LLMLockError, match="stage"):
        load_product_profile(path)
    value = load_product_profile(path, allow_measurement=True)
    assert value["min_mem_available_generate_bytes"] is None
    assert value["min_mem_available_speak_bytes"] is None


def test_equal_thresholds_are_valid_M01():
    value = _release_profile()
    value["min_mem_available_generate_bytes"] = value["min_mem_available_speak_bytes"]
    value["profile_sha256"] = profile_digest(value)
    assert validate_product_profile(value) == value


def test_duplicate_json_fields_are_rejected_P04(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"profile_id":"x","profile_id":"x"}')
    with pytest.raises(LLMLockError, match="duplicate"):
        load_product_profile(path)


def test_bad_digest_is_rejected_P03():
    value = _release_profile()
    value["profile_sha256"] = "0" * 64
    with pytest.raises(LLMLockError, match="checksum"):
        validate_product_profile(value)


def test_bool_cannot_attest_numeric_profile_P03():
    for key in ("threads","prompt_tokens","protocol","temperature"):
        value = _release_profile()
        value[key] = True
        value["profile_sha256"] = profile_digest(value)
        with pytest.raises(LLMLockError):
            validate_product_profile(value)


@pytest.mark.parametrize("contents", [None,b"\xffPRIVATE-LOCK-CANARY",b'{"PRIVATE-LOCK-CANARY": invalid}'], ids=["V01-missing-file","V01-invalid-utf8","V01-invalid-json"])
def test_lock_errors_hide_private_path_and_document_in_traceback(tmp_path,contents):
    import traceback
    path = tmp_path / "PRIVATE-LOCK-CANARY.json"
    if contents is not None:
        path.write_bytes(contents)
    try:
        LLMArtifactLock.load(path)
    except LLMLockError as error:
        diagnostic = "".join(traceback.format_exception(error))
        assert str(path) not in diagnostic
        assert "PRIVATE-LOCK-CANARY" not in diagnostic
        assert error.__suppress_context__ is True
        assert error.__cause__ is None
    else:
        pytest.fail("invalid artifact accepted")


def test_fifo_is_rejected_without_blocking_P08(tmp_path):
    import os
    path = tmp_path / "not-a-file"
    os.mkfifo(path)
    with pytest.raises(LLMLockError,match="regular"):
        load_product_profile(path)
