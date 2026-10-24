---
requestor: Designer
owner: Architect
status: Resolved
severity: Blocking
---

# AR_impl_M4B_IV — planned-recovery timing ownership review

This is the single-question architecture review for the clean M4B replacement design. It does not reopen Accepted
M4A, the verified Foundation revision, model selection, generic EventBus/State Manager/Resource Manager, or legacy
M4B packages. Admission, request-failure cleanup and listen-only product composition are implementation/design
consistency matters and are explicitly outside this architecture request. Superseded active reviews that cite
M4B-MVA-002 cannot resolve this request or release this gate.

## Authority under review

- [`ch_m4b_llm_production.md`](../../implement/ch_m4b_llm_production.md) §5 currently lets the adapter schedule
  same-key planned recovery after Conversation cleanup proof.
- [`ch05_resource_manager.md`](../../implement/ch05_resource_manager.md) §6.2 exposes the narrow injected
  `ScheduleRecovery/WaitRecovery` seam to the adapter, while verification item 28 requires Product Session end
  before same-key recycle.
- [`m4b_foundation_revision.md`](../../implement/m4b_foundation_revision.md) §7 gives SM a private
  `workers -> conversation_close -> recovery -> complete` convergence phase and permits session tracking to clear
  only after any required recovery barrier.
- Existing `arch.md` §§4.1, 4.8 and 6.5–6.7 remain upstream authority. In particular, §6.7 makes SM owner of
  Conversation replacement and Product Session end timing while RM owns the recovery timer and rebuild barrier.

## One blocking question

**Must SM exclusively authorize the start of planned recovery because it uniquely owns Product Session end
timing, while the adapter only marks `RECYCLE_PENDING`, supplies terminal/Conversation cleanup proof and executes
the narrow recovery operation? Or may the adapter autonomously call `ScheduleRecovery` as soon as it observes
Conversation cleanup proof, before SM has completed its private session-end convergence?**

Conversation cleanup proves an adapter-owned resource condition; it does not by itself prove that SM has finished
the Product Session's action/rest, buffer policy, tracking and wake-admission sequence. The current adapter-scheduled
wording therefore appears able to cross the SM-owned session boundary even though it forbids active inference.

## Designer's proposed ownership

1. A memory-capacity outcome returns `END_SESSION`; the adapter atomically records `RECYCLE_PENDING` but does not
   start recovery.
2. SM finishes the primary action/rest path, blocks admission and obtains matching Conversation cleanup proof.
3. In SM's existing private post-close recovery phase, SM authorizes one narrow same-key recovery call.
4. Adapter/composition invokes the existing seam; RM alone owns rebuild, timeout and barrier mechanics.
5. SM completes session clearing, wake admission and `IDLE` only after READY. Recovery failure remains Level 3.

This adds no public state, Event, Fact or `LLMResponse` field. It only makes the existing private convergence phase
the authorization point for planned recovery.

## Requested disposition

Architect either:

- confirms that existing architecture already requires the proposed SM authorization boundary, with exact
  citations, after which Designer will align the two implementation chapters; or
- revises only the affected architecture clause if autonomous adapter scheduling is intended, explicitly defining
  what proof allows Adapter to act before SM completes Product Session convergence, and marks this request
  `Revised` for focused review.

Any Blocking finding must identify the conflicting approved clause and provide the minimum replacement wording.
Prompt quality, numeric response targets, legacy compatibility and implementation style are outside this review.
Developer and Tester entries remain closed.

## Architect disposition — Confirm

**Existing architecture already requires SM exclusive authorization of planned-recovery start timing.**
No `arch.md` revision is needed. The Designer's five-step proposal (§ "Designer's proposed ownership" above)
is fully consistent with the following approved clauses:

### Citations

1. **`arch.md` §6.7 (L795–803) — SM owns session-end timing**:
   SM owns "WAKE readiness、action route、Conversation replacement 與 session end 時序".
   Recovery timer and rebuild barrier belong to RM. Because planned recovery must occur within the
   session-end convergence path, its authorization timing is part of session-end timing and therefore SM-owned.

2. **`arch.md` §6.5 (L754–773) — SM drives all four convergence paths**:
   All four trigger paths (rest / interrupt / error / shutdown) execute the same SM-driven convergence sequence
   including the RM recovery-barrier readiness gate before returning to IDLE. The adapter is a narrow executor
   within this sequence, not its initiator.

3. **`arch.md` §4.1 (L404–407) — proof requirements for cross-module operations**:
   The sequential replacement barrier requires SM to complete admission block → terminal/join proof →
   Conversation cleanup proof before proceeding. Session end is strictly more than replacement (adds buffer
   flush, tracking settlement, wake-admission). Cleanup proof alone is necessary but not sufficient to prove
   SM has completed session convergence.

4. **`m4b_foundation_revision.md` §7 (L301–320) — already correctly implements this boundary**:
   The `_PendingConvergence` phase `workers → conversation_close → recovery → complete` places recovery
   after conversation_close and before complete, inside SM's private convergence. Session tracking clears
   only after lifecycle proof, in-flight empty, and recovery barrier are all satisfied.

5. **`ch05_resource_manager.md` §6.2 (L510–515) + verification item 28 (L641)**:
   The RM seam does not check Product Session state; the caller is responsible for preconditions.
   Verification item 28 explicitly requires "先完成產品session結束再同key回收". Both support SM
   authorization, not adapter-autonomous scheduling.

### Wording gap

`ch_m4b_llm_production.md` §5.3 (L258–260) says "The adapter **schedules** a planned same-key LLM recovery
only after session-end Conversation cleanup proof." This wording lets the adapter autonomously call
`ScheduleRecovery` upon observing cleanup proof, which is necessary but not sufficient — it does not prove
SM has completed buffer flush, tracking settlement, or session-end convergence. This crosses the SM-owned
session boundary defined by §6.7.

### Required action (Designer authority)

Align `ch_m4b_llm_production.md` §5.3 wording so that planned recovery is authorized by SM within its
private post-close convergence phase (as `m4b_foundation_revision.md` §7 already implements), not
autonomously scheduled by the adapter upon cleanup proof alone. Exact wording is Designer's choice.

No architecture clause is revised. No new public state, Event, Fact, or `LLMResponse` field is introduced.

### Unchanged invariants

- §4.1 Conversation lifetime/cardinality and sequential replacement barrier
- §6.5 four-path convergence with unified Level 2→3 escalation
- §6.7 full responsibility matrix (HAL / Worker / Bus / SM / main.py)
- §6.1 RM recovery rebuild role
- §6.4 three-level cancel hierarchy

### Next owner

Designer — align `ch_m4b_llm_production.md` §5.3, then mark this review `Resolved`.

## Designer resolution — Resolved

Designer aligned `ch_m4b_llm_production.md` §5.3 with the confirmed boundary:

- Adapter atomically marks `RECYCLE_PENDING` and cannot treat Conversation cleanup proof alone as recovery
  authorization.
- SM authorizes planned recovery only in its private post-close Product Session convergence phase.
- Adapter/composition invokes the narrow seam; RM owns rebuild, timeout and barrier mechanics.
- SM waits for READY before clearing session tracking, resuming wake admission or returning to `IDLE`.

No `arch.md` change, public state, Event, Fact or `LLMResponse` field was required. The single Blocking question is
resolved and `M4B-ARCH-REVIEW` is closed. Tester and Developer entries remain closed pending the separately opened
replacement coverage round.
