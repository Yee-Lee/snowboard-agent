# M4A M2A Comparative ASR Scorecard 001

Date: 2026-08-21  
Disposition: `REVIEWED_OBSERVATIONS_SHORTLISTED`  
Gate meaning: comparative observations only; this document does not assign PASS,
FAIL, a winner, or a production baseline.

## Evidence identity

- Scorecard generator SHA: `85c5060c2deb4997afe98e9612baa8d4b8c72ac6`
- Controlled scorecard path:
  `/home/yee/.local/share/audio-poc/m2a/evidence/m2a-scorecard-85c5060.json`
- Controlled scorecard SHA-256:
  `0626ab3be00a6c6904b75900ffecd35e982d0bd3f708b4924991254dbdcb6fa0`
- Fixture lock SHA-256:
  `fa3649f2fde77aaaa2132cab81b6d3c562e2b812335d90e846fb6c3f85c943e6`
- Controlled manifest SHA-256:
  `24d3747cbcec7b5a22c7842ac92851a672dcdbe8b256e616c0abf1195dd42a9a`
- Method: exact 20 locked 16 kHz mono S16_LE fixtures; one warm-up and one scored
  inference per item; offline network namespace; no capture or playback device.

The scorecard assembler accepted exactly the six required sanitized formal rows. It
verified candidate/artifact identities, the common fixture lock, 20 observations,
clean teardown, no-audio security evidence, and the exact loaded Python wheel closure.
Diagnostic reruns and controlled transcripts were rejected from scorecard input.

## Comparative observations

| Candidate | CER % | Sentence % | p50 ms | p95 ms | RTF p50 | RSS MiB | Sanitized report SHA-256 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| whisper.cpp small Q8_0 | 15.983607 | 55 | 3956.296 | 4079.104 | 0.979032 | 555.906 | `610bcce6949a0f5728c2f6a307bd17acf4968ccf3018f9009e235ad8da6e465a` |
| whisper.cpp small Q5_1 | 15.573770 | 55 | 8214.087 | 8326.826 | 2.035827 | 485.703 | `07666c0be7770a7383c31c0c49298a8a78e2fb3609fed1d78c415c384a156810` |
| whisper.cpp base Q5_1 | 27.459016 | 25 | 2224.093 | 2252.909 | 0.549382 | 246.734 | `0e3b93a9f1786c49a9c3f46d0cda9692682ce514ea4977707116d361483e2dc3` |
| whisper.cpp medium Q5_0 | 9.836066 | 60 | 24408.214 | 24696.284 | 6.053267 | 1006.344 | `8330f323feb884662c469dfe7fd795208cf6a1337aeea102ee02535fa704bdf8` |
| sherpa Zipformer int8 | 70.081967 | 0 | 616.007 | 1050.485 | 0.150061 | 311.031 | `2e228a6927f7de7830019b8ea241f2838dca2358cde0fea3cf46c798f5259e64` |
| Vosk small-cn 0.22 | 53.688525 | 5 | 1796.106 | 2567.438 | 0.484864 | 232.359 | `63e6ab9cfdae3cd18b6d57665ea870ee9dffde028345405ff56fdb6c878c1e87` |

Whisper formal rows used SHA
`629784f09f0700e7653cee4789cab8caf6d760a3`. Python formal rows used appended fix SHA
`e74f8b86ae6f728c5d2caf1376b614d0b7f6523f`, which preserves the virtualenv launcher
and verifies loaded packages against all pinned wheels.

## Anomaly review

- small Q5 latency was independently rechecked twice on SHA
  `3ab76505bc8dd4c72bfbb00376b3034e64f54c59`. Formal/recheck p50 values were
  8214.087, 8206.636, and 8205.181 ms; CER was exactly 15.573770% in all three.
  The Q5 slowdown relative to small Q8 is reproducible and is not attributed to
  sample-rate drift, throttling, SSH, or a single outlier.
- The first Zipformer attempt on SHA `629784f09f0700e7653cee4789cab8caf6d760a3`
  loaded ambient Sherpa 1.12.25 because the virtualenv symlink was resolved to the
  system interpreter. Its sanitized report SHA-256 is
  `fc3c453f9638db5909db6b307961294cfaf836fff8a3e1908af4aa4a17eab50b`; review rejects
  it from the scorecard while retaining it as evidence. The appended fix enforced the
  exact 1.13.5 two-wheel closure before the accepted formal row.
- Corrected Zipformer formal plus two diagnostic reruns all produced CER 70.081967%
  and 0% sentence correctness; p50 latency was 616.007, 562.678, and 582.642 ms.
- Vosk loaded the exact eleven-wheel closure. Its low-accuracy observation received
  two completed diagnostic reruns retained outside the scorecard; controlled paths
  remain under `/home/yee/.local/share/audio-poc/m2a/evidence/` on the Pi.
- Every reviewed run reported clean teardown, zero audio device owners, no playback,
  and no throttling.

## Shortlist reasoning

The three-row shortlist spans materially different trade-off positions:

1. `asr-whispercpp-small-q8_0-1.9.2`: balanced quality, near-real-time RTF, and moderate
   memory reference.
2. `asr-whispercpp-base-q5_1-1.9.2`: low-resource/low-latency Whisper reference; it
   authorizes a base Q8 quantization-only M2B probe.
3. `asr-whispercpp-medium-q5_0-1.9.2`: observed quality frontier, retained to quantify
   the substantial latency and memory cost.

small Q5 is not shortlisted because its slight CER change accompanies a reproducible
2.07x p50 latency cost versus small Q8. Zipformer and Vosk retain useful speed/resource
observations but their quality gaps do not add a useful optimization starting point
for this fixture lock. These are comparative scope decisions, not rejection gates.

Optional large-v3-turbo Q5_0 was omitted after medium Q5 established a 24.4 s p50 and
1.0 GiB same-runtime quality boundary. Optional Qwen3-ASR was omitted because its
artifact and redistribution notice closure were not acquired; the six required rows
already cover the frozen landscape axes.

## Next authorized work

M2B may now run single-variable probes only against the three named shortlist rows.
The first probe, base Q5_1 versus official base Q8_0 with quantization as the only
change, is complete and reviewed in
[`M4A-M2B-BASE-Q8-QUANTIZATION-PROBE-001`](M4A-M2B-BASE-Q8-QUANTIZATION-PROBE-001.md).
M2 remains open for the rest of M2B, TTS remaining qualification, VAD scope/finalist
disposition, and Core/User provisional-selection review.
