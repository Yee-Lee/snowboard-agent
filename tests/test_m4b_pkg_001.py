"""M4B-PKG-001 — offline package safety and notice closure."""

from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import sys
import zipfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.m4b_llm_product as product
from scripts.m4b_llm_product import (
    InstallInventory,
    ProductFailure,
    PythonABIAttestation,
    PythonPackageAttestation,
    _extract_wheel,
    _load_install_inventory,
    _verify_venv,
    capture_python_abi,
    validate_python_abi,
    verify_installed_python_abi,
    verify_python_abi,
)
from sbd.cognition.litert_lm.lock import RuntimeClosure, RuntimeFile


def _abi(**changes: object) -> PythonABIAttestation:
    value = PythonABIAttestation(
        base_executable="/usr/bin/python3.13",
        base_executable_sha256="a" * 64,
        implementation="CPython",
        version="3.13.5",
        sys_version="3.13.5 (main, Aug 30 2026, 00:00:00) [GCC 14.2.0]",
        soabi="cpython-313-aarch64-linux-gnu",
        multiarch="aarch64-linux-gnu",
        abiflags="",
        pointer_bits=64,
        byteorder="little",
        stdlib="/usr/lib/python3.13",
        platstdlib="/usr/lib/python3.13",
        lib_dynload="/usr/lib/python3.13/lib-dynload",
        glibc_version="2.41",
        packages=tuple(
            PythonPackageAttestation(name, "install ok installed", "3.13.5-2")
            for name in product.PYTHON_PACKAGES
        ),
    )
    return replace(value, **changes)


def _inventory(path: Path, abi: PythonABIAttestation | None = None) -> None:
    value = abi or _abi()
    path.write_text(json.dumps({
        "schema_version": 1,
        "python_abi_attestation": value.as_dict(),
        "python_abi_attestation_sha256": value.sha256,
        "files": [],
    }), encoding="utf-8")


