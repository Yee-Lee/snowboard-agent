# M4A Gate 1B WP3 full-fixture qualification

Status: `REVIEWED — SENSEVOICE ASR FAIL / MATCHA TTS PERFORMANCE PASS, FINAL TTS DISPOSITION PENDING`

## Delivery contribution

This packet advances final-checklist candidate results and ASR/TTS quality,
latency, resource, thermal and cleanup evidence for the two exact Gate 1B
primary rows. It rejects the ASR primary under the frozen quality gate. It does
not close TTS User quality, candidate lifecycle, network-disabled P12, VAD,
M3 HAL or final winner selection.

## Test packet and binding

| Field | Reviewed value |
| --- | --- |
| Test ID | `M4A-G1B-WP3-FULL-QUALIFICATION-001` |
| Delivery requirement | Final checklist sections 3 and 4; preliminary M4A P2/P3/P7/P8 |
| POC SHA | `63c2cc179bb3c2525201da0f7a78d2c50b63d759` |
| Platform | Raspberry Pi 5 Model B Rev 1.1, aarch64, Debian kernel `6.12.47+rpt-rpi-2712`, Python 3.13.5 |
| Runtime | `sherpa-onnx==1.13.5`, `sherpa-onnx-core==1.13.5`, two threads |
| ASR fixture | 50 delivered Option A WAVs; manifest SHA-256 `1b33569bbc1f755771c359b2bba4284e72e71a8d836917db9aa8be63ffe530a2` |
| TTS fixture | 20 tracked prompts; SHA-256 `1f9699344394e718fa0d30fb24df3219407680268340418e564c70cc13007739` |
| Method | Three new-process cold suites; three unscored warm-ups; twenty hot suites with one loaded model; nearest-rank percentiles |
| Raw report | Git-ignored controlled return `m2/20260819T121016Z-qualification-63c2cc1/report.json`; 952,389 bytes; SHA-256 `ac1d4adfb7dcc90a20577eb917595c53d72fe04f08e6d0645a74511aabb8ae6f` |
| Command | `bash poc_audio/tools/run_m4a_qualification.sh` with the exact artifact, runtime, fixture, new work and output paths |

The Pi worktree was clean before and after the run. Pre-test reported 34.2 C,
`throttled=0x0` and no audio-device owner. The run completed at 49.05 C with
`throttled=0x0`.

## Reviewed results

Every worker completed successfully: three ASR cold suites, one 20-cycle ASR
hot suite, three TTS cold suites and one 20-cycle TTS hot suite. This produced
150 cold plus 1,000 hot ASR results and 60 cold plus 400 hot TTS results.

| Gate or observation | Result | Disposition |
| --- | --- | --- |
| ASR Taiwan-Mandarin core CER `<= 20%` | `41.629%` | `FAIL` |
| ASR overall sentence correctness `>= 70%` | `6%` (3/50 fixture identities correct in every hot cycle) | `FAIL` |
| ASR hot latency p50 / p95 / max | `317.238 / 411.204 / 425.426 ms` | observation |
| ASR hot RTF p50 / p95 / max | `0.051220 / 0.051401 / 0.053178` | performance observation only |
| ASR model load p50 / p95 / CPU | `1,613.143 / 1,781.970 ms / 198.207% max` | two-thread observation |
| TTS hot first-buffer p50 / p95 / max | `210.119 / 285.098 / 313.520 ms` | `PASS` against `<= 1,500 ms` |
| TTS hot RTF p50 / p95 / max | `0.098874 / 0.112776 / 0.126653` | `PASS` against `<= 1.0` |
| TTS model load p50 / p95 / CPU | `2,342.217 / 2,357.110 ms / 215.836% max` | two-thread observation |
| ASR peak RSS / advisory | `374.125 / 1,250 MiB` | within advisory |
| TTS peak RSS / advisory | `227.531 / 1,000 MiB` | within advisory |
| ASR / TTS model disk | `232.656 / 142.315 MiB` | observation |

The 20 hot ASR cycles were complete and each fixture returned the same
hypothesis hash in every cycle. The failure is therefore reproducible under
this packet and is not averaged away. Category findings were: code-switch CER
32.2981%, date 30.1587%, number 28.0899%, product-term 58.2090%, and
Taiwan-Mandarin 41.6290%.

ASR hot RSS moved from 372.141 to 372.344 MiB; TTS moved from 227.734 to
228.203 MiB and then plateaued. Both remain `PENDING` technical review because
the frozen no-growth wording has no numeric tolerance; no resource PASS is
claimed from the advisory limit alone.

## Security, cleanup and decision

No raw transcript or PCM was emitted. The runner did not open ALSA and speaker
playback was false. Final child, thread, iterator, stream and device-owner
counters were all zero; an independent post-run `fuser` check also found no
audio-device owner.

SenseVoice is `REJECT` for M2 advance because it failed both frozen ASR hard
quality gates. No deferred fallback may execute without a new Core row-level
ACK; see
[`CR-AUDIO-M4A-G1B-ASR-SCOPE-001`](../../deliveries/CR-AUDIO-M4A-G1B-ASR-SCOPE-001.md).
Matcha passes only the measured latency/RTF observations. Its User quality,
critical-misread, lifecycle, network-disabled, resource-growth and legal
conditions remain open, so it is not yet a finalist or winner.
