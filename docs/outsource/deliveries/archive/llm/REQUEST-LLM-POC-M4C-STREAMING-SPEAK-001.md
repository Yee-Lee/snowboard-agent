# REQUEST-LLM-POC-M4C-STREAMING-SPEAK-001

- Date: 2026-09-17
- From: Core Designer; proposed owner: existing LLM POC team
- Status: `USER AUTHORIZED EXACT DELIVERY AFTER CORE COMMIT／PUSH — POC EXECUTION NOT AUTHORIZED`
- Work: M4C true streaming-speak feasibility, bounded prototype and fallback disposition
- Core decision gate: `M4C-SS`; must be Closed by Core Designer before M4C Test Spec
- Core baseline: `f87cfa50b9c9415430973076a59c6b1961228090`
- Reserved return ID: `DELIVERY-LLM-POC-M4C-STREAMING-SPEAK-001`
- Next exit: LLM POC returns the intake ACK defined in §5.1, including the exact baseline and any requested
  workstation/Pi operations; execution waits for separate applicable authority
- Authority: USER explicitly authorized Core's byte-identical cross-repository delivery on 2026-09-17 to
  the `poc_llm` worktree at `docs/pm_handoff/REQUEST-LLM-POC-M4C-STREAMING-SPEAK-001.md`,
  after this Core request is committed and pushed. Delivery does not authorize prototype execution,
  target-hardware access, reboot, network changes, artifact download, commit, push or publication in the POC
  repository

## 1. Required outcome and disposition

M4C intends to adopt true streaming-speak (`B`). The existing full-response path (`A`) is the control and
emergency fallback, not an equal-preference alternative. The POC must make a bounded good-faith attempt to make
`B` work with the selected M4 model/runtime and accepted Audio/TTS path, then return reproducible evidence for one
of these dispositions:

1. `B_RECOMMENDED`: adopt `B` in M4C design;
2. `A_FALLBACK_CRITICAL_FAILURE`: retain `A` only because every bounded `B` candidate met a critical failure rule
   in §8;
3. `UNSUPPORTED`: the frozen runtime or required interface exposes no usable pre-terminal fragment path; or
4. `INCONCLUSIVE`: required evidence is missing or invalid and one bounded supplement is needed.

An inconvenience, small implementation delta or unfamiliar API is not a reason to prefer `A`. Conversely, POC
self-PASS does not modify Core architecture, approve a public API, provide Test Spec evidence or accept M4C.
Core Designer owns the product design mapping and closes `M4C-SS`; POC completion or self-PASS does not close
that gate. Any proposal to retain `A` or change an architecture boundary is
returned with evidence for the responsible Core owner; the POC must not silently make that change.

## 2. Frozen authority and experiment baseline

### 2.1 Core behavior

The experiment must preserve these current boundaries from the Core baseline:

- `docs/arch.md` §2.8: one streaming-speak control is bound to one
  `(session_id, turn_id, correlation_id)`; fragments are operation data, not Facts, actions or turns;
- terminal `LLMResponse` remains the only cognition Fact and must validate the same speak intent;
- a normal `ActionCompleted(status=ok)` is not published before both terminal semantic validation and speak
  completion;
- invalid/failed terminal, intent mismatch, interrupt and shutdown cancel generation, queued text, TTS and
  playback without publishing normal success; and
- `docs/implement/ch_m4b_llm_production.md` §4.2 remains the `S2` source seam: each `SAFE_TEXT` fragment is
  non-empty, ordered, non-revisable, and the concatenation remains an exact prefix of terminal normalized text.

M4C has no barge-in: Listen/ASR is not active during TTS playback, and the experiment does not add voice
interruption. The short button is the only active-Session interruption input in scope.

Already audible speech is not rolled back and is not itself a failure. Cancellation is judged only on stopping
future generation, fragment admission, synthesis and playback within the measured bound, with no later success
Fact or cross-session leakage. Device-buffer tail after cancellation is reported, not described as recoverable
speech.

### 2.2 Product identity

Use the accepted M4B product identity without prompt, model, sampler or runtime tuning:

