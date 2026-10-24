# Response: REQ-AUDIO-M4-RUNTIME-CLOSURE-002

- **Request**: `REQ-AUDIO-M4-RUNTIME-CLOSURE-002`
- **Status**: `READY FOR AUDIO POC REVIEW — CORE INTEGRATION REMAINS BLOCKED`
- **Date**: 2026-08-25
- **Owner**: Core Developer
- **Target**: Pi host `snowboard`, Python `3.13.5`

## Closure delivery

Core created a Git-external controlled closure at
`/home/yee/.local/share/sbd/m4a-runtime-closure-002/`. It contains three
separate wheel directories, lock manifests, isolated venvs, and the clean
reproduction logs. No wheel, native binary, model, raw audio, or local config
was added to Core Git. The existing Core M3 checkout and its local config were
not modified.

| Runtime | Manifest SHA-256 | Locked packages |
| :--- | :--- | :--- |
| Controller-r2 | `6bb24f9a0a2f2a66a522706b22222081fbf009b28c9dc0942a22d714114276f4` | `pyalsaaudio==0.11.0`, `samplerate==0.2.4`, `numpy==2.4.2`, `PyYAML==6.0.2`, `Pillow==11.1.0` |
| Silero VAD | `65c188c7e902e80b02ac27ef435d0a00763e3b4595d636bd945d2ac789a9aeff` | `onnxruntime==1.29.0`, `numpy==2.5.2`, `protobuf==7.36.0`, `flatbuffers==25.12.19`, `packaging==26.3` |
| Matcha TTS | `c848ab2af1f1487f8ba34578dc28de76ef4a9d7bdb98845b144df4d46a73a7f9` | `sherpa_onnx==1.13.5`, `sherpa-onnx-core==1.13.5`, `numpy==2.5.2` |

Each manifest records exact filenames, package versions, sizes, SHA-256,
source locators, license references, and import names. Every venv proves
`include-system-site-packages = false`.

## Reproduction and preflight

Each runtime was installed into a fresh venv from its controlled wheel directory:

```bash
<venv>/bin/python -m pip install --no-index --no-deps \
  --find-links <runtime>/wheels <runtime>/wheels/*.whl
```

`scripts/m4_audio_runtime_closure.py` fail-closes on an invalid wheel inventory,
checksum or size mismatch, non-isolated venv, installed-package mismatch,
system-resolved import, interpreter-version mismatch, or Core SHA mismatch.
The controller preflight imports the real ALSA HAL, loads the local ALSA
configuration, and constructs its input/output backends.

Fresh reproduction logs are retained in `reproduction-20260825T/` beneath the
controlled closure root. Controller-r2, VAD, and TTS all returned `PASS`.
Controller-r2 is bound to deployed Core SHA
`5c9e5aac47e7f4f0dd168d8c75541438ee74f858`; this is closure provenance only,
not M4a candidate or Gate 3 evidence.

## Gate boundary

Audio POC review of this response, manifests, and clean logs is still required.
Core integration remains blocked until that review completes. Candidate-specific
ASR/TTS integration also requires the M2B reviewed selection and a Core
provisional-selection ACK. Any future candidate must repeat controller preflight
with its own exact source SHA and configuration checksum.
