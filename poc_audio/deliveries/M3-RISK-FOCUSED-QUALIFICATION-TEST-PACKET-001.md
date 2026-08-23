# M3-RISK-FOCUSED-QUALIFICATION-TEST-PACKET-001

Status: `USER APPROVED / RUNNER LOCALLY VERIFIED AT 655e80ec4ed287708ed0a47f383b645d88650b18 / CORE SIGN-OFF PENDING / NO EXECUTION AUTHORITY`

## Purpose and authority

This packet advances final delivery checklist section 5 and the M3 exit gate by
qualifying the M2 finalists on the pinned Raspberry Pi 5, target I2S devices and
accepted Core Audio HAL. It implements
[`RESP-AUDIO-M3-RISK-FOCUSED-GATES-001`](../../docs/pm_handoff/RESP-AUDIO-M3-RISK-FOCUSED-GATES-001.md)
and [`M3-ENTRY-LOCK-002`](M3-ENTRY-LOCK-002.md).

The User approved this packet on 2026-08-23. It must be committed with its runner at
one exact POC execution SHA and then signed off by Core Designer before any formal
M3 qualification run. A
sanity capture/playback may be performed after acknowledgment, but it must use a
separate output directory and must never be promoted into formal evidence.

## Fixed identities

| Field | Fixed value |
| --- | --- |
| POC branch | `audio` |
| POC packet parent SHA | `7b674f50dcd581298613d947b874f7b6c5da332d` |
| POC execution SHA | `655e80ec4ed287708ed0a47f383b645d88650b18` |
| Core accepted Option A delivery | `882e2b6ff571eb9d54ec96bae7d3b63338c5965c` |
| Audio POC Option A validation SHA | `de3b0bab4daaf47f62956d4b27f6697b3d4fa823` |
| Existing Core accepted HAL implementation | `5c9e5aac47e7f4f0dd168d8c75541438ee74f858`; acceptance `2fb2e18f934c3d06392074adba3c4518402101e9` / `core_m3` |
| Core HAL formal execution SHA | `ff09199583644a8f0822153e371589f52ae821a0`; SHA-002 supersedes deprecated `55f3526fd0a37a8831bdff769ea3ba61e5cd0684` |
| Target | Raspberry Pi 5, INMP441 input, MAX98357A output, VoiceHAT overlay |
| Capture conversion | Accepted Option A, explicit 48 kHz to 16 kHz mono S16_LE; ASR boundary is exact 20 ms / 320 samples / 640 bytes |
| VAD | Silero 6.2.1; implementation SHA `5188e3af360ba3b63f5eedb16288d39bc849cacc`; model SHA-256 `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3` |
| ASR primary | whisper.cpp 1.9.2 base Q8; `ggml-base-q8_0.bin`; SHA-256 `c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9` |
| ASR conditional fallback | whisper.cpp 1.9.2 small Q8; `ggml-small-q8_0.bin`; SHA-256 `49c8fb02b65e6049d5fa6c04f81f53b867b5ec9540406812c643f177317f779f` |
| ASR worker | source SHA `62aac01389d06f7f218db0e45acf3de30b4476af`; binary SHA-256 `64ca4ce45899a39afe467e6249a440e3807e18d8e09ff4c3267242d81d2b1b2b`; build report SHA-256 `5539acd951a09169f140181264506f4a4cee0035b7f5ad917bdf4c838175dd0c` |
| ASR recipe | P0, 4 threads, language `zh`, greedy best-of-1, timestamps/internal VAD disabled, fixed initial prompt; prompt SHA-256 `e3b2606c90009ce609aa23183c2229619619cf1173dc17d2ecd2308bfe4fe8ef` |
| TTS | sherpa-onnx 1.13.5 Matcha zh/en archive SHA-256 `271b804af570400d3bcdcb53bf6e53cc9f75180ee763b9f13eb5eaf2b0d086ef`; Vocos 16 kHz SHA-256 `b599142a1fb8ff03de3e84ac35ff537c619e56f4267a6fe894851a42844acf9e` |
| Network | Disabled for formal candidate inference; no runtime fetch |

