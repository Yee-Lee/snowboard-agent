# GATE1-P6.1-P7.1-REDESIGN-001

- **Status**: `DESIGN FROZEN / USER AUTHORIZED EXECUTION 2026-08-27`
- **Supersedes for credit**: legacy P6 and P7 observations produced by the synchronous-cancel path
- **Candidates**: frozen Gemma 4 E2B and Qwen2.5 1.5B Q8
- **Runtime**: pinned LiteRT-LM Python/C API v0.16.0
- **Unchanged product thresholds**: cancel `500 ms`; rebuild READY `10,000 ms`

## 1. Finding and disposition

The legacy adapter ran synchronous `Conversation.send_message()` in a Python worker and invoked
`Conversation.cancel_process()` from the protocol thread. LiteRT-LM v0.16 documents
`CancelProcess()` for asynchronous inference and warns that the cancelled Conversation/session is
poisoned and unsupported for reuse. The old P6 result therefore does not establish correct native
cancel behavior. Because legacy P7 immediately followed that cancel attempt, it also does not
isolate process rebuild from a cancellation-conditioned runtime state.

Legacy observations remain immutable engineering history but receive no P6/P7 credit. P6.1 and
P7.1 are prospectively frozen, independent replacement tests. Neither changes candidate, model,
Engine capacity, prompt, sampler, timeout or product protocol threshold after observing a result.

## 2. Shared isolation and identity

Each `{candidate, test}` pair executes as a separate run after a Pi reboot. At runner entry:

- uptime is at most 900 seconds;
- no LLM adapter/runner process exists and no prior candidate workload ran in that boot;
- the exact source, execution-surface lock, runtime wheel/native library, model, strict config,
  protocol, fixture and artifact receipt identities verify;
- the Pi is 4 GB class, `swap=0`, offline, and `throttled=0x0`;
- full model SHA authentication occurs once before the READY clock.

No P6.1 run may feed P7.1, and no P7.1 run may call the native cancel API. Candidate runs cannot
share a boot. A valid result is never retried or replaced by a more favorable sample.

## 3. P6.1 official asynchronous cancellation

1. Start one child and require exact READY/PING within the unchanged P1 boundary.
2. Create a fresh Conversation and invoke Python v0.16 `send_message_async()`; consume its streaming
   iterator on the generation worker while retaining the native callback for its full lifetime.
3. Prove active generation from at least one valid stream event or a prospective native execution
   activity signal. Thread-count increase alone is diagnostic and cannot be the only proof.
4. Start the `500 ms` clock immediately before sending one correlated protocol `CANCEL`; invoke
   native `cancel_process()` exactly once. Cancelling the Python iterator alone is insufficient.
5. Require the async stream to reach its cancellation terminal and the child to emit correlated
   `CANCELLED` within `500 ms`. Record cancel-request, native-terminal and protocol-terminal times.
6. Close and permanently discard the poisoned Conversation. Never send another request through it.
7. Keep the same Engine and child process, create a new Conversation, complete one fixed health
   request, then cleanly SHUTDOWN with orphan zero.

P6.1 is `PASS` only when all seven steps pass. No terminal by `500 ms`, duplicate cancel, reuse of
the cancelled Conversation, missing health RESULT or cleanup failure is `FAIL`. Infrastructure or
evidence inability before valid async generation is `INCONCLUSIVE`; there is no legacy
`Conditional escalation` credit from the superseded synchronous test.

## 4. P7.1 independent process recovery

1. After an independent reboot, start a healthy child and prove active generation without invoking
   `cancel_process()`, `CancelGroup()` or any P6 path.
2. Apply the existing Level-2 process-group policy: SIGTERM, bounded wait, SIGKILL only if needed,
   waitpid and process-group absence. Record `abort_to_absence_ms` separately.
3. Only after absence is proven, start exactly one replacement child/Engine from the unchanged
   artifact receipt. Start `absence_to_ready_ms` at this barrier.
4. Exact READY must arrive within `10,000 ms`; this is the Core product recovery SLA and is not
   represented as a LiteRT-LM vendor guarantee.
5. Complete PING and one fixed recovery generation, clean SHUTDOWN and orphan-zero proof.

