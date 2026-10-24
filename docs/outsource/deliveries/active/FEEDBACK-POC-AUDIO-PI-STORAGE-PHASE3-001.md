# FEEDBACK-POC-AUDIO-PI-STORAGE-PHASE3-001

- Date: 2026-09-06
- From: Core review
- To: Audio POC Team
- Request: `REQUEST-POC-AUDIO-PI-STORAGE-PHASE3-001`
- Status: `BLOCKING — REVISE AND RETURN`

## Findings

1. **Blocking — incoming request is not an exact delivery.** The Audio copy is a
   summary with a changed status and omits required work, limits, and acceptance.
   Restore the exact Core request as read-only incoming material; record team status
   in a separate ACK or response.
2. **Blocking — product verification trusts self-description.** A marker's declared
   manifest digest is not proof. Read and hash the actual product manifest, verify
   runtime/native inventory and the bytes, sizes, and read-only state of every
   formal dependency. Reject symlink components. Also reject any ancestor/descendant
   nesting among run, evidence, cache, and product roots.
3. **Blocking — formal execution still depends on installer inputs.** Formal TTS and
   runtime startup still require candidate source archives and wheels. Reacquirable
   archives/wheels may be installer or qualification inputs but cannot remain formal
   runtime dependencies. Formal execution must bind only the complete verified M4A
   product inventory.
4. **Blocking — operational entry points are incomplete.** Update the qualification
   shell entry point and README invocations with the required product-root argument
   and the correct product model layout.
5. **Blocking — return packet is incomplete.** Add the exact changed-file list,
   commands and results actually run, and the complete workflow-compliant commit
   title, body, and file proposal.
6. **Blocking — tests do not cover the requested risks.** Add meaningful coverage
   for concurrent reuse of the same read-only product, retained-evidence separation,
   runtime/native inventory mismatch, nested roots, symlink components, and
   read-only product dependencies.
7. **Blocking — cache semantics contradict the contract.** Remove statements that
   create formal expansions in cache. A formal expansion belongs to the verified
   product root; cache is reacquirable and never a formal dependency.

## Required return

Return a reconciled exact request/ACK, corrected source and operating instructions,
the complete verify-only migration manifest, affected and regression test results,
bounded Pi workspace preflight, Git privacy/whitespace checks, and the full commit
proposal. Model/runtime copying, benchmark execution, service activation, hold
movement, cleanup, commit, and push remain unauthorized.
