# Current handoff

- Updated: 2026-09-15
- Writer: Designer only
- Current milestone: M4
- Current stage: M4B Pi `PV` Verify **Pass**; milestone commit remains unprepared
- Next owner: USER for milestone/commit disposition
- Developer entry: **Closed for product changes; any new protected bytes require a new Pi verification**
- Tester mapping: **Resolved by USER-authorized Test Spec corrections, including #1 ATT/#7 R01 evidence separation**
- Last independently portable-verified candidate: `9ffd6e17ad5504d53c7c18799ca4718f69988f7e`
  (historical portable PASS baseline; superseded by later protected-input changes)
- Last Git integration checkpoint: `688b2232b4bbd69f57ac712b1d82aba036179df0`
  (`origin/core`; historical specification-gate commit, not this uncommitted Pi-verified `PV` result)

## M4B Verify disposition — 2026-09-15

- Designer independently read the Pi public `PV-M4B-FINITE-03` final manifest: all seven Test IDs have
  `script_status=Pass/status=Pass/reason_codes=[]`, six applicable Developer reviews Pass and all three
  selected #2 USER verdicts Pass. The bound content/harness/profile tuple is
  `f6b9cfe2dcadeac675deb4811b2711e9c0c6a28d73e4985fc9ae321fb08c7545` /
  `cb79a96c06cdf427142fd9171523ce545e2b35951c59117d9d1dc8cf95988b33` /
  `8d957a4600fc172fd7dd7b285098710af0b753d7d1b697a21bd31611637b3f90`.
  Local protected-content and runner SHA match the Pi checkout and final manifest. On that same Pi checkout,
  the directly affected context/outcome/measurement/PV-runner tests passed 155/155 (exit 0).
- #1 ATT's duplicate syscall-capture sentence was an orphan Test Spec mapping and is removed: ATT proves its
  own offline flags/denial installation, while #7 R01 independently proves zero addressed external network
  attempts with its actual trace. Designer independently computed R08's Pi-local normalized native-answer SHA
  `f4d0c1207e1619f0e4c8864debb428420f36ff8b984607a510e99a133e6c79d6`, matching capture answer.
  No private text or canary was printed/exported.
- This is **M4B `PV` Verify Pass** within the present authority, not a claim of physical wake/display hardware
  Pass, native context replacement, nested-descendant killing in R06 or full product shutdown in R07. #4
  558/699 MiB estimates remain measurement outputs, not adopted release thresholds. No commit or push occurred;
  a milestone commit requires exact pending-byte reconciliation and explicit USER approval under the Git policy.

## Current disposition

- M4A remains Accepted and read-only unless a regression task explicitly names it.
- USER directed a clean rewrite of M4B design, production implementation and tests. The prior
  M4B-MVA-001/002 design and its action-envelope, fresh-Conversation, fake-prewarm and fixed 8/48/768
  recycle behavior are not current authority or compatibility targets.
- Designer-owned legacy M4B authority remains outside active design. The stable design path now contains the
  clean replacement cognition/product authority; it does not restore legacy compatibility.
- POC EFFICIENCY-003 and PROMPT-V2D2-004 remain valid redesign inputs. They are not themselves the
  product contract.
- USER removed the zero-swap-growth safety verdict: the POC `swap=0` environment cannot establish a useful
  active-zram growth test. Designer revised Product §5.3 and §11.2 to record swap deltas without treating growth
  alone as E1, laboratory stop or `R02-HEALTH` failure. The 512 MiB floor, OOM/kernel fault, throttling,
  temperature, sampler/identity and cleanup stops remain. USER explicitly authorized correction of the focused
  Test Spec `M02`/`M04-STOPS`/`R02-HEALTH` rows, now aligned with Product; prior `CONV-POC-01/02` remain
  Incomplete and are not `PV` credit.
- Generic EventBus, State Manager, Resource Manager, offline/privacy, process isolation and Level
  1/2/3 convergence remain accepted foundations; the rewrite does not reopen M4A or unrelated
  milestones.

## Gate status

