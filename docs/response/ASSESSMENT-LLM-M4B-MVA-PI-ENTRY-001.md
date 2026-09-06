# ASSESSMENT-LLM-M4B-MVA-PI-ENTRY-001 — Pi executable-path proof

- Date: 2026-09-06
- Work / baseline / gate: M4B-MVA / M4B-MVA-001 / M4B-MVA-POC
- Authorized starting SHA: `ac25aa104adcadb3b6274ca6f9c3d4154b4004ee`
- Authorized starting surface: `f774c8d018445b91bef4fa3b59bcc4f288d6699deb1fd09a2cb9baf8f2ddc461`
- State: `USER REVIEW COMPLETE / WP04 COMPLETE / READY FOR INTERNAL DELIVERY`
- Hardware result: `PASS` for the reviewed 23/23 machine run; manual semantics are 8 Pass / 4 Fail with the four findings accepted by the User as non-blocking follow-up work

## Authorization and delivery contribution

The User authorized direct Pi debugging, reboot-separated testing and the narrow artifact permission
remediation, while requiring network reachability to remain available between tests. Benchmark/profile
publication remains subject to User review. Work therefore used the clean canonical checkout only as the
accepted identity anchor and a separate private candidate worktree for source repair and rehearsal.

## Entry findings and repairs

Two append-only offline `prepare-install` attempts first established that the selected model and wheel
were unreadable by the `snowboard` service group, then that the runner assumed a flat
`runtime/litert_lm` tree while the accepted runtime uses a CPython virtual-environment
`site-packages/litert_lm` tree. The authorized permission repair changed only the two selected payloads'
group to `snowboard`; owner, mode `0440`, inode, size and content remained unchanged.

Direct Pi diagnosis then found and repaired four source-to-product integration defects:

1. Derive the authenticated runtime import root from the accepted native-library path, compare the
   wheel against that root, and give the child that exact `site-packages` path.
2. Preserve the content-addressed model `payload` as the authenticated object while presenting the
   exact same inode through a run-owned temporary `.litertlm` symlink required by LiteRT-LM.
3. Remove JSON Schema `if/then/else` from the native constrained-decoding schema because LiteRT-LM
   v0.16 LLGuidance rejects those keywords; retain the same `text/end` relation as fail-closed Python
   validation.
4. Align machine-evidence identity with the writer's required product-storage and cache-key fields,
   and allow ten seconds for native Engine shutdown before bounded TERM/KILL fallback.

The temporary model presentation is deleted with the run directory. No model, wheel, native binary,
raw prompt, raw answer or benchmark value is added to Git.

The Core task was executable after these repairs, but its frozen runner assumptions had not all been
validated against the selected Pi/runtime. The POC execution approach also amplified the delay by building
the long orchestration path before proving the smallest real-hardware chain. Future Pi work must first run
observable, bounded smoke steps in this order: authenticated import, model load, one constrained generation,
same-Conversation second turn, close/cleanup, then the full matrix. Each step should report immediately and
must not hide network reachability behind a long opaque timeout.

## Pi verification performed

The selected native Engine loaded successfully through the temporary `.litertlm` presentation. A real
public constrained generation returned the exact compact `text/end` shape. The full API proof then
confirmed selected-runtime import identity, tokenizer/census, two-turn Conversation reuse, cancellation,
fresh-session recovery and cleanup.

Regression execution on the Pi produced:

- MVA targeted suite: 66/66 passed.
- Pi storage-curation suite: 8/8 passed.
- Gate 2 suite: 84/84 passed with one documented platform skip.
- Repository Pi suite: 284 passed, one skipped and nine x86-only Gate 1 packet setup errors caused by
  the packet's deliberate `expected x86_64` guard on aarch64; a targeted traceback verified the guard.
- Private replacement-source rehearsal: all 23 machine case IDs completed once, including six distinct
  cold boots, ten same-boot replacement cases, three 20-session memory cycles and three recovery cases.
  The structural audit validated 1,847 schema-conforming samples, 60 complete memory sessions,
  checkpoint/final/summary binding and cleanup. Audit SHA-256:
  `2f225d6ff947043545537579d7ac7676b3683dac8ccefeaa247464bf77403361`.

