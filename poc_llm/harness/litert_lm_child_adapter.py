#!/usr/bin/env python3
"""Persistent LiteRT-LM child for the ARM64 WIP pre-screen.

Protocol stdout contains JSON-lines frames only. Diagnostics never include prompts,
model output, host identity, or private paths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import threading
from typing import Any, Protocol, TextIO

from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CONTRACT_ROOT = ROOT / "poc_llm/contracts/m1"
PROTOCOL_VERSION = "snowboard.llm/1"


class Cancelled(RuntimeError):
    pass


class Backend(Protocol):
    def generate(self, prompt: str, *, max_output_tokens: int) -> str: ...
    def cancel(self) -> None: ...
    def close(self) -> None: ...


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _protocol_validator() -> Draft202012Validator:
    protocol = json.loads((CONTRACT_ROOT / "protocol-frame-arm64.schema.json").read_text(encoding="utf-8"))
    prompt = json.loads((CONTRACT_ROOT / "prompt-input.schema.json").read_text(encoding="utf-8"))
    response = json.loads((CONTRACT_ROOT / "response.schema.json").read_text(encoding="utf-8"))
    store = {item["$id"]: item for item in (protocol, prompt, response)}
    return Draft202012Validator(
        protocol, resolver=RefResolver.from_schema(protocol, store=store)
    )


def _strict_config_validator() -> Draft202012Validator:
    schema = json.loads(
        (CONTRACT_ROOT / "strict-config-arm64.schema.json").read_text(encoding="utf-8")
    )
    return Draft202012Validator(schema)


def _prompt(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return (
        "Return exactly one JSON object with action_kind, action_payload, and "
        "next_perceptions. Do not add markdown or commentary. Input: " + payload
    )


def _text_content(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        return "".join(_text_content(item) for item in value.get("content", []))
    if isinstance(value, list):
        return "".join(_text_content(item) for item in value)
    return ""


class LiteRtBackend:
    def __init__(self, config: dict[str, Any]):
        import litert_lm  # Imported only after immutable input authentication.

        self._engine = litert_lm.Engine(
            config["model_path"],
            backend=litert_lm.Backend.CPU(thread_count=config["threads"]),
        )
        self._conversation = None
        self._lock = threading.Lock()
        self._sampler = litert_lm.SamplerConfig(
            temperature=config["temperature"], top_p=config["top_p"]
        )

    def generate(self, prompt: str, *, max_output_tokens: int) -> str:
        conversation = self._engine.create_conversation(
            sampler_config=self._sampler,
            max_output_tokens=max_output_tokens,
            automatic_tool_calling=False,
        )
        with self._lock:
            self._conversation = conversation
        try:
            return "".join(_text_content(chunk) for chunk in conversation.send_message_async(prompt))
        except RuntimeError as error:
            if "CANCELLED" in str(error):
                raise Cancelled("generation cancelled") from error
            raise
        finally:
            with self._lock:
                self._conversation = None
            conversation.close()

    def cancel(self) -> None:
        with self._lock:
            conversation = self._conversation
        if conversation is not None:
            conversation.cancel_process()

    def close(self) -> None:
        self.cancel()
        self._engine.close()


class Child:
    def __init__(
        self,
        config: dict[str, Any],
        config_sha256: str,
        backend: Backend,
        output: TextIO,
    ):
        self.config = config
        self.config_sha256 = config_sha256
        self.backend = backend
        self.output = output
        self.protocol = _protocol_validator()
        self.active_request: str | None = None
        self.cancel_requested = False
        self.timeout_requested = False
        self.timer: threading.Timer | None = None
        self.worker: threading.Thread | None = None
        self.closed = False
        self.lock = threading.Lock()
        self.output_lock = threading.Lock()

    def emit(self, frame: dict[str, Any]) -> None:
        with self.output_lock:
            self.output.write(json.dumps(frame, sort_keys=True, separators=(",", ":")) + "\n")
            self.output.flush()

    def ready(self) -> None:
        self.emit({
            "type":"READY", "protocol_version":PROTOCOL_VERSION, "state":"READY",
            "identity":{
                "candidate_id":self.config["candidate_id"],
                "pairing_revision":self.config["pairing_revision"],
                "platform":self.config["platform"],
                "runtime_sha256":self.config["runtime_sha256"],
                "model_sha256":self.config["model_sha256"],
                "config_sha256":self.config_sha256,
            },
        })

    def _terminal(self, request_id: str, raw_output: str | None, error: Exception | None) -> None:
        from poc_llm.harness.m1_contract_boundary import normalize_response

        with self.lock:
            cancelled = self.cancel_requested
            timed_out = self.timeout_requested
            timer = self.timer
            self.timer = None
        if timer is not None:
            timer.cancel()
        if timed_out:
            frame = {"type":"ERROR","protocol_version":PROTOCOL_VERSION,"request_id":request_id,"code":"TIMEOUT","state":"READY"}
        elif cancelled or isinstance(error, Cancelled):
            frame = {"type":"CANCELLED","protocol_version":PROTOCOL_VERSION,"request_id":request_id,"state":"READY"}
        elif error is not None:
            frame = {"type":"ERROR","protocol_version":PROTOCOL_VERSION,"request_id":request_id,"code":"GENERATION_FAILED","state":"READY"}
        else:
            response, _diagnostics = normalize_response(raw_output, self._active_input)
            frame = {"type":"RESULT","protocol_version":PROTOCOL_VERSION,"request_id":request_id,"response":response,"state":"READY"}
        with self.lock:
            self.active_request = None
            self.cancel_requested = False
            self.timeout_requested = False
        self.emit(frame)

    def _timeout(self, request_id: str) -> None:
        with self.lock:
            if self.active_request != request_id or self.cancel_requested:
                return
            self.timeout_requested = True
        self.backend.cancel()

    def _generate(self, request_id: str, value: dict[str, Any]) -> None:
        raw_output = None
        error = None
        try:
            raw_output = self.backend.generate(
                _prompt(value), max_output_tokens=self.config["max_output_tokens"]
            )
        except Exception as caught:  # Sanitized at the protocol boundary.
            error = caught
        self._terminal(request_id, raw_output, error)

    def handle(self, frame: dict[str, Any]) -> bool:
        errors = list(self.protocol.iter_errors(frame))
        if errors or frame.get("type") == "READY":
            request_id = frame.get("request_id")
            if isinstance(request_id, str) and request_id:
                state = "GENERATING" if self.active_request else "READY"
                self.emit({"type":"ERROR","protocol_version":PROTOCOL_VERSION,"request_id":request_id,"code":"INVALID_REQUEST","state":state})
                return True
            return False
        frame_type = frame["type"]
        if frame_type == "GENERATE":
            with self.lock:
                if self.active_request is not None:
                    self.emit({"type":"ERROR","protocol_version":PROTOCOL_VERSION,"request_id":frame["request_id"],"code":"BUSY","state":"GENERATING"})
                    return True
                self.active_request = frame["request_id"]
                self._active_input = frame["input"]
                self.timer = threading.Timer(
                    self.config["generate_timeout_ms"] / 1000,
                    self._timeout,
                    args=(frame["request_id"],),
                )
                self.worker = threading.Thread(
                    target=self._generate,
                    args=(frame["request_id"], frame["input"]),
                    name="litert-generation",
                )
                self.timer.start()
                self.worker.start()
            return True
        if frame_type == "CANCEL":
            with self.lock:
                if frame["request_id"] != self.active_request:
                    state = "GENERATING" if self.active_request else "READY"
                    self.emit({"type":"ERROR","protocol_version":PROTOCOL_VERSION,"request_id":frame["request_id"],"code":"INVALID_REQUEST","state":state})
                    return True
                self.cancel_requested = True
            self.backend.cancel()
            return True
        if frame_type == "SHUTDOWN":
            with self.lock:
                if self.active_request is not None:
                    return False
            self.emit({"type":"SHUTDOWN_ACK","protocol_version":PROTOCOL_VERSION})
            self.closed = True
            return False
        return False

    def close(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            self.backend.cancel()
            self.worker.join(timeout=self.config["term_timeout_ms"] / 1000)
        self.backend.close()


def load_authenticated_config(path: Path, expected_sha256: str) -> dict[str, Any]:
    path = path.resolve()
    if digest(path) != expected_sha256:
        raise ValueError("config identity mismatch")
    config = json.loads(path.read_text(encoding="utf-8"))
    errors = list(_strict_config_validator().iter_errors(config))
    if errors:
        raise ValueError("strict config schema mismatch")
    for key, sha_key in (("runtime_path","runtime_sha256"),("model_path","model_sha256")):
        artifact = Path(config[key])
        if not artifact.is_absolute() or artifact.resolve() != artifact or digest(artifact) != config[sha_key]:
            raise ValueError(f"{key} identity mismatch")
    return config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha256", required=True)
    args = parser.parse_args()
    try:
        config = load_authenticated_config(args.config, args.config_sha256)
        backend = LiteRtBackend(config)
    except Exception:
        print("adapter startup authentication failed", file=sys.stderr)
        return 2
    child = Child(config, args.config_sha256, backend, sys.stdout)
    child.ready()
    try:
        for line in sys.stdin:
            try:
                frame = json.loads(line)
            except (json.JSONDecodeError, UnicodeError):
                break
            if not isinstance(frame, dict) or not child.handle(frame):
                break
    finally:
        child.close()
    return 0 if child.closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
