# REQ-AUDIO-M4-RUNTIME-CLOSURE-002

**Date**: 2026-08-25  
**From**: Audio POC  
**To**: Core Team  
**Status**: `BLOCKING ACTION REQUIRED — CORE INTEGRATION MUST NOT START`  
**Supersedes**: `REQ-AUDIO-M4-RUNTIME-CLOSURE-001`  
**Scope**: Complete Core HAL/controller and finalist runtime closure; no gate change

## Mandatory integration boundary

Core MUST complete, checksum-lock, and verify the entire process-level Python
package closure before starting finalist integration. This is an integration
entry blocker, not a recommendation. An environment that imports finalist
packages successfully but falls back to the Raspberry Pi default `python3`,
system site packages, or an incomplete Core HAL venv MUST be rejected.

Core integration intake MUST remain blocked until the response and artifacts in
this request are committed, returned to Audio, and reviewed. A demo, an existing
developer environment, or individually installed packages do not satisfy this
request.

## Required isolated runtimes

| Runtime boundary | Required locked closure |
| --- | --- |
| Core HAL / M4 controller | Python 3.13 isolated venv; `pyalsaaudio==0.11.0`; `samplerate==0.2.4`; `PyYAML==6.0.2`; an explicitly pinned compatible NumPy; complete transitive/native closure |
| Silero VAD 6.2.1 | Separate Python 3.13 isolated venv; `onnxruntime==1.29.0`; `numpy==2.5.2`; protobuf, flatbuffers, packaging, and the complete offline wheel closure |
| Matcha TTS | Separate Python 3.13 isolated venv; `sherpa-onnx==1.13.5`; `sherpa-onnx-core==1.13.5`; explicitly pinned NumPy and every native/runtime input |
| whisper.cpp base-Q8 | Existing checksum-pinned worker binary and `ggml-base-q8_0.bin`; no Python or binary substitution |

The three Python environments MUST remain separate where their NumPy/native
requirements differ. Core MUST NOT make them appear aligned by enabling
`include-system-site-packages`, changing `PYTHONPATH` to a system package tree,
or silently selecting another installed version.

## Required reproducibility package

For every runtime boundary, Core MUST provide:

1. Exact interpreter path and Python version.
2. `pyvenv.cfg` proving `include-system-site-packages = false`.
3. A machine-readable lock manifest containing every wheel filename, version,
   size, SHA-256, source locator, and license/notice reference.
4. A complete offline install command using `--no-index` and only the locked
   wheel directory.
5. A preflight that imports packages through the named venv and rejects missing,
   extra, mismatched, or system-resolved packages.
6. A preflight against the pinned Core SHA that imports the real Audio HAL and
   configuration package, constructs the ALSA input/output configuration, and
   proves `pyalsaaudio`, `samplerate`, PyYAML, and NumPy resolve from the locked
   controller venv.
7. A clean-environment reproduction log and the Core source SHA that consumes
   the lock.

The preflight MUST fail before integration execution when any required package,
wheel checksum, Core SHA, or interpreter identity differs.

## Evidence motivating the correction

Audio's isolated finalist venvs resolve the locked Silero and Matcha versions.
The Pi default controller Python has no `pyalsaaudio`, while the historical
HAL-only M3 venv contains `pyalsaaudio==0.11.0`, `samplerate==0.2.4`, and
`numpy==2.4.2` but not PyYAML. These are environment-closure observations; they
are not a candidate score, P9 disposition, or permission to relax an M4 gate.

The missing controller packages demonstrate that finalist-only locks are
insufficient. Core owns closing the integration runtime as one reproducible,
offline package set before Gate 3 implementation begins.

## Required Core response and acceptance condition

Core MUST return:

- the closure owner and committed delivery location;
- the controller and finalist lock/manifest SHAs;
- the complete wheel/artifact checksum inventory;
- the exact offline install and fail-closed preflight commands;
- the Core integration source SHA; and
- written confirmation that integration intake remains blocked until the clean
  reproduction and package-alignment review pass.

No Core integration ACK, Gate 3 start, production reference, or package-alignment
closure may be claimed before all items above are present and reviewed. Audio M4
formal evidence remains separate and cannot waive this Core blocker.
