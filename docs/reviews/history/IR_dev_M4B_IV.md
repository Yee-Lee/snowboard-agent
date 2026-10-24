---
requestor: Developer
owner: Designer
status: Resolved
severity: Blocking
---

# IR_dev_M4B_IV — token-limit ticket disposal and next-turn admission

- Date: 2026-09-12; Resolved: 2026-09-12
- Work: `CR_M4B_II` WP-02/WP-03; N07/A05/W03 in current `test_spec_M4B.md`
- Authority SHA: `54c506713082b1ea95cfa331f08b7124dcfa0316`
- Next owner: Developer through `CR_M4B_II`; affected WP-02/WP-03 path reopened after focused coverage confirmation.
- USER confirmed this is Blocking and prohibited Developer API invention or CLOSE workaround.
- At opening, independent implementation could proceed while affected admission continuation remained blocked;
  the Designer closure below reopens that path.

## Blocking B1 — measured token-limit R1 has no legal continuation

Product `ch_m4b_llm_production.md` §5.2 requires codepoint-valid input with more than 32 user
tokens to discard its one-use ticket without GENERATE. §6 requires R1 KEEP_NEXT, preserving the
Conversation. Test N07 requires zero generation/mutation; A05 includes superseded-ticket rejection.

Protocol §4.6 permits only GENERATE or CLOSE in MEASURED. MEASURED is a terminal response, so
§4.5 CANCEL for an active request cannot discard this completed request's ticket. There is no
discard operation or legal transition back to a state accepting another MEASURE.

Reproducible contract trace:

1. OPEN → OPENED, generation 1 / revision 0.
2. MEASURE a <=20-codepoint input → MEASURED, user_tokens=33, ticket T1.
3. Emit the exact input-limit notice with KEEP_NEXT; no GENERATE and no Conversation mutation.
4. Next turn supplies a shorter input; MEASURE on the same Conversation is required.
5. The current state table makes that MEASURE protocol E1.

Expected: same Conversation/revision, invalidated T1 and a legal next-turn MEASURE.
Actual contract: no permitted operation achieves it. CLOSE violates KEEP; GENERATE violates
rejection; accepting another MEASURE silently changes the exact wire contract.

### Confirmed native retention evidence

