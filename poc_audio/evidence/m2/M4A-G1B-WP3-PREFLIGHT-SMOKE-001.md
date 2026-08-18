# M4A Gate 1B WP3 preflight and focused smoke

Status: `PASS — PRELIMINARY SMOKE ONLY / NOT M2 GATE`

## Delivery contribution

This evidence advances the reproducible-program, candidate-manifest,
offline-input, native-format, and cleanup portions of the final checklist for
the two Core-authorized primary rows. It does not select a finalist, close a
frozen quality/resource gate, prove network-disabled operation, or authorize a
fallback/VAD row.

## Exact bindings

| Boundary | POC SHA | Reviewed raw report SHA-256 | Result |
| --- | --- | --- | --- |
| Artifact-only preflight | `d807695c69dd405c64fad1b7d308746ee5caf642` | `4dc8c3362db0307ec80fbb3ea7345fcee298a2140743d82ff04d50a81238973d` | Both focused rows `PREFLIGHT_PASS_NOT_EXECUTED` |
| Offline runtime install/import | `5305a425aff7034d6fdeaceefcdef9b7d534519b` | `3ad8da786a5f46821cb598a48355d9afc4c18117618e976856964aa9bacefbb0` | `RUNTIME_IMPORT_PASS_NOT_INFERRED` |
| One-item candidate smoke | `55124047aeb4fa36b953d43b907ac58108e44d86` | `8ad78274b0e283e929e82d56a248df728de64da2976eb5e96322c3e24876f938` | `SMOKE_PASS_PRELIMINARY_NOT_GATE` |

All three Pi checkouts were clean and matched the local full SHA. The final
pre-test identified Raspberry Pi 5 Model B / aarch64, Debian 13 kernel
`6.12.47+rpt-rpi-2712`, Python `3.13.5`, no thermal throttle and no audio-device
owner. Raw JSON and operator-specific connection details remain outside Git.

## Controlled inputs and runtime

The five unique authorized inputs (two shared runtime wheels, SenseVoice int8,
Matcha acoustic archive and 16 kHz Vocos) matched the Gate 1B manifest byte
sizes and SHA-256 values on the Pi. The first transfer attempt left an
incomplete SenseVoice file and correctly failed before execution. The complete
file was resumed and verified; existing Pi Matcha/Vocos copies were admitted
only after their hashes exactly matched the manifest.

The fresh virtual environment installed only `sherpa-onnx==1.13.5` and
`sherpa-onnx-core==1.13.5` with package indexes and dependency resolution
disabled. Import exposed both `OfflineRecognizer` and `OfflineTts`; five native
libraries were individually hashed. No model was loaded at this boundary.

## Focused real-candidate observations

| Candidate/input | Observation | Cleanup/security |
| --- | --- | --- |
| SenseVoice / frozen `asr-clear-001` (`6e08ad0…`) | 6.0 s audio; load `1624.290 ms`; inference `298.726 ms`; RTF `0.049788`; edit distance `1/10`, CER `0.10`; sentence not exact | Worker exit `0`; only hypothesis SHA-256 retained; raw transcript not emitted |
| Matcha / tracked `tts-001` | load `2308.223 ms`; generation `189.415 ms`; 30,012 mono float32 API samples at native 16 kHz; 1.87575 s audio; RTF `0.100981` | Worker exit `0`; PCM not emitted; ALSA/playback not opened |

Final cleanup counters were child processes `0`, threads `0`, iterators `0`,
streams `0`, and device owners `0`.

## Commands and remaining gate

The reproducible entry points are:

```text
bash poc_audio/tools/run_m4a_authorized_preflight.sh ...
bash poc_audio/tools/run_m4a_runtime_preflight.sh ...
bash poc_audio/tools/run_m4a_candidate_smoke.sh ...
```

The remaining WP3 qualification must still run all 50 ASR fixtures and 20 TTS
prompts with frozen repetitions/metrics, cold/hot p50/p95, first-chunk evidence,
RSS/CPU/disk, timeout/cancel/force-abort/reopen, network-disabled rerun, and User
TTS quality review. The single ASR sentence miss is retained and must not be
averaged away. Matcha first-chunk remains `PENDING`; no callback dependency may
be added without exact authorization. VAD remains blocked by
`CR-AUDIO-M4A-G1B-VAD-SCOPE-001`.
