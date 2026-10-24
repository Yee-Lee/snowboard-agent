---
requestor: Designer
owner: Tester
status: Resolved
severity: Blocking
---

# TR_spec_M4B_VII — explicit ticket-disposal coverage delta

- Date: 2026-09-12; Resolved: 2026-09-12
- Scope: focused delta only; `IR_dev_M4B_IV` disposition and revised product/protocol authority
- Baseline: `test_spec_M4B.md` approved through resolved `TR_spec_M4B_VI`
- Next owner: Developer through `CR_M4B_II`

## Request

Revise the existing `test_spec_M4B.md` in place for the selected `DISCARD_TICKET` /
`TICKET_DISCARDED` contract. Preserve all existing Test IDs and assertions except the now-invalid implicit
supersession wording. This is specification work only; do not execute tests or claim implementation PASS.

At minimum, map explicit cases to the existing `M4B-NORM-001`, `M4B-ADM-001`, `M4B-WIRE-001`,
`M4B-OUTCOME-001` and `M4B-PRIV-001` groups covering:

1. a codepoint-valid 33-token MEASURE followed by exact acknowledged disposal before the input-limit R1 Fact;
2. unchanged session, generation, revision, history and KV; zero GENERATE/native send/semantic mutation; child
   Python temporaries gone before MEASURED, Reasoner normalized-text local gone before issuing discard, and all rejected
   private text absent from live objects before R1;
3. the discarded ticket permanently rejected, then a new MEASURE and normal GENERATE on the same Conversation;
4. repeated 33-token rejection/disposal cycles followed by a successful short turn;
5. exact request/session/generation/revision/ticket/digest and all three proof booleans on TICKET_DISCARDED;
6. the fixed `"__M4B_TICKET_SCRUB__"` scrub-render barrier replaces native `last_rendered_message`, leaves token
   count unchanged and performs no native send; scrub/render/count failure is E1 and no success terminal is accepted;
7. stale, mismatched and duplicate discard plus false/missing proof, malformed/wrong terminal, timeout and EOF;
   these are E1, never R1, and require bounded PGID cleanup proof;
8. DISCARDING accepts no CANCEL or reentrant command; a racing interrupt waits for the terminal or converges by
   the E1 cleanup boundary;
9. CLOSE from MEASURED still discards an outstanding ticket and proves Conversation cleanup.

Update protocol section references after insertion of §§4.4/4.7. Remove `superseded` from A05 unless an actual
authorized supersession transition exists; replace it with discarded-ticket coverage. Use explicit barriers, not
correctness sleeps. Return this review as Revised with exact changed rows and a requirement-to-case mapping for
Designer confirmation.

## Exit

Designer confirms complete mapping, resolves this review and `IR_dev_M4B_IV`, then reopens the affected
`CR_M4B_II` WP-02/WP-03 path. Unaffected Developer work may continue while this request is Open.

## Tester response — Revised (2026-09-12)

Tester revised the existing
[`test_spec_M4B.md`](../test_spec/test_spec_M4B.md) in place. This is a focused specification delta only;
no production code, executable test, candidate execution or PASS claim was introduced. All existing Test IDs
and unrelated assertions remain intact.

### Exact changed rows

| Existing Test ID | Changed rows | Focused delta |
| :--- | :--- | :--- |
| `M4B-NORM-001` | catalog, fixture, `N07` | Separates codepoint rejection from measured 33-token rejection; adds `MEASURED → DISCARDING → TICKET_DISCARDED` and R1 publication barrier. |
| `M4B-ADM-001` | title/catalog/fixture, `A01`, `A05`–`A13` | Corrects MEASURE scratch semantics; removes unauthorized `superseded`; adds explicit request/terminal identity, three proofs, scrub/token-count/non-mutation, parent/child object lifetimes, permanent invalidation, same-Conversation reuse, repeated disposal, failure matrix, CLOSE-from-MEASURED and public-schema non-expansion. |
| `M4B-OUTCOME-001` | catalog, `O01`, `O12` | Makes token-limit R1 wait for exact acknowledged disposal and makes disposal failure E1 with zero normal Fact/action. |
| `M4B-WIRE-001` | catalog, `W03`, `W05`–`W06`, `W08`, `W10`–`W12` | Adds protocol §§4.4/4.7 states, exact disposal wire/proofs, uncancellable/non-reentrant DISCARDING, interrupt race, failure cleanup and MEASURED close behavior. |
| `M4B-PRIV-001` | catalog/fixture, `V07`–`V09` | Adds rejected-text lifetime probes, fixed scrub/ledger restrictions and success/failure cleanup/redaction. |
| Traceability/references | catalog and §6 groups 4/9/10 | Moves S2 references to protocol §§4.5/4.7 and maps disposal, DISCARDING and lifetime cleanup without changing Test-ID ranges. |