| Field | Frozen value |
| --- | --- |
| Core source input | `f87cfa50b9c9415430973076a59c6b1961228090` |
| Profile | `core-m4b-cognition-001` |
| Target | Raspberry Pi 5 4 GB; Debian 13 aarch64; CPU/4 |
| Python | CPython `3.13.5`; `cpython-313-aarch64-linux-gnu` |
| Runtime | LiteRT-LM API `0.16.0`; source commit `924e79c91542761242244e4f1651851f822e4cbb` |
| Runtime wheel SHA-256 | `5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00` |
| Native library SHA-256 | `9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4` |
| Model | `gemma-4-E2B-it.litertlm`; 2,588,147,712 bytes |
| Model SHA-256 | `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c` |
| Sampling | temperature `0.0`; top-p `1.0`; CPU threads `4`; output reserve `128` |
| Context / wire | `1024` tokens; `snowboard.llm/3` |
| System prompt SHA-256 | `872ae6b6418761b271cd6762c08eeaabe1f20d3a1c4aa72602a09eab1f1eb643` |
| Response-schema artifact | source commit `4f34226728bafba445aa736e5e8ba24c0e2a69cd` |
| Response-schema SHA-256 | `796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9` |
| Network | disabled before native import and throughout runtime lifetime |

Use the accepted M4A Matcha TTS, canonical 16 kHz mono S16_LE PCM and existing Audio output path. The intake ACK
must record the exact TTS/runtime/model/voice/Audio manifests and artifact digests actually present on the target.
Any mismatch, alternate model, alternate voice, network fallback or untracked binary stops before measurement.

The POC owner must identify its own starting full 40-character source SHA and a non-recursive tracked-surface
SHA-256 in the intake ACK. That identity becomes the experiment source baseline; a branch name or dirty tree is
not a baseline. Prototype changes remain in the POC repository and the returned execution SHA must be a descendant
of the ACK baseline. This identity check prevents testing the wrong bytes; it is not a role-signature gate.

## 3. Ownership and permitted prototype surface

The POC may determine the best fragment-to-TTS mapping inside its own bounded prototype. It may compare at most
two candidates drawn from:

- sequential calls to the existing `synthesize(text) -> AsyncIterator[bytes]` for ordered fragments;
- a POC-private wrapper/controller that accepts fragments and drives the existing TTS/Audio objects; or
- a POC-private session-style `open/feed/finish/cancel` experiment when evidence shows the first form is
  insufficient.

There is still one logical Core speak operation per turn. One operation may contain multiple private TTS calls;
it must not create multiple actions, Facts, turns, correlations or normal completion events. The POC must report
which mapping it used, its gaps/prosody/startup cost and whether a Core public-contract delta appears necessary.

The POC must not modify or claim authority over the accepted M4A `TTSAdapter`, `Speak`, `AudioOutput`, State
Manager, Session/Conversation lifecycle, M4B semantic validation or Core repository. A proposed Core API is a
return recommendation only; Core Designer will specify any adopted delta through
`Design → Test Spec → Developer → Verify`.

## 4. Prototype behavioral contract

The prototype must satisfy all of the following:

1. A turn starts at most one logical streaming-speak operation. The first eligible `SAFE_TEXT` may start it during
   THINK; later fragments enter the same operation in sequence order.
2. Empty, duplicate, revised, out-of-order or post-terminal fragments are rejected. The concatenation submitted
   to TTS must equal the terminal normalized speech text when terminal validation succeeds.
3. The bounded prototype queue holds at most two pending fragments and at most 256 UTF-8 bytes. A full queue
   applies backpressure to the fragment producer; it must not drop, merge silently, reorder or create an
   unbounded task/list.
4. The normal `S2` release boundary remains punctuation or 24 normalized codepoints. A TTS mapping may coalesce
   an available fragment with the next fragment only if it records the added delay and still preserves order and
   the queue bound. It may not rewrite spoken text.
5. Terminal success closes fragment admission, proves the exact-prefix/equality relation and finishes the one
   operation. Terminal semantic failure or prefix mismatch cancels it and produces no normal success.
6. Interrupt or shutdown closes admission immediately, cancels the active model request, pending fragments, TTS
   iterator/request and Audio playback, joins all owners, and prevents any late output from entering a new turn or
   session.
