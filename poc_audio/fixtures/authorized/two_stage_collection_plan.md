# M1 Two-Stage Fixture Collection Plan

Status: `PROPOSED / NOT FROZEN`  
Decision owner: User / Designer

The formal M1 fixture gate remains 100 clips and 50 ASR utterances. This plan
does not lower that gate. It isolates recording-operation risk before the
formal set is collected.

## Stage A — Pilot: 40 clips

Purpose: validate the actual microphone position, native PCM capture,
checksums, operator workflow, and absence of private audio before creating the
formal comparison fixture.

| Class | Count | Selection |
| --- | ---: | --- |
| Clear speech | 10 | Five Taiwan Mandarin, then code-switch, number, date, and two product terms |
| Natural pause | 10 | Five Taiwan Mandarin, then code-switch, number, date, and two product terms |
| Silence | 10 | `vad-silence-001` through `010`, 12 seconds each |
| Ambient noise | 10 | `vad-noise-001` through `010`, 12 seconds each |

The exact speech IDs and machine-readable selection are in
[`recording_plan_v1.json`](recording_plan_v1.json). The pilot has 20 ASR
utterances and 240 seconds of non-speech; it is deliberately insufficient for
the formal ASR and VAD gates.

### Pilot review

Tester checks metadata/checksums for all 40 files and the operator listens to
representative clear speech, pause, silence, and noise samples. Review asks:

1. Is the spoken signal intelligible at the expected microphone distance?
2. Is clipping, persistent interference, or unintended speech present?
3. Does any physical placement, gain, native PCM setting, or room condition
   need to change?

`PASS` permits only the next collection stage. It never advances or rejects an
ASR/VAD candidate.

If any capture condition changes after Pilot, preserve its raw files locally as
rejected observations and start a new collection revision. Do not mix them
with Formal fixture files.

## Stage B — Formal completion: remaining 60 clips

Precondition: the Pilot is reviewed and the capture conditions are unchanged.
Record the remaining 15 clips in every class, reaching 25 per class and 100
total. The completed set then contains all 50 ASR references and 600 seconds
of silence/noise.

Tester validates the complete local manifest, format, durations, checksums,
category counts, and sanitized summary. Only then may the User/Designer review
the fixture set and metric definitions for freezing. Core acceptance or a
bounded revision of `CR-AUDIO-M3-PCM-001` remains an independent M1 blocker.

## Recording command policy

Use the existing recorder only after the explicit authorization confirmation:

```sh
# Run the selected 40 Pilot clips; completed IDs are resumable.
bash poc_audio/tools/m1_fixture_record.sh \
  --record-all --stage pilot --confirm-authorization

# Review the Pilot set only; it must show 40 valid files.
bash poc_audio/tools/m1_fixture_record.sh --verify --stage pilot

# After Pilot review, collect the remaining 60 and validate the full 100.
bash poc_audio/tools/m1_fixture_record.sh \
  --record-all --stage formal --confirm-authorization
bash poc_audio/tools/m1_fixture_record.sh --verify --stage formal
```

To re-record a specific selected fixture, add `--record <fixture-id> --replace`
and the same `--stage` value. Do not use an unqualified `--record-all` before
the formal completion decision.

## Pre-Pilot monitoring diagnostic

`M1-FIXTURE-PILOT-000` showed that the direct native recording has signal on
the expected left channel, while the operator found raw replay too quiet. Before
resuming Pilot recording, compare the original local source with a temporary
unity-gain dual-mono monitoring copy:

```sh
bash poc_audio/tools/m1_fixture_monitor.sh asr-clear-001 --play
```

The command creates a new Git-ignored file under `artifacts/.../monitor/` and
does not edit the source WAV. If the derived playback is clear, record this as
a monitoring-route finding only; ASR fixture conversion remains governed by
the pinned Core AudioInput boundary. If it is still quiet, stop and inspect the
speaker output route/gain before recording more Pilot clips.
