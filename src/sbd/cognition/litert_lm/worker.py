"""Isolated M4b LiteRT-LM worker; selected runtime imports occur only here."""

from __future__ import annotations

import argparse
import json
import hashlib
import importlib.metadata
import math
import os
import queue
import select
import stat
import sys
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# The child uses the isolated CPython runtime but executes the exact candidate
# worker file selected by the controller.  Add only that candidate's package
# root; no environment-provided PYTHONPATH or system-site path is accepted.
_CANDIDATE_PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(_CANDIDATE_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CANDIDATE_PACKAGE_ROOT))

from sbd.cognition.llm_child_protocol import (
    MAX_CONTROL_BYTES,
    PROTOCOL_VERSION,
    encode_frame,
    parse_cancel,
    parse_generate,
)


PROMPT_PREFIX = (
    "Return exactly one JSON object with action_kind, action_payload, and "
    "next_perceptions. Do not add markdown or commentary. Input: "
)


class WorkerCancelled(RuntimeError):
    pass


class WorkerInputTooLarge(ValueError):
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
        raise RuntimeError("native runtime identity mismatch") from error
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


def _render_prompt(value: Mapping[str, object]) -> str:
    return PROMPT_PREFIX + json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )


def _next_perceptions_schema(available: list[str], *, nonempty: bool) -> dict[str, object]:
    schema: dict[str, object] = {
        "type": "array",
        "items": {"type": "string", "enum": available},
        "uniqueItems": True,
        "maxItems": len(available),
    }
    schema["minItems"] = 1 if nonempty else 0
    return schema


def _branch(kind: str, payload: Mapping[str, object], perceptions: dict[str, object]) -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "action_kind": {"const": kind},
            "action_payload": payload,
            "next_perceptions": perceptions,
        },
        "required": ["action_kind", "action_payload", "next_perceptions"],
        "additionalProperties": False,
    }


def _build_response_schema(value: Mapping[str, object]) -> dict[str, object]:
    capabilities = value["capabilities"]
    if type(capabilities) is not dict:
        raise ValueError("invalid capabilities")
    actions = capabilities["actions"]
    perceptions = capabilities["perceptions"]
    tools = capabilities["tools"]
    if type(actions) is not list or type(perceptions) is not list or type(tools) is not list:
        raise ValueError("invalid capabilities")
    branches: list[dict[str, object]] = []
    nonempty = _next_perceptions_schema(perceptions, nonempty=True)
    if "speak" in actions:
        branches.append(_branch("speak", {
            "type": "object",
            "properties": {"text": {"type": "string", "minLength": 1, "pattern": r".*\S.*"}},
            "required": ["text"],
            "additionalProperties": False,
        }, nonempty))
    if "tool" in actions:
        for tool in sorted(tools, key=lambda item: item["name"]):
            branches.append(_branch("tool", {
                "type": "object",
                "properties": {
                    "name": {"const": tool["name"]},
                    "arguments": {"type": "object"},
                },
                "required": ["name", "arguments"],
                "additionalProperties": False,
            }, nonempty))
    if "rest" in actions:
        branches.append(_branch("rest", {
            "type": "object", "properties": {}, "required": [], "additionalProperties": False,
        }, _next_perceptions_schema([], nonempty=False)))
    if not branches:
        raise ValueError("no constrained response branch")
    return {"oneOf": branches}


def _litert_constraint_schema(value: object) -> object:
    """Project the exact product schema onto LiteRT-LM 0.16.0's surface.

    LLGuidance in the selected runtime rejects ``uniqueItems`` before
    inference.  The worker still validates uniqueness against the exact
    product contract after decoding, so this projection only removes the
    unsupported native keyword; it does not relax delivered responses.
    """
    if type(value) is dict:
        return {
            key: _litert_constraint_schema(item)
            for key, item in value.items()
            if key != "uniqueItems"
        }
    if type(value) is list:
        return [_litert_constraint_schema(item) for item in value]
    return value


