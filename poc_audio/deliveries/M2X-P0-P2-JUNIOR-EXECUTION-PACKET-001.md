# M2X-P0-P2-JUNIOR-EXECUTION-PACKET-001

- **Status**: `USER-AUTHORIZED FOR JUNIOR P0-P2 / EXECUTION NOT STARTED`
- **Track**: M2X historical ASR experience reproduction
- **Authorized depth**: P0, P1 and P2 only
- **Execution target**: Raspberry Pi 5
- **Decision owner**: User
- **Evidence reviewer**: Audio POC Technical Lead
- **Milestone effect**: diagnostic input to M2B method planning; no M2 gate result
- **Microphone capture**: prohibited by this packet
- **Playback**: prohibited

## 1. Assignment and expected outcome

The junior assignee shall reconstruct the archived faster-whisper ASR slice, prove a
bounded offline wrapper lifecycle, and execute a fixed-audio reproduction plus
single-variable decoder ablations. The output is a recommendation about which methods
deserve a later formal M2B probe. It is not a candidate comparison, finalist selection,
hardware qualification, or production dependency decision.

The User authorizes the junior to implement and execute P0-P2 exactly as bounded by
this packet. No additional Core ACK is required. This authority does not include
microphone capture, playback, P3/P4, cloud access or scope expansion.

This packet implements the P0-P2 portion of
[`PLAN-AUDIO-M2X-HISTORICAL-ASR-REPRO-001`](PLAN-AUDIO-M2X-HISTORICAL-ASR-REPRO-001.md).
Where this packet is more specific, it controls junior execution. It does not authorize
P3 live capture or P4 paired microphone attribution.

## 2. Non-negotiable boundaries

The junior must:

- use only the persistent `audio` branch;
- treat `~/workspace/archive/chatbot/snowboard/` as read-only input;
- implement wrappers, tests and manifests only in this repository;
- use a fresh controlled work/evidence directory outside Git for every run;
- pin local model paths and reject aliases or downloads;
- isolate the execution network namespace and prove it has no route;
- keep raw transcript text, private paths, model files, wheels and large reports out
  of Git;
- never open a microphone, speaker, TTS, LLM, Google recognition or full chatbot path;
- preserve every FAIL and INCONCLUSIVE report under a unique path;
- stop on identity mismatch, network need, timeout, OOM, throttling or cleanup failure.

The junior must not:

- run or patch the archived chatbot in place;
- use `plughw:` or implicit resampling as an unexplained compatibility shortcut;
- tune a parameter after viewing output and reuse the same run as unbiased evidence;
- claim that faster-whisper beam behavior proves whisper.cpp beam behavior;
- change M2A/M2B status, shortlist, primary/fallback, milestone tags or Core contracts;
- commit controlled audio, transcripts, model snapshots, caches or secrets.

## 3. Role handoffs

### D0 — junior Developer

Work on the workstation. Implement the packet interface, manifests and tests. Do not
run a real model or hardware benchmark from a dirty worktree. Before handoff:

1. Run all local/fake tests.
2. Confirm `git diff --check` is clean.
3. Commit only the complete M2X implementation using the project commit convention.
4. Push `audio` and give the Tester the full 40-character candidate SHA.
5. Do not amend, squash, rebase or force-push that SHA after handoff.

### T0 — junior Tester

On the Pi, fetch and checkout the exact candidate SHA in detached state. Confirm
`git status --porcelain` is empty and run the environment pre-test. During P0-P2 the
Tester must not modify source, manifests, gates or parameter values. A required fix
returns to the Developer and produces a new appended candidate SHA.

### R0 — Technical Lead review

The Technical Lead reviews sanitized evidence and assigns the method recommendation.
The junior may report packet-level PASS, FAIL or INCONCLUSIVE against the acceptance
criteria below, but may not authorize an M2B probe or change the finalist proposal.

## 4. Required implementation interface

The junior may choose internal module structure, but shall provide these stable entry
points:

```text
poc_audio/tools/run_m2x_p0_preflight.sh
poc_audio/tools/run_m2x_p1_lifecycle.sh
poc_audio/tools/run_m2x_p2_fixed_audio.sh
```

Required tracked inputs:

```text
poc_audio/manifests/m2x_historical_asr_identity.json
poc_audio/manifests/m2x_p2_fixture_subset.json
poc_audio/schemas/m2x_preflight_report.schema.json
poc_audio/schemas/m2x_lifecycle_report.schema.json
poc_audio/schemas/m2x_fixed_audio_report.schema.json
```

Each shell entry point must:

