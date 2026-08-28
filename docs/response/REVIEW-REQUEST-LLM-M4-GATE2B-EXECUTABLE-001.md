# REVIEW-REQUEST-LLM-M4-GATE2B-EXECUTABLE-001

- **Status**: `READY FOR INDEPENDENT REVIEW / WORKTREE ONLY / NOT EXECUTED`
- **Date**: 2026-08-28
- **Branch / base HEAD**: `llm` / `21a13fdf4a936ca9a73256714bdc7e3bca4cca98`
- **Packet**: `G2B-PI-COMBINED-001`
- **Candidate lock SHA-256**: `c8f09ed4e8e0f459afa638c99560f8ffe779c9be1c0352be421feb1dc161d346`
- **Review scope**: Gate 2B executable design only; no hardware result or winner proposal

## Requested decision

Please return `APPROVE` or one bounded `REVISION_REQUIRED` list. Review the worktree because the
candidate remains intentionally uncommitted until the executable review is complete.

## Accepted inputs and corrected integration

The previously listed Accepted Audio blocker is resolved. The executable pins:

- Audio delivery `POC-audio-DEL-2026-001-R1`;
- annotated tag `audio_m4` with tag-object SHA
  `24b2571a23dde2f77027242b61142b0c1a59924c`, targeting the accepted completion below;
- accepted completion SHA `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`;
- corrected delivery SHA `ca51bce9b4e205d9c9faf004d41c27169f108a3f`;
- P9.1/combined execution SHA `8be3bc095b504b8eab1dfeb21b94173728b9656f`;
- Core response `RESP-AUDIO-M4-GATE2B-001` /
  `be19b70b1dd91674e7ff981eb9d6b2dca9741f54`;
- Core HAL execution SHA `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf`.

The accepted Audio coordinator itself cannot provide M4B evidence because it hashes and discards the
ASR hypothesis and then uses a deterministic session-to-TTS mapping. The new coordinator preserves
the accepted VAD/ASR/TTS implementations but adds the missing real boundary: ASR transcript exists
only in memory, is sent to the persistent LiteRT-LM child, and the resulting `speak` text exists only
in memory before it is consumed by accepted TTS and real Core AudioOutput.

## Primary review surface

- `poc_llm/tests/gate2/GATE2B-PI-PACKET-001.md`
- `poc_llm/harness/gate2b-pi-lock-v1.json`
- `poc_llm/tools/run_gate2b_pi_v1.py`
- `poc_llm/harness/gate2b_combined_v1.py`
- `poc_llm/harness/gate2b_resources_v1.py`
- `poc_llm/evidence/m4b/gate2a-provisional-receipt-v1.schema.json`
- `poc_llm/evidence/m4b/accepted-audio-entry-v1.schema.json`
- `poc_llm/evidence/m4b/gate2b-pi-v1-result.schema.json`
- `poc_llm/contracts/m1/strict-config-pi-product-v1.schema.json`
- `poc_llm/fixtures/gate2/accepted-audio-entry-001.json`
- `poc_llm/tests/gate2/test_gate2b_combined_v1.py`

## Required reviewer checks

- Verify exact clean Audio/Core Git identities, the annotated tag object plus dereferenced completion,
  and every portable-kit hash fail closed before model or Audio load.
- Verify the Gate 2A receipt is insufficient by itself: its actual User-reviewed result hash, schema,
  P-item map, lock, Gate 1 entry and model receipt must all match.
- Verify the Gate 2A receipt selects exactly one User-reviewed candidate; Gemma may proceed while the
  general Core Gate 2A ACK is pending, but final delivery still requires it. Qwen cannot enter without
  a written workaround accepted by both User and Core, and its P7.1 remains `FAIL`.
- Verify all four domains load once, the sampler obtains an idle simultaneous-residency sample before
  session 1, 20 frozen sessions execute with the 64-output product profile, all current markers are
  proven, 19 measured five-second pauses occur and shutdown is
  LLM→TTS→ASR→VAD.
- Verify P9 uses only `MemTotal-MemAvailable <= 3584 MiB`, swap zero, PSI full-stall delta zero,
  OOM-kill delta zero, complete non-overlapping owner trees and bounded sampler gaps. RSS/PSS remain
  diagnostic but are recorded per owner.
- Verify P10B correlates every VAD/ASR/LLM/TTS terminal, actually feeds LLM speech into TTS, checks
  temperature/throttling, detects prior-session markers and proves process/device cleanup.
- Verify the empty fault schedule is justified: integration introduces no new cancel/failure
  protocol, so accepted Audio/LLM failure credit is carried rather than replayed or double-counted.
- Verify no surrogate code can be selected and no transcript, prompt, LLM output, model, runtime,
  credential or endpoint enters Git evidence.
- Verify dirty pre-existing evidence/install/work paths are rejected and never deleted.

## Verification already run

```text
python3 -m unittest discover -s poc_llm/tests/gate2 -p 'test_*.py'
Ran 42 tests — OK

python3 -m py_compile poc_llm/tools/run_gate2a_pi_v2.py \
  poc_llm/tools/run_gate2b_pi_v1.py \
  poc_llm/harness/litert_lm_pi_p5_child_adapter_v1.py \
  poc_llm/harness/gate2b_combined_v1.py \
  poc_llm/harness/gate2b_resources_v1.py
exit 0

python3 poc_llm/tools/run_gate2b_pi_v1.py --fatal-outcome-self-test
exit 4
```

These are workstation definition results only. After review, Gate 2A must execute and its evidence
must be User-reviewed before this runner can receive a real entry receipt. Physical Audio artifact
availability and exact controlled paths must also be confirmed on the Pi before the combined run.
