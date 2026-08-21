#!/usr/bin/env python3
"""R5 runner pre-launch authenticator; execution remains separately authorized."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from poc_llm.harness.gate1_r5_projection import digest, projection
PACKET="G1-X86-PI-COMPAT-005"
def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--platform",choices=("ubuntu-x86_64","pi-debian13-aarch64"),required=True); p.add_argument("--candidate-manifest",type=Path,required=True); p.add_argument("--lock",type=Path,required=True); a=p.parse_args()
    try:
        value=projection(a.candidate_manifest,a.lock,a.platform); native=value["acquisition"]["platforms"][a.platform]
        report={"packet_id":PACKET,"runner_platform":a.platform,"candidate_id":value["manifest"]["candidate_id"],"pairing_revision":value["manifest"]["pairing_revision"],"result":"INCONCLUSIVE","identity":{"lock_sha256":digest(a.lock),"manifest_sha256":value["manifest_sha256"],"acquisition_manifest_sha256":value["acquisition_sha256"],"config_sha256":value["config_sha256"],"runtime_sha256":native["runtime_artifact"]["sha256"],"model_sha256":value["manifest"]["model"]["sha256"],"dependency_bundle_sha256":native["dependency_bundle"]["sha256"],"adapter_binding_bundle_sha256":native["adapter_binding_bundle"]["sha256"],"command_sha256":value["manifest"]["commands"][a.platform]["sha256"]},"violations":["R5 repository-only authorization: real execution is blocked"]}
        print(json.dumps(report,sort_keys=True,separators=(",",":"))); return 2
    except Exception as error:
        print(json.dumps({"packet_id":PACKET,"runner_platform":a.platform,"candidate_id":"UNBOUND","pairing_revision":"UNBOUND","result":"INCONCLUSIVE","identity":{"lock_sha256":"0"*64,"manifest_sha256":"0"*64,"acquisition_manifest_sha256":"0"*64,"config_sha256":"0"*64,"runtime_sha256":"0"*64,"model_sha256":"0"*64,"dependency_bundle_sha256":"0"*64,"adapter_binding_bundle_sha256":"0"*64,"command_sha256":"0"*64},"violations":[str(error)]},sort_keys=True,separators=(",",":"))); return 2
if __name__ == "__main__": raise SystemExit(main())
