# GATE1-QWEN-ISOLATED-COMPLETION-ADDENDUM-001

- **Status**: `USER-DIRECTED PROSPECTIVE ISOLATION EXPERIMENT`
- **Base packet**: `G1-PI-COMPAT-007`
- **Candidate**: `CAND-LRT-Q25-15B-Q8-R1`
- **Purpose**: determine whether the prior Qwen P1 timeout was caused by same-run predecessor state

## Frozen hypothesis and boundary

The prior formal runner always placed Qwen after Gemma's complete twenty-session, cancel,
force-abort and rebuild workload. In the non-scoring P1.1 experiment, the same Qwen model and
`Engine.max_num_tokens=512` reached READY in `3572.296 ms` and completed generation. The formal
timeout therefore does not prove that 512 is intrinsically incompatible; it leaves a candidate-
isolation defect as a bounded hypothesis.

This prospective addendum keeps the exact LiteRT-LM wheel, Qwen model, config, adapter, public
catalog, abort fixture, schemas, thresholds and v7 workload. It neither lowers the 10,000 ms READY
deadline nor changes the 512-token Engine capacity. It never overwrites the retained failed run.

## Isolation invariant

The Pi must reboot immediately before execution. At wrapper entry, uptime must be at most 900
seconds, no LiteRT-LM adapter process may exist, Qwen must be the only candidate in the candidate
set and no other candidate workload may execute in the run. The wrapper stores only a SHA-256 of
the boot ID, bounded uptime and zero-predecessor proof; it does not store host identity.

The existing v7 runner then executes Qwen's complete P1/P6/P7/P10A/P11/P12 workload with
`swap=0`, offline interfaces/routes and `throttled=0x0`. A PASS supports the finding that the old
multi-candidate runner lacked candidate-independent target reset. A repeated READY timeout rejects
that hypothesis and retains Qwen FAIL. No repeated attempts or token retuning are permitted.

## Command

```sh
python3 poc_llm/tools/run_gate1_qwen_isolated_completion.py \
  --packet-lock poc_llm/harness/gate1-qwen-isolated-completion-lock-v1.json \
  --candidate-set poc_llm/fixtures/gate1/pi-qwen-isolated-candidate-v1.json \
  --execution-sha <full-sha> \
  --run-id G1-PI-COMPAT-007-QWEN-ISOLATED-<UTC-ID> \
  --evidence-root /tmp/llm-poc-g1-qwen-isolated/evidence
```

Raw stderr, receipts and model output remain outside Git. The sanitized wrapper result binds the
boot isolation proof, exact execution surface and hash of the nested v7 result. User review is
required before this experiment changes the published candidate disposition.