The fixed ASR prompt is:

```text
繁體中文。常用技術詞彙：Wi-Fi、audio frame、音訊基線、候選語音模型、離線執行。
```

The complete controlled artifact/wheel identities remain governed by the existing
candidate manifests. No model, wheel, private audio, raw transcript or sensitive
log is committed to Git.

## Environment and preconditions

Before the first formal case, record and validate:

1. clean POC and Core worktrees at the exact SHAs above;
2. Pi model/RAM, OS, kernel, firmware, ALSA, overlay, input/output device and driver;
3. mic/speaker wiring, enclosure, speaker/mic position, operator distance and room
   condition;
4. candidate, model, voice, runner, configuration and fixture checksums;
5. no thermal throttle at baseline and no unexpected Audio device owner; and
6. controlled raw-evidence directory outside Git with a new immutable run ID.

If an identity, checksum, format or clean-worktree check fails, stop with `FAIL` or
`INCONCLUSIVE` as defined by the accepted gate. Do not substitute another artifact,
device, fixture or SHA.

## Fixed stimulus and capture packet

The text stimulus source is the frozen recording plan
`poc_audio/fixtures/authorized/recording_plan_v1.json`, SHA-256
`d197078d78ad422e1ec6465aea36472adcc4e77c24827c426a03dcbc4b4ba920`.
The TTS prompt source is `poc_audio/fixtures/fake/tts_prompts.json`, SHA-256
`1f9699344394e718fa0d30fb24df3219407680268340418e564c70cc13007739`.

### Target-mic capture rules

- One formal take per distinct stimulus; no best-take selection or retrospective
  filtering.
- Normal speech: User at the recorded fixed distance and ordinary conversational
  level. Low-volume speech: same position and sentence procedure, intentionally
  softer; do not apply gain or normalize.
- Record full HAL output before VAD cropping. Preserve the raw controlled WAV and
  lock its SHA-256, byte size, duration, peak dBFS and RMS dBFS before inference.
- Use the first valid formal take. Environment/operator interruption makes the case
  `INCONCLUSIVE`; it does not authorize an unrecorded replacement.
- The exact captured WAV used for ASR direct-PCM and HAL/VAD-path comparison must be
  byte-identical. Cross-fixture or cross-take comparison is prohibited.

### VAD packet: eight distinct items

| Test ID | Category | Fixed stimulus | Required observation |
| --- | --- | --- | --- |
| `M3-VAD-01` | normal conversational start | `asr-clear-002`, normal voice | Retain intelligible leading/trailing speech; no complete miss |
| `M3-VAD-02` | low-volume start | `asr-clear-003`, low voice | Report exact capture, level evidence, retained/lost leading content and boundary diagnostics |
| `M3-VAD-03` | natural pause | `asr-pause-031`, normal voice with the frozen natural pause | One utterance envelope is allowed; no complete miss |
| `M3-VAD-04` | steady silence | 60 seconds, same fixed room/position, no intentional speech | No sustained false capture |
| `M3-VAD-05` | mechanical device-start | Start/reopen input and remain silent for 10 seconds | Startup mechanics do not create sustained capture; startup-mask behavior reported |
| `M3-VAD-06` | object impact | One operator-confirmed object impact followed by 10 seconds silence | Classification observation; bounded endpoint and cleanup required |
| `M3-VAD-07` | cough | One operator-confirmed cough followed by 10 seconds silence | Classification observation; bounded endpoint and cleanup required |
| `M3-VAD-08` | playback speech | Play `tts-003` once through the target speaker while input is active | Classification observation only; AEC/rejection is out of scope |

VAD uses the unchanged M2 profile: 16 kHz; official 64-sample context; threshold
`0.5`; negative threshold `0.35`; minimum speech 250 ms; startup mask 160 ms;
silence close 500 ms; capture padding 500/600 ms. Reset recurrent, context and
endpoint state between independent cases.

One confirmed low-volume miss triggers review, not automatic rejection. Stop and
present level measurement plus the affected waveform section. Do not apply gain,
pre-roll, threshold, padding or other front-end changes under this packet.

