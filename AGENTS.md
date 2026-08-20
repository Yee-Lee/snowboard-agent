# Audio POC Agent Guide

This repository is an isolated Raspberry Pi 5 audio POC. Every agent must work
backward from the final delivery gate rather than optimizing for a one-off demo.

## Read by task and milestone

Do this at the beginning of a new work session, after a context reset, or when
the milestone state changes:

1. `docs/milestone/README.md` — current status and active milestone.
2. The active `docs/milestone/m*.md` file — entry/exit gate and scope.
3. `docs/audio_poc_workflow.md` — authority for scope, evidence, roles and
   Git/Pi workflow.

Read these only when the task needs them:

- `docs/specs/audio_poc_delivery_checklist.md` — milestone entry, gate
  review, delivery-manifest work, or a task that claims to close a final item.
- `docs/specs/audio_poc_development_guide.md` — POC code, wrappers,
  fixtures, candidate comparison, or combined-pipeline work.
- `docs/specs/core_audio_m3_requirements.md` — M3 work or any change that
  touches the Audio HAL contract.
- `poc_audio/README.md` — workstation/Pi checkout preparation or remote test
  execution.

Do not reread unchanged documents during the same task merely by habit. Follow
links from the active milestone only when the current task needs that detail.

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
- Use `audio` as the only persistent development branch. Local WIP commits may
  be squashed before a candidate is published, but a published or submitted
  candidate SHA is immutable and must never be rewritten with reset or rebase.
- Record rejected validation evidence and append fixes on top of the rejected
  candidate. Converge those new fixes into the next candidate without altering
  any previously submitted SHA.
- Create immutable annotated tags `m0`, `m1`, and so on only when the matching
  milestone or readiness gate is formally complete. Never move an existing
  milestone tag.
- At every milestone gate, update the milestone index, remaining-delivery
  assessment, risks, and any required adjustment request.

## Final Outcome

The POC must deliver one approved VAD, ASR, and TTS baseline, or an explicit
evidence-backed no-go. The result must be reproducible on Raspberry Pi 5,
offline, cancellable, clean after failure, integrated with a pinned M3 Audio HAL
SHA, and proven with at least 20 combined sessions. Submission is only ready for
internal review until all blocking findings are closed.