Developer independently inspected the pinned LiteRT-LM C binding at
[`c/conversation.cc:603–623`](https://github.com/google-ai-edge/LiteRT-LM/blob/924e79c91542761242244e4f1651851f822e4cbb/c/conversation.cc#L603-L623).
The renderer stores its output in the native Conversation's `last_rendered_message` member before
returning a C string. Dropping the Python string/ticket therefore does not erase the native copy.
Next-MEASURE supersession replaces that buffer only when another measurement happens; CLOSE
destroys it but violates the required KEEP behavior. The selected disposition must cover this
native buffer as well as parent/child Python buffers, including the interval after rejection and
before another user turn. This is the same B1 disposal/privacy boundary, not permission to invent
a buffer-clearing call or alter the pinned runtime/artifact identity.

Local read-only source snapshot used for this check: `/private/tmp/m4b-pinned-conversation.cc`;
the pinned source URL is the durable locator. Native/Pi behavior has not been executed.

## Designer options (decision required)

1. **Atomic supersession by next MEASURE.** Permit MEASURE in MEASURED. Atomically invalidate
   the old ticket before measuring/issuing the new one. Define how the parent discards T1 after
   R1, whether the child may retain only non-reversible binding metadata until supersession/CLOSE,
   and when the rejected private text is erased. State explicitly how an old ticket becomes
   permanently unusable before any possible subsequent GENERATE. A supersession rule alone must
   not accidentally leave T1 usable between rejection and the next MEASURE.
2. **Explicit ticket-discard command/ack.** Define exact command/ack keys and identities, legal
   source/target state, ticket invalidation and private-text erasure, cancellation/timeout/EOF
   behavior, and terminal proof. Return to CONVERSATION_READY only after acknowledged disposal;
   preserve Conversation/history/KV/revision. Designer selects names/schema, not Developer.

Option 1 is the smaller wire change if its rejection-time invalidation and privacy semantics can
be fully specified. Option 2 gives an explicit completion boundary at the cost of another protocol
operation. Neither option is adopted by this review. No public SM state/Event/Fact is required.

## Minimum acceptance

- 33-token input returns exact R1 input-limit speech + KEEP_NEXT.
- Same Conversation, generation, history/KV and revision; zero GENERATE/native sends/mutation.
- Old ticket is permanently invalid after the selected disposal boundary, including before/after
  subsequent measurements; rejection cannot accidentally authorize it later.
- The next turn can MEASURE and then generate normally; repeated rejected measurements also work.
- CLOSE can still discard an unconsumed ticket and prove cleanup.
- No rejected private input is retained in application/child pending buffers, workdirs, logs or
  public evidence; only approved digest/counter metadata may remain. No automatic replay.
- Test the chosen boundary's stale/mismatched/duplicate/failure behavior with explicit barriers;
  retain N07/A05/W03 and all existing proof/privacy assertions.

Designer must align product §5.2/§7 and protocol §4.3–4.6, and request Tester updates before
Developer implements the selected behavior. Until disposition, no new wire operation, implicit
supersession transition or CLOSE workaround is authorized.

## Designer disposition — 2026-09-12

**Disposition: Revised — B1 confirmed; Option 2 explicit ticket-discard command/ack selected.**

Option 1 is rejected because merely permitting the next MEASURE to supersede T1 leaves a period after R1 policy
rejection in which T1 can still be presented to GENERATE. Parent intent is not a child-enforced invalidation
boundary, so this cannot satisfy the existing discard, privacy and fail-closed requirements.

The revised authority defines:

- exact `DISCARD_TICKET` request and `TICKET_DISCARDED` terminal schemas, bound to request, session, generation,
  Conversation revision, ticket and input digest;
- an atomic `MEASURED -> DISCARDING -> CONVERSATION_READY` path which permanently invalidates the ticket while
  preserving generation, revision, history and KV;
- the existing renderer called with fixed non-private scrub text `"__M4B_TICKET_SCRUB__"` during discard,
  replacing the pinned native `last_rendered_message` while token count remains unchanged; no invented clear API
  or native send is allowed;
- `native_render_scrubbed=true`, `ticket_invalidated=true` and `private_input_erased=true` as mandatory terminal
  proof. MEASURE releases Python temporaries before MEASURED but its native scratch remains ticket-bound until
  GENERATE, acknowledged discard or CLOSE;
- no cooperative CANCEL for the bounded atomic discard; mismatch, duplicate, stale identity, false/missing proof,
  timeout, malformed terminal and EOF are E1 and require PGID destruction proof;
- Reasoner drops its normalized-text local before issuing snapshot-only DISCARD_TICKET, and may publish token-limit R1 only
  after validating the exact terminal and dropping its snapshot. A disposal failure never becomes R1. Erasure
  means no live object reference, not forensic allocator zeroization.

Authority changed in `implement/ch_m4b_llm_production.md` §§5.1–5.2, 7, 8, 11–12 and `protocol.md` §§4.3–4.7.
No public Event, Fact, SM state or `LLMResponse` field changes, and no architecture revision is required.
`TR_spec_M4B_VII` is opened for the focused coverage delta; the affected WP-02/WP-03 path remains blocked until
Tester returns it Revised and Designer confirms the mapping. Unaffected `CR_M4B_II` work may continue.

## Advisory A1 — stale disposition labels

Product §12's final paragraph, protocol preamble and model spec §6.3 retain draft/pending wording;
current status and committed CR explicitly open Developer entry. The explicit current gate governs
unaffected work. Designer reconciled those labels in this authority revision.

## Designer closure — Resolved (2026-09-12)

Tester returned the focused coverage delta in `TR_spec_M4B_VII`. Designer confirmed all 9/9 requested requirements,
the complete identity/proof/failure matrices, native scrub and object-lifetime barriers, permanent invalidation,
same-Conversation continuation, interrupt/CLOSE behavior and the unchanged public boundary. All 13 portable Test
IDs remain present and no implementation/PASS claim was made.

B1 is resolved at design and specification level. The affected `CR_M4B_II` WP-02/WP-03 path is now open for the
Developer to implement the exact authority; implementation and execution evidence remain Pending.