### ASR packet: five distinct items

| Test ID | Category | Fixed capture/stimulus |
| --- | --- | --- |
| `M3-ASR-01` | normal Taiwan Mandarin | WAV captured for `M3-VAD-01` / `asr-clear-002` |
| `M3-ASR-02` | low-volume start | WAV captured for `M3-VAD-02` / `asr-clear-003` |
| `M3-ASR-03` | natural pause | WAV captured for `M3-VAD-03` / `asr-pause-031` |
| `M3-ASR-04` | code switch | new normal-voice capture of `asr-clear-012` |
| `M3-ASR-05` | domain term | new normal-voice capture of `asr-clear-023` |

After capture and before ASR inference, produce one sanitized fixture-lock index
containing the five IDs, controlled WAV locators, size/duration/SHA-256, reference
SHA-256, capture level measurements and the exact POC execution SHA. The aggregate
fixture SHA is the SHA-256 of the canonical sanitized fixture-lock file and must be
declared in both result paths.

Run order is fixed:

1. Run base Q8 directly on each complete locked 16 kHz WAV, bypassing VAD cropping
   and live HAL ownership. This is `M3-ASR-DIRECT-PCM-BASELINE-001`.
2. On the same byte-identical WAV, replay exact 20 ms frames through the accepted
   HAL-facing adapter, unchanged VAD/endpoint and bounded-utterance path, then base
   Q8. This is `M3-ASR-HAL-PATH-001`.
3. Compare paired per-item raw/task-adjusted CER, sentence outcome, leading/trailing
   content retention and intended-action recoverability. Report category-wide
   differences without cross-fixture substitution.

The direct-PCM and HAL-path executions must use the same candidate binary/model,
prompt, decoder, threads, packet SHA and fixture SHA. One warm-up is allowed before
the five-item sequence; each item has one formal inference and a 120-second timeout.

#### Small Q8 fallback trigger

Small Q8 is not run as a second comparison row. After the base Q8 result is preserved,
stop and request User confirmation plus Core direction before fallback activation.
Fallback may be requested only when:

- base Q8 has a reproducible critical semantic misrecognition that prevents the
  intended downstream action from being recovered; or
- base Q8 has a material category-wide paired regression versus its direct-PCM
  baseline and evidence does not identify malformed PCM, endpoint truncation,
  target-level loss or another common HAL/front-end hard failure.

Crash, OOM, malformed PCM, endpoint truncation, cleanup residue or a shared HAL/VAD
failure does not silently activate small Q8; diagnose the common hard gate instead.
If Core authorizes fallback, use the same five locked WAVs and exact recipe once.

### TTS packet and declared User listening set

| Test ID | Prompt | Category/risk |
| --- | --- | --- |
| `M3-TTS-01` | `tts-001` | short general completion |
| `M3-TTS-02` | `tts-005` | number/percentage |
| `M3-TTS-03` | `tts-009` | date/time |
| `M3-TTS-04` | `tts-013` | code switch and known `start` pronunciation risk |
| `M3-TTS-05` | `tts-014` | product term |
| `M3-TTS-06` | `tts-017` | error message |

Generate and play each prompt once, in the order above, through the target
AudioOutput at Matcha's native 16 kHz mono format. Record ordered input/output chunk
counts and bytes, generation completion, playback completion, first-buffer latency,
generation RTF, xrun/error evidence and cleanup. The User reviews the exact played
output with text disclosed before playback and assigns 1–5 plus critical-misread
yes/no. Median must be at least 4/5 with no critical meaning-changing misread.

## Dedicated lifecycle and failure cases

Each path is one dedicated case; a success observed incidentally in another test does
not replace it.

| Test ID | Path | Fixed bound and required proof |
| --- | --- | --- |
| `M3-LIFE-01` | start/READY then stop | READY within 10 s; stop/completion within 10 s |
| `M3-LIFE-02` | reopen | Five sequential open/start/stop/close cycles; each operation within 10 s |
| `M3-LIFE-03` | invalid input device | Explicit bounded error within 10 s; output identity unchanged |
| `M3-LIFE-04` | invalid output device | Explicit bounded error within 10 s; input identity unchanged |
| `M3-LIFE-05` | bounded cancel | Cancel one active VAD/ASR operation and one active TTS operation; terminal result within 10 s each |
| `M3-LIFE-06` | force-abort | Force-abort one unresponsive deterministic test double/controlled worker; exit within 10 s |

