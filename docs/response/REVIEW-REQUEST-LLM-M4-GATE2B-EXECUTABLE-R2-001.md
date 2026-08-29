# REVIEW-REQUEST-LLM-M4-GATE2B-EXECUTABLE-R2-001

- **Status**: `NON-BLOCKING PARALLEL REVIEW / USER AUTHORIZED PI EXECUTION`
- **Date**: 2026-08-29
- **Supersedes**: `REVIEW-REQUEST-LLM-M4-GATE2B-EXECUTABLE-001`
- **Branch / correction base HEAD**: `llm` / `d79ade7cacc5bcd7abe4fbc2825d601c3fb58c39`
- **Packet**: `G2B-PI-COMBINED-001`
- **Candidate replacement lock SHA-256**: `da1a8a58adc86d412b960f3ee3107e5040ca75a0efe9a13570bb70271f84cb90`
- **Requested response**: `docs/reviews/REVIEW-LLM-M4-GATE2B-EXECUTABLE-R2-001.md`
- **Review scope**: executable and entry validity only; no Pi result or winner proposal

## Requested decision

Return `APPROVE` or one bounded finding list. The User has authorized this exact replacement to be
committed/pushed and executed on Pi without waiting for the response; any finding therefore applies
to evidence review or an affected replacement run and may not rewrite the frozen attempt.

Initial formal attempt `G2B-PI-COMBINED-001` is immutable and `INCONCLUSIVE`: its controlled store
omitted two sherpa wheel sources required by Accepted TTS verification, so TTS rejected startup before
LLM residency and zero sessions ran. Cleanup reached zero residue. Review the corrected pre-residency
input closure for replacement run `G2B-PI-COMBINED-002`; do not reinterpret attempt 001 as candidate
failure or authorize overwriting its evidence.

Attempt `G2B-PI-COMBINED-002` is also immutable and `INCONCLUSIVE`. It authenticated the corrected
Audio closure and started all four domains, but Pi memory PSI was disabled at boot; zero sessions ran
and cooperative cleanup reached zero residue. Review the added pre-residency resource-probe gate and
the PSI-enabled environment for attempt `G2B-PI-COMBINED-003`; do not reinterpret attempt 002 as a
candidate failure.

## Why R2 is required

The original request predates final Gate 2A evidence. Its consumer expected an all-PASS provisional
receipt and still discussed Qwen eligibility. The User instead preserved both candidates' machine
results, selected Gemma as the sole model finalist, rejected Gemma's old product pairing and excluded
Qwen from formal Gate 2B. R2 replaces that consumer without changing historical evidence:

1. the repo-locked Gate 2A receipt retains Gemma P2/P8 `FAIL` and authenticates the actual reviewed
   result, Gate 2A lock, Gate 1 entry and artifact receipt;
2. the Gate 2B lock contains only Gemma and a new versioned generic structured-product adapter/config;
3. the first model contact for the new pairing is the held-out 20-session combined run, so no scored
   Audio transcript or expected response can be used for prompt tuning;
4. Core semantic/selection ACK may arrive during execution under the User's instruction but remains
   mandatory before final delivery.

## Primary review surface

- `docs/response/ASSESSMENT-LLM-M4-GATE2B-ENTRY-AUDIT-001.md`
- `poc_llm/tests/gate2/GATE2B-PI-PACKET-001.md`
- `poc_llm/harness/gate2b-pi-lock-v1.json`
- `poc_llm/tools/run_gate2b_pi_v1.py`
- `poc_llm/harness/litert_lm_gate2b_child_adapter_v1.py`
- `poc_llm/harness/gate2b_combined_v1.py`
- `poc_llm/harness/gate2b_resources_v1.py`
- `poc_llm/contracts/m1/strict-config-pi-gate2b-product-v1.schema.json`
- `poc_llm/evidence/m4b/gate2a-model-finalist-receipt-v1.schema.json`
- `poc_llm/evidence/m4b/accepted-audio-entry-v1.schema.json`
- `poc_llm/evidence/m4b/gate2b-pi-v1-result.schema.json`
- `poc_llm/fixtures/gate2/gate2a-gemma-model-finalist-001.json`
- `poc_llm/fixtures/gate2/accepted-audio-entry-001.json`
- `poc_llm/fixtures/gate2/pi-configs-v2/CAND-LRT-G4E2B-MOBILE-R1-gate2b-product.json`
- `poc_llm/tests/gate2/test_gate2b_combined_v1.py`

## Required reviewer checks

- Confirm no Qwen or old Gate 2A product pairing can enter and no historical P2/P8 result is
  rewritten.
- Confirm the new prompt is generic, deterministic, schema-bound and free of scored session/case
  fixtures; validate the held-out first-contact rule.
- Reproduce the lock and validate all repository artifacts, Gate 2A receipt/result chain, clean exact
  Audio tag/completion and clean exact Core HAL checkout requirements.
- Confirm fixture-lock/manifest, VAD model, ASR worker/model, TTS archive/vocoder, both sherpa wheel
  sources and isolated runtime identities fail closed before residency timing. Static hashes must not
  enter LLM READY or P9/P10B.
- Confirm the POC controller imports the exact Core HAL but does not claim to execute the product
  composition root.
- Confirm post-READY Audio and LLM operation failures become P10B candidate failures, while sampler,
  environment and evidence failures remain `INCONCLUSIVE`.
- Confirm one shared residency runs exactly 20 ordered sessions, in-memory ASR→LLM→TTS transfer,
  19 measured five-second pauses, memory/thermal/PSI/OOM/leak gates and reverse cleanup.
- Confirm memory/PSI/OOM/thermal probe availability is rejected before any domain residency.
- Confirm `--preflight-only` authenticates the full formal entry with no evidence directory, formal
  credit, model/domain residency or formal run-ID consumption.
- Confirm logs and sanitized evidence cannot persist transcript, prompt, speech, credential, endpoint,
  artifact or raw audio content.
- Confirm a dirty/pre-existing path or drifted external input is rejected and never deleted.

## Verification already run

```text
python3 -m unittest discover -s poc_llm/tests/gate2 -p 'test_gate2b_combined_v1.py'
Ran 29 tests — OK

python3 -m py_compile poc_llm/harness/litert_lm_gate2b_child_adapter_v1.py \
  poc_llm/tools/run_gate2b_pi_v1.py
exit 0

python3 -m json.tool <each new or modified Gate 2B JSON/schema>
exit 0

git diff --check
exit 0
```

These prove the replacement definition only. The User separately authorized commit/push, Pi access,
artifact staging and execution. Result publication and a winner proposal still require User review.
