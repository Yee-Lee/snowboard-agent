"""POC measurement RPC child. Native stdout/stderr never reach the evidence log.

This private RPC is POC orchestration, not a Core snowboard.llm/2 conformance
claim. One persistent Engine, one Conversation per session, bounded by parent.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    output = os.fdopen(os.dup(sys.stdout.fileno()), "w", buffering=1)
    with open(os.devnull, "w") as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
    from poc_llm.harness.mva_contract import SESSION_FACTS
    from poc_llm.harness.mva_litert_backend import MvaBackendError, MvaLiteRtBackend
    lock = threading.Lock()

    def send(value):
        with lock:
            output.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
            output.flush()

    def receive():
        line = sys.stdin.buffer.readline(65537)
        if len(line) > 65536 or not line.endswith(b"\n"):
            raise ValueError("invalid RPC")
        return json.loads(line)

    backend = None
    job = None
    try:
        start = receive()
        if set(start) != {"op", "config", "mode"} or start["op"] != "START" or start["mode"] not in {"none", "once"}:
            raise ValueError("invalid start")
        import litert_lm
        runtime_root = Path(start["config"].pop("runtime_root")).resolve()
        if not Path(litert_lm.__file__).resolve().is_relative_to(runtime_root):
            raise ValueError("runtime import drift")
        base = ROOT / "poc_llm/contracts/mva"
        backend = MvaLiteRtBackend.from_paths(start["config"], system_prompt_path=base / "system-prompt-v1.txt",
            user_template_path=base / "user-turn-template-v1.txt", semantic_schema_path=base / "semantic-output-v1.schema.json")
        catalog = json.loads((ROOT / "poc_llm/fixtures/mva/public-catalog-001.json").read_text())
        cases = [catalog["timing"], catalog["prewarm"], *catalog["development_semantics"]]
        census = backend.census({case["case_id"]: case["turns"] for case in cases})
        # Parent gives disposable inference its own 30-second watchdog.
        send({"terminal": "ENGINE_READY", "census": census})

        def execute(request):
            try:
                op = request["op"]
                if op == "GENERATE":
                    result = backend.generate(request["session"], request["turn"], request["text"])
                    send({"ticket": request["ticket"], "terminal": "RESULT", "semantic": result.semantic, "metrics": result.metrics})
                elif op == "PREWARM":
                    metrics = backend.prewarm_once(catalog["prewarm"]["turns"][0])
                    send({"ticket": request["ticket"], "terminal": "READY", "metrics": metrics})
            except BaseException as error:
                code = error.code if isinstance(error, MvaBackendError) else "GENERATION_FAILED"
                send({"ticket": request["ticket"], "terminal": code})

        while True:
            request = receive()
            op = request["op"]
            if op == "CANCEL":
                backend.cancel()
                continue
            if job is not None:
                job.join(timeout=0.2)
                if job.is_alive():
                    raise ValueError("single-flight violation")
                job = None
            if op in {"GENERATE", "PREWARM"}:
                job = threading.Thread(target=execute, args=(request,), daemon=True)
                job.start()
                continue
            if op == "OPEN":
                metrics = backend.open_session(request["session"], SESSION_FACTS)
                send({"ticket": request["ticket"], "terminal": "SESSION_OPENED", "metrics": metrics})
            elif op == "CLOSE":
                metrics = backend.close_session(request["session"])
                send({"ticket": request["ticket"], "terminal": "SESSION_CLOSED", "metrics": metrics})
            elif op == "SHUTDOWN":
                backend.close()
                backend = None
                send({"ticket": request["ticket"], "terminal": "SHUTDOWN_ACK"})
                return 0
            else:
                raise ValueError("unknown RPC")
    except BaseException as error:
        code = error.code if isinstance(error, MvaBackendError) else "PROTOCOL_ERROR"
        send({"terminal": code})
        return 1
    finally:
        if backend is not None:
            # The parent owns the hard cleanup deadline if native close blocks.
            try:
                backend.close()
            except BaseException:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
