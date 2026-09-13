"""M4B offline environment and native import ownership."""
import sys
import json
from dataclasses import replace
from pathlib import Path
import pytest
from sbd.cognition.litert_lm.adapter import isolated_child_environment
from sbd.cognition.litert_lm.worker import _verify_native_library

def test_environment_strips_injection_and_disables_downloads():
    environment = isolated_child_environment(Path("/runtime"), {
        "PATH": "/bin", "PYTHONPATH": "/private/injection",
        "PYTHONHOME": "/private/python", "LD_PRELOAD": "/private/lib",
        "https_proxy": "http://private", "ALL_PROXY": "http://private"})
    assert not any(key in environment for key in ("PYTHONPATH", "PYTHONHOME", "LD_PRELOAD", "https_proxy", "ALL_PROXY"))
    assert environment["PYTHONNOUSERSITE"] == "1"
    assert environment["HF_HUB_OFFLINE"] == environment["TRANSFORMERS_OFFLINE"] == environment["PIP_NO_INDEX"] == "1"
    assert environment["LD_LIBRARY_PATH"] == "/runtime/litert_lm"

def test_controller_import_never_loads_native_runtime():
    assert "litert_lm" not in sys.modules

def test_native_hash_rejects_symlink_before_import(tmp_path):
    import pytest
    library = tmp_path / "lib.so"
    library.write_bytes(b"public-fixture")
    link = tmp_path / "alias.so"
    link.symlink_to(library)
    with pytest.raises(RuntimeError, match="identity"):
        _verify_native_library(link, "0" * 64)


def test_network_filter_checks_arch_and_denies_socket_creation():
    from sbd.cognition.litert_lm.worker import _network_filter_program
    program = _network_filter_program()
    def evaluate(arch, number):
        register, position = 0, 0
        while True:
            code, yes, no, value = program[position]
            if code == 0x20:
                register = arch if value == 4 else number
            elif code == 0x15:
                position += yes if register == value else no
            elif code == 0x06:
                return value
            else:
                raise AssertionError("unexpected filter opcode")
            position += 1
    assert evaluate(0xC000003E, 198) == 0x80000000
    for syscall in (198, 199, 425, 438, 117):
        assert evaluate(0xC00000B7, syscall) == 0x00050001
    for syscall in (63, 64, 93, 98):
        assert evaluate(0xC00000B7, syscall) == 0x7FFF0000


def test_unavailable_network_enforcement_fails_before_ready(monkeypatch):
    import pytest
    from sbd.cognition.litert_lm import worker
    monkeypatch.setattr(worker.sys, "platform", "unsupported-test-platform")
    with pytest.raises(RuntimeError, match="network"):
        worker.install_network_denial()


def _measurement_authorization(tmp_path, monkeypatch):
    from sbd.cognition.litert_lm import measurement
    from sbd.cognition.litert_lm.lock import load_product_profile
    profile = load_product_profile(Path(__file__).resolve().parents[1] / "requirements/m4b/product-profile.json",
                                   allow_measurement=True)
    expected = {"schema_version": 1, "harness_sha256": "a" * 64, "candidate_sha": "b" * 40,
                "profile_sha256": profile["profile_sha256"], "target_identity": "pi5-4gb-debian13-aarch64-cp3135"}
    document = {"authorized_tuple": expected, "approvals": [
        {"role": role, "reviewer": role + "-fixture", "approved_at": "2026-09-12T00:00:00Z",
         "decision": "Approved", "authorized_tuple": expected} for role in ("Designer", "Tester")]}
    path = tmp_path / "approval.json"
    path.write_text(json.dumps(document))
    calls = []
    monkeypatch.setattr(measurement, "_verify_context", lambda value, **_kwargs: calls.append(dict(value)))
    return profile, expected, document, path, calls


def test_measurement_grant_rechecks_exact_dual_approval_and_profile_before_child(tmp_path, monkeypatch):
    from sbd.cognition.litert_lm.measurement import MeasurementGrant, MeasurementAuthorizationError
    profile, expected, document, path, calls = _measurement_authorization(tmp_path, monkeypatch)
    grant = MeasurementGrant.load(path, expected_tuple=expected, profile=profile)
    assert calls == [expected]
    arguments = grant.child_arguments()
    assert arguments[0] == "--measurement-authorization" and Path(arguments[1]) == path
    assert arguments[2] == "--measurement-expected" and json.loads(arguments[3]) == expected
    grant.authorize_profile(profile)
    assert len(calls) == 2
    document["approvals"].pop()
    path.write_text(json.dumps(document))
    with pytest.raises(MeasurementAuthorizationError):
        grant.authorize_profile(profile)
    assert len(calls) == 2


