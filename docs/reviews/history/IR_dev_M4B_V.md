---
requestor: Developer
owner: Designer
status: Resolved
severity: Blocking
---

# IR_dev_M4B_V — merge PM, PR and PH into one Pi verification stage

- Date: 2026-09-13
- Scope: M4B Pi product verification, memory-threshold estimation and human semantic review
- USER decision: PM, PR and PH are one test stage. The same completed run verifies product behavior,
  records the human result and produces the memory-threshold estimate. It must not be repeated as a
  second release run. Threshold values may be adopted by a later design revision and tested through
  the normal `Design → Test Spec → Developer → Verify` flow.
- USER evidence disposition: every previously executed PM, PR or PH run is obsolete. Its output,
  partial output, cards, release profile and threshold estimate must be removed from active target
  and evidence roots and must not seed, satisfy, replay or otherwise influence the new combined test.
- Implementation status: blocked pending Designer authority revision and the resulting Tester mapping;
  this review authorizes no runner or product-code change.

## Superseded Pi-run cleanup

Developer inspected the active Pi target before removal. Six `user-pm-*` directories contained four
Blocked results and two interrupted runs without a terminal status file; one `user-voice-*` directory
contained only `DiagnosticComplete` with `pr_complete=false`, `ph_complete=false`, no replacement and
no new-Conversation answer. No independent PR or PH run existed, and no live process referenced these
directories. On USER instruction, all seven exact run directories were permanently removed from
`<PI_TARGET_ROOT>/`. A post-removal scan found no `user-pm-*`, `user-pr-*`,
`user-ph-*` or `user-voice-*` directory in that target root. This is input cleanup, not test evidence
or a new-stage PASS.

## Blocking B1 — the current three-stage contract duplicates one native scenario

### Basis and conflicting locations

The current product design and Test Spec split one target outcome across three matrix stages:

- Product §5.3 requires a measurement-only run to traverse a complete single-session series, derive
  `min_mem_available_speak_bytes` and `min_mem_available_generate_bytes`, freeze a release profile,
  and then start a separate clean release run.
- Product §11.2 requires the measurement harness to sample generation, replacement and session-close
  boundaries before rerunning the candidate under normal release-profile composition; the same Pi
  evidence section also requires real semantic, context, replacement, timing, resource and human rows.
- Test Spec §2.2 assigns separate `PM`, `PR` and `PH` matrices. Sections 5.2–5.4 consequently attach
  semantic/replacement evidence to `PR,PH`, while the earlier `PM` session already has to execute and
  observe the same real generation, Audio, replacement and cleanup path.

The only genuinely new input after measurement is the pair of derived memory thresholds. Repeating
the entire model/Audio/conversation/human scenario does not create an independent product boundary;
it duplicates target time, user interaction and evidence while introducing another opportunity for
the candidate, runtime, transcript or environment to differ.

### Expected versus current contract

**Expected by USER:** one exact-content Pi stage performs the real product scenario once. That run
automatically attests its inputs, verifies functional behavior, records the human rubric, captures the
complete resource series and calculates the two threshold estimates. There is no subsequent `PR` rerun
and no separate `PH` execution.

**Current:** `PM` captures a full lifecycle, `PR` repeats a clean normal-product lifecycle after profile
freeze, and `PH` is recorded as a third matrix disposition over PR answers. This makes the same scenario
serve as both prerequisite and repeated acceptance evidence.

### Impact

- PM completion cannot lead directly to one unambiguous M4B Pi disposition.
- Real model, Audio, context-fill, replacement and human work are repeated without a distinct USER
  requirement.
- Separate evidence roots/cards can disagree even though they purport to verify one product outcome.
- Runner design is encouraged to orchestrate stage transitions and replay behavior instead of executing
  one bounded, inspectable product verification.

## Required Designer revision

Replace `PM`, `PR` and `PH` with one canonical Pi verification matrix ID and one run disposition. `PV`
(`Pi product verification`) is the Developer-recommended label; Designer may select another single label,
but must not retain the three stages as aliases or sequential gates.

The single stage must:

1. Begin from a newly created empty private/public evidence root and new run ID. Automatically reject
   any pre-existing PM/PR/PH result, partial series, card, frozen profile or threshold as an input.
2. Bind one tracked-content digest, target identity, model/runtime/artifact identity, product/measurement
   profile identity and evidence root through automatic attestation. No role approval artifact is an input.
3. Execute the required real Audio + model scenario once, including the public semantic cases, genuine
   context-dependent turns, admission rejection, Conversation replacement, successful post-replacement
   turns and final cleanup.
4. Capture the unique-PID memory/resource series at the design-required lifecycle boundaries and retain
   the 512 MiB laboratory stop conditions. These observations support measurement validity; they do not
   create a second stage.
5. Record the human rubric against answers from that same run. Human failure fails the combined stage;
   human review must not trigger replay merely to obtain a separate `PH` result.
6. When the combined behavior, human, safety, identity and cleanup requirements are complete, derive the
   two threshold estimates with the existing deterministic §5.3 formula. Preserve raw private evidence,
   sanitized public results, exact digests and per-Test-ID assertion outcomes.
7. Report the threshold pair as an output of this stage, not as authority to silently mutate the current
   product profile and not as a reason to execute a second full native scenario.

Afterward, Designer may revise the release-profile authority to include those measured values. Tester then
maps only the newly introduced threshold behavior, Developer implements the authorized profile/config delta,
and the final bytes are verified through the ordinary project pipeline. That later delta must not be called
`PR`, must not repeat the already accepted semantic/human/context corpus by default, and must remain bounded
to behavior directly affected by the newly adopted threshold values.

## Direct authority and mapping impact

Designer should align at least:

- `docs/implement/ch_m4b_llm_production.md` §5.3 and §11.2: remove the mandatory separate clean
  release rerun and describe one combined Pi stage plus a later ordinary threshold-adoption delta.
- `docs/milestones/M4.md` and any active M4B milestone exit language: express one Pi result rather than
  sequential PM/PR/PH completion.
- `docs/status/current.md`: route the resulting focused Test Spec revision; do not claim execution PASS.

Designer should request Tester alignment of:

- `docs/test_spec/test_spec_M4B.md` §2.1–2.2 and §5: replace the three matrix rows and stage-specific
  result vocabulary with one combined matrix/run disposition.
- Map `M4B-PI-ATT-001`, `M4B-PI-SEM-001`, `M4B-PI-CONV-001`, `M4B-PI-MEM-001`,
  `M4B-PI-WAKE-001`, `M4B-PI-TIME-001` and `M4B-PI-RES-001` to the same run while retaining distinct
  Test IDs and assertion-level evidence.
- Remove separate PM-to-PR freeze/rerun and PH-execution requirements. Keep the deterministic formula,
  human rubric, privacy split, safety stops, identity checks and incomplete/fail semantics.

Designer should also authorize a focused Developer cleanup inventory so the replacement implementation
does not retain the obsolete stage machine by accident. The inventory must cover separate-PM bundle
validation/export, `pm_complete`/`pr_complete`/`ph_complete` result flags, PM-to-PR purpose markers,
separate release-rerun/PH launch paths and the temporary `run-pi-one-turn.sh`, `run-pi-two-turns.sh` and
`run-pi-voice.sh` diagnostic launchers. Shared measurement, automatic attestation, resource sampling,
replacement, privacy and human-rubric capabilities are retained and routed through the new single entry.
Historical documentation need not be rewritten, but no historical or WIP output is an active test input.

## Minimum acceptance

- Product design, milestone, current status and Test Spec describe exactly one Pi verification stage.
- All earlier PM/PR/PH outputs are absent from active Pi target/evidence roots before the new run; their
  digests, profiles, thresholds, transcripts and statuses are neither imported nor referenced.
- One real run yields one disposition with independently visible automated, human and measurement
  sub-results; none can be inferred from test-function counts or another run.
- The run executes semantic/context/replacement behavior once and uses the same answers for human review.
- The complete valid resource series yields the two threshold estimates using the unchanged formula;
  stopped, failed or incomplete evidence yields no estimate.