Wi-Fi was restored after each required reboot and remained connected for the observable rehearsal.
Final postcheck found no MVA worker, zero swap use, no throttling and a clean accepted checkout. Raw
rehearsal records remain private outside Git.

## Executable-path disposition at entry

The executable path and every automated MVA case type have now been exercised on the target Pi; there
is no known missing runtime API or unexercised machine-case branch. This does not convert the rehearsal
into formal hardware PASS/FAIL because it ran from an uncommitted private candidate with networking up.

Those entry conditions were subsequently closed by replacement SHA
`7bb332670b5fdf45f05f07dd385bec94d914b4e1`, the governed `MVA-002` run, User benchmark review and
the private H01–H12 execution described below. Audible-onset parity remains `null` with
`NO_AUDIO_PROOF` unless an accepted M4a Audio identity and common timebase are supplied; it is not a
missing LLM machine case.

## Formal attempt 001 follow-up

Replacement SHA `4f34226728bafba445aa736e5e8ba24c0e2a69cd` passed offline `prepare-install`, but
`MVA-001-api-proof` stopped as INCONCLUSIVE before model load. The operator wrapper supplied the SHA-256
of the pretty-printed receipt file (`d1927c31…a213b`) where `verify_receipt` requires the runner-issued
canonical-JSON digest (`6524d545…e473`). The retained run has one `IDENTITY_DRIFT` sample and no child or
cleanup owner. It is not overwritten or relabeled. The replacement formal series is `MVA-002`, with a
separate ledger and run directories, and uses the canonical digest literally.

## Formal attempt 002 machine evidence

Replacement SHA `7bb332670b5fdf45f05f07dd385bec94d914b4e1` and surface
`61764d0737fcf374468621bd90d4765739d2f9b2b06e4314b1dbb73229f74e89` completed the governed
offline sequence. The runner reports PASS for all 23 ordered machine cases: API proof, six unique-boot
cold cases, ten same-boot replacement cases, three complete 20-session memory cycles and three recovery
cases. Wi-Fi was restored after every case.

The independent structural audit validated one identity, all 23 ledger/summary hashes, 1,822 schema-valid
checkpoint/final samples, 60 memory sessions, three complete steady windows, three recovery barriers and
cleanup for every row. Ledger SHA-256 is `7cd0c7c9…680e8`; audit SHA-256 is `6708ca21…65487`.
Postcheck found zero swap use, throttling `0x0`, no OOM/kernel fault, no owned worker and a clean exact
checkout. The private sanitized User-review aggregate is mode `0600` with SHA-256 `b7614ae1…9df05`.

On 2026-09-06 the User reviewed and accepted the API/session lifecycle, token/context interpretation,
recovery/cleanup, system-resource/thermal envelope, evidence identity/audit and published benchmark
interpretation. The reviewed machine disposition is therefore `PASS` for this LLM-only MVA scope. It is
not a production-profile selection or a Core gate release.

Audio remains the contract-permitted `llm_subsystem` scope with `audible_onset_ms: null` and
`missing_reason: NO_AUDIO_PROOF`, rather than an invented M4 end-to-end latency. The User explicitly
deferred this Audio integration test; it must not be run without renewed User approval. If later approved,
it must bind an accepted M4a Audio package and use one clock from user speech end through VAD/ASR,
LLM/Reasoner, TTS submission and first meaningful physical audible output.

## User-reviewed latency attribution and Core Step 6 adjustment

The User reviewed the timing interpretation below on 2026-09-06 and directed that the bottleneck
attribution and experience-oriented remedies be carried explicitly to Core. This review authorizes this
timing discussion; it does not silently select a production profile or alter the frozen MVA-002 evidence.

### Observed timing

The descriptive medians from the governed timing matrix are:

