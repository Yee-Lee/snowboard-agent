# P4 Option A validation evidence — A10 Option 2 rerun

- **Test ID:** `P4-A10-RERUN-002`
- **POC test SHA:** `de3b0bab4daaf47f62956d4b27f6697b3d4fa823`
- **Execution date:** 2026-08-15 UTC
- **Environment pre-test:** `PASS` before each retained attempt
- **Core decision:** `RESP-AUDIO-M3-P4-REPRO-002`, Option 2 accepted

## Reviewed result

| ID | Result | Evidence summary |
| --- | --- | --- |
| P4-A10 | `PASS` | Core-approved build-wheel hashes were verified against the manifest, then both pinned sdists built from source on a clean Pi with package indexes disabled. A separate new virtual environment installed the generated wheels and imported the required identities successfully. |

The completed rerun returned exit code 0. It built `pyalsaaudio 0.11.0` and
`samplerate 0.2.4`; the independent install imported `numpy 2.4.2`,
`pyalsaaudio 0.11.0`, and `samplerate 0.2.4`, with module version `0.2.4`.
`samplerate` reports embedded libsamplerate version `0.2.2`, which is the pinned
native source version. All ten controlled inputs matched their expected
SHA-256 values. No package index was enabled during either source build or
identity rerun.

## Target and native identity

- Raspberry Pi 5 / aarch64; Debian GNU/Linux 13; kernel `6.12.47+rpt-rpi-2712`
- Python `3.13.5`; CMake `3.31.6`; GCC/G++ `14.2.0`
- `libasound2t64` and `libasound2-dev` `1.2.14-1+rpt1`
- `pyalsaaudio` dynamically links `libasound.so.2`
- `samplerate` links no dynamic `libsamplerate`; its pinned libsamplerate source
  is compiled into the extension

The rerun records SHA-256 and `ldd` output for both generated native extensions
in the raw packet. The samplerate extension SHA-256 matches the previously
recorded clean-build value. The pyalsaaudio extension has a newly recorded hash;
generated wheels and binaries are target-build evidence artifacts rather than
Core reference deliverables, so byte identity is not a gate.

## Retained failed attempt and cleanup

The first rerun attempt is retained as `FAIL`: a controller copied the already
verified NumPy wheel under an invalid shortened filename, which pip rejected
before the identity installation. Both source wheels had built successfully.
The second attempt used the same verified bytes under the official PyPI filename
and is the reviewed result above.

Both attempt directories, command logs, artifact and generated-wheel checksums,
runtime identity, native linkage, environment identity, controller status, and
cleanup proof are retained only under the controlled Git-ignored Pi path:
`poc_audio/evidence/m3_option_a/20260815T-a10-rerun2-de3b0ba/raw/`.
The completed controller recorded a clean worktree and zero ALSA device owners.
No raw audio was opened or retained.