### Requirement-to-case mapping

| Request item | Covering cases |
| :--- | :--- |
| 1. codepoint-valid 33-token MEASURE; ACK before R1 | `N07`, `A07`–`A08`, `O01`, `O12`, `W10` |
| 2. unchanged Conversation identity/state; zero send/mutation; exact object lifetimes | `N07`, `A01`, `A07`–`A08`, `V07`–`V08` |
| 3. permanent invalidation; new MEASURE/GENERATE on same Conversation | `A05`, `A09`, `W10` |
| 4. repeated reject/dispose then successful short turn | `A10` |
| 5. exact identities and all three proof booleans | `A07`–`A08`, `W10`–`W11` |
| 6. fixed scrub, native scratch replacement, unchanged token count, no send/clear | `A07`, `A11`, `W10`–`W11`, `V08` |
| 7. stale/mismatch/duplicate, proof/terminal/scrub failure, timeout/EOF → E1/PGID proof | `A11`–`A12`, `O12`, `W11`, `V09` |
| 8. DISCARDING has no CANCEL/reentry; interrupt race waits or converges by E1 | `W05`, `W12` |
| 9. CLOSE from MEASURED destroys ticket/scratch with cleanup proof | `A06`, `W06` |
| Preserved private-only boundary; no public SM/Event/Fact/response expansion | `A13` |

### Focused conformance disposition

- `A05` no longer contains `superseded`; only explicit discard or GENERATE consumption can resolve a ticket.
- Protocol references after the new §4.4 insertion are aligned: S2/terminal behavior uses §§4.5/4.7 and the
  disposal/state matrix uses §§4.3–4.7.
- Every async ordering assertion uses named MEASURED/DISCARDING/scrub/terminal/R1/interrupt/PGID barriers;
  no correctness sleep or implicit next-MEASURE supersession remains.
- The scrub text is fixed to non-private `__M4B_TICKET_SCRUB__`; no runtime clear API, GENERATE/native send,
  public SM state, Event, Fact or `LLMResponse` was added.
- Blocking coverage gaps found: **none**.

Disposition: **Revised; next owner Designer for focused mapping confirmation.** Only Designer may resolve this
review and reopen the affected `CR_M4B_II` WP-02/WP-03 path.

## Designer mapping confirmation — Resolved (2026-09-12)

Designer independently checked the focused specification against revised product §§5.1–5.2, 7, 8 and 11 plus
protocol §§4.3–4.7. All 9/9 requested requirements have explicit deterministic cases and failure barriers:

- `N07`, `A07`–`A08`, `O01`/`O12` gate 33-token R1 on the exact disposal terminal;
- `A05`–`A12` cover permanent invalidation, same-Conversation continuation, repeated disposal, exact identity,
  three proofs, native scrub/count invariants and all required E1 paths;
- `W05`–`W06`, `W10`–`W12` cover uncancellable/non-reentrant DISCARDING, interrupt race, CLOSE and PGID cleanup;
- `V07`–`V09` cover the permitted native-scratch interval, parent/child object lifetimes and redaction;
- `A13` proves the private-only boundary without public SM/Event/Fact/`LLMResponse` expansion.

All 13 existing portable Test IDs and all unrelated assertions remain present. `A05` no longer names unauthorized
supersession, protocol section references are aligned, and no execution/PASS claim was introduced. Blocking
coverage gaps: **none**. This review is Resolved; the affected `CR_M4B_II` WP-02/WP-03 path is open to Developer.
