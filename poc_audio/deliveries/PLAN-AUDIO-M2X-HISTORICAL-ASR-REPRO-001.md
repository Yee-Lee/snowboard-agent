# PLAN-AUDIO-M2X-HISTORICAL-ASR-REPRO-001 — Pi historical ASR experience reproduction

- **Status**: `PLAN READY — INDEPENDENT EXPERIENCE TRACK / EXECUTION NOT STARTED`
- **Raised**: 2026-08-21
- **Working milestone code**: `M2X`
- **Track**: Cross-milestone, non-gating Audio POC experience diagnostic
- **Execution target**: Raspberry Pi 5 and the reviewed Voice HAT microphone
- **Decision owner**: User
- **Test control owner**: Audio POC Technical Lead
- **Core contract effect**: None; Core approval and ACK are not required for this track
- **Milestone effect**: None unless a later committed decision explicitly adopts a finding
- **Architecture change**: `No`

## 1. Purpose and delivery contribution

`M2X` is the communication and execution code for this independent experience
track. It is not one of the formal M1–M4 delivery milestones, does not create an
`m2x` Git tag, and is not added to the authoritative milestone completion table.

Reconstruct the final historical offline ASR experience found under the
operator-controlled Pi archive, then isolate which observed behavior came from
the ASR model and which came from capture, PCM conversion, endpointing, VAD,
decoder settings or prompt context.

This track contributes evidence and implementation experience to these final
delivery checklist areas:

- exact ASR engine/model/runtime/parameter identity;
- real Pi 5 microphone behavior and delivered PCM characteristics;
- VAD/endpoint start, end, pause, padding and reset behavior;
- latency, RTF, resource, timeout, cancellation and cleanup observations;
- reusable frontend recommendations and explicit demo-code boundaries.

It is not part of the Core contract, is not an M2A candidate row, does not
unblock the M2A fixture lock, does not participate in the M2A shortlist, and
cannot produce a winner, finalist, gate PASS or production dependency decision.
Core approval and ACK are therefore not prerequisites for this experience
track. Its findings may only become a formal M2B probe or candidate proposal
through a later, separate reviewed scope decision.

## 2. Questions to answer

1. Can the last integrated archive ASR path be reproduced offline on the same
   Pi with its observed parameters and a pinned runtime identity?
2. How much of the experience depends on SpeechRecognition/PyAudio endpointing
   rather than faster-whisper itself?
3. Does the historical 48 kHz capture-to-16 kHz conversion preserve different
   speech boundaries or signal characteristics from the pinned Option A path?
4. Do `beam_size=3`, the Chinese prompt and faster-whisper VAD materially affect
   transcript or latency when changed one at a time?
5. Which ideas should be proposed for a future authorized M2B frontend or
   decoder probe, and which archive behaviors should be rejected as implicit,
   unbounded or non-reproducible?

## 3. Frozen historical reference

The reference is the ASR slice of
`~/workspace/archive/chatbot/snowboard/chat_with_snowboard.py`, not the complete
LLM/TTS chatbot. The archive remains read-only and is never treated as a second
development worktree.

The following identity is reconstructed from the archive and the Pi environment.
Every value must be verified and recorded again before first model load:

| Field | Historical reference |
| --- | --- |
| Engine | `faster-whisper` |
| Observed installed engine | `1.2.1`; not yet proven to be the original run version |
| Backend | CTranslate2; observed installed version `4.7.1` |
| Model | `Systran/faster-whisper-base` |
| Cached upstream revision | `ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66` |
| Cached model bytes | `145217532`; checksum still required |
| Device / compute | CPU / CTranslate2 `int8` |
| Worker configuration | `cpu_threads=2`; no explicit `num_workers` in the integrated script |
| Decoder | `language="zh"`, `beam_size=3`, `initial_prompt="中文對話"` |
| Model-side VAD | `vad_filter=True`; implicit defaults must be resolved from the pinned runtime |
| Capture wrapper | SpeechRecognition with PyAudio, requested 48 kHz input |
| Endpoint setup | 1 s ambient calibration; pause 0.8 s; phrase 0.3 s; trailing silence 0.3 s |
| ASR input conversion | `get_raw_data(convert_rate=16000, convert_width=2)` then int16-to-float32 `/32768.0` |