- No second clean release rerun, separate human execution, dual-role approval or freeze-approval artifact
  remains in the M4B acceptance path.
- No obsolete three-stage flag, validator, launcher or completion marker can select or validate the new
  combined path; retained shared mechanisms have focused regression coverage.
- The later adoption of measured threshold values is explicitly a new design/config delta with focused
  coverage and same-bytes Pi verification, not a renamed replay of PM/PR/PH.
- Existing offline, privacy, target/artifact identity, resource safety, cleanup and per-Test-ID evidence
  requirements remain intact.

Designer should respond in this review with `Revised` and the exact affected authority sections, or reject
the requested merge with a concrete conflict against a higher-priority USER requirement. Developer must not
invent the merged runner behavior before the design and Tester mapping are current.

## Designer response — Revised

Designer accepts Blocking B1. The requested merge matches the recorded USER decision and conflicts with no
higher-priority requirement. Authority is revised as follows:

- `docs/implement/ch_m4b_llm_production.md` §5.3 now makes threshold values `PV` evidence outputs, removes the
  separate release run, and routes later threshold adoption through a focused ordinary pipeline.
- Product §11.2 now defines one canonical `PV` run, one evidence root and one disposition with independently
  visible automated, human and measurement sub-results across the existing seven Pi Test IDs. Each Test ID now
  has an explicit itemized stimulus/evidence/assertion inventory; no group may pass by aggregate test counts.
- Per the latest USER scope, `M4B-PI-SEM-001` uses exactly three independent spoken cases: identity, practical
  English-learning advice and the reason for a seven-day week. Each starts fresh and semantic acceptance is
  human-only; no automated semantic judge, heuristic score or model-as-judge is authorized.
- The seven Test IDs are not chained. Each has an independent command, fresh setup, sub-run ID and evidence
  partition; only the top-level content/target identity and aggregate `PV` disposition are shared. A failed item
  reruns alone unless protected inputs change.
- `M4B-PI-CONV-001` is a separate automated script: one question/answer, context fill, rejection, replacement,
  explicit resubmission and a following successful generation, with no human speech or semantic scoring. Its fixed
  initial question is `請簡短介紹台灣。` and its explicit filler is `請再補充一點。`.
- M4B requires exact per-Test-ID verification commands over shared PV harness logic, not a new one-click shell or
  product launcher. Temporary diagnostic launchers are removed; M4C remains the sole product-startup owner.
- `M4B-PI-WAKE-001` is also fully automated: controlled wake stimuli exercise the actual production readiness
  path and the four ordering cases are independently rerunnable from traces, with no USER trigger or visual judgment.
- Only `M4B-PI-SEM-001` requires USER participation and it is the first implementation/verification priority.
  `M4B-PI-TIME-001` is a separate automated real Audio/ASR/model/TTS/Audio sub-run, and `M4B-PI-RES-001` is split
  into eight independently rerunnable offline/health/PID/close/recovery/forced-cleanup/shutdown/privacy cases.
- Product §11.2 also requires a new run ID and empty active evidence roots, rejects all earlier PM/PR/PH outputs as
  inputs, and authorizes the exact obsolete flags, validators, purpose markers and temporary launchers for removal.
- `docs/milestones/M4.md`, `docs/milestones/M4B_MVA.md`, `docs/status/design.md` and
  `docs/status/current.md` now remove sequential PM/PR/PH exit language and route focused mapping to Tester.
- `TR_spec_M4B_VIII` requests the exact Test Spec topology change. Developer entry remains closed until that
  mapping is current and includes focused cleanup coverage; this is a changed executable acceptance contract,
  not role approval or sign-off.

No runner implementation, Pi execution or `PV` PASS is claimed by this response.

## Designer resolution

The revised product authority and the focused Tester mapping are now complete. `TR_spec_M4B_VIII` resolved B1–B5
with independently executable Test IDs and case-level isolation for SEM, WAKE and RES. The implementation blocker
raised here is therefore removed, and Developer may implement the shared PV harness, obsolete-stage cleanup and
exact mapped commands. This resolution supplies no execution evidence or `PV PASS`.
