# M4B-MVA-002 — Designer decision package（SUPERSEDED）

> Archived during the USER-directed M4B clean rewrite on 2026-09-09. This file is historical
> reference only and must not be used as current design or implementation authority.

Date: 2026-09-09. Status: Designer selected adoption proposal recorded; focused review and the
formal profile/identity supplement remain pending. Not Development Ready.

This prospective revision takes precedence over 001 draft timing/scope assumptions only as listed here. Historical issued requests/results remain unchanged. Source: DELIVERY-025 at `23fb481007ebaf9d4c58d66b762a65aacec9196c`; review is report-based, not a repeat POC code audit. Reported 23 machine PASS and manual 8 Pass/4 Fail are retained as reported; no new Core hardware acceptance is asserted.

## Selected adoption proposal — efficiency 003 / prompt 004

The User-delivered engineering reports are
[`EFFICIENCY-003`](../outsource/pm_handoff/DELIVERY-LLM-POC-M4B-MVA-EFFICIENCY-003.md)
and [`PROMPT-V2D2-004`](../outsource/pm_handoff/DELIVERY-LLM-POC-M4B-PROMPT-V2D2-004.md).
Their byte SHA-256 values as received by Core are respectively
`0194853631e159857996bfdb6cafaecf67122c0b6fc0272c9816d98d9c3dad93` and
`9bab6d3fe475309817f68d960361bec689d3a4fa17e1c18fc3f3273ee1f41404`.
These receipt hashes do not replace the missing full POC source/result commit SHA. Both reports are
engineering observations, not a formal hardware packet or an M4B gate PASS.

Designer selects one implementation proposal for focused review:

- **Encoding:** constrained JSON `J`, mapped to internal `SemanticGeneration(text,end)`. `P` is
  ineligible because its explicit-end behavior regressed. `S2` is the only incremental extraction
  seam: M4B buffers provisional text until the valid terminal; M4C may release ordered text through
  the already reviewed single-speak control. `S3`/`S4` are excluded.
- **Readiness:** `D`, on-demand clean Conversation open after product-session begin. Engine loading
  may occur before a request, but no fake turn, history-bearing prewarm or unclaimed Conversation is
  held. `H` remains a future optional optimization: the reported approximately 3.1-second moved open
  cost and approximately 253-MiB early allocation are useful, but the exact H record and required
  formal paired lifecycle/isolation/cleanup packet were not retained.
- **Reasoner input:** only normalized listen text enters the model user role. Session facts,
  capabilities, identities and Core envelopes stay software-owned. The current M4B input envelope is
  at most 20 Unicode codepoints and must also pass a 32-new-user-token pre-admission bound. Future
  projectors require a new aggregate rendered/KV policy; they are not silently admitted here.
- **Prompt:** V2D2 is the current replaceable baseline: exact 57-token core plus the exact 9-token
  trusted personality `溫暖自然，稍帶幽默。`, for 66 system tokens under the reported tokenizer.
  Its known indirect vision answer is accepted only for voice-only M4B and must not become a claim
  that look/camera exists.
- **End semantic proposal:** `end=false` requires nonblank text and produces speak then listen.
  `end=true` permits empty text for immediate rest or nonblank text for one final speak with no next
  perception, followed by normal session end. Empty text with `end=false`, extra fields, invalid
  terminal or identity mismatch remains destructive invalid output. The final-speak path is a
  contract delta and is not implementable until focused architecture/design review passes.

The provisional Core profile identity remains `core-m4b-mva-001`. Selected exact bounds are
20 Unicode codepoints plus 32 new-user tokens, 128 output tokens, 1024 total Engine KV tokens,
one active generation, one Conversation and readiness `D`. Runtime-prefill 128 is telemetry, not an
admission limit or a correctness threshold. The hard admission equation remains current KV plus
rendered new input plus the full 128-token output reserve no greater than 1024.

Profile freeze and both POC gate releases remain blocked on: the full POC result/source commit SHA;
the requested formal/parity disposition (or an explicit User scope revision); exact
startup/open/generate/close/cancel operational deadlines; and the M4B capacity reserve/stable-window
values. EFFICIENCY-003 explicitly says the original five-pair J/P and D/H matrices were not run, so
their absence is preserved rather than converted into PASS. These missing values block release, not
focused design review.

## Ownership and implementation boundary

- SM owns session identity and transitions; Reasoner owns capability and action policy; adapter owns model encoding and Conversation control; RM owns worker recovery. One generation and at most one Conversation are active.
- Model encoding is constrained JSON J with S2 as the sole future incremental extraction seam, as
  selected above. Stable internal SemanticGeneration(text,end) shields Reasoner from parser details.
  Product action/envelope JSON is software-generated.
