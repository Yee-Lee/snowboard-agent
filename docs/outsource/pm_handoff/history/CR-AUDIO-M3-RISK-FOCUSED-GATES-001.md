# CR-AUDIO-M3-RISK-FOCUSED-GATES-001

Status: `READY FOR CORE REVIEW / USER APPROVED / NO EXECUTION AUTHORITY`

## Decision requested

Core/Designer is asked to approve a risk-focused M3 qualification standard for
the accepted VAD, ASR and TTS finalists on the pinned Raspberry Pi 5 Audio HAL.
This request changes only how M3 hardware evidence is judged. It does not
rewrite M1/M2 history, relax a result after execution, authorize a tuning
matrix, or start M3.

## Trigger

The M1 numeric gates were created before real candidate evidence and were useful
for the original candidate-elimination plan. M2 was subsequently changed by
written ACK to a comparative primary/fallback selection, and its Reviewer
accepted Silero as a conditional M3 finalist despite the old 95% numeric
start-retention miss.

Applying every early candidate gate unchanged in M3 would repeat broad
candidate qualification instead of testing the material risks introduced by
the target microphone, speaker and Audio HAL. Specific problems are:

- exact-sentence ASR scoring treats understandable formatting differences as
  failures and does not isolate HAL/microphone regressions;
- manually buffered VAD labels make raw boundary error a poor proxy for whether
  downstream capture retains intelligible speech;
- the old per-engine RSS ceilings are several times the measured finalists and
  provide little warning of real residency risk; and
- long repetition matrices spend Pi/User time without materially improving the
  M3 hardware decision.

The proposed replacement is fixed before M3 execution and focuses on failures
that threaten M4 delivery.

## Unchanged entry lock

- Core Audio HAL implementation/test SHA:
  `de3b0bab4daaf47f62956d4b27f6697b3d4fa823`.
- Raspberry Pi 5 + INMP441 input + MAX98357A output, VoiceHAT overlay, explicit
  accepted 48 kHz-to-16 kHz Option A conversion.
- VAD: Silero 6.2.1 with the exact profile and model identity in
  `M3-ENTRY-LOCK-002`.
- ASR: base Q8 primary; small Q8 quality fallback; P0 + greedy + fixed prompt.
- TTS: Matcha 1.13.5 finalist.
- No threshold, padding, gain, decoder, voice or candidate matrix.

## Proposed M3 result model

Each test case remains `PASS`, `FAIL` or `INCONCLUSIVE`:

- `PASS`: exact preconditions and evidence are complete, all applicable hard
  gates pass, and no critical product-risk finding remains.
- `FAIL`: an applicable hard gate fails reproducibly.
- `INCONCLUSIVE`: environment, fixture, human review or evidence is insufficient
  to make a reliable decision.

Diagnostic metrics and non-critical observations do not silently become hard
gates. Any new threshold or front-end change requires a written amendment before
the confirmation run.

## Proposed hard gates

### 1. Audio HAL and evidence validity

All of the following are required:

- exact clean POC and Core HAL SHAs, candidate/model checksums and fixed command;
- AudioInput delivers ordered 16 kHz mono S16_LE output in exact 20 ms / 320
  sample frames after the accepted conversion;
- AudioOutput consumes every ordered native TTS PCM chunk or returns an explicit
  bounded error;
- input/output start, READY, stop, reopen, invalid-device and failure behavior
  matches the accepted contract;
- offline execution performs no runtime fetch or network access; and
- no model, private audio, sensitive transcript, raw result or secret enters
  Git.

Artifact mismatch, runtime fetch, malformed/truncated PCM or incomplete evidence
is a hard failure or `INCONCLUSIVE` when the environment prevents a valid run.

### 2. Lifecycle and bounded failure

Success, error, timeout, cancel, force-abort and reopen must terminate within the
predeclared bound. Final child process, thread/task, iterator, stream, file
descriptor and device-owner deltas must be zero. Crash, OOM, unbounded timeout,
deadlock or cleanup residue is a hard failure.

### 3. Thermal and execution stability

There must be no thermal-throttle transition during a valid bounded packet and
no monotonic resource growth across the fixed reopen/repetition sequence.
CPU, temperature, RTF and RSS are reported as observations unless they produce
throttle, deadline failure, OOM, instability or make the documented M4 combined
path infeasible.

## Proposed quality gates

### VAD on the target microphone

Use one predeclared risk packet containing normal conversational starts,
low-volume starts, natural pauses, silence, mechanical startup, object impacts,
cough and playback speech.

Hard requirements:

- every normal conversational utterance retains intelligible leading and
  trailing speech in the exact capture sent downstream;
- no normal conversational or natural-pause utterance is completely missed;
- internal pauses may remain one utterance envelope;
- steady silence and device-start mechanics must not create a sustained false
  capture; and
- reset/reopen must not carry VAD state between independent sessions.