`M4B-DESIGN-GATE-REASONER-BEHAVIOR` closed by USER and Designer on 2026-09-10. The blocking
architecture gate `M4B-FOUNDATION-ARCH-REVIEW` closed on 2026-09-10 after Architect revision,
Reviewer PASS and Designer confirmation in
[`AR_impl_M4B_III`](../reviews/history/AR_impl_M4B_III.md). The confirmed authority covers sequential
Conversation replacement, post-action rest/next-turn routing, pre-perception Conversation readiness
and the R1/R2/R3/E1 boundary. Developer entry remained closed while Designer prepared the resulting
foundation design.

Designer completed [`m4b_foundation_revision`](../implement/m4b_foundation_revision.md) on
2026-09-10. Tester supplied independent coverage and Designer closed the mapping gate after Round 3
PASS in [`TR_spec_M4B_V`](../reviews/history/TR_spec_M4B_V.md). The foundation implementation package
was opened to Developer; cognition/product work remains closed.

After Developer correction, Tester independently reported PASS and Designer resolved both
Blocking findings in [`CR_M4B_I`](../reviews/history/CR_M4B_I.md) on 2026-09-11. The foundation
candidate stage is closed: focused **68**, immutable baseline **99 retained / 0 missing**, strict
baseline **99 passed / 0 skipped**, and full repository **770 passed / 2 pre-existing optional
audio skips / 29 deselected**. This verified delta is the Foundation completion Candidate; its
formal SHA is supplied in the USER handoff after commit and push.

Designer completed the clean replacement cognition/product authority on 2026-09-12 in
[`ch_m4b_llm_production`](../implement/ch_m4b_llm_production.md), with direct mappings in Ch 2b/10 and the new
`snowboard.llm/3` protocol. The design fixes the listen-only V2D2 product profile, exact admission,
Conversation reuse/replacement, full outcome matrix, memory/profile staging and Audio+LLM evidence contract.
The focused planned-recovery ownership review [`AR_impl_M4B_IV`](../reviews/history/AR_impl_M4B_IV.md) is Resolved.
Architect confirmed the existing architecture already makes SM the sole authorization owner for session-end
planned-recovery timing; Designer aligned M4B §5.3 without changing `arch.md`.

Independent Reviewer returned PASS with no Blocking findings in
[`IR_review_M4B_III`](../reviews/history/IR_review_M4B_III.md). Designer adopted A1 by aligning the Ch 10 example
timeout and YAML indentation, adopted A2 by pinning two `spoken_length` examples in the coverage request, and
acknowledged A3 without a contract change. `M4B-DESIGN-REVIEW` is Closed.

Tester returned the new [`test_spec_M4B`](../test_spec/test_spec_M4B.md) and complete mapping. Designer independently
confirmed all 11/11 portable groups, 7/7 Pi/human evidence groups, 13 portable IDs, seven Pi/human IDs, exact prompt
hashes, `spoken_length` examples and the sorted/unique 99-node baseline. The resolved
[`TR_spec_M4B_VI`](../reviews/history/TR_spec_M4B_VI.md) closes `M4B-TEST-COVERAGE`; it contains no execution or
acceptance claim.

Developer returned work package [`CR_M4B_II`](../reviews/history/CR_M4B_II.md) **Revised** with WP-01–06 implemented,
including the authorized exact ticket-disposal path. USER authorized commit and push; the resulting provisional
portable candidate is exact SHA `9e005e48fe1582c901fcba3eb152747c92c43890` on `origin/core`. Designer independently confirmed that the
candidate contains the declared work-package scope, the local `origin/core` tracking ref resolves to the same full
SHA, and the candidate checkout was clean before this Designer-only status update. Developer Pi/Linux runs are
diagnostics only and are not Tester evidence or acceptance.

At that stage, Tester portable entry opened for independent verification of that exact SHA. Candidate protected inputs are
immutable for this verification round: any source, test, dependency/lock, config-contract or candidate-runner change
requires an append-only fix commit and a new candidate. Native PM, product cards and human semantic/audio rows remain
Pending; this transition neither supplies dual-role target authorization nor claims a native, human or product PASS.

