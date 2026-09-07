# M4B-MVA-002 — Designer decision package

Date: 2026-09-06. Status: Designer proposal complete; POC-dependent selections and affected architecture review pending. Not Development Ready.

This prospective revision takes precedence over 001 draft timing/scope assumptions only as listed here. Historical issued requests/results remain unchanged. Source: DELIVERY-025 at `23fb481007ebaf9d4c58d66b762a65aacec9196c`; review is report-based, not a repeat POC code audit. Reported 23 machine PASS and manual 8 Pass/4 Fail are retained as reported; no new Core hardware acceptance is asserted.

## Ownership and implementation boundary

- SM owns session identity and transitions; Reasoner owns capability and action policy; adapter owns model encoding and Conversation control; RM owns worker recovery. One generation and at most one Conversation are active.
- Model encoding J/P is selected through [the experiment](../outsource/deliveries/active/REQUEST-LLM-POC-M4B-MVA-EFFICIENCY-002.md). Stable internal SemanticGeneration(text,end) shields Reasoner from format changes. Product JSON is software-generated.
- M4B implements selected encoding, lifecycle, capacity admission, idle end and bounded recovery plus full-response operation. M4C implements incremental Reasoner-to-TTS delivery and integrated cancellation. No model-generated action envelope, tool dispatch, look, summary, retrieval or cross-session memory.
- Stream seam: Begin(sid,tid,cid), ordered Text(sequence,text), exactly one Complete or Failed. Identity and sequence are software fields. Before Complete, text is provisional; M4B full-response consumer buffers it. M4C maintains one speak action with bounded input queue; fragments are not Facts or independent actions. Terminal failure cancels queued/in-flight speech, closes dirty session and emits no success. Already audible content cannot be retracted.

## Readiness and session lifecycle

On-demand open remains fallback. If POC supports pre-open: adapter holds one unclaimed clean Conversation with fixed facts, never prewarm history. SM begin atomically binds it only when facts/profile/generation match. Simultaneous begin/end is single-flight. Opening cancellation closes late native results before any new session. After 30s unclaimed hold, close; no perpetual reopen loop. New user begin can open on demand afterward. Engine-ready and interaction-ready are distinct observations. This ownership extension requires Architect review before implementation.

Cold prewarm stays off until a measured profile explicitly selects it; same-boot replacement uses none. No arbitrary greeting promotion. POC A/B selection determines readiness policy; Developer cannot choose an unmeasured variant.

Idle timeout proposal: 30s only while awaiting the next user input. Pause during active listening capture, generation and playback; arm after completed speech or entering ready-to-listen. First detected speech disarms it; ASR/listen timeout still has its own bound. Timer carries sid/epoch; stale expiry is ignored. Expiry requests normal session end and IDLE. This timer does not interrupt a valid active operation.

Reset means cancel/end current session and return IDLE with no inherited context, not Pi reboot or factory reset. Use the existing interrupt/convergence path; M4C binds the user control, without inventing a new button gesture in M4B.

## Capacity and resource policy

Before inference verify exact runtime current KV + rendered new input + output reserve <= selected KV limit. No fixed 17/18-turn rule. Input too large before mutation retains session with bounded existing fallback. Capacity exhaustion closes session and returns rest/IDLE; Display identifies session end. No silent reset or automatic prompt replay. Summarization/truncation remain excluded.

32/128/1024 remain an experimental envelope, not final production values. Gate adoption must record exact input/output/KV, tokenizer interpretation, startup/open/generate/close/cancel deadlines and readiness policy in a versioned profile with digest. POC watchdogs are execution bounds, not response SLA. Missing values block release, not workstation design work.

Remove fixed session-count and relative-PSS recycle. Proposed capacity control: low MemAvailable observed twice at least 1s apart prevents new admission, closes the session after bounded convergence and requests one replacement; a sample below the hard reserve prevents admission immediately. RM opens its barrier only above reserve plus configured hysteresis. Replacement still low fails once, no loop. OOM, swap growth, thermal fault, identity loss and unprovable cleanup use immediate fault handling, never wait for two samples. PSS is attribution until combined evidence supports an absolute limit. Numeric reserve/hysteresis are adopted at M4C composition gate; M4B verifies the policy with injected values and records its real observed envelope, not full-product headroom.

## Objective acceptance and handoff

M4B: real runtime normal/follow-up/end lifecycle, session isolation, capacity rejection before inference, idle expiry, interruption during open/generate/close, invalid/late output, one recovery and failed-recovery stop; no orphan process or stale success. Unit injections prove policies; target observations prove selected native behavior. Inherit unchanged install/offline/privacy checks; inspect only changed loading/logging paths. Do not repeat POC model selection or introduce a new subjective knowledge/briefness gate.

Record first/subsequent caller timing and complete recovery duration at M4B. M4C records the full speech-end-to-audible path and combined resources. 2s target/3s ceiling and 10s recovery become ALPHA product acceptance metrics; misses before ALPHA require recorded gap/next action, not hidden PASS or automatic model rejection. Operational timeouts remain mandatory at every stage.

Manual H03/H05/H06/H11 remain recorded Fail accepted by User as follow-up issues. Objective malformed output, lifecycle failure and capability bypass are software defects; factual/wording observations do not start unlimited tuning. ALPHA quality review has a fixed corpus and a recorded disposition, with any experiment separately bounded.

## Remaining gates, not delegated implementation guesses

1. M4B-MVA-EFFICIENCY: encoding/readiness experiment and report adoption.
2. Affected Architect/Reviewer approval: early ownership and incremental action seam; unchanged 001 faces need not reopen.
3. Designer profile freeze and both POC gates explicitly released; then Tester activates TR_spec_M4B_IV, Developer estimates and implements after coverage sign-off.
4. M4C composition gate sets resource numbers and launcher/control/display contract before its implementation.