1. use `set -euo pipefail`;
2. refuse a dirty repository;
3. require new work/output paths outside the repository;
4. enter an isolated user/network namespace before Python or native runtime load;
5. set offline environment flags and reject active interfaces/routes;
6. accept only explicit artifact/runtime/fixture paths;
7. validate every expected byte size and SHA-256 before use;
8. write controlled and sanitized reports separately;
9. terminate its worker process group on timeout/cancel/error;
10. verify zero child, thread, iterator, stream and audio-device owners at exit.

The persistent worker protocol must have bounded `READY`, `TRANSCRIBE`, `RESULT`,
`ERROR` and `QUIT/BYE` behavior. Transcript text may appear only in controlled output;
sanitized output contains lengths, edit counts and hypothesis hashes.

## 5. Historical identity to reconstruct

The reference code is the ASR portion of:

```text
~/workspace/archive/chatbot/snowboard/chat_with_snowboard.py
```

The starting observations are not accepted identities until P0 verifies them:

| Field | Starting observation |
| --- | --- |
| Engine | faster-whisper |
| Observed engine version | 1.2.1; original-run version unproven |
| Backend | CTranslate2 4.7.1 |
| Model | `Systran/faster-whisper-base` |
| Cached revision | `ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66` |
| Cached snapshot bytes | 145,217,532; per-file hashes required |
| Compute | CPU, CTranslate2 int8, two CPU threads |
| Historical decoder | language zh, beam size 3, prompt `中文對話` |
| Historical model VAD | enabled; exact pinned defaults required |
| Historical capture request | SpeechRecognition/PyAudio, 48 kHz |
| Historical ASR input | explicit 16 kHz mono float32 derived from int16 |

CTranslate2 int8 is not whisper.cpp Q8_0. Reports must use distinct identities and
must not merge metrics with the M2A/M2B whisper.cpp scorecards.

## 6. P0 — identity and offline preflight

### 6.1 Method

1. Record workstation and Pi full SHA, Pi model/RAM, OS, kernel, architecture, free
   disk, temperature, throttling and current audio-device owner count.
2. Record archive script byte size, SHA-256 and Git/file metadata when available.
   Recheck the hash at packet exit; any change is FAIL.
3. Resolve the cached model snapshot without a model alias. Produce a deterministic
   tree manifest sorted by relative path with file size and SHA-256 for every file.
4. Record model revision, tokenizer/config identity and all available license/notices.
5. Pin an offline runtime closure: Python, faster-whisper, CTranslate2 and every loaded
   dependency. Record wheel/source filename, source URL or immutable revision, size,
   SHA-256 and license. Installation must use an isolated virtualenv with
   `--no-index --no-deps` against the verified closure.
6. Resolve faster-whisper VAD defaults from the pinned source/runtime; unknown values
   remain unknown and block a claim of exact historical reproduction.
7. Prove model alias/network resolution is rejected before model load.
8. Validate the six P2 input identities and controlled references without reading
   transcript text into tracked output.
9. Write one controlled report and one sanitized report; do not load the model.

Artifact acquisition, if required, is a separate preparation step. It must finish and
be hashed before offline P0 begins. P0 itself may not download anything.

### 6.2 Acceptance

`PREFLIGHT_READY_NOT_EXECUTED` requires all of the following:

- exact model tree identity and immutable revision;
- exact installable runtime closure and licenses/notices;
- explicit decoder, prompt, VAD and PCM profile;
- clean exact Pi SHA and read-only unchanged archive;
- all six fixed inputs verified;
- alias/network refusal demonstrated;
- no model load, audio-device use or residual process;
- controlled/sanitized separation verified.

Use `INCONCLUSIVE` when the currently observed runtime can be pinned but the original
historical version/default cannot be proven. The report may recommend an
`OBSERVED_ENVIRONMENT_REPRODUCTION`, but it must not call it exact historical
reproduction. Artifact mismatch, missing provenance/license, network-only model
resolution or an unverified input blocks P2. A cleanup or archive mutation is `FAIL`
and blocks every later packet until reviewed.

## 7. P1 — deterministic lifecycle smoke

### 7.1 Method

P1 uses fake/synthetic 16 kHz mono PCM and does not load the real model. Exercise:

| Case | Required behavior |
| --- | --- |
| ready/success | one worker READY, one bounded result, clean BYE |
| declared input error | stable sanitized error code, worker remains controllable |
| item timeout | deadline fires, process group terminates |
| explicit cancel | bounded cancellation latency, process group terminates |
| forced abort | SIGTERM grace then SIGKILL, force-abort evidence retained |
| reopen | new worker succeeds after every prior terminal path |
| sample-rate drift | 48 kHz or non-mono fixture rejected before inference |
| network attempt | attempted route/download rejected and reported |

