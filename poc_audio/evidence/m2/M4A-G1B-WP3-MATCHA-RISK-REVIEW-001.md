# M4A Gate 1B WP3 Matcha risk-focused review

Status: `REVIEWED — M2 HIGH-RISK PASS / ADVANCE TO M3 FINALIST`

## Delivery contribution

This report closes the remaining M2 screen for exact candidate
`tts-sherpa-matcha-zh-en-1.13.5`. It combines the previously reviewed
performance/resource observations with one bounded lifecycle packet, one true
network-disabled P12 run, and the User's review of ten preselected high-risk
prompts. It advances Matcha as the TTS finalist for M3 hardware/HAL validation;
it does not claim final winner, redistribution approval, or M4 combined-system
acceptance.

## Scope and evidence binding

| Evidence | Exact source SHA / controlled result |
| --- | --- |
| Reviewed 20-prompt performance/resource packet | `63c2cc179bb3c2525201da0f7a78d2c50b63d759`; [`M4A-G1B-WP3-FULL-QUALIFICATION-001`](M4A-G1B-WP3-FULL-QUALIFICATION-001.md) |
| Risk-focused scope, lifecycle and P12 | `8a2ce01e2fdb120cff3be6a416ca6021ddb57fed` |
| Ten-prompt quality generator and packet | `cfba8165ca379d0bbb04e345c198f6f67886c601` |
| Lifecycle result | `~/.local/share/audio-poc/m4a/matcha-risk-lifecycle-8a2ce01-001.json`; SHA-256 `4f836b7cbba5d1e2ae844a2586b7fe59c39ea9e6787df972f6bb02dc3214d41c` |
| Network-disabled result | `~/.local/share/audio-poc/m4a/matcha-risk-offline-8a2ce01-001.json`; SHA-256 `d7a6244209728cdedf091e2b620676d6a1a26bed8b1fc75d2a36ddf8fa314cc3` |
| User-review packet | `~/.local/share/audio-poc/m4a/matcha-risk-quality-cfba816-001/review.json`; SHA-256 `4a01329c8f3699db582f9a7ed1c082cca5c6e20456efa9daa1aa1618863d4b10` |

All new packets ran on Raspberry Pi 5 Model B Rev 1.1, aarch64, kernel
`6.12.47+rpt-rpi-2712`, Python 3.13.5. The exact runtime remained
`sherpa-onnx==1.13.5` with the authorized Matcha acoustic archive and 16 kHz
Vocos. Raw WAV and JSON results remain outside Git at the controlled paths.

## Reviewed high-risk results

| Area | Reviewed result | Disposition |
| --- | --- | --- |
| Identity/runtime | Exact authorized runtime and artifacts were verified before generation | `PASS` |
| Performance | First-buffer p95 `285.098 ms`; RTF p95 `0.112776` | `PASS` under the existing M2 gates |
| Resource/thermal | Peak RSS `227.531 MiB` versus `1,000 MiB` advisory; hot-cycle RSS `227.734` to `228.203 MiB` then plateaued; qualification ended at 49.05 C with `throttled=0x0` | no material-risk blocker |
| Lifecycle | Success, declared error, timeout, cancel, force-abort and five reopen paths completed; final child/thread/iterator/stream/device-owner counters were zero | `PASS` |
| Offline P12 | In a disabled network namespace only loopback existed and was down; inference succeeded with zero network syscalls; latency `190.146 ms`, RTF `0.101192`, cleanup counters zero | `PASS` |
| User quality | Scores `5,5,5,5,5,5,4,5,5,5`; median `5`; no critical misread | `PASS` |

The resource movement is retained as an observation. Under the User-authorized
risk-focused scope, sub-MiB allocator/cache/page-accounting differences do not
trigger tuning or rejection when the process remains far below the advisory
ceiling, plateaus, and shows no thermal throttling.

## User quality review

The ten fixed 16 kHz mono S16_LE samples were played from the Pi through the
target speaker. The User assigned the following final scores on 2026-08-23:

| Index | Fixture | Score | Critical misread | Note |
| ---: | --- | ---: | --- | --- |
| 1 | `tts-005` | 5 | no | — |
| 2 | `tts-006` | 5 | no | — |
| 3 | `tts-008` | 5 | no | — |
| 4 | `tts-009` | 5 | no | — |
| 5 | `tts-011` | 5 | no | — |
| 6 | `tts-012` | 5 | no | — |
| 7 | `tts-013` | 4 | no | In `現在執行 start 和 stop。`, `start` sounded closer to `top`; the sample was replayed at normal speed and once at 80% speed before the final score. |
| 8 | `tts-014` | 5 | no | — |
| 9 | `tts-017` | 5 | no | — |
| 10 | `tts-018` | 5 | no | — |

The median is `5`, above the frozen M2 threshold of `>=4`, and the critical
misread count is zero. The `tts-013` pronunciation remains a recorded minor
quality risk for the full finalist review; it is not hidden or treated as a
critical command reversal.

## Decision and remaining boundary

Matcha passes this bounded M2 high-risk screen and is the TTS finalist to carry
into M3. No extra resource matrix, soak, pronunciation tuning, or full
20-prompt rerun is authorized in M2. M3/M4 must still validate the finalist on
the pinned Audio HAL and complete the full quality/combined-session scope.

The archive's missing embedded license/notice and unresolved training-data
lineage remain a known legal limitation. They do not block this internal,
offline POC report or M3 technical validation, but they block redistribution,
product adoption, and Gate 2B final-winner approval until User/Core records a
separate legal decision.
