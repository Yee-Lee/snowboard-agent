"""M4A-IPC-001 — Audio Protocol v1 framing and child cleanup."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from sbd.adaptor.framed_child import (
    AudioProtocolError,
    ChildState,
    FramedProcess,
    MAX_CONTROL_BYTES,
    MAX_PCM_BYTES,
    encode_control,
    read_control,
    read_exact_payload,
    require_positive_request_id,
    require_schema,
)


def _reader(*parts: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader(limit=MAX_CONTROL_BYTES + 1)
    for part in parts:
        reader.feed_data(part)
    reader.feed_eof()
    return reader


def test_m4a_ipc_001_control_boundary_fragment_coalesce_and_schema() -> None:
    async def run() -> None:
        prefix = encode_control({"protocol": 1, "value": ""})
        exact = encode_control({"protocol": 1, "value": "x" * (MAX_CONTROL_BYTES - len(prefix))})
        assert len(exact) == MAX_CONTROL_BYTES
        split = len(exact) // 2
        assert await read_control(_reader(exact[:split], exact[split:])) == {
            "protocol": 1,
            "value": "x" * (MAX_CONTROL_BYTES - len(prefix)),
        }
        with pytest.raises(AudioProtocolError, match="exceeds"):
            encode_control({"protocol": 1, "value": "x" * (MAX_CONTROL_BYTES - len(prefix) + 1)})

        payload = b"\x01\x00" * 8
        header = encode_control({"protocol": 1, "event": "PCM"})
        coalesced = _reader(header + payload)
        assert (await read_control(coalesced))["event"] == "PCM"
        assert await read_exact_payload(coalesced, len(payload), hashlib.sha256(payload).hexdigest()) == payload

        require_schema({"protocol": 1, "event": "READY"}, keys={"protocol", "event"}, label="READY")
        with pytest.raises(AudioProtocolError, match="missing or extra"):
            require_schema({"protocol": 1, "event": "READY", "extra": 1}, keys={"protocol", "event"}, label="READY")

    asyncio.run(run())


@pytest.mark.parametrize(
    "raw",
    [
        b"not-json\n",
        b"\xff\n",
        b"[]\n",
        b'{"event":"READY"}\n',
        b'{"protocol":2,"event":"READY"}\n',
    ],
)
def test_m4a_ipc_001_rejects_invalid_utf8_json_and_protocol(raw: bytes) -> None:
    async def run() -> None:
        with pytest.raises(AudioProtocolError):
            await read_control(_reader(raw))

    asyncio.run(run())


@pytest.mark.parametrize("request_id", [0, -1, 2, "1", True])
def test_m4a_ipc_001_rejects_nonpositive_or_wrong_request_identity(request_id) -> None:
    with pytest.raises(AudioProtocolError, match="identity"):
        require_positive_request_id(request_id, 1)


@pytest.mark.parametrize(
    ("payload_bytes", "payload", "checksum"),
    [
        (0, b"", hashlib.sha256(b"").hexdigest()),
        (3, b"abc", hashlib.sha256(b"abc").hexdigest()),
        (64 * 1024 * 1024 + 2, b"", "0" * 64),
        (4, b"ab", hashlib.sha256(b"ab").hexdigest()),
        (4, b"abcd", "0" * 64),
    ],
)
def test_m4a_ipc_001_rejects_payload_bounds_truncation_and_hash(payload_bytes: int, payload: bytes, checksum: str) -> None:
    async def run() -> None:
        with pytest.raises(AudioProtocolError):
            await read_exact_payload(_reader(payload), payload_bytes, checksum)

    asyncio.run(run())


def test_m4a_ipc_001_accepts_exact_inclusive_64_mib_pcm_boundary() -> None:
    async def run() -> None:
        payload = b"\x00\x00" * (MAX_PCM_BYTES // 2)
        assert await read_exact_payload(
            _reader(payload), MAX_PCM_BYTES, hashlib.sha256(payload).hexdigest(),
        ) == payload

    asyncio.run(run())


@pytest.mark.parametrize(
    "identity_names",
    [
        (
            "runtime_lock_sha256", "vad_model_sha256", "asr_binary_sha256",
            "asr_model_sha256", "profile_sha256",
        ),
        (
            "runtime_lock_sha256", "acoustic_model_sha256", "vocoder_sha256",
            "profile_sha256",
        ),
    ],
)
def test_m4a_ipc_001_ready_exact_domain_keys_and_each_identity_mismatch(
    tmp_path: Path,
    identity_names: tuple[str, ...],
) -> None:
    expected = {name: "a" * 64 for name in identity_names}
    process = FramedProcess(
        argv_builder=lambda workdir: ["unused"],
        work_root=tmp_path,
        expected_ready=expected,
        ready_timeout=1,
        terminate_timeout=1,
        kill_timeout=1,
    )
    process._process = SimpleNamespace(pid=1234)  # type: ignore[assignment]
    ready = {
        "protocol": 1, "event": "READY", "pid": 1234, "pgid": 1234,
        **expected,
    }
    process._validate_ready(ready)
    for name in identity_names:
        wrong = dict(ready)
        wrong[name] = "b" * 64
        with pytest.raises(AudioProtocolError, match=name):
            process._validate_ready(wrong)
    for mutation in (
        lambda value: value.__setitem__("extra", True),
        lambda value: value.__setitem__("pid", 999),
        lambda value: value.__setitem__("pgid", 999),
        lambda value: value.__setitem__("protocol", 2),
    ):
        wrong = dict(ready)
        mutation(wrong)
        with pytest.raises(AudioProtocolError):
            process._validate_ready(wrong)


def _child_script(
    tmp_path: Path,
    *,
    mismatch: bool = False,
    descendant: bool = False,
    stubborn_descendant: bool = False,
) -> Path:
    script = tmp_path / ("child-mismatch.py" if mismatch else "child.py")
    identity = "b" * 64 if mismatch else "a" * 64
    descendant_code = ""
    if descendant:
        child_code = (
            "import signal,time;"
            "signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(30)"
            if stubborn_descendant
            else "import time;time.sleep(30)"
        )
        descendant_code = (
            "\nimport subprocess\n"
            f"child=subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
            "Path(sys.argv[1]).write_text(str(child.pid))\n"
        )
    script.write_text(
        "import json, os, sys\nfrom pathlib import Path\n"
        + descendant_code
        + f"print(json.dumps({{'protocol':1,'event':'READY','pid':os.getpid(),'pgid':os.getpgrp(),'identity':'{identity}'}}), flush=True)\n"
        "for line in sys.stdin:\n"
        "    item=json.loads(line)\n"
        "    if item.get('op') == 'SHUTDOWN':\n"
        "        print(json.dumps({'protocol':1,'event':'SHUTDOWN_ACK'}), flush=True)\n"
        "        raise SystemExit(0)\n"
        "    if item.get('op') == 'HANG':\n"
        "        import time; time.sleep(30)\n",
        encoding="utf-8",
    )
    return script


def test_m4a_ipc_001_ready_identity_idempotent_lifecycle_and_cleanup(tmp_path: Path) -> None:
    async def run() -> None:
        script = _child_script(tmp_path)
        process = FramedProcess(
            argv_builder=lambda workdir: [sys.executable, str(script)],
            work_root=tmp_path / "work",
            expected_ready={"identity": "a" * 64},
            ready_timeout=1.0,
            terminate_timeout=1.0,
            kill_timeout=1.0,
        )
        await process.start()
        pid = process.pid
        workdir = process.workdir
        assert pid and workdir and workdir.exists() and process.state is ChildState.READY
        await process.start()
        assert process.pid == pid
        await process.stop()
        assert process.state is ChildState.STOPPED
        assert workdir is not None and not workdir.exists()
        await process.stop()

    asyncio.run(run())


def test_m4a_ipc_001_request_ids_increase_and_shutdown_is_ready_only(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        process = FramedProcess(
            argv_builder=lambda workdir: [sys.executable, str(_child_script(tmp_path))],
            work_root=tmp_path / "work",
            expected_ready={"identity": "a" * 64},
            ready_timeout=1.0,
            terminate_timeout=1.0,
            kill_timeout=1.0,
        )
        await process.start()
        assert process.allocate_request_id() == 1
        with pytest.raises(AudioProtocolError, match="READY"):
            process.allocate_request_id()
        with pytest.raises(AudioProtocolError, match="READY"):
            await process.stop()
        process.operation_finished()
        assert process.allocate_request_id() == 2
        process.operation_finished()
        await process.stop()
        assert process.state is ChildState.STOPPED and process.returncode == 0

    asyncio.run(run())


def test_m4a_ipc_001_asr_child_rejects_second_begin_as_busy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sbd.perception.listen.whispercpp import supervisor

    for name in ("vad", "worker", "model", "lock"):
        (tmp_path / name).write_bytes(name.encode())
    args = SimpleNamespace(
        vad_model=tmp_path / "vad", asr_binary=tmp_path / "worker",
        asr_model=tmp_path / "model", runtime_lock=tmp_path / "lock",
        profile_sha256="a" * 64, work_dir=tmp_path,
    )

    class Native:
        pid = 1234
        def stop(self) -> None: pass
        def terminate(self) -> None: pass

    class Executor:
        def __init__(self, *args, **kwargs): pass
        def shutdown(self, **kwargs): pass

    commands = iter((
        {"protocol": 1, "op": "BEGIN", "request_id": 1, "format": "16000_mono_s16le", "frame_bytes": 640},
        {"protocol": 1, "op": "BEGIN", "request_id": 2, "format": "16000_mono_s16le", "frame_bytes": 640},
        {"protocol": 1, "op": "CANCEL", "request_id": 1},
        {"protocol": 1, "op": "SHUTDOWN"},
    ))
    events: list[dict[str, object]] = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(supervisor, "parse_args", lambda: args)
    monkeypatch.setattr(supervisor, "Silero", lambda path: SimpleNamespace(probability=lambda frame: 0.0, reset=lambda: None))
    monkeypatch.setattr(supervisor, "NativeWorker", lambda *values: Native())
    monkeypatch.setattr(supervisor.concurrent.futures, "ThreadPoolExecutor", Executor)
    monkeypatch.setattr(supervisor.os, "getpid", lambda: 1234)
    monkeypatch.setattr(supervisor.os, "getpgrp", lambda: 1234)
    monkeypatch.setattr(supervisor.os, "getpgid", lambda pid: 1234)
    monkeypatch.setattr(supervisor.select, "select", lambda *values: ([object()], [], []))
    monkeypatch.setattr(supervisor, "read_control", lambda: next(commands))
    monkeypatch.setattr(supervisor, "emit", lambda value: events.append(value))
    monkeypatch.setattr(supervisor, "_exit_after_shutdown_ack", lambda: None)

    assert supervisor.main() == 0
    assert {"protocol": 1, "event": "BUSY", "request_id": 2} in events
    assert {"protocol": 1, "event": "CANCELLED", "request_id": 1} in events
    assert events[-1] == {"protocol": 1, "event": "SHUTDOWN_ACK"}


def test_m4a_ipc_001_asr_child_releases_native_state_before_shutdown_ack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sbd.perception.listen.whispercpp import supervisor

    for name in ("vad", "worker", "model", "lock"):
        (tmp_path / name).write_bytes(name.encode())
    args = SimpleNamespace(
        vad_model=tmp_path / "vad", asr_binary=tmp_path / "worker",
        asr_model=tmp_path / "model", runtime_lock=tmp_path / "lock",
        profile_sha256="a" * 64, work_dir=tmp_path,
    )
    order: list[str] = []

    class Native:
        pid = 1234
        def stop(self) -> None: order.append("native.stop")
        def terminate(self) -> None: order.append("native.terminate")

    class Executor:
        def __init__(self, *args, **kwargs): pass
        def shutdown(self, *, wait, cancel_futures):
            order.append(f"shutdown:{wait}:{cancel_futures}")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(supervisor, "parse_args", lambda: args)
    monkeypatch.setattr(
        supervisor, "Silero", lambda path: SimpleNamespace(probability=lambda frame: 0.0),
    )
    monkeypatch.setattr(supervisor, "NativeWorker", lambda *values: Native())
    monkeypatch.setattr(supervisor.concurrent.futures, "ThreadPoolExecutor", Executor)
    monkeypatch.setattr(supervisor.gc, "collect", lambda: order.append("collect"))
    monkeypatch.setattr(
        supervisor, "_exit_after_shutdown_ack", lambda: order.append("exit"),
    )
    monkeypatch.setattr(supervisor.os, "getpid", lambda: 1234)
    monkeypatch.setattr(supervisor.os, "getpgrp", lambda: 1234)
    monkeypatch.setattr(supervisor.os, "getpgid", lambda pid: 1234)
    monkeypatch.setattr(supervisor.select, "select", lambda *values: ([object()], [], []))
    monkeypatch.setattr(
        supervisor, "read_control",
        lambda: {"protocol": 1, "op": "SHUTDOWN"},
    )
    monkeypatch.setattr(
        supervisor, "emit", lambda value: order.append(value["event"]),
    )

    assert supervisor.main() == 0
    assert order[:6] == [
        "READY", "shutdown:True:True", "native.stop", "collect",
        "SHUTDOWN_ACK", "exit",
    ]


@pytest.mark.parametrize("fragmented_begin", [False, True])
def test_m4a_ipc_001_actual_asr_process_handles_coalesced_and_fragmented_input(
    tmp_path: Path,
    fragmented_begin: bool,
) -> None:
    launcher = tmp_path / "asr-supervisor-fixture.py"
    for name in ("vad", "worker", "model", "lock"):
        (tmp_path / name).write_bytes(name.encode())
    launcher.write_text(
        "import os\n"
        "from pathlib import Path\n"
        "from types import SimpleNamespace\n"
        "from sbd.perception.listen.whispercpp import supervisor as target\n"
        "class Silero:\n"
        "    def __init__(self, path): self.calls = 0\n"
        "    def reset(self): self.calls = 0\n"
        "    def probability(self, frame):\n"
        "        self.calls += 1\n"
        "        return 1.0 if self.calls <= 10 else 0.0\n"
        "class Native:\n"
        "    def __init__(self, *args): self.pid = os.getpid()\n"
        "    def transcribe(self, path): return ('fixture', 0.1)\n"
        "    def stop(self): pass\n"
        "    def terminate(self): pass\n"
        f"root = Path({str(tmp_path)!r})\n"
        "target.parse_args = lambda: SimpleNamespace("
        "vad_model=root/'vad', asr_binary=root/'worker', asr_model=root/'model', "
        "runtime_lock=root/'lock', profile_sha256='a'*64, work_dir=root)\n"
        "target.Silero = Silero\n"
        "target.NativeWorker = Native\n"
        "raise SystemExit(target.main())\n",
        encoding="utf-8",
    )

    async def run() -> None:
        environment = os.environ.copy()
        source_root = str(Path(__file__).resolve().parents[1] / "src")
        environment["PYTHONPATH"] = source_root + os.pathsep + environment.get("PYTHONPATH", "")
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(launcher),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tmp_path,
            env=environment,
            start_new_session=True,
        )
        try:
            assert process.stdin is not None and process.stdout is not None
            ready = await asyncio.wait_for(read_control(process.stdout), timeout=5)
            assert ready["event"] == "READY"

            begin = encode_control({
                "protocol": 1, "op": "BEGIN", "request_id": 1,
                "format": "16000_mono_s16le", "frame_bytes": 640,
            })
            first_frame = encode_control({
                "protocol": 1, "op": "FRAME", "request_id": 1,
                "sequence": 0, "payload_bytes": 640,
            }) + b"\x00" * 640
            if fragmented_begin:
                split = len(begin) // 2
                process.stdin.write(begin[:split])
                await process.stdin.drain()
                await asyncio.sleep(0.01)
                process.stdin.write(begin[split:] + first_frame)
            else:
                process.stdin.write(begin + first_frame)
            await process.stdin.drain()

            event = await asyncio.wait_for(read_control(process.stdout), timeout=5)
            assert event == {
                "protocol": 1, "event": "FRAME_ACCEPTED",
                "request_id": 1, "sequence": 0,
            }
            endpoint = None
            for sequence in range(1, 120):
                process.stdin.write(encode_control({
                    "protocol": 1, "op": "FRAME", "request_id": 1,
                    "sequence": sequence, "payload_bytes": 640,
                }) + b"\x00" * 640)
                await process.stdin.drain()
                event = await asyncio.wait_for(read_control(process.stdout), timeout=5)
                if event["event"] == "ENDPOINT":
                    endpoint = event
                    break
                assert event == {
                    "protocol": 1, "event": "FRAME_ACCEPTED",
                    "request_id": 1, "sequence": sequence,
                }
            assert endpoint is not None and endpoint["captured_frames"] <= 120
            terminal = await asyncio.wait_for(read_control(process.stdout), timeout=5)
            assert terminal["event"] == "RESULT" and terminal["text"] == "fixture"

            process.stdin.write(encode_control({"protocol": 1, "op": "SHUTDOWN"}))
            await process.stdin.drain()
            assert await asyncio.wait_for(read_control(process.stdout), timeout=5) == {
                "protocol": 1, "event": "SHUTDOWN_ACK",
            }
            deadline = asyncio.get_running_loop().time() + 5
            while (
                process.returncode is None
                and asyncio.get_running_loop().time() < deadline
            ):
                await asyncio.sleep(0.01)
            assert process.returncode == 0
        finally:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=2)
                except TimeoutError:
                    process.kill()
                    await process.wait()

    asyncio.run(run())


def test_m4a_ipc_001_tts_child_rejects_second_generate_as_busy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sbd.action.speak.matcha import worker

    model = tmp_path / "matcha"
    (model / "espeak-ng-data").mkdir(parents=True)
    for name in ("model-steps-3.onnx", "lexicon.txt", "tokens.txt"):
        (model / name).write_bytes(name.encode())
    for name in ("vocoder", "lock"):
        (tmp_path / name).write_bytes(name.encode())
    args = SimpleNamespace(
        model_dir=model, vocoder=tmp_path / "vocoder",
        runtime_lock=tmp_path / "lock", profile_sha256="a" * 64,
        work_dir=tmp_path,
    )

    class PendingFuture:
        def done(self) -> bool: return False

    class Executor:
        def __init__(self, *args, **kwargs): pass
        def submit(self, *args, **kwargs): return PendingFuture()
        def shutdown(self, **kwargs): pass

    commands = iter((
        {"protocol": 1, "op": "GENERATE", "request_id": 1, "text": "first", "voice_id": worker.VOICE_ID},
        {"protocol": 1, "op": "GENERATE", "request_id": 2, "text": "second", "voice_id": worker.VOICE_ID},
        {"protocol": 1, "op": "CANCEL", "request_id": 1},
        None,
    ))
    events: list[dict[str, object]] = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(worker, "parse_args", lambda: args)
    monkeypatch.setattr(worker, "load_tts", lambda *values: object())
    monkeypatch.setattr(worker.concurrent.futures, "ThreadPoolExecutor", Executor)
    monkeypatch.setattr(worker.os, "getpid", lambda: 1234)
    monkeypatch.setattr(worker.os, "getpgrp", lambda: 1234)
    monkeypatch.setattr(worker.select, "select", lambda *values: ([object()], [], []))
    monkeypatch.setattr(worker, "read_control", lambda: next(commands))
    monkeypatch.setattr(worker, "emit", lambda value, payload=None: events.append(value))

    assert worker.main() == 3
    assert {"protocol": 1, "event": "BUSY", "request_id": 2} in events
    assert {"protocol": 1, "event": "CANCEL_DEFERRED", "request_id": 1} in events


def test_m4a_ipc_001_tts_child_ack_precedes_native_runtime_teardown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sbd.action.speak.matcha import worker

    model = tmp_path / "matcha"
    (model / "espeak-ng-data").mkdir(parents=True)
    for name in ("model-steps-3.onnx", "lexicon.txt", "tokens.txt"):
        (model / name).write_bytes(name.encode())
    for name in ("vocoder", "lock"):
        (tmp_path / name).write_bytes(name.encode())
    args = SimpleNamespace(
        model_dir=model, vocoder=tmp_path / "vocoder",
        runtime_lock=tmp_path / "lock", profile_sha256="a" * 64,
        work_dir=tmp_path,
    )
    order: list[str] = []

    class Executor:
        def __init__(self, *args, **kwargs): pass
        def shutdown(self, *, wait, cancel_futures):
            order.append(f"shutdown:{wait}:{cancel_futures}")

    commands = iter(({"protocol": 1, "op": "SHUTDOWN"},))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(worker, "parse_args", lambda: args)
    monkeypatch.setattr(worker, "load_tts", lambda *values: object())
    monkeypatch.setattr(worker.concurrent.futures, "ThreadPoolExecutor", Executor)
    monkeypatch.setattr(
        worker, "_exit_after_shutdown_ack", lambda: order.append("exit"),
    )
    monkeypatch.setattr(worker.os, "getpid", lambda: 1234)
    monkeypatch.setattr(worker.os, "getpgrp", lambda: 1234)
    monkeypatch.setattr(worker.select, "select", lambda *values: ([object()], [], []))
    monkeypatch.setattr(worker, "read_control", lambda: next(commands))
    monkeypatch.setattr(
        worker, "emit",
        lambda value, payload=None: order.append(value["event"]),
    )

    assert worker.main() == 0
    assert order[:3] == ["READY", "SHUTDOWN_ACK", "exit"]
    assert "shutdown:True:True" not in order


def test_m4a_ipc_001_ready_mismatch_terminates_group_and_removes_workdir(tmp_path: Path) -> None:
    async def run() -> None:
        script = _child_script(tmp_path, mismatch=True)
        process = FramedProcess(
            argv_builder=lambda workdir: [sys.executable, str(script)],
            work_root=tmp_path / "work",
            expected_ready={"identity": "a" * 64},
            ready_timeout=1.0,
            terminate_timeout=0.2,
            kill_timeout=1.0,
        )
        with pytest.raises(AudioProtocolError, match="identity"):
            await process.start()
        assert process.state is ChildState.DESTROYED
        assert process.returncode is not None
        assert process.workdir is None

    asyncio.run(run())


def test_m4a_ipc_001_clean_shutdown_rejects_lingering_descendant(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        pid_file = tmp_path / "descendant.pid"
        script = _child_script(
            tmp_path, descendant=True, stubborn_descendant=True,
        )
        process = FramedProcess(
            argv_builder=lambda workdir: [sys.executable, str(script), str(pid_file)],
            work_root=tmp_path / "work",
            expected_ready={"identity": "a" * 64},
            ready_timeout=1.0,
            terminate_timeout=0.1,
            kill_timeout=1.0,
        )
        await process.start()
        descendant_pid = int(pid_file.read_text())
        await asyncio.sleep(0.1)
        with pytest.raises(
            AudioProtocolError,
            match="child shutdown process-group exit timed out",
        ):
            await process.stop()
        assert process.state is ChildState.DESTROYED
        assert not process._live_process_group_members(process.pid or -1)
        try:
            os.kill(descendant_pid, 0)
        except ProcessLookupError:
            pass
        else:
            stat = Path(f"/proc/{descendant_pid}/stat")
            assert stat.is_file() and stat.read_text().split()[2] == "Z"

    asyncio.run(run())


@pytest.mark.parametrize("stubborn", [False, True])
def test_m4a_ipc_001_force_abort_kills_nested_descendant_process_group(
    tmp_path: Path, stubborn: bool,
) -> None:
    async def run() -> None:
        pid_file = tmp_path / "descendant.pid"
        script = _child_script(
            tmp_path, descendant=True, stubborn_descendant=stubborn,
        )
        process = FramedProcess(
            argv_builder=lambda workdir: [sys.executable, str(script), str(pid_file)],
            work_root=tmp_path / "work",
            expected_ready={"identity": "a" * 64},
            ready_timeout=1.0,
            terminate_timeout=0.2,
            kill_timeout=1.0,
        )
        await process.start()
        descendant_pid = int(pid_file.read_text())
        assert os.getpgid(descendant_pid) == process.pid
        if stubborn:
            await asyncio.sleep(0.1)
        await process.force_terminate()
        assert process.returncode is not None and process.state is ChildState.DESTROYED
        for _ in range(100):
            try:
                os.kill(descendant_pid, 0)
            except ProcessLookupError:
                break
            await asyncio.sleep(0.01)
        else:
            # A killed but unreaped orphan can briefly remain as a zombie.  It
            # must no longer be a live member of the owned process group.
            stat = Path(f"/proc/{descendant_pid}/stat")
            assert stat.is_file() and stat.read_text().split()[2] == "Z"

    asyncio.run(run())
