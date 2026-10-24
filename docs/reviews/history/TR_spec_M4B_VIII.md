---
requestor: Designer
owner: Tester
status: Resolved
---

# TR_spec_M4B_VIII — map one Pi product-verification stage

- Date: 2026-09-13
- Scope: `test_spec_M4B.md` §§2.1–2.2 and §5
- Authority: `ch_m4b_llm_production.md` §§5.3/11.2 and revised `IR_dev_M4B_V`

## Request

Replace the `PM`, `PR` and `PH` matrices with one canonical `PV` (`Pi product verification`) run, one evidence
root and one disposition. They must not remain as aliases, sequential gates or separate executions.

Do not chain the Test IDs inside that stage. Define one independent command, fresh setup, sub-run ID and evidence
partition per Test ID, with automatic attestation repeated for each. No Test ID may consume another Test ID's
transcript, model state, resource series, threshold, card or completion flag. A failed/incomplete item is rerun by
itself under a new attempt ID; prior partial attempts remain diagnostic and are never merged. Completed sibling
results remain usable only while the protected content and common attested tuple are unchanged.

Specify one exact executable verification command per Test ID/case. Commands may invoke a shared PV harness, but
must not introduce an M4B one-click product launcher or replacement shell-launcher family; M4C owns that product
boundary. Each command resolves the locked deployment, automatically attests inputs, creates fresh evidence,
executes one bounded case, cleans up and prints its locator. It accepts no authorization file or
diagnostic/PM/PR/PH mode. Each semantic command opens exactly one microphone window and exits after one answer with
`NeedsHumanReview`; no semantic verdict is automatic. Every other Test ID has its own automated bounded command.

Only `M4B-PI-SEM-001` requires USER participation or human judgment. Prioritize its Test Spec mapping,
implementation and Pi verification before the six fully automated Test IDs so the human-dependent work is not
delayed. `M4B-PI-ATT-001` and `M4B-PI-CONV/MEM/WAKE/TIME/RES-001` must be executable and decided automatically.

Map all seven existing Pi Test IDs to that same run while preserving their distinct Test ID, case ID and
assertion-level results. The required mapping is:

1. **`M4B-PI-ATT-001`**
   - Require a new run ID and newly empty private/public evidence roots. Reject every earlier PM/PR/PH result,
     partial series, card, frozen profile, threshold, transcript, status and digest as a `PV` input.
   - Bind one tracked-content, harness, measurement-profile, target and evidence-root tuple across controller,
     child and final manifest by automatic technical attestation.
   - Check Pi model, OS/kernel, CPU/RAM, CPython 3.13.5, ABI/SOABI/MULTIARCH; model/runtime/wheel/native/artifact
     filenames, sizes and digests; deployment paths; licenses/notices; exact prompt/grammar/tokenizer/sampling/
     threads/context/protocol/offline profile fields; READY `pid == pgid`, no Conversation and no prewarm.
   - Dirty/unbound input, missing/extra/system-site artifact, field mismatch, alternate endpoint or fallback is Fail.

2. **`M4B-PI-SEM-001`**
   - Define exactly three independent spoken cases, each using a fresh Conversation, case ID and separate evidence:
     `S01-IDENTITY` = `你是誰？`; `S02-ENGLISH` = `想要英文進步應該怎麼做？`;
     `S03-SEVEN-DAYS` = `為什麼一個星期有七天？`.
   - Human-only acceptance checks respectively that the answer identifies 雪板, gives relevant/practical
     English-learning advice, and gives a coherent explanation of the seven-day week. A failed case is rerun alone.
     Do not add an automatic semantic judge, heuristic score or model-as-judge.
   - The runner records inputs, ASR transcript, constrained JSON, answers, run identity and evidence but assigns no
     semantic verdict. Keep content private and publish only case IDs, digests and the human result; do not record
     reviewer identity as approval metadata or replay the cases to obtain another result.

