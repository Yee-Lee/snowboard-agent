# Current handoff

- Updated: 2026-09-21
- Writer: Designer only
- Current milestone: M4C complete offline voice-device integration
- Current stage: **M4-ERR Accepted；M4C Design complete；M4C-SS Closed（B2）；Test Spec complete**
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
  negative coverage, speech-quality judgment and same-bytes Pi evidence remain mandatory.
- [`test_spec_M4C.md`](../test_spec/test_spec_M4C.md) now maps the fixed volume, B2 controller／extraction／
  outcome, no-input, regression and nine whole-product scenario contracts. `M4C-S02` absorbs the eligible B2
  normal turn and is automatic; S09 has the fixed quality sample plus three interrupt variants, for 16 exact
  variants total. `TR_spec_M4C_I` remains Resolved with 0 Blocking.

## Developer route

Implement the current M4C design and Test Spec from:

1. [`M4C`](../milestones/M4C.md) as product design authority;
2. [`M4C Test Spec`](../test_spec/test_spec_M4C.md) as the executable Test ID／oracle authority; and
3. accepted M4A／M4B／M4-ERR only through the direct regression and composition boundaries routed by those files.

Implement the single B2 path without reopening the POC or adding an A-mode fallback. Complete all applicable
portable tests, then execute the 16 designated Pi sub-runs on the pending bytes. Pi Verify and one workstation
same-bytes reconciliation must pass before any commit preparation.

## Role routing now

| Role | Action now |
| :--- | :--- |
| Designer | Design and Test Spec alignment complete；answer only focused implementation conflicts |
| Tester | Test Spec complete；retain authority over Test IDs and formal evidence |
| Developer | Implement M4C, run portable coverage and complete same-bytes Pi Verify before commit preparation |
| Architect / Reviewer | No active request；enter only for a focused conflict that the accepted contracts cannot support |

Designer replaces this file only when Test Spec coverage, Developer entry, stage, gate or next owner changes.
