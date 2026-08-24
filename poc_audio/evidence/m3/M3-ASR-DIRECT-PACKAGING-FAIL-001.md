# M3-ASR-DIRECT-PACKAGING-FAIL-001

**Date**: 2026-08-24
**Status**: `REJECTED FORMAL ATTEMPT / PACKAGING DEFECT FIXED APPEND-ONLY`
**Test ID**: `M3-ASR-DIRECT-PCM-BASELINE-001`

## Reviewed result

The exact-SHA Pi runner emitted `FAIL` before inference because `m3_asr.py` requested
the nonexistent tracked path `poc_audio/manifests/m2b_c_task_scoring.json`. The frozen
manifest is actually tracked as `m2b_c_task_adjusted_scoring.json` and contains the
required `normalization.traditional_to_simplified` mapping.

| Identity | Value |
| --- | --- |
| Audio execution SHA | `25e263b7b3cc91103d1c7332b794017c842e331b` |
| Core execution SHA | `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` |
| Controlled result locator | `controlled://audio-m3/20260824-r2/M3-ASR-DIRECT-PCM-BASELINE-001` |
| Controlled evidence SHA-256 | `28d00575fa05ecd8d56a9cb61ffae98cf1aa1bf607837a06667d65f09429b501` |
| Result | `FAIL` |

The runner confirmed a disabled network namespace and zero residue for children,
threads, tasks, iterators, streams, file descriptors, and device owners. No ASR model
inference began, so this attempt contains no quality disposition and does not consume
or replace the five-fixture formal baseline.

## Minimal correction

The append-only correction points `m3_asr.py` at the existing frozen
`m2b_c_task_adjusted_scoring.json`; it does not alter audio, model, prompt,
normalization data, scoring rules, fixture identities, or Core HAL behavior. A focused
packaging test now loads the manifest from the repository and asserts a frozen mapping
entry, preventing another candidate from passing while the runtime dependency is
absent.

Focused M3 packet/HAL verification after the correction: `27 passed`; packet
validation: `PASS`. The rejected result remains preserved on the Pi. A new exact Audio
execution SHA and matching sign-off are required before a new formal attempt.
