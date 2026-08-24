# M3-CORE-HAL-PLAYBACK-DRAIN-DEBUG-001

Status: `CONFIRMED CORE HAL PLAYBACK BLOCKER / PATCHED REVIEW CANDIDATE VERIFIED`

## Delivery contribution

This diagnostic advances the M3 physical AudioOutput, complete-playback, lifecycle,
and cleanup gates. It identifies why packet-pinned Core HAL playback could report
successful writes while producing no audible output, and verifies a minimal Core
patch on the target Pi. It is not a published M3 finalist score or an M3.1
front-end remediation.

## Exact identities

| Item | Identity |
| --- | --- |
| Audio POC formal runner | `655e80ec4ed287708ed0a47f383b645d88650b18` |
| Packet-pinned Core execution baseline | `ff09199583644a8f0822153e371589f52ae821a0` |
| Current Core branch base used for review | `51fe185d143595702caec03eeec7b63a63e2391d` |
| Isolated Core review candidate | `6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf` |
| Thin review bundle SHA-256 | `9c3631df2eb374730543532df835b1da5a4527cb85cd11fd477b1e91928aeb41` |
| Readable patch SHA-256 | `0973786ee71645db1b476ec5ce0065a93560e56964d24021fd47b3fd62d656de` |
| Controlled source WAV SHA-256 | `70869d488e5aa13559abbae225eb94918d3752cbfd0330ef669956381451c4a2` |

The controlled WAV remains outside Git. It is a 6.000-second, 16 kHz, mono,
S16_LE M3 operator capture. Its formal result remains
`DRAFT_USER_CONFIRMATION_PENDING`; this diagnostic does not publish or rescore it.

## Reproduction and isolation

The packet-pinned `AlsaAudioOutput` completed every write, reset its adapter, and
closed `hw:0,0`, but the operator heard no sound. Read-only checks established:

- the source and Core-adapted PCM were non-zero, unclipped, and measured
  `peak=-12.4 dBFS`, `RMS=-30.9 dBFS`;
- the exact Core adapter emitted identical left/right 48 kHz stereo S32_LE samples;
- the kernel enabled the VoiceHAT amplifier for the playback interval and disabled
  it afterward;
- ALSA device ownership returned to zero; and
- `aplay` of the original WAV and `aplay -D hw:0,0` of the Core-adapted native WAV
  were both audible.

The remaining difference was completion semantics. The accepted Core code flushed
the resampler and completed writes but never called ALSA `drain()` before close.
A direct pyalsaaudio test with the same `960 frames × 4` configuration plus one
success-path `drain()` was audible at a level comparable to `aplay`.

## Minimal patch

The review candidate changes only Core AudioOutput completion semantics:

- call `drain()` after iterator exhaustion, adapter flush, and all successful writes;
- do not drain iterator-error, write-error, force-abort, or cancellation paths;
- fail explicitly when the backend cannot provide success-path drain support;
- retain adapter reset and prompt close/device cleanup; and
- add portable coverage for five successful drains, abort/error/cancel exclusion,
  drain failure, reset, and close.

It does not change gain, sample scaling, resampler, chunking, period/buffer,
public/native formats, POC code, or frozen quality gates.

## Verification

| Environment | Check | Result |
| --- | --- | --- |
| Workstation, candidate `6c7fc8c...` | Focused AudioOutput suite | `8 passed` |
| Workstation, candidate `6c7fc8c...` | Full non-RPi suite | `268 passed, 21 deselected` |
| Pi 5, candidate `6c7fc8c...` | Focused AudioOutput suite | `8 passed` |
| Pi 5, candidate `6c7fc8c...` | Full non-RPi suite | `267 passed, 1 optional skipped, 21 deselected` |
| Pi 5, same started output | Five silent play/drain reuse cycles | `5/5 complete`, `0.580 s`, device released |
| Pi 5, exact adapted speech | Patched Core AudioOutput | drain complete, `6.055 s`, device released |
| Pi 5, operator observation | Exact adapted speech | audible; level comparable to `aplay` |

The one Pi optional skip is retained as reported; the focused file containing the
real samplerate test passed all eight tests. Temperature remained bounded and
throttling was `0x0` during the preceding diagnostic inventory.

## Disposition

M3 formal execution remains stopped. Core review/ACK and adoption of an authoritative
Core SHA are required before Audio updates the pinned packet identity and resumes.
This is a Core HAL completion defect, so the conditional M3.1 gain/pre-roll/front-end
framework is not activated.
