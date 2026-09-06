# DELIVERY-025 — M4B-MVA Step 5 Result

- **Date**: 2026-09-06
- **From**: LLM POC Team
- **To**: PM / Core Designer
- **Status**: `SUBMITTED — USER-APPROVED RESULT / CORE STEP 6 ACK REQUESTED`
- **Baseline**: `M4B-MVA-001`
- **Formal execution SHA**: `7bb332670b5fdf45f05f07dd385bec94d914b4e1`
- **Formal surface SHA-256**: `61764d0737fcf374468621bd90d4765739d2f9b2b06e4314b1dbb73229f74e89`
- **Scope**: `llm_subsystem`

## Result delivered

The User reviewed and approved publication of the Pi 5 MVA results. Formal `MVA-002` completed all
23 machine cases and the independent audit passed. The reviewed LLM-only hardware disposition is
`PASS`. The private audit SHA-256 is `6708ca2103dc2c82dd4dd616880c3fa2a97afb0690937ab2d7ea109eb3d65487`;
the private review aggregate SHA-256 is `b7614ae133574c002b6b863e90a5df4ac762dff11b73db2c82aacad60059df05`.

The User-directed long-Conversation supplemental ran three fresh cycles. Every cycle completed 17
turns and received typed `CONTEXT_LIMIT` on attempted turn 18: KV grew from 167 to 910, and the frozen
128-token output reserve made `910 + 128 > 1024`. Fresh-session recovery and cleanup passed in all
cycles. Private evidence SHA-256 is
`4b118b165d4bc9ca27569907c5ea675cce2003214bc25bac2fc9e3d1716e2cd5`.

The private H01–H12 run completed 12 sessions and 24 generations without retry. User-reviewed sanitized
results are 8 Pass / 4 Fail / 0 Unclear. H03 missed explicit end intent, H05 reversed a density fact,
H06 over-refused general knowledge and H11 was too verbose. The failures remain recorded as failures;
the User accepted all four as non-blocking follow-up improvements. No raw prompt, answer or audio is
committed.

## Product findings Core must address

1. Hide Conversation creation from request latency. Cold/once-prewarm first-turn caller TTC was
   7.704 s: about 3.305 s Conversation open, 1.689 s generation-to-first-token and 2.708 s for the
   remaining 25 output tokens. Evaluate a clean pre-opened Conversation or reuse of a warmed
   Conversation only after quality, isolation, cancellation, capacity and memory validation.
2. Do not require complete JSON before speech. Design a compact stream-safe semantic frame and submit
   validated text to TTS in punctuation- or size-bounded chunks while preserving Reasoner authority,
   cancellation and backpressure.
3. Budget history, new input and expected output together. Add summarization/truncation or controlled
   rollover before the measured KV boundary; do not treat repeated short sessions as long-context proof.
4. Do not recycle by session count. Define owner-PSS, MemAvailable, swap/OOM/thermal and dirty-cleanup
   limits with sustained violations and hysteresis. The formal peak owner PSS was 1981.592 MiB, while
   the 60-session run showed no progressive system-memory pressure attributable to session count.
5. Tighten prompt/response budgeting for brief voice answers, improve basic-knowledge behavior and add
   a controller-owned idle timeout/reset so a missed model `end=true` cannot retain a Conversation.

## Audio disposition

No accepted M4a Audio identity and common-timebase audible-onset proof was present. The result is therefore
`speech_end_to_audible_onset=null`, `NO_AUDIO_PROOF`, scope `llm_subsystem`. The User explicitly deferred
this integration test; it must not run without renewed User approval and does not block this LLM Step 5
delivery.

## Core response requested

Please complete Step 6 by recording the full result commit, accepted scope and chosen product profile;
resolve the five product findings above; and explicitly return `gate released`, or one bounded blocking
finding. Until that ACK, `M4B-MVA-POC` remains externally Open even though POC Step 5 is delivered.

Detailed evidence interpretation and the full latency, memory, long-session and manual tables are in
`docs/response/ASSESSMENT-LLM-M4B-MVA-PI-ENTRY-001.md`.
