# Current handoff

- Updated: 2026-10-18
- Writer: Designer only
- Current milestone: ALPHA Voice-only product convergence — L／P／R／Q／M
- Current stage: **ALPHA delivery complete；no active work package**
- Next owner: None
- Delivery basis: **USER accepts `8b4af53f433c4bcdb5b858973e10767318986554` from the existing
  same-content Pi, Q and real-user operation evidence.**

## Gate transition facts

- M4／M4C remains Accepted; old evidence is not reopened.
- Developer delivery `19d9ca2` retains WIP `9c13509` and delivers fixed terminal installation plus repaired
  interruption／restart／stop. Pi native／portable／installed-entry checks and USER live retest are in
  [development.md](development.md). Iteration delivery does not imply whole-ALPHA Accepted.
- USER and Designer agree to close ALPHA against exactly five areas: Lifecycle (L), Performance (P),
  Recovery (R), Quality (Q), Manual (M). ALPHA.P is P's analysis／experiment／improvement work package.
- Reopen P and M work, preserving the delivered repair. P01–P05 definitions／results remain unchanged by
  the new round. New automated cases are PN01–PN05, paired with fixed-scenario human PH01–PH05;
  PN06／PH06 is conditional on a concrete cause-discrimination gap. PN／PH are inside P, not new areas.
- [ALPHA.md](../milestones/ALPHA.md) §4.5–§4.7 fixes questions, two fresh-App blocks per mode,
  before／after rules, real-time PN PCM, shared structured observations, diagnostic completeness,
  correspondence／uncertainty, failure handling and at most one evidence-supported improvement.
- Reproduced slow samples require analyzable request／Turn／fragment correlation, observed parent／child／
  LLM／TTS／Audio boundaries and relevant token／context counts. Missing required data is diagnostic INVALID;
  inaccessible native subphases are explicit limits, not invented causes.
- ALPHA §6A now records M's original live-testing background, failed launches／operation findings,
  successful repaired-version retest and retained timings with existing log／status locators. It classifies
  earlier unnamed activity without manufacturing prior M test cards／run IDs or rewriting failures.
- Latest M first-response observation: ASR final → Audio first write 13.333 s; legacy `llm_send` →
  first-safe-text 12.762 s. Legacy `llm_send` is child native-generation start, not measured parent IPC send.
  Cause remains unproven; old text rows truncate and human speech-end／acoustic timestamps are absent.
- M final-version free conversation／operation is distinct from PH's fixed timing script. USER completed it
  on the retained delivery with cross-Session reuse, return to standby and normal stop; it is not repeated
  merely because it was not originally labeled as a separate card.
- Q retains six mandatory revised basic-quality cases after ALPHA.P. Old questions are retired and original
  Q05／Q06 FAIL cards remain. Earlier overall quality acceptance does not waive final objective／semantic PASS.
- L／R／Q design is not reopened. Apply directly affected development regression and complete final L／R／Q,
  valid P and M against one final product content; no splicing older candidates. Existing applicable
  final-candidate P／PH／M evidence may be reused without duplicate testing.

## Test Spec coverage confirmed

- Designer checked the revised [test_spec_ALPHA.md](../test_spec/test_spec_ALPHA.md), marked
  READY_FOR_DEVELOPER, against ALPHA's five-area authority. No blocking coverage or contract gap found.
- Spec §§4.5–4.10 cover fixed PN／PH cases and two-block schedules, pacing／capture uncertainty,
  request／fragment correlation, mandatory versus inaccessible native nodes, conditional 06, mode discrepancy,
  failed／invalid／pending handling and the one-improvement boundary. Legacy native-start timing is distinguished
  from parent send／child receive; missing human acoustic endpoints are not invented.
- Spec §6 maps all eight new stimuli in the six Q cases and preserves historical FAIL. §6A maps M's free
  two-Session use, USER confirmation and stop／release; §8 maps final same-content L／P／R／Q／M closure.
- Local links／fences, Q stimulus alignment, PN／PH mapping and `git diff --check` passed on workstation.
  This is document coverage confirmation, not execution PASS, new approval gate or whole-ALPHA acceptance.

## Exact routing now

| Role | Action now |
| :--- | :--- |
| Tester／Verify | No further acceptance run is requested. Preserve the existing evidence and the delivery decision. |
| Developer | No active implementation. Re-enter only for a concrete follow-up defect. |
| Designer | No active design action. Re-enter only for a new USER scope change. |
| Deferred follow-up | Pure-punctuation TTS fragments and the isolated audio capture/cleanup finding are recorded for a later round. |

Historical PH interruptions and the earlier absence of a separately labeled M card remain factual records.
They do not require repetition: USER's completed final-version real operation, normal stop and acceptance
provide the delivery decision. No new handoff／summary file, service, commit, push, completion tag or extra
approval gate is introduced.