Before and after every case, record child process, thread/task, iterator, stream,
file-descriptor and device-owner counts. Every final delta must be zero. Also record
backpressure/underrun/overflow/xrun evidence when applicable. A crash, OOM, deadlock,
unbounded timeout or residue is a hard failure.

## Resource, thermal and offline observations

- Sample candidate/worker RSS, process CPU, system CPU, temperature and throttle
  state at baseline, during each domain sequence and after cleanup.
- Compare matching isolated peaks with M2 references: Silero `80.391 MiB`, base Q8
  `285.484 MiB`, optional small Q8 `573.922 MiB`, Matcha `227.531 MiB`.
- These values and their arithmetic sums are observations, not M3 numeric pass
  ceilings or combined-residency evidence.
- Fail only on OOM, crash, sustained/monotonic growth, throttle transition, bounded
  deadline failure, instability, cleanup residue or evidence that makes the planned
  M4 combined path infeasible.
- Run formal candidate inference with network disabled and retain evidence of zero
  runtime fetch/network attempt. Restore operator-managed networking only after all
  candidate processes and device owners are closed.

## Commands and execution order

The local packet and artifact-independent lifecycle validation commands are:

```bash
bash poc_audio/tools/run_m3_qualification.sh validate
bash poc_audio/tools/run_m3_qualification.sh fake-lifecycle --output <new-sanitized-json>
```

The packet validator and fake lifecycle runner exist and pass locally. They fail
closed for formal modes and explicitly label fake output as not hardware evidence.
The Core repo is available at `~/workspace/snowboard-agent/`, and Core delivery
`DELIVERY-AUDIO-M3-CORE-HAL-OUTPUT-SHA-002` fixes formal execution to
`ff09199583644a8f0822153e371589f52ae821a0`. HAL `preflight`, `capture`,
`direct-pcm`, the four HAL-owned lifecycle rows, finalist VAD, direct ASR,
HAL/VAD-path ASR, the dedicated candidate cancel/force-abort rows and the fail-closed
22-result summary are implemented against that exact HAL. The formal backend is ready
for local verification before the candidate commit is
submitted for Core packet sign-off. Matcha TTS uses a bounded persistent child protocol and sends its native
16 kHz mono S16_LE PCM to the pinned Core AudioOutput without POC resampling. No
generic ALSA or POC-side resampler may substitute for the pinned HAL.

Every formal command revalidates the controlled sign-off, clean POC/Core SHAs,
target Pi identity, direct `hw:` devices, bounded timeout and zero cleanup residue.
The TTS, VAD and both ASR inference modes are launched by the packet shell inside an
unprivileged user/network namespace; the runner requires only loopback to exist and
requires it to remain down before candidate code starts.
All output/evidence paths must be new; captured private WAVs remain outside Git.

