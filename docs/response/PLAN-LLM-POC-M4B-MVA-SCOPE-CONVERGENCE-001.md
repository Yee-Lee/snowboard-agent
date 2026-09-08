# PLAN-LLM-POC-M4B-MVA-SCOPE-CONVERGENCE-001

- Date: 2026-09-08
- Trigger: User scope convergence after bounded Pi engineering discovery
- Work / gates: `M4B-MVA` / `M4B-MVA-POC` / `M4B-MVA-EFFICIENCY`
- Status: `PLAN FREEZE CANDIDATE / IMPLEMENTATION NOT STARTED`

## Delivery contribution

This plan closes the smallest remaining path to a Core-reviewable encoding/readiness answer. It adds
only the minimum Reasoner reference and prompt proposal needed to make the model-facing input surface
truthful and measurable. It does not expand the original experiment, implement the production
Reasoner, add product capabilities, or claim formal Pi evidence from prior engineering runs.

## User decisions and fixed terminology

- Do not extend the original experiment. Stop work on `S3`, `S4`, broad prompt search and additional
  prewarm variants. Reuse already-confirmed engineering observations instead of repeating them.
- The POC Reasoner may provide an executable reference architecture, while Core retains production
  Reasoner policy and adoption authority.
- Implement and test only the current `listen` path. Preserve an explicit projector boundary for
  future `read`, `look` and other perceptions, but do not implement or test those capabilities now.
- Current fast voice input is at most 20 Unicode codepoints. Trusted personality and other settings
  have a separate combined limit of 20 Unicode codepoints. Exact tokenizer and KV checks still apply.
- `128` runtime prefill tokens is a measured performance boundary, not an admission failure. The
  current `1024` KV capacity remains the hard runtime boundary.
- `V1` means the current 113-token prompt. `V2` is the minimal-core proposal family. `V2.1` is the
  rejected 37-token candidate; `V2.2` is the 56-token candidate; `V2.2P` adds the rejected nine-token
  personality phrase.

## Bounded work plan

### C1 — Close engineering discovery without expansion

Produce one sanitized decision table from existing observations only:

- J exact constrained JSON remains the control baseline.
- P constraint/parser feasibility and its explicit-end model-intent regression remain separate facts.
- S2 constrained-J incremental extraction is the only fallback proposal retained for Core review.
- D/H request-path, holding-memory and lifecycle observations are retained; only the missing matched D
  post-request memory comparison remains eligible for development measurement.
- The `128/129` prefill step, absent clean prefix-KV API, question-length observations and failed prompt
  candidates are supplemental design information, not added formal experiment arms.

Stop condition: no new encoding, schema, prewarm or question-length candidate is introduced.

### C2 — Minimum viable Reasoner reference

Implement a repository-isolated Reasoner reference with this boundary:

1. Accept validated `SessionFacts` and one current `TurnInput` collection.
2. Select exactly one non-empty, `ok` `listen` perception for the current implementation.
3. Reject unsupported/multiple active perceptions with a typed result; expose a projector interface so
   later stages can add other perception types without changing the LLM backend contract.
4. Remove the product envelope before model invocation and emit one normalized model-facing listen text.
5. Enforce the 20-codepoint voice limit, retain the current 32-token single-listen safety check only for
   this bounded path, and apply the complete
   incremental/KV/output-reserve admission check. Crossing 128 records a performance tier only.
6. Accept only `SemanticGeneration(text,end)`, validate the relation, and deterministically project to
   current `speak/listen` or `rest`. Model chunks never dispatch tools or next perceptions.

Workstation tests cover valid listen, empty/failed listen, multiple listen, unsupported kind, codepoint
and token rejection, KV overflow, semantic fallback, explicit/negative end and session isolation. They
do not simulate future `read`, `look` or tool behavior.

Stop condition: the current listen path is executable, deterministic and covered; extension points exist
but no future capability is implemented.

### C3 — Qualified prompt proposal

Use the fixed Reasoner projection so rendered-input composition is measurable. Compare `V1` with at most
two new V2 candidates. A candidate must retain identity, zh-TW, concise/basic-correct behavior, explicit
current capability limits, explicit/negative end semantics and a bounded trusted personality setting.
Protocol, envelope parsing, session isolation, tool dispatch and JSON shape stay in software.

Use a one-pass public listen screening first. Only a candidate that passes structure, end and capability
checks receives three engineering confirmation repetitions and a short/20-codepoint timing pair on Pi.
Record system, setting, projected-user, rendered, runtime-prefill, output and KV token counts; first
decodable text, first safe chunk and terminal time remain separate. Report whether the candidate stays
below or crosses 128, but never reject it for crossing.

Stop condition: stop at the first candidate that passes all public functional checks and shows a stable,
useful latency profile with explicit token headroom. If both candidates fail, return the failures without
adding a third tuning round.

### C4 — Core revision request and original experiment completion

Submit a single User-reviewed proposal to Core containing:

- the original encoding answer and retained J/S2 recommendation;
- the original readiness answer, with the bounded matched D/H evidence still required;
- the minimum Reasoner listen projection and qualified prompt candidate;
- a compact supplemental section for the prefill boundary, cache limitation, input-length behavior,
  prompt failures and memory cost.

Core must freeze any changed formal candidate, prompt, Reasoner projection, case count and selection rule.
Only then complete the affected formal A/B measurements from a clean checkout of the pushed SHA. Do not
rerun unaffected findings or treat engineering artifacts as formal evidence.

## Workstation and Pi split

- Workstation: contract/types, Reasoner tests, evidence schema, plan reconciliation, review, commit/push.
- Pi POC workspace: selected tokenizer counts, real prompt behavior, LiteRT rendered/prefill metrics,
  missing bounded D comparison, target debugging and cleanup verification.
- Pi never commits. Reconcile the reviewed non-sensitive diff on the workstation and commit/push only at
  a milestone under the repository policy. Formal results require a later clean checkout of that SHA.

## Exclusions

- No Audio E2E run or three-second audible claim.
- No implementation of `read`, `look`, tool execution or production composition.
- No `S3` compact schema, `S4` unconstrained encoding, fake-turn prewarm or further model selection.
- No publication of benchmark results or candidate recommendation before User review.