CTranslate2 `int8` is not the whisper.cpp `Q8_0` artifact format. Results from
this track must not be merged with or relabeled as the existing whisper.cpp Q8
evidence.

The incomplete cached faster-whisper medium download and the earlier tiny/model
scripts are outside the first reproduction packet. They require separate
identity and purpose if later requested.

## 4. User authority and fail-closed entry conditions

The User has established this as an independent Audio POC experience-collection
track outside the Core contract. No Core approval or ACK is required. The
current request authorizes planning, not immediate Pi execution; execution
starts when the User asks the Technical Lead to run one or more named packets.
Microphone capture always requires a separate same-session User confirmation
because it creates private audio.

Before any execution:

1. Record the clean local and Pi full SHA and run the normal Pi environment
   pre-test outside formal latency/resource measurement.
2. Confirm the archive is read-only for the session. New wrappers, tests and
   manifests are developed in this repository only.
3. Pin engine/backend/package provenance, licenses and exact model files with
   byte sizes and SHA-256 checksums. No runtime download is allowed.
4. Create a fresh external work directory; do not reuse an old output directory
   or write results into the archive.
5. Resolve and record the actual capture device and realized format. Do not use
   a stale card index as evidence.
6. Confirm no process owns an audio device and no formal benchmark is running.
7. Obtain separate User confirmation immediately before any new microphone
   recording. The authorization must cover the fixed prompt card, storage
   location, retention and review audience.
8. Predeclare the selected fixture IDs or live prompt IDs before seeing output.

Stop without model load or capture on artifact mismatch, unknown provenance or
license, missing User execution request or capture confirmation, network
requirement, dirty Pi checkout, occupied device, unresolved PCM format or
inability to create an isolated bounded worker.

## 5. Implementation boundary

Build a minimal diagnostic wrapper that reproduces only:

```text
microphone or fixed WAV
  -> explicit historical frontend profile
  -> bounded faster-whisper worker
  -> controlled raw result
  -> sanitized metrics
```

Do not execute the complete archive chatbot. Do not invoke Google recognition,
LLM, TTS, playback, cloud services or product composition code. Do not patch the
archive script in place.

The wrapper must:

- accept an explicit model path and refuse aliases that can trigger downloads;
- report resolved engine, backend, model, parameters and PCM identity;
- use a persistent child process so timeout/cancel can terminate native work;
- impose an outer maximum utterance duration while recording that this is a
  safety bound around the historically unbounded `phrase_time_limit=None`;
- expose historical endpoint, VAD, prompt and decoder settings explicitly;
- preserve raw and normalized transcript identities without writing private
  transcript text to tracked Git files;
- prove zero child process, thread, stream and audio-device owner after success,
  timeout, cancel and error.

## 6. Input modes

Run the lowest-risk available mode first. Later modes add evidence but do not
replace earlier ones.

### Mode F — existing controlled fixture replay (recommended first)

Use a small, predeclared subset of already controlled 16 kHz mono S16_LE
fixtures. If access to those fixtures is not separately authorized for this
track, use only reviewed archive WAVs whose ownership and transcript handling
are confirmed.

Minimum quick packet:

- one silence/noise item;
- one Taiwan Mandarin item;
- one code-switch item;
- one number/date item;
- one product-term item;
- one longer bounded item when available.

This mode isolates engine/runtime/decoder behavior. It does not reproduce live
SpeechRecognition endpointing and cannot answer real microphone questions.

### Mode A — reviewed archive WAV replay

Preflight `example/test_mic.wav` and `example/test_fix.wav` for ownership,
privacy, PCM metadata and checksum before use. Unknown transcript or capture
conditions limit them to smoke observations; do not calculate CER against an
invented reference.

This mode is useful for confirming that the reconstructed runtime accepts old
audio, but it is not comparative evidence unless exact references and capture
provenance are recovered.

### Mode U — User-operated live historical experience

With explicit recording authorization, the User reads a fixed prompt card at a
fixed position and normal speaking level. Include at least:

- two Taiwan Mandarin prompts;
- one Mandarin/English code-switch prompt;
- one number/date prompt;
- one product-term prompt;
- one prompt containing a natural internal pause.