Developer opened Blocking [`IR_dev_M4B_IV`](../reviews/history/IR_dev_M4B_IV.md) after proving that the original MEASURED
state had no legal token-limit R1 continuation which both kept the Conversation and invalidated its ticket.
Designer confirmed the gap, rejected delayed next-MEASURE supersession, and revised product/protocol authority to
require exact `DISCARD_TICKET` / `TICKET_DISCARDED` proof before R1. The operation preserves generation, revision,
history and KV; disposal mismatch/failure is E1. This is a private protocol/adapter correction with no public
SM/Event/Fact/response or architecture change. Focused Tester request
[`TR_spec_M4B_VII`](../reviews/history/TR_spec_M4B_VII.md) is Resolved after Designer confirmed all 9/9 requested
requirements, retained all 13 portable Test IDs and found no Blocking coverage gap. Both reviews are Resolved;
their authorization is implemented in the Revised `CR_M4B_II` candidate. No Tester, native or product PASS is
claimed by this handoff.

Tester independently verified exact candidate `9ffd6e17ad5504d53c7c18799ca4718f69988f7e` on Pi/Linux
aarch64 with CPython 3.11.16, 3.12.14 and 3.13.15: each canonical run passed **1005** with zero
Fail/Error/Skip/XFail/XPASS. Matrix SHA-256 is
`2438944bc0ad64f48ae577ca3cd7c2e9ff1c0008174ab8d398459c8293c5fbdb`; profile and catalog
digests match approved authority. Exact-SHA runner regression passed 78/78 on every minor and the
B1/B2 negative paths fail closed. Designer found no design deviation or new high-risk regression,
resolved [`CR_M4B_II`](../reviews/history/CR_M4B_II.md), and froze protected inputs at this SHA for
the next gate. PM, PR, PH, native-model, product-card and human evidence remain Pending.

USER superseded the role-approval clauses in `test_spec_M4B.md` §5.4; approval files, reviewer identities,
timestamps and dual-role freeze records are not implementation requirements. Developer review
[`IR_dev_M4B_V`](../reviews/history/IR_dev_M4B_V.md) then recorded the newer USER decision that PM, PR and PH must be one
Pi product-verification stage rather than sequential gates. Designer accepted B1 and revised product §§5.3/11.2:
one `PV` stage aggregates independently executable Test IDs with visible automated, human and measurement
sub-results plus deterministic threshold estimates. There is no second release run or separate human stage. The
estimates do not silently mutate release authority; adopting them is a later focused normal-pipeline delta.
Tester mapping request [`TR_spec_M4B_VIII`](../reviews/history/TR_spec_M4B_VIII.md) was Resolved under the
then-current script-only authority. Designer confirmed three human-only semantic cases, six script-driven Test
IDs, independent Test-ID state/evidence, separate commands and single-case reruns for SEM/WAKE/RES. The later USER
requirement for Developer review of #1/#3–#7 supersedes only that mapping's result disposition; it does not reopen
the independent commands or case structure and makes no product-execution or `PV PASS` claim.

USER confirmed that replacing the POC JSON constraint with regex prevents the real LLM from answering normally.
Designer corrected product §§4.1/4.2/6/9/11 to the POC-delivered constrained-JSON `J` path:
`ResponseFormat.json(response_schema)`, raw-JSON decoding or direct already-decoded mapping validation, and exact
`text/end` semantics.
The product no longer fixes output member order or insignificant whitespace and no longer carries a GBNF/native-
regex identity. The prior `char+` response to the regex shortest path and its non-empty-for-both-end semantic
change are superseded; `end=true` again permits empty text. Prompt/model/sampling/profile ID and unrelated
lifecycle behavior are unchanged. Existing regex/GBNF/`char+` implementation, Test Spec rows and protected tuples
cannot satisfy the corrected authority.

A subsequent Designer provenance audit found that the first JSON correction was still not the POC implementation:
it invented a minified `oneOf/const/minLength` schema with digest `642a94...`. POC commit
`4f34226728bafba445aa736e5e8ba24c0e2a69cd` instead loaded the exact 352-byte
`semantic-output-v1.schema.json` artifact, digest
`796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9`, and passed the decoded mapping to
`ResponseFormat.json`. LiteRT-LM v0.16 rejected conditional keywords in the native schema, so `text/end`
relationships remained Python fail-closed validation. Designer §4.1, Ch 10, model spec and READY protocol now bind
that exact artifact locator and digest. The former Designer schema and all dependent evidence are superseded.

