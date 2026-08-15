# M1-FIXTURE-FORMAL-SAMPLING-001 — Formal Fixture Technical and Listening Review

Status: `PASS WITH OBSERVATION`

## Delivery contribution

This evidence advances the M1 fixture catalog and quality-review portion of the
delivery gate. It records a reproducible, sanitised technical review of the 60
items added after Pilot and an authorized human listening review. It does not
freeze the fixture set, convert native audio, or authorize a real candidate
run.

## Baseline and command

- Pi review source SHA: `ceaca843df3f6a6f563df4e7cd60b314d6478192`
- Controlled native fixture revision:
  `poc_audio/fixtures/artifacts/m1-authorized-zh-tw-v1-pilot-r1/`
- Sanitised local review result:
  `review/formal-sampling-ceaca84.json`
- Sanitised review SHA-256:
  `2b8263b0efd5eee052ec01069becdb91e551a5c731fc7dc7f194aadd61a397f4`

The review runner derives the Formal collection as the exact complement of the
recorded 40-item Pilot selection; it does not infer it from fixture-ID ranges.
It opens WAV files read-only and emits only fixture IDs and signal statistics:

```sh
bash poc_audio/tools/m1_fixture_review.sh \
  --artifact-dir poc_audio/fixtures/artifacts/m1-authorized-zh-tw-v1-pilot-r1 \
  --stage formal
bash poc_audio/tools/m1_fixture_formal.sh verify
```

## Reviewed result

| Check | Result |
| --- | --- |
| Exact Formal complement | `PASS`, 60 fixtures reviewed |
| Native PCM metadata and duration | `PASS`, no issues; 15 × 6 s, 15 × 8 s, 30 × 12 s |
| Channel layout | `PASS`, no Formal fixture has non-zero samples on the expected-silent right channel |
| Full 100-item local manifest | `PASS`, 100 valid files, 50 ASR references, 600 seconds non-speech |
| Fixed stratified listening sample | `PASS`, 10 / 10 speech fixtures accepted by User/Designer during the Pi review |

The speech listening sample covers clear speech and natural pause across Taiwan
Mandarin, code-switch, number, date, and product-term categories:
`asr-clear-006`, `012`, `017`, `021`, `025`; `asr-pause-031`, `037`, `042`,
`046`, `050`. The technical sample additionally includes `vad-silence-011`,
`025`, `vad-noise-011`, and `025`. Raw audio and its replay output remain
outside Git.

## Observation: isolated near-full-scale samples

Seven Formal files each contain exactly one source sample at the configured
near-full-scale threshold: `asr-clear-013`, `asr-clear-025`,
`asr-pause-035`, `vad-silence-011`, `vad-noise-012`, `vad-noise-018`, and
`vad-noise-021`.

This is not evidence of sustained clipping: no file has a contiguous
full-scale plateau in this review, and the accepted listening sample includes
`asr-clear-025` without an audible objection. A single threshold event can be
an impulse or a very short saturated sample, so it is retained as a
non-blocking observation rather than described as zero clipping. Reopen this
finding if a later review finds audible distortion, repeated saturation, or
candidate input sensitivity.

## Remaining gate work

Native acquisition, checksum/metadata verification, technical review, and the
sampled human review are complete. The fixture set remains `NOT FROZEN` until
the pinned native-to-delivered conversion produces transformed metadata and
checksums, catalog/reference normalization review is complete, and the
Designer/Tester accepts `metrics_v1.md` before any real candidate result is
revealed. Core P4 final selection ACK remains an independent M2-entry blocker.
