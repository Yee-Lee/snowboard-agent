"""User-authorized append-only long-Conversation diagnostic for the selected Pi MVA runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

from poc_llm.harness.mva_contract import reasoner_projection
from poc_llm.harness.mva_identity import load_config, verify_receipt
from poc_llm.harness.mva_process import Child, RunError
from poc_llm.harness.mva_product_layout import (
    cache_object_path,
    runtime_import_root,
    runtime_model_path,
)
from poc_llm.harness.mva_resources import PiSampler, stop_reason
from poc_llm.harness.mva_surface import canonical_bytes


PROMPTS = [
    "請簡單介紹你自己。",
    "你能幫我做什麼？",
    "你現在可以看到東西嗎？",
    "那你可以聽我說話嗎？",
    "回答時會使用什麼語言？",
    "請再簡短一點。",
    "天空為什麼是藍色的？",
    "可以說得更簡單嗎？",
    "白天為什麼會有陽光？",
    "晚上為什麼會變暗？",
    "雲是怎麼形成的？",
    "雨又是怎麼形成的？",
    "請用一句話回答。",
    "你能使用工具嗎？",
    "你能看見周圍環境嗎？",
    "請記得保持簡短。",
    "現在還在同一個對話嗎？",
    "請說明你目前的能力。",
    "再用更簡單的方式說。",
    "請用最後一句話總結。",
]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--checkout", required=True, type=Path)
    result.add_argument("--implementation-sha", required=True)
    result.add_argument("--config", required=True, type=Path)
    result.add_argument("--receipt", required=True, type=Path)
    result.add_argument("--receipt-sha256", required=True)
    result.add_argument("--output", required=True, type=Path)
    return result


def require_pi(checkout: Path, expected_sha: str) -> None:
    if platform.system() != "Linux" or platform.machine() != "aarch64":
        raise RunError("PREFLIGHT_BLOCKED")
    if Path("/proc/device-tree/model").read_text().strip("\0\n") != "Raspberry Pi 5 Model B Rev 1.1":
        raise RunError("PREFLIGHT_BLOCKED")
    actual = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True, timeout=10,
    ).strip()
    dirty = subprocess.check_output(
        ["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=all"],
        text=True,
        timeout=10,
    ).strip()
    if actual != expected_sha or dirty:
        raise RunError("IDENTITY_DRIFT")


def exclusive_json(path: Path, value: dict) -> str:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    data = json.dumps(
        value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False,
    ).encode() + b"\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    return hashlib.sha256(data).hexdigest()


def inference_config(config: dict, profile: dict, directory: Path) -> dict:
    result = {
        key: profile["inference"][key]
        for key in (
            "temperature",
            "top_p",
            "maximum_output_tokens",
            "user_new_token_admission",
            "engine_kv_tokens",
        )
    }
    result.update(
        {
            "threads": profile["platform"]["threads"],
            "model_path": str(runtime_model_path(config, directory)),
            "runtime_root": config["runtime_root"],
            "cache_dir": str(cache_object_path(config)),
        }
    )
    return result


def run_cycle(cycle: int, checkout: Path, config: dict, profile: dict, sampler: PiSampler) -> dict:
    child = None
    latest_resource = None
    resource_samples = []
    terminal = "PROTOCOL_ERROR"
    turns = []
    recovery = {"status": "NOT_EXECUTED"}
    session_active = False
    limit_attempt_turn = None
    post_long_session_resource = None
    post_recovery_resource = None
    with tempfile.TemporaryDirectory(prefix=f"mva-long-{cycle}-") as raw_directory:
        directory = Path(raw_directory)
        try:
            environment = {
                key: value for key, value in os.environ.items() if key in {"PATH", "LANG", "LC_ALL"}
            }
            environment.update(
                {
                    "PYTHONPATH": str(checkout) + os.pathsep + str(runtime_import_root(config)),
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONNOUSERSITE": "1",
                }
            )
            child = Child(
                [sys.executable, "-m", "poc_llm.harness.mva_worker"],
                cwd=str(directory),
                env=environment,
            )
            last_probe = 0.0

            def monitor(force: bool = False) -> None:
                nonlocal last_probe, latest_resource
                now = time.monotonic()
                if not force and now - last_probe < 1:
                    return
                last_probe = now
                latest_resource = sampler.sample(child.owners())
                resource_samples.append(latest_resource)
                reason = stop_reason(latest_resource, sampler.initial_swap)
                if reason:
                    raise RunError(reason)

            child.send({"op": "START", "config": inference_config(config, profile, directory), "mode": "none"})
            started = child.receive(120, monitor)
            if started.get("terminal") != "ENGINE_READY":
                raise RunError("PROTOCOL_ERROR")
            monitor(force=True)
            opened = child.call("OPEN", timeout=30, monitor=monitor, session=f"long-session-{cycle}")
            if opened.get("terminal") != "SESSION_OPENED" or opened.get("metrics", {}).get("initial_kv_tokens") != 0:
                raise RunError("PROTOCOL_ERROR")
            session_active = True
            for turn_id, prompt in enumerate(PROMPTS, 1):
                reply = child.call(
                    "GENERATE",
                    timeout=30,
                    monitor=monitor,
                    session=f"long-session-{cycle}",
                    turn=turn_id,
                    text=prompt,
                )
                monitor(force=True)
                if reply.get("terminal") == "CONTEXT_LIMIT":
                    terminal = "CONTEXT_LIMIT_BEFORE_20"
                    limit_attempt_turn = turn_id
                    session_active = False
                    time.sleep(1)
                    monitor(force=True)
                    post_long_session_resource = latest_resource
                    break
                if reply.get("terminal") != "RESULT":
                    terminal = reply.get("terminal", "PROTOCOL_ERROR")
                    raise RunError(terminal)
                projection = reasoner_projection(reply.get("semantic"))
                if projection["action_kind"] != "speak":
                    raise RunError("EARLY_END")
                metrics = reply.get("metrics", {})
                required = {
                    "new_user_tokens",
                    "rendered_tokens",
                    "incremental_tokens",
                    "kv_tokens",
                    "output_tokens",
                    "ttft_ms",
                    "ttc_ms",
                }
                if set(metrics) != required or any(metrics[key] is None for key in required):
                    raise RunError("PROTOCOL_ERROR")
                turns.append(
                    {
                        "turn": turn_id,
                        "tokens": {
                            "new_user": metrics["new_user_tokens"],
                            "rendered": metrics["rendered_tokens"],
                            "incremental": metrics["incremental_tokens"],
                            "output": metrics["output_tokens"],
                            "kv": metrics["kv_tokens"],
                        },
                        "timing_ms": {
                            "ttft": metrics["ttft_ms"],
                            "runtime_ttc": metrics["ttc_ms"],
                        },
                        "resources": latest_resource,
                    }
                )
            else:
                terminal = "COMPLETED_20"

            if session_active:
                closed = child.call(
                    "CLOSE", timeout=30, monitor=monitor, session=f"long-session-{cycle}",
                )
                if closed.get("terminal") != "SESSION_CLOSED":
                    raise RunError("CLEANUP_FAILED")
                session_active = False
                time.sleep(1)
                monitor(force=True)
                post_long_session_resource = latest_resource

            recovery_session = f"long-recovery-{cycle}"
            opened = child.call("OPEN", timeout=30, monitor=monitor, session=recovery_session)
            if opened.get("terminal") != "SESSION_OPENED" or opened.get("metrics", {}).get("initial_kv_tokens") != 0:
                raise RunError("PROTOCOL_ERROR")
            recovered = child.call(
                "GENERATE",
                timeout=30,
                monitor=monitor,
                session=recovery_session,
                turn=1,
                text=PROMPTS[0],
            )
            if recovered.get("terminal") != "RESULT":
                raise RunError("PROTOCOL_ERROR")
            recovered_metrics = recovered.get("metrics", {})
            closed = child.call("CLOSE", timeout=30, monitor=monitor, session=recovery_session)
            if closed.get("terminal") != "SESSION_CLOSED":
                raise RunError("CLEANUP_FAILED")
            time.sleep(1)
            monitor(force=True)
            post_recovery_resource = latest_resource
            recovery = {
                "status": "PASS",
                "initial_kv": opened["metrics"]["initial_kv_tokens"],
                "result_kv": recovered_metrics.get("kv_tokens"),
            }
        except RunError:
            if session_active and child is not None:
                try:
                    child.call("CLOSE", timeout=30, session=f"long-session-{cycle}")
                except Exception:
                    pass
            raise
        finally:
            cleanup = child.cleanup() if child is not None else {
                "status": "FAIL",
                "owners_absent": False,
                "cooperative": False,
                "exit_code": None,
            }
    return {
        "cycle": cycle,
        "terminal": terminal,
        "completed_turns": len(turns),
        "limit_attempt_turn": limit_attempt_turn,
        "turns": turns,
        "post_long_session_resource": post_long_session_resource,
        "recovery": recovery,
        "post_recovery_resource": post_recovery_resource,
        "resource_envelope": {
            "max_owner_pss_mib": max(
                item["owner_pss_mib"] for item in resource_samples
                if item["owner_pss_mib"] is not None
            ),
            "min_mem_available_mib": min(item["mem_available_mib"] for item in resource_samples),
            "max_system_used_mib": max(item["system_used_mib"] for item in resource_samples),
            "max_temperature_c": max(item["temperature_c"] for item in resource_samples),
            "max_swap_used_kib": max(item["swap_used_kib"] for item in resource_samples),
            "throttled_values": sorted({item["throttled"] for item in resource_samples}),
            "oom_or_kernel_fault": any(item["oom_or_kernel_fault"] for item in resource_samples),
        },
        "cleanup": cleanup,
    }


def main() -> int:
    args = parser().parse_args()
    checkout = args.checkout.resolve()
    require_pi(checkout, args.implementation_sha)
    config = load_config(args.config, checkout_root=checkout)
    receipt = json.loads(args.receipt.read_text())
    verify_receipt(config, receipt, args.receipt_sha256)
    profile = json.loads((checkout / "poc_llm/contracts/mva/mva-profile-001.json").read_text())
    sampler = PiSampler()
    cycles = [run_cycle(index, checkout, config, profile, sampler) for index in range(1, 4)]
    verify_receipt(config, receipt, args.receipt_sha256)
    runner_pass = all(
        cycle["terminal"] in {"COMPLETED_20", "CONTEXT_LIMIT_BEFORE_20"}
        and cycle["recovery"]["status"] == "PASS"
        and cycle["cleanup"]["status"] == "PASS"
        and cycle["cleanup"]["owners_absent"]
        for cycle in cycles
    )
    result = {
        "format": "mva-long-session-supplemental-v1",
        "execution_sha": args.implementation_sha,
        "scope": "llm_subsystem",
        "cycles_requested": 3,
        "turns_requested_per_cycle": 20,
        "runner_status": "PASS" if runner_pass else "FAIL",
        "twenty_turn_outcome": (
            "PASS" if all(cycle["terminal"] == "COMPLETED_20" for cycle in cycles)
            else "CONTEXT_LIMIT_OBSERVED"
        ),
        "cycles": cycles,
        "raw_prompt_or_answer_retained": False,
    }
    digest = exclusive_json(args.output, result)
    print(
        json.dumps(
            {
                "runner_status": result["runner_status"],
                "twenty_turn_outcome": result["twenty_turn_outcome"],
                "completed_turns": [cycle["completed_turns"] for cycle in cycles],
                "limit_attempt_turns": [cycle["limit_attempt_turn"] for cycle in cycles],
                "evidence_sha256": digest,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0 if runner_pass else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt):
        print('{"runner_status":"FAIL","terminal":"SUPPLEMENTAL_RUN_FAILED"}')
        raise SystemExit(2)
