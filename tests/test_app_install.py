"""Offline install deployment paths and safety; real runtime proof is on Pi."""
from pathlib import Path
import subprocess

import pytest
import yaml

from scripts.install_app import install


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    source = tmp_path / "source"
    for name in ("src", "requirements", "scripts"):
        (source / name).mkdir(parents=True)
    (source / "src/example.py").write_text("value = 1")
    (source / "scripts/run-app.sh").write_text("#!/bin/sh\nexit 0\n")
    for name in ("controller", "llm-runtime"):
        runtime = tmp_path / name
        (runtime / "bin").mkdir(parents=True)
        (runtime / "bin/python").write_text("python")
        (runtime / "pyvenv.cfg").write_text("runtime")
        (runtime / "__editable__old.pth").write_text("old development path")
    assets = tmp_path / "assets"
    assets.mkdir()
    for name in ("model", "profile", "lock", "display"):
        (assets / name).write_text(name)
    raw = {"cognition": {"llm": {"driver": "litert_lm",
               "runtime_python": str(tmp_path / "llm-runtime/bin/python"),
               "model_path": str(assets / "model"), "product_profile_path": str(assets / "profile"),
               "artifact_lock_path": str(assets / "lock")}},
           "perception": {"listen": {"adapter": {"driver": "whispercpp",
               "artifact_lock_path": str(assets / "lock")}}},
           "action": {"tts": {"driver": "sherpa_matcha", "artifact_lock_path": str(assets / "lock")}},
           "core": {"display": {"driver": "ssd1351", "native_library_path": str(assets / "display")}}}
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump(raw))
    return source, config, tmp_path / "controller/bin/python", tmp_path / "installed"


def test_install_copies_runtime_assets_and_removes_development_references(inputs):
    source, config, python, prefix = inputs
    original = config.read_bytes()
    install(*inputs)
    raw = yaml.safe_load((prefix / "config.local.yaml").read_text())
    assert raw["cognition"]["llm"]["runtime_python"] == str(prefix / "runtimes/llm/bin/python")
    assert raw["cognition"]["llm"]["model_path"] == str(prefix / "artifacts/llm/model")
    assert Path(raw["cognition"]["llm"]["artifact_lock_path"]).parents[2] == prefix
    assert Path(raw["perception"]["listen"]["adapter"]["artifact_lock_path"]).parent == prefix / "requirements/m4a"
    assert Path(raw["action"]["tts"]["artifact_lock_path"]).parent == prefix / "requirements/m4a"
    assert raw["core"]["display"]["native_library_path"] == str(prefix / "native/libdisplay.so")
    assert raw["log"]["file"] == str(prefix / "logs/application.log")
    assert str(source.parent / "assets") not in (prefix / "config.local.yaml").read_text()
    assert (prefix / ".venv/bin/python").read_text() == "python"
    assert not list(prefix.rglob("__editable__*"))
    assert config.read_bytes() == original
    assert (prefix / "run.sh").stat().st_mode & 0o111
    assert (prefix / "config.local.yaml").stat().st_mode & 0o777 == 0o600


def test_existing_install_is_not_overwritten(inputs):
    *_, prefix = inputs
    prefix.mkdir()
    (prefix / "user-config").write_text("keep")
    with pytest.raises(ValueError, match="DESTINATION_EXISTS"):
        install(*inputs)
    assert (prefix / "user-config").read_text() == "keep"


def test_fixed_entry_selects_release_without_overwriting_original_source(inputs):
    *_, prefix = inputs
    install(*inputs)
    release = prefix / "releases/fix"
    (release / "scripts").mkdir(parents=True)
    launcher = release / "scripts/run-app.sh"
    launcher.write_text('#!/bin/sh\n[ "$1" = "--help" ] && exit 23\nexit 1\n')
    launcher.chmod(0o755)
    (prefix / "current").symlink_to(release)
    result = subprocess.run([str(prefix / "run.sh"), "--help"], timeout=5)
    assert result.returncode == 23
    assert (prefix / "src/example.py").read_text() == "value = 1"


def test_symlink_destination_is_rejected(inputs):
    *_, prefix = inputs
    prefix.symlink_to(prefix.parent / "absent")
    with pytest.raises(ValueError, match="DESTINATION_EXISTS"):
        install(*inputs)


def test_missing_input_does_not_create_partial_install(inputs):
    source, config, python, prefix = inputs
    raw = yaml.safe_load(config.read_text())
    Path(raw["cognition"]["llm"]["model_path"]).unlink()
    with pytest.raises(ValueError, match="INPUT_MISSING"):
        install(*inputs)
    assert not prefix.exists()


def test_temporary_audio_dependencies_are_rejected(inputs):
    source, config, python, prefix = inputs
    raw = yaml.safe_load(config.read_text())
    raw["action"]["tts"]["runtime_python"] = str(python)
    config.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match="INSTALLED_AUDIO_PRODUCT_REQUIRED"):
        install(*inputs)
    assert not prefix.exists()
