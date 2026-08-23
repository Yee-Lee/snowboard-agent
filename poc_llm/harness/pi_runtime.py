"""Shared fail-closed runtime helpers for physical-Pi LLM packets."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import selectors
import signal
import subprocess
import time
from typing import Any, TextIO

from jsonschema import Draft202012Validator, RefResolver


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_VERSION = "snowboard.llm/1"


class PiPacketFailure(RuntimeError):
    pass


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def git_state() -> tuple[str, bool]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, check=True,
        capture_output=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True, check=True,
        capture_output=True,
    ).stdout
    return head, not bool(dirty)


def meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        if name in {"MemTotal", "MemAvailable", "SwapTotal"}:
            values[name] = int(value.split()[0]) * 1024
    return values


def os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')
    return values


def offline_routes() -> bool:
    route4 = Path("/proc/net/route").read_text(encoding="ascii").splitlines()[1:]
    route6 = Path("/proc/net/ipv6_route").read_text(encoding="ascii").splitlines()
    return not any(line.strip() for line in route4) and all(
        line.split()[-1] == "lo" for line in route6 if line.strip()
    )


def offline_environment() -> dict[str, Any]:
    """Return a small, non-sensitive proof that scored execution is offline."""
    interfaces: dict[str, str] = {}
    for interface in Path("/sys/class/net").iterdir():
        if interface.name == "lo":
            continue
        state = (interface / "operstate").read_text(encoding="ascii").strip()
        interfaces[interface.name] = state
    sensitive = sorted(
        name for name in os.environ
        if any(token in name.lower() for token in (
            "proxy", "token", "api_key", "apikey", "secret", "credential",
        ))
    )
    if not offline_routes() or any(state != "down" for state in interfaces.values()) or sensitive:
        raise PiPacketFailure("offline environment proof failed")
    return {
        "routes_offline": True,
        "non_loopback_interfaces": interfaces,
        "sensitive_environment_names": sensitive,
    }


def throttle_preflight() -> str:
    probe = subprocess.run(
        ["vcgencmd", "get_throttled"], text=True, capture_output=True, check=False,
    )
    state = probe.stdout.strip()
    if probe.returncode != 0 or state != "throttled=0x0":
        raise PiPacketFailure("Pi prelaunch throttling state is not clean")
    return state


def native_library_preflight(path: Path, expected_sha256: str) -> dict[str, str]:
    """Authenticate the installed native library and reject wrong ELF/linkage early."""
    if not path.is_file() or digest(path) != expected_sha256:
        raise PiPacketFailure("installed native library identity mismatch")
    header = subprocess.run(
        ["readelf", "-h", str(path)], text=True, capture_output=True, check=False,
    )
    if (header.returncode != 0 or "Class:" not in header.stdout
            or "ELF64" not in header.stdout or "Machine:" not in header.stdout
            or "AArch64" not in header.stdout):
        raise PiPacketFailure("installed native library ELF identity mismatch")
    linkage = subprocess.run(
        ["ldd", str(path)], text=True, capture_output=True, check=False,
    )
    if linkage.returncode != 0 or "not found" in linkage.stdout:
        raise PiPacketFailure("installed native library linkage mismatch")
    return {"native_library_sha256": expected_sha256, "elf_machine": "AArch64", "linkage": "resolved"}


def target_preflight(expected_sha: str) -> dict[str, Any]:
    release = os_release()
    memory = meminfo()
    head, clean = git_state()
    if (
        head != expected_sha or not clean or release.get("ID") != "debian"
        or release.get("VERSION_ID") != "13" or platform.machine() != "aarch64"
        or memory.get("SwapTotal") != 0 or memory.get("MemTotal", 0) > 5_000_000_000
        or memory.get("MemTotal", 0) < 3_500_000_000
    ):
        raise PiPacketFailure("Pi target preflight identity mismatch")
    network = offline_environment()
    throttled = throttle_preflight()
    return {
        "git_sha": head,
        "os_id": release["ID"],
        "os_version": release["VERSION_ID"],
        "machine": platform.machine(),
        "mem_total_bytes": memory["MemTotal"],
        "swap_total_bytes": memory["SwapTotal"],
        "network": network,
        "throttled_prelaunch": throttled,
    }


def protocol_validator(protocol_schema: Path, prompt_schema: Path, response_schema: Path) -> Draft202012Validator:
    protocol = load(protocol_schema)
    store = {item["$id"]: item for item in (protocol, load(prompt_schema), load(response_schema))}
    return Draft202012Validator(protocol, resolver=RefResolver.from_schema(protocol, store=store))


def read_frame(stream: TextIO, timeout_s: float, validator: Draft202012Validator) -> dict[str, Any]:
    selector = selectors.DefaultSelector()
    selector.register(stream, selectors.EVENT_READ)
    try:
        if not selector.select(timeout_s):
            raise PiPacketFailure("protocol frame deadline exceeded")
        line = stream.readline()
    finally:
        selector.close()
    if not line:
        raise PiPacketFailure("candidate stdout closed")
    try:
        frame = json.loads(line)
    except json.JSONDecodeError as exc:
        raise PiPacketFailure("candidate emitted invalid JSONL") from exc
    if not isinstance(frame, dict) or not validator.is_valid(frame):
        raise PiPacketFailure("candidate emitted protocol-invalid frame")
    return frame


def send(process: subprocess.Popen[str], frame: dict[str, Any]) -> None:
    if process.stdin is None:
        raise PiPacketFailure("candidate stdin unavailable")
    process.stdin.write(json.dumps(frame, separators=(",", ":")) + "\n")
    process.stdin.flush()


def group_absent(group_id: int) -> bool:
    try:
        os.killpg(group_id, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def stop(process: subprocess.Popen[str] | None, term_s: float = 2.0, kill_s: float = 1.0) -> dict[str, Any]:
    if process is None:
        return {"exit_code": None, "waited": False, "term_sent": False, "kill_sent": False, "process_group_absent": True}
    term_sent = kill_sent = False
    group_id = process.pid
    if process.poll() is None:
        try:
            os.killpg(group_id, signal.SIGTERM)
            term_sent = True
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=term_s)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(group_id, signal.SIGKILL)
                kill_sent = True
            except ProcessLookupError:
                pass
            process.wait(timeout=kill_s)
    return {
        "exit_code": process.returncode,
        "waited": process.poll() is not None,
        "term_sent": term_sent,
        "kill_sent": kill_sent,
        "process_group_absent": group_absent(group_id),
    }


def launch(
    *,
    config: Path,
    config_sha256: str,
    config_schema: Path,
    protocol_schema: Path,
    install_root: Path,
    stderr: TextIO,
) -> subprocess.Popen[str]:
    argv = [
        "env", f"PYTHONPATH={install_root}", "python3",
        "poc_llm/harness/litert_lm_pi_child_adapter.py",
        "--config", str(config), "--config-sha256", config_sha256,
        "--config-schema", str(config_schema), "--config-schema-sha256", digest(config_schema),
        "--protocol-schema", str(protocol_schema), "--protocol-schema-sha256", digest(protocol_schema),
    ]
    return subprocess.Popen(
        argv, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr,
        text=True, start_new_session=True,
        env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
    )


def require_ready(process: subprocess.Popen[str], validator: Draft202012Validator, config: dict[str, Any], config_sha256: str) -> None:
    if process.stdout is None:
        raise PiPacketFailure("candidate stdout unavailable")
    ready = read_frame(process.stdout, config["ready_timeout_ms"] / 1000, validator)
    expected = {
        "candidate_id": config["candidate_id"], "pairing_revision": config["pairing_revision"],
        "platform": config["platform"], "runtime_sha256": config["runtime_sha256"],
        "model_sha256": config["model_sha256"], "config_sha256": config_sha256,
    }
    if ready.get("type") != "READY" or ready.get("identity") != expected:
        raise PiPacketFailure("READY identity mismatch")
