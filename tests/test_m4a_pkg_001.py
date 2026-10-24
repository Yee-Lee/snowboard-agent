"""M4A-PKG-001 — tracked closure, safe extraction, and notices."""

from __future__ import annotations

import io
import hashlib
import json
import re
import tarfile
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from sbd.adaptor.audio_lock import AudioArtifactLock
from scripts.m4a_audio_product import (
    ProductFailure,
    RuntimeLock,
    _load_matcha_closure,
    _load_notice_bundle,
    _install_venv,
    _matcha_tree_identity,
    _safe_extract,
    _verify_matcha_tree,
    _verify_flat_inputs,
    _verify_installed_runtime,
    build_whisper,
    install,
)


LOCK_ROOT = Path(__file__).parent.parent / "requirements" / "m4a"


def test_m4a_pkg_001_every_product_row_has_provenance_target_and_notice() -> None:
    value = json.loads((LOCK_ROOT / "audio-artifacts.json").read_text(encoding="utf-8"))
    required = {
        "kind", "name", "version", "filename", "size_bytes", "sha256",
        "source_locator", "notice_ref", "target_os", "target_arch",
        "target_python", "baseline_source_sha",
    }
    assert value["artifacts"]
    assert all(set(row) == required for row in value["artifacts"])
    assert all(row["notice_ref"].startswith("THIRD_PARTY_NOTICES.md#") for row in value["artifacts"])


def test_m4a_pkg_001_whisper_wrapper_is_byte_identical_to_accepted_poc() -> None:
    build = json.loads((LOCK_ROOT / "whispercpp-build.json").read_text(encoding="utf-8"))
    repo = LOCK_ROOT.parent.parent
    expected = {
        "native/m4a_whispercpp_worker/CMakeLists.txt": "a1da74fa0f0a2f8cf94ea178c122b81eea6a4ee50275e9d8445710b19157c1a8",
        "native/m4a_whispercpp_worker/worker.cpp": "d3d0db1724b5882a358a6f6ae6edd08bc71d7ce9b0ce4b43781e72c8688a51dd",
    }
    assert {row["path"]: row["sha256"] for row in build["wrapper_sources"]} == expected
    for row in build["wrapper_sources"]:
        core_source = repo / row["path"]
        assert __import__("hashlib").sha256(core_source.read_bytes()).hexdigest() == row["sha256"]


