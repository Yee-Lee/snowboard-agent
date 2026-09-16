# Current handoff

- Updated: 2026-09-16
- Writer: Designer only
- Current milestone: M4C
- Current stage: **Design entry open**
- Next owner: Designer
- Developer entry: **Closed until M4C design and Test Spec are complete**

## M4B completion disposition

USER accepted M4B as complete on 2026-09-16. The same-bytes Raspberry Pi 5 product verification
`PV-M4B-FINITE-03` passed all seven Test IDs, including six applicable Developer reviews and the
three USER semantic verdicts. The verified protected-content, harness and profile digests are:

- `f6b9cfe2dcadeac675deb4811b2711e9c0c6a28d73e4985fc9ae321fb08c7545`
- `cb79a96c06cdf427142fd9171523ce545e2b35951c59117d9d1dc8cf95988b33`
- `8d957a4600fc172fd7dd7b285098710af0b753d7d1b697a21bd31611637b3f90`

The verified bytes were committed as
`f87cfa50b9c9415430973076a59c6b1961228090` (`feat[M4B]: complete constrained-JSON product
verification`) and pushed to `origin/core`; local `HEAD` and `origin/core` matched that SHA when
the completion transition was recorded. M4B is Accepted and read-only unless a named regression
or focused post-acceptance delta explicitly reopens it.

The accepted claim does not include physical wake/display hardware, native context exhaustion,
R06 nested-descendant killing or R07 full-product shutdown. The measured 558/699 MiB values remain
finite-session estimates rather than adopted release thresholds. These declared boundaries do not
block M4B acceptance or M4C design entry. Any later threshold adoption is a separate normal-pipeline
delta.

## M4C entry

M4C's four prerequisites are satisfied: the Reasoner behavior gate is closed; replacement design,
protocol/profile and Test Spec coverage are complete; reusable Audio+LLM resource/timing evidence
exists; and the product candidate is verified, committed and aligned with Accepted M4A.

Designer may now start M4C design from:

1. [`M4C`](../milestones/M4C.md) for scope and entry boundaries;
2. [`M4A Audio production`](../implement/ch_m4a_audio_production.md) §§1, 7, 10 and 12 for the
   accepted audio composition surface;
3. [`M4B LLM / Reasoner product`](../implement/ch_m4b_llm_production.md) §§1, 5–7, 9–10 and 11.2 for
   the accepted cognition, lifecycle, resource and timing inputs.

Do not open Developer entry until the resulting M4C design has gone through Test Spec coverage.
Do not infer new response-time ceilings, resource thresholds, streaming behavior or soak counts
from M4B observations; M4C must define those only where its own product requirements need them.

## Role routing now

| Role | Action now |
| :--- | :--- |
| Designer | Begin the M4C design delta from the routed sections above |
| Tester | Wait for the M4C design handoff before authoring Test Spec |
| Developer | Closed; no M4C product changes yet |
| Architect / Reviewer | No active request; enter only if M4C design exposes a focused conflict or review need |

Designer only replaces this file when the stage, gate, entry state or next owner changes.
