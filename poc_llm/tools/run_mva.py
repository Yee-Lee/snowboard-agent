"""Offline MVA entrypoint. Workstation: snapshot only; Pi requires operator approval."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time

from poc_llm.harness.mva_controller import Controller, ORDER, verify_next_case
from poc_llm.harness.mva_evidence import EvidenceWriter
from poc_llm.harness.mva_identity import load_config, prepare_receipt, verify_receipt
from poc_llm.harness.mva_process import RunError
from poc_llm.harness.mva_resources import PiSampler
from poc_llm.harness.mva_surface import build_manifest, canonical_bytes, surface_digest, verify_manifest

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "poc_llm/harness/mva-surface-lock-v1.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exclusive_json(path, value):
    with path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n")
        output.flush()
        os.fsync(output.fileno())


def require_pi():
    if platform.system() != "Linux" or platform.machine() != "aarch64":
        raise RunError("PREFLIGHT_BLOCKED")
    if Path("/proc/device-tree/model").read_text().strip("\0\n") != "Raspberry Pi 5 Model B Rev 1.1":
        raise RunError("PREFLIGHT_BLOCKED")
    info = platform.freedesktop_os_release()
    if info.get("ID") != "debian" or info.get("VERSION_ID") != "13" or platform.python_version() != "3.13.5":
        raise RunError("PREFLIGHT_BLOCKED")
    values = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    if not 3 * 1024**2 <= int(values["MemTotal"].split()[0]) <= 4 * 1024**2:
        raise RunError("PREFLIGHT_BLOCKED")
    # Require operator to disable externally routable interfaces before measurement.
    for path in Path("/sys/class/net").iterdir():
        if path.name != "lo" and (path / "operstate").read_text().strip() == "up":
            raise RunError("PREFLIGHT_BLOCKED")


def require_checkout(expected_sha):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()
    if git("rev-parse", "HEAD") != expected_sha or git("status", "--porcelain"):
        raise RunError("IDENTITY_DRIFT")


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("case", choices=["snapshot", "verify-snapshot", "prepare-install", *ORDER])
    result.add_argument("--implementation-sha")
    result.add_argument("--surface-sha256")
    result.add_argument("--config", type=Path)
    result.add_argument("--receipt", type=Path)
    result.add_argument("--receipt-sha256")
    result.add_argument("--evidence-root", type=Path)
    result.add_argument("--operator-authorized", action="store_true",
                        help="operator attests explicit User approval of this exact packet/SHA/Pi scope")
    return result


def main():
    args = parser().parse_args()
    if args.case == "snapshot":
        manifest = build_manifest(ROOT)
        exclusive_json(LOCK, manifest)
        print(json.dumps({"surface_sha256": surface_digest(manifest), "status": "WORKSTATION_SNAPSHOT"}))
        return 0
    if args.case == "verify-snapshot":
        manifest = json.loads(LOCK.read_text())
        verify_manifest(ROOT, manifest, args.surface_sha256 or surface_digest(manifest))
        print(json.dumps({"surface_sha256": surface_digest(manifest), "status": "PASS"}))
        return 0
    if not args.operator_authorized or not all((args.implementation_sha, args.surface_sha256, args.config, args.receipt)):
        raise RunError("PREFLIGHT_BLOCKED")
    require_pi()
    require_checkout(args.implementation_sha)
    verify_manifest(ROOT, json.loads(LOCK.read_text()), args.surface_sha256)
    config = load_config(args.config)
    if args.receipt.resolve().is_relative_to(ROOT):
        raise RunError("PREFLIGHT_BLOCKED")
    if args.case == "prepare-install":
        receipt = prepare_receipt(config)
        exclusive_json(args.receipt, receipt)
        os.chmod(args.receipt, 0o600)
        print(json.dumps({"receipt_sha256": hashlib.sha256(canonical_bytes(receipt)).hexdigest(), "status": "VERIFIED_NOT_MEASURED"}))
        return 0
    if not args.evidence_root or not args.receipt_sha256:
        raise RunError("PREFLIGHT_BLOCKED")
    receipt = json.loads(args.receipt.read_text())
    profile_path = ROOT / "poc_llm/contracts/mva/mva-profile-001.json"
    profile = json.loads(profile_path.read_text())
    identity = {"plan_sha256": sha(ROOT / "poc_llm/tests/mva/M4B-MVA-POC-PACKET-001.md"),
        "surface_sha256": args.surface_sha256, "profile_sha256": sha(profile_path),
        "semantic_schema_sha256": sha(ROOT / profile["surface"]["semantic_schema_path"]),
        "wire_schema_sha256": sha(ROOT / profile["surface"]["wire_schema_path"]),
        "config_sha256": hashlib.sha256(canonical_bytes(config)).hexdigest(),
        "model_sha256": profile["candidate"]["model_sha256"], "runtime_sha256": profile["candidate"]["runtime_wheel_sha256"],
        "audio_sha256": None}
    identity_key = hashlib.sha256(canonical_bytes([args.implementation_sha, identity, args.receipt_sha256])).hexdigest()
    run_id = "MVA-001-" + args.case
    # Reserve the immutable run before probes, so preflight failures also remain visible.
    writer = EvidenceWriter(args.evidence_root, run_id)
    ledger_path = args.evidence_root / "mva-001-ledger.jsonl"
    with ledger_path.open("a+", encoding="utf-8") as ledger:
        fcntl.flock(ledger, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger.seek(0)
        entries = [json.loads(line) for line in ledger if line.strip()]
        boot = hashlib.sha256(Path("/proc/sys/kernel/random/boot_id").read_bytes()).hexdigest()
        preflight_error = None
        sampler = None
        try:
            verify_next_case(entries, args.case, boot, identity_key)
            for entry in entries:
                summary_path = args.evidence_root / ("MVA-001-" + entry["case"]) / "summary.json"
                if sha(summary_path) != entry["summary_sha256"]:
                    raise RunError("IDENTITY_DRIFT")
            sampler = PiSampler()
        except Exception:
            preflight_error = "PREFLIGHT_BLOCKED"

        def verify_install():
            if preflight_error:
                raise RunError(preflight_error)
            try:
                verify_receipt(config, receipt, args.receipt_sha256)
            except Exception:
                raise RunError("IDENTITY_DRIFT") from None

        controller = Controller(case=args.case, run_id=run_id, implementation_sha=args.implementation_sha,
            identity=identity, config=config, sampler=sampler, writer=writer, verify_install=verify_install)
        result = controller.run()
        exclusive_json(writer.directory / "summary.json", result)
        entry = {"case": args.case, "identity": identity_key, "boot_digest": boot, "status": result["status"],
                 "summary_sha256": sha(writer.directory / "summary.json")}
        ledger.write(json.dumps(entry, sort_keys=True) + "\n")
        ledger.flush()
        os.fsync(ledger.fileno())
        print(json.dumps({"case": args.case, "status": result["status"], "review": "USER_REVIEW_REQUIRED"}))
        return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt):
        # Never echo raw argparse values, native error strings, paths or credentials.
        print('{"status":"Blocked","terminal":"PREFLIGHT_BLOCKED"}')
        raise SystemExit(2)
