# DELIVERY-022 — Gate 2B Inference Pre-warm Lifecycle Requirement

- **Date**: 2026-08-29
- **From**: LLM POC Team
- **To**: PM / Core Designer
- **Status**: `SUBMITTED — DESIGN INTEGRATION REQUIRED / ACK MAY FOLLOW EXECUTION`
- **Affected boundary**: LiteRT-LM child startup and Core availability state
- **Exact corrective commit**: supplied by the accompanying pushed Git revision

## Required design change

Core must not treat LiteRT-LM `Engine()` construction or the old child `READY` event as proof that
the first user inference meets the request SLA. Adopt this lifecycle for the product child:

1. authenticate artifacts/configuration and construct the Engine (`ENGINE_LOADED`);
2. execute one fixed, public, non-sensitive pre-warm request through the same chat template,
   tokenizer, constrained-output path and disposable Conversation used by product requests;
3. close that Conversation and discard its output, history and KV state; and
4. publish `INFERENCE_READY` only after pre-warm completes successfully.

The existing wire-level `READY` frame may be retained for compatibility only if its documented
meaning becomes `INFERENCE_READY`. Pre-warm duration belongs to startup/availability accounting; it
must not be hidden inside the first user's generation latency. Repeat the lifecycle on every child
process/service start. Same-boot cache reuse can reduce the cost but is not a correctness guarantee.

## Evidence behind the requirement

Immutable Gate 2B Attempt 003 used pairing `litert-lm-v0.16.0-pi-g2b-r1`. After READY, its first
request reached both the child and parent 15-second deadline. A reboot-cold, no-credit reproduction
of the identical prompt/output completed in `16.704 s`; a same-boot fresh process and fresh Engine
completed it in `5.061 s`. Thus Engine construction had finished in both cases, but only the
same-boot path had paid the first-inference/cache preparation cost. Attempt 003 remains FAIL and is
not rewritten by this delivery.

The diagnostic also found two independent integration defects: the declared 128-token input profile
actually reached 298 prefill tokens, and the complete output was schema-invalid and omitted the
current marker. Pre-warm does not excuse either defect. Pairing `r4` separately enforces the rendered
input budget with the model tokenizer and uses LiteRT-LM LLGuidance constrained decoding for the
frozen speak-only response structure and controlled current-marker pattern. Exact-once, forbidden-
literal and prior-marker behavior remain independently scored. The preceding `r2` public no-credit
probe proved prompt-only marker wording insufficient and never entered formal Audio residency.
Attempt 004 then proved that a 64-token output ceiling can truncate otherwise constrained JSON; an
identical-input no-credit reproduction completed at 72 tokens. The corrected output ceiling is 128,
within the unchanged 1024-token Engine capacity and independent of the 128-token input limit.
Pairing `r5` preserves this LLM lifecycle and every r4 token/deadline/marker setting unchanged; it
only authenticates and activates the Accepted Audio `controller-r2` runtime closure for the combined
controller. It does not add or alter a Core pre-warm requirement.

## Watchdog and state requirements

- Authenticate/hash static artifacts before startup timing; never hash the model in READY.
- Use distinct Engine-load/pre-warm, first-token, generation and terminal-observation watchdogs.
- Keep the 15-second scored generation deadline. A 2-second parent terminal-only grace may receive a
  child `TIMEOUT`/`ERROR`, but cannot convert late generation into PASS.
- Reject before inference if the chat-template-rendered input exceeds 128 model tokens; also reject
  if runtime benchmark `prefill_tokens` exceeds 128.
- Emit only sanitized pre-warm telemetry (timings, token counts and public prompt digest); never log
  prompt/output text.
- After pre-warm, verify the disposable Conversation is closed and no user history/KV is carried into
  the first scored or production session.

## Core ACK requested

Please acknowledge in one response that the Core child/service design will:

1. distinguish `ENGINE_LOADED` from `INFERENCE_READY`;
2. make a fixed disposable pre-warm mandatory before accepting user work;
3. account for pre-warm in startup availability rather than request latency;
4. enforce the actual rendered-token budget and preserve separate output-schema/marker checks; and
5. use separate generation and terminal-observation deadlines.

ACK may follow the already User-authorized corrective Pi execution and does not block evidence
collection. Final Gate 2 delivery must link the Core disposition. Any new corrective benchmark result
remains `REVIEW_REQUIRED` until the User approves publication.
