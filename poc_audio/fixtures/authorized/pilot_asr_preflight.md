# Pilot ASR Preflight Protocol

Status: `APPROVED OBSERVATION-ONLY` via
[`CR-M1-PILOT-PREFLIGHT-001`](../../deliveries/CR-M1-PILOT-PREFLIGHT-001.md)

This advances reproducible ASR-input development only. It neither freezes M1
nor starts M2 candidate selection.

## Preconditions

- Pi worktree is at this exact committed SHA and clean after checkout.
- The Git-ignored Pilot directory passes its 40-item verification.
- No audio process owns the device; this preflight reads local WAV files only.
- A selected ASR engine/model has a separate manifest for version, source,
  checksum, license, aarch64 installation, and offline use before execution.

## Prepare the immutable Pilot revision

Run on the Pi from the repository root:

```sh
bash poc_audio/tools/m1_pilot_preflight_prepare.sh \
  --prepare \
  --input-dir poc_audio/fixtures/artifacts/m1-authorized-zh-tw-v1-pilot-r1 \
  --output-dir poc_audio/fixtures/artifacts/m1-authorized-zh-tw-v1-pilot-r1-asr-preflight-v1
```

The command validates every native WAV/checksum and writes 40 local 16 kHz mono
S16_LE WAVs plus `asr_preflight_manifest.json`. Do not use `--replace` unless
intentionally recreating the entire local revision after review.

## Permitted result

Publish a sanitized `OBSERVATION` only: source SHA, both manifest checksums,
candidate identity, command, and cleanup outcome. Do not commit raw WAV,
absolute artifact paths, private audio, or full transcript output.