def test_user_diagnostic_grant_crosses_isolated_child_without_approval_file(tmp_path, monkeypatch):
    from sbd.cognition.litert_lm.measurement import MeasurementGrant
    profile, expected, _document, _path, _calls = _measurement_authorization(tmp_path, monkeypatch)
    contexts = []

    def verify(value, *, allow_dirty=False):
        contexts.append((dict(value), allow_dirty))

    monkeypatch.setattr("sbd.cognition.litert_lm.measurement._verify_context", verify)
    grant = MeasurementGrant.user_diagnostic(expected_tuple=expected, profile=profile,
                                               diagnostic_directory=tmp_path)
    assert grant.is_user_diagnostic() is True
    assert contexts == [(expected, True)]
    assert grant.child_arguments() == [
        "--measurement-user-diagnostic",
        "--measurement-diagnostic-directory",
        str(tmp_path),
        "--measurement-expected",
        json.dumps(expected, sort_keys=True, separators=(",", ":")),
    ]
    grant.authorize_profile(profile)
    assert contexts == [(expected, True), (expected, True)]


@pytest.mark.parametrize("field,value", [("candidate_sha", "0" * 40),
    ("harness_sha256", "0" * 64), ("profile_sha256", "0" * 64),
    ("target_identity", "another-target"), ("schema_version", True)])
def test_measurement_authorization_never_rebinds_approved_tuple(tmp_path, monkeypatch, field, value):
    from sbd.cognition.litert_lm.measurement import MeasurementGrant, MeasurementAuthorizationError
    profile, expected, document, path, calls = _measurement_authorization(tmp_path, monkeypatch)
    with pytest.raises(MeasurementAuthorizationError):
        MeasurementGrant.load(path, expected_tuple=expected | {field: value}, profile=profile)
    assert calls == []


def test_measurement_grant_is_not_a_boolean_or_unverified_constructor(tmp_path, monkeypatch):
    from sbd.cognition.litert_lm.measurement import MeasurementGrant, MeasurementAuthorizationError
    from sbd.cognition.litert_lm.adapter import LiteRTLMAdapter
    from sbd.cognition.llm import LLMFatalError
    from tests.fakes.m4b_llm_child import adapter_fixture
    profile, expected, document, path, calls = _measurement_authorization(tmp_path, monkeypatch)
    with pytest.raises(MeasurementAuthorizationError):
        MeasurementGrant()
    original, _, _, sampler = adapter_fixture()
    lock = replace(original._lock, product_profile=profile, identity=original._lock.ready_identity(profile))
    for grant in (None, True):
        with pytest.raises(LLMFatalError):
            LiteRTLMAdapter(original._cfg, lock=lock, schedule_recovery=original._schedule_recovery,
                wait_recovery=original._wait_recovery, resource_sampler=sampler, measurement_grant=grant)


@pytest.mark.asyncio
async def test_measurement_adapter_uses_lab_floor_without_fabricated_release_thresholds(tmp_path, monkeypatch):
    from sbd.cognition.litert_lm.measurement import MeasurementGrant, MEASUREMENT_SAFETY_FLOOR_BYTES
    from sbd.cognition.litert_lm.adapter import LiteRTLMAdapter
    from sbd.cognition.llm import LLMFatalError
    from tests.fakes.m4b_llm_child import adapter_fixture, Child
    profile, expected, document, path, calls = _measurement_authorization(tmp_path, monkeypatch)
    grant = MeasurementGrant.load(path, expected_tuple=expected, profile=profile)
    original, _, tickets, sampler = adapter_fixture()
    underlying = sampler.sample
    available = MEASUREMENT_SAFETY_FLOOR_BYTES
    def sample(**kwargs):
        return replace(underlying(**kwargs), mem_total_bytes=2 * 1024**3, mem_available_bytes=available)
    sampler.sample = sample
    children = []
    def factory(cfg, lock, epoch, *, measurement_grant):
        assert measurement_grant is grant
        child = Child(lock, epoch)
        children.append(child)
        return child
    lock = replace(original._lock, product_profile=profile, identity=original._lock.ready_identity(profile))
    adapter = LiteRTLMAdapter(original._cfg, lock=lock, schedule_recovery=original._schedule_recovery,
        wait_recovery=original._wait_recovery, resource_sampler=sampler, measurement_grant=grant,
        child_factory=factory)
    await adapter.start()
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "你好")
    assert (await adapter.generate(snapshot, "你好")).text == "你好"
    assert profile["min_mem_available_generate_bytes"] is profile["min_mem_available_speak_bytes"] is None
    available -= 1
    with pytest.raises(LLMFatalError):
        await adapter.measure("s", 1, "再說")
    assert children[0].terminated == 1 and children[0].runtime.sends == 1
    assert not adapter.recovery_pending and tickets == []


