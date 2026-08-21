# M4A M2B Base Q8 Quantization Probe 001

Date: 2026-08-21  
Disposition: `OBSERVATIONS_REVIEWED / DELTA RETAINED`  
Meaning: one M2B single-variable comparison; not a final primary/fallback selection.

## Fixed comparison

- Named baseline: `asr-whispercpp-base-q5_1-1.9.2`
- Probe: `asr-whispercpp-base-q8_0-1.9.2-m2b`
- Only changed variable: model quantization, `Q5_1` to `Q8_0`
- Fixed engine/runtime: whisper.cpp `1.9.2`, native CPU-only aarch64, four threads
- Fixed source/model revision:
  `ggerganov/whisper.cpp@5359861c739e955e79d9a303bcbc70fb988958b1`
- Fixed fixture lock:
  `fa3649f2fde77aaaa2132cab81b6d3c562e2b812335d90e846fb6c3f85c943e6`
- Method: exact 20 fixtures, one warm-up plus one scored inference each, isolated
  network namespace, 120-second item timeout, 2400-second row budget, no capture or
  playback.

The tracked authorization is
[`m2b_base_q8_probe.json`](../../manifests/m2b_base_q8_probe.json). The formal probe ran
on Pi source SHA `f41a3cde6cc5d362579aae90e642356f8cbfc721`.

## Artifact identity

| Variant | Filename | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Baseline Q5_1 | `ggml-base-q5_1.bin` | 59,707,625 | `422f1ae452ade6f30a004d7e5c6a43195e4433bc370bf23fac9cc591f01a8898` |
| Probe Q8_0 | `ggml-base-q8_0.bin` | 81,768,585 | `c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9` |

Q8_0 adds 22,060,960 bytes (36.948313%). Models remain in controlled Pi storage and
are not committed.

## Formal delta

| Observation | Base Q5_1 | Base Q8_0 | Q8_0 delta |
| --- | ---: | ---: | ---: |
| Overall CER % | 27.459016 | 25.819672 | -1.639344 points (-5.970148% relative) |
| Sentence correctness % | 25 | 25 | 0 points |
| Latency p50 ms | 2224.093 | 1258.191 | -965.902 (-43.429029%) |
| Latency p95 ms | 2252.909 | 1299.629 | -953.280 (-42.313294%) |
| RTF p50 | 0.549382 | 0.309818 | -0.239564 (-43.606088%) |
| Peak RSS MiB | 246.734 | 266.062 | +19.328 (+7.833537%) |

The formal sanitized report is retained at
`/home/yee/.local/share/audio-poc/m2a/evidence/m2b-base-q8-f41a3cd.sanitized.json`
with SHA-256
`bb6cacc53d09c26f3bcb5d832dd374b155e3696ef5c9c6daa035d0a6cfcb81eb`.
Its controlled companion SHA-256 is
`b5e9899700677b2473d36a0edba349844e38905794fdd181d81e4b5f386f30e6`.

## Diagnostic confirmation

Because Q8_0 being faster than Q5_1 is counterintuitive, the same probe was repeated
twice on SHA `6dbea1cf1eb5fed36be148b172706ade9b46b7f9`. Both reports are explicitly excluded
from the delta table.

| Run | CER % | Sentence % | p50 ms | p95 ms | RTF p50 | RSS MiB | Sanitized SHA-256 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Formal | 25.819672 | 25 | 1258.191 | 1299.629 | 0.309818 | 266.062 | `bb6cacc53d09c26f3bcb5d832dd374b155e3696ef5c9c6daa035d0a6cfcb81eb` |
| Recheck 1 | 25.819672 | 25 | 1264.901 | 1300.744 | 0.309866 | 266.047 | `861ce0b70cab66cc2b113f08dd7c7cf6415e19f1358338670f602ac09c2e6886` |
| Recheck 2 | 25.819672 | 25 | 1270.959 | 1300.284 | 0.309957 | 266.078 | `66b26470b697d64960512399c469b4e528c261805f98f6b25ca489272f12049b` |

All 20 hypothesis hashes were identical across the three executions. Each run had
clean teardown, zero audio device owners, no playback, no network route, and no Pi
throttling. The observation therefore supports a reproducible ARM quantized-kernel
trade-off rather than sample-rate drift, SSH effects, caching, or a single outlier.

## Review

Within the base low-resource track, Q8_0 retains the observed accuracy and materially
reduces latency/RTF at a bounded model-size and RSS cost. This probe supports carrying
base Q8_0 forward instead of base Q5_1 for later comparative primary/fallback review.
It does not by itself select the overall ASR primary or close M2B.