```bash
bash poc_audio/tools/run_m3_qualification.sh preflight \
  --core-root <core-at-ff09199583644a8f0822153e371589f52ae821a0> \
  --signoff <controlled-signoff.json> --test-id M3-PREFLIGHT-01 \
  --input-device <hw:CARD,DEV> --output-device <hw:CARD,DEV> --input-channel <0-or-1> \
  --artifact-dir <controlled-artifact-root> --runtime-python <authorized-sherpa-python> \
  --binary <checksum-pinned-base-q8-worker> --model <ggml-base-q8_0.bin> \
  --vad-runtime-python <authorized-silero-python> --vad-model <silero_vad.onnx> \
  --fixture-dir <controlled-capture-dir> --evidence-log <new-controlled-json> \
  --controlled-locator <controlled://locator> --output <new-sanitized-result-json>

bash poc_audio/tools/run_m3_qualification.sh capture \
  --core-root <core-at-ff09199583644a8f0822153e371589f52ae821a0> \
  --signoff <controlled-signoff.json> --test-id <M3-CAPTURE-ID> \
  --input-device <hw:CARD,DEV> --output-device <hw:CARD,DEV> --input-channel <0-or-1> \
  --frames <20ms-frame-count> --capture-wav <new-controlled-wav> \
  --evidence-log <new-controlled-json> --controlled-locator <controlled://locator> \
  --output <new-sanitized-result-json>

bash poc_audio/tools/run_m3_qualification.sh direct-pcm \
  --core-root <core-at-ff09199583644a8f0822153e371589f52ae821a0> \
  --signoff <controlled-signoff.json> --test-id M3-PCM-01 \
  --input-device <hw:CARD,DEV> --output-device <hw:CARD,DEV> --input-channel <0-or-1> \
  --pcm-wav <controlled-16k-mono-s16-wav> --samples-per-chunk 320 \
  --evidence-log <new-controlled-json> --controlled-locator <controlled://locator> \
  --output <new-sanitized-result-json>

bash poc_audio/tools/run_m3_qualification.sh hal-lifecycle \
  --core-root <core-at-ff09199583644a8f0822153e371589f52ae821a0> \
  --signoff <controlled-signoff.json> --test-id <M3-LIFE-01-through-04> \
  --lifecycle-scenario <start-stop|reopen-5|invalid-input|invalid-output> \
  --input-device <hw:CARD,DEV> --output-device <hw:CARD,DEV> --input-channel <0-or-1> \
  --evidence-log <new-controlled-json> --controlled-locator <controlled://locator> \
  --output <new-sanitized-result-json>

bash poc_audio/tools/run_m3_qualification.sh tts \
  --core-root <core-at-ff09199583644a8f0822153e371589f52ae821a0> \
  --signoff <controlled-signoff.json> --test-id M3-TTS-SET-01 \
  --input-device <hw:CARD,DEV> --output-device <hw:CARD,DEV> --input-channel <0-or-1> \
  --artifact-dir <controlled-artifact-root> --work-dir <new-disposable-model-dir> \
  --runtime-python <authorized-sherpa-runtime-python> \
  --evidence-log <new-controlled-json> --controlled-locator <controlled://locator> \
  --output <new-sanitized-result-json>

bash poc_audio/tools/run_m3_qualification.sh asr-direct \
  --core-root <core-at-ff09199583644a8f0822153e371589f52ae821a0> \
  --signoff <controlled-signoff.json> --test-id M3-ASR-DIRECT-PCM-BASELINE-001 \
  --input-device <hw:CARD,DEV> --output-device <hw:CARD,DEV> --input-channel <0-or-1> \
  --fixture-dir <controlled-five-wav-dir> --binary <checksum-pinned-base-q8-worker> \
  --model <ggml-base-q8_0.bin> --work-dir <new-controlled-asr-work-dir> \
  --timeout 120 --evidence-log <new-controlled-json> \
  --controlled-locator <controlled://locator> --output <new-sanitized-result-json>

bash poc_audio/tools/run_m3_qualification.sh vad-hal \
  --core-root <core-at-ff09199583644a8f0822153e371589f52ae821a0> \
  --signoff <controlled-signoff.json> --test-id M3-VAD-SET-01 \
  --input-device <hw:CARD,DEV> --output-device <hw:CARD,DEV> --input-channel <0-or-1> \
  --fixture-dir <controlled-ten-wav-dir> --vad-runtime-python <authorized-silero-python> \
  --vad-model <silero_vad.onnx> --work-dir <new-controlled-vad-work-dir> \
  --timeout 900 --evidence-log <new-controlled-json> \
  --controlled-locator <controlled://locator> --output <new-sanitized-result-json>

bash poc_audio/tools/run_m3_qualification.sh asr-hal \
  --core-root <core-at-ff09199583644a8f0822153e371589f52ae821a0> \
  --signoff <controlled-signoff.json> --test-id M3-ASR-HAL-PATH-001 \
  --input-device <hw:CARD,DEV> --output-device <hw:CARD,DEV> --input-channel <0-or-1> \
  --fixture-dir <controlled-vad-work-dir/bounded-asr> \
  --source-fixture-lock <direct-asr-work-dir/m3_asr_fixture_lock.json> \
  --binary <checksum-pinned-base-q8-worker> --model <ggml-base-q8_0.bin> \
  --work-dir <new-controlled-asr-hal-work-dir> --timeout 120 \
  --evidence-log <new-controlled-json> --controlled-locator <controlled://locator> \
  --output <new-sanitized-result-json>

bash poc_audio/tools/run_m3_qualification.sh candidate-lifecycle \
  --core-root <core-at-ff09199583644a8f0822153e371589f52ae821a0> \
  --signoff <controlled-signoff.json> --test-id <M3-LIFE-05-or-M3-LIFE-06> \
  --candidate-scenario <cancel-or-force-abort> \
  --input-device <hw:CARD,DEV> --output-device <hw:CARD,DEV> --input-channel <0-or-1> \
  --artifact-dir <controlled-artifact-root> --runtime-python <authorized-sherpa-python> \
  --binary <checksum-pinned-base-q8-worker> --model <ggml-base-q8_0.bin> \
  --fixture-dir <controlled-five-wav-dir> --work-dir <new-controlled-lifecycle-work-dir> \
  --timeout 10 --evidence-log <new-controlled-json> \
  --controlled-locator <controlled://locator> --output <new-sanitized-result-json>

bash poc_audio/tools/run_m3_qualification.sh summarize \
  --core-root <core-at-ff09199583644a8f0822153e371589f52ae821a0> \
  --signoff <controlled-signoff.json> --result-dir <sanitized-result-directory> \
  --output <new-draft-summary-json>
```

