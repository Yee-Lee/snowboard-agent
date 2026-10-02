# Current design status

- Owner: Designer
- Scope: ALPHA Voice-only product convergence
- State: **Design and Test Spec correction complete；Developer entry open**
- Next owner: Developer
- Developer entry: **Open — resume the bounded ALPHA runner work package**

## Accepted input

- M4／M4C is Accepted on the formal Voice-only product path. ALPHA does not reopen its subsystem matrix or
  accepted evidence.
- [`ALPHA.md`](../milestones/ALPHA.md) is the current authority. USER fixed the product questions, run split,
  quality rubric and exclusions on 2026-09-26.
- No architecture change or external POC is required for Test Spec entry.
- `IR_dev_ALPHA_I` reproduced and resolved two executable-contract conflicts. The accepted product behavior remains unchanged:
  one Button starts a Session and Turn 2 follows `KEEP_NEXT`; the 20-codepoint／32-token admission limit remains.

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

The focused 2026-10-02 correction fixes the shared P05／Recovery stimulus as
「用三句短話介紹滑雪注意事項。」 and Q04 as 「用一句話說初學滑雪為何要戴安全帽。」. Both retain the approved
semantic intent while providing an eligible production-LLM path without changing admission behavior.

## Explicit exclusions

- No 20-session or two-hour soak, long-term-stability claim, resource／thermal／memory research, performance
  ceiling, manifest／checksum revalidation or separate offline／privacy Test ID.
- No complete ASR／LLM／TTS／Audio fault matrix, abnormal-shutdown matrix, POC-trigger review, extra sign-off,
  generic close-proof or repeated administrative evidence.
- Cleanup assertions remain only where they prove Session, recovery or shutdown behavior.

## Developer handoff

The existing `test_spec_ALPHA.md` now requires exactly three Session-start Buttons and six voice turns, uses the
two corrected exact stimuli, and retains real ASR／LLM admission, the existing rubrics and all four run boundaries.
`IR_dev_ALPHA_I` is Resolved with no open findings. Developer resumes only the existing bounded ALPHA runner work
package; no new Test ID, rerun matrix, product-source workaround or review gate is authorized.
