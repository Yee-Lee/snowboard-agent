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
- Keep models, binaries, private audio, sensitive transcripts, credentials,
  endpoints, raw results, and operator configuration out of Git.
- Do not modify the Snowboard product composition root.
- Post-process and second-scorer work is diagnostic only and does not enter the
  formal AR1M3 comparison.
- Preserve failed evidence and never relax a method after seeing results.

## Git commits

Use `[work_type][AR1Mx/stage]: concise title` with a concise English bullet-list
body near 60 words. Commit complete, reviewable work segments, not every
investigation step.

## Final outcome

AR1M4 submits exactly `SUPPORTED`, `NOT_SUPPORTED`, or `INCONCLUSIVE`. User owns
the product decision. AR1 cannot accept a Core gate, create `ALPHA.R1`, or
select M5.
