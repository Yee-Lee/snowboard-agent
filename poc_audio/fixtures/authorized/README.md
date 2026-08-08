# M1 Authorized Fixture Acquisition

Status: `PENDING USER AUTHORIZATION AND RECORDING`

This packet prepares the fixed VAD/ASR fixture required by the M1 gate. It
advances the final delivery checklist's fixture catalog, quality evidence, and
data-safety requirements. It does not authorize recording and is not a frozen
fixture set by itself.

## Proposed source

Use project-authored, non-sensitive prompts recorded by an operator who
explicitly authorizes the recordings for internal Audio POC evaluation. This
avoids an unverified external-dataset license and covers the target Taiwan
Mandarin, code-switch, number/date, and product-term cases.

The tracked [recording plan](recording_plan_v1.json) defines:

- 25 clear-speech clips;
- 25 speech clips containing a marked natural pause;
- 25 silence clips and 25 ambient-noise clips;
- 50 ASR references shared with the speech portion of the VAD set;
- at least 10 combined minutes of silence/noise observation.

The existing tracked TTS set already contains 20 non-sensitive prompts.

## Data boundary

Raw/native and transformed WAV files must stay under
`poc_audio/fixtures/artifacts/`, which is Git-ignored. Do not record names,
addresses, credentials, private conversation, or other sensitive content.
Tracked indexes may contain only fixture IDs, the project-authored reference,
format/duration metadata, source authorization, and SHA-256 checksums.

No endpoint, login account, SSH setting, absolute operator path, or device
owner information belongs in the fixture index.

## Required approval before capture

The User/Designer must confirm both statements:

1. The speaker authorizes these recordings for internal Audio POC evaluation.
2. The resulting audio is controlled project test data and will not be
   redistributed or committed to Git.

After confirmation, change `authorization_status` in the plan through a
reviewable decision record. Until then, do not collect audio and do not mark
the fixture gate accepted.

## Capture and conversion boundary

Capture the source in the device's reviewed native format: 48 kHz, stereo,
S32_LE through direct `hw:` access. Keep that immutable native source and its
checksum. Do not use `plughw:` to silently create the candidate fixture.

The native recording is not candidate-ready. Channel selection, valid-bit
interpretation, anti-alias filtering, 3:1 resampling, and S16 conversion must
use the same pinned Option A policy accepted for the Core AudioInput boundary,
or a separately frozen fixture-preparation implementation that is explicitly
cross-validated against it. Each transformed WAV receives its own checksum.

## Completion gate

The fixture-set approval remains pending until all of the following exist:

- explicit authorization decision;
- 100 expected files with unique IDs and SHA-256 checksums;
- native and delivered PCM metadata and duration checks;
- labels/references and the frozen [metric definitions](../metrics_v1.md);
- a sanitized pre-test showing category counts and at least 10 minutes of
  silence/noise;
- Tester review with raw audio remaining outside Git.
