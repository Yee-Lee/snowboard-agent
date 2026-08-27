# GATE1-QWEN-P6-P7-ISOLATED-ADDENDUM-001

- **Status**: `USER-DIRECTED PROSPECTIVE RUNNER-CORRECTION EXPERIMENT`
- **Base packet**: `G1-PI-COMPAT-007`
- **Candidate**: `CAND-LRT-Q25-15B-Q8-R1`
- **Credit requested**: P6 and P7 only

## Finding addressed

A retained internal reboot-isolated run exposed a redundant second Engine startup before P6. This
packet evaluates the corrected sequence without publishing or adjudicating that run. P6/P7 do not
require a new Engine before cancellation. P7 requires exactly one force-abort followed by one
rebuild/READY/recovery barrier.

## Frozen focused method

After a new Pi reboot, the focused runner authenticates the unchanged Qwen model and starts the
unchanged 512-token child with the same 10,000 ms READY threshold. The same healthy child performs
the fixed P6 generation/cancel probe with the unchanged 500 ms cancel threshold and is then the
target of P7 force-abort. Only the contract-required rebuild is launched afterward; it retains the
unchanged 10,000 ms rebuild/READY bound,
fixed recovery input, shutdown and orphan-zero requirements.

The packet does not rerun P1/P10A, does not change a token, timeout, fixture, model, runtime,
sampler, schema or candidate identity, and does not insert a cooldown, cache drop or warm-up. A
rebuild timeout is P7 FAIL. No repeated attempt is permitted.

## Command

```sh
python3 poc_llm/tools/run_gate1_qwen_p6_p7_isolated.py \
  --packet-lock poc_llm/harness/gate1-qwen-p6-p7-isolated-lock-v1.json \
  --candidate-set poc_llm/fixtures/gate1/pi-qwen-isolated-candidate-v1.json \
  --execution-sha <full-sha> \
  --run-id G1-QWEN-P6P7-ISOLATED-<UTC-ID> \
  --evidence-root /tmp/llm-poc-g1-qwen-p6p7/evidence
```

The result remains internal until User review. It will be combined with the accepted Gemma run and
the isolated Qwen P1/P10A/P11/P12 receipt only at Gate 1 closure.