7. Speech already audible before cancellation is ignored for correctness. Evidence must still measure cancellation
   observation to final audible sample, list any queued/device-buffer tail, and prove that no new fragment begins
   afterward.
8. TTS error/timeout/abort cannot be translated into success. All normal, negative and cancelled cases finish with
   zero orphan child/process/thread/task/iterator, zero pending fragment and zero Audio device owner.

## 5. Fixed experiment

### 5.1 Intake and preflight

Before prototype execution, return an intake ACK containing:

- POC baseline SHA and tracked-surface digest;
- exact target, ABI, runtime, model, prompt/schema, TTS/voice and Audio identities;
- proposed candidate mapping(s), exact commands and expected case count;
- the acoustic-onset method, measured clock-mapping/error bound and fixed microphone/speaker placement;
- raw/private evidence root, sanitized return paths and digest method; and
- whether workstation preparation, Pi access, network change or reboot is required.

Do not begin cross-repository preparation or target work until the USER grants the corresponding authority. A
byte-identical copy of this request and its source/destination SHA-256 must be recorded when delivery is authorized.

### 5.2 Deterministic controller cases

Run these with frozen synthetic fragment/terminal traces before live-model A/B. They may use deterministic PCM,
but must exercise the candidate controller, real queue and the same cancellation ownership used by the Pi path.

| Case | Injection | Required observation |
| --- | --- | --- |
| `C01-ONE` | one fragment, matching terminal | one operation, exact text, one normal completion |
| `C02-MULTI` | two ordered fragments, matching terminal | no duplicate/missing/reordered text |
| `C03-BACKPRESSURE` | producer exceeds queue capacity | bounded wait; no drop, hidden merge or extra owner |
| `C04-INVALID-TERMINAL` | first fragment consumed, terminal invalid | stop future audio; no normal success |
| `C05-PREFIX-MISMATCH` | terminal does not match emitted prefix | cancel complete path; no normal success |
| `C06-POST-TERMINAL` | fragment after terminal | reject fragment; no second operation/completion |
| `C07-INTERRUPT` | interrupt while queued, synthesizing and playing | each injection point converges independently |
| `C08-SHUTDOWN` | shutdown while synthesizing and playing | bounded join and zero owner/leak |
| `C09-TTS-FAILURE` | TTS error, timeout and force-abort | no success; reusable or truthfully destroyed backend |
| `C10-LATE-OUTPUT` | cancelled old operation emits late callback | callback rejected; new session remains clean |

Each subcase starts from fresh controller state and retains its own evidence partition. A failure in one subcase
does not erase or rerun successful subcases.

### 5.3 TTS mapping screen

Screen at most two mapping candidates on Pi using the real accepted TTS and Audio path. Use these exact public
speech strings and the same frozen S2 fragment trace for both candidates:

| Trace | Ordered fragments | Terminal text |
| --- | --- | --- |
| `T01` | `我是雪板，` + `很高興為您服務！` | `我是雪板，很高興為您服務！` |
| `T02` | `因為太陽光穿過大氣，` + `藍光被散射，` + `所以天空看起來是藍色的。` | `因為太陽光穿過大氣，藍光被散射，所以天空看起來是藍色的。` |
| `T03` | `多聽多說，` + `找對話練習，` + `會很有幫助喔！` | `多聽多說，找對話練習，會很有幫助喔！` |

Run three repetitions per string/candidate in alternating candidate order. Record per-fragment TTS start, first
PCM, Audio first write, acoustic onset/end, inter-fragment acoustic gap, total completion and cancellation tail.
Human review uses only these fixed questions for each sample:

- Is every word understandable?
- Is any content duplicated, missing or reordered?
- Is there a disruptive artificial pause or boundary that changes understanding?

Any `yes` to the latter two questions or `no` to intelligibility fails that sample. Preserve the raw private audio
for audit and return a sanitized per-sample verdict plus audio digest. Select the lowest-complexity candidate with
all samples passing. If neither passes, return the quality critical failure; do not tune a third candidate.

### 5.4 Live A/B comparison