def test_m4b_pkg_001_controller_has_no_selected_runtime_dependency() -> None:
    project = (Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    dependencies = project.partition("dependencies = [")[2].partition("]")[0].lower()
    assert "litert" not in dependencies and "gemma" not in dependencies


def test_m4b_pkg_001_worker_import_does_not_load_controller_factory() -> None:
    worker = Path(__file__).parent.parent / "src/sbd/cognition/litert_lm/worker.py"
    code = (
        "import runpy,sys;"
        f"runpy.run_path({str(worker)!r},run_name='m4b_worker_import_probe');"
        "assert 'sbd.cognition.factory' not in sys.modules;"
        "assert 'sbd.core.config.loader' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", code],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_m4b_pkg_001_cognition_public_factory_export_remains_lazy() -> None:
    from sbd.cognition import make_llm_adapter as exported
    from sbd.cognition.factory import make_llm_adapter

    assert exported is make_llm_adapter


def test_m4b_pkg_001_notice_names_runtime_model_and_license() -> None:
    notice = (Path(__file__).parent.parent / "requirements/m4b/THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8").lower()
    for term in ("litert-lm", "liblitert-lm.so", "gemma 4 e2b", "apache-2.0", "notice"):
        assert term in notice


def test_m4b_pkg_001_safe_exact_wheel_extraction(tmp_path: Path) -> None:
    payload = b"module"
    row = RuntimeFile("package/module.py", len(payload), hashlib.sha256(payload).hexdigest())
    closure = RuntimeClosure(tmp_path / "manifest", "a" * 64, (row,))
    wheel = tmp_path / "runtime.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(row.relative_path, payload)
    output = tmp_path / "runtime"
    _extract_wheel(wheel, output, closure)
    assert (output / row.relative_path).read_bytes() == payload


def test_m4b_pkg_001_safe_exact_wheel_extraction_accepts_empty_venv_site_packages(
    tmp_path: Path,
) -> None:
    payload = b"module"
    row = RuntimeFile("package/module.py", len(payload), hashlib.sha256(payload).hexdigest())
    closure = RuntimeClosure(tmp_path / "manifest", "a" * 64, (row,))
    wheel = tmp_path / "runtime.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(row.relative_path, payload)
    output = tmp_path / "runtime"
    output.mkdir()

    _extract_wheel(wheel, output, closure)

    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert (output / row.relative_path).read_bytes() == payload


@pytest.mark.parametrize("unsafe", ["nonempty", "symlink"])
def test_m4b_pkg_001_wheel_extraction_rejects_unsafe_existing_destination(
    tmp_path: Path, unsafe: str,
) -> None:
    payload = b"module"
    row = RuntimeFile("package/module.py", len(payload), hashlib.sha256(payload).hexdigest())
    closure = RuntimeClosure(tmp_path / "manifest", "a" * 64, (row,))
    wheel = tmp_path / "runtime.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(row.relative_path, payload)
    output = tmp_path / "runtime"
    if unsafe == "nonempty":
        output.mkdir()
        (output / "unexpected").write_bytes(b"x")
    else:
        target = tmp_path / "target"
        target.mkdir()
        output.symlink_to(target, target_is_directory=True)

    with pytest.raises(ProductFailure, match="destination"):
        _extract_wheel(wheel, output, closure)


@pytest.mark.parametrize("entry", ["../escape", "/absolute"])
def test_m4b_pkg_001_rejects_unsafe_or_extra_wheel_entry(tmp_path: Path, entry: str) -> None:
    closure = RuntimeClosure(tmp_path / "manifest", "a" * 64, (
        RuntimeFile("safe", 1, hashlib.sha256(b"x").hexdigest()),
    ))
    wheel = tmp_path / "runtime.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("safe", b"x")
        archive.writestr(entry, b"bad")
    with pytest.raises(ProductFailure, match="unsafe|inventory"):
        _extract_wheel(wheel, tmp_path / "output", closure)


@pytest.mark.parametrize("relative_path", ["duplicate", "../escape", "/absolute"])
def test_m4b_pkg_001_install_inventory_rejects_duplicate_or_unsafe_path(
    tmp_path: Path, relative_path: str,
) -> None:
    rows = [{
        "relative_path": "duplicate",
        "size_bytes": 1,
        "sha256": hashlib.sha256(b"x").hexdigest(),
    }, {
        "relative_path": relative_path,
        "size_bytes": 1,
        "sha256": hashlib.sha256(b"x").hexdigest(),
    }]
    inventory = tmp_path / "install-inventory.json"
    inventory.write_text(
        json.dumps({"schema_version": 1, "files": rows}),
        encoding="utf-8",
    )
    with pytest.raises(ProductFailure, match="inventory is invalid"):
        _load_install_inventory(inventory)


def test_m4b_pkg_001_exact_target_abi_is_canonical_and_stable() -> None:
    value = _abi()
    validate_python_abi(value)
    restored = PythonABIAttestation.from_mapping(value.as_dict())
    assert restored == value
    assert restored.sha256 == value.sha256
    assert len(value.sha256) == 64


@pytest.mark.parametrize(("field", "wrong"), [
    ("base_executable", "/opt/python3.13"),
    ("base_executable_sha256", "not-a-digest"),
    ("implementation", "PyPy"),
    ("version", "3.13.4"),
    ("version", "3.13.6"),
    ("sys_version", "3.13.4 (drift)"),
    ("soabi", "cpython-313-x86_64-linux-gnu"),
    ("multiarch", "x86_64-linux-gnu"),
    ("abiflags", "m"),
    ("stdlib", "/usr/local/lib/python3.13"),
    ("platstdlib", "/opt/python3.13"),
    ("lib_dynload", "/tmp/lib-dynload"),
    ("glibc_version", "unknown"),
    ("pointer_bits", 32),
    ("byteorder", "big"),
])
def test_m4b_pkg_001_rejects_wrong_fixed_python_abi_field(field: str, wrong: object) -> None:
    with pytest.raises(ProductFailure, match="ABI identity"):
        validate_python_abi(_abi(**{field: wrong}))


@pytest.mark.parametrize("packages", [
    lambda values: values[:-1],
    lambda values: values + (values[0],),
    lambda values: values[:-1] + (replace(values[-1], version="3.13.5-3"),),
    lambda values: values[:-1] + (replace(values[-1], status="not-installed"),),
    lambda values: tuple(replace(value, version="3.13.4-1") for value in values),
])
def test_m4b_pkg_001_rejects_missing_duplicate_mixed_or_uninstalled_package(packages) -> None:
    original = _abi().packages
    with pytest.raises(ProductFailure, match="package"):
        validate_python_abi(_abi(packages=packages(original)))


def test_m4b_pkg_001_compare_rejects_every_run_bound_drift() -> None:
    expected = _abi()
    for actual in (
        replace(expected, base_executable_sha256="b" * 64),
        replace(expected, glibc_version="2.42"),
        replace(expected, sys_version=expected.sys_version + " drift"),
        replace(
            expected,
            packages=expected.packages[:-1] + (
                replace(expected.packages[-1], version="3.13.5-3"),
            ),
        ),
    ):
        with pytest.raises(ProductFailure, match="drift|package"):
            verify_python_abi(expected, actual)


def test_m4b_pkg_001_capture_python_abi_uses_exact_base_and_package_tuple(monkeypatch) -> None:
    monkeypatch.setattr(product.os, "lstat", lambda path: SimpleNamespace(st_mode=stat.S_IFREG, st_uid=0))
    monkeypatch.setattr(product, "_digest", lambda path: "a" * 64)
    probe = _abi().as_dict()
    probe = {
        key: probe[key]
        for key in set(product.EXPECTED_PYTHON_ABI) | {"sys_version", "glibc_version"}
    }
    calls: list[list[str]] = []

    def runner(argv, **kwargs):
        calls.append(argv)
        if argv[0] == str(product.BASE_PYTHON):
            return subprocess.CompletedProcess(argv, 0, json.dumps(probe), "")
        package = argv[-1]
        assert package in product.PYTHON_PACKAGES
        return subprocess.CompletedProcess(argv, 0, "install ok installed\t3.13.5-2\n", "")

    actual = capture_python_abi(product.BASE_PYTHON, runner=runner)
    assert actual == _abi()
    assert len(calls) == 1 + len(product.PYTHON_PACKAGES)
    assert calls[0][1:3] == ["-I", "-B"]
    assert [call[-1] for call in calls[1:]] == list(product.PYTHON_PACKAGES)


@pytest.mark.parametrize(("mode", "uid"), [
    (stat.S_IFLNK, 0),
    (stat.S_IFDIR, 0),
    (stat.S_IFREG, 1000),
])
def test_m4b_pkg_001_capture_rejects_nonregular_symlink_or_non_root_base(
    monkeypatch, mode: int, uid: int,
) -> None:
    monkeypatch.setattr(product.os, "lstat", lambda path: SimpleNamespace(st_mode=mode, st_uid=uid))
    with pytest.raises(ProductFailure, match="missing or unsafe"):
        capture_python_abi(product.BASE_PYTHON)


def test_m4b_pkg_001_capture_rejects_missing_base_before_probe(monkeypatch) -> None:
    called = False

    def runner(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError

    monkeypatch.setattr(
        product.os, "lstat",
        lambda path: (_ for _ in ()).throw(FileNotFoundError(path)),
    )
    with pytest.raises(ProductFailure, match="missing or unsafe"):
        capture_python_abi(product.BASE_PYTHON, runner=runner)
    assert called is False


def test_m4b_pkg_001_capture_rejects_alternate_base_before_probe(tmp_path: Path) -> None:
    called = False

    def runner(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError

    with pytest.raises(ProductFailure, match="base interpreter"):
        capture_python_abi(tmp_path / "python3.13", runner=runner)
    assert called is False


def test_m4b_pkg_001_install_inventory_binds_exact_abi_digest(tmp_path: Path) -> None:
    path = tmp_path / "install-inventory.json"
    _inventory(path)
    inventory = _load_install_inventory(path)
    assert inventory.python_abi == _abi()
    assert inventory.python_abi_sha256 == _abi().sha256
    value = json.loads(path.read_text(encoding="utf-8"))
    value["python_abi_attestation_sha256"] = "0" * 64
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ProductFailure, match="checksum"):
        _load_install_inventory(path)


def _venv_probe(
    install_root: Path, *, paths: list[str] | None = None,
    extension_path: str = "/usr/lib/python3.13/lib-dynload/_bz2.cpython-313-aarch64-linux-gnu.so",
    venv_platstdlib: str | None = None,
) -> str:
    site = install_root / "lib/python3.13/site-packages"
    return json.dumps({
        "implementation": "cpython",
        "version": "3.13.5",
        "prefix": str(install_root),
        "base_prefix": "/usr",
        "enable_user_site": False,
        "paths": paths or [
            "/usr/lib/python313.zip", "/usr/lib/python3.13",
            "/usr/lib/python3.13/lib-dynload", str(site),
        ],
        "stdlib": "/usr/lib/python3.13",
        "platstdlib": "/usr/lib/python3.13",
        "venv_platstdlib": venv_platstdlib or str(install_root / "lib/python3.13"),
        "json_path": "/usr/lib/python3.13/json/__init__.py",
        "extension_path": extension_path,
        "module_origin": str(site / "litert_lm/__init__.py"),
    })


def _venv(tmp_path: Path) -> tuple[Path, Path]:
    root = (tmp_path / "runtime").absolute()
    (root / "bin").mkdir(parents=True)
    runtime = root / "bin/python"
    runtime.write_bytes(b"python")
    (root / "pyvenv.cfg").write_text(
        "home = /usr/bin\n"
        "include-system-site-packages = false\n"
        "version = 3.13.5\n"
        "executable = /usr/bin/python3.13\n",
        encoding="utf-8",
    )
    return root, runtime


def test_m4b_pkg_001_venv_allows_stdlib_and_product_site(tmp_path: Path) -> None:
    root, runtime = _venv(tmp_path)
    runner = lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, _venv_probe(root), "")
    _verify_venv(root, runtime, runner=runner)


@pytest.mark.parametrize("escaped", [
    "/usr/lib/python3/dist-packages",
    "/usr/local/lib/python3.13/site-packages",
    "/home/operator/.local/lib/python3.13/site-packages",
])
def test_m4b_pkg_001_venv_rejects_third_party_site_escape(
    tmp_path: Path, escaped: str,
) -> None:
    root, runtime = _venv(tmp_path)
    runner = lambda argv, **kwargs: subprocess.CompletedProcess(
        argv, 0, _venv_probe(root, paths=[escaped]), "",
    )
    with pytest.raises(ProductFailure, match="isolation mismatch"):
        _verify_venv(root, runtime, runner=runner)


def test_m4b_pkg_001_venv_rejects_dynamic_stdlib_extension_escape(tmp_path: Path) -> None:
    root, runtime = _venv(tmp_path)
    runner = lambda argv, **kwargs: subprocess.CompletedProcess(
        argv, 0, _venv_probe(root, extension_path="/usr/local/lib/python3.13/_json.so"), "",
    )
    with pytest.raises(ProductFailure, match="isolation mismatch"):
        _verify_venv(root, runtime, runner=runner)


def test_m4b_pkg_001_venv_rejects_platstdlib_escape(tmp_path: Path) -> None:
    root, runtime = _venv(tmp_path)
    runner = lambda argv, **kwargs: subprocess.CompletedProcess(
        argv, 0, _venv_probe(root, venv_platstdlib="/tmp/escaped-python"), "",
    )
    with pytest.raises(ProductFailure, match="isolation mismatch"):
        _verify_venv(root, runtime, runner=runner)


def test_m4b_pkg_001_install_uses_bounded_target_venv_without_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    lock_path = tmp_path / "llm-artifacts.json"
    manifest_path = tmp_path / "llm-runtime-rpi-cp313.json"
    notice_path = tmp_path / "THIRD_PARTY_NOTICES.md"
    for path, payload in (
        (lock_path, b"lock"), (manifest_path, b"manifest"), (notice_path, b"notice"),
    ):
        path.write_bytes(payload)
    lock = SimpleNamespace(
        runtime={"wheel_size_bytes": 1, "wheel_sha256": "a" * 64},
        identity=SimpleNamespace(candidate_id="CAND-LRT-G4E2B-MOBILE-R1"),
    )
    closure = SimpleNamespace(digest="b" * 64, files=())
    monkeypatch.setattr(product, "_load", lambda *args: (lock, closure))
    monkeypatch.setattr(product, "_verify_file", lambda *args, **kwargs: None)
    monkeypatch.setattr(product, "_extract_wheel", lambda *args, **kwargs: None)
    monkeypatch.setattr(product, "_verify_venv", lambda *args, **kwargs: None)
    calls: list[tuple[list[str], dict[str, str]]] = []

    def runner(argv, **kwargs):
        calls.append((argv, kwargs["env"]))
        return subprocess.CompletedProcess(argv, 0, "", "")

    output = tmp_path / "runtime"
    result = product.install(
        lock_path=lock_path,
        manifest_path=manifest_path,
        notice_path=notice_path,
        wheel_path=tmp_path / "runtime.whl",
        runtime_python=product.BASE_PYTHON,
        output=output,
        capture_abi=lambda path: _abi(),
        runner=runner,
    )

    assert len(calls) == 1
    argv, environment = calls[0]
    assert argv[:-1] == [
        str(product.BASE_PYTHON), "-I", "-B", "-m", "venv", "--copies", "--without-pip",
    ]
    assert Path(argv[-1]).parent == tmp_path
    assert environment == {
        "PATH": "/usr/bin:/bin", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
    }
    assert all(item not in {"apt", "apt-get", "pip"} and not item.startswith("http") for item in argv)
    assert (output / "llm-runtime-rpi-cp313.json").read_bytes() == b"manifest"
    assert manifest_path.read_bytes() == b"manifest"
    assert result["runtime_file_count"] == 0


def test_m4b_pkg_001_acceptance_recheck_rejects_post_install_drift(
    tmp_path: Path, monkeypatch,
) -> None:
    expected = _abi()
    inventory = InstallInventory({}, expected, expected.sha256, "d" * 64)
    monkeypatch.setattr(product, "_load_install_inventory", lambda path: inventory)
    monkeypatch.setattr(product, "_verify_venv", lambda *args, **kwargs: None)
    with pytest.raises(ProductFailure, match="drift"):
        verify_installed_python_abi(
            install_root=tmp_path,
            runtime_python=tmp_path / "bin/python",
            capture_abi=lambda path: replace(expected, base_executable_sha256="b" * 64),
        )


def test_m4b_pkg_001_bad_abi_fails_before_staging_side_effect(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setattr(product, "_load", lambda *args: (
        SimpleNamespace(runtime={"wheel_size_bytes": 1, "wheel_sha256": "a" * 64}),
        SimpleNamespace(),
    ))
    monkeypatch.setattr(product, "_verify_file", lambda *args, **kwargs: None)
    parent = tmp_path / "must-not-exist"
    with pytest.raises(ProductFailure, match="ABI identity"):
        product.install(
            lock_path=tmp_path / "lock",
            manifest_path=tmp_path / "manifest",
            notice_path=tmp_path / "notices",
            wheel_path=tmp_path / "wheel",
            runtime_python=product.BASE_PYTHON,
            output=parent / "runtime",
            capture_abi=lambda path: replace(_abi(), version="3.13.4"),
        )
    assert not parent.exists()


def test_m4b_pkg_001_failed_install_rejects_staging_residue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(product, "_load", lambda *args: (
        SimpleNamespace(
            runtime={"wheel_size_bytes": 1, "wheel_sha256": "a" * 64},
            identity=SimpleNamespace(candidate_id="candidate"),
        ),
        SimpleNamespace(digest="b" * 64, files=()),
    ))
    monkeypatch.setattr(product, "_verify_file", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        product, "_extract_wheel",
        lambda *args, **kwargs: (_ for _ in ()).throw(ProductFailure("injected install failure")),
    )
    monkeypatch.setattr(product.shutil, "rmtree", lambda path: None)
    output = tmp_path / "runtime"

    with pytest.raises(ProductFailure, match="staging cleanup"):
        product.install(
            lock_path=tmp_path / "lock",
            manifest_path=tmp_path / "manifest",
            notice_path=tmp_path / "notices",
            wheel_path=tmp_path / "wheel",
            runtime_python=product.BASE_PYTHON,
            output=output,
            capture_abi=lambda path: _abi(),
            runner=lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, "", ""),
        )
    assert not output.exists()
    assert tuple(tmp_path.glob(".runtime.staging-*"))
