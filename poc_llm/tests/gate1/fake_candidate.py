#!/usr/bin/env python3
"""Protocol-complete test double; never candidate evidence."""
import argparse, json, sys, time
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument("--catalog",type=Path,required=True); parser.add_argument("--candidate-id",required=True)
parser.add_argument("--runtime-sha",required=True); parser.add_argument("--model-sha",required=True); parser.add_argument("--config-sha",required=True)
args=parser.parse_args()
catalog=json.loads(args.catalog.read_text()); cases={c["fixture_id"]:c for c in catalog["cases"]}
def emit(x): print(json.dumps(x,separators=(",",":")),flush=True)
def expected(case):
    e=case["expected"]
    if e["mode"]=="fallback": return {"action_kind":"speak","action_payload":{"text":"Sorry, please try again."},"next_perceptions":["listen"]}
    kind=e["action_kind"]
    payload={"text":"Synthetic response."} if kind=="speak" else ({"name":e["tool_name"],"arguments":{}} if kind=="tool" else {})
    return {"action_kind":kind,"action_payload":payload,"next_perceptions":e["next_perceptions"]}
emit({"type":"READY","candidate_id":args.candidate_id,"runtime_sha256":args.runtime_sha,"model_sha256":args.model_sha,"config_sha256":args.config_sha})
for line in sys.stdin:
    req=json.loads(line); op=req.get("op")
    if op=="PING": emit({"type":"PONG"})
    elif op=="GENERATE": emit({"type":"RESULT","normalized":expected(cases[req["fixture_id"]]),"log_forbidden_hits":[]})
    elif op=="BENCH": emit({"type":"BENCH_RESULT","ttft_ms":1.0,"output_tokens":16,"rss_bytes":1048576})
    elif op=="TIMEOUT_PROBE": time.sleep(req["timeout_ms"]/1000); emit({"type":"ERROR","code":"TIMEOUT","state":"READY"})
    elif op=="START_CANCEL_PROBE": emit({"type":"GENERATING","operation_id":req["operation_id"]})
    elif op=="CANCEL": emit({"type":"CANCELLED","operation_id":req["operation_id"],"state":"READY"})
    elif op=="HISTORY_PROBE": emit({"type":"HISTORY_RESULT","output_marker":req["current_marker"],"previous_marker_present":False,"state":"READY"})
    elif op=="SHUTDOWN": emit({"type":"SHUTDOWN_ACK"}); break
    else: emit({"type":"ERROR","code":"UNKNOWN_OPERATION"})