Compare full-response `A` with the selected streaming candidate `B` on the actual LLM→TTS→Audio path. Keep one
Engine loaded, use a fresh clean Conversation for every sample, wait five idle seconds between samples, and run
five paired repetitions per input in alternating order: `A1/B1`, `B2/A2`, `A3/B3`, `B4/A4`, `A5/B5`.

| Case | Exact public input | Purpose |
| --- | --- | --- |
| `L01-IDENTITY` | `你是誰？` | short first-turn answer |
| `L02-EXPLAIN` | `天空為什麼是藍色的？` | punctuation/longer answer |
| `L03-ADVICE` | `我應該怎麼加強英語口說能力呢？` | natural multi-fragment candidate |
| `L04-END` | `請結束對話。` | single explicit product end phrase; final speech followed by session end |

Do not retry or replace an answer to improve timing. Invalid, empty, early-end, failed and fallback results remain
in the denominator and are reported by category. If deterministic sampling nevertheless produces different A/B
terminal text, retain both samples, report the mismatch and exclude that pair only from paired acoustic-latency
aggregation; do not silently substitute a replay.

For every sample record, in one proven monotonic mapping:

```text
LLM send -> first SAFE_TEXT -> each fragment enqueue -> each TTS start ->
each first PCM -> each Audio first write -> first acoustic onset ->
LLM terminal -> terminal validation -> final acoustic sample -> operation terminal
```

Also record terminal-text digest and normalized length, fragment sequence/length/digest, queue high-water marks,
TTS request count, cancellation state, owner PSS/RSS/CPU/thread counts, combined unique-PID PSS, MemAvailable,
swap, temperature and throttling. Missing nodes are explicit nulls with a stable reason.

### 5.5 Live negative cases

Run each injection once against the selected `B` controller with real TTS/Audio. Use a fixed public text/fragment
trace where model corruption is injected so no prompt tuning or nondeterministic model failure is required:

- `N01`: invalid terminal after first fragment has become audible;
- `N02`: terminal-prefix mismatch after first fragment has become audible;
- `N03`: short-button interrupt while queued, during TTS and during playback;
- `N04`: application shutdown while queued and during playback;
- `N05`: queue saturation while TTS is slower than fragment arrival; and
- `N06`: TTS timeout followed by bounded abort/force-abort.

Judge only future-output stop, terminal status, ownership cleanup and cross-session isolation. Already audible text
before the injected cancellation is not a failure and does not require semantic rollback.

## 6. Measurement and evidence rules

`Audio first write` is an internal node, not audible onset. Acoustic onset/end must come from a fixed-position
microphone capture of the physical speaker with a documented mapping to the event clock. Freeze the onset detector,
ambient-noise check, microphone gain, distance, sample rate and calibration before the measured run. The measured
clock/onset uncertainty must be at most 50 ms; otherwise latency disposition is `INCONCLUSIVE`. Human inspection
may confirm detector placement and the fixed speech-quality rubric but must not move timestamps sample by sample.

For each A/B case report all samples plus median and range. Report these paired deltas without P95 or significance
claims:

- LLM send → first acoustic onset;
- first `SAFE_TEXT` → first acoustic onset;
- terminal validation → first acoustic onset;
- first acoustic onset → final acoustic sample; and
- cancellation observed → final acoustic sample for negative cases.

Raw prompts, model output, trace logs and audio stay in the approved private evidence location. The Git-safe return
contains only the public inputs above, normalized lengths, hashes, timings, resource facts, verdicts and neutral
private-bundle locator/digest. Do not place credentials, host paths, unrelated speech or private transcripts in
Git. Preserve incomplete/failed runs and report every expected case; no best-of filtering is allowed.

## 7. Safety, watchdogs and stopping rules

- Startup watchdog: 120 seconds; generation watchdog: 30 seconds; each experiment-mode watchdog: 1800 seconds.
- Use the Core cancellation bounds: cooperative `abort` gets 2 seconds per active operation; Speak/TTS
  `force_abort` gets 1 second and Reasoner/LLM `force_abort` gets 3 seconds. Timeout or missing termination proof
  follows the Core Level 3 failure path and is a `CONTROL_FAILURE`, not a successful cancellation.
