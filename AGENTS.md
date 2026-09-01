# ASR Product R1 Agent Guide

This repository evaluates low-latency, local, streaming ASR on Raspberry Pi 5
CPU-only hardware.

## Read first

At a new session, context reset, or milestone change, read:

1. `docs/milestone/README.md`.
2. The active `docs/milestone/ar1_m*.md` file.
3. `docs/workflow.md`.

Read the relevant file under `docs/specs/` before changing evaluation, runtime
protocol, fixtures, or the outcome checklist. The inbound contract is under
`docs/handoff/inbound/`.

## Required behavior

- The permanent development branch is `asr_r1`.
- The immutable historical control is `audio_m4` at
  `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`.
- AR1 milestone tags are `asr_r1_m0` through `asr_r1_m4`. Create an annotated
  tag only after formal completion; never move it.
- Candidate SHAs become immutable when published, submitted, or used for Pi
  evidence. Append fixes; never rewrite a submitted SHA.
- Real execution requires milestone entry, exact identities, a clean SHA, a
  frozen packet, and reviewed evidence.
- Hardware results are `PASS`, `FAIL`, or `INCONCLUSIVE` only after review.
- Obtain explicit User approval before creating or pushing any commit that
  contains formal scores, rankings, hardware-result dispositions,
  qualification decisions, or final outcome language. Draft measurements and
  scorecards must be labeled non-formal and must not imply approval.
- Keep models, binaries, private audio, sensitive transcripts, credentials,
  endpoints, raw results, and operator configuration out of Git.
- Do not modify the Snowboard product composition root.
- Post-process and second-scorer work is diagnostic only and does not enter the
  formal AR1M3 comparison.
- Preserve failed evidence and never relax a method after seeing results.
- Development code and scripts must reference repository resources only with
  paths relative to the repository root. Never hard-code host-specific
  absolute paths or depend on a checkout location, and reject any resolved
  repository-resource path that escapes the repository root.
- The workstation must support the complete non-formal functional test suite.
  Reserve formal scoring/comparative results and integrated product
  qualification for Pi 5; Pi smoke still repeats critical functional and
  lifecycle cases and workstation results never substitute for Pi evidence.

## Git commits

Use `[work_type][AR1Mx/stage]: concise title` with a concise English bullet-list
body near 60 words. Commit complete, reviewable work segments, not every
investigation step.

## Final outcome

AR1M4 submits exactly `SUPPORTED`, `NOT_SUPPORTED`, or `INCONCLUSIVE`. User owns
the product decision. AR1 cannot accept a Core gate, create `ALPHA.R1`, or
select M5.
