"""Git-safe append-only M4C-SS evidence helpers."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any


FORBIDDEN_KEYS = frozenset({
    "audio_bytes", "credential", "host", "model_output", "path", "pcm", "prompt",
    "raw", "raw_audio", "session_id", "transcript",
})


class EvidenceError(ValueError):
    pass


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise EvidenceError("NON_CANONICAL_VALUE") from error


def require_sanitized(value: Any) -> None:
    """Reject private-content field names recursively before any disk write."""

    if isinstance(value, dict):
        for key, child in value.items():
            if type(key) is not str:
                raise EvidenceError("NON_STRING_KEY")
            lowered = key.lower()
            if lowered in FORBIDDEN_KEYS or any(
                lowered.startswith(prefix + "_") or lowered.endswith("_" + prefix)
                for prefix in FORBIDDEN_KEYS
            ):
                raise EvidenceError("PRIVATE_FIELD")
            require_sanitized(child)
    elif isinstance(value, list):
        for child in value:
            require_sanitized(child)
    elif value is not None and type(value) not in {str, int, float, bool}:
        raise EvidenceError("NON_JSON_VALUE")


def _safe_component(value: str, label: str) -> str:
    if (
        type(value) is not str or not value or len(value) > 256
        or value in {".", ".."} or "/" in value or "\\" in value
        or not all(character.isalnum() or character in "-_.:" for character in value)
    ):
        raise EvidenceError(f"INVALID_{label}")
    return value


class SanitizedEvidenceWriter:
    """Reserve one case directory and never overwrite an existing record."""

    def __init__(self, root: Path, run_id: str, case_key: str) -> None:
        self.root = root.resolve()
        self.run_id = _safe_component(run_id, "RUN_ID")
        self.case_key = _safe_component(case_key, "CASE_KEY")
        self.directory = self.root / self.run_id / self.case_key
        self.directory.mkdir(parents=True, exist_ok=False)
        self._events = (self.directory / "events.jsonl").open("x", encoding="utf-8")
        self._closed = False

    def append(self, event: dict[str, Any]) -> None:
        if self._closed:
            raise EvidenceError("WRITER_CLOSED")
        try:
            require_sanitized(event)
            encoded = canonical_bytes(event).decode("utf-8")
        except Exception:
            self.close_incomplete()
            raise
        self._events.write(encoded + "\n")
        self._events.flush()
        os.fsync(self._events.fileno())

    def finalize(self, summary: dict[str, Any]) -> dict[str, Any]:
        if self._closed:
            raise EvidenceError("WRITER_CLOSED")
        try:
            require_sanitized(summary)
            encoded = json.dumps(
                summary, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False,
            ) + "\n"
        except (EvidenceError, TypeError, ValueError):
            self.close_incomplete()
            raise
        self._events.close()
        summary_path = self.directory / "summary.json"
        with summary_path.open("x", encoding="utf-8") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        manifest = bundle_manifest(self.directory)
        self._closed = True
        return manifest

    def close_incomplete(self) -> None:
        """Close the reserved partition without deleting or disguising it."""

        if not self._closed:
            self._events.flush()
            os.fsync(self._events.fileno())
            self._events.close()
            self._closed = True


def bundle_manifest(directory: Path) -> dict[str, Any]:
    root = directory.resolve()
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise EvidenceError("SYMLINK_FORBIDDEN")
        if not path.is_file():
            continue
        relative = PurePosixPath(path.relative_to(root).as_posix())
        if relative.name == "manifest.json":
            continue
        content = path.read_bytes()
        files.append({
            "path": str(relative),
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        })
    value = {"format": "m4c-ss-private-bundle-manifest-v1", "files": files}
    return {**value, "manifest_sha256": hashlib.sha256(canonical_bytes(value)).hexdigest()}