Every previously executed PM, PR or PH run is obsolete. Its complete or partial outputs, cards, profiles,
thresholds, transcripts, statuses and digests are not active evidence and cannot seed, satisfy or influence `PV`.
The new run uses a new run ID and newly empty private/public evidence roots; historical records remain history only.

## Ordered exits

1. **Complete:** Developer rewrite, append-only B1/B2 fixes, exact candidate
   `9ffd6e17ad5504d53c7c18799ca4718f69988f7e`, independent portable PASS and Designer alignment.
2. **Complete:** Designer accepted `IR_dev_M4B_V` B1 and replaced the three-stage PM/PR/PH contract with one `PV`
   stage plus a later focused threshold-adoption delta.
3. **Complete:** Tester mapped all seven independent Test IDs and case-level SEM/WAKE/RES reruns;
   `TR_spec_M4B_VIII` B1–B5 are Resolved with no execution or `PV PASS` claim.
4. **Superseded:** The regex/GBNF `char+` correction and `TR_spec_M4B_IX` mapping do not govern the corrected
   constrained-JSON path.
5. **Complete:** Designer restored POC constrained-JSON `J`, legal JSON lexical equivalence and POC `text/end`
   semantics; regex/GBNF are excluded from the current product profile.
6. **Complete:** Designer corrected `PV` authority: scripts evaluate all seven Test IDs; USER judges #2 answer
   meaning; Developer inspects every number/output for #1/#3/#5–#7, while #4 keeps complete raw evidence,
   automatic every-point audit and focused boundaries/extrema/anomaly/formula review.
7. **Complete for the review requirement only:** Tester defined the exact Developer-review command/record schema, generated complete inspection
   catalog and evidence binding, `NeedsDeveloperReview` transition, one per-Test-ID WAKE/RES review, stale-review
   invalidation and G07–G10 finalizer truth table; Designer confirmed alignment.
8. **Complete:** Tester revised P03/P09/A05 profile-ready and dependent identity rows to the exact 352-byte POC
   artifact, locator/digest and native/Python validation boundary. Designer independently confirmed the portable
   negative seam, raw/decoded terminal, S2/outcome, seven Pi Test IDs and the preserved review catalog/state/
   finalizer mapping; this is coverage only, not implementation or product PASS.
9. **Complete for authority/mapping only:** USER removed the tautological zero-swap-growth safety verdict.
   Designer corrected Product §5.3/§11.2, and USER-authorized Test Spec `M02`/Pi MEM `M04-STOPS`/Pi RES
   `R02-HEALTH` now omit that verdict while retaining telemetry, the 512 MiB floor and other health stops.
   Existing native JSON/schema and Developer-review mappings remain valid; no `PV` credit is supplied.
