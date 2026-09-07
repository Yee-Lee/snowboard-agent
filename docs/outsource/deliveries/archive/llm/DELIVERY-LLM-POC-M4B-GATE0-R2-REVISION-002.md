# Core Team → LLM POC Team: M4b Gate 0 R2 Revision 002

- **Delivery ID**: `DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-002`
- **Related handoff**: `PM-OUT-260817-015-llm-poc-contract-plan-review`
- **Related finding**: `OUT-M4B-2026-007`
- **Previous revision request**: `DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-001`
- **Reviewed response**: `RESP-DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-001`
- **Reviewed POC branch / commit**: `llm` / `096cd728a277db584b23a5b0c91e3e7692b672fb`
- **Preserved baselines**: `0cff62f942f2eec82fcc0b0f953a7cc4a2819e3a`,
  `1d3444009a1edbf63e1b24a5e6977cbdb7203c80`
- **Status**: `REVISION REQUIRED — GATE 0 R2 NOT ACCEPTED`
- **Owner**: Core Team Designer
- **Architecture change**: `No`

## 1. Disposition

Core verified that local `HEAD` and `origin/llm` both resolve to the submitted full SHA and that
the worktree is clean. The 25-file list in the response matches the reviewed commit. The committed
packet now rejects the original expected-JSON-printer reproduction, validates its schemas, drives
the declared protocol gates and caps the synthetic selector result at two.

`OUT-M4B-2026-007` nevertheless remains open. Four directly affected fail-closed paths still allow
false-positive or non-reconcilable Gate 1 evidence, and one failure path leaves a live child. Gate 0
R2 and handoff 015 therefore cannot be closed or archived yet.

Core does not require an Ubuntu candidate benchmark, Pi run or candidate evidence for this
revision. The reviewed work correctly keeps Gate 1 `NOT_STARTED`, Gate 2A/2B plan-only and all
future finalist/winner decisions Core-owned.

## 2. Verification accepted in this review

```text
PYTHONPYCACHEPREFIX=/tmp/llm_poc_review_pycache \
  python3 -m unittest -v poc_llm.tests.gate1.test_gate1_packet
Ran 2 tests in 36.051s — OK

python3 poc_llm/harness/gate1_validator.py \
  --catalog poc_llm/fixtures/gate1/catalog.json --self-test
result=PASS; violations=[]

python3 poc_llm/tools/run_m4b_gate.py --gate 2A ... --plan-only
result=PLAN_VALID; execution_performed=false

python3 poc_llm/tools/run_m4b_gate.py --gate 2B ... --plan-only
result=PLAN_VALID; execution_performed=false
```

These results validate the reported self-test boundary. They do not exercise the four negative
paths below, so the passing two-test suite is not sufficient to accept the packet.

## 3. Remaining Blocking corrections

### `OUT-M4B-2026-007-A` — Log hygiene trusts candidate-supplied claims

- **Contract basis**: M4B contract P3 makes log hygiene mandatory and forbids prompt, raw model
  output, payload, credential or hidden context in logs. A single leak cannot be averaged away.
- **Reproduction**: a protocol-complete candidate wrote
  `raw model output: SECRET_PAYLOAD` to the runner-owned raw stderr file while every result frame
  reported `log_forbidden_hits=[]`.
- **Actual result**: runner exit `0`, overall `PASS`, P3 `PASS`; raw stderr retained the forbidden
  content verbatim.
- **Cause / impact**: `run_gate1_prescreen.py` copies `log_forbidden_hits` from the candidate frame
  and the validator trusts it. The runner never performs its own hygiene check on captured output.
  A leaking candidate can self-attest that it did not leak and remain finalist-eligible.
- **Minimum acceptance**: make log-hygiene determination runner-owned over the actual captured
  streams/sanitized evidence. Add a negative candidate that emits a frozen forbidden sentinel while
  claiming no hits; it must return non-zero, P3/overall non-PASS and be selector-ineligible.

### `OUT-M4B-2026-007-B` — P4 cold evidence is incomplete but can PASS

- **Contract basis**: M4B contract P4 requires, after warm-up, three cold and twenty hot raw samples
  for TTFT, total latency and generation tok/s, plus P50/P95 for those measurements. An incomplete
  measurement is not `PASS` or a threshold disposition.
- **Evidence**: the cold loop records only runner-observed `cold_total_ms` and checks only the frame
  type. The schema/result have no cold TTFT, output-token or tok/s samples and no cold TTFT/tok/s
  P50/P95. Threshold disposition is derived only from the hot values.
