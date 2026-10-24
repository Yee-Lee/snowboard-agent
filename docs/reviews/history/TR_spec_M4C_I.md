---
requestor: Designer
owner: Tester
status: Resolved
---

# TR_spec_M4C_I — M4C Test Spec design-alignment review

Scope: [`test_spec_M4C.md`](../test_spec/test_spec_M4C.md) and its route from
[`test_spec_M4.md`](../test_spec/test_spec_M4.md), checked against
[`M4C.md`](../milestones/M4C.md), Accepted M4A／M4B／M4-ERR and the repository workflow.

Disposition: **Blocking findings present.** The routing update is correct and the spec covers the intended
feature areas, but Developer entry remains Closed until all findings below are revised and rechecked. This is
the Test Spec stage of the normal pipeline, not an additional approval or freeze gate.

## B1 — Verification identity and manual-result model contradict the same-bytes workflow

**Locations:** Test Spec lines 33–42, 51, 67–70, 225–235, 275, 311–315 and 497–516.

**Expected:** Before commit, every portable／Pi result binds the pending tracked bytes through an automatic
tracked-content digest, base SHA, pending-path set, harness/config/artifact digests and target facts. Only the
product-required USER audible-quality verdict is a human acceptance result. Script-only cases are decided by
automatic assertions and target facts; Developer inspection may aid development but is not a second manual gate.

**Actual:** Every record requires `candidate_sha`, although the verified content is intentionally uncommitted,
and every script-only PV requires `developer_review`. The finalizer therefore adds a role-based manual result not
present in M4C design and can either create a circular pre-commit SHA requirement or bind the wrong bytes.

**Preferred correction:** Replace `candidate_sha` with explicit `base_sha`, `tracked_content_sha256` and the
pending-path/content binding used by the manifest. Remove `developer_review` from result vocabulary, the PV
matrix, scenario terminals and finalizer. Retain `user_result` only for the exact audible-quality cases. Make
all other fields and cleanup/resource inventories automatically asserted. Run every PU／PI Test ID on CPython
3.11、3.12、3.13 in the declared workstation portable matrix; include a pure-Python import／collection case for
the controller/config modules so they cannot import Pi-only dependencies. Keep `PS` Linux／POSIX and CPython
3.13 only. M4C does not establish a Windows support target.

**Minimum recheck:** No result depends on an uncreated commit or role approval; changing any pending byte,
harness/config/artifact digest or target fact invalidates the result; USER quality is the only manual PASS input.

## B2 — Several portable oracles do not describe the adopted volume/B2 behavior

**Locations:** Test Spec lines 98, 104–105, 116–135 and 164–169.

**Expected / required corrections:**

- `volume_percent=25` is the M4C product config value, not the schema default; the schema default remains `100`.
- Exercise the future `VolumeControl` seam directly without creating or injecting an `adjustments/volume`
  runtime module. Prove production composition constructs exactly one decorator; do not require the decorator
  constructor to detect and reject an artificial double wrap unless design separately adopts that API behavior.
- `C01` distinguishes current queue depth `0` after drain from high-water `1` after one admission.
- With two fragments already queued, B2 makes one TTS request containing exact head+one-lookahead concatenation.
  `C02` must not permit two independent syntheses.
- Before terminal flush, admitted concatenation is a prefix of terminal normalized text; after flush it equals
  terminal text. `C06` must not add admitted text to terminal text. A mismatch is
  `not terminal_text.startswith(admitted_prefix)`, correcting the reversed `C07` stimulus.
- Fix `C18` to native generation failure → `TTS_GENERATION_FAILED + REBUILD_REQUIRED +
  backend.action.speak.tts`; fix `C19` to watchdog expiry without terminal／cleanup proof →
  `TTS_PROTOCOL_FAILED + REBUILD_REQUIRED + backend.action.speak.tts`. They are not
  `STREAMING_TERMINAL_FAILED`, which is reserved for a failed LLM terminal after partial fragment admission.
  Fix `C20` to a short-press cancellation whose cooperative TTS abort times out and whose bounded force-abort
  succeeds: no fault Fact, no normal Fact, `ForceAbortReport` proves the TTS owner stopped. A spontaneous adapter
  exception after partial PCM belongs to C18／C19, not the cancellation row.