- Before every case require `MemAvailable >= 512 MiB`; sample resource ownership at least 10 Hz during overlap.
- Stop the current mode on any swap increase, OOM/kernel fault, thermal throttling, temperature `>= 80 C`, target
  identity loss, sampler loss, duplicate/missing owner or failed cleanup.
- Cancel uses bounded cooperative cancel, then TERM, then KILL/process-group cleanup when the prior stage cannot
  prove convergence. Report which level was required; never translate forced destruction into normal success.
- Runtime network remains disabled. Reboot, network switching, target package/model replacement and new artifact
  download require separate operator/USER authority and are not implied by this request.
- No automatic retry. A harness/measurement defect may rerun only the affected case once, retaining both attempts
  and the reason. Product/quality failure is evidence, not a retry trigger.
- The budget is two mapping candidates, the fixed cases above and one bounded supplement requested by Core. No
  open-ended segmentation, prompt, model, voice, queue or threshold tuning is authorized.

## 8. Go/No-Go rules

Return `B_RECOMMENDED` when all controller and negative cases pass, one bounded mapping passes every fixed speech
sample, no safety stop occurs, and live `B` produces an acoustic onset earlier than paired `A` by more than the
measurement uncertainty in at least one eligible input without a later-than-uncertainty median regression in any
other eligible input. A small but real benefit is sufficient; `B` need not meet a new absolute response-time
ceiling in this POC.

Return `A_FALLBACK_CRITICAL_FAILURE` only after both allowed mapping candidates, where applicable, and only for one
or more of these reasons:

- `CONTROL_FAILURE`: duplicate/missing/reordered speech, extra action/completion, unbounded queue, late output,
  cross-session leakage or inability to converge cancellation/cleanup;
- `QUALITY_FAILURE`: neither bounded mapping passes the fixed intelligibility/content/boundary rubric;
- `RESOURCE_FAILURE`: `B` reproducibly triggers a §7 safety stop that `A` does not;
- `NO_MATERIAL_OVERLAP`: no eligible live input improves acoustic onset beyond measurement uncertainty, or `B`
  causes a systematic median onset regression; or
- `PUBLIC_CONTRACT_BLOCK`: evidence proves a safe implementation requires an M4A/Core public-contract change
  outside this POC, and neither allowed private mapping can satisfy the experiment.

Return `UNSUPPORTED` when the frozen runtime cannot expose any valid pre-terminal `SAFE_TEXT` on the eligible live
cases or the accepted artifact/interface cannot execute either bounded mapping. Name the exact missing API or
rejected feature; do not invent a new model encoding or substitute runtime.

Return `INCONCLUSIVE` for missing identity, excessive measurement uncertainty, insufficient eligible paired data
or evidence corruption. Core may request one focused supplement. `INCONCLUSIVE` does not silently select `A`, and
the supplement may not repeat unaffected cases or expand the candidate set.

## 9. Return package

Return exactly one `DELIVERY-LLM-POC-M4C-STREAMING-SPEAK-001` package containing:

1. disposition and concise recommendation;
2. POC baseline/execution full SHAs, tracked-surface digest and dirty-state proof;
3. exact target/runtime/model/prompt/schema/TTS/voice/Audio identities and artifact digests;
4. exact commands, case catalog, expected/executed counts and any retained rerun;
5. selected/rejected mapping descriptions and whether a Core public-contract delta is recommended;
6. controller, mapping-screen, live A/B and negative-case tables with every required metric/null reason;
7. speech-quality verdicts, acoustic method/calibration/error bound and cancellation-tail observations;
8. resource/safety series summary, watchdog outcomes and complete owner cleanup result;
9. sanitized evidence manifest plus raw private-bundle SHA-256 and neutral locator; and
10. failures, limitations, missing evidence and the exact scope of any requested bounded supplement.

There is no calendar deadline imposed by this request. If authorization, target access, identity or required
measurement hardware is unavailable, return `BLOCKED` with that fact instead of changing the experiment. The POC
owner does not approve `B`, change Core authority or claim M4C acceptance. Core Designer maps the result into the
M4C design, routes any actual architecture delta to its owner, and then hands the adopted design directly to Test
Spec under the normal product pipeline.
