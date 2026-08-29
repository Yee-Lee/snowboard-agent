# LLM POC Winner Manifest R3

- **Delivery ID**: `POC-llm-DEL-2026-001-R3`
- **Date**: 2026-08-29
- **Repository / branch**: `poc_llm/snowboard-agent` / `llm`
- **Delivery HEAD**: supplied in the post-commit response; not self-prefilled
- **Status**: `USER-APPROVED POC WINNER / CORE FINAL ACK PENDING`
- **Winner**: `CAND-LRT-G4E2B-MOBILE-R1` / Gemma 4 E2B mobile
- **Known defect**: `LiteRT-LM Engine/Session resident retention / USER WAIVED FOR POC`
- **Owner**: LLM POC Technical Lead

## Frozen winner identity

| Item | Frozen value |
| --- | --- |
| Pairing revision | `litert-lm-v0.16.0-pi-g2b-r5` |
| Platform | Raspberry Pi 5 4 GB / Debian 13 aarch64 / `swap=0` / offline |
| Runtime | LiteRT-LM API `0.16.0`, AArch64 wheel |
| Runtime wheel SHA-256 | `5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00` |
| Native library SHA-256 | `9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4` |
| Runtime source | LiteRT-LM `v0.16.0`, source tag commit `924e79c91542761242244e4f1651851f822e4cbb` |
| Runtime license | Apache-2.0 |
| Model source | `litert-community/gemma-4-E2B-it-litert-lm@6b78abd019e61a1ca4cbe3b212d2c9ce8ff38a94` |
| Model file | `gemma-4-E2B-it.litertlm`, artifact-embedded mobile quantization |
| Model SHA-256 | `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c` |
| Model size | 2,588,147,712 bytes |
| Model license | Apache-2.0 in authenticated candidate metadata |
| Protocol | `snowboard.llm/1` |
| Product config | `poc_llm/fixtures/gate2/pi-configs-v2/CAND-LRT-G4E2B-MOBILE-R1-gate2b-product-v2.json` |
| Product config SHA-256 | `c4557b018733ce8a2f4aa46b375cc7dafb31fbd8c363271deb1156c651e5171e` |

No model, wheel, native library, raw prompt/output/audio or credential is committed in Git. Core
must acquire and authenticate the exact artifacts through the recorded source/receipt chain; runtime
download and network fallback remain prohibited.

## Frozen product boundary

| Setting | Value |
| --- | ---: |
| Rendered input limit | 128 tokens, enforced before generation |
| Output limit | 128 tokens |
| Engine capacity | 1024 tokens |
| Temperature / top-p | `0.0` / `1.0` |
| Threads | 4 |
| READY deadline | 45,000 ms for Gate 2B startup envelope |
| Generate / terminal grace | 15,000 / 2,000 ms |
| Cancel / TERM / KILL | 500 / 2,000 / 1,000 ms |
| Rebuild READY | 10,000 ms |
| Output | constrained `speak` JSON plus current-request marker |
| Conversation policy | fresh single-turn Conversation per operation; deterministic close |
| Readiness policy | Engine load, fixed pre-warm, then `INFERENCE_READY` |

The strict config, child protocol frame schema, Gate 2B adapter, prompt boundary and marker rules in
the execution surface are the POC reference for Core `docs/model_spec.md` and `docs/protocol.md`.
They are not authorization to copy POC orchestration into the product composition root unchanged.

## Cumulative P1–P12 record