- `O01` explicitly injects a zero-fragment `ReplaceableGenerationFailure` with complete typed request-terminal
  and engine-usable proof and requires the existing fixed R2 `REPLACE_NEXT` outcome. It must not allow
  `END_SESSION`. `O06` remains the distinct successful terminal-only B2 path.

**Impact:** Current alternatives allow incompatible implementations to Pass and misclassify rebuild-required
TTS failures as reusable streaming-terminal failures.

**Minimum recheck:** Each corrected row has one stimulus and one exact observable outcome; B2 batching,
prefix/equality direction and M4-ERR disposition are mutually consistent across CTRL／EXTRACT／OUTCOME.

## B3 — S09 does not guarantee the required eligible live stream or fixed quality sample

**Locations:** Test Spec lines 447–483 and traceability lines 524–527.

**Expected:** M4C-S09 proves on exact product bytes that at least one eligible real LLM turn emits safe text and
physical audible onset before terminal, and separately applies the fixed public B2 speech-quality sample/rubric.
Clock/acoustic uncertainty must be measured, bounded and smaller than the claimed onset-before-terminal lead.

**Actual:** The live input is the short `你是誰？`, which is not guaranteed to produce an eligible pre-terminal
fragment, while “fixed public speech sample” is unnamed and no controlled fragment/terminal trace is specified.
The spec asserts timestamp order without an acoustic calibration/error oracle.

**Exact correction:** Replace the S09 normal command with variant `LIVE_ELIGIBLE_L02` and public input
`天空為什麼是藍色的？`; if it produces no pre-terminal fragment, that subcase is Incomplete and must not switch
to A. Add variant `QUALITY_T02` on the same protected tuple using real Matcha／Audio and this exact controlled
trace:

```text
fragments = 「因為太陽光穿過大氣，」 + 「藍光被散射，」 + 「所以天空看起來是藍色的。」
terminal  = 「因為太陽光穿過大氣，藍光被散射，所以天空看起來是藍色的。」
```

For `QUALITY_T02`, USER answers exactly: understandable?; duplicated/missing/reordered content?; disruptive
artificial boundary that changes understanding? Pass requires yes／no／no. For `LIVE_ELIGIBLE_L02`, record the
clock mapping and measured acoustic uncertainty; require uncertainty `<= 50 ms` and
`llm_terminal - physical_audible_onset` strictly greater than that uncertainty. Keep model text/audio private and
publish only lengths, digests, timings and verdicts.

**Minimum recheck:** S09 enumerates the live eligible subcase, fixed mapping-quality subcase and all three fresh
interrupt variants, with exact expected counts and no A-mode escape.

## B4 — Pi stimuli and aggregation are not yet uniquely executable

**Locations:** Test Spec lines 317–337, 382–405, 427–445 and 497–516.

**Expected:** Every Pi Test ID fixes its stimulus, variant count, stable fault code/key, injection point and exact
terminal oracle. Runtime recovery fatal uses the Accepted M4-ERR `exit 4`. The finalizer proves every designated
variant exists; one aggregate card cannot hide a missing sub-run.

**Actual:** S03 permits timeout “or” `NO_SPEECH`; S06 leaves `<FAULT_CODE>` for runtime selection; S08 leaves
rebuild timeout “/” READY mismatch and accepts any nonzero exit. The finalizer says “nine designated sub-run
results” even though S04, S06 and S09 contain multiple mandatory fresh sub-runs.

**Exact correction:** Use the following fixed catalog:

| Test ID / variant | Exact stimulus and terminal oracle |
| :--- | :--- |
| `S03/TWO_TIMEOUTS` | Two consecutive real product Listen windows with no speech until the configured listen timeout; both outcomes must be `timeout` (not selectable `NO_SPEECH`); first plays the fixed retry, second ends without another retry |
| `S06/PERCEPTION_ASR_INFERENCE` | Fire `asr.inference.rejected` during active real ASR inference → `ASR_INFERENCE_FAILED + REBUILD_REQUIRED + backend.perception.listen.asr`; rebuild READY; final IDLE |
| `S06/THINK_LLM_CHILD_EXIT` | Fire `llm.child.exit` during active GENERATE → `LLM_BACKEND_FAILED + REBUILD_REQUIRED + backend.cognition.reasoner.llm`; rebuild READY; final IDLE |
| `S06/ACTION_TTS_CHILD_EXIT` | Fire `tts.child.exit` during active synthesize → `TTS_PROTOCOL_FAILED + REBUILD_REQUIRED + backend.action.speak.tts`; rebuild READY; final IDLE |
| `S08/LLM_READY_MISMATCH_FATAL` | Fire `llm.child.exit`, then make the replacement child return a READY `profile_id` different from `core-m4b-cognition-001`; no false IDLE/new Session; sanitized single root; exit exactly `4` |

The finalizer catalog is exactly 17 fresh sub-runs over nine aggregate Test IDs:

```text
S01: START_IDLE
S02: NORMAL_END
S03: TWO_TIMEOUTS
S04: PERCEPTION, THINK, ACTION
S05: APP_EXIT
S06: PERCEPTION_ASR_INFERENCE, THINK_LLM_CHILD_EXIT, ACTION_TTS_CHILD_EXIT
S07: DISPLAY_DEGRADE
S08: LLM_READY_MISMATCH_FATAL
S09: LIVE_ELIGIBLE_L02, QUALITY_T02, QUEUED, SYNTHESIZING, PLAYING
```

Reject a missing, duplicate, extra or mismatched variant. `user_result` is required for S02 and
`S09/QUALITY_T02`; S09 live eligibility and all other outcomes are automatic.

**Minimum recheck:** The command/catalog pair resolves every placeholder to one deterministic case, and the
finalizer cannot Pass until every required fresh partition and variant is present on the unchanged protected tuple.

## B5 — Accepted input provenance is incorrect

**Location:** Test Spec lines 7–12.

**Expected:** M4A remains Accepted at `6c3ba95455dc5c2a152aa230b8ae5915887fe6a9`; M4B is Accepted at
`f87cfa50b9c9415430973076a59c6b1961228090`; M4-ERR is Accepted at `f572915d0b0d5c52067e9100c5b022e57aefe506`.

**Actual:** M4A is attributed to the M4B commit `f87cfa50...`, which can bind regression provenance to the wrong
accepted baseline.

**Preferred correction / minimum recheck:** Correct the M4A SHA and verify all three identities against their
current authorities; retain the M4C-SS implementation/report source and binding commit without treating either
POC commit as Core product PASS evidence.

## Non-blocking cleanup folded into the revision

- In S04 PERCEPTION, describe short-press interrupt convergence rather than saying it is necessarily “during
  ERROR”; interrupt is not a fabricated system fault.
- For partial S16_LE, make fail-closed/no-partial-write the product oracle. An internal exception class may vary
  unless design explicitly makes it public.
- Replace import-only affected-test discovery with the actual candidate diff plus the accepted regression/Test ID
  inventory so indirect callers cannot disappear from `M4C-REG-001`.

## Tester response

Revise the existing `test_spec_M4C.md` and set this review to `Revised`. Do not create a replacement spec, ACK or
summary. Designer recheck will cover only B1–B5, their direct traceability/finalizer effects and regressions.

Before returning, run this one-pass checklist:

1. accepted SHAs are M4A `6c3ba954...`, M4B `f87cfa50...`, M4-ERR `f572915d...`;
2. no `candidate_sha`, `developer_review`, Developer human-result column or manual finalizer prerequisite remains;
3. PU／PI declare all three Python minors and a portable import／collection case with Pi-only dependencies absent;
4. V03／V09／V10, C01／C02／C06／C07／C18–C20 and O01 have the exact corrections in B2;
5. S09 contains exactly the five named variants, T02 trace, three USER questions and acoustic uncertainty oracle;
6. S03／S06／S08 use the exact catalog in B4 and finalizer requires exactly 17 fresh sub-runs;
7. traceability and command examples use the same variant names/counts, with no placeholder, slash-choice or
   “or equivalent” acceptance wording; and