| Scenario | READY | First-turn TTFT | First-turn caller TTC | Second-turn caller TTC |
| --- | ---: | ---: | ---: | ---: |
| Cold / no prewarm | 3.192 s | 8.561 s | 20.625 s | 4.388 s |
| Cold / one disposable prewarm | 23.244 s | 1.689 s | 7.704 s | 4.376 s |
| Same-boot replacement / no prewarm | 0.394 s | 1.516 s | 7.519 s | 3.940 s |
| Same-boot replacement / one disposable prewarm | 7.032 s | 1.482 s | 7.421 s | 3.942 s |

For the cold/one-prewarm first turn, the 7.704-second caller TTC has the following measured attribution:

| Caller-path component | Median / derived duration | Interpretation |
| --- | ---: | --- |
| Create the product Conversation | 3.305 s | Occurs after the caller begins; disposable prewarm did not retain a product Conversation |
| Runtime call to first token | 1.689 s | Native TTFT after the Conversation already exists |
| First token to complete constrained output | 2.708 s | Derived as 4.397 s runtime TTC minus 1.689 s TTFT |
| IPC, parse/validation and POC projection residual | about 0.002 s | Derived caller remainder; not a material bottleneck in this sample |
| Total caller TTC | 7.704 s | Product Conversation open plus complete generation and POC boundary work |

Each of the three cold/one-prewarm first turns decoded 26 output tokens. Therefore the portion after the
first token was approximately 25 tokens in 2.708 seconds, or about 9.2 tokens/s. Those 26 tokens include
the constrained JSON structure, keys, punctuation, Boolean and response text; sanitized evidence does not
retain the raw answer, so the number of speakable Chinese characters must not be invented.

It is incorrect to subtract TTFT directly from caller TTC and label the resulting approximately six
seconds as post-first-token decode. Caller TTC begins before Conversation creation, whereas runtime TTFT
begins inside the later generation call. The actual measured first-token-to-complete-output interval is
about 2.7 seconds; the separate approximately 3.3-second Conversation open is the other major first-turn
cost. Same-session second turns avoid that open and complete at the caller in approximately 3.9–4.4 seconds.

The disposable prewarm comparison also requires careful interpretation. On a cold boot it moves expensive
first-inference work ahead of the request and improves request-time caller TTC, but READY itself grows from
3.192 to 23.244 seconds. If a user waits from process start, the observed time through complete LLM output
is approximately 23.817 seconds without prewarm and 30.948 seconds with it. Same-boot replacement prewarm
adds approximately 6.6 seconds to READY while improving first-turn caller TTC by only about 0.1 second.
Prewarm is therefore useful only when it can finish before interaction and must not be enabled blindly on
every replacement.

### API lifecycle and token interpretation

The selected-runtime API proof opened a Conversation with initial KV 0. Its first turn had 6 new-user
tokens, 147 rendered tokens, 148 runtime-reported incremental prefill tokens, 26 output tokens and a final
KV count of 174. The same Conversation's second turn had 4 new-user tokens, 27 rendered/incremental tokens,
32 output tokens and a final KV count of 233. This is the expected arithmetic: the first turn performs the
one-time system prompt, chat-template and user-message prefill; the second turn reuses that cached
history and processes only its new rendered turn. The approximately 148 tokens are therefore not repeated
growth on every turn.

After typed cancellation, a fresh API-proof session opened at KV 0 and reproduced the same
`0 → 174 → 233` trajectory, showing that cancelled/closed history was not inherited. The User accepted
this lifecycle proof while directing Core to hide the approximately 3.3-second Conversation open from the
completed-request critical path.

Each of all 60 memory-test sessions independently reproduced the same token trajectory: open KV 0, first
turn KV 174 and second turn KV 233, followed by Conversation close/discard. Session 20 therefore did not
contain the KV of sessions 1–19 and remained at 233/1024 before close. The memory soak tests process/Engine
resident retention across repeated Conversations; they are not a 20-turn context-capacity test.

This is a material coverage limit in the Core-frozen plan: no formal case kept one Conversation open for
20 sequential turns. The evidence can support repeated short-session create/use/close retention, but it
cannot support long-session KV growth, the usable number of turns before the 1024-token admission boundary,
long-session memory pressure or reclamation after a large live KV. The User directed Core to account for
this gap in product design and the next measurement surface.