def test_m4a_pkg_001_notice_inventory_includes_runtime_models_and_accepted_risk() -> None:
    notice = (LOCK_ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8").lower()
    for term in ("silero", "onnx runtime", "numpy", "flatbuffers", "protobuf", "whisper.cpp", "whisper model", "sherpa-onnx", "matcha", "vocos", "espeak-ng"):
        assert term in notice
    assert "accepted risk" in notice
    assert "training-data" in notice and "voice lineage" in notice
    lock = AudioArtifactLock.load(LOCK_ROOT / "audio-artifacts.json")
    assert len(_load_notice_bundle(LOCK_ROOT, lock)) == 64
    headings = {
        re.sub(r"[^a-z0-9 -]", "", line[3:].strip()).replace(" ", "-")
        for line in notice.splitlines()
        if line.startswith("## ")
    }
    for artifact in lock.artifacts:
        assert artifact.notice_ref.partition("#")[2] in headings


def test_m4a_pkg_001_notice_inventory_fails_closed_when_component_is_missing(
    tmp_path: Path,
) -> None:
    lock = AudioArtifactLock.load(LOCK_ROOT / "audio-artifacts.json")
    (tmp_path / "THIRD_PARTY_NOTICES.md").write_text(
        "## Silero VAD\nIncomplete inventory.\n", encoding="utf-8",
    )
    with pytest.raises(ProductFailure, match="incomplete"):
        _load_notice_bundle(tmp_path, lock)


def test_m4a_pkg_001_matcha_archive_has_tracked_extracted_tree_closure() -> None:
    lock = AudioArtifactLock.load(LOCK_ROOT / "audio-artifacts.json")
    closure = _load_matcha_closure(LOCK_ROOT, lock)
    assert closure["archive_sha256"] == lock.require("matcha-archive").sha256
    assert closure["file_count"] == 362
    assert closure["tree_sha256"] == "5e4f8625f9f7d62f9a410d33571ebcd1e3e5b8b0f43f1ebda23512a79e2f3319"
    assert {
        "model-steps-3.onnx", "lexicon.txt", "tokens.txt", "phone-zh.fst",
        "date-zh.fst", "number-zh.fst", "espeak-ng-data/phondata",
    } <= set(closure["required_files"])


def test_m4a_pkg_001_matcha_tree_verifier_rejects_unpacked_component_drift(
    tmp_path: Path,
) -> None:
    root = tmp_path / "matcha-icefall-zh-en"
    (root / "espeak-ng-data").mkdir(parents=True)
    (root / "model-steps-3.onnx").write_bytes(b"model")
    (root / "espeak-ng-data" / "phondata").write_bytes(b"voice-data")
    count, digest, files = _matcha_tree_identity(root)
    closure = {
        "root_dir": root.name,
        "file_count": count,
        "tree_sha256": digest,
        "required_files": files,
    }
    assert _verify_matcha_tree(root, closure) == digest
    (root / "espeak-ng-data" / "phondata").write_bytes(b"drift")
    with pytest.raises(ProductFailure, match="tree identity"):
        _verify_matcha_tree(root, closure)


def test_m4a_pkg_001_safe_extract_rejects_traversal_and_symlink(tmp_path: Path) -> None:
    for index, member in enumerate((tarfile.TarInfo("../escape"), tarfile.TarInfo("unsafe-link"))):
        archive = tmp_path / f"unsafe-{index}.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            if index == 0:
                member.size = 1
                bundle.addfile(member, io.BytesIO(b"x"))
            else:
                member.type = tarfile.SYMTYPE
                member.linkname = "/etc/passwd"
                bundle.addfile(member)
        with pytest.raises(ProductFailure, match="unsafe"):
            _safe_extract(archive, tmp_path / f"out-{index}", "r:gz")


def test_m4a_pkg_001_input_inventory_rejects_extra_before_artifact_use(tmp_path: Path) -> None:
    lock = AudioArtifactLock.load(LOCK_ROOT / "audio-artifacts.json")
    (tmp_path / "unexpected").write_bytes(b"x")
    with pytest.raises(ProductFailure, match="inventory"):
        _verify_flat_inputs(tmp_path, lock, ("silero-model",))
    assert {path.name for path in tmp_path.iterdir()} == {"unexpected"}


def test_m4a_pkg_001_build_failure_removes_new_staging_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.m4a_audio_product as product_module

    source = tmp_path / "whisper.cpp-v1.9.2.tar.gz"
    build_root = tmp_path / "build-staging"
    output = tmp_path / "worker"
    artifact = SimpleNamespace(verify=lambda path: None)
    product = SimpleNamespace(require=lambda name: artifact)
    lock = {
        "source_filename": source.name,
        "source_sha256": "a" * 64,
    }

    def fail_extract(archive: Path, destination: Path, mode: str) -> Path:
        destination.mkdir(parents=True)
        (destination / "partial").write_bytes(b"partial")
        raise ProductFailure("controlled extraction failure")

    monkeypatch.setattr(product_module, "_assert_offline", lambda: None)
    monkeypatch.setattr(product_module.AudioArtifactLock, "load", lambda path: product)
    monkeypatch.setattr(product_module, "_load_build_lock", lambda path: lock)
    monkeypatch.setattr(product_module, "_sha256", lambda path: "a" * 64)
    monkeypatch.setattr(product_module, "_safe_extract", fail_extract)
    with pytest.raises(ProductFailure, match="extraction"):
        build_whisper(SimpleNamespace(
            lock_root=LOCK_ROOT, source_archive=source,
            build_root=build_root, output=output,
        ))
    assert not build_root.exists() and not output.exists()


def test_m4a_pkg_001_build_success_captures_tool_output_and_records_binary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.m4a_audio_product as product_module

    source = tmp_path / "whisper.cpp-v1.9.2.tar.gz"
    build_root = tmp_path / "build-staging"
    output = tmp_path / "worker"
    artifact = SimpleNamespace(verify=lambda path: None)
    product = SimpleNamespace(require=lambda name: artifact)
    lock = {
        "source_filename": source.name,
        "source_sha256": "a" * 64,
        "cmake_options": ["-DCPU_ONLY=ON"],
    }
    calls: list[dict[str, object]] = []

    def extract(archive: Path, destination: Path, mode: str) -> Path:
        root = destination / "whisper.cpp"
        root.mkdir(parents=True)
        (root / "CMakeLists.txt").write_text("fixture", encoding="utf-8")
        (root / "LICENSE").write_text("fixture", encoding="utf-8")
        return root

    def run(argv, **kwargs):
        calls.append(kwargs)
        if "--build" in argv:
            built = build_root / "build" / "bin" / "m4a-whispercpp-worker"
            built.parent.mkdir(parents=True)
            built.write_bytes(b"binary")
        return subprocess.CompletedProcess(argv, 0, "private build path", "private error")

    monkeypatch.setattr(product_module, "_assert_offline", lambda: None)
    monkeypatch.setattr(product_module.AudioArtifactLock, "load", lambda path: product)
    monkeypatch.setattr(product_module, "_load_build_lock", lambda path: lock)
    monkeypatch.setattr(
        product_module, "_sha256",
        lambda path: (
            "a" * 64 if path == source.resolve()
            else hashlib.sha256(path.read_bytes()).hexdigest()
        ),
    )
    monkeypatch.setattr(product_module, "_safe_extract", extract)
    monkeypatch.setattr(product_module, "_wrapper_sources_sha256", lambda value: "b" * 64)
    monkeypatch.setattr(product_module.subprocess, "run", run)
    result = build_whisper(SimpleNamespace(
        lock_root=LOCK_ROOT, source_archive=source,
        build_root=build_root, output=output,
    ))
    assert result["status"] == "Pass" and output.read_bytes() == b"binary"
    assert output.with_suffix(".json").is_file()
    assert len(calls) == 2
    assert all(call["capture_output"] is True and call["text"] is True for call in calls)


def test_m4a_pkg_001_install_preflight_failure_removes_staging_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.m4a_audio_product as product_module

    install_root = tmp_path / "product"
    monkeypatch.setattr(product_module, "_assert_offline", lambda: None)
    monkeypatch.setattr(product_module, "_verify_flat_inputs", lambda *args: None)
    monkeypatch.setattr(
        product_module,
        "_target_python_identity",
        lambda *args: (_ for _ in ()).throw(ProductFailure("wrong target")),
    )
    with pytest.raises(ProductFailure, match="wrong target"):
        install(SimpleNamespace(
            lock_root=LOCK_ROOT, input_root=tmp_path / "inputs",
            install_root=install_root, python=Path("/usr/bin/python3"),
        ))
    assert not install_root.exists()
    assert not list(tmp_path.glob(".product.staging-*"))


def test_m4a_pkg_001_install_subprocess_output_is_captured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    destination = tmp_path / "runtime"

    def run(argv, **kwargs):
        calls.append(kwargs)
        if argv[2:4] == ["venv", "--copies"]:
            (destination / "bin").mkdir(parents=True)
            (destination / "pyvenv.cfg").write_text(
                "include-system-site-packages = false\n", encoding="utf-8",
            )
        return subprocess.CompletedProcess(argv, 0, "private build path", "private error")

    monkeypatch.setattr(subprocess, "run", run)
    _install_venv(Path("/python"), destination, [tmp_path / "wheel.whl"], {})
    assert len(calls) == 2
    assert all(call["capture_output"] is True and call["text"] is True for call in calls)


def test_m4a_pkg_001_installed_runtime_requires_target_identity_and_exact_packages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter((
        subprocess.CompletedProcess([], 0, '{"implementation":"CPython","minor":"3.13","machine":"aarch64"}\n', ""),
        subprocess.CompletedProcess([], 0, '[{"name":"numpy","version":"2.5.2"},{"name":"pip","version":"26.0"}]\n', ""),
    ))
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: next(responses))
    runtime = RuntimeLock(
        runtime="tts", interpreter="CPython 3.13", arch="aarch64",
        profile="matcha-zh-en-default-sid-0", baseline_source_sha="1" * 40,
        wheels=({"distribution": "numpy", "version": "2.5.2"},),
    )
    _verify_installed_runtime(Path("/product/tts/bin/python"), runtime, {})


@pytest.mark.parametrize(
    "packages",
    [
        '[{"name":"numpy","version":"2.5.1"}]',
        '[{"name":"numpy","version":"2.5.2"},{"name":"requests","version":"2"}]',
        '[]',
    ],
)
def test_m4a_pkg_001_installed_runtime_rejects_version_extra_or_missing(
    monkeypatch: pytest.MonkeyPatch, packages: str,
) -> None:
    responses = iter((
        subprocess.CompletedProcess([], 0, '{"implementation":"CPython","minor":"3.13","machine":"aarch64"}', ""),
        subprocess.CompletedProcess([], 0, packages, ""),
    ))
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: next(responses))
    runtime = RuntimeLock(
        runtime="tts", interpreter="CPython 3.13", arch="aarch64",
        profile="matcha-zh-en-default-sid-0", baseline_source_sha="1" * 40,
        wheels=({"distribution": "numpy", "version": "2.5.2"},),
    )
    with pytest.raises(ProductFailure, match="inventory"):
        _verify_installed_runtime(Path("/product/tts/bin/python"), runtime, {})