- **Actual result**: the protocol self-test produced overall `PASS` with three cold total-latency
  samples while every required cold TTFT/tok/s field was absent.
- **Impact**: a candidate can supply invalid or absent cold performance values and still create a
  complete-looking P4 PASS/finalist input; Core cannot make the required P4 comparison.
- **Minimum acceptance**: validate and preserve cold TTFT, output token and tok/s raw samples and
  their P50/P95 alongside total latency. Update the locked result schema and selector completeness
  checks. Missing, invalid or inconsistent cold metrics must be non-PASS and covered by regression.

### `OUT-M4B-2026-007-C` — Cleanup skips the process group after leader exit

- **Contract basis**: the Gate 1 packet and `OUT-M4B-2026-007` require bounded TERM→KILL→wait and
  absence of the complete process group on every success/failure path.
- **Reproduction**: a protocol-complete candidate spawned a same-process-group `sleep` child, then
  returned `SHUTDOWN_ACK` and exited its leader normally.
- **Actual result**: runner returned `FAIL` with
  `cleanup={exit_code:0, waited:true, process_group_absent:false}`, but the child remained alive
  after runner exit.
- **Cause / impact**: `stop()` sends no group signal when `process.poll()` is already non-`None`.
  The caller then marks cleanup as waited, so `finally` does not retry. A detected cleanup failure
  can itself leave the exact orphan the packet promises to remove.
- **Minimum acceptance**: always reconcile the process group independently of leader state. If any
  member remains, perform bounded group TERM→check→KILL→check and retain truthful exit proof. Add a
  leader-exits-first regression that verifies the child is gone before the runner returns.

### `OUT-M4B-2026-007-D` — Selector accepts unauthenticated placeholder PASS evidence

- **Contract basis**: Gate 1 finalist selection requires immutable, same-pairing, both-platform
  runner evidence bound to the locked packet/candidate identities. Schema validity alone cannot
  turn unavailable identity into a finalist.
- **Reproduction**: Core supplied two handcrafted schema-valid PASS JSON files, one per platform,
  with all thirteen identity SHA fields equal to `UNAVAILABLE`, sixty repeated placeholder cases,
  PASS gates, synthetic metrics and claimed cleanup.
- **Actual result**: selector exit `0`, aggregate `PASS`, and `CAND-HANDCRAFTED` appeared in
  `proposed_finalists`.
- **Cause / impact**: the result schema permits `UNAVAILABLE` for PASS evidence; selector checks
  equality between the two files but not availability or agreement with the actual locked artifact
  identities. It checks only case count, not the frozen catalog/repetition set.
- **Minimum acceptance**: eligible PASS/threshold evidence must contain real 64-hex identities and
  match the loaded lock's fixed artifact checksums. Selector must reject unavailable identity and
  verify the exact frozen `(fixture_id, repetition)` set plus internally consistent P4 aggregates.
  Add the handcrafted two-platform reproduction as a negative test; it must produce no finalist.

## 4. Core decisions remain unchanged

- A complete valid P4 measurement below the starting target remains
  `Core threshold decision required`; incomplete P4 evidence cannot use this disposition.
- No standing 4GB exception is granted. An 8GB result cannot repair or substitute for a mandatory
  4GB failure without a separate written Core/User contract decision.
- The Accepted Audio final handoff ID, full SHA and kit are not yet available. Core commit
  `790c0f86e12422542ef94cacd3c4dd850e346bca` is not a final Audio package; Gate 2B remains Blocked.
- Future Gate 1 proposed-finalist, Gate 2A provisional-finalist and Gate 2B final-winner ACKs remain
  Core decisions after their respective real evidence. None is pre-authorized here.

## 5. Required next return

LLM POC Team should revise only the four direct `OUT-M4B-2026-007` closure gaps above and their
locked schemas/tests. Preserve all three existing commit identities and return one new commit on
`origin/llm` with:

- response/packet paths, branch and new full 40-character SHA;
- exact changed-file list and mapping to `007-A` through `007-D`;
- official self-test plus the four new negative regression commands/results;
- confirmation that no Ubuntu candidate benchmark, Pi run or candidate evidence was performed.

Until Core re-reviews that exact SHA and closes these paths, 015 remains open, Gate 0 R2 remains
unaccepted, Gate 1 remains not started, and no finalist/freeze/target execution is authorized.