3. **`M4B-PI-CONV-001`**
   - Start a fresh Product Session with no state/evidence from `M4B-PI-SEM-001`. The script submits
     `請簡短介紹台灣。` through the real Reasoner/worker/model path and requires one structurally successful answer
     without judging its meaning. It then sends `請再補充一點。` as labelled new explicit turns until exact
     context-equation rejection. Record every revision/generation/token metric.
   - Require rejection before mutation/send, full application notice, action completion and three-part close proof
     before OPEN; preserve session identity, monotonic turn IDs, exactly one generation increment and no overlap.
   - Production performs no automatic replay. After new readiness, the harness issues a new explicit input event
     with the rejected test text, followed by one explicit normal test turn; both must reach successful generation
     on the clean Conversation. This requires no human speech or answer-semantic judgment. Private
     evidence proves old-context absence.

4. **`M4B-PI-MEM-001`**
   - Define a fresh, fully automated command with no microphone input, human judgment or evidence imported from
     another Test ID. Shared sampler code is allowed; shared state, series or disposition is not.
   - Use an automatically attested null-threshold measurement profile that normal AppConfig rejects; accept no
     role authorization/signature input.
   - Capture the complete unique-PID, MemTotal/MemAvailable, swap, temperature and throttling series at all
     Engine/Conversation/generation/action/Audio/replacement/close boundaries.
   - Enforce the 512 MiB floor and stop on swap growth, OOM/kernel fault, throttling, `>= 80 C`, duplicate/missing
     PID, sampler/identity loss or cleanup failure.
   - Only a complete valid series yields both threshold estimates from the unchanged integer formula. Record inputs,
     results and digests; do not mutate a profile or run a release replay.

5. **`M4B-PI-WAKE-001`**
   - Define a fully automated Pi command with no human trigger or judgment. Drive controlled GPIO/voice stimuli
     through the actual production wake/readiness path and correlate Display, microphone, ASR and OPEN with
     wake-ack and Conversation-ready barriers; pure mock-only execution cannot Pass.
   - Before both barriers require no audio pull, active listen/ASR, perception worker or Reasoner admission.
   - Define four independently rerunnable cases with fresh setup/evidence: `W01-OPEN-FIRST`, `W02-ACK-FIRST`,
     `W03-SLOW-OPEN` and `W04-INTERRUPT-OPEN`. Display adds no product Fact/state/turn/model content. Trace
     assertions determine Pass/Fail without a USER button press, wake-word utterance or visual inspection.

6. **`M4B-PI-TIME-001`**
   - Define a fresh, fully automated command with no human speech, judgment or imported evidence. A fixed audio
     fixture traverses the actual Audio input, ASR, Reasoner, real model, TTS and Audio output path; pure timestamp
     fakes cannot Pass.
   - Record the exact monotonic sequence from Conversation ready through ASR final, LLM send, first safe text,
     LLM terminal, TTS PCM ready and Audio first positive write for that turn.
   - Check nondecreasing order and cross-process clock mapping; require explicit null plus stable reason for every
     missing/inapplicable node. Do not introduce a latency ceiling or audible-onset claim.

7. **`M4B-PI-RES-001`**
   - Define eight independently executable automated cases with fresh setup/evidence and individual outcomes:
     - `R01-OFFLINE`: zero non-loopback network, downloader, telemetry, DNS or fallback attempt.
     - `R02-HEALTH`: zero swap growth, OOM/kernel fault, throttling or temperature-stop violation.
     - `R03-PID`: complete unique-PID ownership; no duplicate, missing owner or owner leak.
     - `R04-NORMAL-CLOSE`: bounded owner/descendant exit after normal close.
     - `R05-RECOVERY`: correct planned-recovery order, bounded old-child exit, matching new READY and usable
       following child/turn.
     - `R06-FORCED-CLEANUP`: forced PGID cleanup boundedly reaps every descendant.
     - `R07-SHUTDOWN`: final shutdown leaves no owner, child, waiter, task or resource handle.
     - `R08-PRIVACY`: zero private-canary/reversible-encoding hits across logs, public evidence, temporary paths,
       argv/environment and persisted files; raw evidence remains access-controlled and public locators opaque.

Remove the role-approval file, reviewer identity/timestamp, dual-role freeze, separate release rerun and separate
human execution. A stopped, failed or incomplete run yields no threshold estimate. A complete run reports one
disposition with independently visible automated, human and measurement sub-results. The estimates are outputs,
not release-profile authority.

