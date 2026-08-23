# RESP-AUDIO-M3-RISK-FOCUSED-GATES-001

**Date**: 2026-08-23
**Role**: Core Designer
**Target**: `CR-AUDIO-M3-RISK-FOCUSED-GATES-001`
**Status**: `ACCEPTED WITH CONDITIONS`

---

## 1. M3 Risk-Focused Result Model and Hard Gates

**Accepted.**

The shift from M1 numeric candidate-advance gates to risk-focused qualification is
approved. M2 Reviewer accepted Silero as a conditional finalist despite the 78%
start-retention miss; applying the M1 95% gate as an automatic M3 rejection would
conflict with that accepted disposition. The `PASS / FAIL / INCONCLUSIVE` model and
the rule that diagnostic metrics do not silently become hard gates are adopted.

**Hard Gate 1 (HAL and evidence validity)**: Accepted as stated. All six
sub-requirements adopted. Artifact mismatch, runtime fetch, malformed PCM and
incomplete evidence are hard failures or INCONCLUSIVE.

**Hard Gate 2 (Lifecycle and bounded failure)**: Accepted as stated. Zero
child/thread/iterator/stream/fd/device-owner delta required. Crash, OOM, unbounded
timeout, deadlock and cleanup residue are hard failures.

**Hard Gate 3 (Thermal and execution stability)**: Accepted as stated.
CPU/temperature/RTF/RSS are observations unless they produce throttle, deadline
failure, OOM, instability or make the M4 combined path infeasible.

---

## 2. VAD Capture-Retention and Low-Volume Trigger

**Accepted with one clarification.**

The five VAD hard requirements are adopted as written.

**Clarification on low-volume trigger**: one confirmed low-volume miss triggers
review, not automatic rejection. Before proposing a fixed front-end gain, the team
must stop and provide signal evidence (level measurement and waveform section). The
written gain amendment must be received and committed before the confirmation run.
The confirmation run must check clipping, normal speech, silence, mechanical startup,
impacts, ASR output and cleanup as stated in the CR.

The M1 manually buffered p95 raw-boundary gate is not an M3 rejection gate.
Capture-retention counts and raw boundaries remain reported observations.

---

## 3. ASR Semantic-Regression Scoring and Fallback Activation

**Accepted with one addition.**

Hard requirements adopted. The old 70% exact-sentence gate is not an isolated M3
failure criterion. Number/date/percentage format differences that preserve meaning
are not acoustic failures.

**Addition**: the category-wide regression comparison requires the direct-PCM
baseline to be identified by its exact fixture SHA and execution SHA in the M3 test
packet before scoring. The comparison must use the same fixture items; cross-fixture
comparison does not satisfy this gate.

**Fallback activation**: the quality-fallback trigger rule for small Q8 must be
stated explicitly in the M3 test packet before any execution. Small Q8 results are
not a second tuning row.

---

## 4. TTS User Review and Latency/RTF Trigger Treatment

**Accepted as stated.**

User quality median ≥ 4/5 is a hard gate. The 1.5 s first-buffer and 1.0 RTF
values are risk triggers requiring review on a repeatable miss, not automatic voice
rejection in isolation.

---

## 5. M2 RSS Values as Regression Baselines; Combined RSS as M4 Gate

**Accepted.**

| Component | M2 reference peak RSS |
| --- | ---: |
| Silero VAD | `80.391 MiB` |
| base Q8 ASR primary | `285.484 MiB` |
| small Q8 ASR fallback | `573.922 MiB` |
| Matcha TTS | `227.531 MiB` |

These are not combined-residency evidence. The arithmetic sums (`593.406 MiB`
primary, `881.844 MiB` with small Q8) are planning references only. Actual
simultaneous-residency acceptance remains an M4 gate. The old 250/1,250/1,000 MiB
ceilings are retired as M3 pass claims.

---

## 6. Fixed Packet Size/Repetition Minimum

The following minimums must be satisfied before the test packet is considered fixed:

**VAD packet**: at least one item from each of the eight named categories — normal
conversational start, low-volume start, natural pause, steady silence, mechanical
device-start, object impact, cough, playback speech. Minimum eight distinct stimulus
items.

**ASR packet**: at least one item from each of — normal Taiwan Mandarin sentence,
low-volume start, sentence with natural pause, code-switch item, domain-term item.
Minimum five distinct items. All must be the same fixture items used for the
direct-PCM baseline comparison (§3 above). Fixture SHA must be declared.

**TTS packet**: at least five prompts of varying length and content type covering
the named risk categories. User listening set must be declared before the session.

**Lifecycle paths**: each of start, stop, reopen, invalid-device, force-abort and
bounded cancel must appear at least once as a dedicated test case.

**Repetitions**: no minimum count beyond lifecycle correctness. No candidate matrix.

---

## 7. Authorization to Prepare M3 Test Packet

**Authorized.**

The team is authorized to prepare and commit the M3 test packet following the
constraints above and in `M3-ENTRY-LOCK-002`. The packet must be committed and
reviewed by Core Designer before any scored hardware run begins. A sanity
capture/playback is permitted but cannot be promoted to formal evidence.

The following pre-execution stops from CR §"Minimal bounded execution" remain
binding without exception:

- applying fixed gain or changing any finalist parameter;
- activating the ASR fallback;
- expanding the packet because of an unexpected observation;
- publishing candidate scores or a hardware disposition; or
- declaring M3 complete.

M3 hardware qualification does not begin until the test packet is committed and
this response is acknowledged by the POC team.

---

## 8. Supersession Confirmation

`CR-AUDIO-M3-RISK-FOCUSED-GATES-001`, if acknowledged, supersedes only the use of
M1 section 4 numeric candidate-advance gates as automatic M3 rejection rules.

Preserved without change:

- all M1/M2 results and their original labels;
- the exact M3 entry identities in `M3-ENTRY-LOCK-002`;
- offline, provenance, lifecycle, cleanup, thermal and data-security gates;
- M4 combined-residency and 20-session requirements; and
- the rule that thresholds cannot be relaxed after seeing M3 results.

---

## 9. Next Steps

1. POC team acknowledges this response in writing.
2. POC team commits M3 test packet with exact fixture IDs, repetitions, timeouts
   and User-listening subset, satisfying the minimums in §6.
3. Core Designer reviews committed test packet.
4. Upon packet sign-off, M3 hardware qualification may begin.
