#!/usr/bin/env python3
"""R5 packet validator and deterministic projection self-test entry point."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from gate1_r5_projection import digest, load, locked, projection
def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--lock",type=Path,required=True); p.add_argument("--catalog",type=Path); p.add_argument("--manifest",type=Path); p.add_argument("--platform",choices=("ubuntu-x86_64","pi-debian13-aarch64")); p.add_argument("--self-test",action="store_true"); a=p.parse_args()
    try:
        paths=locked(load(a.lock))
        if a.catalog:
            catalog=load(a.catalog); source=catalog["source_catalog"]
            if digest(Path(source["path"])) != source["sha256"]: raise ValueError("R5 catalog source identity mismatch")
        value={"result":"PASS","packet_id":"G1-X86-PI-COMPAT-005"}
        if a.manifest:
            if not a.platform: p.error("--manifest requires --platform")
            item=projection(a.manifest,a.lock,a.platform); value.update({"candidate_id":item["manifest"]["candidate_id"],"platform":a.platform,"config_sha256":item["config_sha256"]})
        elif not a.self_test: p.error("choose --self-test or --manifest")
        print(json.dumps(value,sort_keys=True,separators=(",",":"))); return 0
    except Exception as error:
        print(json.dumps({"result":"FAIL","packet_id":"G1-X86-PI-COMPAT-005","violations":[str(error)]},sort_keys=True,separators=(",",":"))); return 1
if __name__ == "__main__": raise SystemExit(main())
