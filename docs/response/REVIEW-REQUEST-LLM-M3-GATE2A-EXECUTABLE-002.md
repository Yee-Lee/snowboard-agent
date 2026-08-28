# REVIEW-REQUEST-LLM-M3-GATE2A-EXECUTABLE-002

- **Status**: `READY FOR INDEPENDENT REVIEW / WORKTREE ONLY / NOT EXECUTED`
- **Date**: 2026-08-28
- **Branch / base HEAD**: `llm` / `21a13fdf4a936ca9a73256714bdc7e3bca4cca98`
- **Packet**: `G2A-PI-LLM-002`
- **Candidate lock SHA-256**: `36d6447fe040fcb0f9637decba505c58626e1bd3c66a0a626ce275e14bd3e118`
- **Review scope**: executable design only; no Pi result or candidate proposal

## Requested decision

Please return `APPROVE` or one bounded `REVISION_REQUIRED` list for the Gate 2A executable
candidate. Review the worktree itself because this revision is intentionally not committed or
pushed before approval.

## Resolved entry findings

The prior audit found that `run_gate2a_pi.py` and `gate2a-pi-lock-v1.json` implemented obsolete
packet `001`, required a superseded Gate 1 `006` receipt, reran P1/P6/P7/P10A/P11/P12 and used the
one-shot P5 fixture. The replacement:

1. authenticates `G1-M4B-CLOSURE-001`, the Core Gate 1 closure ACK, both nested Gate 1 locks and all
   shared component identities;
2. requires the Gate 1 execution SHA to be an ancestor of the current clean execution SHA;
3. reuses a schema-valid Gate 1 artifact receipt by immutable filesystem metadata and performs zero
   routine full-model hashes;
4. executes and scores only P2/P3/P4/P5/P8, carrying P1/P6.1/P7.1/P10A/P11/P12 unchanged;
5. forces Qwen P7.1 to remain `FAIL / SLOW_RECOVERY` and prevents normal provisional eligibility;
6. separates the frozen 128/16 P4 profile from the 128/64 product-contract profile used by P2/P8,
   while freezing P5 Gemma Engine/chunk 1024/512 and Qwen 512/256;
7. implements P5 as repeated official asynchronous real-model chunks under one 15-second outer
   protocol timer, followed by same-child health and a standard-process rebuild;
8. gives P8 an independent resident Engine, fresh Conversation per request, prior-marker checking
   and a per-turn KV bound without storing model text.

## Primary review surface

- `poc_llm/tests/gate2/GATE2A-PI-PACKET-002.md`
- `poc_llm/harness/gate2a-pi-lock-v2.json`
- `poc_llm/tools/run_gate2a_pi_v2.py`
- `poc_llm/harness/litert_lm_pi_p5_child_adapter_v1.py`
- `poc_llm/contracts/m1/strict-config-pi-p5-v1.schema.json`
- `poc_llm/contracts/m1/strict-config-pi-product-v1.schema.json`
- `poc_llm/evidence/m4b/gate1-closure-entry-v1.schema.json`
- `poc_llm/evidence/m4b/gate2a-pi-v2-result.schema.json`
- `poc_llm/fixtures/gate2/gate1-closure-entry-001.json`
- `poc_llm/fixtures/gate2/gate2a-public-catalog-002.json`
- `poc_llm/fixtures/gate2/p5-continuous-timeout-002.json`
- `poc_llm/fixtures/gate2/p8-state-isolation-001.json`
- `poc_llm/fixtures/gate2/pi-configs-v2/`
- `poc_llm/tests/gate2/test_gate2a_pi_v2.py`

## Required reviewer checks

- Verify the lock closes every direct and inherited executable input and that no self-referential
  source-SHA rule was reintroduced.
- Verify P2 is exact 10 cases × 3, P3 is deterministic exact fallback 10 × 3, P4 is cold 3 plus
  warmup 3 plus hot 20, P5 is one fixed continuous timeout operation, and P8 is five isolated turns.
- Verify P5 cannot emit an early success or select a post-result/adaptive fixture and invokes native
  cancellation exactly once for the timed-out operation; missing/late terminals and rebuild failure
  are candidate `FAIL`, while a pre-timeout `RESULT` remains definition `INCONCLUSIVE`.
- Verify P2 rejects the exact fallback on normal cases, P8 requires the current nonce exactly once,
  and neither uses the 16-token performance/minimal profile.
- Verify result semantics distinguish candidate `FAIL`, infrastructure `INCONCLUSIVE`, and complete
  P4 method below the negotiable threshold.
- Verify the Qwen waiver only authorizes evaluation and cannot rewrite P7.1 or produce a normal
  recommendation without the later User/Core workaround disposition.
- Verify no raw prompt, transcript, model output, model, runtime wheel, credential or endpoint is
  written to Git evidence.
- Verify one candidate consumes one clean reboot and prior boot/candidate reuse fails closed.

## Verification already run

```text
python3 -m unittest discover -s poc_llm/tests/gate2 -p 'test_*.py'
Ran 42 tests — OK

python3 -m unittest discover -s poc_llm/tests/gate1 -p 'test_*.py'
Ran 136 tests — OK

python3 -m py_compile poc_llm/tools/run_gate2a_pi_v2.py \
  poc_llm/harness/litert_lm_pi_p5_child_adapter_v1.py
exit 0

python3 poc_llm/tools/run_gate2a_pi_v2.py --fatal-outcome-self-test
exit 4
```

These checks prove the definition and retained regression surface only. They do not authorize or
claim a physical-Pi result. After approval, the next step is one milestone commit, then separate
clean-reboot Gemma and Qwen executions using their persisted Gate 1 artifact receipts.