8. `git diff --check` passes, then set only this review's `status` to `Revised` and return it to Designer.

## Designer recheck — round 1

Disposition: **Rejected／two bounded corrections remain.** B1, B3, B4's fixed catalog and B5 now match the
requested contract. B2 retains one directly identified defect, and the revised finalizer introduces one
contradiction that did not exist in the returned draft. Make only the following corrections; do not reopen the
rows already found conforming.

### R1 — Withdrawn: Windows is not an M4C target

M4C and its accepted M4A／M4B／M4-ERR inputs do not define Windows as a supported or required verification
platform. “Portable” requires controller/config collection without Pi-native dependencies; it does not authorize
Designer to add a Windows CI gate. The prior Windows-specific recheck requirement is withdrawn and is not
Blocking.

**Exact cleanup:** Rename G04 from “Windows-safe import and collection” to “portable import and collection” and
execute it on the PU／PI platforms already declared in §2.2, on CPython 3.11, 3.12 and 3.13, with Pi-native
dependencies unavailable. No Windows runner or Windows compatibility claim is required.

### R2 — B2 C18 retains prohibited alternative acceptance wording

**Evidence:** C18 still says “`TTSGenerationError` or equivalent”, although checklist item 7 requires no
“or equivalent” acceptance wording and the row must have one fixed stimulus.

**Exact correction:** Make the C18 stimulus exactly: the TTS adapter raises `TTSGenerationError` during native
generation after the Speak operation is active. Keep the existing exact outcome
`TTS_GENERATION_FAILED + REBUILD_REQUIRED + backend.action.speak.tts`; remove “or equivalent”.

### R3 — command examples and finalizer cannot identify one canonical 17-result set

**Evidence:** S04, S06 and S09 interrupt command blocks still use pipe-choice variant placeholders
(`<PERCEPTION|THINK|ACTION>`, `<PERCEPTION_ASR_INFERENCE|...>` and `<QUEUED|SYNTHESIZING|PLAYING>`), so the
commands do not themselves enumerate the catalog required by checklist item 7. More importantly, §5.13 says a
failed variant may be rerun under a new `sub_run_id` while unaffected results remain valid, but the old failed
attempt remains in the run and the same finalizer rejects every duplicate or extra variant. Following both rules
makes recovery from one failed attempt impossible.

**Exact correction:**

1. Replace the three pipe-choice command examples with an explicit command invocation for every named variant
   (three S04, three S06 and three S09 interrupt invocations). Binding-value placeholders such as
   `<PV_RUN_ID>` may remain; variant names may not be placeholders or choices.
2. Define immutable attempts separately from the designated result set. `finalize` must select exactly one
   automatically designated, non-superseded result for each of the 17 catalog entries; a retry atomically marks
   the previous same-tuple attempt superseded and cannot replace a result from a different protected tuple.
3. Reject duplicate **active designations**, extra catalog variants, missing variants, tuple mismatch, or any
   supersession chain that is ambiguous／cyclic. Superseded attempts remain evidence but do not count among the
   17 designated results.

### Return condition

After R2, R3 and the R1 wording cleanup, synchronize G04, the affected command blocks, §5.13 and any traceability wording;
run `git diff --check`; set this review back to `Revised`; return it to Designer. No additional response document
or review round is required.

## Designer final recheck

Disposition: **Resolved／0 Blocking.** R1 is correctly platform-neutral; R2 fixes C18 to the single
`TTSGenerationError` stimulus; R3 enumerates every S04／S06／S09 variant and defines exactly one active,
non-superseded designation for each of the 17 catalog entries. §5.13 is the controlling finalizer contract:
superseded same-tuple attempts remain evidence but do not count as duplicate active designations. B1–B5,
traceability and finalizer effects are therefore complete for Developer entry.
