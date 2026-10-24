# Core → Audio POC: ASR Product R1 Feasibility Outcome Contract

- **Delivery ID**: `DELIVERY-AUDIO-POC-ASR-PRODUCT-R1-CONTRACT-001`
- **Status**: `AUTHORIZED FOR POC INTAKE — EXECUTION PLAN OWNED BY AUDIO POC`
- **Date**: 2026-08-31
- **Contract owner**: Core Designer
- **Research owner**: Audio POC Team
- **Product decision owner**: User
- **Product route**: potential `M4a.R1 → M4b.R1 → M4c.R1 → M4.R1 → ALPHA.R1`
- **Current Audio control**: `audio_m4` / `5694ead4ba6be928fdb4dbdf6da7155b214d72bd` /
  `POC-audio-DEL-2026-001-R1`

---

## 1. Contract question

Audio POC Team is authorized to answer one product question:

> Is there clear, reproducible evidence that a new ASR pipeline approach is feasible under the
> product's relevant constraints and worth developing into the `ALPHA.R1` product line?

For this question, an ASR pipeline may include the recognition engine/model together with a
suitable VAD / endpoint strategy and evidence-backed postprocess components such as a second-pass
scorer or rescoring stage. None of these components is mandatory; Audio POC decides whether each
one contributes to a worthwhile R1 approach.

This is an outcome contract, not a prescribed evaluation plan. The contract does not preselect an
architecture, engine, model, runtime, candidate list, experiment sequence, metric, threshold,
runner, internal milestone, schedule, or optimization method.

## 2. Audio POC autonomy

Audio POC Team owns the research plan and may independently:

- select, add, remove, or stop ASR, VAD / endpoint, postprocess, second-pass scorer, rescoring, or
  combined pipeline candidate paths;
- define and revise experiments, fixtures, metrics, thresholds, tools, work packages, and internal
  gates;
- decide how much prior Audio evidence can be reused and what must be rerun;
- stop early when evidence supports a no-go or when additional work is not worthwhile;
- revise its internal plan without requesting a Core contract revision.

Intermediate plan changes, candidate changes, failed experiments, and ordinary technical findings
do not require Core approval. They remain governed by the Audio POC repository's own evidence,
publication-confirmation, privacy, hardware, and immutable-candidate workflow.

A new Core/User decision is required only when the POC requests a different product question, a
new Core-owned interface or behavior, authority outside its already approved environment, or a
material expansion of product responsibility. Such a decision is separate from ordinary research
plan maintenance.

## 3. Final outcome

The final handoff must state exactly one outcome:

| Outcome | Meaning |
| :--- | :--- |
| `SUPPORTED` | Clear evidence shows that the approach is feasible and sufficiently valuable to justify continued Core development toward `ALPHA.R1`. |
| `NOT_SUPPORTED` | Available evidence shows that the approach is infeasible, not sufficiently valuable, or not preferable to the current control. |
| `INCONCLUSIVE` | The evidence cannot reliably answer the contract question. |

Audio POC Team owns the technical recommendation. User retains the product decision. A
`SUPPORTED` handoff does not itself accept `M4a.R1`, create `ALPHA.R1`, modify Core, or select the
M5 baseline. A `NOT_SUPPORTED` or `INCONCLUSIVE` handoff does not alter the existing M4 / ALPHA
route.

## 4. Evidence sufficiency

Audio POC Team decides the exact evaluation method. Its final evidence only needs to be sufficient
for an independent reader to understand and reproduce why the stated outcome follows. The handoff
must therefore identify:

- the evaluated pipeline and immutable ASR, VAD / endpoint, postprocess / rescoring, runtime,
  model/artifact, dependency, license, and configuration identities relevant to the conclusion;
- the committed POC branch and full 40-character delivery SHA;
- the reproducible procedure and sanitized evidence index supporting the conclusion;
- how the result compares with the current Audio control, or why a direct comparison is not a
  valid way to answer the question;
- the observed benefit, cost, product relevance, limitations, failed paths, and residual risks;
- the Core product deltas that would be required if User chooses to continue toward `ALPHA.R1`.

The POC chooses the measurements and decision rules. Core will not retroactively impose a new
candidate matrix or tune the POC method after results are known. Missing identity, unreproducible
evidence, privacy violations, or a conclusion unsupported by the submitted evidence may cause the
final disposition to remain `INCONCLUSIVE`; they do not silently rewrite this contract.

## 5. Stable boundaries

- Research remains in the Audio POC repository and its approved environments. POC commits or
  branch history are not merged into Core product history.
- VAD / endpoint and postprocess / rescoring are optional parts of this R1 pipeline research. Their
  inclusion here does not establish a generic Core postprocess layer or reopen the abandoned
  standalone postprocess note; only the final evidence-backed R1 proposal may recommend a product
  delta.
- Models, binaries, private audio, sensitive transcripts, credentials, endpoints, and large raw
  results must not be committed to Git. The final handoff uses approved sanitized evidence and
  controlled artifact identities.
- The existing M4 / ALPHA line continues independently. This contract neither blocks it nor grants
  the R1 line acceptance credit.
- Core may establish and advance a separate R1 worktree before the original ALPHA is Accepted, but
  POC evidence never substitutes for Core design, product implementation, Tester acceptance, or
  exact-SHA product evidence.
- `ALPHA` and `ALPHA.R1` remain separate candidates. A later explicit baseline-selection decision
  permits exactly one of them to enter M5.

## 6. Handoff flow

```text
Core outcome contract
  → Audio POC committed receipt
    → Audio POC autonomous research and internal plan revisions
      → User-confirmed final POC report
        → committed final evidence handoff: SUPPORTED / NOT_SUPPORTED / INCONCLUSIVE
          → Core evidence intake
            → User product decision for ALPHA.R1 and the eventual M5 baseline
```

No recurring Core plan ACK is required. Core's final intake checks whether the evidence supports
the submitted outcome and respects the stable boundaries; it does not reopen ordinary POC method
choices. Any additional research after the final disposition requires an explicit User decision,
not an implicit extension of this contract.

---

This delivery authorizes Audio POC intake and autonomous planning. It does not authorize a Core
merge, a product baseline change, an `ALPHA.R1` acceptance claim, a commit or push by the delivering
Designer in the Audio repository, or concurrent entry of both ALPHA candidates into M5.