After Core signs the committed packet, formal execution must first pass the
controlled external signoff guard:

```bash
bash poc_audio/tools/run_m3_qualification.sh authorize \
  --signoff <controlled-core-signoff.json> \
  --core-root <clean-core-checkout-at-signed-sha>
```

The guard binds the signed packet-manifest SHA-256, clean POC SHA and clean Core SHA,
and rejects the old `5c9e5aac...` implementation because it lacks the requested
output adaptation. The signoff file stays in the controlled store, not Git.

The fixed overall bounds are 10 minutes for preflight/capture, 15 minutes for each
direct-PCM or VAD/ASR sequence, 20 minutes for TTS and 15 minutes for lifecycle.
Offline execution is enforced on every candidate inference mode rather than deferred
to a separate permissive-network replay.

Execution order is preflight, capture/fixture lock, direct-PCM baseline, VAD/ASR,
TTS, lifecycle and summary. Stop immediately on identity mismatch, malformed
PCM, runtime network access, crash, OOM, deadlock, unbounded timeout or cleanup
residue. Preserve rejected/incomplete evidence.

## Result and publication rules

Each case is `PASS`, `FAIL` or `INCONCLUSIVE` only under the accepted risk-focused
gate. Raw probability, boundaries, PCM, waveform sections, transcripts, User forms
and detailed logs stay in the controlled store. Git receives only checksums,
sanitized summaries, commands and controlled locators.

After execution, present draft results, method, limitations and proposed disposition
to the User. Before explicit User confirmation, do not commit/push a scorecard,
deliver a result, activate small Q8, change a finalist parameter, start M3.1, declare
a winner/no-go or mark M3 complete.

## M3.1 and P9 boundaries

M3.1 is not part of this run. A qualifying reproducible hard-gate failure, specific
root-cause evidence and a separately approved single-action proposal are all required
before a new M3.1 packet can be prepared.

The exact `M4B-P9-RESIDENCY-SURROGATE-001` artifact, protocol and source identity were
received from LLM POC and passed their six-test deterministic regression. Its corrected
Core ACK remains pending, so Audio does not yet integrate or execute P9. This is
`ARTIFACT RECEIVED / CORE ACK PENDING / NON-BLOCKING FOR THIS AUDIO M3 QUALIFICATION
PACKET`; do not claim P9 complete or grant LLM Gate 2 credit.
