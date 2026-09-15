"""Isolated v3 child. No model content is logged, persisted, or sent outside IPC.

Runtime source authority: google-ai-edge/LiteRT-LM commit
924e79c91542761242244e4f1651851f822e4cbb, python/litert_lm/{engine,conversation}.py;
runtime/conversation/conversation.cc:235-255,515-550 and prompt_utils.cc:83-181.
The C renderer retains last_rendered_message (c/conversation.cc:603-623);
approved DISCARD_TICKET replaces it using the fixed public scrub rendering.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
import platform
import queue
import select
import stat
import sys
import sysconfig
import threading
import time
import traceback
import secrets
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

_CANDIDATE_PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(_CANDIDATE_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CANDIDATE_PACKAGE_ROOT))

from sbd.cognition.llm_child_protocol import (
    MAX_CONTROL_BYTES, TICKET_SCRUB_TEXT, ProtocolLedger, decode_frame, encode_frame, require, validate_counts)
from sbd.cognition.semantic import (
    RESPONSE_SCHEMA_LOCATOR, RESPONSE_SCHEMA_SHA256, load_response_schema,
    validate_semantic, SemanticError,
)
from sbd.cognition.prompt_builder import SYSTEM_PROMPT

_DIAGNOSTIC_DIRECTORY: Path | None = None


def _diagnostic_mark(stage: str, **values: object) -> None:
    directory = _DIAGNOSTIC_DIRECTORY
    if directory is None:
        return
    row = {"wall_time": datetime.now(timezone.utc).isoformat(),
           "monotonic_ns": time.monotonic_ns(), "pid": os.getpid(),
           "stage": stage, **values}
    raw = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(directory / f"llm-child-{os.getpid()}-events.jsonl",
        os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    try:
        os.write(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

class WorkerCancelled(RuntimeError):
    pass

class WorkerCancelFailed(RuntimeError):
    pass

def _verify_native_library(path: Path, expected_sha256: str) -> None:
    if path.is_symlink() or path.parent.is_symlink():
        raise RuntimeError("native runtime identity mismatch")
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise RuntimeError("native runtime identity mismatch") from None
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError("native runtime identity mismatch")
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
    finally:
        os.close(descriptor)
    if digest.hexdigest() != expected_sha256:
        raise RuntimeError("native runtime identity mismatch")

class LiteRTRuntime:
    """Pinned 0.16.0 CPU Engine; only this child imports native dependencies."""

    def __init__(self, *, model: str, runtime_root: str, native_sha256: str) -> None:
        # Authenticate the native bytes before importing a module that may load them.
        root_input = Path(runtime_root)
        if (
            not root_input.is_absolute()
            or root_input.is_symlink()
            or not root_input.is_dir()
            or root_input.resolve() != root_input
        ):
            raise RuntimeError("runtime root escaped verified closure")
        root = root_input
        native_path = root / "litert_lm/liblitert-lm.so"
        _verify_native_library(native_path, native_sha256)
        sys.path.insert(0, str(root))
        import litert_lm  # type: ignore[import-not-found]
        from litert_lm import (  # type: ignore[import-not-found]
            Backend,
            ConstrainedDecodingConfig,
            Engine,
            ResponseFormat,
            SamplerConfig,
        )
        from litert_lm._ffi import LiteRtLmConstraintProviderType  # type: ignore[import-not-found]

        module_input = Path(litert_lm.__file__)
        module_path = module_input.resolve()
        distribution = importlib.metadata.distribution("litert-lm-api")
        metadata_files = [
            Path(distribution.locate_file(item)).resolve()
            for item in distribution.files or ()
            if item.as_posix().endswith(".dist-info/METADATA")
        ]
        if (
            module_input.is_symlink()
            or module_input.parent.is_symlink()
            or not module_input.is_file()
            or root not in module_path.parents
            or distribution.version != "0.16.0"
            or len(metadata_files) != 1
            or root not in metadata_files[0].parents
            or metadata_files[0] != root / "litert_lm_api-0.16.0.dist-info/METADATA"
        ):
            raise RuntimeError("runtime import escaped verified closure")

        self._response_format = ResponseFormat
        self._sampler_config = SamplerConfig(temperature=0.0, top_p=1.0)
        self._cancelled_error = getattr(litert_lm, "Cancelled", WorkerCancelled)
        self._constraint = ConstrainedDecodingConfig(
            enable=True,
            provider=LiteRtLmConstraintProviderType.LL_GUIDANCE,
        )
        self._engine = Engine(
            model,
            backend=Backend.CPU(thread_count=4),
            max_num_tokens=1024,
            enable_benchmark=True,
        )
        from sbd.cognition.prompt_builder import attest_prompt
        attest_prompt(self._engine.tokenize)
        self._conversation: Any = None
        self._active: Any = None
        self._pending_cancel = False
        self._cancel_requested = False
        self._lock = threading.Lock()


    def open_conversation(self) -> None:
        require(self._conversation is None)
        self._conversation = self._engine.create_conversation(
            system_message=SYSTEM_PROMPT, automatic_tool_calling=False,
            constrained_decoding_config=self._constraint,
            sampler_config=self._sampler_config, max_output_tokens=128,
            filter_channel_content_from_kv_cache=False)

    def measure(self, text: str) -> dict[str, int]:
        conversation = self._conversation
        require(conversation is not None)
        before = conversation.token_count
        # Pinned native RenderMessageIntoString uses the same GetSingleTurnText
        # path as SendMessage. The product never uses has_pending_message:
        # RenderSingleTurnTemplateCommon returns false appending state and
        # never appends history. No inference/session input allocation occurs.
        rendered = conversation.render_message_to_string(text)
        require(type(rendered) is str and bool(rendered))
        user = len(self._engine.tokenize(text))
        incremental = len(self._engine.tokenize(rendered))
        # LiteRT counts the conversation's start token in the first native
        # prefill even though it is not present in the rendered message text.
        runtime_prefill = incremental + (1 if before == 0 else 0)
        require(conversation.token_count == before, "measurement")
        return {"user_tokens": user, "current_kv_tokens": before,
                "rendered_incremental_tokens": incremental,
                "runtime_prefill_tokens": runtime_prefill,
                "output_reserve_tokens": 128, "engine_context_tokens": 1024}

    def generate(self, text: str) -> tuple[str, int, int, int]:
        conversation = self._conversation
        require(conversation is not None)
        # Keep the POC-proven JSON-Schema constraint. LiteRT-LM's regex response
        # format changes greedy token selection and can terminate after a lone
        # punctuation mark even with the same model, prompt, and sampler.
        with self._lock:
            if self._pending_cancel:
                self._pending_cancel = False
                raise WorkerCancelled()
            self._active = conversation
        try:
            try:
                response_format = self._response_format.json(load_response_schema())
                _diagnostic_mark("response_format_selected", kind="json",
                                 response_schema_locator=RESPONSE_SCHEMA_LOCATOR,
                                 response_schema_sha256=RESPONSE_SCHEMA_SHA256)
                raw = conversation.send_message(text, max_output_tokens=128,
                    response_format=response_format)
            except self._cancelled_error:
                raise WorkerCancelled() from None
            _diagnostic_mark("native_generate_returned",
                raw_type=type(raw).__name__,
                raw_keys=(sorted(raw) if isinstance(raw, dict) else None),
                role=(raw.get("role") if isinstance(raw, dict) else None),
                content_type=(type(raw.get("content")).__name__
                              if isinstance(raw, dict) else None),
                content_count=(len(raw.get("content"))
                               if isinstance(raw, dict) and isinstance(raw.get("content"), list)
                               else None))
            require(type(raw) is dict and set(raw) == {"role", "content"})
            require(raw["role"] == "assistant" and type(raw["content"]) is list and len(raw["content"]) == 1)
            block = raw["content"][0]
            _diagnostic_mark("native_generate_block",
                block_type=type(block).__name__,
                block_keys=(sorted(block) if isinstance(block, dict) else None),
                block_kind=(block.get("type") if isinstance(block, dict) else None))
            require(type(block) is dict and set(block) == {"type", "text"} and block["type"] == "text")
            _diagnostic_mark("native_output", raw_json=block["text"])
            info = conversation.get_benchmark_info()
            _diagnostic_mark("native_generate_metrics",
                decode_tokens=info.last_decode_token_count,
                conversation_tokens=conversation.token_count,
                actual_prefill_tokens=info.last_prefill_token_count)
            return (block["text"], info.last_decode_token_count, conversation.token_count,
                    info.last_prefill_token_count)
        finally:
            with self._lock:
                self._active = None

    def scrub_ticket(self) -> None:
        conversation = self._conversation
        require(conversation is not None, "scrub")
        before = conversation.token_count
        require(type(before) is int and before >= 0, "scrub")
        rendered = conversation.render_message_to_string(TICKET_SCRUB_TEXT)
        require(type(rendered) is str and TICKET_SCRUB_TEXT in rendered, "scrub")
        require(bool(rendered.encode("utf-8")), "scrub")
        after = conversation.token_count
        require(type(after) is int and before == after, "scrub")

    def cancel(self) -> None:
        with self._lock:
            self._pending_cancel = True
            active = self._active
        if active is not None:
            active.cancel_process()

    def clear_pending_cancel(self) -> None:
        with self._lock:
            self._pending_cancel = False

    def close_conversation(self) -> None:
        conversation, self._conversation = self._conversation, None
        require(conversation is not None)
        conversation.close()

    def close(self) -> None:
        require(self._conversation is None)
        self._engine.close()


class WorkerSession:
    """Runtime-independent execution shared by native child and portable fake."""
    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime
        self.ledger = ProtocolLedger()

    def execute(self, frame: Mapping[str, object]) -> list[dict[str, object]]:
        # Caller has already accepted the command into the ledger.
        base = {key: frame[key] for key in ("protocol", "request_id", "session_id", "generation")}
        op = frame["op"]
        if op == "OPEN":
            self.runtime.open_conversation()
            return [{**base, "event": "OPENED", "conversation_revision": 0}]
        if op == "MEASURE":
            counts = self.runtime.measure(frame["text"])
            validate_counts(counts)
            return [{**base, "event": "MEASURED", **counts,
                "conversation_revision": self.ledger.revision,
                "input_sha256": frame["input_sha256"], "ticket": secrets.token_hex(16)}]
        if op == "CLOSE":
            self.runtime.close_conversation()
            return [{**base, "event": "CLOSED", "request_terminal_proven": True,
                "cleanup_proven": True, "engine_usable": True}]
        if op == "DISCARD_TICKET":
            self.runtime.scrub_ticket()
            self.ledger.ticket = None
            return [{**base, "event": "TICKET_DISCARDED",
                **{key: frame[key] for key in ("conversation_revision", "ticket", "input_sha256")},
                "native_render_scrubbed": True, "ticket_invalidated": True,
                "private_input_erased": True, "conversation_state": "ready"}]
        require(op == "GENERATE")
        counts = self.ledger.consumed
        require(counts is not None)
        require(counts["user_tokens"] <= 32)
        require(counts["current_kv_tokens"] + counts["rendered_incremental_tokens"] + 128 <= 1024)
        send = time.monotonic_ns()
        raw, decode, kv, actual_prefill = self.runtime.generate(frame["text"])
        _diagnostic_mark("native_prefill_check", request_id=frame.get("request_id"),
            expected_prefill_tokens=counts["runtime_prefill_tokens"],
            actual_prefill_tokens=actual_prefill)
        require(type(actual_prefill) is int and actual_prefill == counts["runtime_prefill_tokens"], "runtime_prefill")
        # Native synchronous SendMessage calls session WaitUntilDone; the
        # control loop additionally joins this worker thread before any terminal.
        try:
            semantic = validate_semantic(raw)
        except SemanticError:
            return [{**base, "event": "REQUEST_FAILED", "code": "INVALID_SEMANTIC",
                "request_terminal_proven": True, "engine_usable": True,
                "terminal_monotonic_ns": time.monotonic_ns()}]
        return [{**base, "event": "RESULT", "conversation_revision": self.ledger.revision + 1,
            "text": semantic.text, "end": semantic.end,
            **{key: counts[key] for key in ("user_tokens", "current_kv_tokens", "rendered_incremental_tokens", "runtime_prefill_tokens")},
            "decode_tokens": decode, "conversation_kv_tokens": kv,
            "llm_send_monotonic_ns": send, "first_safe_text_monotonic_ns": None,
            "terminal_monotonic_ns": time.monotonic_ns()}]


def _write(frame: Mapping[str, object]) -> None:
    sys.stdout.buffer.write(encode_frame(frame))
    sys.stdout.buffer.flush()


class _ControlInput:
    """Explicit bounded buffering, so coalesced CANCEL is visible to select."""
    def __init__(self, fd: int) -> None:
        self.fd = fd
        self.buffer = bytearray()

    def ready(self, timeout: float) -> bool:
        return bool(self.buffer) or bool(select.select([self.fd], [], [], timeout)[0])

    def read(self) -> dict[str, object]:
        while b"\n" not in self.buffer:
            require(len(self.buffer) <= MAX_CONTROL_BYTES, "frame")
            block = os.read(self.fd, MAX_CONTROL_BYTES + 1 - len(self.buffer))
            require(bool(block), "frame")
            self.buffer.extend(block)
        index = self.buffer.index(b"\n") + 1
        raw = bytes(self.buffer[:index])
        del self.buffer[:index]
        return decode_frame(raw)


def verify_platform_abi(profile: Mapping[str, object]) -> None:
    observed = (platform.python_implementation(), platform.python_version(),
                sysconfig.get_config_var("SOABI"), sysconfig.get_config_var("MULTIARCH"))
    expected = tuple(profile[key] for key in ("python_implementation", "python_version",
                                              "python_soabi", "python_multiarch"))
    require(observed == expected, "abi")
    require(sys.platform == "linux" and platform.machine() == "aarch64", "abi")
    require(sys.flags.isolated == 1 and sys.flags.no_user_site == 1, "abi")
    require(Path(sysconfig.get_path("stdlib")).resolve() == Path("/usr/lib/python3.13"), "abi")


def _network_filter_program() -> tuple[tuple[int, int, int, int], ...]:
    # Linux arm64 uses asm-generic syscall numbers. Check arch before numbers.
    # Deny socket/socketpair and io_uring creation; pidfd_getfd/ptrace cannot
    # import a socket from another owner. All inherited FDs are stdio pipes.
    # https://docs.kernel.org/userspace-api/seccomp_filter.html
    # Numeric ABI checked against torvalds/linux v6.12 include/uapi:
    # asm-generic/unistd.h:329,522-525,759,785; linux/audit.h:388-391;
    # linux/elf-em.h:46; linux/seccomp.h:38-46,62-67;
    # linux/bpf_common.h; linux/filter.h:24-33; linux/prctl.h:68,175.
    program = [(0x20, 0, 0, 4), (0x15, 1, 0, 0xC00000B7),
               (0x06, 0, 0, 0x80000000), (0x20, 0, 0, 0)]
    for number in (198, 199, 425, 438, 117):
        program.extend(((0x15, 0, 1, number), (0x06, 0, 0, 0x00050001)))
    program.append((0x06, 0, 0, 0x7FFF0000))
    return tuple(program)


def install_network_denial() -> None:
    """Unprivileged kernel filter installed before native import, or no READY."""
    require(sys.platform == "linux" and platform.machine() == "aarch64", "network")
    require(len(threading.enumerate()) == 1, "network")
    require(all(stat.S_ISFIFO(os.fstat(fd).st_mode) for fd in (0, 1)), "network")
    require(os.readlink("/proc/self/fd/2") == "/dev/null", "network")
    # close_fds at spawn plus this audit rules out inherited or pre-filter
    # sockets/rings. The scandir descriptor itself has closed before fstat.
    for name in os.listdir("/proc/self/fd"):
        fd = int(name)
        if fd <= 2:
            continue
        try:
            os.fstat(fd)
        except OSError as error:
            import errno
            require(error.errno == errno.EBADF, "network")
        else:
            require(False, "network")
    import ctypes
    class Filter(ctypes.Structure):
        _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
                    ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint32)]
    class Program(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.POINTER(Filter))]
    instructions = _network_filter_program()
    filters = (Filter * len(instructions))(*(Filter(*row) for row in instructions))
    program = Program(len(instructions), filters)
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    prctl.restype = ctypes.c_int
    require(prctl(38, 1, 0, 0, 0) == 0, "network")  # PR_SET_NO_NEW_PRIVS
    require(prctl(22, 2, ctypes.addressof(program), 0, 0) == 0, "network")


def run(runtime: Any, ready: Mapping[str, object]) -> int:
    session = WorkerSession(runtime)
    control = _ControlInput(sys.stdin.fileno())
    _write(ready)
    while True:
        frame = control.read()
        session.ledger.command(frame)
        if frame["op"] == "SHUTDOWN":
            runtime.close()
            ack = {"protocol": 3, "event": "SHUTDOWN_ACK"}
            session.ledger.event(ack)
            _write(ack)
            return 0
        result_queue: queue.Queue = queue.Queue()
        runtime.clear_pending_cancel()
        def execute() -> None:
            try:
                outcome = session.execute(frame)
            except WorkerCancelled:
                outcome = WorkerCancelled()
            except BaseException as error:
                _diagnostic_mark("native_operation_failed",
                    operation=frame.get("op"), request_id=frame.get("request_id"),
                    exception_type=type(error).__name__, exception=str(error),
                    traceback="".join(traceback.format_exception(error)))
                outcome = None
            # The native method stack has returned. Erase the shared request
            # payload before the thread can join and MEASURED can be emitted.
            frame.pop("text", None)
            result_queue.put(outcome)
        thread = threading.Thread(target=execute, name="llm-native", daemon=False)
        thread.start()
        while True:
            alive = thread.is_alive()
            if control.ready(0.01 if alive else 0):
                cancel = control.read()
                require(cancel.get("op") == "CANCEL")
                session.ledger.command(cancel)
                runtime.cancel()
                deferred = {"protocol": 3, "event": "CANCEL_DEFERRED", "request_id": frame["request_id"]}
                session.ledger.event(deferred)
                _write(deferred)
            elif not alive:
                break
        thread.join()
        events = result_queue.get_nowait()
        if session.ledger.cancelled:
            op = frame["op"]
            if op == "OPEN":
                runtime.close_conversation()
            if op == "MEASURE" and events is not None:
                # The joined renderer may have completed before cancellation.
                # No outstanding ticket remains after CANCELLED, so its native
                # input scratch must be scrubbed before claiming cleanup.
                try:
                    runtime.scrub_ticket()
                except BaseException:
                    events = None
            cancelled = {"protocol": 3, "event": "CANCELLED",
                "request_id": frame["request_id"], "operation": op,
                "request_terminal_proven": events is not None,
                "operation_cleanup_proven": op != "CLOSE" and events is not None,
                "engine_usable": events is not None,
                "conversation_state": ("tainted" if events is None else
                    {"OPEN": "none", "MEASURE": "ready", "GENERATE": "tainted", "CLOSE": "tainted"}[op])}
            # Invalid/missing proof is emitted for parent convergence, never
            # accepted locally as a usable transition.
            _write(cancelled)
            if events is None or op == "CLOSE":
                return 2
            session.ledger.event(cancelled)
        else:
            require(type(events) is list, "runtime")
            for event in events:
                session.ledger.event(event)
                _write(event)
        # Erase references to the completed private request and model response.
        frame = {}
        events = None


def main() -> int:
    global _DIAGNOSTIC_DIRECTORY
    _DIAGNOSTIC_DIRECTORY = None
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--product-profile", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--artifact-lock", required=True)
    parser.add_argument("--measurement-authorization")
    parser.add_argument("--measurement-pv", action="store_true")
    parser.add_argument("--measurement-private-directory")
    parser.add_argument("--measurement-user-diagnostic", action="store_true")
    parser.add_argument("--measurement-diagnostic-directory")
    parser.add_argument("--measurement-expected")
    args = parser.parse_args()
    require(bool(args.measurement_diagnostic_directory) == args.measurement_user_diagnostic,
            "measurement")
    require(bool(args.measurement_private_directory)
            == args.measurement_pv, "measurement")
    require(sum(bool(value) for value in (args.measurement_authorization,
        args.measurement_user_diagnostic, args.measurement_pv)) <= 1, "measurement")
    if args.measurement_pv:
        directory = Path(args.measurement_private_directory).resolve(strict=True)
        require(directory.is_dir() and not stat.S_IMODE(directory.stat().st_mode) & 0o077,
                "measurement")
        _DIAGNOSTIC_DIRECTORY = directory
    if args.measurement_user_diagnostic:
        directory = Path(args.measurement_diagnostic_directory).resolve(strict=True)
        require(directory.is_dir() and not stat.S_IMODE(directory.stat().st_mode) & 0o077,
                "measurement")
        _DIAGNOSTIC_DIRECTORY = directory
        _diagnostic_mark("child_starting", python=sys.version.split()[0])
    from sbd.cognition.litert_lm.lock import LLMArtifactLock, load_product_profile
    root = Path(__file__).resolve().parents[4]
    lock = LLMArtifactLock.load(Path(args.artifact_lock), repo_root=root)
    _diagnostic_mark("artifact_lock_verified")
    load_response_schema(repo_root=root)
    _diagnostic_mark("response_schema_verified",
                     response_schema_locator=RESPONSE_SCHEMA_LOCATOR,
                     response_schema_sha256=RESPONSE_SCHEMA_SHA256)
    measurement_mode = (bool(args.measurement_authorization) or args.measurement_user_diagnostic
                        or args.measurement_pv)
    require(measurement_mode == bool(args.measurement_expected), "measurement")
    grant = None
    if measurement_mode:
        from sbd.cognition.litert_lm.measurement import MeasurementGrant
        profile = load_product_profile(Path(args.product_profile), allow_measurement=True)
        expected = json.loads(args.measurement_expected)
        if args.measurement_pv:
            grant = MeasurementGrant.pv(expected_tuple=expected, profile=profile,
                private_directory=_DIAGNOSTIC_DIRECTORY)
        elif args.measurement_user_diagnostic:
            grant = MeasurementGrant.user_diagnostic(expected_tuple=expected, profile=profile,
                diagnostic_directory=_DIAGNOSTIC_DIRECTORY)
        else:
            grant = MeasurementGrant.load(Path(args.measurement_authorization),
                expected_tuple=expected, profile=profile)
    else:
        profile = load_product_profile(Path(args.product_profile))
    verify_platform_abi(profile)
    _diagnostic_mark("platform_abi_verified")
    if args.measurement_user_diagnostic:
        # This explicitly non-formal path is for rapid user-driven Pi debugging.
        # The launcher already binds exact paths and the native loader will fail
        # closed on unusable bytes; avoid rescanning the multi-gigabyte model.
        model_path = Path(args.model)
        require(Path(args.runtime_root).is_dir() and model_path.is_file()
                and not model_path.is_symlink(), "runtime")
        _diagnostic_mark("diagnostic_artifact_hash_skipped")
    else:
        require(lock.runtime_closure is not None, "runtime")
        lock.runtime_closure.verify_install(Path(args.runtime_root))
        _diagnostic_mark("runtime_closure_verified")
        # Reauthenticate paths in the child before native import/Engine creation.
        # Importing sbd.core.config executes its YAML-backed application loader. The
        # isolated native runtime intentionally contains only the locked LiteRT-LM
        # closure, so the worker uses the two path fields this verifier requires.
        cfg = SimpleNamespace(model_path=Path(args.model),
                              product_profile_path=Path(args.product_profile))
        lock.verify_config_paths(cfg, allow_measurement=grant is not None)
        _diagnostic_mark("model_profile_verified")
    install_network_denial()
    _diagnostic_mark("network_denial_installed")
    if _DIAGNOSTIC_DIRECTORY is not None:
        # Keep native C/C++ errors in the authorized private diagnostic bundle.
        # The inherited-descriptor audit and network filter have already run.
        descriptor = os.open(_DIAGNOSTIC_DIRECTORY / f"llm-child-{os.getpid()}-stderr.log",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            os.dup2(descriptor, 2)
        finally:
            os.close(descriptor)
    native_started = time.monotonic_ns()
    _diagnostic_mark("native_runtime_starting")
    runtime = LiteRTRuntime(model=args.model, runtime_root=args.runtime_root,
                            native_sha256=lock.runtime["native_sha256"])
    _diagnostic_mark("native_runtime_ready",
                     startup_duration_ns=time.monotonic_ns() - native_started)
    ready = {"protocol": 3, "event": "READY", **lock.ready_identity(profile).fields,
             "pid": os.getpid(), "pgid": os.getpgrp()}
    require(os.getpid() == os.getpgrp(), "pid")
    _diagnostic_mark("ready_emitting")
    return run(runtime, ready)


if __name__ == "__main__":
    try:
        status = main()
    except BaseException as error:
        try:
            _diagnostic_mark("child_failed", exception_type=type(error).__name__,
                exception=str(error), traceback="".join(traceback.format_exception(error)))
        except BaseException:
            pass
        status = 2
    # Parent is responsible for descendant/exit proof, including startup failure.
    os._exit(status)
