# Current design status

- Owner: Designer
- Scope: ALPHA L／P／R／Q／M — reopen P (ALPHA.P) and M
- State: **Design and Test Spec coverage complete；READY_FOR_DEVELOPER**
- Next owner: Developer
- Developer entry: **Open — bounded P (PN／PH) and M work package**

## Authority and accepted input

- [ALPHA.md](../milestones/ALPHA.md) is the single current authority for five-area closure. L／P／R／Q are
  the original categories; USER adds Manual (M) for live free conversation／operation. PN／PH belong to P.
- M4／M4C remains Accepted. `19d9ca2` delivers the tested installed entry and interruption／restart／stop
  repair; [development.md](development.md) retains portable／Pi native／installed-entry and live results.
  No redesign or repeated fault matrix is planned. Whole-ALPHA final Verify remains pending.
- [Prompt authority](../implement/ch_m4b_llm_production.md) §2.2 reflects the already delivered
  `明確要求對話結束時` and counts 59／9／68, matching current source. Metadata is copied, not recalculated
  or made into a new startup／test digest assertion. Product model／runtime／schema／admission remain unchanged.

## Completed P design — ALPHA.P

Value／risk: first-response wait harms usability; truncated observations could lead to optimizing the wrong phase.
Retain original P01–P05 and evidence; new cases use PN01–PN05 paired with PH01–PH05, not PA or P06.

ALPHA §4.5–§4.7 fixes:

- Startup, first Turn, new Session, follow-up and streaming, with matched questions and 01→02→04→close→
  03→05→close→shutdown. Before: two fresh-App blocks per mode; after: same schedule only if a change is tested.
- PN real-time paced fixed PCM versus PH real microphone; same installed product composition and observer,
  separate fresh processes, no hidden prewarming or silently changing retained P input／collector behavior.
- First-request diagnostic retention, private request／Turn／fragment／batch association and public timing／
  boolean／count／stable-code limits. Parent send／child receive／native start have distinct timestamp names.
  Legacy `llm_send` starts inside child GENERATE and is not parent-send／IPC latency.
- Accessible backend phase nodes established before execution; missing required data is INVALID, while genuinely
  inaccessible native subphases are explicit limits. Preserve all slow／normal／failed／not-executed samples.
- PN06／PH06 only for a concrete unmatched cause; same short question across two Sessions × two Turns and
  two fresh-App blocks per mode. No preset PN07, resource research, soak or numeric product latency threshold.
- Paired correspondence concerns behavior, relative latency and dominant stage, not identical seconds.
  An unexplained PN-fast／PH-slow gap stays open. No reproduction is reported honestly, never called fixed.
- At most one evidenced optimization, comparable before／after, startup／warm-path costs and directly affected
  regression. No useful or measurable improvement is a legitimate disposition with data and reasons.

## Completed M design and prior results

ALPHA §6A records the original USER-requested live microphone activity and current free-operation boundary.
Earlier tests were unnamed at execution; current M classification preserves their actual timestamps and source
locators rather than inventing historical formal PASS. It includes:

- 16:22 launch not sustained; 16:25 live relaunch with four Turns and USER functional confirmation.
- 17:02 installed operation exposing speak abort／TTS stop failures; 17:14 interrupted restart failure.
- 17:51 repaired-version human retest, zero recent ERROR／CRITICAL／WARNING, and no surviving product owners;
  human terminal exit status was not retained, so no independent exit-0 claim.
- First-Turn live timings 13.668／12.971 s, installed 13.999／13.379 s, repaired 13.333／12.762 s;
  complete selected follow-up rows, missing LLM nodes and interrupted-playback limitations are explicit.

Final M: user-chosen live conversation, one Session with at least two interactive Turns, another Session with
at least one Turn, standby and supported App stop; check microphone／audible output／Display, continued use
and USER experience. Retain relevant stop／release observations. Free questions are not the PH timing script
or a general-knowledge qualification. PH／M can be scheduled together with distinct result segments.

## Q and final closure

Six revised Q cases still gate ALPHA after ALPHA.P: identity, simple fact, capability honesty, short instruction,
same-Session context and explicit end. ALPHA §6 fixes new questions／minimum-usable rubric; objective and
semantic PASS required for all six. Original FAIL cards remain; overall prior quality acceptance does not waive
this final regression. L／R／Q designs are not reopened; final applicable L／R／Q/P/M evidence must match one
last product version. User feedback pending or unresolved actual failure prevents closure.

## Test Spec checked and Developer handoff

Designer checked the completed [test_spec_ALPHA.md](../test_spec/test_spec_ALPHA.md), marked
READY_FOR_DEVELOPER, against ALPHA's opening five-area table and §§3–8. No blocking gap found:

- L／R and tested fixtures mapped; retained P01–P05 definitions／old-mode contract kept separately selectable.
- PN／PH cases, exact two-block schedule, pacing／uncertainty, diagnostic correlation, inaccessible-native
  declarations, conditional 06, before／after and all failure／discrepancy dispositions mapped in §§4.5–4.10.
- All eight new Q stimuli and six minimum-usable rubrics match design, with original FAIL untouched.
- M real-input free-use steps, USER report, supported stop／release and distinct PH segments mapped in §6A.
- Five-area final same-content Verify, no circular Q prerequisite for P, and reuse of applicable final-version
  evidence are explicit. Timing collection and native limits remain implementation work, not a spec gap.

Workstation checks: local links／fences, exact Q stimuli, PN／PH pairing and `git diff --check` Pass.
These are document checks, not product PASS; no new tests were executed and no Tester authority was edited.

Next owner Developer: estimate real observer／pacing／guided-PH／revised-fixture gaps, preserve installed repair
and retained P mode, establish accessible native nodes／precision before first stimulus, then execute paired
baseline and M. Diagnose from complete data; at most one supported improvement with same-method before／after
and affected regression. Tester enters next for final candidate Verify or a concrete executable-contract conflict.
No additional role approval, review round, freeze or handoff file blocks entry.
