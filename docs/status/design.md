# Current design status

- Owner: Designer
- Scope: M4B MVA adoption
- State: blocked on external efficiency result and affected review

## Current authority

- Milestone gate: `docs/milestones/M4B_MVA.md`
- Product design: `docs/implement/ch_m4b_llm_production.md`
- Pending adoption delta: `docs/implement/m4b_mva_002_decisions.md`
- Architecture reviews: `docs/reviews/AR_impl_M4B_II.md`, `docs/reviews/AR_review_M4B_I.md`
- Developer escalation: `docs/reviews/IR_dev_M4B_III.md`
- Tester handoff: `docs/reviews/TR_spec_M4B_IV.md`

## Next Designer work

After the efficiency report arrives, adopt exactly one encoding/readiness/profile combination, record
the report full SHA and affected architecture/design sections, then activate the focused reviews. Do not
reopen Accepted M4A, POC winner selection, target ABI, license or immutable machine results.

When all affected reviews and coverage sign-off close, update `current.md` and authorize a concrete
Developer work package. Do not append old review transcripts or prior milestone chronology here.