Low-volume leading loss is the named M3 blocker. One confirmed low-volume miss
triggers review rather than automatic candidate rejection. If signal evidence
shows target-mic level is the cause, the team may propose one fixed front-end
gain. The confirmation run must check clipping, normal speech, silence,
mechanical startup, impacts, ASR output and cleanup. No gain/threshold/padding
matrix is permitted.

Impacts, cough and playback speech are classified observations. A basic VAD is
not failed merely because it detects acoustic speech or a sharp impact; repeated
steady-environment activation or an activation that makes the bounded pipeline
unusable is a hard product-risk finding. Capture-retention counts and raw
boundaries remain reported, but the old manually buffered raw-boundary p95 is
not an M3 rejection gate.

### ASR through the target microphone

Run base Q8 primary once on a fixed target-mic packet covering normal Taiwan
Mandarin, low-volume starts, pauses, code-switch and domain terms. Preserve raw
transcripts in the controlled store.

Hard requirements:

- no empty/truncated result caused by AudioInput, endpoint or lifecycle failure;
- no systematic loss of leading/trailing content introduced by the target-mic
  path;
- no critical semantic misrecognition that prevents the intended downstream
  action from being recovered; and
- no material category-wide regression attributable to the HAL/front-end when
  compared with the locked direct-PCM baseline.

Report raw and task-adjusted CER plus sentence outcomes, but do not use the old
70% exact-sentence gate as an isolated M3 failure. Number/date/percentage format
differences that preserve meaning are not acoustic failures. Small Q8 executes
only if the primary has a hard failure or the predeclared quality-fallback rule
is met; it is not a second tuning row.

### TTS through the target speaker

Play one fixed risk-focused prompt set through M3 AudioOutput. The User reviews
the exact played output with the text disclosed before playback.

Hard requirements:

- every PCM iterator completes in order without missing start/end audio,
  truncation, repeated chunks, xrun corruption or device residue;
- User quality median is at least 4/5; and
- there is no critical misread that changes the intended meaning or action.

First-buffer latency, playback completion latency and generation RTF remain
reported. The existing 1.5 s first-buffer and 1.0 RTF values are risk triggers:
a repeatable miss must be reviewed for user-visible deadline or M4 feasibility,
not treated as an automatic voice rejection in isolation.

## Resource baselines and escalation rule

Use the accepted M2 isolated peak RSS values as regression references:

| Component | M2 reference peak RSS |
| --- | ---: |
| Silero VAD | `80.391 MiB` |
| base Q8 ASR primary | `285.484 MiB` |
| small Q8 ASR fallback | `573.922 MiB` |
| Matcha TTS | `227.531 MiB` |

The approximate arithmetic sums are `593.406 MiB` for the primary set and
`881.844 MiB` with small Q8. They are not combined-residency evidence and must
not be labelled as such.

M3 records the same measurement boundary and investigates a material unexplained
increase from the matching M2 baseline. No fixed percentage delta is proposed
because HAL buffers, capture/playback ownership and sampling boundaries differ.
The old 250/1,250/1,000 MiB VAD/ASR/TTS ceilings become historical candidate
screening references, not M3 pass claims. Hard failure occurs only for OOM,
crash, sustained growth, throttle, bounded-deadline failure, cleanup residue or
evidence that the fixed candidates cannot support the planned M4 combined run.
Actual simultaneous-residency acceptance remains an M4 gate.

## Minimal bounded execution

The exact fixture IDs, repetitions, timeouts and User-listening subset must be
fixed in the M3 test packet before any scored run. The packet should use the
smallest set that covers each named high-risk category and all lifecycle paths;
it must not reproduce the M1/M2 candidate matrix. A sanity capture/playback may
run first, but its output cannot be silently promoted to formal evidence.

Stop and request direction before:

- applying fixed gain or changing any finalist parameter;
- activating the ASR fallback;
- expanding the packet because of an unexpected observation;
- publishing candidate scores or a hardware disposition; or
- declaring M3 complete.

## Supersession boundary

If approved, this request supersedes only the use of M1 section 4 numeric
candidate-advance gates as automatic M3 rejection rules. It preserves:

- all M1/M2 results and their original labels;
- the exact M3 entry identities and Audio HAL contract;
- offline, provenance, lifecycle, cleanup, thermal and data-security gates;
- M4 combined-residency and 20-session requirements; and
- the rule that thresholds cannot be relaxed after seeing M3 results.

## Core/Designer response requested

Please return one written disposition that:

1. accepts or rejects the risk-focused M3 result model and hard gates;
2. accepts or amends the VAD capture-retention and low-volume trigger;
3. accepts or amends ASR semantic-regression scoring and fallback activation;
4. accepts or amends the TTS User review and latency/RTF trigger treatment;
5. accepts the M2 RSS values as regression baselines and confirms combined RSS
   remains an M4 gate;
6. supplies any required fixed packet size/repetition minimum before execution;
   and
7. authorizes preparation of the M3 test packet, or lists the exact remaining
   blocker.

Until that response is committed, M3 remains `PLANNED` and no hardware
qualification run is authorized by this draft.