| P item | Immutable machine record | Winner disposition |
| --- | --- | --- |
| P1 | `PASS` | accepted Gate 1 lifecycle/READY evidence |
| P2 | `FAIL` 3/30 on old Gate 2A pairing | retained; semantics adjusted; replacement Gate 2B pairing completed 20/20 held-out full-chain sessions |
| P3 | `PASS` | accepted deterministic safety boundary |
| P4 | `PASS` | TTFT P95 727.983 ms; decode P50 11.293 tok/s |
| P5 | `PASS` | accepted continuous-timeout and cleanup evidence |
| P6.1 | `PASS` | native cancel 1.069 ms; terminal 96.322 ms |
| P7.1 | `PASS` | abort/absence 15.109 ms; rebuild READY 513.968 ms |
| P8 | `FAIL / DEPENDENCY_LIMITED_BY_P2` on old pairing | retained; no prior-state leak; Gate 2B replacement passed all current/prior-marker boundaries |
| P9 | `FAIL` | User-waived known LiteRT-LM resident-retention defect |
| P10A | `PASS` | accepted 20-session LLM-only soak |
| P10B | `FAIL` through shared P9 resource predicate | 20/20 functional combined sessions; User defect waiver selects winner |
| P11 | `PASS` | accepted provenance/license/artifact receipt |
| P12 | `PASS` | accepted offline/log-hygiene evidence; Gate 2B also offline/clean |

Machine results are never rewritten. The User waiver and winner decision are governance
dispositions layered on the immutable receipts and must be visible in Core's downstream risk record.

## Gate 2B evidence

| Item | Identity / result |
| --- | --- |
| Packet | `G2B-PI-COMBINED-001`, revision `2026-08-29-r14-user-resource-adjustment` |
| Formal run | `G2B-PI-COMBINED-006` |
| Execution SHA | `0c75536e6ee99b502c59438989ca852194648946` |
| Execution surface SHA-256 | `22f52d8b8b5b6d0aacbe2959c49441ccee30a0bacb68b9b8fcfc04877c14665a` |
| Sanitized evidence SHA-256 | `f5f5b3acd15e32bb0208da9f838cec4415469c28c12a45b25f8c2f5f55ad33fa` |
| Full-chain sessions | 20/20 terminal success; schema/marker/trap/history guards complete |
| Capacity / health | peak system-used 2,382.969 MiB; 54.0°C; swap/OOM/throttle zero |
| Leak observation | combined PSS 5.900893 MiB/session and 131.578 MiB late-minus-early median |
| Cleanup | all domains cooperative; process groups absent; ALSA owners zero |
| Publication | User approved; known runtime defect waived for POC winner |

Accepted Audio identity is tag `audio_m4` object `24b2571a23dde2f77027242b61142b0c1a59924c`,
completion SHA `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`, Core response
`RESP-AUDIO-M4-GATE2B-001` / `be19b70b1dd91674e7ff981eb9d6b2dca9741f54`, controller-r2 manifest
`6bb24f9a0a2f2a66a522706b22222081fbf009b28c9dc0942a22d714114276f4` and 20-fixture
lock `d7d3086c578511763b60074ef7c049e37ef814094e399ad3562e3be2fda0e0f8`.

## Residual risk and Core action

The retained PSS is classified as a LiteRT-LM runtime defect because the reference adapter follows
the documented fresh-Conversation/close lifecycle. Existing evidence cannot separate anonymous
allocator/KV high-water from file-backed residency. No system pressure, swap, OOM, throttling,
functional failure or cleanup residue occurred in the 20-session run.

Core must preserve the pre-warm lifecycle, process isolation and recovery barrier; monitor
`MemAvailable` plus process attribution; define a bounded Engine/process recycle policy; and repeat
the combined envelope against the exact production SHA in Gate 3. The POC waiver does not waive
product verification.

## External state at handoff

- User publication approval and POC winner decision: complete.
- Gate 1 Core closure ACK: complete.
- Gate 2A/result semantics, pre-warm lifecycle and Memory PSI adjustment: consolidated Core response
  requested by `DELIVERY-024`; exact ACK is not present in this checkout.
- Gate 2B Core final-winner ACK: pending `DELIVERY-024` review.
- Product `docs/model_spec.md`, `docs/protocol.md` and Gate 3 implementation/testing remain Core-owned
  and must not be inferred as completed by this POC handoff.