Run each prompt twice. Record enclosure, microphone position, approximate
speaker distance, background condition, resolved device, ambient-calibration
threshold and realized PCM format. Raw audio and full transcript remain in the
controlled external directory.

This mode reproduces the historical interaction experience. Because separately
spoken utterances are not identical, it must not be used alone to claim one
frontend is more accurate than another.

### Mode P — paired frontend isolation

Capture each authorized utterance once in immutable native Voice HAT format:
48 kHz, stereo, S32_LE through direct `hw:` access. Feed the same source into
two offline, explicit transformations:

1. a pinned historical-equivalent conversion/endpoint profile; and
2. the pinned Option A channel/valid-bit/resampler path plus the comparison
   endpoint profile.

Both outputs use the same faster-whisper process, model, prompt and decoder.
This is the only mode intended to attribute a difference to frontend behavior.
If SpeechRecognition live behavior cannot be reproduced from a recorded stream,
report that limitation and keep the live experience and PCM comparison separate.

Do not use `plughw:` as an unexplained comparison implementation. Any channel
mapping, resampling, gain or padding must be explicit and recorded.

## 7. Execution packets

### M2X-P0 — identity and offline preflight

- Verify archive paths without modifying them.
- Hash the complete base model snapshot and runtime inputs.
- Record Python, faster-whisper, CTranslate2, SpeechRecognition and PyAudio
  versions and licenses.
- Verify the wrapper refuses network-dependent model resolution.
- Verify target Pi/OS/kernel/device identity, available disk and clean checkout.
- Output: `PREFLIGHT_READY_NOT_EXECUTED` or `INCONCLUSIVE`.

### M2X-P1 — deterministic wrapper and lifecycle smoke

- Use fake/synthetic PCM first.
- Prove READY, success, declared error, timeout, cancel, forced abort and reopen.
- Confirm zero child/thread/stream/device-owner counts after every case.
- Do not open the real microphone in this packet.

### M2X-P2 — quick fixed-audio reproduction

- Run Mode F and, when permitted, Mode A.
- One unscored warm-up followed by one scored/observed inference per selected
  item; no cold matrix, soak or repeated candidate campaign.
- Keep the historical integrated settings unchanged.
- Output an observation table, not a candidate disposition.

### M2X-P3 — User live experience

- Run Mode U only after a same-session capture authorization and clean device
  preflight.
- Enforce the outer utterance timeout and provide an immediate operator stop.
- Collect User notes using fixed questions: missed start, clipped ending,
  unwanted early stop, perceived response delay and obvious transcript error.
- Stop and clean up before reviewing or changing any parameter.

### M2X-P4 — paired attribution

- Run Mode P using the same immutable native audio for both paths.
- Compare PCM and endpoint effects before comparing transcripts.
- If an optimization is explored, change only one of endpoint, VAD, prompt,
  beam or thread count relative to the named historical baseline.
- Return a delta table and a recommendation for zero or more future M2B probes.

## 8. Measurements

Every real run records command, UTC time, exit code, full repo SHA and runtime
identity. Collect:

### Frontend and endpoint

- native and delivered sample rate, channels, format, frames and checksum;
- selected channel and valid-bit interpretation;
- resampler/converter identity;
- peak, RMS, clipping count and silence ratio;
- detected speech start/end and retained utterance duration;
- leading/trailing speech loss against reviewed labels when available;
- ambient energy threshold and endpoint/VAD parameters;
- empty, false-start, early-stop and maximum-duration outcomes.

### ASR and performance

- raw transcript in controlled evidence and its hash in sanitized evidence;
- normalized CER, exact sentence diagnostic and number/product correctness only
  where an approved reference exists;
- model load time, ASR-only latency, capture-to-final latency and RTF;
- peak RSS, CPU time/thread configuration, temperature and throttling;
- timeout/cancel latency and cleanup proof.

### User observation

- fixed prompt ID and repeat number;
- perceived missed start, clipped ending or premature endpoint;
- perceived response delay and obvious semantic error;
- free-form comments stored only in controlled raw evidence when they contain
  private transcript text.

User observations provide experience context; they are not a hardware or
quality gate by themselves.