P7.1 is `PASS` only when cleanup, READY within ten seconds, recovery generation and final cleanup
all pass. At the ten-second boundary, a missing READY fixes the scored result as `FAIL`. The runner
may continue a separately labelled, non-scoring observation until 30 seconds:

- READY after 10 seconds but at or before 30 seconds: `SLOW_RECOVERY` diagnostic;
- no READY by 30 seconds: `WEDGED_OR_UNBOUNDED` diagnostic.

The extended observation cannot convert FAIL to PASS. Cleanup/waitpid/orphan failure is immediate
P7.1 FAIL. The Level-3 fatal outcome mapping remains exit `4` and must be verified without calling
the POC harness a product/systemd restart.

## 5. Expected-value hypothesis, not a verdict

Gemma previously rebuilt in `478.670 ms`. Qwen independently completed initial READY in
`3490.826 ms` and `3479.672 ms`. With P6 poisoning removed, Qwen P7.1 has measured headroom under
the unchanged ten-second SLA. This supports executing P7.1 but cannot predeclare PASS; target state,
cleanup and the new receipt must decide the result.

## 6. Publication boundary

Workstation unit tests must prove async terminal correlation, exactly-one cancel, poisoned
Conversation disposal, same-Engine new-Conversation health, P6.1/P7.1 run separation, two P7 clocks,
immutable ten-second adjudication and 30-second diagnostic-only behavior. On 2026-08-27, after the
workstation suite passed, the User authorized direct Pi execution and allowed reviewer examination
to follow without delaying development. No new benchmark or candidate proposal is published before
User result approval.

## 7. Authorized execution sequence after review

The operator runs exactly four invocations, rebooting and restoring the locked offline staging
before each one. `<execution-sha>` is the later clean committed source SHA; `<evidence-root>` is a
private Pi evidence directory and is not committed.

```text
python3 poc_llm/tools/run_gate1_p6_1_p7_1.py --packet-lock poc_llm/harness/gate1-p6-1-p7-1-lock-v1.json --candidate-set poc_llm/fixtures/gate1/pi-compat-candidates-v7.json --candidate-id CAND-LRT-G4E2B-MOBILE-R1 --test-id P6.1 --execution-sha <execution-sha> --run-id G1-P6.1-GEMMA-001 --evidence-root <evidence-root>
python3 poc_llm/tools/run_gate1_p6_1_p7_1.py --packet-lock poc_llm/harness/gate1-p6-1-p7-1-lock-v1.json --candidate-set poc_llm/fixtures/gate1/pi-compat-candidates-v7.json --candidate-id CAND-LRT-G4E2B-MOBILE-R1 --test-id P7.1 --execution-sha <execution-sha> --run-id G1-P7.1-GEMMA-001 --evidence-root <evidence-root>
python3 poc_llm/tools/run_gate1_p6_1_p7_1.py --packet-lock poc_llm/harness/gate1-p6-1-p7-1-lock-v1.json --candidate-set poc_llm/fixtures/gate1/pi-compat-candidates-v7.json --candidate-id CAND-LRT-Q25-15B-Q8-R1 --test-id P6.1 --execution-sha <execution-sha> --run-id G1-P6.1-QWEN-001 --evidence-root <evidence-root>
python3 poc_llm/tools/run_gate1_p6_1_p7_1.py --packet-lock poc_llm/harness/gate1-p6-1-p7-1-lock-v1.json --candidate-set poc_llm/fixtures/gate1/pi-compat-candidates-v7.json --candidate-id CAND-LRT-Q25-15B-Q8-R1 --test-id P7.1 --execution-sha <execution-sha> --run-id G1-P7.1-QWEN-001 --evidence-root <evidence-root>
```

All invocations must use the same `<evidence-root>`. Before candidate launch, the runner reads its
prior sanitized receipts and rejects a reused boot ID, duplicate `{candidate,test}`, or a mixed
execution SHA/surface. The four receipts must therefore contain four reboot-isolated observations;
P6.1 and P7.1 for a candidate cannot share a boot ID. Any accidental same-boot execution is invalid
evidence rather than a rerunnable FAIL. This execution surface is authorized by the User; later
review does not retroactively alter a valid frozen observation.
