# DELIVERY-024 — Gate 2B Closure and Gemma POC Winner

- **Date**: 2026-08-29
- **From**: LLM POC Team
- **To**: PM / Core Designer
- **Status**: `SUBMITTED — USER-APPROVED POC WINNER / CORE FINAL ACK REQUESTED`
- **Winner**: `CAND-LRT-G4E2B-MOBILE-R1` / Gemma 4 E2B mobile
- **Pairing**: `litert-lm-v0.16.0-pi-g2b-r5`
- **Formal run**: `G2B-PI-COMBINED-006`
- **Execution SHA**: `0c75536e6ee99b502c59438989ca852194648946`
- **Closure content commit**: `5ffdd9eaa3beb9ca09ff6a63839e02248c9a78ae`
- **Execution surface SHA-256**: `22f52d8b8b5b6d0aacbe2959c49441ccee30a0bacb68b9b8fcfc04877c14665a`
- **Sanitized evidence SHA-256**: `f5f5b3acd15e32bb0208da9f838cec4415469c28c12a45b25f8c2f5f55ad33fa`
- **Winner manifest**: `POC-llm-DEL-2026-001-R3`

## Decision delivered

The User reviewed and authorized publication of the immutable Gate 2B evidence, classified the
observed LiteRT-LM Engine/Session resident retention as a known runtime defect, granted a defect
waiver and selected Gemma as the LLM POC winner. This decision does not rewrite the formal machine
result. Core final-winner ACK is still required before the product team may lock the model/runtime or
begin production persistent-child integration.

## Entry and functional result

The clean Pi 5 4 GB checkout passed 84 definition tests with one platform skip. At the same exact
SHA, zero-residency `G2B-PREFLIGHT-006` and one-session full-chain `G2B-DIAGNOSTIC-006` both passed
before the formal run. The diagnostic and formal run used the Core-recorded Accepted Audio package,
real VAD/ASR/LLM/TTS/ALSA, isolated runtimes, offline routes, `swap=0` and authenticated artifacts.

Attempt 006 completed all 20/20 held-out VAD→ASR→LLM→TTS/ALSA sessions. Every domain returned
terminal `SUCCESS`; every LLM result passed constrained schema, current-marker exactly-once, trap
absence and prior-marker isolation. The 19 fixed five-second pauses completed, log hygiene passed,
all four domains stopped cooperatively and no process-group or ALSA owner remained.

Peak system-used memory was 2,382.969 MiB on the 4 GB Pi, peak temperature was 54.0°C, `swap=0`, OOM
delta zero and throttling zero. Owner sampling and cadence were complete. Memory PSI is intentionally
absent under the User-approved prospective r14 adjustment recorded in `DELIVERY-023`.

## Immutable failure and User defect waiver

The frozen verifier returns machine `P9=FAIL` and `P10B=FAIL` because the process-PSS leak rule was
exceeded:

| Measurement | Observed | Frozen limit |
| --- | ---: | ---: |
| Combined PSS slope | 5.900893 MiB/session | <= 4 MiB/session |
| Combined late-minus-early median | 131.578 MiB | <= 64 MiB |
| LLM PSS slope | 5.484794 MiB/session | diagnostic owner attribution |
| LLM late-minus-early median | 115.865 MiB | diagnostic owner attribution |
| System-used slope | 0.101957 MiB/session | <= 4 MiB/session |
| System-used late-minus-early median | 32.750 MiB | <= 64 MiB |

The adapter creates one fresh Conversation per request and unconditionally closes it in `finally`,
matching the documented LiteRT-LM lifecycle. Total process PSS does not distinguish anonymous
allocator/KV high-water from lazy file-backed model residency; the stable system-used measurements,
zero swap/OOM and 20/20 successful sessions show no observed target memory pressure in this run.
The User therefore accepts this as `KNOWN_RUNTIME_DEFECT / ENGINE-SESSION RESIDENT RETENTION` and
waives it for POC winner selection. Attempts 001–006 and their machine dispositions remain immutable.

## Product handoff requirements

Core should consume the winner exactly as fixed by `POC-llm-DEL-2026-001-R3` and implement these
requirements together:

1. separate `ENGINE_LOADED` from `INFERENCE_READY`; publish READY only after the fixed non-sensitive
   pre-warm required by `DELIVERY-022`;
2. enforce the rendered 128-token input budget, 128-token output ceiling, Engine capacity 1024,
   constrained `speak` JSON and current-request marker boundary;
3. keep one operation per fresh Conversation, close it deterministically, prohibit cross-operation
   history/KV reuse and retain process isolation plus terminate→kill→waitpid→rebuild recovery;
4. monitor target `MemAvailable`, process PSS attribution and owner cleanup; define a bounded
   Engine/process recycle policy before Gate 3 rather than assuming Conversation close returns PSS;
5. remeasure the exact production SHA under the same 4 GB, `swap=0`, offline 20-session envelope.
   The POC waiver does not waive Core Gate 3 product verification.

## One Core response requested

Please respond once with:

1. acceptance of the User-approved Gemma POC winner and immutable Attempt 006 evidence;
2. acceptance of the known-runtime-defect waiver without rewriting machine P9/P10B;
3. consolidated disposition of `DELIVERY-019`, `DELIVERY-021`, `DELIVERY-022` and `DELIVERY-023`;
4. confirmation that the R3 winner manifest is the input for Core `docs/model_spec.md` and
   `docs/protocol.md` work; and
5. the Gate 2B final-winner ACK, or one bounded blocking finding if Core cannot accept the waiver.

The closure content, winner manifest, milestone state and round-close audit are immutable at
`5ffdd9eaa3beb9ca09ff6a63839e02248c9a78ae` on the pushed `llm` branch. The subsequent provenance
addendum changes only this locator and the matching R3 locator; its exact commit and file SHA-256
values are supplied by the Core relay envelope so that it does not rely on an impossible
self-referential Git SHA.