Add focused coverage for the obsolete-stage cleanup inventory: separate-PM bundle validation/export,
`pm_complete`/`pr_complete`/`ph_complete` or equivalent flags, PM-to-PR purpose markers, separate release-rerun and
PH launch/validation paths, and temporary `run-pi-one-turn.sh`, `run-pi-two-turns.sh` and `run-pi-voice.sh`
launchers must not select, seed or validate `PV`. Retained shared attestation, sampling, replacement, privacy,
human-rubric and cleanup mechanisms remain covered through the single entry.

Record that later adoption of the estimates is a new focused `Design → Test Spec → Developer → Verify` delta. It
is not named `PR` and does not repeat the accepted semantic/human/context corpus by default; it verifies only
behavior directly affected by the adopted threshold values.

## Minimum acceptance

- §§2.1–2.2 and §5 use only `PV` for M4B Pi product verification.
- `PV` starts with a new run ID and empty active roots; all earlier PM/PR/PH outputs are absent and rejected as
  inputs rather than imported, referenced or replayed.
- All seven Test IDs share only the top-level content/target identity and aggregate disposition; each has an
  independent command, setup, sub-run ID, evidence partition and outcome.
- Failure or incompleteness reruns only that Test ID unless protected content or the common attested tuple changes.
- Only `M4B-PI-SEM-001` requires human input/judgment and it is delivered first; all other Test IDs are fully
  automated acceptance.
- One failed automated, human, safety, identity, cleanup or required resource sub-result fails `PV`.
- No approval artifact, PM-to-PR transition, release replay or separate PH execution remains.
- Formula, raw-series completeness, fail-closed checks, privacy split and per-Test-ID evidence remain intact.
- No obsolete three-stage flag, validator, purpose marker or launcher can select or validate the combined path.
- Every Test ID/case has one exact executable verification command through shared acceptance tooling; M4B adds no
  user-facing one-click launcher, and M4C remains the product-startup owner.
- The later threshold-adoption boundary is explicit and is not treated as acceptance already supplied by `PV`.

## Tester response — Revised (initial mapping)

- `git diff --check`: Pass.
- Pi Test IDs present: 7/7.
- No executable legacy Pi measurement/release/human matrix or rerun gate remains in the requested scope.
- No product test was executed; this is Test Spec mapping only and makes no `PV` PASS claim.
- Review ticket and Designer-owned status were not changed; other existing worktree changes were preserved.

Tester disposition: Revised; next owner Designer.

## Designer review — Rejected/Revised

The PM/PR/PH removal and 7/7 Test ID inventory are correct, but the executable mapping does not match the latest
USER-approved independent-test authority. All findings below are Blocking and share one correction round.

### B1 — Test IDs remain chained inside one execution

- **Actual:** §2.2 says one controller creates the run once and calls per-ID children “not separate executions.”
  §5 then feeds `M4B-PI-SEM-001` H08/H09 into `M4B-PI-CONV-001`, reuses captured public turns for
  `M4B-PI-TIME-001`, and makes `M4B-PI-MEM-001`/`M4B-PI-RES-001` observe the same run.
- **Expected:** each Test ID has its own exact command, fresh setup, sub-run ID, evidence partition, Product Session
  where applicable and outcome. Tests share only the protected content/target/artifact tuple and aggregate `PV`
  disposition. No transcript, state, event, series, card or completion flag crosses Test IDs. A failed item reruns
  alone while protected inputs remain unchanged.

### B2 — The semantic corpus and decision mechanism are stale

- **Actual:** §5.2 retains H01–H09, including the old grams/cannot-see/cannot-tool/end/personality/玉山 cases, and
  retains automated structural judgment as part of the semantic run.
- **Expected:** exactly three independent fresh-Conversation cases:
  `S01-IDENTITY` = `你是誰？`; `S02-ENGLISH` = `想要英文進步應該怎麼做？`;
  `S03-SEVEN-DAYS` = `為什麼一個星期有七天？`. Only these cases require USER participation. Their answer
  semantics are human-only; no automatic semantic judge, heuristic or model-as-judge is allowed. Recording failure
  or human failure reruns only that case.

### B3 — Conversation replacement still requires semantic/human input

- **Actual:** §5.3 starts from H08/H09 and requires a human repeat plus another human turn.
- **Expected:** a fresh fully automated script with no #2 state/evidence. It submits `請簡短介紹台灣。`, requires
  one structurally successful generation without semantic scoring, submits labelled `請再補充一點。` turns until
  exact context rejection, verifies cleanup/replacement, then explicitly resubmits the rejected test text and one
  normal test turn. No human speech or judgment is used.

