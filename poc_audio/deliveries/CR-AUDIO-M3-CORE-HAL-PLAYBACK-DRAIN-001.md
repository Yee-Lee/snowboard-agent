# CR-AUDIO-M3-CORE-HAL-PLAYBACK-DRAIN-001

Status: `PATCHED / PI VERIFIED / READY FOR ONE-TIME CORE REVIEW AND ACK`

## Decision requested

Core Designer is asked to review and accept the supplied minimal Core AudioOutput
success-completion patch. The patch makes `AudioOutput.play()` drain fully written
PCM through the physical ALSA device before returning success, while preserving
non-draining error/cancel cleanup.

No implementation discovery is requested from Core. Audio has reproduced the defect,
implemented the patch on current Core base, run workstation/Pi regressions, and
completed a target-speaker acoustic A/B. Core only needs to review the exact candidate
and issue one written ACK or one consolidated rejection with evidence.

## Trigger and confirmed root cause

Formal M3 execution on Pi 5 used:

- Audio runner `655e80ec4ed287708ed0a47f383b645d88650b18`;
- Core HAL `ff09199583644a8f0822153e371589f52ae821a0`;
- direct VoiceHAT `hw:0,0`; and
- 16 kHz mono S16_LE stream input adapted by Core to 48 kHz stereo S32_LE.

Core reported successful writes and clean device release but produced no audible
output. The source and converted PCM were non-zero and unclipped; `aplay` of both the
source and exact Core-adapted native WAV was audible. A pyalsaaudio test using the
same direct device and `960 × 4` configuration became audible when it explicitly
called `drain()` before close. The accepted Core code has no success-path drain.

Full sanitized evidence is recorded in
`M3-CORE-HAL-PLAYBACK-DRAIN-DEBUG-001`. Raw/private WAV data remains in the controlled
Pi store and is not included in this handoff.

## Supplied implementation

| Item | Identity |
| --- | --- |
| Core current base | `51fe185d143595702caec03eeec7b63a63e2391d` |
| Direct-child review candidate | `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` |
| Thin bundle | `CORE-HAL-PLAYBACK-DRAIN-REVIEW-001.bundle` |
| Thin bundle SHA-256 | `9c3631df2eb374730543532df835b1da5a4527cb85cd11fd477b1e91928aeb41` |
| Readable patch | `CORE-HAL-PLAYBACK-DRAIN-REVIEW-001.patch` |
| Readable patch SHA-256 | `0973786ee71645db1b476ec5ce0065a93560e56964d24021fd47b3fd62d656de` |

The thin bundle contains exactly one commit and requires base `51fe185...`. The
candidate is therefore eligible for Core fast-forward after review; Core does not
need to recreate or cherry-pick the implementation.

## Accepted semantics represented by the patch

1. Successful `play()` means the iterator is exhausted, adapter tail is flushed,
   every native write succeeds, and ALSA drain completes.
2. Iterator error, write error, force-abort, and cancellation skip drain and retain
   prompt close/drop behavior.
3. Missing drain support and drain failure are explicit playback failures, not
   silent success.
4. Adapter state resets after every success or failure; repeated `play()` calls on
   one started device remain supported.
5. Formats, scaling, resampler, period/buffer, dependency identities, and HAL public
   protocol remain unchanged.

## Verification supplied for review

- Workstation focused: `8 passed`.
- Workstation full non-RPi: `268 passed, 21 deselected`.
- Pi focused: `8 passed`.
- Pi full non-RPi: `267 passed, 1 optional skipped, 21 deselected`.
- Pi real ALSA reuse: five successive silent play/drain cycles, all complete,
  `0.580 s`, no remaining owner.
- Pi exact adapted speech: `6.055 s`, drain complete, no remaining owner, audible
  and comparable in level to the `aplay` control per current-run User observation.

## Scope and gate boundary

- No POC-side resampler or gain is introduced.
- No quality threshold, playback gate, or cleanup gate is relaxed.
- No M3.1 front-end remediation is activated; this is an M3 Core HAL defect.
- The existing `ff091...` execution SHA and submitted packet SHA remain immutable.
- The draft capture result and rejected playback observation remain preserved.
- Formal M3 execution stays stopped until Core accepts an authoritative replacement
  SHA and the Audio packet/signoff identities are updated append-only.

## Single response requested

Core should return one response that:

1. accepts candidate `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` as the authoritative append-only
   Core HAL replacement, or rejects it with all findings consolidated;
2. confirms the success/error/cancel semantics above;
3. confirms the supplied portable and Pi evidence is sufficient, or lists every
   additional required test in that same response;
4. authorizes Audio to replace `ff091...` mechanically in the packet and prepare one
   append-only packet/signoff update; and
5. names one Core owner for the final exact-identity ACK after that mechanical update.

No separate design proposal, exploratory implementation task, gain change, resampler
change, or repeated intermediate review is requested.