The independent-session shape still has a valid narrow purpose: it prospectively checks the earlier
Gate 2B per-session resident-retention finding by repeatedly creating and closing Conversations without a
fixed-count recycle. The omission is the complementary long-live-Conversation case, not a reason to discard
the 60-session retention evidence.

The frozen limits of 32 new-user, 128 maximum-output and 1024 Engine-KV tokens are measurement-envelope
values, not production recommendations. The observed formal output stopped naturally at 26–32 tokens; the
runtime did not decode 128 tokens. Core must separately select response-length and context limits; within
the measured repeated two-turn scope, no memory-pressure evidence requires reducing KV capacity.

### User-directed long-Conversation supplemental

The User directly requested the missing complementary test without waiting for a Core surface revision:
three fresh child cycles, each with one Conversation and a fixed public script of up to 20 sequential
turns. `MVA-LONG-002` is an append-only supplemental diagnostic and does not alter the frozen MVA-002
surface or its 23-case ledger. Its private evidence SHA-256 is
`4b118b165d4bc9ca27569907c5ea675cce2003214bc25bac2fc9e3d1716e2cd5`; the executed runner SHA-256 is
`40286e814f0dd6d956df6044722ffc433362ebb9350b19dcb46cd3658666ce38`.

All three cycles completed 17 turns and received typed `CONTEXT_LIMIT` on attempted turn 18. KV grew from
167 after turn 1 to 910 after turn 17. With the frozen 128-token output reserve, `910 + 128` already exceeds
the 1024-token Engine envelope before counting the next rendered input, so the admission oracle correctly
blocked turn 18. This is a capacity-policy boundary, not a crash or missing runtime API. A fresh recovery
Conversation opened at KV 0 and completed at KV 167 in every cycle.

| Cycle | Completed / attempted limit | Owner PSS turn 1 → 17 | One second after long context discard | Fresh recovery + close |
| --- | --- | ---: | ---: | ---: |
| 1 | 17 / turn 18 | 1735.945 → 1809.086 MiB | 1788.555 MiB | 1830.211 MiB |
| 2 | 17 / turn 18 | 1735.883 → 1809.055 MiB | 1788.523 MiB | 1829.289 MiB |
| 3 | 17 / turn 18 | 1735.930 → 1809.055 MiB | 1788.523 MiB | 1827.367 MiB |

The live long context added approximately 73.1 MiB owner PSS in each cycle. Discarding it released about
20.5 MiB within one second, while later native high-water residency remained above the initial sample;
the measurement cannot attribute the retained pages to a leak. Minimum MemAvailable stayed above about
3100 MiB, swap remained zero, throttling was `0x0`, no OOM/kernel fault occurred and cleanup was
cooperative with all owners absent. This supplemental is enough to expose the practical 1024-KV boundary
and linear-looking live-context cost in the measured range, but it is not a long-duration soak.

Core should therefore make the output reserve adaptive to the requested response budget or explicitly
budget prompt/history/input/output together; a fixed 128-token reserve consumes usable context even for a
short-answer voice profile. It should also define summarization/truncation or controlled session rollover
before the admission boundary rather than letting turn count implicitly determine behavior.

## User-reviewed manual semantics (WP04)

The operator executed the twelve private held-out H01–H12 sessions once on the Pi. The private packet,
runner and raw prompt/answer evidence remain mode `0600` outside Git. Execution completed 12 sessions and
24 generations without retry; all Conversations closed and final cleanup was cooperative with no owners.
The raw evidence SHA-256 is `0a5b06cecee6f8deea5d744da1876c766d20966033b9f6c184033e05cd7b013c`.
Only schema-valid sanitized assessments are committed under
`poc_llm/evidence/m4b/mva-manual-001/`.

