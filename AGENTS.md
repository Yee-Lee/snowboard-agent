# Audio POC Agent Guide

This repository is an isolated Raspberry Pi 5 audio POC. Every agent must work
backward from the final delivery gate rather than optimizing for a one-off demo.

## Read First

Read these files before planning, changing code, or running hardware tests:

1. `docs/audio_poc_workflow.md` — authoritative working process, scope, roles,
   evidence rules, and final-delivery traceability.
2. `docs/milestone/README.md` — current milestone status and the active
   milestone document.
3. `docs/pm_handoff/audio_poc_development_guide.md` — POC requirements.
4. `docs/pm_handoff/audio_poc_delivery_checklist.md` — final delivery gate.
5. `docs/pm_handoff/core_audio_m3_requirements.md` — M3 Audio HAL dependency.

## Required Working Behavior

- M0 is a readiness gate. M1–M4 are the four delivery milestones.
- Treat `docs/milestone/README.md` as the single source of truth for current
  milestone status. Do not silently start a later milestone.
- Before doing work, identify which final checklist item it advances. Do not do
  work with no delivery contribution.
- Hardware results are `PASS`, `FAIL`, or `INCONCLUSIVE` only after evidence is
  reviewed. A verbal report or successful demo is not a pass.
- Never relax a frozen gate after seeing candidate results. Raise a change
  request when the final goal is no longer reachable under current assumptions.
- Keep POC orchestration out of the product composition root. Do not add
  barge-in, AEC, wake word, or unrelated product features.
- Do not commit models, large results, private audio, secrets, or sensitive
  transcripts.
- At every milestone gate, update the milestone index, remaining-delivery
  assessment, risks, and any required adjustment request.

## Final Outcome

The POC must deliver one approved VAD, ASR, and TTS baseline, or an explicit
evidence-backed no-go. The result must be reproducible on Raspberry Pi 5,
offline, cancellable, clean after failure, integrated with a pinned M3 Audio HAL
SHA, and proven with at least 20 combined sessions. Submission is only ready for
internal review until all blocking findings are closed.
