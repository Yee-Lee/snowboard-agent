# GATE2A-PI-PACKET-002 — Cumulative Remaining LLM-only Validation

- **Packet ID**: `G2A-PI-LLM-002`
- **Revision**: `2026-08-26-r2`
- **Status**: `REVIEW FINDINGS REVISED / RE-REVIEW REQUIRED / NOT AUTHORIZED`
- **Entry receipt**: Core-accepted `G1-PI-COMPAT-007` cumulative receipt
- **Formal credit executed here**: M4B-P2, P3, P4, P5, P8
- **Formal credit carried from Gate 1**: M4B-P1, P6, P7, P10A, P11, P12
- **Outcome ceiling**: provisional finalist; never final winner
- **Gate 1 candidate entry**: Gemma normal finalist; Qwen User defect waiver with P7.1 `FAIL`

## 1. No-repeat entry rule

Gate 2A consumes the Gate 1 cumulative receipt, execution-surface SHA-256 and evidence-manifest SHA.
The receipt's Gate 1 `execution_sha` must be a Git ancestor of the current clean checkout; it is
chronological provenance, not an equality-based carry-forward key. The current checkout may contain
later evidence, ACK, delivery or milestone documentation commits without invalidating Gate 1.

Carry-forward instead verifies the exact Gate 1 lock digest and every shared runtime, model, config,
protocol, fixture, Pi and read-only artifact identity that influences the accepted item. A change to
an execution artifact named by the lock invalidates only its affected P evidence. Ordinary child
startup and cleanup used by the remaining cases are operational prerequisites, not new P1/P7 claims.

If an identity changes, only affected P evidence is invalidated and returned to its owning packet.
Gate 2A must not silently rehash, retune or repair a Gate 1 artifact. P5 is first and only executed
against the model on the physical Pi in this packet.

## 2. Remaining work packages

### G2A-WP01 — P2/P3 product result contract and log hygiene

Run the ten model-backed valid catalog cases three hot repetitions each through one persistent Engine.
Require exact product-schema output and the frozen expected action/tool disposition for all 30 model
results. Run each of the ten invalid/raw-output fixtures three deterministic repetitions at the
reference normalizer boundary; require the documented fallback and no exception for all 30 boundary
results. Scan all owned logs for prompt, raw output, payload, credential, endpoint, hidden-context and
fixture-marker leakage. One failure is P2/P3 `FAIL`; no averaging.

### G2A-WP02 — P4 performance

Using the fixed standard input and 128/16-token envelope, record three independent cold samples, then
one persistent Engine with three discarded warmups and twenty hot samples. Preserve raw wall, init,
TTFT, prefill/decode counts and rates plus P50/P95, RSS/PSS, CPU and temperature. TTFT P95 <=2.5 s and
decode P50 >=4 tok/s is P4 `PASS`; a complete method below target is
`Core threshold decision required`, not automatic failure.

### G2A-WP03 — P5 physical-Pi timeout

Use `M4B-P5-CONTINUOUS-TIMEOUT-002` on the Pi as one outer protocol operation with one frozen
15-second timer. Inside that operation, execute the same public extreme input in consecutive real
model chunks of at most 512 output tokens. Completion/EOS of any chunk has the predeclared
disposition `CONTINUE`: immediately start the identical next chunk under the original timer and
never emit `RESULT`. This continuous-chunk rule is fixed before candidate execution and is neither
an adaptive fixture nor a result-dependent retry.

At the outer deadline, cancel the currently owned generation and require a correlated `TIMEOUT`
from 15.000 through 17.000 seconds, at least one real model chunk started, no hung worker, READY
recovery, then one unchanged standard-config rebuild probe and zero residue. An early `RESULT` is a
packet/adapter defect and makes the evidence `INCONCLUSIVE`; a candidate generation error, wrong or
late terminal, failed timeout cancellation, hang or failed recovery is `FAIL`. There is no fast-model
terminal case and no post-result replacement disposition to request. No workstation model result is
accepted.

### G2A-WP04 — P8 history isolation

Run five frozen nonce/trap single-turn requests through one resident Engine, creating a new
conversation each time. Require no prior nonce/trap reproduction, no KV/context accumulation beyond
the fixed envelope, schema-valid terminals and final zero residue. Store hashes and dispositions,
never model text.

### G2A-WP05 — cumulative provisional decision

Combine this packet's P2/P3/P4/P5/P8 manifest with the accepted Gate 1 receipt. Gemma follows the
normal all-mandatory-item rule. The User separately retained Qwen for Gate 2A with P7.1 `FAIL`; this
waiver permits evaluation but never changes its score. Qwen may be proposed provisionally only when
all newly executed items pass (or P4 has its written threshold decision) and User/Core issue a
written product-workaround disposition for the carried P7.1 defect. At most one provisional
candidate is recommended after User review.

## 3. Cost controls

- Reuse the Gate 1 read-only model receipt and execution-surface digest; do not perform a routine
  multi-gigabyte rehash or require the later documentation commit to equal the Gate 1 Git SHA.
- P2/P3 share one Engine; invalid P3 fixtures never invoke the model.
- P4 retains only the samples required by its formal method.
- P5 and P8 each use one purpose-specific lifecycle plus only their mandated rebuild/cleanup.
- Do not run P1/P6/P7/P10A/P11/P12 again unless their bound identity changed.

## 4. Evidence and reviewer gate

The final executable revision must bind a runner, cumulative-receipt schema, configs, catalog,
`p5-continuous-timeout-002.json`, P8 fixtures, result schema and all checksums. Its entry verifier
must execute an ancestor check plus lock/component digest comparison; direct Gate 1/current `HEAD`
equality is forbidden. Raw model text remains outside Git. Reviewer approval is required before
commit/push, Core delivery or Pi execution.