- M4B implements selected encoding, lifecycle, capacity admission, idle end and bounded recovery plus full-response operation. M4C implements incremental Reasoner-to-TTS delivery and integrated cancellation. No model-generated action envelope, tool dispatch, look, summary, retrieval or cross-session memory.
- Stream seam: Begin(sid,tid,cid), ordered Text(sequence,text), exactly one Complete or Failed. Identity and sequence are software fields. Before Complete, text is provisional; M4B full-response consumer buffers it. M4C maintains one speak action with bounded input queue; fragments are not Facts or independent actions. Terminal failure cancels queued/in-flight speech, closes dirty session and emits no success. Already audible content cannot be retracted.

## Readiness and session lifecycle

Selected M4B readiness is on-demand `D`: SM begin obtains a newly opened clean Conversation and no
unclaimed Conversation is held before the request. Simultaneous begin/end is single-flight. Opening
cancellation closes late native results before any new session. Engine-ready and interaction-ready
remain distinct observations. The architecture may retain the already reviewed pre-open ownership
seam, but H is not enabled by this profile.

Cold prewarm stays off until a measured profile explicitly selects it; same-boot replacement uses none. No arbitrary greeting promotion. POC A/B selection determines readiness policy; Developer cannot choose an unmeasured variant.

Idle timeout proposal: 30s only while awaiting the next user input. Pause during active listening capture, generation and playback; arm after completed speech or entering ready-to-listen. First detected speech disarms it; ASR/listen timeout still has its own bound. Timer carries sid/epoch; stale expiry is ignored. Expiry requests normal session end and IDLE. This timer does not interrupt a valid active operation.

Reset means cancel/end current session and return IDLE with no inherited context, not Pi reboot or factory reset. Use the existing interrupt/convergence path; M4C binds the user control, without inventing a new button gesture in M4B.

## Capacity and resource policy

Before inference verify exact runtime current KV + rendered new input + output reserve <= selected KV limit. No fixed 17/18-turn rule. Input too large before mutation retains session with bounded existing fallback. Capacity exhaustion closes session and returns rest/IDLE; Display identifies session end. No silent reset or automatic prompt replay. Summarization/truncation remain excluded.

The selected provisional envelope is 20 Unicode codepoints plus 32 new-user tokens, 128 output
tokens and 1024 total Engine KV tokens under the reported tokenizer. It is not a frozen production
profile until the exact source identity, operational deadline table, capacity values and complete
profile digest are recorded. POC watchdogs are execution bounds, not response SLA. Missing values
block release, not workstation design work.

Remove fixed session-count and relative-PSS recycle. Proposed capacity control: low MemAvailable observed twice at least 1s apart prevents new admission, closes the session after bounded convergence and requests one replacement; a sample below the hard reserve prevents admission immediately. RM opens its barrier only above reserve plus configured hysteresis. Replacement still low fails once, no loop. OOM, swap growth, thermal fault, identity loss and unprovable cleanup use immediate fault handling, never wait for two samples. PSS is attribution until combined evidence supports an absolute limit. Numeric reserve/hysteresis are adopted at M4C composition gate; M4B verifies the policy with injected values and records its real observed envelope, not full-product headroom.

## Objective acceptance and handoff

M4B: real runtime normal/follow-up/end lifecycle, session isolation, capacity rejection before inference, idle expiry, interruption during open/generate/close, invalid/late output, one recovery and failed-recovery stop; no orphan process or stale success. Unit injections prove policies; target observations prove selected native behavior. Inherit unchanged install/offline/privacy checks; inspect only changed loading/logging paths. Do not repeat POC model selection or introduce a new subjective knowledge/briefness gate.

Record first/subsequent caller timing and complete recovery duration at M4B. M4C records the full speech-end-to-audible path and combined resources. 2s target/3s ceiling and 10s recovery become ALPHA product acceptance metrics; misses before ALPHA require recorded gap/next action, not hidden PASS or automatic model rejection. Operational timeouts remain mandatory at every stage.

Manual H03/H05/H06/H11 remain recorded Fail accepted by User as follow-up issues. Objective malformed output, lifecycle failure and capability bypass are software defects; factual/wording observations do not start unlimited tuning. ALPHA quality review has a fixed corpus and a recorded disposition, with any experiment separately bounded.

## Remaining gates, not delegated implementation guesses

1. M4B-MVA-EFFICIENCY: formal/source identity and profile-value supplement; the engineering
   selection is recorded but the gate remains Open.
2. Affected Architect/Reviewer approval: J/S2, D readiness and V2D2 final-speak semantics; unchanged
   001 faces need not reopen.
3. Designer profile freeze and both POC gates explicitly released; then Tester activates TR_spec_M4B_IV, Developer estimates and implements after coverage sign-off.
4. M4C composition gate sets resource numbers and launcher/control/display contract before its implementation.
