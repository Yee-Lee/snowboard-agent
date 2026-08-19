#!/usr/bin/env python3
"""Protocol-only Pi compatibility double; never real candidate evidence."""

import argparse
import json
import sys


parser = argparse.ArgumentParser()
parser.add_argument("--candidate-id", required=True)
parser.add_argument("--runtime-version", required=True)
parser.add_argument("--runtime-sha", required=True)
parser.add_argument("--model-sha", required=True)
parser.add_argument("--config-sha", required=True)
args = parser.parse_args()


def emit(value: dict) -> None:
    print(json.dumps(value, separators=(",", ":")), flush=True)


emit({
    "type":"READY", "candidate_id":args.candidate_id,
    "runtime_version":args.runtime_version, "runtime_sha256":args.runtime_sha,
    "model_sha256":args.model_sha, "config_sha256":args.config_sha,
})
for line in sys.stdin:
    request = json.loads(line)
    if request.get("op") == "PING":
        emit({"type":"PONG"})
    elif request.get("op") == "MINIMAL_GENERATE":
        emit({"type":"RESULT", "status":"OK"})
    elif request.get("op") == "SHUTDOWN":
        emit({"type":"SHUTDOWN_ACK"})
        break
    else:
        emit({"type":"ERROR", "code":"UNSUPPORTED"})
