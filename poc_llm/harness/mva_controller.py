"""MVA fixed public matrix orchestration; hardware outcomes require later review."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import threading
import time

from poc_llm.harness.mva_contract import fixed_steady_window, ordinary_least_squares_slope, reasoner_projection
from poc_llm.harness.mva_evidence import fill_missing_reasons, TERMINALS
from poc_llm.harness.mva_process import Child, RunError
from poc_llm.harness.mva_product_layout import cache_object_path
from poc_llm.harness.mva_resources import stop_reason

ROOT = Path(__file__).resolve().parents[2]
PROFILE = json.loads((ROOT / "poc_llm/contracts/mva/mva-profile-001.json").read_text())
CATALOG = json.loads((ROOT / "poc_llm/fixtures/mva/public-catalog-001.json").read_text())
ORDER = ["api-proof"] + ["cold-" + item for item in PROFILE["matrix"]["cold_order"]] + [
    "replacement-" + item for item in PROFILE["matrix"]["replacement_order"]] + [
    "memory-1", "memory-2", "memory-3", "recovery-1", "recovery-2", "recovery-3"]


def utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def verify_next_case(entries: list[dict], case: str, boot_digest: str, identity: str):
    if len(entries) >= len(ORDER) or case != ORDER[len(entries)]:
        raise RunError("PREFLIGHT_BLOCKED")
    if any(entry["case"] != ORDER[index] or entry["identity"] != identity
           or entry["status"] != "PASS" for index, entry in enumerate(entries)):
        raise RunError("PREFLIGHT_BLOCKED")
    if case.startswith("cold-") and any(entry["boot_digest"] == boot_digest for entry in entries):
        raise RunError("PREFLIGHT_BLOCKED")
    replacements = [entry for entry in entries if entry["case"].startswith("replacement-")]
    if case.startswith("replacement-") and replacements and replacements[0]["boot_digest"] != boot_digest:
        raise RunError("PREFLIGHT_BLOCKED")


def steady_analysis(rows: list[dict]) -> dict:
    sessions = {}
    for row in rows:
        if row["terminal"] == "SESSION_CLOSED" and row["session_id"]:
            sessions[int(row["session_id"].rsplit("-", 1)[1])] = row
    result = {"window": list(range(11, 21)), "status": "Incomplete", "metrics": {}}
    if not all(index in sessions for index in range(11, 21)):
        return result
    for key in ("owner_pss_mib", "system_used_mib"):
        values = {index: sessions[index]["resources"][key] for index in range(11, 21)}
        if any(value is None for value in values.values()):
            return result
        pairs = fixed_steady_window(values)
        early = statistics.median(value for index, value in pairs if index <= 15)
        late = statistics.median(value for index, value in pairs if index >= 16)
        result["metrics"][key] = {"samples": pairs, "ols_mib_per_session": ordinary_least_squares_slope(pairs),
                                  "early_median_mib": early, "late_median_mib": late, "delta_mib": late - early}
    result["status"] = "Complete"
    return result


class Controller:
    def __init__(self, *, case: str, run_id: str, implementation_sha: str, identity: dict,
                 config: dict, sampler, writer, verify_install, child_factory=Child):
        if case not in ORDER:
            raise RunError("PREFLIGHT_BLOCKED")
        self.case, self.run_id = case, run_id
        self.sha, self.identity = implementation_sha, identity
        self.config, self.sampler, self.writer = config, sampler, writer
        self.verify_install, self.child_factory = verify_install, child_factory
        self.child = None
        self.rows = []
        self.generation = 0
        self.deadline = time.monotonic() + (7200 if case.startswith("memory-") else 1800)
        self.last_probe = 0.0
        self.last_owners = []
        self.clock_monotonic_anchor = time.monotonic()
        self.clock_utc_anchor = datetime.now(timezone.utc).timestamp()
        self.last_resources = {key: None for key in ("owner_pss_mib", "owner_rss_mib", "mem_total_mib",
            "mem_available_mib", "system_used_mib", "swap_used_kib", "temperature_c", "throttled", "oom_or_kernel_fault")}
        self.mode = "once" if case.split("-")[-1].startswith("O") else "none"
        self.ready_ms = None
        self.started = utc()
        self.session = None
        self.turn = None
        self.cleanups = {}
        self.censuses = []
        self.replacement_lock = threading.Lock()

    def replace_child(self, reason, directory):
        if reason != "capacity_test" or self.session is not None or self.child is None:
            raise RunError("PROTOCOL_ERROR")
        if not self.replacement_lock.acquire(blocking=False):
            raise RunError("PROTOCOL_ERROR")
        try:
            start = time.monotonic()
            if not self.close_child():
                raise RunError("CLEANUP_FAILED")
            self.start_child(directory)
            self.record("RECOVERY_READY", start, caller=(time.monotonic() - start) * 1000)
        finally:
            self.replacement_lock.release()

    def monitor(self, force=False):
        now = time.monotonic()
        if now >= self.deadline:
            raise RunError("TIMEOUT")
        if not force and now - self.last_probe < 1:
            return
        self.last_probe = now
        try:
            owners = self.child.owners() if self.child else []
            self.last_resources = self.sampler.sample(owners)
            self.last_owners = owners
            self.verify_install()
        except RunError:
            raise
        except Exception:
            raise RunError("SAMPLER_FAILED") from None
        reason = stop_reason(self.last_resources, self.sampler.initial_swap)
        if self.child:
            self.record("RESOURCE_SAMPLE", now)
        if reason:
            raise RunError(reason)

    def record(self, terminal, start, *, metrics=None, caller=None, status="INCONCLUSIVE"):
        metrics = metrics or {}
        now = time.monotonic()
        sample = {
            "run_id": self.run_id, "cycle_id": self.case if self.case.startswith("memory-") else None,
            "mode": "capacity_test" if self.case.startswith("recovery-") else self.mode,
            "case_id": self.case, "session_id": self.session, "turn_id": self.turn,
            "utc_start": datetime.fromtimestamp(self.clock_utc_anchor + start - self.clock_monotonic_anchor,
                timezone.utc).isoformat().replace("+00:00", "Z"), "monotonic_start_s": start, "monotonic_end_s": now,
            "implementation_sha": self.sha, "identity": deepcopy(self.identity),
            "platform": {key: PROFILE["platform"][key] for key in ("hardware", "os", "architecture", "backend", "threads")},
            "command": ["python3", "-m", "poc_llm.tools.run_mva", self.case],
            "process": {"start_utc": self.started, "end_utc": None, "exit_code": None,
                "status": status, "child_generation": self.generation or None,
                "owner_pid_set": list(self.last_owners)},
            "timing_ms": {"ready": self.ready_ms, "open": metrics.get("open_ms"), "ttft": metrics.get("ttft_ms"),
                "runtime_ttc": metrics.get("ttc_ms"), "caller_ttc": caller, "close": metrics.get("close_ms"),
                "speech_end_to_audible_onset": None},
            "token_metrics": {key: metrics.get(source) for key, source in {
                "new_user": "new_user_tokens", "rendered": "rendered_tokens", "incremental": "incremental_tokens",
                "kv": "kv_tokens", "output": "output_tokens"}.items()},
            "resources": deepcopy(self.last_resources), "terminal": terminal,
            "cleanup": {"status": "INCONCLUSIVE", "owners_absent": None, "alsa_owners_zero": None},
            "scope": "llm_subsystem", "raw_sanitized_log_path": self.run_id + "/samples.jsonl", "missing_reasons": {},
        }
        sample["platform"]["python"] = platform.python_version()
        if "initial_kv_tokens" in metrics:
            sample["token_metrics"]["kv"] = metrics["initial_kv_tokens"]
        fill_missing_reasons(sample)
        self.writer.append(sample, checkpoint=True)
        self.rows.append(sample)

    def start_child(self, directory):
        self.verify_install()
        self.monitor(force=True)
        self.generation += 1
        self.started = utc()
        begin = time.monotonic()
        env = {key: value for key, value in os.environ.items() if key in {"PATH", "LANG", "LC_ALL"}}
        env.update({"PYTHONPATH": str(ROOT) + os.pathsep + self.config["runtime_root"],
                    "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"})
        self.child = self.child_factory([sys.executable, "-m", "poc_llm.harness.mva_worker"], cwd=directory, env=env)
        inference = {key: PROFILE["inference"][key] for key in (
            "temperature", "top_p", "maximum_output_tokens", "user_new_token_admission", "engine_kv_tokens")}
        inference.update({"threads": 4, "model_path": self.config["model_path"],
                          "runtime_root": self.config["runtime_root"],
                          "cache_dir": str(cache_object_path(self.config))})
        self.child.send({"op": "START", "config": inference, "mode": self.mode})
        result = self.child.receive(120, self.monitor)
        if result.get("terminal") != "ENGINE_READY":
            raise RunError(result.get("terminal") if result.get("terminal") in TERMINALS else "PROTOCOL_ERROR")
        expected_cases = [CATALOG["timing"], CATALOG["prewarm"], *CATALOG["development_semantics"]]
        census = result.get("census", {})
        if set(census) != {case["case_id"] for case in expected_cases}:
            raise RunError("PROTOCOL_ERROR")
        for case in expected_cases:
            counts = census[case["case_id"]]
            if len(counts) != len(case["turns"]) or any(type(n) is not int or not 0 <= n <= 32 for n in counts):
                raise RunError("INPUT_TOO_LARGE")
        self.censuses.append({"child_generation": self.generation, "counts": census})
        if self.mode == "once":
            self.expect("PREWARM", "READY", timeout=min(30, 120 - (time.monotonic() - begin)))
        self.ready_ms = (time.monotonic() - begin) * 1000
        if self.ready_ms > 120000:
            raise RunError("TIMEOUT")
        self.monitor(force=True)
        self.record("READY", begin)

    def expect(self, op, terminal, *, timeout=30, **kwargs):
        reply = self.child.call(op, timeout=timeout, monitor=self.monitor, **kwargs)
        if reply.get("terminal") != terminal:
            code = reply.get("terminal")
            raise RunError(code if code in TERMINALS else "PROTOCOL_ERROR")
        return reply

    def session_pair(self, number):
        self.session = f"session-{number}"
        self.turn = None
        start = time.monotonic()
        result = self.expect("OPEN", "SESSION_OPENED", session=self.session)
        open_caller = (time.monotonic() - start) * 1000
        self.monitor(force=True)
        self.record("SESSION_OPENED", start, metrics=result["metrics"])
        for self.turn, text in enumerate(CATALOG["timing"]["turns"], 1):
            self.monitor(force=True)
            start = time.monotonic()
            result = self.expect("GENERATE", "RESULT", session=self.session, turn=self.turn, text=text)
            projection = reasoner_projection(result["semantic"])
            if projection["action_kind"] != "speak":
                raise RunError("EARLY_END")
            caller = (time.monotonic() - start) * 1000 + (open_caller if self.turn == 1 else 0)
            metrics = result["metrics"]
            required = {"new_user_tokens", "rendered_tokens", "incremental_tokens", "kv_tokens", "output_tokens", "ttft_ms", "ttc_ms"}
            if set(metrics) != required or any(metrics[key] is None for key in required):
                raise RunError("PROTOCOL_ERROR")
            self.monitor(force=True)
            self.record("RESULT", start, metrics=metrics, caller=caller)
        start = time.monotonic()
        last_result = self.rows[-1]
        result = self.expect("CLOSE", "SESSION_CLOSED", session=self.session)
        close_caller = (time.monotonic() - start) * 1000
        # Include close IPC in final caller TTC, while retaining separate close timing.
        last_result["timing_ms"]["caller_ttc"] += close_caller
        last_result["timing_ms"]["close"] = result["metrics"]["close_ms"]
        self.monitor(force=True)
        self.record("SESSION_CLOSED", start, metrics=result["metrics"])
        self.session = None
        self.turn = None

    def api_proof(self):
        self.session_pair(1)  # actual render/token counts, constraint and normal reuse
        self.session = "cancel-proof"
        self.expect("OPEN", "SESSION_OPENED", session=self.session)
        start = time.monotonic()
        cancelled = False

        def cancel_monitor():
            nonlocal cancelled
            self.monitor()
            if not cancelled and time.monotonic() - start >= 0.05:
                self.child.send({"op": "CANCEL"})
                cancelled = True

        reply = self.child.call("GENERATE", timeout=30, monitor=cancel_monitor,
            session=self.session, turn=1, text=CATALOG["timing"]["turns"][0])
        if not cancelled or reply.get("terminal") != "CANCELLED":
            raise RunError("INCOMPLETE")
        self.record("CANCELLED", start)
        self.session_pair(2)  # poisoned Conversation discarded, fresh session remains usable
        self.record("API_PROOF", start)

    def close_child(self):
        if self.child is None:
            return True
        cleanup = self.child.cleanup()
        cleanup["end_utc"] = utc()
        self.cleanups[self.generation] = cleanup
        self.child = None
        return cleanup["status"] == "PASS" and cleanup["cooperative"] and cleanup["exit_code"] == 0

    def run(self) -> dict:
        disposition = "PASS"
        begin = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="mva-child-") as directory:
            try:
                self.verify_install()
                if self.case.startswith("replacement-"):
                    for _ in range(5):
                        self.monitor(force=True)
                        time.sleep(1)
                self.start_child(directory)
                if self.case == "api-proof":
                    self.api_proof()
                elif self.case.startswith("recovery-"):
                    # Exactly one same-key request from READY_NO_SESSION, no physical pressure.
                    self.replace_child("capacity_test", directory)
                    self.session_pair(1)  # new generation can accept a session after the barrier
                else:
                    count = 20 if self.case.startswith("memory-") else 1
                    for number in range(1, count + 1):
                        self.session_pair(number)
                self.verify_install()
            except BaseException as error:
                code = error.code if isinstance(error, RunError) else "PROTOCOL_ERROR"
                disposition = "Blocked" if code in {"INPUT_TOO_LARGE", "PREFLIGHT_BLOCKED"} else (
                    "INCONCLUSIVE" if code in {"SAMPLER_FAILED", "INCOMPLETE", "PROTOCOL_ERROR", "IDENTITY_DRIFT"} else "FAIL")
                self.record(code, begin, status=disposition)
                if self.child:
                    try:
                        self.child.send({"op": "CANCEL"})
                        self.child.receive(2)
                    except Exception:
                        pass
            finally:
                if not self.close_child():
                    disposition = "FAIL"
                for sample in self.rows:
                    cleanup = self.cleanups.get(sample["process"]["child_generation"], {
                        "status": "INCONCLUSIVE", "owners_absent": None, "alsa_owners_zero": None, "exit_code": None})
                    sample["cleanup"] = {key: cleanup[key] for key in ("status", "owners_absent", "alsa_owners_zero")}
                    sample["process"].update({"end_utc": cleanup.get("end_utc"), "exit_code": cleanup["exit_code"], "status": disposition})
                    fill_missing_reasons(sample)
                    self.writer.append(sample)
        return {"case": self.case, "status": disposition, "sample_count": len(self.rows),
                "steady_analysis": steady_analysis(self.rows) if self.case.startswith("memory-") else None,
                "cleanup": self.cleanups, "token_census": self.censuses,
                "clock_monotonic_anchor": self.clock_monotonic_anchor, "clock_utc_anchor": self.clock_utc_anchor}