For each case record child PID/process group, exit code, wall time, cleanup counts and
device owners before/after. Tests must prove that transcript text cannot enter the
sanitized schema.

### 7.2 Acceptance

P1 is `PASS` only when every declared case produces the expected bounded result and
all cleanup counts are zero. Any orphan, unreleased device, uncontrolled transcript,
unbounded wait or failure to reopen is `FAIL` and blocks P2. Missing observability is
`INCONCLUSIVE`; do not infer cleanup from absence of console output.

## 8. P2 — fixed-audio reproduction and method ablation

### 8.1 Frozen six-item subset

The subset must be committed before any candidate output is viewed:

| Order | Fixture | Role |
| ---: | --- | --- |
| 1 | `vad-silence-011` | silence/false-emission observation |
| 2 | `asr-pause-027` | Taiwan Mandarin with retained pause |
| 3 | `asr-pause-038` | Mandarin/English code-switch |
| 4 | `asr-pause-042` | number/date correctness |
| 5 | `asr-pause-048` | product-term correctness |
| 6 | `common_voice_zh-TW_19057680.mp3` | external sanity and longest locked M2A item, 8.784 s |

P0 must resolve each controlled WAV, duration, PCM identity and SHA-256 against the
reviewed M1/M2 lock. The Common Voice identifier names its source MP3, but inference
uses only the already locked derived 16 kHz mono S16_LE WAV. If `vad-silence-011`
cannot be resolved against an authoritative controlled manifest, P2 stops as
`INCONCLUSIVE`; it is not replaced after results are seen.

### 8.2 Frozen profiles

All profiles use the same faster-whisper base snapshot, CPU int8, two CPU threads,
language zh, same six WAV bytes and same scoring. Only the named fields differ:

| Profile | Beam | Prompt | Model VAD | Purpose |
| --- | ---: | --- | --- | --- |
| `D0_RUNTIME_BASELINE` | 1 | none | false | minimal deterministic decoder reference |
| `D1_BEAM3_ONLY` | 3 | none | false | isolate beam-size effect |
| `D2_ZH_PROMPT_ONLY` | 1 | `中文對話` | false | isolate historical prompt effect |
| `D3_MODEL_VAD_ONLY` | 1 | none | true | isolate pinned faster-whisper VAD effect |
| `HISTORICAL_COMBINED` | 3 | `中文對話` | true | reproduce integrated historical profile; not causal evidence |

Temperature, condition-on-previous-text, word timestamps, worker count and every
unlisted option must be explicitly pinned and identical across profiles. The manifest
must contain the resolved VAD defaults rather than relying on library defaults.

### 8.3 Execution order

1. Confirm P0 ready and P1 pass evidence refers to the same candidate SHA.
2. Confirm performance governor, no throttling, no audio-device owner and no concurrent
   formal benchmark.
3. Execute profiles in the table order. Do not inspect transcripts between profiles.
4. For every profile/item perform one unscored warm-up and one scored inference.
5. Use one persistent worker per profile; unload and prove cleanup before the next.
6. Apply the frozen per-item timeout and row budget from the committed manifest.
7. After all profiles finish, write raw controlled output and one sanitized comparison.
8. Recheck archive hash, Pi temperature/throttling, network isolation and cleanup.

There is no microphone capture, historical 48 kHz frontend replay or
SpeechRecognition endpoint attribution in P2. Those remain P3/P4 questions.

### 8.4 Measurements

Record per item/profile:

- raw and normalized transcript in controlled evidence;
- transcript length/hash, edit distance and sentence diagnostic in sanitized evidence;
- silence false-emission character count;
- number/date exact value and product-term correctness;
- ASR-only latency, native inference time, CPU time, RTF and peak RSS;
- timeout/error code and worker cleanup.

Record aggregate CER, sentence correctness, category observations, latency p50/p95,
RTF p50/p95, peak RSS and model load time. Do not combine capture-to-final and ASR-only
latency. Do not average diagnostic profiles into the M2A scorecard.

### 8.5 Packet acceptance

P2 is `PASS` as a reproduction packet only when all five profiles complete the exact
six items under the frozen identities/bounds, raw/sanitized separation is clean, the
archive remains unchanged, and every worker cleans up. `PASS` means the experiment is
reproducible; it does not mean any profile has acceptable ASR quality.

