# Current design status

- Owner: Designer
- Scope: ALPHA Voice-only product convergence
- State: **Design complete；Test Spec entry open**
- Next owner: Tester
- Developer entry: **Closed pending `test_spec_ALPHA.md`**

## Accepted input

- M4／M4C is Accepted on the formal Voice-only product path. ALPHA does not reopen its subsystem matrix or
  accepted evidence.
- [`ALPHA.md`](../milestones/ALPHA.md) is the current authority. USER fixed the product questions, run split,
  quality rubric and exclusions on 2026-09-26.
- No architecture change or external POC is required for Test Spec entry.

## Fixed ALPHA design

| Authority | Fixed scope |
| :--- | :--- |
| `ALPHA-L01-LIFECYCLE` | One offline Pi run: startup, three Sessions × two Turns, per-Session cleanup, shutdown, owner absence, restart to `IDLE`, and one aggregate privacy scan |
| `ALPHA-P01-PERFORMANCE` | One separate controlled Pi run with P01–P05 startup／first-turn／follow-up／warm-session／streaming measurements; no numeric acceptance threshold |
| `ALPHA-R01-LLM-RECOVERY` | One actual LLM-child streaming failure, product convergence, one replacement, one subsequent normal Session and final owner absence |
| `ALPHA-Q-RUN-01-QUALITY` | Six fixed cases, one attempt each; automatic path verdict plus Codex semantic verdict, with only unresolved ambiguity routed to USER |

Performance baseline is mandatory; a code optimization is not. Only a clear, attributable product bottleneck may
create one bounded improvement work item, followed by the same before／after measurement and directly affected
regression.

## Explicit exclusions

- No 20-session or two-hour soak, long-term-stability claim, resource／thermal／memory research, performance
  ceiling, manifest／checksum revalidation or separate offline／privacy Test ID.
- No complete ASR／LLM／TTS／Audio fault matrix, abnormal-shutdown matrix, POC-trigger review, extra sign-off,
  generic close-proof or repeated administrative evidence.
- Cleanup assertions remain only where they prove Session, recovery or shutdown behavior.

## Tester handoff

Tester creates `docs/test_spec/test_spec_ALPHA.md` and maps exactly the four authorities above. Fixtures may be
frozen in the Test Spec, but coverage must not add excluded scope. Developer remains closed until the Test Spec
provides executable IDs, steps, outcome criteria and the single `NEEDS_USER_DECISION` route for semantic ambiguity.
