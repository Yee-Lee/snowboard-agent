# Current handoff

- Updated: 2026-09-26
- Writer: Designer only
- Current milestone: M4C complete offline voice-device integration
- Current stage: **M4-ERR Accepted；M4C Design／Test Spec streamlined；Developer final alignment**
- Next owner: Developer
- Developer entry: **M4C Open**

## Gate transition facts

- M4-ERR final run `M4-ERR-DEV-04` passed `M4-ERR-PV-001`–`M4-ERR-PV-005`, 1,715 applicable
  non-RPi regressions and same-bytes digest reconciliation. The verified content was committed and pushed as
  `f572915d0b0d5c52067e9100c5b022e57aefe506`; M4-ERR is Accepted and its taxonomy／recovery behavior is now
  the M4C input rather than an open implementation slice.
- LLM POC returned `DELIVERY-LLM-POC-M4C-STREAMING-SPEAK-001` from implementation／review source
  `a6de0e66d7effe03549037eb8f50b99e42399620`, bound by pushed commit
  `a492a1416721c73c989dd46067b3e9dd1c24508d`. The byte-identical Core copy has SHA-256
  `c097d550d263070ef216bfa391e87c69b6b27aa68baf26f09ea7428be8bf069f`.
- Designer closes `M4C-SS` by adopting true streaming `B2-ONE-LOOKAHEAD-COALESCE` with a
  punctuation-or-12-normalized-codepoint S2 boundary. Existing public TTS／Audio／Fact contracts remain
  unchanged, so no architecture request is needed.
- The POC executed 0 of its 82 formal cases and used a dirty Pi development checkout; its engineering
  observations select the design but provide no M4C Test ID PASS credit. Core exact-product qualification,
  negative coverage and same-bytes Pi verification remain in the normal M4C pipeline; the necessary audible
  observation is part of S02 rather than a separate gate.
- [`test_spec_M4C.md`](../test_spec/test_spec_M4C.md) maps fixed volume, B2 controller／extraction／outcome,
  no-input, Display isolation and directly affected regressions. The Pi catalog is S01–S05 only: five Test
  IDs and seven sub-runs. S06/S07 are portable integration; S08 adds no test; S09 is traced to S02,
  C14/C15 and S04/ACTION. No independent S09 human result remains.

## Developer route

Implement the current M4C design and Test Spec from:

1. [`M4C`](../milestones/M4C.md) as product design authority;
2. [`M4C Test Spec`](../test_spec/test_spec_M4C.md) as the executable Test ID／oracle authority; and
3. accepted M4A／M4B／M4-ERR only through the direct regression and composition boundaries routed by those files.

Keep the single B2 path without reopening the POC or adding an A-mode fallback. Align the runner to the
seven-entry Pi catalog, retain the completed S06/S07 integration coverage, and run every test applicable to
the final pending bytes on Pi. A content comparison is performed once only when transfer/candidate preparation
actually requires it; it is not a per-run Test ID.

## Role routing now

| Role | Action now |
| :--- | :--- |
| Designer | Streamlined Design authority complete；answer only focused implementation conflicts |
| Tester | Streamlined Test Spec complete；Verify against its Test IDs and catalog |
| Developer | Align runner to seven entries and keep the verified S06/S07 implementation unchanged |
| Architect / Reviewer | No active request；enter only for a focused conflict that the accepted contracts cannot support |

Designer replaces this file only when Test Spec coverage, Developer entry, stage, gate or next owner changes.