### B4 — Automated Test IDs still reuse shared human/run evidence

- **Actual:** §5.4 samples the same combined run and waits for human results; §5.5 does not state that all four wake
  cases are script-driven without USER action; §5.6 asserts over already captured public turns; §5.7 combines the
  approved resource cases into seven shared-run rows.
- **Expected:** #1 and #3–#7 are fully automated and independently executable. #4 uses its own scripted lifecycle
  and complete series; #5 has fresh `W01-OPEN-FIRST`, `W02-ACK-FIRST`, `W03-SLOW-OPEN`,
  `W04-INTERRUPT-OPEN` cases with no USER trigger; #6 uses a fresh fixed-audio real Audio/ASR/model/TTS/Audio
  sub-run; #7 has eight fresh cases: `R01-OFFLINE`, `R02-HEALTH`, `R03-PID`, `R04-NORMAL-CLOSE`,
  `R05-RECOVERY`, `R06-FORCED-CLEANUP`, `R07-SHUTDOWN`, `R08-PRIVACY`.

### B5 — Traceability still names superseded acceptance

- **Actual:** §6 still maps “signed measurement, formula/freeze, separate release rerun.” §7 still describes an
  exact-candidate/replacement entry rather than the revised tracked-content `PV` mapping state.
- **Expected:** §6 names automatic attestation, independent measurement/estimate evidence and no release rerun;
  §7 reports this mapping revision accurately without an execution or PASS claim.

### Required correction

Revise only `test_spec_M4B.md` §§2.1–2.2, §5, §6 Pi traceability and §7 disposition. Preserve the correct
automatic-attestation, empty-root, obsolete-output rejection, safety, privacy, formula and no-rerun work already
present. Return one complete `Revised` response with `git diff --check`; do not execute product tests. Prioritize
the #2 mapping, but complete all B1–B5 before returning to Designer.

## Tester response — Revised (B1–B5 correction)

Tester corrected B1–B5 in `docs/test_spec/test_spec_M4B.md` only at §§2.1–2.2, §5, the §6 Pi traceability table
and §7 disposition:

- **B1:** `PV` now aggregates seven independently executable Test IDs. Each has an exact command, fresh setup,
  unique sub-run ID, empty evidence partitions and independent outcome. Only the protected tuple and aggregate
  identity are shared; no transcript, state, event, series, card or completion flag crosses Test IDs. A failed
  item reruns alone without changing protected bytes.
- **B2:** `M4B-PI-SEM-001` now contains only `S01-IDENTITY`, `S02-ENGLISH` and `S03-SEVEN-DAYS`, each in a fresh
  Conversation. Only these cases use USER participation, and answer semantics use the USER verdict only. No
  structural semantic gate, heuristic or model-as-judge remains; recording/USER failure reruns only that case.
- **B3:** `M4B-PI-CONV-001` is a fresh fully automated script using the specified Taiwan introduction and labelled
  supplement turns through exact rejection, cleanup/replacement, explicit rejected-text resubmission and one
  following normal turn. It consumes no semantic/human input or evidence.
- **B4:** ATT and CONV/MEM/WAKE/TIME/RES are independent automated sub-runs. MEM owns its scripted lifecycle and
  raw series; WAKE has the four required fresh script-driven cases; TIME owns a fixed-audio real pipeline; RES has
  the eight required fresh cases. None waits for or validates another Test ID.
- **B5:** §6 now maps automatic attestation plus independent measurement/estimate evidence with no release rerun.
  Section 7 records the mapping-only Pending disposition, with no product execution or `PV` PASS claim.

`git diff --check` passes. No product test was executed. Developer entry remains closed pending Designer review.

## Designer re-review — Rejected/Revised (B1/B4 remain)

The correction closes B2, B3 and B5. B1 and B4 remain Blocking because two multi-case automated Test IDs are
still bundled behind one command, so the approved case-level isolation and rerun behavior is not executable.

### B1/B4 — WAKE and RES cases are still bundled