| Cases | Overall | User-reviewed interpretation |
| --- | --- | --- |
| H01, H02, H04, H07, H08, H09, H10, H12 | Pass | Identity, basic explanation, capability honesty, follow-up memory and applicable end intent met the rubric. |
| H03 | Fail; accepted non-blocking | An explicit close returned speech with `end=false`. Core must keep `end` as a signal, but independently close/reset an idle Conversation when the user sends no further request. |
| H05 | Fail; accepted non-blocking | The response was coherent and follow-up logic remained usable, but the density direction for freezing/melting water was factually reversed. |
| H06 | Fail; accepted non-blocking | The capability boundary was honest and negative end intent was correct, but the model over-refused a general-knowledge question as if direct perception were required. |
| H11 | Fail; accepted non-blocking | Knowledge and continuity were acceptable, but 78- and 70-token replies violated the global short-answer intent. Prompt design and/or a tighter response budget should enforce voice-appropriate brevity. |

The four observed failures remain failures; User acceptance changes their release severity, not the data.
The reviewed result is 8 Pass / 4 Fail / 0 Unclear, with all four failures assigned to post-POC quality or
controller hardening rather than blocking this measured runtime delivery. During this manual run, peak
owner PSS was 1902.852 MiB, minimum MemAvailable was 3091.797 MiB, maximum temperature was 53.2°C,
swap was zero, throttling was `0x0` and no OOM/kernel fault occurred.

### Responsibility boundary

Core's frozen measurement request specifies exact `text/end` constrained semantics, one active
Conversation per product session, controller costs in caller TTC, and disposal of the prewarm Conversation
before a separate product session is opened. The POC adapter implements that frozen surface with
`ResponseFormat.json`, accumulates all asynchronous output chunks, parses and validates the complete JSON,
then applies a deterministic Reasoner projection oracle. The oracle is not the product Reasoner, and the
POC private JSON RPC is not the Core production protocol.

Consequently, the current full-response gate is a property of the measured POC adapter and frozen
interface, not proof that Core must put JSON or complete-response buffering on the product's audible
critical path. MVA-002 proves the measured runtime/session/resource behavior, but its JSON-gated caller TTC
must not be adopted as an acceptable voice-experience profile without redesign.

### Memory interpretation

`owner PSS` is the proportional set size of the LLM-owned process tree: private resident pages plus the
processes' proportional share of shared resident pages. It is a better ownership estimate than summing RSS,
but it is neither model-file size nor whole-system used memory. It also must not be added directly to
`MemTotal - MemAvailable`, because reclaimable file cache and shared-page accounting make those metrics
different views of the same machine.

The global MVA-002 peak owner PSS was 1,981.592 MiB. It occurred in same-boot `replacement-O5` after one
prewarm, during second-turn/post-close sampling; at that point MemAvailable was approximately
2,875–2,881 MiB, swap was zero and temperature was at most 51.0°C. For comparison, observed owner-PSS
maxima were 1,763.373 MiB for same-boot replacement without prewarm and 1,981.592 MiB with prewarm. The
selected no-prewarm 60-session memory cycles peaked at 1,800.639 MiB. This indicates that prewarm leaves
roughly 0.2 GiB of additional resident ownership in these samples even after its disposable Conversation is
closed; it does not by itself prove that retaining the prewarm Conversation would add the same amount.

All three no-prewarm memory cycles completed 20 two-turn sessions. In the frozen session 11–20 steady
window, owner-PSS early-to-late median deltas were +0.125 MiB, +0.063 MiB and +11.406 MiB; corresponding
OLS slopes were +0.532, -1.106 and +2.368 MiB/session. Whole-system-used median deltas were +1.391 MiB,
0 MiB and -2.000 MiB. The third +11.406 MiB value is a difference between five-sample medians, not the
session-11-to-session-20 net change. Its session-terminal PSS was 1,783.154 MiB at session 11, temporarily
sat around 1,792.857–1,795.514 MiB for sessions 16–19, and returned to 1,783.576 MiB at session 20. The
endpoint delta was therefore only +0.422 MiB. The same owner PID remained active, and whole-system used
memory fell by 10.797 MiB between those endpoints.