class LiteRTRuntime:
    """Narrow wrapper around one persistent Engine and fresh Conversations."""

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
        self._active: Any = None
        self._pending_cancel = False
        self._cancel_requested = False
        self._lock = threading.Lock()

    def _activate(self, conversation: Any) -> bool:
        with self._lock:
            self._active = conversation
            pending_cancel = self._pending_cancel
            self._pending_cancel = False
            if pending_cancel:
                self._cancel_requested = True
        if pending_cancel:
            try:
                conversation.cancel_process()
            except BaseException as error:
                raise WorkerCancelFailed("native cancellation failed") from error
        return pending_cancel

    def _deactivate(self) -> None:
        with self._lock:
            self._active = None

    def clear_pending_cancel(self) -> None:
        with self._lock:
            self._pending_cancel = False
            self._cancel_requested = False

    def generate(self, value: Mapping[str, object]) -> tuple[dict[str, object], dict[str, object]]:
        schema = _build_response_schema(value)
        constraint_schema = _litert_constraint_schema(schema)
        prompt = _render_prompt(value)
        conversation = self._engine.create_conversation(
            automatic_tool_calling=False,
            constrained_decoding_config=self._constraint,
            max_output_tokens=128,
        )
        try:
            if self._activate(conversation):
                raise WorkerCancelled("generation cancelled before inference")
            rendered = conversation.render_message_to_string(prompt)
            rendered_token_count = len(self._engine.tokenize(rendered))
            if rendered_token_count > 128:
                raise WorkerInputTooLarge("rendered input exceeds token limit")
            with self._lock:
                cancel_requested = self._cancel_requested
            if cancel_requested:
                raise WorkerCancelled("generation cancelled before inference")
            try:
                raw = conversation.send_message(
                    prompt,
                    max_output_tokens=128,
                    response_format=self._response_format.json(constraint_schema),
                )
            except self._cancelled_error as error:
                raise WorkerCancelled("native inference cancelled") from error
            except RuntimeError as error:
                # API 0.16.0 may surface the native typed cancellation through
                # its exact C-API marker instead of exporting the subclass.
                if str(error) == "CANCELLED":
                    raise WorkerCancelled("native inference cancelled") from error
                raise
            response = _product_response(raw)
            _validate_product_response(response, value)
            info = conversation.get_benchmark_info()
            metrics = {
                "init_ms": float(info.init_time_in_second) * 1000.0,
                "ttft_ms": float(info.time_to_first_token_in_second) * 1000.0,
                "prefill_tokens": int(info.last_prefill_token_count),
                "prefill_tokens_per_second": float(info.last_prefill_tokens_per_second),
                "decode_tokens": int(info.last_decode_token_count),
                "decode_tokens_per_second": float(info.last_decode_tokens_per_second),
                "kv_tokens": int(conversation.token_count),
            }
            return response, metrics
        finally:
            self._deactivate()
            conversation.close()

    def cancel(self) -> None:
        with self._lock:
            active = self._active
            self._cancel_requested = True
            if active is None:
                self._pending_cancel = True
                return
        active.cancel_process()

    def close(self) -> None:
        self._engine.close()


def _product_response(raw: object) -> dict[str, object]:
    if type(raw) is dict and set(raw) == {"action_kind", "action_payload", "next_perceptions"}:
        return raw
    if type(raw) is dict and set(raw) == {"role", "content"}:
        content = raw["content"]
        if type(content) is list and len(content) == 1 and type(content[0]) is dict and set(content[0]) == {"type", "text"} and content[0]["type"] == "text":
            try:
                decoded = json.loads(content[0]["text"])
            except (TypeError, json.JSONDecodeError) as error:
                raise ValueError("runtime response is not product JSON") from error
            if type(decoded) is dict and set(decoded) == {"action_kind", "action_payload", "next_perceptions"}:
                return decoded
    raise ValueError("runtime response envelope is invalid")


def _validate_product_response(
    response: Mapping[str, object], value: Mapping[str, object],
) -> None:
    if set(response) != {"action_kind", "action_payload", "next_perceptions"}:
        raise ValueError("runtime response schema mismatch")
    capabilities = value["capabilities"]
    if type(capabilities) is not dict:
        raise ValueError("runtime response capability mismatch")
    actions = capabilities["actions"]
    perceptions = capabilities["perceptions"]
    tools = capabilities["tools"]
    kind = response["action_kind"]
    payload = response["action_payload"]
    requested = response["next_perceptions"]
    if (
        type(kind) is not str
        or type(payload) is not dict
        or type(requested) is not list
        or any(type(item) is not str for item in requested)
        or len(requested) != len(set(requested))
        or any(item not in perceptions for item in requested)
    ):
        raise ValueError("runtime response value mismatch")
    if kind == "speak":
        if (
            kind not in actions
            or set(payload) != {"text"}
            or type(payload["text"]) is not str
            or not payload["text"].strip()
            or not requested
        ):
            raise ValueError("runtime speak response mismatch")
        return
    if kind == "tool":
        matched = next((
            tool for tool in tools
            if type(tool) is dict and tool.get("name") == payload.get("name")
        ), None)
        if (
            kind not in actions
            or set(payload) != {"name", "arguments"}
            or matched is None
            or type(payload["arguments"]) is not dict
            or not requested
        ):
            raise ValueError("runtime tool response mismatch")
        return
    if kind != "rest" or kind not in actions or payload or requested:
        raise ValueError("runtime rest response mismatch")