## 9. Comparison rules

- Compare candidates or frontends only on the same source PCM and reference.
- Never compare a live utterance with a separately spoken utterance as if they
  were identical input.
- Keep capture-to-final and ASR-only latency separate.
- Keep CTranslate2 int8 and whisper.cpp Q8_0 identities separate.
- Report historical defaults that cannot be resolved as unknown, not inferred.
- Do not tune after seeing a prompt result and then reuse that prompt as unbiased
  evidence.
- Preserve failed, timed-out and inconclusive runs.
- Reproduction assertions may be `PASS`, `FAIL` or `INCONCLUSIVE`; overall
  findings remain diagnostic observations and never become an M2 disposition.

## 10. Stop conditions

Terminate the current packet, collect bounded diagnostics and prove cleanup on:

- any runtime network attempt or missing offline artifact;
- model/runtime checksum mismatch;
- OOM, thermal throttling or the predeclared timeout;
- microphone/device ownership conflict, xrun or unresolved realized format;
- failure to stop the native ASR worker or release the audio device;
- raw evidence escaping the controlled directory;
- operator withdrawal of capture authorization;
- parameter drift from the predeclared profile.

A cleanup failure blocks later packets until reviewed. It is not repaired by
rerunning the same packet with a relaxed bound.

## 11. Evidence and data handling

Suggested external raw locations:

```text
/controlled/audio-poc/work/historical-asr-repro-001/
/controlled/audio-poc/evidence/historical-asr-repro-001/
```

Suggested tracked artifacts after review:

```text
poc_audio/evidence/diagnostic/M2X-001.md
poc_audio/deliveries/RESP-AUDIO-M2X-HISTORICAL-ASR-REPRO-001.md
```

Do not commit models, package caches, raw WAV, private transcript, full operator
comments, endpoints, credentials or large raw reports. A sanitized index may
contain IDs, metadata, hashes, metrics, disposition and controlled locators.

Every packet includes at least:

```text
test_id
delivery_requirement
purpose
preconditions
repo_sha
archive_identity
runtime_and_model_identity
hardware_and_environment
input_mode_and_fixture_ids
commands
parameter_profile
repeat_count
assertions_and_bounds
required_evidence
cleanup_check
```

## 12. Fast path and estimated operator involvement

The smallest useful sequence is:

1. M2X-P0 identity/offline preflight.
2. M2X-P1 fake lifecycle smoke.
3. M2X-P2 six-item fixed-audio observation.
4. Review before requesting microphone access.
5. M2X-P3 approximately ten authorized live utterances.

M2X-P4 is performed only if P2/P3 show a plausible frontend effect worth
isolating. The User is needed for authorization, prompt delivery and experience
notes in P3; P0-P2 do not require microphone operation.

## 13. Exit and follow-up decisions

This track exits when:

- the historical integrated ASR identity is either reproducibly demonstrated
  or marked `INCONCLUSIVE` with a specific missing dependency/artifact;
- at least one fixed-audio run has bounded performance and cleanup evidence;
- any authorized live run has complete PCM/endpoint metadata and User notes;
- frontend, decoder and model effects are separated as far as the evidence
  permits;
- the response recommends one of the following:
  - no carry-forward;
  - retain parameters as implementation experience only;
  - propose exact one-variable M2B probes;
  - raise a separate candidate/scope request for faster-whisper.

Completion does not update the milestone index, create a milestone tag, change
M2 reachability, modify a Core contract or authorize M3. Experience and
recommendations remain internal to Audio POC. Any later adoption into formal
milestone evidence or a Core-facing dependency requires a separate committed
decision with exact scope, identity, fixtures and evidence mapping.

## 14. User-selectable execution depth

When ready to execute, the User may request:

1. **P0-P2 only (recommended first)** — offline identity, lifecycle and fixed
   audio reproduction with no microphone capture.
2. **P0-P3** — add User-operated live historical experience under explicit
   recording authorization.
3. **P0-P4** — add paired frontend attribution after reviewing P2/P3.

The recommended first request is Option 1. This independent track does not wait
for Core review. No historical runtime or microphone execution begins until the
User requests the corresponding packet depth; microphone recording still uses
the explicit confirmation in Section 4.