@pytest.mark.parametrize("fault", [None, "namespace", "pid_reuse", "clock", "exited"])
def test_linux_clock_proof_requires_live_bound_identity_and_same_time_namespace(tmp_path, monkeypatch, fault):
    from types import SimpleNamespace
    from sbd.cognition.litert_lm import adapter as module
    from tests.fakes.m4b_llm_child import adapter_fixture
    original, _, _, _ = adapter_fixture()
    child = module.SubprocessLLMChild(original._cfg, original._lock, 1)
    child.pid = child.pgid = 77
    child._process = SimpleNamespace(pid=77, returncode=0 if fault == "exited" else None)
    for relative in ("self/ns", "77/ns"):
        (tmp_path / relative).mkdir(parents=True)
    namespace = tmp_path / "self/ns/time"
    namespace.write_text("time namespace")
    if fault == "namespace":
        (tmp_path / "77/ns/time").write_text("different namespace")
    else:
        (tmp_path / "77/ns/time").hardlink_to(namespace)
    tail = ["S"] + ["0"] * 19
    tail[2], tail[19] = "77", "100"
    stat_path = tmp_path / "77/stat"
    stat_path.write_text("77 (worker) " + " ".join(tail))
    real_read = Path.read_text
    reads = []
    def read(path, *args, **kwargs):
        value = real_read(path, *args, **kwargs)
        if path == stat_path:
            reads.append(1)
            if fault == "pid_reuse" and len(reads) == 2:
                value = value[:-3] + "101"
        return value
    monkeypatch.setattr(Path, "read_text", read)
    monkeypatch.setattr(module, "Path", lambda value: tmp_path if str(value) == "/proc"
                        else tmp_path / str(value).removeprefix("/proc/"))
    monkeypatch.setattr(module, "sys", SimpleNamespace(platform="linux"))
    clock = "another-clock" if fault == "clock" else "clock_gettime(CLOCK_MONOTONIC)"
    monkeypatch.setattr(module, "time", SimpleNamespace(get_clock_info=lambda name: SimpleNamespace(implementation=clock)))
    token = child.clock_mapping_token()
    assert (token is not None) is (fault is None)
    if token is not None:
        assert token[:2] == (77, 100)


