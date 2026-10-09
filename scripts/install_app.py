#!/usr/bin/env python3
"""Offline, fresh-prefix installation of the tested voice App (not a service)."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]


def install(source: Path, config_path: Path, python: Path, prefix: Path) -> None:
    source = source.resolve()
    config_path = config_path.resolve()
    prefix = prefix.absolute()
    if prefix.exists() or prefix.is_symlink():
        raise ValueError("INSTALL_DESTINATION_EXISTS")
    if prefix.is_relative_to(source) or prefix == prefix.parent:
        raise ValueError("INSTALL_DESTINATION_UNSAFE")
    raw = yaml.safe_load(config_path.read_text())
    llm = raw["cognition"]["llm"]
    listen = raw["perception"]["listen"]["adapter"]
    tts = raw["action"]["tts"]
    display = raw["core"]["display"]
    if (llm["driver"], listen["driver"], tts["driver"], display["driver"]) != (
            "litert_lm", "whispercpp", "sherpa_matcha", "ssd1351"):
        raise ValueError("PRODUCTION_CONFIG_REQUIRED")

    def configured(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else config_path.parent / path

    # Do not resolve bin/python symlinks: their containing venv is the runtime.
    controller = python.absolute().parent.parent
    llm_runtime = configured(llm["runtime_python"]).parent.parent
    for runtime in (controller, llm_runtime):
        if not (runtime / "pyvenv.cfg").is_file() or not (runtime / "bin/python").is_file():
            raise ValueError("VENV_RUNTIME_REQUIRED")
    # Audio is already a stable installed product. Reject temporary audio dependencies.
    for section in (listen, tts):
        for key in ("runtime_python", "model_path", "worker_path", "vad_model_path", "vocoder_path"):
            if section.get(key) is not None:
                path = configured(section[key])
                if not path.is_relative_to(Path("/var/lib/snowboard/products")) or not path.exists():
                    raise ValueError("INSTALLED_AUDIO_PRODUCT_REQUIRED")

    model_relative = "artifacts/llm/" + configured(llm["model_path"]).name
    files = {
        model_relative: configured(llm["model_path"]),
        "config/llm-profile.json": configured(llm["product_profile_path"]),
        "requirements/m4b/llm-artifacts.json": configured(llm["artifact_lock_path"]),
        "requirements/m4a/listen-artifacts.json": configured(listen["artifact_lock_path"]),
        "requirements/m4a/tts-artifacts.json": configured(tts["artifact_lock_path"]),
        "native/libdisplay.so": configured(display["native_library_path"]),
    }
    if any(not path.is_file() for path in files.values()):
        raise ValueError("INSTALL_INPUT_MISSING")

    # Fresh directory only. Failures retain the partial destination for diagnosis.
    prefix.mkdir(mode=0o700, parents=True, exist_ok=False)
    ignored = shutil.ignore_patterns("__pycache__", "*.pyc", "__editable__*")
    shutil.copytree(source / "src", prefix / "src", ignore=ignored)
    shutil.copytree(source / "requirements", prefix / "requirements", ignore=ignored)
    (prefix / "scripts").mkdir()
    shutil.copy2(source / "scripts/run-app.sh", prefix / "scripts/run-app.sh")
    shutil.copytree(controller, prefix / ".venv", symlinks=True, ignore=ignored)
    shutil.copytree(llm_runtime, prefix / "runtimes/llm", symlinks=True, ignore=ignored)
    for relative, original in files.items():
        target = prefix / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)

    llm.update(runtime_python=str(prefix / "runtimes/llm/bin/python"),
               model_path=str(prefix / model_relative),
               product_profile_path=str(prefix / "config/llm-profile.json"),
               artifact_lock_path=str(prefix / "requirements/m4b/llm-artifacts.json"))
    listen["artifact_lock_path"] = str(prefix / "requirements/m4a/listen-artifacts.json")
    tts["artifact_lock_path"] = str(prefix / "requirements/m4a/tts-artifacts.json")
    display["native_library_path"] = str(prefix / "native/libdisplay.so")
    (prefix / "logs").mkdir(mode=0o700)
    raw.setdefault("log", {}).update(file=str(prefix / "logs/application.log"))
    installed_config = prefix / "config.local.yaml"
    installed_config.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False))
    installed_config.chmod(0o600)
    entry = prefix / "run.sh"
    entry.write_text('#!/bin/sh\nset -eu\n'
                     'APP_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
                     'if [ -L "$APP_ROOT/current" ]; then APP_ROOT="$APP_ROOT/current"; fi\n'
                     'umask 077\n'
                     'exec "$APP_ROOT/scripts/run-app.sh" "$@"\n')
    entry.chmod(0o755)
    (prefix / "scripts/run-app.sh").chmod(0o755)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--python", required=True, type=Path,
                        help="Existing production controller venv bin/python to copy")
    parser.add_argument("--prefix", required=True, type=Path,
                        help="New, fixed installation directory; existing directories are rejected")
    args = parser.parse_args()
    try:
        install(ROOT, args.config, args.python, args.prefix)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
        print("Installation failed; check inputs and any retained partial destination.", file=sys.stderr)
        return 2
    print("Installation complete. Run the installation's run.sh; Ctrl+C stops App, not Pi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
