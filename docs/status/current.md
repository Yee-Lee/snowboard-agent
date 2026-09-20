# Current handoff

- Updated: 2026-09-20
- Writer: Designer only
- Current milestone: M4-ERR Developer convergence and same-bytes Pi Verify
- Current stage: **M4-ERR Design／Test Spec aligned；`IR_dev_M4_ERR_II` Resolved；Developer entry open**
- Next owner: Developer
- Developer entry: **M4-ERR Open；commit requires all applicable tests and same-bytes Pi Verify；M4C Closed**

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

USER subsequently inserted M4-ERR between Accepted M4A／M4B and M4C implementation. M4C product-scenario
design may continue, but M4C must not enter Test Spec or development until M4-ERR has completed its own
`Design → Test Spec → Developer → Verify`. M4-ERR closes the generic and M4-production error taxonomy,
diagnostics, backend-usability, recovery and fatal-exit behavior; M4C then verifies representative
whole-product scenarios without repeating every component-level fault cause.

M4C-SS is a separate USER-defined M4C design gate. Before M4C Test Spec, Designer must consume the bounded
streaming-speak POC evidence and close the gate with exactly one disposition: adopt true streaming B, or
evidence-backed abandonment to full-response A. The gate does not add a role-signoff stage and POC self-PASS
does not close it. M4C has no barge-in; VAD remains the M4A baseline with M4C product-quality observation.
Repeated sessions, soak and formal performance/resource thresholds remain ALPHA scope.

M4C-SS was delivered byte-identically on 2026-09-19 to the sibling `poc_llm` worktree at
`docs/pm_handoff/REQUEST-LLM-POC-M4C-STREAMING-SPEAK-001.md`, after fetching and fast-forwarding its clean `llm`
branch to `origin/llm` baseline `5080abd84dafcbc0f8307a086fa8009a0b6a818b`. The committed Core source and
delivered destination both had SHA-256 `234b5998589d3c956005f465862e137b471a2e26e75c3a19c6be5cb166c0b59c`.
The incoming file is intentionally uncommitted pending LLM POC intake. POC execution, Pi access, reboot, network
change, artifact download, commit and push remain unauthorized. M4-ERR Design is complete and its Test Spec work
does not depend on the M4C-SS result.

## Role routing now

| Role | Action now |
| :--- | :--- |
| Designer | `IR_dev_M4_ERR_II` Resolved；consume the LLM POC intake/result later for M4C-SS |
| Tester | PI-012 prefix correction accepted；wait for Developer candidate and Verify；do not start M4C Test Spec |
| Developer | Complete PI-012, all affected regressions and remaining WP7；then run full `M4-ERR-PV-001`–`M4-ERR-PV-005` in one same-bytes M4-ERR Pi Verify run before any commit |
| Architect / Reviewer | No active request; enter only if an active design exposes a focused conflict or review need |

Designer only replaces this file when the stage, gate, entry state or next owner changes.
