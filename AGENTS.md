# LLM POC Agent Guide

This repository is an isolated Raspberry Pi 5 LLM POC (M4b). Every agent must work
backward from the final delivery gate rather than optimizing for a one-off demo.

## Read by task and milestone

Do this at the beginning of a new work session, after a context reset, or when
the milestone state changes:

1. `docs/milestone/README.md` — current status and active milestone.
2. The active, or next when none has started, `docs/milestone/m*.md` file — entry/exit gate and scope.

Read these only when the task needs them:

- `docs/llm_poc_workflow.md` — authority when work touches scope, evidence or
  result semantics, roles, milestone gates/status, test packets, Git/Pi work,
  data/artifact handling, delivery handoff, or when the shorter documents are
  ambiguous.
- `docs/pm_handoff/DELIVERY-LLM-POC-M4B-CONTRACT-001.md` — authoritative M4b LLM POC contract (read-only income).
- `docs/pm_handoff/core_llm_m4b_tasks.md` — M4b boundary reference (read-only income).
- `poc_llm/README.md` — workstation/Pi checkout preparation or remote test execution.

Do not reread unchanged documents during the same task merely by habit. Follow
links from the active milestone only when the current task needs that detail.

## Document Handling & Communication Rules

- **`docs/pm_handoff/` is Read-Only**: Incoming requirements, contracts, and handoff messages from PM / Core Team are strictly read-only.
- **Handoff Archival (`docs/pm_handoff/history/`)**: When an incoming handoff message is completed, superseded, or no longer actively tracked, move it to `docs/pm_handoff/history/`. Do not delete incoming message records.
- **Team Responses & Replies**:
  - Use `docs/response/` for internal technical ACK, assessments, and requirement mapping (`ACK-*.md`).
  - Use `docs/delivery/` for formal external handoffs and deliverables to be relayed by PM (`DELIVERY-*.md`).
  - **Never edit or write responses directly inside `docs/pm_handoff/`**.

## Required Working Behavior

- M4b is the target LLM delivery milestone. Treat `docs/milestone/README.md` as the single source of truth.
- Before doing work, identify which final checklist item it advances. Do not do work with no delivery contribution.
- Hardware results are `PASS`, `FAIL`, or `INCONCLUSIVE` only after evidence is reviewed.
- Keep POC orchestration out of the product composition root. Do not add unrelated product features.
- Do not commit models, large results, private prompts, secrets, or sensitive data.
- At every milestone gate, update the milestone index, risks, and adjustment requests.
- Editing plans or scaffolds does not start a milestone. A milestone starts only after its entry review is complete and the milestone index is explicitly changed to `IN_PROGRESS`.

## Final Outcome

The POC must deliver an approved LiteRT-LM runtime, model baseline, prompt boundary, and child process protocol. The result must be reproducible on Raspberry Pi 5, offline, cancellable, clean after failure, integrated with an accepted M4a Audio HAL SHA, and proven with at least 20 combined sessions. Submission is only ready for internal review until all blocking findings are closed.