def _write(value: Mapping[str, object]) -> None:
    sys.stdout.buffer.write(encode_frame(value))
    sys.stdout.buffer.flush()


def _exit_after_shutdown_ack() -> None:
    """Exit without re-entering the selected runtime's native teardown."""
    os._exit(0)


def _read_line() -> dict[str, object]:
    raw = sys.stdin.buffer.readline(MAX_CONTROL_BYTES + 1)
    if not raw or len(raw) > MAX_CONTROL_BYTES or not raw.endswith(b"\n"):
        raise ValueError("invalid bounded control frame")
    value = json.loads(raw.decode("utf-8"))
    if type(value) is not dict:
        raise ValueError("control frame is not an object")
    return value


def _advance_request_identity(
    request_id: str,
    generation: int | None,
    counter: int,
) -> tuple[int, int]:
    _, generation_text, counter_text = request_id.split(".")
    observed_generation = int(generation_text)
    observed_counter = int(counter_text)
    if (
        observed_generation < 1
        or observed_counter != counter + 1
        or (generation is not None and observed_generation != generation)
    ):
        raise ValueError("request identity sequence mismatch")
    return observed_generation, observed_counter


def _terminal_from_outcome(
    request_id: str,
    kind: str,
    payload: object,
    *,
    cancel_sent: bool,
) -> dict[str, object]:
    if kind == "cancel_failed":
        return {
            "type": "ERROR", "protocol_version": PROTOCOL_VERSION,
            "request_id": request_id, "code": "CANCEL_FAILED", "state": "FATAL",
        }
    if cancel_sent:
        return {
            "type": "CANCELLED", "protocol_version": PROTOCOL_VERSION,
            "request_id": request_id, "state": "READY",
        }
    if kind == "result":
        response, metrics = payload  # type: ignore[misc]
        return {
            "type": "RESULT", "protocol_version": PROTOCOL_VERSION,
            "request_id": request_id, "response": response,
            "metrics": metrics, "state": "READY",
        }
    code = "INVALID_REQUEST" if kind == "invalid_request" else "GENERATION_FAILED"
    return {
        "type": "ERROR", "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id, "code": code, "state": "READY",
    }


def _prewarm(runtime: LiteRTRuntime) -> None:
    value = {
        "perceptions": [{"kind": "listen", "status": "ok", "text": "Say ready."}],
        "pending_message_count": 0,
        "capabilities": {"perceptions": ["listen"], "actions": ["speak"], "tools": []},
    }
    response, metrics = runtime.generate(value)
    _validate_product_response(response, value)
    if not response or int(metrics["decode_tokens"]) <= 0:
        raise RuntimeError("prewarm failed")


