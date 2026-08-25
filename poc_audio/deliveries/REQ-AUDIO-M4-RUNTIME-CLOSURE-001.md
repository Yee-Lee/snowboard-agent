# REQ-AUDIO-M4-RUNTIME-CLOSURE-001

**Date**: 2026-08-25  
**From**: Audio POC  
**To**: Core Team  
**Status**: `ACTION REQUIRED BEFORE CORE INTEGRATION`  
**Scope**: M4 finalist runtime closure; no gate change requested

## Request

Before Core starts finalist integration, provide and lock the offline runtime
closure for the selected Audio M4 finalists. The Core integration environment
must not rely on the Raspberry Pi default `python3` package set.

| Finalist | Required locked runtime |
| --- | --- |
| Silero VAD 6.2.1 | Python 3.13 isolated venv; `onnxruntime==1.29.0`; `numpy==2.5.2`; complete offline wheel closure including protobuf, flatbuffers and packaging |
| Matcha TTS | Python 3.13 isolated venv; `sherpa-onnx==1.13.5`; matching `sherpa-onnx-core==1.13.5`; pinned numpy and all required native/runtime inputs |
| whisper.cpp base-Q8 | Existing checksum-pinned worker binary and `ggml-base-q8_0.bin`; no Python runtime substitution |

Each closure must provide: exact Python interpreter path/version, `pyvenv.cfg`
with `include-system-site-packages = false`, wheel filename and SHA-256 inventory,
offline install command (`--no-index`), package-version proof, artifact/source
locator and license/notice index. The integration manifest must bind those values
to its source SHA and reject a fallback to system-site packages.

## Pi preflight finding

On the M4 Pi, default `python3` currently resolves:

| Package | Observed default | Required M4 value |
| --- | ---: | ---: |
| onnxruntime | 1.24.2 | 1.29.0 |
| numpy | 2.4.2 | 2.5.2 |
| sherpa-onnx | 1.12.25 | 1.13.5 |

This is an environment-qualification finding, not an M4 candidate score,
winner/no-go decision, or a request to relax the frozen packet. Audio POC found
the required offline wheels on the Pi and demonstrated that isolated venvs can
resolve the named versions without network access. Those local setup observations
are not formal Pi evidence and must be independently reproduced from the Core
closure before integration.

## Required Core response

1. Confirm the owner and delivery location for the runtime closure.
2. Provide the manifest/lock SHA and all wheel/artifact checksums.
3. State whether Core will consume the Audio wrapper boundary or create a
   separately version-locked integration wrapper.
4. Confirm the integration preflight rejects default/system Python package drift.

Until this is received and reviewed, Audio M4 formal execution and Core integration
remain separate. M4 status stays `AT_RISK`; no `PASS`, Gate 2B credit, or production
acceptance is implied.