@pytest.mark.parametrize("fault", [None, "candidate", "dirty", "harness", "python", "board", "memory", "os"])
def test_grant_context_authenticates_checkout_harness_and_exact_target(tmp_path, monkeypatch, fault):
    import hashlib
    from types import SimpleNamespace
    from sbd.cognition.litert_lm import measurement
    (tmp_path / "scripts").mkdir()
    harness = tmp_path / "scripts/m4b_measurement.py"
    harness.write_bytes(b"# approved harness\n")
    expected = {"candidate_sha": "a" * 40, "harness_sha256": hashlib.sha256(harness.read_bytes()).hexdigest()}
    if fault == "harness":
        harness.write_bytes(b"# changed harness\n")
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        assert argv[:3] == ["git", "-C", str(tmp_path)]
        assert kwargs["timeout"] == 15 and kwargs["check"] is True
        output = "b" * 40 if fault == "candidate" else "a" * 40
        if "status" in argv:
            output = " M src/changed.py" if fault == "dirty" else ""
        return SimpleNamespace(stdout=output.encode())
    monkeypatch.setattr(measurement, "_ROOT", tmp_path)
    monkeypatch.setattr(measurement.subprocess, "run", run)
    monkeypatch.setattr(measurement, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(measurement, "platform", SimpleNamespace(machine=lambda: "aarch64",
        python_implementation=lambda: "CPython", python_version=lambda: "3.13.6" if fault == "python" else "3.13.5"))
    read_text, read_bytes = Path.read_text, Path.read_bytes
    def text(path, *args, **kwargs):
        if str(path) == "/etc/os-release":
            return 'ID=debian\nVERSION_ID="12"\n' if fault == "os" else 'ID=debian\nVERSION_ID="13"\n'
        if str(path) == "/proc/meminfo":
            return "MemTotal: 8000000 kB\n" if fault == "memory" else "MemTotal: 3800000 kB\n"
        return read_text(path, *args, **kwargs)
    def binary(path, *args, **kwargs):
        if str(path) == "/proc/device-tree/model":
            return b"other-board" if fault == "board" else b"Raspberry Pi 5 Model B Rev 1.0\0"
        return read_bytes(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", text)
    monkeypatch.setattr(Path, "read_bytes", binary)
    if fault is None:
        measurement._verify_context(expected)
        assert len(calls) == 2
    else:
        with pytest.raises(measurement.MeasurementAuthorizationError):
            measurement._verify_context(expected)


@pytest.mark.parametrize("authorization", ["valid", "diagnostic", "complete_pm", "revoked", "absent"])
def test_native_child_reauthenticates_measurement_before_native_import(tmp_path, monkeypatch, authorization):
    import builtins
    from types import SimpleNamespace
    from sbd.cognition.litert_lm import worker, lock as lock_module
    from sbd.cognition.llm import LLMFatalError
    from tests.fakes.m4b_llm_child import product_lock
    profile, expected, document, path, contexts = _measurement_authorization(tmp_path, monkeypatch)
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(profile))
    model_path = tmp_path / "model"
    model_path.write_bytes(b"model")
    stages = []
    real_lock = product_lock()
    fake_lock = SimpleNamespace(
        runtime_closure=SimpleNamespace(verify_install=lambda root: stages.append("install")),
        verify_config_paths=lambda cfg, **kwargs: stages.append(("paths", kwargs)),
        ready_identity=real_lock.ready_identity, runtime=real_lock.runtime)
    monkeypatch.setattr(lock_module.LLMArtifactLock, "load", lambda *args, **kwargs: fake_lock)
    monkeypatch.setattr(worker, "verify_platform_abi", lambda profile: stages.append("abi"))
    monkeypatch.setattr(worker, "install_network_denial", lambda: stages.append("network"))
    monkeypatch.setattr(worker, "LiteRTRuntime", lambda **kwargs: stages.append("native") or object())
    monkeypatch.setattr(worker, "run", lambda runtime, ready: stages.append(ready["profile_stage"]) or 0)
    monkeypatch.setattr(worker.os, "getpgrp", lambda: worker.os.getpid())
    original_import = builtins.__import__
    def isolated_import(name, *args, **kwargs):
        if name == "sbd.core.config.models":
            raise AssertionError("isolated worker imported YAML-backed AppConfig package")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", isolated_import)
    argv = ["worker", "--model", str(model_path), "--product-profile", str(profile_path),
            "--runtime-root", str(tmp_path), "--artifact-lock", str(tmp_path / "lock")]
    if authorization in {"valid", "revoked"}:
        argv.extend(["--measurement-authorization", str(path), "--measurement-expected", json.dumps(expected)])
    elif authorization in {"diagnostic", "complete_pm"}:
        argv.extend(["--measurement-user-diagnostic", "--measurement-diagnostic-directory",
                     str(tmp_path), "--measurement-expected", json.dumps(expected)])
        if authorization == "complete_pm":
            argv.append("--measurement-complete-pm")
    if authorization == "revoked":
        document["approvals"][0]["decision"] = "Rejected"
        path.write_text(json.dumps(document))
    monkeypatch.setattr(worker.sys, "argv", argv)
    if authorization in {"valid", "diagnostic", "complete_pm"}:
        assert worker.main() == 0
        assert contexts == [expected]
        expected_stages = (["abi", "network", "native", "measurement"]
                           if authorization in {"diagnostic", "complete_pm"} else
                           ["abi", "install", ("paths", {"allow_measurement": True}),
                            "network", "native", "measurement"])
        assert stages == expected_stages
        if authorization == "diagnostic":
            logs = list(tmp_path.glob("llm-child-*-events.jsonl"))
            assert len(logs) == 1
            child_events = [json.loads(line) for line in logs[0].read_text().splitlines()]
            assert child_events[0]["stage"] == "child_starting"
            assert child_events[-1]["stage"] == "ready_emitting"
    else:
        with pytest.raises((LLMFatalError, lock_module.LLMLockError)):
            worker.main()
        assert contexts == [] and stages == []
