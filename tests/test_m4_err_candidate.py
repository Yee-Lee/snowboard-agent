"""M4-ERR WP7 content binding and bounded composition audit."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

from sbd.core.candidate_identity import tracked_content_digest


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_m4_err_pu_010_tracked_content_digest(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    source = tmp_path / "src/sbd/core/value.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "src/sbd/core/value.py")

    before = tracked_content_digest(tmp_path, scopes=("src/sbd/core",))
    assert tracked_content_digest(tmp_path, scopes=("src/sbd/core",)) == before
    source.write_text("VALUE = 2\n", encoding="utf-8")
    changed = tracked_content_digest(tmp_path, scopes=("src/sbd/core",))
    assert changed != before

    untracked = tmp_path / "src/sbd/core/scratch.py"
    untracked.write_text("ignored = True\n", encoding="utf-8")
    assert tracked_content_digest(tmp_path, scopes=("src/sbd/core",)) == changed
    included = tracked_content_digest(
        tmp_path,
        scopes=("src/sbd/core",),
        pending_new_paths=("src/sbd/core/scratch.py",),
    )
    assert included != changed


def test_m4_err_pi_010_fault_boundaries_raise_typed_fault_from_cause() -> None:
    root = Path(__file__).resolve().parents[1]
    boundaries = {
        "src/sbd/perception/listen/listener.py": {"body"},
        "src/sbd/perception/listen/whispercpp/adapter.py": {"transcribe"},
        "src/sbd/cognition/reasoner.py": {"body"},
        "src/sbd/action/speak/speaker.py": {"body"},
        "src/sbd/action/speak/matcha/adapter.py": {"generate"},
        "src/sbd/core/gpio/gpiod/driver.py": {"_run_callback", "_report_fault"},
    }
    missing: list[str] = []
    for relative, function_names in boundaries.items():
        path = root / relative
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        functions = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for name in function_names:
            function = functions.get(name)
            if function is None:
                missing.append(f"{relative}:{name}:missing")
                continue
            source = ast.unparse(function)
            if not any(marker in source for marker in (
                "ComponentSystemFault", "fault.to_event()", "self._report_fault("
            )):
                missing.append(f"{relative}:{name}:untyped")
    assert missing == []