The evidence supports a temporary native-residency/allocator or reclaim-accounting plateau, not a proven
11.4 MiB permanent accumulation. It does not contain allocator-level instrumentation, so the exact cause
must remain unassigned. The cycles do not show a consistent cross-cycle monotonic system leak, but twenty
sessions are still insufficient to declare long-duration memory stability or dismiss transient retained
allocation as harmless.

Across the complete formal matrix, minimum MemAvailable was 2,845.891 MiB; swap remained zero, no
OOM/kernel fault occurred and throttling remained `0x0`. The LLM-only POC therefore had ample measured
headroom, but this is not a full-product capacity conclusion because Accepted Audio processes were not in
the same run.

The User's reviewed disposition is that this evidence does not justify a session-count recycle policy:
session count was not observed to create progressive memory pressure. Core should instead define an
absolute owner-PSS upper bound together with a whole-system MemAvailable reserve and swap/OOM/thermal
health gates. A bound should require sustained or consecutive violations and hysteresis so a temporary
10–12 MiB plateau does not cause needless replacement. The exact product limits remain a Core Step 6
decision after Audio composition; this LLM-only run supplies the observed envelope, not permission to
invent the final threshold.

### Required Core efficiency work

Core Step 6 must address the following before selecting a product profile:

1. Hide Conversation creation from the completed-user-request critical path. Core should compare two
   prospective variants: (a) after disposable Engine prewarm, immediately create and hold a clean product
   Conversation; or (b) promote/reuse the warmed Conversation itself only if its prewarm history and KV can
   be made product-valid and held-out quality, session isolation, capacity, cancellation and memory checks
   show no material regression. The current public greeting prewarm leaves prompt/response history and must
   not be presumed clean merely to save 3.3 seconds. Conversation creation may alternatively overlap VAD/ASR.
   Measure Engine-ready and interaction-ready separately instead of conflating them.
2. Separate model semantic transport from evidence serialization. Keep `text/end` as internal semantics if
   desired, but evaluate a compact, stream-safe model frame, such as a validated continue/end prefix plus
   text, rather than requiring the model to finish a JSON object before downstream speech can begin.
3. Allow the LLM adapter to release validated speakable text incrementally. Batch safe text chunks at
   punctuation or bounded-size boundaries and feed them to TTS while later tokens are still decoding.
   Define backpressure, cancellation, interruption and invalid-terminal behavior so partial speech cannot
   create an unauthorized action or survive a dirty session.
4. Keep Reasoner ownership of action/end policy. Streaming must not let model text directly dispatch tools
   or bypass capability checks; Core must define the incremental LLM→Reasoner→TTS contract rather than
   treating the POC projection oracle as a production implementation.
5. Re-measure first speakable chunk, first TTS submission and physical audible onset on one accepted Audio
   timebase. Current MVA-002 has no accepted common-timebase Audio proof, so audible latency remains `null`
   and cannot be inferred from TTFT or complete-response TTC.
6. Do not recycle by an arbitrary completed-session count. Use owner-PSS and MemAvailable upper/lower bounds,
   sustained-pressure hysteresis, swap/OOM/thermal faults, dirty session state and failed cleanup as the
   replacement signals. Keep long-soak monitoring for future drift, but do not treat session number itself
   as memory pressure without evidence.
7. Adopt the supplemental long-session finding prospectively. `MVA-LONG-002` reached KV 910 after turn 17
   and correctly refused attempted turn 18 because the fixed 128-token output reserve would exceed the
   1024-token envelope. Core should explicitly budget history, new input and expected output; add
   summarization/truncation or controlled rollover before the limit; and avoid treating 20 independent
   two-turn sessions as long-context proof. Keep the supplemental separate from immutable MVA-002.
8. Harden semantics without hiding the manual failures. Tighten the short-answer prompt and output budget,
   improve general-knowledge behavior, and keep a controller-owned idle timeout/reset so a missed model
   `end=true` cannot retain a Conversation indefinitely. Re-run held-out quality after those product changes.

These changes create a new product/protocol surface. They require a revised Core baseline and prospective
Pi/Accepted-Audio validation; the existing append-only MVA-002 records must remain unchanged.