- **Actual — WAKE:** `test_spec_M4B.md` §5.5 provides one `M4B-PI-WAKE-001` command without a `case-id`, then
  executes W01–W04 as rows inside it. Although the prose says each row gets fresh setup, there is no exact command,
  sub-run/attempt identity or evidence partition by which one failed WAKE case can be executed again alone.
- **Actual — RES:** §5.7 likewise provides one command that explicitly “executes exactly eight cases.” Its failure
  rule reruns the complete RES attempt, not only R01–R08's failed case. This contradicts the approved independent
  case boundary and the USER instruction not to bundle tests.
- **Actual — production path:** §5.5 says the script injects GPIO/voice stimuli, but does not require them to
  traverse the actual production wake/readiness path or state that a pure mock-only path cannot Pass.
- **Actual — R06:** `R06-FORCED-CLEANUP` additionally requires a rebuilt child and following turn. That belongs to
  R05 recovery and is not part of the approved R06 criterion; it would add an unauthorized acceptance dependency.
- **Expected:** W01–W04 and R01–R08 each have an exact individually executable command with `case-id`, fresh setup,
  fresh case sub-run/attempt identity, empty private/public case partitions and an individual outcome. A case
  failure reruns only that case. A non-executing per-Test-ID aggregation step may combine the designated case cards;
  no command may run all WAKE or all RES cases as one product execution. WAKE must traverse the real production
  path, and a mock-only path must fail. R06 ends after proving bounded forced-PGID descendant cleanup; rebuild and
  following-turn usability remain R05-only.

### Required correction

Revise `test_spec_M4B.md` §2.1 rerun wording and §§5.5/5.7 so the case-level command, identity, partition, outcome
and rerun boundaries are executable. Align §7 with the remaining/resolved finding state. Preserve the accepted B2,
B3 and B5 corrections and all independent Test-ID, automatic-attestation, safety, privacy and no-rerun work. Return
one `Revised` response with `git diff --check`; do not execute product tests. Developer entry remains closed.

## Tester response — Revised (WAKE/RES case isolation)

Tester retained the accepted B2/B3/B5 mapping and corrected the remaining B1/B4 scope:

- `test_spec_M4B.md` §2.1 now defines each product-executing command as the smallest rerun unit. SEM, WAKE and RES
  aggregate designated case cards without product execution; only the failed case receives a fresh attempt.
- Section 5.5 now supplies four separate exact commands for `W01-OPEN-FIRST`, `W02-ACK-FIRST`,
  `W03-SLOW-OPEN` and `W04-INTERRUPT-OPEN`. Every command has its own case ID, sub-run/attempt identity, fresh
  setup and empty evidence partitions. Each traverses the actual production GPIO/voice wake and readiness path;
  direct state mutation, bypassed wiring or a pure mock-only path is Fail.
- Section 5.7 now supplies eight separate exact commands for `R01-OFFLINE` through `R08-PRIVACY` with the same
  case-level isolation and single-case rerun rule. The RES aggregate command launches no product behavior.
- `R06-FORCED-CLEANUP` now ends after bounded forced-PGID owner/descendant exit and convergence. Rebuild, new READY
  and following-turn usability remain solely in `R05-RECOVERY`.
- Section 7 records this correction as Revised pending Designer confirmation, with all evidence Pending and no
  product execution or `PV` PASS claim.

Mechanical checks found four independent WAKE commands and eight independent RES commands, each with `case-id`,
fresh setup and new case partitions. `git diff --check` passes. Developer entry remains closed.

## Designer confirmation — Resolved

Designer independently confirmed the remaining B1/B4 correction against product §11.2 and the prior review
findings. W01–W04 and R01–R08 now have separate exact product-executing commands, case/sub-run/attempt identities,
fresh empty evidence partitions, individual outcomes and single-case reruns. Their aggregation commands launch no
product behavior. WAKE traverses the actual production ingress/readiness path and rejects mock-only or bypassed
wiring. R06 ends at bounded forced-PGID cleanup; recovery/new-READY/following-turn assertions remain R05-only.

B1–B5 are resolved. The Test Spec mapping is accepted as implementation input. This closes only the specification
gate: no product test ran, no `PV` evidence exists and no `PV PASS` or M4B acceptance is claimed. Developer entry
may open for the mapped implementation delta, with #2 implemented and verified first.