P2 is `FAIL` on parameter drift, transcript leakage, network access, archive mutation,
unbounded execution or incomplete cleanup. P2 is `INCONCLUSIVE` on unresolved original
defaults, missing fixture/reference, artifact/runtime mismatch, OOM, timeout or thermal
throttling that prevents the complete matrix. Preserve all partial observations.

## 9. Method carry-forward review

For each of `BEAM3`, `ZH_PROMPT` and `MODEL_VAD`, return exactly one recommendation:

- `PROPOSE_EXACT_M2B_PROBE`
- `EXPERIENCE_ONLY`
- `NO_CARRY_FORWARD`
- `INCONCLUSIVE`

`PROPOSE_EXACT_M2B_PROBE` requires all of:

1. same input bytes and one-variable attribution against `D0_RUNTIME_BASELINE`;
2. at least one beneficial transcript/category observation relevant to the frozen
   M2 objectives;
3. no new numeric/entity false correction or silence hallucination in the six items;
4. bounded latency/RSS cost and complete cleanup;
5. a precise transferable hypothesis for a separate implementation, such as
   “test whisper.cpp base Q8 beam size 3 against greedy,” not a claim that the faster-
   whisper result already proves the target engine.

Use `EXPERIENCE_ONLY` when the effect depends on faster-whisper implementation or the
combined historical profile and cannot be cleanly transferred. Use
`NO_CARRY_FORWARD` when there is no beneficial output change, the method only adds
cost, or it introduces a safety regression. Use `INCONCLUSIVE` when identity, sample
size or evidence prevents attribution.

The six-item result only authorizes a proposal. A later M2B probe must be separately
reviewed, use the exact 20-item lock, change one variable, preserve raw/adjusted output
identity and produce its own delta table.

## 10. Evidence layout and handoff

Use a new controlled root, for example:

```text
/home/yee/.local/share/audio-poc/m2x/historical-asr-repro-001/
  artifacts/
  runtimes/
  work/<packet-id>-<full-sha>/
  evidence/<packet-id>-<full-sha>.controlled.json
  evidence/<packet-id>-<full-sha>.sanitized.json
```

Tracked review files, created only after Technical Lead review:

```text
poc_audio/evidence/diagnostic/M2X-001.md
poc_audio/deliveries/RESP-AUDIO-M2X-HISTORICAL-ASR-REPRO-001.md
```

The junior handoff must include:

- full implementation and tested Pi SHA;
- exact commands and UTC timestamps;
- P0/P1/P2 disposition and report SHA-256 values;
- artifact/model tree and runtime closure identities;
- selected fixture manifest identity;
- profile matrix and aggregate sanitized observations;
- every timeout/error/cleanup finding;
- controlled evidence paths and retention note;
- recommendation for beam, prompt and VAD using the four allowed labels;
- explicit statement that no capture or playback occurred.

## 11. Stop and escalation rules

Stop immediately and report the exact blocker when:

- a required archive/model/runtime/fixture identity cannot be fixed;
- runtime import/model load attempts network access;
- the Pi checkout is dirty or differs from the handed-off SHA;
- a controlled path would enter Git;
- a timeout cannot terminate the full process group;
- cleanup leaves a child/thread/stream/device owner;
- temperature throttling, OOM or disk pressure invalidates comparison;
- executing the packet would require microphone access or playback.

Do not download, relax a bound, substitute a fixture, alter a profile or rerun into the
same output path to hide a blocker. Record `INCONCLUSIVE` and return to the Technical
Lead. Three repeated instances of the same unresolved blocker should be reported for
formal blocked-status review; the junior must not self-authorize expanded scope.

## 12. Junior completion checklist

- [ ] Read the M2X plan, milestone index, active M2 document and workflow.
- [ ] Confirm no unrelated dirty changes are included in the candidate.
- [ ] Implement all three entry points, manifests, schemas and fake tests.
- [ ] Commit/push one exact candidate SHA and switch Developer to Tester role.
- [ ] Pi exact-SHA checkout, clean status and environment pre-test recorded.
- [ ] P0 identity/offline preflight reviewed as ready before model execution.
- [ ] P1 lifecycle cases all pass with zero cleanup residue.
- [ ] P2 six fixtures and five profiles execute without mid-run tuning.
- [ ] Archive hash and no-capture/no-playback statements verified before and after.
- [ ] Controlled and sanitized report checksums returned.
- [ ] Beam, prompt and VAD recommendations use only the four allowed labels.
- [ ] No M2/M2B milestone or finalist decision is changed by the junior.
