# DELIVERY — LLM POC M4B Gate 2B Winner Handoff 001

- **Date**: 2026-08-29
- **From**: LLM POC Team / User-authorized relay
- **To**: Core Designer
- **Status**: `ACTIVE — FINAL WINNER ACK REQUESTED`
- **Source repository / branch**: `poc_llm/snowboard-agent` / `llm`
- **Closure content commit**: `5ffdd9eaa3beb9ca09ff6a63839e02248c9a78ae`
- **Provenance addendum commit**: `485bb2a7c07d86a09899f09358c744edd733f875`
- **Winner**: `CAND-LRT-G4E2B-MOBILE-R1` / Gemma 4 E2B mobile

## Purpose and authority boundary

This envelope supplies the immutable publication locator requested by Core's single blocking
finding. It does not rerun or rewrite Attempt 006. Intake of this package does not pre-author Core
acceptance, product model/runtime lock, implementation completion or Gate 3 PASS. The machine
`P9=FAIL` and `P10B=FAIL` results remain immutable; the User-approved known-runtime-defect waiver is
the governance basis for selecting Gemma as the POC winner.

## Immutable enclosure map

| Enclosure | Location in this Core checkout | SHA-256 |
| --- | --- | --- |
| `DELIVERY-019-PM-LLM-POC-P2-P3-P8-SEMANTICS-ADJUSTMENT.md` | `docs/outsource/pm_handoff/history/` | `8ea93a9665fbf3552126fb6d34ee69c15f7ec2dcba3ff112fa3b5e23e1ca9b9c` |
| `DELIVERY-021-PM-LLM-POC-GATE2A-CLOSURE-GEMMA-FINALIST.md` | `docs/outsource/pm_handoff/history/` | `14cd9fa14ae580e54cb910258d335d94c98489d92c99791a50df71ac0a8e3988` |
| `DELIVERY-022-PM-LLM-POC-GATE2B-PREWARM-LIFECYCLE.md` | `docs/outsource/pm_handoff/` | `7d60d8532145774a0cef022fe5b602290ef4697eb05a51f943cff605834340c9` |
| `DELIVERY-023-PM-LLM-POC-GATE2B-MEMORY-PSI-REMOVAL.md` | `docs/outsource/pm_handoff/` | `4ebdc655d20b80ce2546168de6071a34a5ad9519f195bba4b8ffd6dca42fea96` |
| `DELIVERY-024-PM-LLM-POC-GATE2B-CLOSURE-GEMMA-WINNER.md` | `docs/outsource/pm_handoff/` | `6787639ce93aa1e9755bb69b6b0434b323b5679fb769a18255dcf2d497345f26` |
| `ASSESSMENT-LLM-M4-GATE2B-20260829-USER-REVIEW.md` | `docs/outsource/pm_handoff/` | `7132342ea1b92a83a3a2373893c5a44324224909930db8228bfdcdeb2ff409e8` |
| `POC-llm-DEL-2026-001-R3.md` | `docs/outsource/pm_handoff/` | `7a2c9b64efab3c5542ed41ce52cc5a7a7192f57a09330cbf2ef5e83bc7a24350` |

The provenance addendum commit is a descendant of the closure content commit and changes only the
publication locators in `DELIVERY-024` and R3. The relay records its exact SHA externally because a
Git commit cannot embed its own identifier. Core can verify both commits from the pushed `llm`
branch and every enclosure from the table above.

## Core review disposition carried forward

Core has reported that `DELIVERY-022` is acceptable as a design requirement to be incorporated into
`docs/protocol.md`. Core has also reported that `DELIVERY-023` is acceptable as a prospective
contract addendum: memory PSI is removed from POC Gate 2B while the 4 GB envelope, swap/OOM, PSS leak,
thermal and cleanup gates remain. These dispositions do not need to be reopened by this locator
supplement.

## One bounded response requested

Please verify provenance addendum commit `485bb2a7c07d86a09899f09358c744edd733f875`, the enclosure
hashes and the closure content commit, then issue the Gate 2B final-winner ACK. If Core still cannot
accept the package, please return one bounded blocking finding. Use R3 as the input to
`docs/model_spec.md`, `docs/protocol.md` and Gate 3 work while preserving the pre-warm lifecycle,
resident-retention mitigation and exact production-SHA revalidation requirements.
