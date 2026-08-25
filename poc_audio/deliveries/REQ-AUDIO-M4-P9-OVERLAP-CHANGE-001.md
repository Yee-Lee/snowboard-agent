# REQ-AUDIO-M4-P9-OVERLAP-CHANGE-001

Status: `SUPERSEDED BY USER-DIRECTED P9.1 DESIGN`

On 2026-08-25 the User identified the original P9 method as a design defect and
directed Audio POC to propose P9.1. The replacement design is
`P9.1-REALISTIC-TURN-RESIDENCY-DESIGN-001`. This document remains as the
append-only failure diagnosis; its earlier external-decision request is no
longer the active closure path.

## Requested decision

LLM POC and Core must issue a versioned, checksum-locked correction before Audio
can resume formal M4 execution. The correction must choose and explicitly approve
one of these contract changes:

1. provide a new P9 surrogate whose worker lifetime covers the complete approved
   Audio session, preferably terminating on an explicit completion command; or
2. redefine the exact Audio workload boundary that must overlap each six-second
   `INFER`, then re-freeze the 20-entry catalog and runner semantics.

Audio must not extend the immutable artifact, shorten the approved full-session
workload, or reinterpret the overlap boundary without that written decision.

## Exact execution identity

- Audio candidate: `79185f992dd1510a9e8298242cec66b237081c52`
- Core HAL: `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf`
- P9 artifact: `M4B-P9-RESIDENCY-SURROGATE-001`, protocol `1.0`
- P9 runner SHA-256: `311466f963bce806b2c89a1c4f5b3275134312e307386c35631eabfb3d21be76`
- P9 lock SHA-256: `d8310132072e822a316521e3bd1cd21e7f0c8396dd49d82c1c6a64a247b7f7f0`
- P9 profile: four CPU workers for `6.0 s`, Pi 5 4GB, Debian 13,
  zero swap and offline execution
- Core runtime closure: `RESP-AUDIO-M4-RUNTIME-CLOSURE-002`; controller-r2,
  VAD and TTS preflights all passed against the pinned Core SHA

## Reproducible finding

The authorized formal P9 run produced a draft `FAIL` with
`P9ProtocolError: M4 Audio workload did not complete while P9 workers were alive`.
The controlled raw evidence SHA-256 is
`69be306ebc4ba5d7c7a6ad951fab9b983042a69f49b8b06a967a460d2f9b9c97`, at
`controlled://audio-poc/m4/20260825/p9-79185f9-closure`. Publication remains
pending explicit User confirmation.

A bounded single-session timing probe on the same clean Pi/runtime identities
measured:

| Stage | Elapsed |
| --- | ---: |
| Silero VAD | `0.169 s` |
| base-Q8 ASR under P9 load | `6.028 s` |
| Matcha generation plus physical playback | `2.261 s` |
| Complete Audio overlap | `8.459 s` |

The ASR stage alone exceeds the immutable six-second worker lifetime; the full
approved session cannot satisfy the current overlap requirement. This is not a
package-alignment failure and cannot be corrected by raising a client timeout.

## Audio-side follow-up after external correction

The same probe showed a controller thread delta of `+3` after the first Core
output conversion. An isolated resampler probe identified the NumPy/OpenBLAS
pool: default execution changed native threads from `1` to `4`, while
`OPENBLAS_NUM_THREADS=1` remained `1` to `1`. Audio will bind and regression-test
that controller setting in the next candidate; it does not resolve the P9
duration mismatch.

After the external response, Audio requires a new immutable candidate SHA, new
User authorization and fixture lock, then must restart in the approved order:
P9, independent offline 20-session combined validation, and 12 failure cases.
