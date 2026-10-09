"""Execute the terminal launcher; doubles cover routing, real Pi covers hardware."""
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys

import pytest


LAUNCHER = Path(__file__).resolve().parents[1] / "scripts/run-app.sh"


@pytest.fixture
def product(tmp_path):
    root = tmp_path / "repo with spaces"
    (root / "scripts").mkdir(parents=True)
    package = root / "src/sbd"
    package.mkdir(parents=True)
    launcher = root / "scripts/run-app.sh"
    shutil.copy2(LAUNCHER, launcher)
    (package / "__init__.py").write_text("")
    (package / "main.py").write_text('''
import asyncio, json, os, signal
from pathlib import Path
def bootstrap_logging():
    pass
async def run_app(config_path):
    config = json.loads(Path(config_path).read_text())
    if config.get("wait"):
        stopped = asyncio.Event()
        asyncio.get_running_loop().add_signal_handler(signal.SIGINT, stopped.set)
    print(json.dumps({"pid": os.getpid(), "config": config_path,
                      "cwd": os.getcwd()}), flush=True)
    if config.get("wait"):
        await stopped.wait()
        print("graceful stop", flush=True)
    return config.get("exit_code", 0)
''')
    config = root / "config.local.yaml"
    config.write_text("{}")
    return root, launcher, config


def invoke(launcher, *args, cwd=None, env=None):
    return subprocess.run(["sh", str(launcher), *args], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=10)


def test_help_does_not_require_product_environment():
    result = invoke(LAUNCHER, "--help")
    assert result.returncode == 0
    assert "Ctrl+C" in result.stdout and "--config" in result.stdout


@pytest.mark.parametrize("args", [("--config",), ("--python",), ("--unexpected",)])
def test_invalid_arguments_fail_without_launch(args):
    result = invoke(LAUNCHER, *args)
    assert result.returncode == 2 and "ERROR:" in result.stderr


def test_default_config_and_repository_imports_from_other_directory(product, tmp_path):
    root, launcher, config = product
    hostile = tmp_path / "wrong modules/sbd"
    hostile.mkdir(parents=True)
    (hostile / "__init__.py").write_text('raise RuntimeError("wrong repository")')
    env = dict(os.environ, PYTHONPATH=str(hostile.parent))
    result = invoke(launcher, "--python", sys.executable, cwd=tmp_path, env=env)
    assert result.returncode == 0, result.stderr
    row = json.loads(result.stdout)
    assert row["config"] == str(config) and row["cwd"] == str(root)


def test_relative_config_python_paths_and_exit_code(product, tmp_path):
    _, launcher, _ = product
    config = tmp_path / "chosen config.json"
    config.write_text('{"exit_code": 7}')
    python = tmp_path / "chosen python"
    python.symlink_to(sys.executable)
    result = invoke(launcher, "--python", "./chosen python", "--config", config.name, cwd=tmp_path)
    assert result.returncode == 7
    assert json.loads(result.stdout)["config"] == str(config)


def test_missing_config_never_falls_back_to_mock(product):
    _, launcher, config = product
    config.unlink()
    result = invoke(launcher, "--python", sys.executable)
    assert result.returncode == 2 and "config file is missing" in result.stderr
    assert not result.stdout


def test_missing_python_has_actionable_error(product):
    _, launcher, _ = product
    result = invoke(launcher, "--python", "/nonexistent/product-python")
    assert result.returncode == 2 and "Python is unavailable" in result.stderr


def test_exec_delivers_sigint_to_app_and_preserves_graceful_exit(product):
    _, launcher, config = product
    config.write_text('{"wait": true}')
    process = subprocess.Popen(["sh", str(launcher), "--python", sys.executable],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert select.select([process.stdout], [], [], 5)[0], "App did not start"
        row = json.loads(process.stdout.readline())
        assert row["pid"] == process.pid  # exec leaves no shell between terminal and App.
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=5)
        assert process.returncode == 0, stderr
        assert "graceful stop" in stdout
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