10. **Active:** Developer's affected resource/measurement/PV predicates now remove swap-growth-only stops;
    `R02-OOM` replaces the stale swap-specific Pass assertion and actual setup `SwapTotal` is captured.
    Focused workstation tests passed 133/133 and Developer reports focused Pi tests 167/167, but fresh same-bytes
    full `PV` evidence is still Pending. The latest #3 sub-run reached eight real model generations and stopped
    on valid `end=true` before context rejection; it remains Incomplete. The earlier classification as a
    model fault is withdrawn. Valid `end=true` is a normal model-owned
    terminal; the unproven requirement to continue long fills until 1024-token rejection was the upstream
    Test Spec/Product contract problem. Product §11.2 and USER-authorized Test Spec §5.3/§5.4 now require a
    finite native first/continue/normal-close lifecycle for independent #3/#4, and retain deterministic
    context/replacement checks in portable `M4B-CONV-001` on identical Pi bytes with controlled admission
    snapshots. Controlled model-`end=true` routing stays in portable `M4B-OUTCOME-001` `O06`/`O07`, not
    an untried native explicit-end Pass condition. Controlled evidence is not native natural-context credit.
    Old #3/#4 attempts remain Incomplete. First finite Pi diagnostic `PV-M4B-FINITE-01/CONV-01` #3 has script
    and Developer Pass after 410 fields/146 rows, two real `end=false` JSON turns with same child/generation,
    revision 0→1→2, second KV 112 and matching close/cleanup. Independent `MEM-01` #4 has 253 valid samples,
    finite estimates and script Pass, but Developer correctly withheld Pass because setup `SwapTotal` was missing
    from its private series. Current runner now captures exact setup `SwapTotal`/swappiness and start/end swap-used;
    protected bytes changed, so these diagnostics are not final same-digest credit. Fresh Pi #3/#4 and #4 review
    are pending. Corrected finite Pi diagnostic `PV-M4B-FINITE-02` #3 again has script plus Developer Pass;
    independent #4 has 270 complete samples, setup `SwapTotal=2,147,467,264` bytes/swappiness 60, finite
    estimates and script Pass, but recording review failed because its 3,635,477-byte inspection catalog exceeded
    the former 1 MiB read limit. Developer separated a 16 MiB catalog-only limit from 1 MiB binding/manifest;
    protected bytes changed, so `FINITE-02` is non-final. Designer found this 16 MiB limit still below a legal
    near-watchdog two-turn projection (~3,000 samples/~38.5 MiB catalog). Product/Test Spec now permit a
    compact #4 catalog after automatic every-point audit but do not require it: the existing full catalog and
    `derive_thresholds()` every-point validation are valid for the current 241-point `FINITE-03` series if its
    evidence/inputs/digests pass review. Do not modify the protected runner or repeat #4 measurement solely to
    change review format. Recorded
    `PV-M4B-ALIGNED-01` #1/#5/#6 have script and Developer
    Pass. #5 WAKE aggregate/review covered 1,612 fields and 573 rows across four Pi case captures and five
    public cards; the transient tool-capacity rejection was retried successfully on the same command. USER
    clarified #5 is controlled-wake **core product wiring** barrier evidence, not physical voice-wake sensor
    or physical Display hardware evidence. Product §11.2/Test Spec §5.5 now map MockGPIO for W01/W03,
    MockWakeWordInputSource for W02/W04 and optional MockDisplay as stimulus/observation endpoints while real
    ButtonInputSource, StateManager, Conversation control, AlsaAudioInput, WhisperCppASR,
    DisplayArbiter/StatusBar and both barriers remain mandatory. Test Spec now accepts the existing structured
    `production_path`/`display`/trace as W00 core-wiring description and clarifies W04's correct empty barriers;
    no protected runner rename/rerun is required solely for this wording. `FINITE-03` W02 original card was
    designated after the mapping correction; W03/W04 inspection/designation and #5 aggregation/review remain
    pending. Designer independently recomputed the current protected-content digest and runner SHA as
    `f6b9cfe2dcadeac675deb4811b2711e9c0c6a28d73e4985fc9ae321fb08c7545` and
    `cb79a96c06cdf427142fd9171523ce545e2b35951c59117d9d1dc8cf95988b33`, matching Developer's
    `FINITE-03` tuple. Old #5 Pass must not be described as physical wake/display hardware Pass. These
    results predate the new protected runner/metrics bytes and are development evidence only, not final
    same-content-digest `PV` credit; all seven IDs still require the normal same-bytes final Pi verification.

## Role routing now

| Role | Read now | Action now |
| :--- | :--- | :--- |
| Designer | this file and focused Product/Test Spec sections | M4B `PV` Verify Pass recorded; no active design correction |
| Architect | this file only | no active architecture action |
| Reviewer | this file only | no active review action |
| Tester | this file only | #1 ATT/#7 R01 and controlled-wake mappings synchronized; no additional gate |
| Developer | this file only | no active product change; any changed pending bytes return to Pi verification before commit |

Temporary legacy files are not normal background reading. Search them only when the USER or a new
review requests a specific historical statement, Test ID or SHA.

## Update rule

Designer only replaces this file when a gate, stage, entry state or next owner actually changes.
Progress details remain in the role-owned status file; no duplicate handoff or summary is created.