def _write_startup_evidence(
    path: Path, *, engine_load_latency_ms: float, prewarm_latency_ms: float,
) -> None:
    value = {
        "schema_version": 1,
        "engine_load_latency_ms": engine_load_latency_ms,
        "prewarm_latency_ms": prewarm_latency_ms,
        "prewarm_prompt_sha256": hashlib.sha256(_render_prompt({
            "perceptions": [{"kind": "listen", "status": "ok", "text": "Say ready."}],
            "pending_message_count": 0,
            "capabilities": {"perceptions": ["listen"], "actions": ["speak"], "tools": []},
        }).encode()).hexdigest(),
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        written = 0
        while written < len(payload):
            written += os.write(descriptor, payload[written:])
    finally:
        os.close(descriptor)


def run(args: argparse.Namespace) -> int:
    engine_started = time.monotonic()
    runtime = LiteRTRuntime(
        model=args.model,
        runtime_root=args.runtime_root,
        native_sha256=args.native_sha256,
    )
    engine_load_latency_ms = (time.monotonic() - engine_started) * 1000.0
    try:
        prewarm_started = time.monotonic()
        _prewarm(runtime)
        prewarm_latency_ms = (time.monotonic() - prewarm_started) * 1000.0
        _write_startup_evidence(
            Path(args.startup_evidence),
            engine_load_latency_ms=engine_load_latency_ms,
            prewarm_latency_ms=prewarm_latency_ms,
        )
        _write({
            "type": "READY", "protocol_version": PROTOCOL_VERSION, "state": "READY",
            "identity": {
                "candidate_id": args.candidate_id,
                "pairing_revision": args.pairing_revision,
                "platform": args.platform,
                "runtime_sha256": args.runtime_sha256,
                "model_sha256": args.model_sha256,
                "config_sha256": args.config_sha256,
            },
        })
        outcomes: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=1)
        active_id: str | None = None
        worker: threading.Thread | None = None
        cancel_sent = False
        request_generation: int | None = None
        request_counter = 0
        while True:
            if worker is not None and not worker.is_alive():
                worker.join()
                kind, payload = outcomes.get_nowait()
                assert active_id is not None
                _write(_terminal_from_outcome(
                    active_id, kind, payload, cancel_sent=cancel_sent,
                ))
                if kind == "cancel_failed":
                    return 2
                runtime.clear_pending_cancel()
                active_id = None
                worker = None
                cancel_sent = False
            readable, _, _ = select.select([sys.stdin.buffer], [], [], 0.05)
            if not readable:
                continue
            frame = _read_line()
            frame_type = frame.get("type")
            if frame_type == "GENERATE":
                if worker is not None:
                    request_id = str(frame.get("request_id", "llm.0.0"))
                    _write({"type": "ERROR", "protocol_version": PROTOCOL_VERSION, "request_id": request_id, "code": "BUSY", "state": "GENERATING"})
                    continue
                request_id, value = parse_generate(frame)
                request_generation, request_counter = _advance_request_identity(
                    request_id, request_generation, request_counter,
                )
                active_id = request_id

                def infer() -> None:
                    try:
                        outcomes.put(("result", runtime.generate(value)))
                    except WorkerInputTooLarge:
                        outcomes.put(("invalid_request", None))
                    except WorkerCancelled:
                        outcomes.put(("cancelled", None))
                    except WorkerCancelFailed:
                        outcomes.put(("cancel_failed", None))
                    except BaseException as error:
                        outcomes.put(("error", type(error).__name__))

                worker = threading.Thread(target=infer, name="m4b-inference", daemon=False)
                worker.start()
            elif frame_type == "CANCEL":
                request_id = parse_cancel(frame)
                if worker is None or request_id != active_id:
                    raise ValueError("cancel identity mismatch")
                if not cancel_sent:
                    cancel_sent = True
                    try:
                        runtime.cancel()
                    except BaseException:
                        _write({
                            "type": "ERROR", "protocol_version": PROTOCOL_VERSION,
                            "request_id": request_id, "code": "CANCEL_FAILED", "state": "FATAL",
                        })
                        return 2
            elif frame == {"type": "PING", "protocol_version": PROTOCOL_VERSION} and worker is None:
                _write({"type": "PONG", "protocol_version": PROTOCOL_VERSION, "state": "READY"})
            elif frame == {"type": "SHUTDOWN", "protocol_version": PROTOCOL_VERSION} and worker is None:
                _write({"type": "SHUTDOWN_ACK", "protocol_version": PROTOCOL_VERSION})
                _exit_after_shutdown_ack()
                return 0
            else:
                raise ValueError("invalid control operation")
    finally:
        runtime.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    for name in (
        "model", "product-config", "runtime-root", "candidate-id",
        "pairing-revision", "platform", "runtime-sha256", "model-sha256",
        "config-sha256", "native-sha256",
        "startup-evidence",
    ):
        parser.add_argument(f"--{name}", required=True)
    return parser


def main() -> int:
    try:
        return run(_parser().parse_args())
    except BaseException:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "PROMPT_PREFIX", "_build_response_schema", "_render_prompt",
    "_advance_request_identity", "_terminal_from_outcome",
    "_validate_product_response", "_verify_native_library",
    "_write_startup_evidence",
    "LiteRTRuntime", "WorkerCancelFailed", "WorkerInputTooLarge",
]
