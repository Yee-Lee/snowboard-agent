# DELIVERY-LLM-POC-M4B-GATE2B-FINAL-WINNER-ACK-001

- **Date**: 2026-08-29
- **From**: Core Designer
- **To**: LLM POC Team (M4b) / PM Team
- **Status**: `ACKNOWLEDGED — GEMMA POC WINNER ACCEPTED / CORE GATE 3 PENDING`
- **Closes**: `M4B-G2B-F01`, `DELIVERY-024-PM-LLM-POC-GATE2B-CLOSURE-GEMMA-WINNER`
- **Execution SHA**: `0c75536e6ee99b502c59438989ca852194648946`
- **Closure content commit**: `5ffdd9eaa3beb9ca09ff6a63839e02248c9a78ae`
- **Publication / provenance commit**: `485bb2a7c07d86a09899f09358c744edd733f875`
- **Winner manifest**: `POC-llm-DEL-2026-001-R3`

## Final winner decision

Core accepts `CAND-LRT-G4E2B-MOBILE-R1` / Gemma 4 E2B mobile as the
final LLM POC winner and accepts R3 as the authoritative input for Core
`docs/model_spec.md`, `docs/protocol.md`, M4b test planning and Gate 3 product
work. Qwen remains excluded from the formal path.

This ACK consolidates and closes the requested dispositions:

- `DELIVERY-019` P2/P3/P8 semantic separation and immutable Gate 2A results;
- `DELIVERY-021` sole Gemma model-finalist selection;
- `DELIVERY-022` mandatory Engine-loaded / pre-warm / inference-ready lifecycle;
- `DELIVERY-023` prospective POC Gate 2B Memory PSI removal while retaining the
  other resource, leak, thermal, stability and cleanup gates; and
- `DELIVERY-024` User-approved POC winner and known-defect waiver.

## Immutable machine result and waiver boundary

Formal run `G2B-PI-COMBINED-006` remains machine P9 `FAIL` and P10B `FAIL`.
Core does not relabel or overwrite those values. Attempt 006 exceeded the
frozen process-PSS leak rules but completed 20/20 held-out full-chain sessions
with valid schema/current-marker/prior-marker boundaries, peak system-used
memory `2382.969 MiB`, `swap=0`, zero OOM/throttling, bounded temperature and
zero final process/ALSA residue.

Core accepts the User's `KNOWN_RUNTIME_DEFECT / ENGINE-SESSION RESIDENT
RETENTION` waiver for POC winner selection. The waiver does not establish root
cause, promise a PSS plateau, waive product cleanup/recovery, or grant Core Gate
3 PASS. Core must define a bounded Engine/process recycle policy and repeat the
4 GB offline 20-session envelope against the exact product SHA.

## Provenance closure

Core verified:

1. `0c75536...` is an ancestor of closure `5ffdd9e...`, which is an ancestor of
   provenance commit `485bb2a...`;
2. the closure commit changes documentation, milestone records, the User
   assessment and R3 manifest only; no runner/lock/schema/config/result or
   Attempt 006 input changed;
3. the provenance commit changes only the delivery and R3 publication locators;
4. the committed delivery, assessment and R3 SHA-256 values equal the Core
   enclosures: `6787639c...`, `7132342e...`, `7a2c9b64...`; and
5. the exact Gate 2B lock digest reproduces as
   `22f52d8b8b5b6d0aacbe2959c49441ccee30a0bacb68b9b8fcfc04877c14665a`.

Core also reproduced the exact execution surface's workstation Gate 2 suite:

```text
python3 -m pytest -q poc_llm/tests/gate2
84 passed in 10.96s
```

`M4B-G2B-F01` is Resolved. No Pi rerun or evidence mutation is required.

## Accepted winner identity

| Item | Accepted value |
| :--- | :--- |
| Pairing | `litert-lm-v0.16.0-pi-g2b-r5` |
| Runtime | LiteRT-LM API `0.16.0`; AArch64 wheel SHA-256 `5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00` |
| Native library | SHA-256 `9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4` |
| Model | `gemma-4-E2B-it.litertlm`; SHA-256 `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c`; 2,588,147,712 bytes |
| Model source | `litert-community/gemma-4-E2B-it-litert-lm@6b78abd019e61a1ca4cbe3b212d2c9ce8ff38a94` |
| Runtime / model license | Apache-2.0; preserve exact source metadata, license text and notices |
| Product config | SHA-256 `c4557b018733ce8a2f4aa46b375cc7dafb31fbd8c363271deb1156c651e5171e` |
| Protocol | `snowboard.llm/1` |

## Core development gate

The final POC input dependency is satisfied, but this ACK is not Core product
acceptance. Candidate-specific implementation starts only after the updated
`docs/protocol.md` passes design review and Tester completes the M4b test-spec
coverage review. Core must preserve exact artifact/config locks, offline/no-
fallback behavior, mandatory pre-warm, rendered-token limits, constrained
output, fresh Conversation isolation, cancellation/recovery proof, resident-
retention mitigation and exact-SHA Gate 3 evidence.
