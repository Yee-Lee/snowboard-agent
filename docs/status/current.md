# Current handoff

- Updated: 2026-09-26
- Writer: Designer only
- Current milestone: M4C complete offline voice-device integration
- Current stage: **M4 Accepted；M4C formal Pi PV 7/7 Pass**
- Next owner: Designer
- Developer entry: **M4C Closed**

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
- Candidate `0b2160e5d48dcc959b08f4a23ede91a9e0d5640d` completed formal Raspberry Pi run
  `M4C-FORMAL-PV-20260926-01`. All seven catalog entries are designated Pass; the finalizer reports
  `pv_status=Pass` with one earlier S02 timeout retained as a superseded attempt. The Pi checkout remained
  clean and its tracked-content SHA-256 matched the workstation value
  `d5d94f7c539c3f8de276f3974876074ac43bae810bb1cdab08bf9b9bd93a3502`.

## Acceptance disposition

M4C and its parent M4 milestone are Accepted. Preserve the fixed B2 path, seven-entry catalog and formal
evidence; do not reopen completed scenarios merely to add administrative checks. ALPHA is a separate product
convergence gate and begins only as its own routed task.

## Role routing now

| Role | Action now |
| :--- | :--- |
| Designer | M4C acceptance recorded；route the next explicitly selected milestone or gate |
| Tester | M4C formal evidence complete；no active M4C work |
| Developer | M4C closed；enter only for a concrete regression or newly routed milestone |
| Architect / Reviewer | No active request；enter only for a focused conflict that the accepted contracts cannot support |

Designer replaces this file only when Test Spec coverage, Developer entry, stage, gate or next owner changes.
