---
requestor: Developer
owner: Designer
status: Resolved
---

# IR_dev_ALPHA_I — Executable ALPHA stimulus contract

Date: 2026-10-02. Scope: only the two stimulus/admission issues below. Accepted M4 behavior and
evidence remain unchanged. Designer coordinates the Test Spec correction with Tester; this is an
authority conflict, not an additional review/sign-off gate.

## Blocking ALPHA-DEV-01 — A Button on every turn interrupts the intended Session

- Basis/location: `test_spec_ALPHA.md` §3.2 requires, for all six turns, “exactly one Button stimulus
  is admitted to the intended current Session”. Its §3.1 and `ALPHA.md` §3.2 describe a new Button
  only for Turn 1. `docs/implement/ch04_state_manager.md` event handling and ACTION `KEEP_NEXT`
  preserve the Conversation and automatically enter the next PERCEPTION; a Button outside
  IDLE/ERROR requests interruption.
- Expected: three Sessions, each completing two ASR/LLM turns and normal end in the same Conversation.
  Actual: `src/sbd/core/state_manager/manager.py` handles the second Button with
  `_begin_convergence("interrupt")`; it cannot admit that Button as a new turn in the current Session.
- Reproduction: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_m4c_s02_tryrun.py
  tests/test_m4c_s04_tryrun.py` passes. S02 executes the real State Manager's two-turn KEEP_NEXT/END_SESSION
  path from one Button. S04 proves a second Button interrupts PERCEPTION, THINK and ACTION and produces
  no subsequent successful affected operation.
- Impact: a faithful lifecycle driver fails before the required normal second turn. Changing Button
  semantics would reopen Accepted behavior and expand ALPHA product scope.
- Preferred correction: replace the §3.2 per-turn Button bullet with:
  “Exactly one new Button stimulus starts each Session. Each of its two fixed PCM stimuli is consumed
  once by the intended current turn through real ASR and LLM; Turn 2 follows the existing KEEP_NEXT
  transition without another Button.”
- Minimum acceptance: the Test Spec consistently requires three Session-start Buttons and six voice
  turns; no extra product Event/state mutation or Button semantics change is needed.

## Blocking ALPHA-DEV-02 — Two fixed texts can select input-limit speech instead of LLM

- Basis/location: `test_spec_ALPHA.md` §2.2 fixes `FX-MULTI-FRAGMENT`; §§4–5 require its real safe LLM
  fragments. §6.2 fixes `FX-Q04` and requires a relevant one-sentence answer through real LLM.
  `docs/implement/ch_m4b_llm_production.md` §3.2 preserves punctuation during normalization and
  rejects more than 20 normalized code points with application-owned R1 speech, without inference.
- Reproduction: use `ListenProjector.project` and the real `Reasoner` through
  `tests.test_m4b_outcome_001.run/ProductLLM/fact` with the exact specified stimuli. The resulting
  observations are:

  | Fixture | Normalized code points | MEASURE calls | GENERATE calls | Input-limit reply |
  | :--- | ---: | ---: | ---: | :--- |
  | FX-MULTI-FRAGMENT | 21 | 0 | 0 | true |
  | FX-Q04 | 21 | 0 | 0 | true |
  | FX-Q06-T1 (control) | 20 | 1 | 1 | false |

- The diagnostic exercises product admission with exact text, not production Pi ASR. Both affected
  stimuli have 20 spoken characters plus punctuation; an ASR result without punctuation may be
  eligible. Eligibility therefore cannot be inferred from the spoken question alone, and a runner
  must not remove decoded punctuation, bypass admission or accept R1 as an LLM result.
- Impact: a faithful punctuated ASR result prevents P05 characterization, prevents Recovery's required
  injection point, and makes Q04 fail relevance. The fixture contract currently offers no predetermined
  resolution; substituting a question after seeing an answer is explicitly prohibited.
- Preferred correction: Designer/Tester fix shorter stimuli before any valid execution, retaining the
  same semantic intent and rubric. Suggested text: FX-MULTI-FRAGMENT “用三句短話介紹滑雪注意事項。”;
  FX-Q04 “用一句話說初學滑雪為何要戴安全帽。” Update both design and Test Spec wherever exact stimuli
  are specified, then resolve the fixed local PCM binding before runs. Real ASR and token admission
  remain required. Alternatively explicitly establish that the fixed original PCM's real ASR result
  is eligible before the once-only valid run; no transcript injection or per-run text rewrite.
- Minimum acceptance: the fixed fixture mapping has an eligible real-ASR path to production LLM for
  these cases; the 20-codepoint/32-token contract stays intact. Do not silently switch to ALPHA.R1.

## Developer disposition

The combined focused regression command including `tests/test_m4b_outcome_001.py` exited 0 on the
workstation. No product source, ALPHA runner or authority was changed; no ALPHA/Pi Pass is claimed.
The concrete bounded work package is in `docs/status/development.md`. Developer resumes after these
contract corrections; no other gate is requested.

## Designer response — 2026-10-02

Both Blocking findings are accepted as executable-contract defects; neither authorizes a product-source change.

- `ALPHA-DEV-01`: `ALPHA.md` §3.2 now makes the existing behavior explicit: one Button starts each Session and
  Turn 2 enters through `KEEP_NEXT` without another Button. Tester must align §3.2 of the Test Spec so the result
  is three Session-start Buttons and six real ASR／LLM turns.
- `ALPHA-DEV-02`: the authority adopts the shorter exact stimuli
  `用三句短話介紹滑雪注意事項。` for shared P05／Recovery and
  `用一句話說初學滑雪為何要戴安全帽。` for Q04. Their semantic intent and rubrics are unchanged. Real ASR and
  production admission remain mandatory; punctuation removal, admission bypass and input-limit R1 credit remain
  forbidden.
- Focused workstation diagnosis through the same `ListenProjector`／`Reasoner` harness records 14 and 17
  normalized code points respectively; each produces one MEASURE, one GENERATE, one response and zero errors.
  This confirms the authority correction's admission path but is not Pi or ALPHA acceptance evidence.

At this response the status moved to `Revised`, not `Resolved`, until Tester applied the three focused Test Spec
corrections. Developer entry remained closed during that correction; no additional review or sign-off was
introduced.

## Resolution — 2026-10-02

Tester applied the complete focused delta to `test_spec_ALPHA.md`:

- Lifecycle now requires exactly three Session-start Buttons and six voice turns, with every Turn 2 entering via
  `KEEP_NEXT` without another Button.
- `FX-MULTI-FRAGMENT` and `FX-Q04` now exactly match the corrected authority stimuli, while real ASR／LLM
  admission, the existing semantic rubrics and all four run boundaries remain unchanged.
- No stale original stimulus or per-turn Button wording remains.

The focused State Manager／Reasoner regression command exited 0, both corrected stimuli independently exercised
one MEASURE and one GENERATE with zero errors, and `git diff --check` passed. This is sufficient contract coverage;
it is not ALPHA or Pi acceptance. Both Blocking findings are closed, open findings are zero, and Developer may
resume the existing bounded ALPHA work package. Disposition: `Resolved`.
